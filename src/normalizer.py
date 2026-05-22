import re
import unicodedata
from datetime import timedelta, datetime


EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def _split_category(raw: str) -> tuple[str, str]:
    """
    Limpieza y atomización de strings para cumplimiento de la Primera Forma Normal (1FN).
    Divide categorías y descripciones combinadas en el esquema legacy para garantizar la 
    atomicidad de los datos en el nuevo modelo normalizado.
    """
    if raw and "|" in raw:
        name, desc = raw.split("|", 1)
        return name.strip(), desc.strip()
    return (raw or "Sin categoría").strip(), "Sin descripción"


def _clean_text(raw, default: str | None = None, title_case: bool = False) -> str | None:
    """Limpia espacios, tabs y valores vacíos de texto legacy."""
    if raw is None:
        return default
    value = re.sub(r"\s+", " ", str(raw)).strip()
    if not value or value.upper() in {"N/A", "NAN", "NONE", "NULL"}:
        return default
    return value.title() if title_case else value


def _slug_text(raw: str) -> str:
    """Convierte texto con acentos a una clave estable para correos fallback."""
    normalized = unicodedata.normalize("NFD", raw)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", ".", ascii_text.lower()).strip(".")
    return slug or "usuario.desconocido"


def _normalize_email(raw, user_name: str) -> str:
    """Normaliza correos legacy y genera uno estable cuando el correo no es válido."""
    email = _clean_text(raw)
    if email:
        email = email.lower().replace("_at_", "@").replace(" at ", "@")
        email = re.sub(r"\s+", "", email)
        if EMAIL_RE.match(email):
            return email
    return f"{_slug_text(user_name)}@sin-correo.local"


def _parse_date(raw) -> object:
    """
    Normaliza fechas heterogéneas del legado a objetos date de Python.
    Soporta formatos: YYYY-MM-DD, DD/MM/YYYY, M/D/YYYY y objetos date nativos.
    Retorna None para valores no parseables ('N/A', 'Desconocida', textos libres).
    """
    if raw is None:
        return None
    # Si ya es un objeto date/datetime, retornarlo directamente
    if hasattr(raw, 'year'):
        return raw
    raw_str = _clean_text(raw)
    if raw_str is None:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%-d/%-m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw_str, fmt).date()
        except (ValueError, TypeError):
            continue
    return None  # 'N/A', 'Desconocida', valores libres → NULL


def _normalize_loan_status(raw) -> str:
    """Convierte estados legacy del Excel al dominio permitido por PostgreSQL."""
    status = (raw or "").strip().upper()
    status_map = {
        "DEVUELTO": "DEVUELTO",
        "PENDIENTE": "ACTIVO",
        "ACTIVO": "ACTIVO",
        "ATRASADO": "VENCIDO",
        "VENCIDO": "VENCIDO",
    }
    return status_map.get(status, "ACTIVO")


def normalize_from_dirty(conn) -> dict:
    """
    Motor de normalización y transformación de datos (ETL Interno).
    El procesamiento en Python permite realizar una limpieza de strings y deduplicación 
    de entidades de mayor complejidad que el SQL estándar, resolviendo inconsistencias del modelo legacy.
    """
    stats = {"books": 0, "users": 0, "loans": 0, "inventory": 0, "reviews": 0}
    with conn.cursor() as cur:
        # 1. Extracción y Limpieza de Libros y autores
        cur.execute(
            'SELECT titulo_libro, autor_nombre, categoria_y_descripcion, '
            'editorial_info, fecha_publicacion FROM "Biblioteca_Data"'
        )
        books = cur.fetchall()
        for title, author, catdesc, editorial, pubdate in books:
            clean_title = _clean_text(title)
            if not clean_title:
                continue
            clean_author = _clean_text(author, "Autor Desconocido", title_case=True)
            clean_editorial = _clean_text(editorial, "Editorial Desconocida", title_case=True)
            category, description = _split_category(catdesc)
            category = _clean_text(category, "Sin categoría", title_case=True)
            description = _clean_text(description, "Sin descripción")
            parsed_pubdate = _parse_date(pubdate)
            # El uso de Stored Procedures centraliza la lógica de inserción en múltiples tablas relacionadas, 
            # asegurando la integridad referencial y la atomicidad de la transacción.
            cur.execute("SAVEPOINT normalize_book")
            try:
                cur.execute(
                    "CALL sp_insertar_libro(%s,%s,%s,%s,%s,%s)",
                    (clean_title, parsed_pubdate, category, description, clean_editorial, clean_author)
                )
                stats["books"] += 1
                cur.execute("RELEASE SAVEPOINT normalize_book")
            except Exception:
                cur.execute("ROLLBACK TO SAVEPOINT normalize_book")

        cur.execute(
            'SELECT nombre_usuario, correo_usuario, libros_prestados, '
            'fecha_salida, estado_prestamo FROM "Prestamos_Crudos"'
        )
        loans_seen: set[tuple[int, int, object, str]] = set()
        user_by_name: dict[str, int] = {}
        for user_name, email, borrowed, checkout, status in cur.fetchall():
            # Valor por defecto para nombres nulos en el legado
            clean_name = _clean_text(user_name, "Usuario Desconocido", title_case=True)
            valid_email = _normalize_email(email, clean_name)
            user_key = clean_name.casefold()

            if user_key in user_by_name:
                user_id = user_by_name[user_key]
            else:
                cur.execute("SAVEPOINT normalize_user")
                try:
                    cur.execute(
                        "INSERT INTO usuarios(nombre, correo) VALUES (%s,%s) "
                        "ON CONFLICT (correo) DO UPDATE SET correo=EXCLUDED.correo RETURNING id_usuario",
                        (clean_name, valid_email),
                    )
                    user_id = cur.fetchone()[0]
                    user_by_name[user_key] = user_id
                    stats["users"] += 1
                    cur.execute("RELEASE SAVEPOINT normalize_user")
                except Exception:
                    cur.execute("ROLLBACK TO SAVEPOINT normalize_user")
                    continue
            # Normalización de listas multivaloradas: la iteración del CSV permite la creación de registros 
            # individuales por cada libro prestado, cumpliendo estrictamente con la 1FN.
            for title in [_clean_text(item) for item in (borrowed or "").split(",")]:
                if not title:
                    continue
                cur.execute("SELECT id_libro FROM libros WHERE titulo=%s", (title,))
                result = cur.fetchone()
                if result:
                    # Limpieza y coerción de fecha usando _parse_date (soporta múltiples formatos del legado)
                    parsed_checkout = _parse_date(checkout) or datetime.today().date()
                    clean_status = _normalize_loan_status(status)
                    return_date = parsed_checkout + timedelta(days=10) if clean_status == "DEVUELTO" else None
                    loan_key = (user_id, result[0], parsed_checkout, clean_status)
                    if loan_key in loans_seen:
                        continue
                    loans_seen.add(loan_key)
                    cur.execute(
                        "INSERT INTO prestamos(id_usuario, id_libro, fecha_salida, fecha_devolucion, estado) "
                        "VALUES (%s,%s,%s,%s,%s)",
                        (user_id, result[0], parsed_checkout, return_date, clean_status),
                    )
                    stats["loans"] += 1

        cur.execute('SELECT sede_nombre, ubicacion_sede, libro_asociado, cantidad_total FROM "Inventario_Sedes"')
        for branch, location, title, quantity in cur.fetchall():
            clean_branch = _clean_text(branch, "Sede Desconocida", title_case=True)
            clean_location = _clean_text(location, "Sin ubicacion")
            cur.execute("SAVEPOINT normalize_sede")
            try:
                cur.execute(
                    "INSERT INTO sedes(nombre, ubicacion) VALUES (%s,%s) "
                    "ON CONFLICT (nombre) DO UPDATE SET ubicacion=EXCLUDED.ubicacion RETURNING id_sede",
                    (clean_branch, clean_location)
                )
                branch_id = cur.fetchone()[0]
                cur.execute("RELEASE SAVEPOINT normalize_sede")
            except Exception:
                cur.execute("ROLLBACK TO SAVEPOINT normalize_sede")
                continue

            clean_title = _clean_text(title)
            cur.execute("SELECT id_libro FROM libros WHERE titulo=%s", (clean_title,))
            book = cur.fetchone()
            if book:
                # Coercion de tipo para cantidad_total (evitando textos como "Diez" o negativos)
                try:
                    qty = int(quantity)
                    qty = max(0, qty)
                except (ValueError, TypeError):
                    qty = 0

                cur.execute("SAVEPOINT normalize_inv")
                try:
                    cur.execute(
                        "INSERT INTO inventario(id_sede, id_libro, cantidad_total) VALUES (%s,%s,%s) "
                        "ON CONFLICT (id_sede,id_libro) DO UPDATE SET cantidad_total=EXCLUDED.cantidad_total",
                        (branch_id, book[0], qty)
                    )
                    stats["inventory"] += 1
                    cur.execute("RELEASE SAVEPOINT normalize_inv")
                except Exception:
                    cur.execute("ROLLBACK TO SAVEPOINT normalize_inv")

        cur.execute('SELECT usuario_id, libro_titulo, comentario, calificacion FROM "Reseñas_Usuarios"')
        for user_raw_id, title, comment, rating in cur.fetchall():
            clean_title = _clean_text(title)
            cur.execute("SELECT id_libro FROM libros WHERE titulo=%s", (clean_title,))
            book = cur.fetchone()
            # usuario_id puede ser un entero, texto como 'Usuario_Desconocido', o None
            try:
                uid_offset = max(int(str(user_raw_id).strip()) - 1, 0)
            except (ValueError, TypeError):
                uid_offset = 0
            cur.execute(
                "SELECT id_usuario FROM usuarios ORDER BY id_usuario OFFSET %s LIMIT 1",
                (uid_offset,)
            )
            user = cur.fetchone()
            if book and user:
                # Coercion de calificacion caotica ("5/5", "Cinco", nulos)
                try:
                    rtg = int(str(rating).split("/")[0]) if rating else 3
                except ValueError:
                    rtg = 3
                rtg = max(1, min(5, rtg))

                cur.execute("SAVEPOINT normalize_resena")
                try:
                    cur.execute(
                        "INSERT INTO resenas(id_usuario, id_libro, comentario, calificacion) VALUES (%s,%s,%s,%s) "
                        "ON CONFLICT (id_usuario,id_libro) DO NOTHING",
                        (user[0], book[0], _clean_text(comment, "Sin comentario"), rtg)
                    )
                    stats["reviews"] += 1
                    cur.execute("RELEASE SAVEPOINT normalize_resena")
                except Exception:
                    cur.execute("ROLLBACK TO SAVEPOINT normalize_resena")
    return stats

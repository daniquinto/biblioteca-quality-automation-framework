from datetime import timedelta


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


def normalize_from_dirty(conn) -> dict:
    """
    Motor de normalización y transformación de datos (ETL Interno).
    El procesamiento en Python permite realizar una limpieza de strings y deduplicación 
    de entidades de mayor complejidad que el SQL estándar, resolviendo inconsistencias del modelo legacy.
    """
    stats = {"books": 0, "users": 0, "loans": 0, "inventory": 0, "reviews": 0}
    with conn.cursor() as cur:
        # 1. Extracción y Limpieza de Libros y autores
        cur.execute('SELECT titulo_libro, autor_nombre, categoria_y_descripcion, editorial_info, fecha_publicacion FROM "Biblioteca_Data"')
        books = cur.fetchall()
        for title, author, catdesc, editorial, pubdate in books:
            category, description = _split_category(catdesc)
            # El uso de Stored Procedures centraliza la lógica de inserción en múltiples tablas relacionadas, 
            # asegurando la integridad referencial y la atomicidad de la transacción.
            cur.execute("CALL sp_insertar_libro(%s,%s,%s,%s,%s,%s)", (title, pubdate, category, description, editorial, author))
            stats["books"] += 1

        cur.execute('SELECT nombre_usuario, correo_usuario, libros_prestados, fecha_salida, estado_prestamo FROM "Prestamos_Crudos"')
        for user_name, email, borrowed, checkout, status in cur.fetchall():
            # Limpieza de correo electrónico mediante expresiones regulares
            import re
            valid_email = email if email and re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email) else f"usuario_{stats['users']}@invalido.com"
            
            cur.execute(
                "INSERT INTO usuarios(nombre, correo) VALUES (%s,%s) ON CONFLICT (correo) DO UPDATE SET nombre=EXCLUDED.nombre RETURNING id_usuario",
                (user_name, valid_email),
            )
            user_id = cur.fetchone()[0]
            stats["users"] += 1
            # Normalización de listas multivaloradas: la iteración del CSV permite la creación de registros 
            # individuales por cada libro prestado, cumpliendo estrictamente con la 1FN.
            for title in [item.strip() for item in (borrowed or "").split(",") if item.strip()]:
                cur.execute("SELECT id_libro FROM libros WHERE titulo=%s", (title,))
                result = cur.fetchone()
                if result:
                    # Limpieza y coerción de fecha usando datetime (evitando "Sin fecha")
                    from datetime import datetime
                    try:
                        if isinstance(checkout, str):
                            parsed_checkout = datetime.strptime(checkout.strip(), "%Y-%m-%d").date()
                        else:
                            parsed_checkout = checkout
                    except Exception:
                        parsed_checkout = datetime.today().date()
                        
                    return_date = parsed_checkout + timedelta(days=10) if status == "DEVUELTO" else None
                    cur.execute(
                        "INSERT INTO prestamos(id_usuario, id_libro, fecha_salida, fecha_devolucion, estado) VALUES (%s,%s,%s,%s,%s)",
                        (user_id, result[0], parsed_checkout, return_date, status),
                    )
                    stats["loans"] += 1

        cur.execute('SELECT sede_nombre, ubicacion_sede, libro_asociado, cantidad_total FROM "Inventario_Sedes"')
        for branch, location, title, quantity in cur.fetchall():
            cur.execute("INSERT INTO sedes(nombre, ubicacion) VALUES (%s,%s) ON CONFLICT (nombre) DO UPDATE SET ubicacion=EXCLUDED.ubicacion RETURNING id_sede", (branch, location))
            branch_id = cur.fetchone()[0]
            cur.execute("SELECT id_libro FROM libros WHERE titulo=%s", (title,))
            book = cur.fetchone()
            if book:
                # Coerción de tipo para cantidad_total (evitando textos como "Diez" o negativos)
                try:
                    qty = int(quantity)
                    qty = max(0, qty)
                except (ValueError, TypeError):
                    qty = 0
                    
                cur.execute("INSERT INTO inventario(id_sede, id_libro, cantidad_total) VALUES (%s,%s,%s) ON CONFLICT (id_sede,id_libro) DO UPDATE SET cantidad_total=EXCLUDED.cantidad_total", (branch_id, book[0], qty))
                stats["inventory"] += 1

        cur.execute('SELECT usuario_id, libro_titulo, comentario, calificacion FROM "Reseñas_Usuarios"')
        for user_raw_id, title, comment, rating in cur.fetchall():
            cur.execute("SELECT id_libro FROM libros WHERE titulo=%s", (title,))
            book = cur.fetchone()
            cur.execute("SELECT id_usuario FROM usuarios ORDER BY id_usuario OFFSET %s LIMIT 1", (max(int(user_raw_id) - 1, 0),))
            user = cur.fetchone()
            if book and user:
                # Coerción de calificación caótica ("5/5", "Cinco", nulos)
                try:
                    rtg = int(str(rating).split("/")[0]) if rating else 3
                except ValueError:
                    rtg = 3
                rtg = max(1, min(5, rtg))
                
                cur.execute("INSERT INTO resenas(id_usuario, id_libro, comentario, calificacion) VALUES (%s,%s,%s,%s) ON CONFLICT (id_usuario,id_libro) DO NOTHING", (user[0], book[0], comment, rtg))
                stats["reviews"] += 1
    return stats

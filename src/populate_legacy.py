import random
from datetime import date, timedelta
from faker import Faker

BOOK_WORDS = ["Datos", "Algoritmos", "Calidad", "Python", "MongoDB", "PostgreSQL", "Arquitectura", "Software"]
CATEGORIES = ["Tecnología", "Literatura", "Ciencia", "Historia", "Matemáticas", "Ingeniería"]
STATES = ["ACTIVO", "DEVUELTO", "VENCIDO"]

def random_title(fake: Faker) -> str:
    return f"{random.choice(BOOK_WORDS)} y {fake.word().capitalize()} {random.randint(1, 999)}"

def inject_noise(text: str) -> str:
    """Inyecta ruido tipográfico aleatorio a una cadena (espacios, mayúsculas)."""
    if random.random() < 0.2:
        return f"   {text}  \t"
    if random.random() < 0.2:
        return text.upper()
    if random.random() < 0.1:
        return "NaN"
    return text

def populate_dirty_tables(conn, total_records: int = 250, locale: str = "es_CO") -> dict:
    """Generador de datos sintéticos con anomalías caóticas explícitas."""
    fake = Faker(locale)
    inserted = {"Biblioteca_Data": 0, "Prestamos_Crudos": 0, "Inventario_Sedes": 0, "Reseñas_Usuarios": 0}
    created_titles: list[str] = []
    
    with conn.cursor() as cur:
        cur.execute('SELECT COALESCE(MAX(id_registro), 0) FROM "Biblioteca_Data"')
        max_id = cur.fetchone()[0]

        for i in range(total_records):
            title = random_title(fake)
            created_titles.append(title)
            category = random.choice(CATEGORIES)
            description = fake.sentence(nb_words=8)
            
            # --- ANOMALÍAS EN Biblioteca_Data ---
            # Fechas inconsistentes
            pub_date = fake.date_between(start_date="-25y", end_date="today").isoformat()
            if random.random() < 0.1:
                pub_date = "Desconocida"
            elif random.random() < 0.1:
                pub_date = "N/A"
            elif random.random() < 0.2:
                # Formato DD/MM/YYYY
                pub_date = fake.date_between(start_date="-25y", end_date="today").strftime("%d/%m/%Y")
            
            titulo_ruido = inject_noise(title)
            autor_ruido = inject_noise(fake.name())
            
            # Simular id_registro duplicado inyectándolo explícitamente a veces (basado en el max_id actual)
            current_id = max_id + i + 1
            id_registro = current_id if random.random() > 0.1 else random.randint(max_id + 1, current_id)
            
            cur.execute("SAVEPOINT populate_row")
            try:
                cur.execute(
                    'INSERT INTO "Biblioteca_Data" (id_registro, titulo_libro, autor_nombre, '
                    'categoria_y_descripcion, editorial_info, fecha_publicacion) VALUES (%s,%s,%s,%s,%s,%s)',
                    (id_registro, titulo_ruido, autor_ruido, f"{category}|{description}", fake.company(), pub_date),
                )
                inserted["Biblioteca_Data"] += 1
                
                # Ocasionalmente duplicar fila entera
                if random.random() < 0.05:
                    cur.execute(
                        'INSERT INTO "Biblioteca_Data" (id_registro, titulo_libro, autor_nombre, '
                        'categoria_y_descripcion, editorial_info, fecha_publicacion) VALUES (%s,%s,%s,%s,%s,%s)',
                        (id_registro, titulo_ruido, autor_ruido, f"{category}|{description}", fake.company(), pub_date),
                    )
                    inserted["Biblioteca_Data"] += 1
                
                cur.execute("RELEASE SAVEPOINT populate_row")
            except Exception:
                cur.execute("ROLLBACK TO SAVEPOINT populate_row")

            # --- ANOMALÍAS EN Prestamos_Crudos ---
            borrowed_books = ", ".join(random.sample(created_titles, k=min(len(created_titles), random.randint(1, 3))))
            
            # Correos rotos o nulos
            email = fake.email()
            if random.random() < 0.1:
                email = email.replace("@", "_at_")
            elif random.random() < 0.1:
                email = None
                
            # Fechas mixtas
            raw_date = date.today() - timedelta(days=random.randint(0, 45))
            str_date = raw_date.isoformat()
            if random.random() < 0.1:
                str_date = "Sin fecha"
            elif random.random() < 0.1:
                str_date = raw_date.strftime("%d/%m/%Y")
            
            id_prestamo = max_id + i + 1 if random.random() > 0.05 else max_id + i # Duplicate IDs
                
            cur.execute(
                'INSERT INTO "Prestamos_Crudos" (id_prestamo, nombre_usuario, correo_usuario, '
                'libros_prestados, fecha_salida, estado_prestamo) VALUES (%s,%s,%s,%s,%s,%s)',
                (id_prestamo, fake.name(), email, borrowed_books, str_date, random.choice(STATES)),
            )
            inserted["Prestamos_Crudos"] += 1
            # Duplicar fila entera de préstamo a veces
            if random.random() < 0.05:
                cur.execute(
                    'INSERT INTO "Prestamos_Crudos" (id_prestamo, nombre_usuario, correo_usuario, '
                    'libros_prestados, fecha_salida, estado_prestamo) VALUES (%s,%s,%s,%s,%s,%s)',
                    (id_prestamo, fake.name(), email, borrowed_books, str_date, random.choice(STATES)),
                )
                inserted["Prestamos_Crudos"] += 1

            # --- ANOMALÍAS EN Inventario_Sedes ---
            sede_nombre = f"Sede {random.randint(1, 8)}"
            if random.random() < 0.1:
                sede_nombre = f"  {sede_nombre.lower()} \t"
                
            cantidad_total = str(random.randint(0, 40))
            if random.random() < 0.1:
                cantidad_total = "-5" # negativo
            elif random.random() < 0.1:
                cantidad_total = "Diez" # texto
            elif random.random() < 0.1:
                cantidad_total = None # nulo
                
            cur.execute(
                'INSERT INTO "Inventario_Sedes" (sede_nombre, ubicacion_sede, libro_asociado, '
                'cantidad_total) VALUES (%s,%s,%s,%s)',
                (sede_nombre, fake.address().replace("\n", ", "), title, cantidad_total),
            )
            inserted["Inventario_Sedes"] += 1

            # --- ANOMALÍAS EN Reseñas_Usuarios ---
            usuario_id = str(max_id + i + 1)
            if random.random() < 0.1:
                usuario_id = "Usuario_Desconocido"
            elif random.random() < 0.1:
                usuario_id = None
                
            calificaciones_caoticas = ["5/5", "Cinco", "2-5", "10/5", "3"]
            calificacion = str(random.randint(1, 5))
            if random.random() < 0.3:
                calificacion = random.choice(calificaciones_caoticas)
                
            cur.execute(
                'INSERT INTO "Reseñas_Usuarios" (usuario_id, libro_titulo, comentario, calificacion) '
                'VALUES (%s,%s,%s,%s)',
                (usuario_id, title, fake.sentence(nb_words=12), calificacion),
            )
            inserted["Reseñas_Usuarios"] += 1

    return inserted

import random
from datetime import date, timedelta
from faker import Faker

BOOK_WORDS = ["Datos", "Algoritmos", "Calidad", "Python", "MongoDB", "PostgreSQL", "Arquitectura", "Software"]
CATEGORIES = ["Tecnología", "Literatura", "Ciencia", "Historia", "Matemáticas", "Ingeniería"]
STATES = ["ACTIVO", "DEVUELTO", "VENCIDO"]


def random_title(fake: Faker) -> str:
    return f"{random.choice(BOOK_WORDS)} y {fake.word().capitalize()} {random.randint(1, 999)}"


def populate_dirty_tables(conn, total_records: int = 250, locale: str = "es_CO") -> dict:
    """
    Generador de datos sintéticos degradados para pruebas de integridad.
    La inserción de registros con fallos estructurales permite validar la capacidad de 
    detección del motor de calidad y demostrar la ineficiencia del modelo legacy ante volúmenes crecientes.
    """
    fake = Faker(locale)
    inserted = {"Biblioteca_Data": 0, "Prestamos_Crudos": 0, "Inventario_Sedes": 0, "Reseñas_Usuarios": 0}
    created_titles: list[str] = []
    with conn.cursor() as cur:
        for i in range(total_records):
            title = random_title(fake)
            created_titles.append(title)
            category = random.choice(CATEGORIES)
            description = fake.sentence(nb_words=8)
            publication_date = fake.date_between(start_date="-25y", end_date="today").isoformat()
            
            # Introducción del separador '|' para simular falta de atomicidad en los atributos (Violación de la 1FN).
            cur.execute(
                'INSERT INTO "Biblioteca_Data" (titulo_libro, autor_nombre, categoria_y_descripcion, editorial_info, fecha_publicacion) VALUES (%s,%s,%s,%s,%s)',
                (title, fake.name(), f"{category}|{description}", fake.company(), publication_date),
            )
            inserted["Biblioteca_Data"] += 1

            # Simulación de listas multivaloradas en préstamos para forzar el análisis de cumplimiento de la 1FN.
            borrowed_books = ", ".join(random.sample(created_titles, k=min(len(created_titles), random.randint(1, 3))))
            cur.execute(
                'INSERT INTO "Prestamos_Crudos" (id_prestamo, nombre_usuario, correo_usuario, libros_prestados, fecha_salida, estado_prestamo) VALUES (%s,%s,%s,%s,%s,%s)',
                (i + 1, fake.name(), fake.email(), borrowed_books, date.today() - timedelta(days=random.randint(0, 45)), random.choice(STATES)),
            )
            inserted["Prestamos_Crudos"] += 1

            # Generación de redundancia de datos de sedes por cada libro para evaluar el impacto de la desnormalización.
            cur.execute(
                'INSERT INTO "Inventario_Sedes" (sede_nombre, ubicacion_sede, libro_asociado, cantidad_total) VALUES (%s,%s,%s,%s)',
                (f"Sede {random.randint(1, 8)}", fake.address().replace("\n", ", "), title, random.randint(0, 40)),
            )
            inserted["Inventario_Sedes"] += 1

            # Almacenamiento de calificaciones como texto para validar la detección de tipos de datos inconsistentes.
            cur.execute(
                'INSERT INTO "Reseñas_Usuarios" (usuario_id, libro_titulo, comentario, calificacion) VALUES (%s,%s,%s,%s)',
                (i + 1, title, fake.sentence(nb_words=12), str(random.randint(1, 5))),
            )
            inserted["Reseñas_Usuarios"] += 1
    return inserted

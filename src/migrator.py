from datetime import date, datetime
from pathlib import Path
from .utils import load_json

def _json_safe(value):
    """
    Normalizador de tipos para compatibilidad JSON.
    Transforma objetos 'date' y 'datetime' al estándar ISO 8601, resolviendo la limitación 
    nativa del formato JSON para el manejo de tipos temporales de Python/Postgres.
    """
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value

def migrate_to_mongo(conn, mongo_db, mapping_path: Path) -> dict:
    """
    Orquestador de migración de esquema relacional a documental.
    Implementa un modelo denormalizado en MongoDB para optimizar el rendimiento de lectura 
    mediante el acceso a datos en un solo paso, evitando operaciones de 'lookup' en tiempo real.
    """
    load_json(mapping_path)  
    stats = {"books": 0, "users": 0, "loans": 0, "inventory": 0}
    
    # Asegura la idempotencia de la migración mediante la limpieza de colecciones de destino
    mongo_db.books.delete_many({})
    mongo_db.users.delete_many({})
    mongo_db.loans.delete_many({})
    mongo_db.inventory.delete_many({})

    with conn.cursor() as cur:
        # Extracción consolidada de libros y autores mediante agregación SQL.
        # El uso de ARRAY_AGG y GROUP BY reduce la latencia de red al recuperar 
        # múltiples relaciones en una sola transacción hacia PostgreSQL.
        cur.execute("""
            SELECT l.id_libro, l.titulo, l.fecha_publicacion, c.nombre, c.descripcion, e.nombre,
                   COALESCE(ARRAY_AGG(a.nombre) FILTER (WHERE a.nombre IS NOT NULL), '{}') AS autores
            FROM libros l
            LEFT JOIN categorias c ON c.id_categoria = l.id_categoria
            LEFT JOIN editoriales e ON e.id_editorial = l.id_editorial
            LEFT JOIN libros_autores la ON la.id_libro = l.id_libro
            LEFT JOIN autores a ON a.id_autor = la.id_autor
            GROUP BY l.id_libro, l.titulo, l.fecha_publicacion, c.nombre, c.descripcion, e.nombre
        """)
        
        books = []
        for row in cur.fetchall():
            # Implementación del patrón de 'Documento Embebido' para categorías y editoriales.
            # Los datos con baja tasa de cambio se encapsulan en el documento del libro 
            # para maximizar la eficiencia de las consultas de catálogo.
            books.append({
                "book_id": row[0],
                "title": row[1],
                "published_at": _json_safe(row[2]),
                "category": {"name": row[3], "description": row[4]},
                "publisher": {"name": row[5]},
                "authors": [{"name": author} for author in row[6]],
            })
            
        if books:
            mongo_db.books.insert_many(books)
        stats["books"] = len(books)

        # Migración de Usuarios: Mantenemos la estructura plana por simplicidad de búsqueda
        cur.execute("SELECT id_usuario, nombre, correo FROM usuarios")
        users = [{"user_id": r[0], "name": r[1], "email": r[2]} for r in cur.fetchall()]
        if users:
            mongo_db.users.insert_many(users)
        stats["users"] = len(users)

        # Migración de Préstamos: Se mantienen referencias (IDs) en lugar de embeber el libro completo
        # para evitar el crecimiento excesivo del documento del usuario.
        cur.execute("SELECT id_prestamo, id_usuario, id_libro, fecha_salida, fecha_devolucion, estado FROM prestamos")
        loans = [{"loan_id": r[0], "user_id": r[1], "book_id": r[2], "checkout_date": _json_safe(r[3]), "return_date": _json_safe(r[4]), "status": r[5]} for r in cur.fetchall()]
        if loans:
            mongo_db.loans.insert_many(loans)
        stats["loans"] = len(loans)

        # Migración de Inventario
        cur.execute("SELECT id_sede, id_libro, cantidad_total FROM inventario")
        inventory = [{"branch_id": r[0], "book_id": r[1], "total_quantity": r[2]} for r in cur.fetchall()]
        if inventory:
            mongo_db.inventory.insert_many(inventory)
        stats["inventory"] = len(inventory)
        
    return stats

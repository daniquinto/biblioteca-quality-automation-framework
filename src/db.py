import os
from contextlib import contextmanager
from dotenv import load_dotenv
import psycopg2
from pymongo import MongoClient

load_dotenv()

@contextmanager
def pg_connection():
    """
    Context Manager para PostgreSQL.
    Asegura el cierre automático de la conexión (idempotencia y liberación de recursos) 
    independientemente del éxito o fallo de las operaciones en el bloque 'with'.
    """
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "biblioteca_db"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )
    try:
        yield conn
        conn.commit()  # Persistencia atómica de las transacciones confirmadas.
    except Exception:
        conn.rollback()  # Preservación de la consistencia de la base de datos ante excepciones.
        raise
    finally:
        conn.close()

def mongo_database():
    """
    Singleton de conexión para el motor documental MongoDB.
    La parametrización mediante URI permite la adaptabilidad de la infraestructura 
    sin modificar la lógica de persistencia del framework.
    """
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    return client[os.getenv("MONGO_DB", "biblioteca_mongo")]

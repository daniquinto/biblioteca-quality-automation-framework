import os
from contextlib import contextmanager
from dotenv import load_dotenv
import psycopg2
from pymongo import MongoClient

load_dotenv()


@contextmanager
def pg_connection():
    """
    Context Manager para asegurar que la conexión a PostgreSQL se cierra
    correctamente y se hace commit de las transacciones.
    """
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "biblioteca_db"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def mongo_database():
    """
    Retorna la base de datos de MongoDB lista para usar.
    """
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    return client[os.getenv("MONGO_DB", "biblioteca_mongo")]

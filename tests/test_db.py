import pytest
from unittest.mock import patch, MagicMock
from src.db import pg_connection, mongo_database

@patch('src.db.psycopg2')
def test_pg_connection_success(mock_psycopg2):
    """Valida que pg_connection hace commit y close automáticamente."""
    mock_conn = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn

    with pg_connection() as conn:
        assert conn == mock_conn

    assert mock_conn.commit.called
    assert mock_conn.close.called
    assert not mock_conn.rollback.called

@patch('src.db.psycopg2')
def test_pg_connection_exception(mock_psycopg2):
    """Valida que una excepción provoca un rollback."""
    mock_conn = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn

    with pytest.raises(ValueError):
        with pg_connection():
            raise ValueError("Test Error")

    assert mock_conn.rollback.called
    assert mock_conn.close.called
    assert not mock_conn.commit.called

@patch('src.db.MongoClient')
def test_mongo_database(mock_mongo_client):
    """Valida la conexión a MongoDB."""
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client
    
    # Mockear el acceso por índice/llave al diccionario del cliente
    mock_db = MagicMock()
    mock_client.__getitem__.return_value = mock_db

    db = mongo_database()

    assert mock_mongo_client.called
    assert db == mock_db

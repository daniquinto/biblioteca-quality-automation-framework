import pytest
from unittest.mock import MagicMock, patch
from src.migrator import migrate_to_mongo

def test_migrate_to_mongo_success():
    """Valida el proceso de transformación y carga hacia NoSQL."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Mockear las lecturas de base de datos
    # 1. Usuarios, 2. Préstamos de ese usuario
    mock_cursor.fetchall.side_effect = [
        [(1, "Juan", "juan@test.com")], # Usuarios
        [(101, "Libro A", "2023-01-01", "2023-01-15", "DEVUELTO")], # Préstamos del usuario 1
    ]

    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    stats = migrate_to_mongo(mock_conn, mock_db, "dummy_mapping.json")

    assert mock_collection.insert_one.call_count == 1
    
    # Validar que se enmascaró el email
    args, _ = mock_collection.insert_one.call_args
    doc = args[0]
    assert doc["nombre"] == "Juan"
    assert doc["email"] != "juan@test.com" # Debe estar enmascarado
    assert len(doc["prestamos"]) == 1

def test_migrate_to_mongo_empty():
    """Valida el comportamiento si no hay usuarios."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    mock_db = MagicMock()
    
    stats = migrate_to_mongo(mock_conn, mock_db, "dummy.json")
    
    assert stats["usuarios_migrados"] == 0

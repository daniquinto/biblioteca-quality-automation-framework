from unittest.mock import MagicMock, patch
from src.migrator import migrate_to_mongo


@patch("src.migrator.load_json")
def test_migrate_to_mongo_masks_email(mock_load_json):
    """Valida que los emails de usuarios se enmascaren antes de insertar en MongoDB."""
    mock_load_json.return_value = {}
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Simula: libros, usuarios, préstamos, inventario
    mock_cursor.fetchall.side_effect = [
        [],  # books (SELECT con GROUP BY)
        [(1, "Juan Pérez", "juan@test.com")],   # usuarios
        [],  # préstamos
        [],  # inventario
    ]

    mock_db = MagicMock()
    mock_db.books = MagicMock()
    mock_db.users = MagicMock()
    mock_db.loans = MagicMock()
    mock_db.inventory = MagicMock()

    stats = migrate_to_mongo(mock_conn, mock_db, "dummy_mapping.json")

    # Debe haber intentado insertar usuarios
    assert mock_db.users.insert_many.called
    inserted_users = mock_db.users.insert_many.call_args[0][0]
    assert len(inserted_users) == 1
    assert inserted_users[0]["email"] != "juan@test.com"   # PII enmascarado
    assert inserted_users[0]["name"] == "Juan Pérez"
    assert stats["users"] == 1


@patch("src.migrator.load_json")
def test_migrate_to_mongo_empty_tables(mock_load_json):
    """Valida que con tablas vacías no se llame insert_many."""
    mock_load_json.return_value = {}
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    mock_db = MagicMock()
    mock_db.books = MagicMock()
    mock_db.users = MagicMock()
    mock_db.loans = MagicMock()
    mock_db.inventory = MagicMock()

    stats = migrate_to_mongo(mock_conn, mock_db, "dummy.json")

    assert stats["books"] == 0
    assert stats["users"] == 0
    assert stats["loans"] == 0
    mock_db.users.insert_many.assert_not_called()

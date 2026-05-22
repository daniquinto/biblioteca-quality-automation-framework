import pytest
from unittest.mock import MagicMock
from src.populate_legacy import populate_dirty_tables

def test_populate_dirty_tables():
    """Valida la generación de datos sintéticos con Faker."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    stats = populate_dirty_tables(mock_conn, total_records=10)

    # 4 tablas x 10 registros
    assert mock_cursor.execute.call_count == 40
    assert stats["Biblioteca_Data"] == 10
    assert stats["Prestamos_Crudos"] == 10
    assert stats["Inventario_Sedes"] == 10
    assert stats["Reseñas_Usuarios"] == 10

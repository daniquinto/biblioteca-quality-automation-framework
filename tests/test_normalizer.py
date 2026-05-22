import pytest
from unittest.mock import MagicMock
from src.normalizer import normalize_from_dirty, _split_category

def test_split_category():
    """Valida la atomización de la categoría y descripción."""
    # Caso 1: Formato válido con pipe
    cat, desc = _split_category("Ciencia Ficción | Una gran novela")
    assert cat == "Ciencia Ficción"
    assert desc == "Una gran novela"
    
    # Caso 2: Sin pipe, solo categoría
    cat, desc = _split_category("Drama")
    assert cat == "Drama"
    assert desc == "Sin descripción"
    
    # Caso 3: String vacío o nulo
    cat, desc = _split_category("")
    assert cat == "Sin categoría"
    assert desc == "Sin descripción"
    
    cat, desc = _split_category(None)
    assert cat == "Sin categoría"
    assert desc == "Sin descripción"

def test_normalize_from_dirty_success():
    """Valida que la normalización ejecute las queries correctas."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Simulamos fetchalls vacíos para evitar error con fetchone
    mock_cursor.fetchall.return_value = []
    
    # Simulamos fetchone
    mock_cursor.fetchone.return_value = (5,)

    stats = normalize_from_dirty(mock_conn)

    assert mock_cursor.execute.call_count > 0
    assert "books" in stats
    assert "users" in stats

def test_normalize_from_dirty_exception():
    """Valida que un error en la BD lance una excepción."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    mock_cursor.execute.side_effect = Exception("DB error")
    
    with pytest.raises(Exception, match="DB error"):
        normalize_from_dirty(mock_conn)

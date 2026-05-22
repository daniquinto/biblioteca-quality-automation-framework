import pytest
from unittest.mock import MagicMock, patch
from src.normalizer import normalize_from_dirty

def test_normalize_from_dirty_success():
    """Valida que la normalización ejecute las queries correctas."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Simulamos que las queries no devuelven error y algunas hacen fetch
    mock_cursor.fetchone.return_value = (5,)

    stats = normalize_from_dirty(mock_conn)

    assert mock_cursor.execute.call_count > 0
    assert "categorias" in stats
    assert "autores" in stats
    assert "editoriales" in stats
    assert stats["categorias"] == 5

def test_normalize_from_dirty_exception():
    """Valida que un error en la BD lance una excepción."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    mock_cursor.execute.side_effect = Exception("DB error")
    
    with pytest.raises(Exception, match="DB error"):
        normalize_from_dirty(mock_conn)

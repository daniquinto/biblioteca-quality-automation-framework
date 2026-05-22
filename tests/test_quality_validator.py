from unittest.mock import MagicMock, patch
from src.quality_validator import validate_dirty_data

@patch('src.quality_validator.load_json')
def test_validate_dirty_data_success(mock_load_json):
    """Valida que la calidad verifique reglas regex y retorne el reporte."""
    # Mockear las reglas
    mock_load_json.return_value = {
        "reglas": {
            "Prestamos_Crudos": [
                {"campo": "correo_usuario", "pattern": "^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$"}
            ]
        }
    }
    
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    # Supongamos que mock_cursor.description retorna el nombre de las columnas
    mock_cursor.description = [("id",), ("correo_usuario",)]
    
    # 3 filas: 2 con correos válidos, 1 inválido
    mock_cursor.fetchall.return_value = [
        (1, "test@test.com"),
        (2, "usuario_at_email.com"), # Inválido
        (3, "valido@correo.com")
    ]
    
    report = validate_dirty_data(mock_conn, "dummy.json")
    
    assert report["total_records"] == 3
    assert report["invalid_records"] == 1
    
def test_validate_dirty_data_no_rules():
    """Valida el comportamiento si el json de reglas está vacío o no coincide."""
    with patch('src.quality_validator.load_json') as mock_load_json:
        mock_load_json.return_value = {"reglas": {}}
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        report = validate_dirty_data(mock_conn, "dummy.json")
        assert report["total_records"] == 0
        assert report["invalid_records"] == 0

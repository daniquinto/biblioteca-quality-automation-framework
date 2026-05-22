from unittest.mock import MagicMock, patch
from src.quality_validator import validate_dirty_data


@patch("src.quality_validator.load_json")
def test_validate_dirty_data_success(mock_load_json):
    """Valida que la calidad verifique reglas regex y retorne el reporte."""
    # La clave correcta del JSON es "tables", no "reglas"
    mock_load_json.return_value = {
        "tables": {
            "Prestamos_Crudos": {
                "correo_usuario": {"regex": "^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$"}
            }
        }
    }

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mock_cursor.description = [("id",), ("correo_usuario",)]
    mock_cursor.fetchall.return_value = [
        (1, "test@test.com"),
        (2, "usuario_at_email.com"),   # Inválido — falla regex
        (3, "valido@correo.com"),
    ]

    report = validate_dirty_data(mock_conn, "dummy.json")

    assert report["total_records"] == 3
    assert report["invalid_records"] == 1


@patch("src.quality_validator.load_json")
def test_validate_dirty_data_no_rules(mock_load_json):
    """Valida el comportamiento si el json de reglas está vacío."""
    mock_load_json.return_value = {"tables": {}}

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    report = validate_dirty_data(mock_conn, "dummy.json")
    assert report["total_records"] == 0
    assert report["invalid_records"] == 0

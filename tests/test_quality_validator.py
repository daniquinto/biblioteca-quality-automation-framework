from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch
from src.quality_validator import validate_dirty_data, validate_sql_static, _validate_value, _is_date


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


def test_validate_value_required_field_empty():
    """Valida que detecta campos requeridos vacíos."""
    failures = _validate_value("Test", "col1", "", {"required": True})
    assert len(failures) == 1
    assert "valor obligatorio vacío" in failures[0]


def test_validate_value_required_field_none():
    """Valida que detecta campos requeridos con None."""
    failures = _validate_value("Test", "col1", None, {"required": True})
    assert len(failures) == 1


def test_validate_value_max_length():
    """Valida que detecta valores que exceden max_length."""
    failures = _validate_value("Test", "col1", "abcdef", {"max_length": 5})
    assert len(failures) == 1
    assert "longitud mayor a 5" in failures[0]


def test_validate_value_integer_type_valid():
    """Valida que acepta valores enteros válidos."""
    failures = _validate_value("Test", "col1", "123", {"type": "integer"})
    assert len(failures) == 0


def test_validate_value_integer_type_invalid():
    """Valida que rechaza valores no enteros."""
    failures = _validate_value("Test", "col1", "abc", {"type": "integer"})
    assert len(failures) == 1
    assert "debe ser entero" in failures[0]


def test_validate_value_date_type_valid():
    """Valida que acepta fechas válidas."""
    failures = _validate_value("Test", "col1", "2024-01-01", {"type": "date"})
    assert len(failures) == 0


def test_validate_value_date_type_invalid():
    """Valida que rechaza fechas inválidas."""
    failures = _validate_value("Test", "col1", "no-es-fecha", {"type": "date"})
    assert len(failures) == 1


def test_validate_value_min():
    """Valida que detecta valores menores que min."""
    failures = _validate_value("Test", "col1", "5", {"min": 10})
    assert len(failures) == 1
    assert "menor que 10" in failures[0]


def test_validate_value_max():
    """Valida que detecta valores mayores que max."""
    failures = _validate_value("Test", "col1", "15", {"max": 10})
    assert len(failures) == 1
    assert "mayor que 10" in failures[0]


def test_validate_value_allowed_values():
    """Valida que detecta valores no permitidos."""
    failures = _validate_value("Test", "col1", "INVALIDO", {"allowed_values": ["ACTIVO", "DEVUELTO"]})
    assert len(failures) == 1
    assert "valor no permitido" in failures[0]


def test_validate_value_must_contain():
    """Valida que detecta cuando falta contenido requerido."""
    failures = _validate_value("Test", "col1", "sin_separador", {"must_contain": "|"})
    assert len(failures) == 1
    assert "debe contener" in failures[0]


def test_validate_value_no_empty_items_csv():
    """Valida que detecta CSV con elementos vacíos."""
    failures = _validate_value("Test", "col1", "item1,,item3", {"no_empty_items_csv": True})
    assert len(failures) == 1
    assert "contiene elementos CSV vacíos" in failures[0]


def test_is_date_with_date_object():
    """Valida que reconoce objetos date."""
    result = _is_date(datetime(2024, 1, 1).date())
    assert result is True


def test_is_date_with_iso_string():
    """Valida que reconoce strings ISO format."""
    result = _is_date("2024-01-01")
    assert result is True


def test_is_date_with_invalid_string():
    """Valida que rechaza strings inválidos."""
    result = _is_date("no-es-fecha")
    assert result is False


def test_validate_sql_static_forbidden_keywords():
    """Valida que detecta palabras clave prohibidas."""
    with NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write("DROP DATABASE test_db;")
        f.flush()
        
        config = {
            "sql_static_rules": {
                "forbidden_keywords": ["DROP DATABASE", "TRUNCATE"],
                "avoid_text_fields": False,
                "require_primary_keys": False
            }
        }
        
        errors = validate_sql_static(Path(f.name), config)
        assert len(errors) > 0
        assert "palabra prohibida" in errors[0]
        
        Path(f.name).unlink()


def test_validate_sql_static_text_fields():
    """Valida que detecta uso de campos TEXT."""
    with NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write("CREATE TABLE test (col TEXT);")
        f.flush()
        
        config = {
            "sql_static_rules": {
                "forbidden_keywords": [],
                "avoid_text_fields": True,
                "require_primary_keys": False
            }
        }
        
        errors = validate_sql_static(Path(f.name), config)
        assert len(errors) > 0
        assert "TEXT" in errors[0]
        
        Path(f.name).unlink()


def test_validate_sql_static_require_primary_keys():
    """Valida que detecta ausencia de PRIMARY KEY."""
    with NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write("CREATE TABLE test (col VARCHAR(100));")
        f.flush()
        
        config = {
            "sql_static_rules": {
                "forbidden_keywords": [],
                "avoid_text_fields": False,
                "require_primary_keys": True
            }
        }
        
        errors = validate_sql_static(Path(f.name), config)
        assert len(errors) > 0
        assert "claves primarias" in errors[0]
        
        Path(f.name).unlink()

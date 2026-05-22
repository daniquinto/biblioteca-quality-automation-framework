"""
test_normalizer.py — Tests unitarios para normalizer.py y utils.py.
Cubre: _split_category, normalize_from_dirty (caminos feliz y excepción),
load_json, y el logger de utils.
"""
import json
import pytest
from unittest.mock import MagicMock
from src.normalizer import (
    normalize_from_dirty,
    _clean_text,
    _normalize_email,
    _normalize_loan_status,
    _split_category,
)
from src.utils import load_json, setup_logger, execute_sql_file


# ─── Tests de _split_category ─────────────────────────────────────────────────

def test_split_category_with_pipe():
    cat, desc = _split_category("Tecnología|Libros de programación")
    assert cat == "Tecnología"
    assert desc == "Libros de programación"


def test_split_category_without_pipe():
    cat, desc = _split_category("Ciencia")
    assert cat == "Ciencia"
    assert desc == "Sin descripción"


def test_split_category_none():
    cat, desc = _split_category(None)
    assert cat == "Sin categoría"
    assert desc == "Sin descripción"


def test_split_category_empty_string():
    cat, desc = _split_category("")
    assert cat == "Sin categoría"
    assert desc == "Sin descripción"


def test_split_category_multiple_pipes():
    cat, desc = _split_category("Novela|Drama|Clásico")
    assert cat == "Novela"
    assert desc == "Drama|Clásico"


@pytest.mark.parametrize(
    ("raw_status", "expected"),
    [
        ("Devuelto", "DEVUELTO"),
        ("  devuelto ", "DEVUELTO"),
        ("Pendiente", "ACTIVO"),
        ("PENDIENTE", "ACTIVO"),
        ("Atrasado", "VENCIDO"),
        ("   atrasado  \t", "VENCIDO"),
        (None, "ACTIVO"),
        ("Estado raro", "ACTIVO"),
    ],
)
def test_normalize_loan_status(raw_status, expected):
    assert _normalize_loan_status(raw_status) == expected


def test_clean_text_collapses_noise_and_title_cases():
    assert _clean_text("   GABRIEL GARCÍA MÁRQUEZ  \t ", title_case=True) == "Gabriel García Márquez"


def test_normalize_email_repairs_at_noise():
    assert _normalize_email("ana.mar_libros_at_email.com", "Ana Martínez") == "ana.mar_libros@email.com"


def test_normalize_email_uses_stable_name_fallback():
    assert _normalize_email(None, "María García") == "maria.garcia@sin-correo.local"


# ─── Tests de normalize_from_dirty ────────────────────────────────────────────

def _make_mock_conn(books=None, prestamos=None, inventario=None, resenas=None):
    """Construye una conexión mock con side_effects configurados."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur

    books = books or []
    prestamos = prestamos or []
    inventario = inventario or []
    resenas = resenas or []

    # fetchall: libros, prestamos, inventario, resenas
    cur.fetchall.side_effect = [books, prestamos, inventario, resenas]
    # fetchone para sp, usuarios, préstamos, sedes, libros
    cur.fetchone.return_value = (1,)
    return conn, cur


def test_normalize_from_dirty_empty_tables():
    """Con tablas vacías, stats deben ser todos cero."""
    conn, _ = _make_mock_conn()
    stats = normalize_from_dirty(conn)
    assert stats == {"books": 0, "users": 0, "loans": 0, "inventory": 0, "reviews": 0}


def test_normalize_from_dirty_books():
    """Un libro válido debe incrementar el contador."""
    conn, cur = _make_mock_conn(
        books=[("El Principito", "Saint-Exupéry", "Literatura|Novela corta", "Planeta", "1943-04-06")]
    )
    stats = normalize_from_dirty(conn)
    assert stats["books"] == 1
    # Debe haber llamado CALL sp_insertar_libro
    calls = [str(c) for c in cur.execute.call_args_list]
    assert any("sp_insertar_libro" in c for c in calls)


def test_normalize_from_dirty_user_invalid_email():
    """Correo malformado debe ser reemplazado por un correo de fallback."""
    conn, cur = _make_mock_conn(
        prestamos=[("Juan", "correo_malformado", "El Principito", "2024-01-01", "ACTIVO")]
    )
    stats = normalize_from_dirty(conn)
    assert stats["users"] == 1
    # El correo insertado debe usar fallback estable por nombre.
    calls = [str(c) for c in cur.execute.call_args_list]
    assert any("juan@sin-correo.local" in c for c in calls)


def test_normalize_from_dirty_inventory_text_quantity():
    """Cantidad textual 'Diez' debe coercionarse a 0."""
    conn, cur = _make_mock_conn(
        inventario=[("Sede 1", "Calle 1", "El Principito", "Diez")]
    )
    stats = normalize_from_dirty(conn)
    assert stats["inventory"] == 1


def test_normalize_from_dirty_inventory_negative_quantity():
    """Cantidad negativa debe coercionarse a 0."""
    conn, cur = _make_mock_conn(
        inventario=[("Sede 2", "Av. 45", "Cien años", "-5")]
    )
    stats = normalize_from_dirty(conn)
    assert stats["inventory"] == 1


def test_normalize_from_dirty_raises_on_db_error():
    """Un fallo en la conexión debe propagar la excepción."""
    conn = MagicMock()
    conn.cursor.side_effect = Exception("DB error")
    with pytest.raises(Exception, match="DB error"):
        normalize_from_dirty(conn)


# ─── Tests de utils ───────────────────────────────────────────────────────────

def test_load_json_valid(tmp_path):
    """load_json debe devolver el dict del archivo JSON."""
    data = {"key": "value", "number": 42}
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(data), encoding="utf-8")
    result = load_json(json_file)
    assert result == data


def test_load_json_file_not_found():
    """load_json debe lanzar FileNotFoundError si el archivo no existe."""
    with pytest.raises(FileNotFoundError):
        load_json("/ruta/que/no/existe/archivo.json")


def test_get_logger_returns_logger():
    """setup_logger debe retornar un objeto de logging."""
    import logging
    logger = setup_logger("test_logger")
    assert isinstance(logger, logging.Logger)


def test_execute_sql_file(tmp_path):
    """execute_sql_file debe leer el SQL y ejecutarlo en el cursor."""
    sql_file = tmp_path / "test.sql"
    sql_file.write_text("SELECT 1;", encoding="utf-8")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    execute_sql_file(mock_conn, sql_file)
    mock_cursor.execute.assert_called_once_with("SELECT 1;")

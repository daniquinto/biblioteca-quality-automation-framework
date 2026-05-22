import pytest
from unittest.mock import MagicMock, patch
from src.excel_loader import load_excel
from src.excel_exporter import export_normalized_to_excel


@patch("pathlib.Path.exists", return_value=True)
@patch("src.excel_loader.openpyxl")
def test_load_excel_success(mock_openpyxl, mock_exists):
    """Valida que los datos de Excel se inserten correctamente."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mock_wb = MagicMock()
    mock_openpyxl.load_workbook.return_value = mock_wb
    mock_wb.sheetnames = ["Biblioteca_Data"]

    mock_sheet = MagicMock()
    mock_wb.__getitem__.return_value = mock_sheet

    # values_only=True devuelve tuplas directamente
    mock_sheet.iter_rows.return_value = [
        ("titulo_libro", "autor_nombre", "categoria_y_descripcion", "editorial_info", "fecha_publicacion"),
        ("T1", "A1", "C1|D1", "E1", "2020-01-01"),
        ("T2", "A2", "C2|D2", "E2", "2021-05-10"),
    ]

    stats = load_excel(mock_conn, "dummy.xlsx")

    assert stats["Biblioteca_Data"] == 2
    assert mock_cursor.execute.call_count == 2


def test_load_excel_file_not_found():
    """Valida el manejo de error cuando el Excel no existe."""
    mock_conn = MagicMock()
    with pytest.raises(FileNotFoundError):
        load_excel(mock_conn, "/ruta/falsa/no_existe.xlsx")


@patch("src.excel_exporter.openpyxl")
def test_export_normalized_to_excel(mock_openpyxl):
    """Valida que la exportación genere el archivo Excel con las tablas correctas."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mock_cursor.description = [("col1",), ("col2",)]
    mock_cursor.fetchall.return_value = [(1, "A"), (2, "B")]

    mock_wb = MagicMock()
    mock_openpyxl.Workbook.return_value = mock_wb
    mock_ws = MagicMock()
    mock_wb.create_sheet.return_value = mock_ws

    out_path = export_normalized_to_excel(mock_conn, "out_dummy.xlsx")

    assert "out_dummy.xlsx" in out_path
    assert mock_wb.save.called
    assert mock_cursor.execute.call_count == 5  # 5 tablas/vistas

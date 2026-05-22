import pytest
from unittest.mock import MagicMock, patch
from src.excel_loader import load_excel

@patch('src.excel_loader.pd')
def test_load_excel_success(mock_pd):
    """Prueba que los datos de Excel se inserten correctamente."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Mock del DataFrame de pandas
    mock_df = MagicMock()
    mock_df.fillna.return_value = mock_df
    # Simulamos dos filas
    mock_df.itertuples.return_value = [
        MagicMock(Titulo="A", Autor="B", Categoria="C", Editorial="D", Publicacion="E"),
        MagicMock(Titulo="F", Autor="G", Categoria="H", Editorial="I", Publicacion="J")
    ]
    
    mock_pd.read_excel.return_value = mock_df

    stats = load_excel(mock_conn, "dummy.xlsx")

    assert stats["filas_procesadas"] == 2
    assert mock_cursor.execute.call_count == 2

@patch('src.excel_loader.pd')
def test_load_excel_file_not_found(mock_pd):
    """Valida el manejo de error cuando el Excel no existe."""
    mock_conn = MagicMock()
    mock_pd.read_excel.side_effect = FileNotFoundError("No such file")

    stats = load_excel(mock_conn, "dummy.xlsx")

    assert stats["filas_procesadas"] == 0
    assert "error" in stats

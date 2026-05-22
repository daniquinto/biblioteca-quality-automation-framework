"""
excel_exporter.py — Exportación de tablas normalizadas hacia Excel.

Propósito:
    Genera un informe final en formato .xlsx con las tablas clave normalizadas
    (libros, usuarios, prestamos, resenas, etc.), cumpliendo con el requerimiento
    del taller de entregar 'informe de la data a Excel ya normalizada'.
"""

import logging
from pathlib import Path
import openpyxl

logger = logging.getLogger(__name__)

def export_normalized_to_excel(conn, output_path: str | Path) -> str:
    """
    Exporta las principales vistas o tablas normalizadas a un archivo Excel.
    
    Args:
        conn: Conexión psycopg2 activa.
        output_path: Ruta de destino del archivo .xlsx.
        
    Returns:
        Ruta absoluta del archivo exportado.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    wb = openpyxl.Workbook()
    # Remover hoja por defecto
    default_sheet = wb.active
    if default_sheet:
        wb.remove(default_sheet)
        
    tablas_a_exportar = [
        "libros",
        "usuarios",
        "prestamos",
        "resenas",
        "vw_libros_mas_prestados" # Vista analítica importante
    ]
    
    with conn.cursor() as cur:
        for tabla in tablas_a_exportar:
            try:
                # Comprobar si existe y obtener datos
                cur.execute(f"SELECT * FROM {tabla}")
                filas = cur.fetchall()
                columnas = [desc[0] for desc in cur.description]
                
                # Crear hoja e insertar cabecera
                ws = wb.create_sheet(title=tabla[:31]) # Excel limita nombres a 31 chars
                ws.append(columnas)
                
                # Insertar filas
                for fila in filas:
                    ws.append(fila)
                    
                logger.info("Exportada tabla/vista '%s' con %d registros.", tabla, len(filas))
            except Exception as e:
                logger.warning("No se pudo exportar '%s': %s", tabla, e)
                conn.rollback() # Limpiar estado de transacción para continuar
                
    wb.save(str(path))
    wb.close()
    
    return str(path)

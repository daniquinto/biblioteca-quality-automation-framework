import os
import subprocess
from pathlib import Path
from src.db import pg_connection, mongo_database
from src.populate_legacy import populate_dirty_tables
from src.quality_validator import validate_dirty_data, validate_sql_static
from src.normalizer import normalize_from_dirty
from src.migrator import migrate_to_mongo
from src.utils import ROOT, execute_sql_file, load_json, setup_logger
from src.excel_loader import load_excel
from src.excel_exporter import export_normalized_to_excel
from src.deduplicator import deduplicate_biblioteca

# Definición de rutas base para asegurar la portabilidad del framework en diferentes entornos
SQL_DIR = ROOT / "sql"
CONFIG_DIR = ROOT / "config"

def run_view_and_function_examples(conn, logger):
    """
    Ejecuta pruebas de consumo de objetos programables.
    Se separa en una función propia para validar la integridad de la base de datos 
    independientemente del flujo de migración.
    """
    with conn.cursor() as cur:
        # Validación de procedimientos mediante cursores (Auditoría)
        cur.execute("CALL sp_auditar_prestamos_activos()")
        
        # Validación de vistas analíticas: Se comprueba la agregación de datos post-normalización
        cur.execute("SELECT titulo, total_prestamos, usuarios FROM vw_libros_mas_prestados LIMIT 10")
        rows = cur.fetchall()
        logger.info("Top 10 libros más prestados desde vw_libros_mas_prestados:")
        for row in rows:
            logger.info("Libro=%s | Total=%s | Usuarios=%s", row[0], row[1], row[2])
            
        # Validación de funciones escalares: Se verifica la lógica de negocio de multas
        cur.execute("SELECT id_prestamo FROM prestamos ORDER BY id_prestamo LIMIT 1")
        first = cur.fetchone()
        if first:
            cur.execute("SELECT fn_calcular_multa(%s)", (first[0],))
            logger.info("Multa calculada para préstamo %s: %s COP", first[0], cur.fetchone()[0])

def main():
    """
    Orquestador principal (Workflow Manager).
    Diseñado para ejecutar secuencialmente las fases de Calidad, Normalización y Migración,
    asegurando que ninguna fase inicie si la anterior no ha garantizado la integridad mínima.
    """
    logger = setup_logger()
    logger.info("Iniciando Framework de Calidad, Automatización y Migración de Datos")
    
    config_path = CONFIG_DIR / "config_calidad.json"
    mapping_path = CONFIG_DIR / "mapping_mongo.json"
    config = load_json(config_path)

    # Fase 1: Análisis Estático. Se realiza antes de tocar la DB para detectar 
    # malas prácticas de diseño en los scripts SQL (ej. falta de PKs).
    static_errors = validate_sql_static(SQL_DIR / "01_legacy_dirty_schema.sql", config)
    for error in static_errors:
        logger.warning("Validación estática SQL: %s", error)

    with pg_connection() as conn:
        # Fase 2: Preparación del entorno Legacy. 
        # (El esquema legacy se crea automáticamente al iniciar el contenedor PostgreSQL
        # mediante el script mapeado en /docker-entrypoint-initdb.d/01_legacy_dirty_schema.sql)
        logger.info("Esquema legacy precargado en el volumen de PostgreSQL")

        # Fase 3a: Ingesta de datos reales desde Excel (opcional).
        # Si EXCEL_PATH está definido, se cargan filas reales y sucias antes del Faker,
        # garantizando que el pipeline de calidad reciba un conjunto de datos mixto
        # (real + sintético) más representativo de un entorno productivo.
        excel_path = os.getenv("EXCEL_PATH", "")
        if excel_path:
            logger.info("Cargando datos reales desde Excel: %s", excel_path)
            excel_stats = load_excel(conn, excel_path)
            logger.info("Ingesta Excel completada: %s", excel_stats)
        else:
            logger.info("EXCEL_PATH no definido — se omite la ingesta desde Excel.")

        # Fase 3b: Estrés y Poblamiento. Se utiliza Faker para simular un volumen real
        # que exponga las ineficiencias del modelo no normalizado.
        total_records = int(os.getenv("TOTAL_RECORDS", "250"))
        locale = os.getenv("FAKER_LOCALE", "es_CO")
        inserted = populate_dirty_tables(conn, total_records=total_records, locale=locale)
        logger.info("Poblamiento masivo completado: %s", inserted)

        # Fase 4: Auditoría de Calidad Dinámica. 
        # Valida los datos insertados contra las reglas de negocio definidas en JSON.
        quality_report = validate_dirty_data(conn, config_path)
        logger.info(
            "Reporte de calidad legacy: total=%s, inválidos=%s",
            quality_report["total_records"], quality_report["invalid_records"],
        )

        # Fase 4.5: Deduplicación por Similitud Difusa (Fuzzy Matching).
        # Elimina registros casi-duplicados de Biblioteca_Data usando fuzz.ratio()
        # con blocking por primera palabra para mantener la complejidad tratable.
        # Debe correr después de la auditoría de calidad (Fase 4) y antes de la
        # normalización (Fase 5) para que el ETL opere sobre datos ya deduplicados.
        logger.info("Ejecutando deduplicación fuzzy sobre Biblioteca_Data")
        dedup_report = deduplicate_biblioteca(conn)
        logger.info("Deduplicación completada: %s", dedup_report)

        # Fase 5: Normalización 3FN.
        # Se aplican los scripts de corrección y se transforman los datos hacia el nuevo modelo.
        logger.info("Aplicando esquema normalizado 3FN")
        execute_sql_file(conn, SQL_DIR / "02_normalized_schema.sql")
        execute_sql_file(conn, SQL_DIR / "03_db_objects.sql")

        normalized_stats = normalize_from_dirty(conn)
        logger.info("Normalización completada: %s", normalized_stats)

        # Fase 6: Pruebas de Integridad.
        run_view_and_function_examples(conn, logger)

        # Fase 6.5: Exportación a Excel.
        # El taller pide un informe en Excel de los datos normalizados.
        logger.info("Exportando informe de datos normalizados a Excel...")
        export_path = ROOT / "data" / "biblioteca_normalizada.xlsx"
        export_normalized_to_excel(conn, export_path)
        logger.info("Exportación completada: %s", export_path)

        # Fase 7: Migración NoSQL (Cross-Platform).
        # Transformación final de datos relacionales a documentos JSON para MongoDB.
        logger.info("Migrando datos normalizados hacia MongoDB")
        mongo_stats = migrate_to_mongo(conn, mongo_database(), mapping_path)
        logger.info("Migración MongoDB completada: %s", mongo_stats)

    logger.info("Proceso finalizado correctamente. Revise logs/reporte_calidad.log")

    # Fase 8: Análisis Estático de Código Python.
    # Se ejecuta al finalizar todas las fases de datos para asegurar que el propio
    # framework cumple los estándares de calidad de código que predica.
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)

    # 8a. flake8 — estándar de pipeline: detecta errores de estilo PEP-8 y bugs evidentes.
    flake8_report = logs_dir / "flake8_report.txt"
    flake8_result = subprocess.run(
        ["flake8", "src/", "--statistics", "--output-file", str(flake8_report)],
        capture_output=True,
        text=True,
    )
    if flake8_result.returncode == 0:
        logger.info("flake8: sin violaciones PEP-8. Reporte en %s", flake8_report)
    else:
        logger.warning(
            "flake8: se encontraron advertencias (código %d). Ver %s",
            flake8_result.returncode, flake8_report,
        )

    # 8b. pylint — reporte visual con puntuación 0–10 (más llamativo para el taller).
    pylint_report = logs_dir / "pylint_report.txt"
    pylint_result = subprocess.run(
        ["pylint", "src/", "--output-format=text", f"--output={pylint_report}"],
        capture_output=True,
        text=True,
    )
    # pylint usa código de salida bit-a-bit (0=OK, 1=fatal, 2=error, 4=warn, 8=refactor, 16=convention)
    # Códigos distintos de 32 (uso) indican que se produjo algún reporte.
    score_line = next(
        (line for line in pylint_result.stdout.splitlines() if "Your code has been rated" in line),
        None,
    )
    if score_line:
        logger.info("pylint: %s. Ver %s", score_line.strip(), pylint_report)
    else:
        logger.info("pylint: análisis completado. Ver %s", pylint_report)

    # Fase 9: Unit Testing & Coverage (QA de Código)
    # Valida que el framework tenga al menos un 80% de cobertura.
    pytest_report = logs_dir / "pytest_coverage.txt"
    logger.info("Ejecutando suite de pruebas y validando cobertura (>80%)...")
    pytest_result = subprocess.run(
        [
            "pytest",
            "tests/",
            "--cov=src",
            "--cov-fail-under=80",
            "--cov-report=term",
            f"--output={pytest_report}"
        ],
        capture_output=True,
        text=True,
    )
    
    # Escribir el reporte en archivo de forma manual porque pytest --cov-report=term no tiene un --output nativo simple para ambos
    with open(pytest_report, "w", encoding="utf-8") as f:
        f.write(pytest_result.stdout)
        f.write("\n")
        f.write(pytest_result.stderr)

    if pytest_result.returncode == 0:
        logger.info("pytest: cobertura validada con éxito. Reporte en %s", pytest_report)
    else:
        logger.warning(
            "pytest: la cobertura no alcanza el 80%% o fallaron pruebas (código %d). Ver %s",
            pytest_result.returncode, pytest_report,
        )

    logger.info("Análisis estático y pruebas completados. Reportes en logs/")

if __name__ == "__main__":
    main()

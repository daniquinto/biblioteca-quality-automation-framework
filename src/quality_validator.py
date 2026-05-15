import re
from datetime import date, datetime
from pathlib import Path
from typing import Any
from .utils import load_json


def validate_sql_static(sql_path: Path, config: dict) -> list[str]:
    """
    Analizador estático de SQL para el aseguramiento de estándares de diseño.
    La validación previa a la ejecución previene la creación de deudas técnicas 
    y asegura que el esquema cumple con los requisitos de normalización y tipos de datos.
    """
    text = sql_path.read_text(encoding="utf-8")
    errors: list[str] = []
    rules = config.get("sql_static_rules", {})
    upper_text = text.upper()
    for keyword in rules.get("forbidden_keywords", []):
        if keyword.upper() in upper_text:
            errors.append(f"SQL contiene palabra prohibida: {keyword}")
    if rules.get("avoid_text_fields") and re.search(r"\bTEXT\b", upper_text):
        errors.append("SQL legacy usa campos TEXT; se recomienda VARCHAR con longitud controlada.")
    if rules.get("require_primary_keys") and "PRIMARY KEY" not in upper_text:
        errors.append("SQL no declara claves primarias.")
    return errors


def _is_date(value: Any) -> bool:
    if isinstance(value, date):
        return True
    try:
        datetime.fromisoformat(str(value))
        return True
    except ValueError:
        return False


def _validate_value(table: str, column: str, value: Any, rule: dict) -> list[str]:
    failures: list[str] = []
    if rule.get("required") and (value is None or str(value).strip() == ""):
        failures.append(f"{table}.{column}: valor obligatorio vacío")
        return failures
    if value is None:
        return failures
    value_str = str(value)
    if "max_length" in rule and len(value_str) > int(rule["max_length"]):
        failures.append(f"{table}.{column}: longitud mayor a {rule['max_length']}")
    if rule.get("type") == "integer":
        try:
            int(value)
        except (TypeError, ValueError):
            failures.append(f"{table}.{column}: debe ser entero")
    if rule.get("type") == "date" and not _is_date(value):
        failures.append(f"{table}.{column}: debe ser fecha válida")
    if "min" in rule:
        try:
            if int(value) < int(rule["min"]):
                failures.append(f"{table}.{column}: menor que {rule['min']}")
        except (TypeError, ValueError):
            failures.append(f"{table}.{column}: no permite validar mínimo")
    if "max" in rule:
        try:
            if int(value) > int(rule["max"]):
                failures.append(f"{table}.{column}: mayor que {rule['max']}")
        except (TypeError, ValueError):
            failures.append(f"{table}.{column}: no permite validar máximo")
    if "regex" in rule and not re.match(rule["regex"], value_str):
        failures.append(f"{table}.{column}: no cumple regex {rule['regex']}")
    if "allowed_values" in rule and value_str not in rule["allowed_values"]:
        failures.append(f"{table}.{column}: valor no permitido {value_str}")
    if "must_contain" in rule and rule["must_contain"] not in value_str:
        failures.append(f"{table}.{column}: debe contener '{rule['must_contain']}'")
    if rule.get("no_empty_items_csv"):
        items = [item.strip() for item in value_str.split(",")]
        if not items or any(not item for item in items):
            failures.append(f"{table}.{column}: contiene elementos CSV vacíos")
    return failures


def validate_dirty_data(conn, config_path: Path) -> dict:
    """
    Auditoría dinámica de integridad de datos crudos.
    La validación exhaustiva registro por registro identifica fallos de integridad 
    antes de proceder con los procesos de limpieza y normalización atómica.
    """
    config = load_json(config_path)
    report = {"total_records": 0, "invalid_records": 0, "errors": []}
    with conn.cursor() as cur:
        for table, columns in config["tables"].items():
            quoted_table = f'"{table}"'
            cur.execute(f"SELECT * FROM {quoted_table}")
            names = [desc[0] for desc in cur.description]
            for row in cur.fetchall():
                report["total_records"] += 1
                row_dict = dict(zip(names, row))
                row_errors: list[str] = []
                for column, rule in columns.items():
                    row_errors.extend(_validate_value(table, column, row_dict.get(column), rule))
                if row_errors:
                    report["invalid_records"] += 1
                    report["errors"].append({"table": table, "row": row_dict, "errors": row_errors})
    return report

from pathlib import Path
from src.quality_validator import validate_sql_static


def test_detects_text_fields(tmp_path: Path):
    sql = tmp_path / "schema.sql"
    sql.write_text("CREATE TABLE ejemplo(id INT PRIMARY KEY, descripcion TEXT);", encoding="utf-8")
    config = {"sql_static_rules": {"avoid_text_fields": True, "forbidden_keywords": [], "require_primary_keys": True}}
    errors = validate_sql_static(sql, config)
    assert any("TEXT" in error for error in errors)

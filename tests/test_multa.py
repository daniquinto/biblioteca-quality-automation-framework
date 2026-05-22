"""
test_multa.py — Test de integración Python vs PostgreSQL.

Objetivo del taller:
    Verificar que la lógica de negocio implementada en Python reproduce
    exactamente los resultados de fn_calcular_multa() en PostgreSQL,
    validando así la consistencia entre la capa de aplicación y la BD.

Fórmula de fn_calcular_multa (de 03_db_objects.sql):
    dias_retraso = max((fecha_devolucion ?? CURRENT_DATE) - fecha_salida - 15, 0)
    multa = dias_retraso * 1500

Requisito:
    La base de datos debe estar disponible con el esquema normalizado ya creado
    (main.py ejecutado al menos una vez). Si no está disponible, los tests se
    saltan con pytest.mark.skip para no bloquear el pipeline de CI.

Ejecución:
    pytest tests/test_multa.py -v
    pytest --cov=src --cov-report=term-missing tests/
"""

from __future__ import annotations

import os
import pytest
from datetime import date, timedelta

# ─── Fórmula Python (espejo exacto del SQL) ───────────────────────────────────

def calcular_multa_python(fecha_salida: date, fecha_devolucion: date | None = None) -> int:
    """
    Réplica Python de fn_calcular_multa de PostgreSQL.

    Lógica idéntica al SQL:
        v_dias_retraso := GREATEST(COALESCE(v_fecha_devolucion, CURRENT_DATE) - v_fecha_salida - 15, 0)
        RETURN v_dias_retraso * 1500

    Args:
        fecha_salida:      Fecha en que se realizó el préstamo.
        fecha_devolucion:  Fecha de devolución real; None simula un préstamo activo
                           (PostgreSQL usa CURRENT_DATE en ese caso).

    Returns:
        Multa en COP (pesos colombianos).
    """
    if fecha_salida is None:
        return 0
    fecha_final = fecha_devolucion if fecha_devolucion is not None else date.today()
    dias_retraso = max((fecha_final - fecha_salida).days - 15, 0)
    return dias_retraso * 1500


# ─── Tests puros de la fórmula Python (sin BD) ───────────────────────────────

class TestCalcularMultaPython:
    """Verifica la fórmula Python de forma aislada, sin conexión a Postgres."""

    def test_sin_retraso_exacto_15_dias(self):
        """Exactamente 15 días → sin multa."""
        salida = date(2024, 1, 1)
        devolucion = date(2024, 1, 16)  # 15 días exactos
        assert calcular_multa_python(salida, devolucion) == 0

    def test_sin_retraso_menos_de_15_dias(self):
        """10 días → sin multa."""
        salida = date(2024, 1, 1)
        devolucion = date(2024, 1, 11)
        assert calcular_multa_python(salida, devolucion) == 0

    def test_un_dia_de_retraso(self):
        """16 días → 1 día de mora → 1500 COP."""
        salida = date(2024, 1, 1)
        devolucion = date(2024, 1, 17)
        assert calcular_multa_python(salida, devolucion) == 1500

    def test_diez_dias_de_retraso(self):
        """25 días → 10 días de mora → 15000 COP."""
        salida = date(2024, 1, 1)
        devolucion = date(2024, 1, 26)
        assert calcular_multa_python(salida, devolucion) == 15_000

    def test_treinta_dias_de_retraso(self):
        """45 días → 30 días de mora → 45000 COP."""
        salida = date(2024, 3, 1)
        devolucion = date(2024, 4, 15)
        assert calcular_multa_python(salida, devolucion) == 45_000

    def test_fecha_salida_none_retorna_cero(self):
        """Si no hay fecha_salida el préstamo no existe → multa = 0."""
        assert calcular_multa_python(None) == 0

    def test_devolucion_none_usa_hoy(self):
        """
        Préstamo activo (sin fecha de devolución): Python debe usar date.today()
        igual que el COALESCE(..., CURRENT_DATE) de PostgreSQL.
        Si el préstamo fue hace más de 15 días, hay multa.
        """
        salida = date.today() - timedelta(days=20)
        multa = calcular_multa_python(salida, None)
        assert multa == 5 * 1500  # 20 - 15 = 5 días de mora


# ─── Tests de integración Python vs PostgreSQL ────────────────────────────────

# Saltar si no hay conexión configurada
_DB_AVAILABLE = bool(os.getenv("POSTGRES_HOST") or os.getenv("DATABASE_URL"))

@pytest.mark.skipif(
    not _DB_AVAILABLE,
    reason="POSTGRES_HOST no está configurado — test de integración omitido."
)
class TestMultaIntegracionPostgres:
    """
    Compara el resultado de calcular_multa_python() con fn_calcular_multa() de Postgres.
    Requiere que el esquema normalizado esté creado (main.py ejecutado previamente).
    """

    @pytest.fixture(autouse=True)
    def db_conn(self):
        """Fixture: abre una conexión real y hace rollback al finalizar el test."""
        from src.db import pg_connection
        with pg_connection() as conn:
            self.conn = conn
            yield conn
            conn.rollback()  # Nunca persistir datos de test

    def _insert_prestamo(self, fecha_salida: date, fecha_devolucion: date | None) -> int:
        """
        Inserta un préstamo mínimo de prueba con usuario y libro ficticios.
        Retorna el id_prestamo generado.
        """
        with self.conn.cursor() as cur:
            # Usuario de prueba
            cur.execute(
                "INSERT INTO usuarios(nombre, correo) VALUES (%s, %s) "
                "ON CONFLICT (correo) DO UPDATE SET nombre=EXCLUDED.nombre "
                "RETURNING id_usuario",
                ("Test User", "test.multa@test-framework.internal"),
            )
            user_id = cur.fetchone()[0]

            # Libro de prueba (categoría y editorial mínimas)
            cur.execute(
                "INSERT INTO categorias(nombre, descripcion) VALUES (%s, %s) "
                "ON CONFLICT (nombre) DO UPDATE SET nombre=EXCLUDED.nombre "
                "RETURNING id_categoria",
                ("Test Cat", "Categoría de prueba"),
            )
            cat_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO editoriales(nombre) VALUES (%s) "
                "ON CONFLICT (nombre) DO UPDATE SET nombre=EXCLUDED.nombre "
                "RETURNING id_editorial",
                ("Test Editorial",),
            )
            ed_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO libros(titulo, fecha_publicacion, id_categoria, id_editorial) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (titulo) DO UPDATE SET titulo=EXCLUDED.titulo "
                "RETURNING id_libro",
                ("Libro Test Multa", date(2000, 1, 1), cat_id, ed_id),
            )
            book_id = cur.fetchone()[0]

            # Préstamo de prueba
            cur.execute(
                "INSERT INTO prestamos(id_usuario, id_libro, fecha_salida, fecha_devolucion, estado) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id_prestamo",
                (user_id, book_id, fecha_salida, fecha_devolucion,
                 "DEVUELTO" if fecha_devolucion else "ACTIVO"),
            )
            return cur.fetchone()[0]

    def _multa_postgres(self, id_prestamo: int) -> int:
        with self.conn.cursor() as cur:
            cur.execute("SELECT fn_calcular_multa(%s)", (id_prestamo,))
            return int(cur.fetchone()[0])

    # ── Casos de prueba concretos ──────────────────────────────────────────

    def test_sin_retraso_python_equals_postgres(self):
        """15 días exactos: ambos deben retornar 0."""
        salida = date(2024, 6, 1)
        devolucion = date(2024, 6, 16)
        id_prestamo = self._insert_prestamo(salida, devolucion)

        python_result = calcular_multa_python(salida, devolucion)
        postgres_result = self._multa_postgres(id_prestamo)

        assert python_result == postgres_result == 0

    def test_un_dia_mora_python_equals_postgres(self):
        """16 días: ambos deben retornar 1500."""
        salida = date(2024, 6, 1)
        devolucion = date(2024, 6, 17)
        id_prestamo = self._insert_prestamo(salida, devolucion)

        python_result = calcular_multa_python(salida, devolucion)
        postgres_result = self._multa_postgres(id_prestamo)

        assert python_result == postgres_result
        assert python_result == 1500

    def test_diez_dias_mora_python_equals_postgres(self):
        """25 días: ambos deben retornar 15000."""
        salida = date(2024, 6, 1)
        devolucion = date(2024, 6, 26)
        id_prestamo = self._insert_prestamo(salida, devolucion)

        python_result = calcular_multa_python(salida, devolucion)
        postgres_result = self._multa_postgres(id_prestamo)

        assert python_result == postgres_result
        assert python_result == 15_000

    def test_prestamo_activo_python_equals_postgres(self):
        """
        Préstamo activo (sin fecha devolución): ambos usan CURRENT_DATE/date.today().
        Puede haber diferencia de ±1 día si el test corre justo en medianoche,
        pero en condiciones normales deben coincidir exactamente.
        """
        salida = date.today() - timedelta(days=20)
        id_prestamo = self._insert_prestamo(salida, None)

        python_result = calcular_multa_python(salida, None)
        postgres_result = self._multa_postgres(id_prestamo)

        # Tolerancia de ±1500 COP (diferencia de 1 día en edge case de medianoche)
        assert abs(python_result - postgres_result) <= 1500, (
            f"Python={python_result} COP vs Postgres={postgres_result} COP — "
            f"diferencia mayor a 1 día de mora"
        )

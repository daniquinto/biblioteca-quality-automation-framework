"""
deduplicator.py — Deduplicación por similitud difusa sobre la tabla legacy Biblioteca_Data.

Propósito:
    Identificar y eliminar registros duplicados o casi-duplicados generados por errores
    de digitación, variaciones de formato o ingesta redundante de datos (Excel + Faker).
    Opera directamente sobre los datos sucios *antes* de la normalización, garantizando
    que el pipeline ETL reciba un conjunto de datos lo más limpio posible a nivel de
    identidad de entidades.

Estrategia de optimización — Blocking por primera palabra:
    La comparación ingenua entre N registros requiere N*(N-1)/2 operaciones (O(n²)).
    Para 500 registros eso son 124.750 pares; para 2.000 son casi 2 millones.
    
    Solución: agrupar los registros en "bloques" por la primera palabra normalizada
    del título (ej. "cien", "don", "el", "la"…) y comparar únicamente dentro de cada
    bloque. Títulos genuinamente distintos rara vez comparten la misma primera palabra,
    por lo que la tasa de falsos negativos es muy baja y la reducción de comparaciones
    es drástica (típicamente 95-99 % menos pares).

    Complejidad efectiva: O(B · (n/B)²) = O(n²/B), donde B = número de bloques.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import defaultdict
from itertools import combinations

from thefuzz import fuzz

logger = logging.getLogger(__name__)

# Umbral de similitud a partir del cual dos registros se consideran duplicados.
# 85 % ofrece un balance entre precisión y recall para títulos de libros.
SIMILARITY_THRESHOLD = 85

# ─────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_text(text: str | None) -> str:
    """
    Normalización ligera para maximizar la efectividad del ratio de similitud:
      1. Convierte a minúsculas.
      2. Elimina acentos y diacríticos (NFD → ASCII).
      3. Colapsa espacios múltiples.
    No elimina stopwords intencionalmente: queremos que "El Quijote" y
    "La Quijote" sean distinguibles.
    """
    if not text:
        return ""
    # Eliminar diacríticos
    nfd = unicodedata.normalize("NFD", text)
    ascii_text = nfd.encode("ascii", "ignore").decode("ascii")
    # Minúsculas y espacios limpios
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def _blocking_key(title: str) -> str:
    """
    Extrae la clave de bloque: primera palabra significativa del título normalizado.
    Títulos vacíos o de una sola palabra van al bloque especial '__single__'.
    """
    normalized = _normalize_text(title)
    words = normalized.split()
    return words[0] if words else "__empty__"


def _similarity(r1: tuple, r2: tuple) -> int:
    """
    Calcula la similitud entre dos registros usando una cadena compuesta:
    'titulo || autor'. Combinar ambos campos reduce los falsos positivos
    cuando dos libros distintos tienen títulos similares pero autores diferentes.

    Args:
        r1, r2: tuplas (id_registro, titulo_libro, autor_nombre)

    Returns:
        Porcentaje de similitud 0–100.
    """
    _, title1, author1 = r1
    _, title2, author2 = r2
    key1 = f"{_normalize_text(title1)} {_normalize_text(author1)}"
    key2 = f"{_normalize_text(title2)} {_normalize_text(author2)}"
    return fuzz.ratio(key1, key2)


# ─────────────────────────────────────────────────────────────────────────────
# Función principal
# ─────────────────────────────────────────────────────────────────────────────

def deduplicate_biblioteca(conn, threshold: int = SIMILARITY_THRESHOLD) -> dict:
    """
    Detecta y elimina duplicados fuzzy en la tabla legacy ``Biblioteca_Data``.

    Algoritmo:
        1. Carga todos los registros (id, título, autor) desde Postgres.
        2. Agrupa los registros en bloques por la primera palabra del título
           (técnica de *blocking*) para evitar la comparación O(n²) global.
        3. Dentro de cada bloque, evalúa todos los pares con ``fuzz.ratio()``.
        4. Para cada par con similitud ≥ ``threshold``:
           - El registro con el menor ``id_registro`` se designa Registro Maestro.
           - El duplicado (id mayor) se elimina de la tabla.
           - Se evita procesar IDs ya eliminados para no generar eliminaciones
             en cascada ni errores de integridad.
        5. Retorna un reporte con las métricas del proceso.

    Args:
        conn:      Conexión psycopg2 activa.
        threshold: Porcentaje mínimo de similitud para considerar duplicado (0–100).

    Returns:
        ``{"duplicados_encontrados": N, "registros_eliminados": N, "bloques_procesados": B}``
    """
    stats = {"duplicados_encontrados": 0, "registros_eliminados": 0, "bloques_procesados": 0}

    with conn.cursor() as cur:
        # 1. Cargar todos los registros de la tabla legacy
        cur.execute(
            'SELECT id_registro, titulo_libro, autor_nombre FROM "Biblioteca_Data" ORDER BY id_registro'
        )
        records: list[tuple] = cur.fetchall()

    if len(records) < 2:
        logger.info("Deduplicador: menos de 2 registros — no hay pares que comparar.")
        return stats

    logger.info("Deduplicador: %d registros cargados. Construyendo bloques…", len(records))

    # 2. Agrupar en bloques por primera palabra del título (blocking)
    blocks: dict[str, list[tuple]] = defaultdict(list)
    for record in records:
        key = _blocking_key(record[1])  # record[1] = titulo_libro
        blocks[key].append(record)

    logger.info(
        "Deduplicador: %d bloques generados (promedio %.1f registros/bloque).",
        len(blocks), len(records) / len(blocks),
    )

    # Conjunto de IDs ya marcados para eliminar — evita procesarlos dos veces
    ids_to_delete: set[int] = set()
    duplicates_found = 0

    # 3. Comparar pares dentro de cada bloque
    with conn.cursor() as cur:
        for block_key, block_records in blocks.items():
            stats["bloques_procesados"] += 1

            if len(block_records) < 2:
                continue  # Bloques de un solo elemento no tienen pares

            for r1, r2 in combinations(block_records, 2):
                id1, id2 = r1[0], r2[0]

                # Saltar si alguno ya fue eliminado en esta sesión
                if id1 in ids_to_delete or id2 in ids_to_delete:
                    continue

                sim = _similarity(r1, r2)

                if sim >= threshold:
                    duplicates_found += 1
                    # 4. El id menor es el Registro Maestro; el id mayor se elimina
                    duplicate_id = max(id1, id2)

                    logger.debug(
                        "Duplicado detectado (sim=%d%%): id=%d '%s' ≈ id=%d '%s' → eliminando id=%d",
                        sim, id1, r1[1], id2, r2[1], duplicate_id,
                    )

                    cur.execute(
                        'DELETE FROM "Biblioteca_Data" WHERE id_registro = %s',
                        (duplicate_id,),
                    )
                    ids_to_delete.add(duplicate_id)

    stats["duplicados_encontrados"] = duplicates_found
    stats["registros_eliminados"] = len(ids_to_delete)

    logger.info(
        "Deduplicación completada: %d pares duplicados, %d registros eliminados en %d bloques.",
        stats["duplicados_encontrados"],
        stats["registros_eliminados"],
        stats["bloques_procesados"],
    )
    return stats

# Biblioteca Quality Automation Framework

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-7-47A248?logo=mongodb&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Coverage](https://img.shields.io/badge/Coverage-82%25-brightgreen)
![Flake8](https://img.shields.io/badge/Flake8-0%20errors-brightgreen)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)

> **Framework de Ingeniería de Datos** para la migración, limpieza, normalización y aseguramiento de calidad de la *Biblioteca Central Universitaria*. Implementa un pipeline ETL completo con pruebas unitarias automatizadas, análisis estático de código y despliegue en contenedores Docker.

---

## Tabla de Contenidos

1. [Arquitectura y Visión General](#1-arquitectura-y-visión-general)
2. [Tecnologías](#2-tecnologías)
3. [Estructura del Proyecto](#3-estructura-del-proyecto)
4. [Pipeline ETL — 9 Fases](#4-pipeline-etl--9-fases)
5. [Ejecución con Docker](#5-ejecución-con-docker)
6. [CI/CD con GitHub Actions](#6-cicd-con-github-actions)
7. [Salidas y Evidencias](#7-salidas-y-evidencias)
8. [Decisiones de Ingeniería](#8-decisiones-de-ingeniería)

---

## 1. Arquitectura y Visión General

El sistema resuelve un escenario real de deuda técnica: una base de datos *Legacy* plana (violaciones 1FN, tipos inconsistentes, PII en texto claro, duplicados) que debe ser transformada en un modelo **Relacional Normalizado (3FN)** en PostgreSQL y replicada como modelo documental en **MongoDB**.

```
┌─────────────────────────────────────────────────────────────────┐
│                     biblioteca_app (Python)                      │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │  Ingest  │→ │ Dedup    │→ │Normalize │→ │    Export      │  │
│  │  Excel   │  │  Fuzzy   │  │  3FN     │  │  Excel + Mongo │  │
│  │  +Faker  │  │ Matching │  │  SQL     │  │  + PII Masking │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │       QA Pipeline: flake8 · pylint · pytest --cov=80%   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────┬──────────────────┬───────────────────────────────┘
               ▼                  ▼
        PostgreSQL 16         MongoDB 7
        (Schema 3FN)       (Documentos NoSQL)
```

---

## 2. Tecnologías

| Categoría | Herramienta | Versión |
|---|---|---|
| Lenguaje | Python | 3.12 |
| Base de Datos Relacional | PostgreSQL | 16 |
| Base de Datos Documental | MongoDB | 7 |
| Orquestación | Docker Compose | v2 |
| Driver PostgreSQL | psycopg2-binary | latest |
| Driver MongoDB | pymongo | latest |
| Datos Sintéticos | Faker | latest |
| Excel I/O | openpyxl | latest |
| Deduplicación | thefuzz + python-Levenshtein | latest |
| Testing | pytest + pytest-cov | latest |
| Análisis Estático | flake8 + pylint | latest |
| CI/CD | GitHub Actions | — |

---

## 3. Estructura del Proyecto

```text
biblioteca_quality_framework/
│
├── .github/
│   └── workflows/
│       └── ci.yml               # Pipeline CI: Flake8 + Pytest >80% cov
│
├── config/
│   ├── config_calidad.json      # Reglas de validación de datos (tablas, columnas, regex)
│   └── mapping_mongo.json       # Mapeo de colecciones Relacional → NoSQL
│
├── data/
│   └── Gestion_Biblioteca_Datos_Sucios_Para_Limpiar.xlsx  # Fuente real por defecto
│
├── logs/
│   ├── reporte_calidad.log      # Log transaccional del pipeline
│   ├── flake8_report.txt        # Reporte de análisis de estilo
│   ├── pylint_report.txt        # Reporte de análisis de calidad
│   └── pytest_coverage.txt      # Evidencia de cobertura >80%
│
├── sql/
│   ├── 01_legacy_dirty_schema.sql   # Esquema plano legacy (cargado por Docker init)
│   ├── 02_normalized_schema.sql     # Modelo 3FN destino
│   └── 03_db_objects.sql            # Stored Procedures, Views, fn_calcular_multa()
│
├── src/
│   ├── __init__.py
│   ├── db.py                    # Context managers: pg_connection(), mongo_database()
│   ├── deduplicator.py          # Fuzzy Matching con Blocking por primera palabra
│   ├── excel_exporter.py        # Generador del informe final Excel (openpyxl)
│   ├── excel_loader.py          # Ingesta de datos legacy desde .xlsx
│   ├── migrator.py              # Migración a MongoDB con PII Masking (SHA-256)
│   ├── normalizer.py            # Coerción de tipos y normalización 1FN → 3FN
│   ├── populate_legacy.py       # Inyección de datos caóticos con Faker
│   ├── quality_validator.py     # Motor de validación dinámica de reglas JSON
│   └── utils.py                 # Logger, load_json(), execute_sql_file()
│
├── tests/
│   ├── test_db.py               # Context managers con mocks de psycopg2/pymongo
│   ├── test_deduplicator.py     # Algoritmo Fuzzy: duplicados, distintos, cascada
│   ├── test_excel.py            # Ingest y Export Excel con mocks de openpyxl
│   ├── test_masking.py          # PII Masking: correos válidos, nulos, borde
│   ├── test_migrator_mongo.py   # Migración NoSQL con colecciones separadas
│   ├── test_multa.py            # Fórmula Python vs fn_calcular_multa() (PostgreSQL)
│   ├── test_normalizer.py       # _split_category, normalize_from_dirty, utils
│   ├── test_populate.py         # Generación de datos caóticos con Faker
│   └── test_quality_validator.py # Motor de reglas JSON con mocks de cursor
│
├── .env                         # Variables de entorno (no versionado en producción)
├── .flake8                      # Configuración: max-line-length=120
├── Dockerfile                   # Imagen Python 3.12-slim
├── docker-compose.yml           # Servicios: postgres, mongo, app (con healthchecks)
├── pytest.ini                   # pythonpath=. para resolución de módulo src/
├── requirements.txt             # Dependencias del proyecto
└── README.md
```

---

## 4. Pipeline ETL — 9 Fases

El orquestador `main.py` ejecuta las siguientes fases de forma secuencial e idempotente:

| Fase | Descripción | Módulo |
|:---:|---|---|
| **1** | Inicialización del esquema *Legacy* vía volumen Docker | `sql/01_legacy_dirty_schema.sql` |
| **2** | Ingesta de datos reales desde `data/Gestion_Biblioteca_Datos_Sucios_Para_Limpiar.xlsx` | `excel_loader.py` |
| **3** | Generación opcional de datos sintéticos con Faker (`TOTAL_RECORDS>0`) | `populate_legacy.py` |
| **4** | Auditoría de calidad de datos crudos contra reglas JSON | `quality_validator.py` |
| **5** | Deduplicación por similitud difusa (Fuzzy Matching ≥85%) | `deduplicator.py` |
| **6** | Normalización 3FN: coerción de tipos, Stored Procedures | `normalizer.py` |
| **6.5** | Ejecución de objetos SQL: Views, Funciones de negocio | `sql/03_db_objects.sql` |
| **7** | Exportación del informe final normalizado a Excel | `excel_exporter.py` |
| **8** | Migración a MongoDB con enmascaramiento PII (SHA-256) | `migrator.py` |
| **9** | QA automatizado: flake8 + pylint + pytest --cov-fail-under=80 | CI Pipeline |

---

## 5. Ejecución con Docker

### Requisitos previos
- Docker Engine ≥ 24.0
- Docker Compose v2

### Iniciar el stack completo

```bash
# Derribar entornos anteriores y levantar desde cero (limpio)
docker compose down -v
docker compose up --build
```

Docker Compose orquestará automáticamente:
1. **PostgreSQL 16**: Carga el esquema *Legacy* en `/docker-entrypoint-initdb.d/`
2. **MongoDB 7**: Levanta con autenticación configurada vía `.env`
3. **App Python**: Espera los *healthchecks* de ambas DB y luego ejecuta `main.py`

### Monitorear el progreso en tiempo real

```bash
docker compose logs -f app
```

### Acceso a las bases de datos

```bash
# PostgreSQL — psql interactivo
docker compose exec postgres psql -U biblioteca_user -d biblioteca_db

# MongoDB — mongosh interactivo
docker compose exec mongo mongosh -u biblioteca_user -p biblioteca_pass --authenticationDatabase admin
```

---

## 6. CI/CD con GitHub Actions

Cada `push` o `pull_request` a la rama `main` dispara automáticamente el pipeline definido en `.github/workflows/ci.yml`:

```
push → Checkout → Python 3.12 → pip install → Flake8 → Pytest (>80% cov)
```

### Etapas del pipeline

| Etapa | Comando | Criterio de éxito |
|---|---|---|
| Análisis de Estilo | `flake8 src/ tests/` | 0 errores |
| Pruebas Unitarias | `pytest tests/ --cov=src --cov-fail-under=80` | 62 passed, cobertura ≥80% |

> **Nota:** Los tests de integración (`TestMultaIntegracionPostgres`) se saltan automáticamente en CI cuando `POSTGRES_HOST` no está configurado, sin bloquear el pipeline.

### Estado actual del pipeline

```
✅ Flake8       — 0 errores
✅ Pytest       — 62 passed, 4 skipped (integración DB)
✅ Coverage     — 82% (umbral: 80%)
```

---

## 7. Salidas y Evidencias

Al finalizar exitosamente, el pipeline genera los siguientes artefactos:

### Bases de Datos
| Motor | Puerto | Contenido |
|---|---|---|
| PostgreSQL | `5432` | Esquema 3FN con libros, autores, usuarios, préstamos, inventario, reseñas |
| MongoDB | `27017` | Colecciones: `books`, `users` (email enmascarado), `loans`, `inventory` |

### Archivos generados

```
data/
└── biblioteca_normalizada.xlsx    # Reporte con 5 pestañas:
                                   #   libros | usuarios | prestamos
                                   #   resenas | vw_libros_mas_prestados

logs/
├── reporte_calidad.log            # Traza completa del pipeline
├── flake8_report.txt              # Análisis de estilo
├── pylint_report.txt              # Score de calidad (target: ≥8/10)
└── pytest_coverage.txt            # Evidencia de cobertura ≥80%
```

---

## 8. Decisiones de Ingeniería

### Fuzzy Matching con Blocking
La comparación ingenua entre N registros requiere O(n²) operaciones. Se implementa una técnica de *Blocking* que agrupa los registros por la primera palabra del título, reduciendo las comparaciones en un **95-99%** mientras mantiene una tasa de falsos negativos mínima.

### Coerción Robusta de Tipos
El pipeline usa `try/except` nativos de Python para manejar entradas caóticas (fechas en formato `DD/MM/YYYY`, cantidades como `"Diez"` o `"-5"`, correos malformados), equivalente al patrón `errors='coerce'` de Pandas pero sin dependencias externas pesadas.

### PII Masking por capas
Se implementa el principio de **minimización de datos** en dos niveles:
- **Opción A (activa):** Máscara parcial `j***n@correo.com` — preserva trazabilidad para entornos de demo.
- **Opción B (comentada):** Hash SHA-256 irreversible — apto para producción real.

### Transaccionalidad ACID
Los *context managers* (`with conn.cursor() as cur`) garantizan que ante cualquier fallo en una fase, la base de datos revierta a su último estado consistente mediante `conn.rollback()` automático.

### Idempotencia
Todos los `INSERT` usan `ON CONFLICT DO UPDATE/DO NOTHING`, permitiendo ejecutar el pipeline múltiples veces sobre el mismo entorno sin duplicar datos ni lanzar errores.

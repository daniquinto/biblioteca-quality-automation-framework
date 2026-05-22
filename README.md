# Framework de Calidad, Automatización y Migración de Datos - Biblioteca Central

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![MongoDB](https://img.shields.io/badge/MongoDB-7-green?logo=mongodb)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![Coverage](https://img.shields.io/badge/Coverage-%3E80%25-brightgreen)
![Quality](https://img.shields.io/badge/Quality-Pylint%20%7C%20Flake8-blueviolet)

## 1. Arquitectura y Visión General

Este proyecto de Ingeniería de Datos automatiza la extracción, limpieza, normalización y migración de datos para la **Biblioteca Central**. Resuelve un ecosistema *Legacy* con violaciones graves de diseño de datos (1FN) y anomalías caóticas, llevándolo hacia un entorno **Relacional Normalizado (3FN)** en PostgreSQL, y exportando modelos documentales hacia **MongoDB**.

Todo el ciclo está orquestado desde un contenedor Docker (App-Python) que interactúa con las bases de datos de forma autónoma.

### Flujo del ETL (Pipeline)
1. **Inicialización DB:** PostgreSQL levanta el esquema *Legacy* (tablas planas sin integridad).
2. **Ingesta de Datos:** Carga registros reales desde archivos `.xlsx` y genera un volumen de datos sintéticos caóticos (anomalías explícitas, valores nulos, PII en texto claro) usando Faker.
3. **Auditoría de Calidad:** Valida las reglas de negocio declaradas en `config_calidad.json`.
4. **Deduplicación Difusa (Fuzzy Matching):** Limpia duplicados en las tablas planas comparando strings con métricas de distancia (`thefuzz`) antes de normalizar.
5. **Normalización (3FN):** Separa las tablas en un modelo robusto y transfiere los datos sanos coercing tipos.
6. **Ejecución Lógica de Negocio:** Ejecuta Stored Procedures, Views (ej. top libros), y funciones en PostgreSQL (ej. cálculo de multas).
7. **Exportación a Excel:** Genera el reporte final (`data/biblioteca_normalizada.xlsx`) con las tablas limpias.
8. **Migración a MongoDB (Cross-Platform):** Transfiere documentos aplicando **Data Masking** (SHA/Máscara parcial) a información sensible (PII).
9. **QA Code Pipeline:** Corre análisis estático (`flake8`, `pylint`) y pruebas unitarias (`pytest --cov-fail-under=80`).

---

## 2. Tecnologías y Librerías

- **Orquestación:** Docker Compose.
- **Python Drivers:** `psycopg2-binary` (PostgreSQL), `pymongo` (MongoDB).
- **Procesamiento de Datos:** `openpyxl` (Excel Ingest/Export), `Faker` (Synthetic Data).
- **Limpieza de Datos:** `thefuzz`, `python-Levenshtein` (Fuzzy Matching).
- **QA y Pruebas:** `pytest`, `pytest-cov`, `flake8`, `pylint`, `unittest.mock`.

---

## 3. Estructura del Proyecto

```text
biblioteca_quality_framework/
├── main.py                  # Orquestador del Pipeline (9 Fases)
├── requirements.txt         # Dependencias
├── Dockerfile               # Construcción de la imagen Python App
├── docker-compose.yml       # Levantamiento de infraestructura
├── .env                     # Variables de entorno
├── config/
│   ├── config_calidad.json  # Reglas dinámicas de QA de datos
│   └── mapping_mongo.json   # Reglas de Mapeo Relacional -> NoSQL
├── data/                    # Entrada/Salida de archivos (.xlsx)
├── sql/
│   ├── 01_legacy_dirty_schema.sql  # Auto-ejecutado por Postgres init
│   ├── 02_normalized_schema.sql    # Esquema 3FN
│   └── 03_db_objects.sql           # Vistas, Funciones, y Cursores
├── src/
│   ├── db.py                # Context managers de conexiones DB
│   ├── deduplicator.py      # Fuzzy matching y consolidación
│   ├── excel_exporter.py    # Generador del informe final Excel
│   ├── excel_loader.py      # Lector de datos Legacy
│   ├── migrator.py          # Data Masking & Migración MongoDB
│   ├── normalizer.py        # Limpieza y coerción (Regex, Dates)
│   ├── populate_legacy.py   # Inyección de caos e irregularidades
│   ├── quality_validator.py # Motor validador de integridad
│   └── utils.py             # Funciones de parseo y logger
├── tests/                   # Suite de Pruebas Unitarias (>80% Cov)
└── logs/                    # Artefactos: reportes Pylint, Pytest, Flake8
```

---

## 4. Ejecución del Proyecto (Docker)

El proyecto está diseñado para correr al "Push of a button".

### Requisitos
- Docker y Docker Compose instalados.

### Instrucciones
1. Clona el repositorio y ubícate en la raíz.
2. (Opcional) Crea/deposita tu archivo excel `biblioteca.xlsx` en la carpeta `/data` si deseas probar con datos reales, y ajusta `.env`.
3. Levanta la infraestructura:

```bash
docker compose up --build
```

El orquestador de Docker:
- Descargará las imágenes de PostgreSQL 16 y MongoDB 7.
- Inicializará las bases de datos montando el script legacy en `/docker-entrypoint-initdb.d/`.
- Compilará la imagen de la aplicación en Python (`biblioteca_app`).
- Esperará a que los *healthchecks* de las bases de datos sean positivos.
- Lanzará todo el pipeline en `main.py`.

Para ver únicamente los logs de la aplicación Python y seguir el progreso:
```bash
docker compose logs -f app
```

---

## 5. Salidas y Evidencias (Entregables)

Al finalizar exitosamente, el contenedor emitirá resultados en múltiples formatos:

1. **Bases de Datos Vivas:** 
   - PostgreSQL accesible en puerto `5432` con esquema 3FN poblado.
   - MongoDB accesible en puerto `27017` con documentos migrados.
2. **Reporte Excel:**
   - En la ruta `data/biblioteca_normalizada.xlsx` estarán las tablas estructuradas (Libros, Préstamos, Reseñas, Usuarios y Vista Analítica).
3. **Logs y QA:**
   - En la ruta `logs/` se encuentran:
     - `reporte_calidad.log`: Log general de la transacción.
     - `flake8_report.txt` y `pylint_report.txt`: Resultados del análisis estático de código.
     - `pytest_coverage.txt`: Evidencia de que las pruebas unitarias superaron la valla del 80%.

---

## 6. Detalles Avanzados de Ingeniería

- **Seguridad por Diseño (Data Masking):** Se aplica la función `_mask_email()` en la capa de migración a Mongo. Correos como `juan@example.com` llegan como hashes SHA-256 o en formato `j****n@example.com` al entorno NoSQL.
- **Fuzzy Matching con Blocking:** Para evitar que la deduplicación crezca a *O(n²)* en tiempo de procesamiento, la técnica agrupa strings por la primera palabra clave, realizando comparaciones efectivas (distancia de Levenshtein) y tomando decisiones inteligentes sobre el "Registro Maestro".
- **Coerción Robusta de Datos:** El framework previene *crashes* en SQL usando `try/except` envolventes (simulando `.to_numeric(errors='coerce')` de Pandas) y `datetime.strptime` nativos en Python.
- **Transaccionalidad (ACID):** El uso de *Context Managers* en Python asegura que ante cualquier fallo fatal, el estado de la base de datos revierta a su último punto limpio (`conn.rollback()`).

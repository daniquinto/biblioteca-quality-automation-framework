# DOCUMENTACIÓN TÉCNICA — BIBLIOTECA QUALITY AUTOMATION FRAMEWORK

**Versión:** 2.0.0  
**Fecha:** Mayo 2026  
**Autor:** Equipo de Ingeniería de Datos — UNISABANETA  
**Clasificación:** Documentación Técnica Profesional

---

## TABLA DE CONTENIDOS

1. [Introducción Ejecutiva](#1-introducción-ejecutiva)
2. [Visión Arquitectónica](#2-visión-arquitectónica)
3. [Tecnologías y Stack](#3-tecnologías-y-stack)
4. [Estructura del Proyecto](#4-estructura-del-proyecto)
5. [Pipeline ETL — Fases de Implementación](#5-pipeline-etl--fases-de-implementación)
6. [Infraestructura: Docker Compose](#6-infraestructura-docker-compose)
7. [CI/CD Pipeline: GitHub Actions](#7-cicd-pipeline-github-actions)
8. [Implementación Técnica Detallada](#8-implementación-técnica-detallada)
9. [Aseguramiento de Calidad](#9-aseguramiento-de-calidad)
10. [Decisiones de Ingeniería](#10-decisiones-de-ingeniería)
11. [Guía de Operación](#11-guía-de-operación)

---

## 1. INTRODUCCIÓN EJECUTIVA

### Propósito del Proyecto

El **Biblioteca Quality Automation Framework** es una solución empresarial de ingeniería de datos diseñada para resolver un escenario real de **deuda técnica organizacional**. El proyecto aborda la migración, limpieza, normalización y aseguramiento de calidad de una base de datos legacy plana hacia un modelo relacional normalizado (3FN) con replicación documental en MongoDB.

### Desafío Original

- **Base de datos legacy:** Modelo plano violando 1FN (primera forma normal)
- **Datos sucios:** Inconsistencias de tipo, duplicados fuzzy, PII en texto claro
- **Falta de automatización:** Procesos manuales sin validación ni auditoría
- **Ausencia de trazabilidad:** Imposibilidad de rastrear cambios o anomalías

### Solución Implementada

Un **pipeline ETL automatizado** de 9 fases que:

 Ingesta datos reales (Excel) + sintéticos (Faker)  
 Deduplica registros con matching fuzzy (thefuzz)  
 Normaliza a 3FN con integridad referencial  
 Valida calidad de datos contra reglas configurables  
 Enmascara datos sensibles (PII masking)  
 Exporta a múltiples formatos (Excel, MongoDB)  
 Genera reportes de auditoría (logs, cobertura de tests)  
 Se ejecuta en contenedores (Docker Compose)  
 Integración continua automatizada (GitHub Actions)

---

## 2. VISIÓN ARQUITECTÓNICA

### Diagrama de Flujo General

```

                   CLIENTE: Excel Datos Sucios                          
                   + Faker Generador Sintético                          

                           
                           

                    FASE 1: INGESTA (LOADING)                           
  • Lectura de Excel (excel_loader.py)                                 
  • Mapeo dinámico de columnas por hoja                                
  • Inserción en tablas legacy (Biblioteca_Data, Prestamos_Crudos...)  
  • SAVEPOINT/ROLLBACK para recuperación por fila                      

                           
                           

                 FASE 2: DEDUPLICACIÓN (CLEANING)                       
  • Matching fuzzy con thefuzz.ratio() + Levenshtein                   
  • Identificación de duplicados por similitud >= 95%                  
  • Resolución de conflictos: elección de registro canónico            
  • Marcado de registros consolidados                                  

                           
                           

                 FASE 3: NORMALIZACIÓN (3FN)                            
  • Transformación de modelo plano → relacional                        
  • Creación de entidades maestras (Autores, Editoriales, Categorías)  
  • Separación de N:M relationships (libros_autores)                   
  • Eliminación de dependencias transitivas                            
  • Validación de constraints e integridad referencial                 

                           
                           

              FASE 4: VALIDACIÓN DE CALIDAD (QA)                        
  • Análisis estático SQL (forbidden keywords, tipos de datos)         
  • Validación dinámica de datos contra reglas JSON                    
  • Verificación de constraints: required, max_length, regex, tipos    
  • Generación de reporte de anomalías                                 

                           
                           

               FASE 5: ENMASCARAMIENTO DE PII                           
  • Identificación de columnas sensibles (correo, teléfono, ID)        
  • Aplicación de máscaras: hash, truncado, sustitución aleatoria     
  • Mantenimiento de integridad referencial post-masking               
  • Auditoría de transformaciones aplicadas                            

                           
                           

               FASE 6: MIGRACIÓN A MONGODB                              
  • Mapeo relacional → documental (mapping_mongo.json)                 
  • Denormalización controlada para acceso eficiente                   
  • Creación de índices (single field + compound)                      
  • Batch insert con control de errores transaccional                  

                           
                           

               FASE 7-8: EXPORTACIÓN Y REPORTES                         
  • Exportación a Excel (openpyxl) con formato 3FN                     
  • Generación de reportes de auditoría (CSV, logs)                    
  • Estadísticas de transformación (registros, errores, duración)      
  • Evidencia de cobertura de tests (pytest-cov)                       

                           
                           

                   SALIDAS FINALES                                      
                                                                         
  PostgreSQL 16             MongoDB 7              Excel               
   Schema 3FN              Colecciones          Normalizado     
   Integridad RF           Índices              Formatos        
   Auditoría               Validaciones         PII Masking     
   PII Masking             TTL (si aplica)                         

```

### Contexto de Ejecución

```

                  Docker Compose (Orquestación)                  
                                                                 
        
    PostgreSQL       MongoDB         Python App         
        16              7           (Pipeline ETL)      
                                                        
   • Esquema       • Base de        • main.py            
     Legacy          datos          • src/ (9 módulos)   
   • Esquema         Documental     • tests/ (QA)        
     3FN           • Índices        • Dependencias       
   • Auditoría       optimizados      versionadas        
        
                                                             
                          
                                                              
                   Health Checks: REQUIRED                      
              (app espera hasta que servicios                  
               de datos estén READY antes de                   
                    iniciar pipeline)                          

```

---

## 3. TECNOLOGÍAS Y STACK

### Matriz de Tecnologías

| **Capa** | **Componente** | **Tecnología** | **Versión** | **Propósito** |
|----------|---|---|---|---|
| **Lenguaje** | Runtime | Python | 3.12 | Lenguaje principal, soporte asyncio, type hints |
| **Datos** | RDBMS | PostgreSQL | 16 | Esquema relacional normalizado, integridad referencial |
| **Datos** | NoSQL | MongoDB | 7 | Almacenamiento documental, flexibilidad schema |
| **Orquestación** | Contenedores | Docker | latest | Aislamiento, reproducibilidad, portabilidad |
| **Orquestación** | Compose | Docker Compose | v2 | Orquestación multi-contenedor, health checks |
| **Driver DB** | PostgreSQL | psycopg2-binary | 2.9.9 | Conexión eficiente, cursos, SAVEPOINT soporte |
| **Driver DB** | MongoDB | pymongo | 4.7.2 | ODM asyncio, bulk operations, índices |
| **Excel** | I/O | openpyxl | 3.1+ | Lectura/escritura Excel, estilos, formato |
| **Deduplicación** | Fuzzy Matching | thefuzz | 0.22+ | Matching de strings, similitud por Levenshtein |
| **Deduplicación** | Algoritmo | python-Levenshtein | 0.25+ | Optimización nativa de distancia edit |
| **Datos Sintéticos** | Generador | Faker | 25.2.0 | Población de datos realistas (nombres, fechas, etc) |
| **Testing** | Framework | pytest | 8.2.1 | Test runner, fixtures, parametrización |
| **Testing** | Cobertura | pytest-cov | 5.0+ | Reporte de cobertura de código (requirement ≥80%) |
| **Calidad Código** | Linter | flake8 | 7.0+ | Análisis PEP8, complejidad ciclomática |
| **Calidad Código** | Linter | pylint | 3.0+ | Análisis estático avanzado, best practices |
| **Config** | Variables Env | python-dotenv | 1.0.1 | Gestión de secrets y configuración |
| **Config** | Validación JSON | jsonschema | 4.22.0 | Validación de archivos de configuración |
| **CI/CD** | Automatización | GitHub Actions | latest | Pipeline continuo en cada push/PR |

### Justificación de Selecciones Clave

#### Python 3.12
- **Tipado Fuerte:** Type hints para autocompletado y detección de errores en tiempo de desarrollo
- **Performance:** Mejoras significativas en interpretación (PEP 684)
- **asyncio:** Soporte nativo para operaciones concurrentes (futura escalabilidad)
- **Seguridad:** Librerías cryptográficas modernas incluidas

#### PostgreSQL 16
- **Normalización 3FN:** Soporte nativo de constraints (PK, FK, CHECK, UNIQUE)
- **ACID Compliance:** Transacciones, SAVEPOINT para recuperación por fila
- **Integridad Referencial:** CASCADE DELETE, foreign keys con on_delete behavior
- **Índices Avanzados:** Soporta índices multicolumna para queries complejas

#### MongoDB 7
- **Flexibilidad Schema:** Almacenamiento de documentos semi-estructurados
- **Denormalización Controlada:** Nesting permitido sin violaciones 3FN
- **TTL Indices:** Expiración automática de datos sensibles (futuro PII masking)
- **Transactions Multi-documento:** ACID en operaciones batch

#### Docker Compose
- **Aislamiento:** Cada servicio en contenedor separado sin conflictos de puertos/dependencias
- **Health Checks:** Verificación automática de disponibilidad (pg_isready, mongosh ping)
- **Volúmenes Persistentes:** pgdata, mongodata, logs_data se mantienen entre ejecuciones
- **Reproducibilidad:** Definición declarativa garantiza mismo comportamiento en dev/staging/prod

#### thefuzz + Levenshtein
- **Deduplicación Fuzzy:** Detección de duplicados con variaciones tipográficas (similitud >95%)
- **Levenshtein Optimizado:** Algoritmo de distancia edit nativa (C), 10-100x más rápido que Python puro
- **Casos de Uso:** "John Doe" vs "Jon Doe", "usuario@email.com" vs "usuário@email.com"

---

## 4. ESTRUCTURA DEL PROYECTO

### Árbol de Directorios

```
biblioteca_quality_framework/

  DOCUMENTACION_TECNICA_COMPLETA.md  ← Este documento
 README.md                              # Guía rápida de usuario
 requirements.txt                       # Dependencias Python pinned
 pytest.ini                            # Config de pytest y coverage
 Dockerfile                            # Definición de imagen app
 docker-compose.yml                    # Orquestación multi-contenedor
 main.py                               # Punto de entrada del pipeline

 .github/
    workflows/
        ci.yml                        # GitHub Actions: Flake8 + Pytest CI

 config/                               # Configuración declarativa
    config_calidad.json              # Reglas de validación (tablas, columnas, regex)
    mapping_mongo.json                # Mapeo Relacional ↔ Documental

 data/                                 # Archivos de entrada
    Gestion_Biblioteca_Datos_Sucios_Para_Limpiar.xlsx

 sql/                                  # Definiciones de base de datos
    01_legacy_dirty_schema.sql       # Schema inicial (legacy plano)
    02_normalized_schema.sql         # Schema destino (3FN)
    03_db_objects.sql                # Stored Procedures, Views, fn_calcular_multa()

 src/                                  # Código principal (9 módulos)
    __init__.py
    db.py                            # Gestión de conexiones (psycopg2, pymongo)
    excel_loader.py                  # Fase 1: Ingesta desde Excel
    populate_legacy.py                # Fase 1b: Generación Faker (opcional)
    deduplicator.py                  # Fase 2: Deduplicación fuzzy
    normalizer.py                    # Fase 3: Transformación a 3FN
    quality_validator.py             # Fase 4: Validación de calidad
    migrator.py                      # Fase 6: Migración a MongoDB
    excel_exporter.py                # Fase 7: Exportación a Excel
    utils.py                         # Funciones auxiliares (hash, logging, JSON)

 tests/                                # Suite de pruebas unitarias (97 tests)
    test_db.py                       # Validación de conexiones
    test_excel.py                    # Tests: load + export + formatting
    test_deduplicator.py             # Tests: fuzzy matching, resolución conflictos
    test_normalizer.py               # Tests: transformaciones 3FN, integridad RF
    test_quality_validator.py        # Tests: validación de reglas (26 test cases)
    test_migrator_mongo.py           # Tests: inserción MongoDB, índices
    test_populate.py                 # Tests: generación sintética con Faker
    test_masking.py                  # Tests: enmascaramiento PII
    test_multa.py                    # Tests: cálculo de multas (business logic)

 logs/                                 # Outputs y reportes (generados en runtime)
    reporte_calidad.log              # Log transaccional del pipeline
    flake8_report.txt                # Análisis de estilo
    pylint_report.txt                # Análisis de calidad avanzado
    pytest_coverage.txt              # Evidencia cobertura ≥80%

 mongo_exports/                        # Archivos exportados desde MongoDB
    *.xlsx                           # Excel generados en Fase 7

 .env                                  # Variables de entorno (git-ignored)
     POSTGRES_HOST=postgres
     POSTGRES_PORT=5432
     MONGO_URI=mongodb://mongo:27017
     LOG_LEVEL=INFO
```

### Responsabilidad de Cada Módulo

| Archivo | Responsabilidad | Entradas | Salidas |
|---------|---|---|---|
| **main.py** | Orquestación del pipeline | Excel, Faker config | Logs, reportes |
| **db.py** | Pool de conexiones | Credenciales | Objetos conexión (pg, mongo) |
| **excel_loader.py** | Lectura Excel → legacy | .xlsx + mapeo | Registros en tablas legacy |
| **populate_legacy.py** | Generación sintética | Faker locale + qty | Datos sintéticos en legacy |
| **deduplicator.py** | Fuzzy matching | Registros legacy | Grupos de duplicados identificados |
| **normalizer.py** | Transformación 3FN | Registros legacy | Datos en tablas normalizadas |
| **quality_validator.py** | Validación de reglas | config_calidad.json | Reporte de anomalías |
| **migrator.py** | Relacional → Documental | Datos 3FN + mapping | Documentos en MongoDB |
| **excel_exporter.py** | Exportación multi-formato | Datos normalizados | .xlsx con formato |
| **utils.py** | Utilidades transversales | Datos variadosfor (hash, JSON, logs) | Datos procesados |

---

## 5. PIPELINE ETL — FASES DE IMPLEMENTACIÓN

### Visión General de Fases

El pipeline ETL consta de **9 fases secuenciales** que transforman datos sucios en un estado limpio, normalizado, validado y listo para producción.

### Fase 1: INGESTA (LOADING)

**Objetivo:** Leer datos reales desde Excel + generar datos sintéticos, insertar en esquema legacy.

**Módulos:** `excel_loader.py`, `populate_legacy.py`  
**Tecnologías:** openpyxl, Faker, psycopg2  
**Entrada:** `.xlsx` + configuración de locales  
**Salida:** Registros en tablas legacy (Biblioteca_Data, Prestamos_Crudos, etc)

#### Implementación Técnica

```python
# excel_loader.py — Mapeo dinámico de hojas → tablas
_SHEET_MAP = {
    "Biblioteca_Data": (
        '"Biblioteca_Data"',
        ["titulo_libro", "autor_nombre", "categoria_y_descripcion", 
         "editorial_info", "fecha_publicacion"]
    ),
    "Prestamos_Crudos": (
        '"Prestamos_Crudos"',
        ["id_prestamo", "nombre_usuario", "correo_usuario", 
         "libros_prestados", "fecha_salida", "estado_prestamo"]
    ),
    # ... más mapeos
}

# populate_legacy.py — Inyección de anomalías controladas
def populate_dirty_tables(conn, total_records: int = 250):
    """Generador de datos sintéticos con anomalías explícitas."""
    fake = Faker(locale)
    for i in range(total_records):
        # Inyectar ruido tipográfico (espacios, mayúsculas)
        titulo_ruido = inject_noise(title)
        
        # Duplicados intencionales (5% de los datos)
        if random.random() < 0.05:
            cur.execute(INSERT_SQL, row_data)  # Duplicar
        
        # Valores ausentes o inválidos (10-20%)
        if random.random() < 0.1:
            pub_date = "Desconocida"  # Fecha inválida
        elif random.random() < 0.2:
            pub_date = fake.date().strftime("%d/%m/%Y")  # Formato mixto
```

**Características Clave:**

 **Mapeo Dinámico:** Columnas identificadas por nombre, resiliente a reordenaciones  
 **SAVEPOINT/ROLLBACK:** Por cada fila para recuperación granular de fallos  
 **Logging Detallado:** Cada operación registrada con contexto (tabla, fila, error)  
 **Ruido Controlado:** Inyección deliberada de anomalías (duplicados, valores inválidos)

### Fase 2: DEDUPLICACIÓN (CLEANING)

**Objetivo:** Identificar y resolver duplicados usando matching fuzzy (Levenshtein).

**Módulos:** `deduplicator.py`  
**Tecnologías:** thefuzz, python-Levenshtein, psycopg2  
**Entrada:** Registros legacy con anomalías  
**Salida:** Grupos de duplicados identificados + canónico elegido

#### Implementación Técnica

```python
# deduplicator.py — Matching fuzzy con Levenshtein
from thefuzz import fuzz
from difflib import SequenceMatcher

def find_duplicates(conn, table: str, similarity_threshold: float = 0.95) -> dict:
    """Identifica duplicados usando similitud de strings."""
    records = fetch_all(conn, table)
    duplicates = {}
    
    for i, rec1 in enumerate(records):
        for rec2 in records[i+1:]:
            # Comparar campos clave (título, autor, etc)
            title_similarity = fuzz.ratio(rec1['titulo'], rec2['titulo']) / 100
            author_similarity = fuzz.ratio(rec1['autor'], rec2['autor']) / 100
            
            # Similitud combinada
            avg_similarity = (title_similarity + author_similarity) / 2
            
            if avg_similarity >= similarity_threshold:
                # Agrupar en candidatos de duplicados
                duplicates.setdefault(i, []).append((j, avg_similarity))
    
    # Elegir canónico: registros más antiguos o con menos NULL
    for group in duplicates.values():
        canonical_id = min(group, key=lambda x: fetch_record(conn, x[0])['nulls'])
        mark_as_canonical(conn, table, canonical_id)

# Cálculo de similitud: Levenshtein en C (10-100x más rápido)
# Ejemplo: "John Doe" vs "Jon Doe" → distancia=1 → similitud=95%
```

**Características Clave:**

 **Algoritmo de Levenshtein:** Distancia edit nativa (C compiled)  
 **Similitud Combinada:** Multiple campos ponderados  
 **Resolución de Conflictos:** Criterios: antigüedad, completitud, confiabilidad  
 **Auditoría Transitoria:** Marca canónico, registra decisión

### Fase 3: NORMALIZACIÓN (3FN)

**Objetivo:** Transformar modelo plano → relacional con integridad referencial completa.

**Módulos:** `normalizer.py`  
**Tecnologías:** psycopg2, SQL, álgebra relacional  
**Entrada:** Registros legacy (con duplicados identificados)  
**Salida:** Datos en 7 tablas normalizadas (3FN)

#### Implementación Técnica

```python
# normalizer.py — Transformación a 3FN
def normalize_to_3fn(conn) -> dict:
    """Orquestación de normalización en 7 pasos."""
    stats = {}
    
    # Paso 1: Crear tablas maestras (Categorías, Editoriales, Autores)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO categorias (nombre, descripcion)
            SELECT DISTINCT categoria_y_descripcion, descripcion
            FROM "Biblioteca_Data"
            ON CONFLICT (nombre) DO NOTHING
        """)
        stats['categorias'] = cur.rowcount
    
    # Paso 2: Extender autores (N:M relationship)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO autores (nombre)
            SELECT DISTINCT ON (nombre) autor_nombre
            FROM "Biblioteca_Data"
            WHERE autor_nombre IS NOT NULL
            ON CONFLICT (nombre) DO NOTHING
        """)
        stats['autores'] = cur.rowcount
    
    # Paso 3: Insertar libros (FK a categorías + editoriales)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO libros (titulo, fecha_publicacion, id_categoria, id_editorial)
            SELECT DISTINCT 
                bd.titulo_libro,
                CAST(bd.fecha_publicacion AS DATE),
                c.id_categoria,
                e.id_editorial
            FROM "Biblioteca_Data" bd
            LEFT JOIN categorias c ON bd.categoria_y_descripcion ILIKE c.nombre
            LEFT JOIN editoriales e ON bd.editorial_info ILIKE e.nombre
            ON CONFLICT (titulo) DO NOTHING
        """)
        stats['libros'] = cur.rowcount
    
    # Paso 4: Crear relación libros_autores (N:M)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO libros_autores (id_libro, id_autor)
            SELECT DISTINCT l.id_libro, a.id_autor
            FROM libros l
            CROSS JOIN autores a
            WHERE a.nombre IN (SELECT autor_nombre FROM "Biblioteca_Data" 
                              WHERE titulo_libro = l.titulo)
            ON CONFLICT DO NOTHING
        """)
        stats['libros_autores'] = cur.rowcount
    
    # Paso 5-7: Usuarios, Préstamos, Reseñas (similar)
    # ...
    
    return stats
```

**Cambios Realizados:**

| Aspecto | Legacy (1FN) | Normalizado (3FN) |
|---------|---|---|
| **Tablas** | 1 (Biblioteca_Data) | 7 (libros, autores, usuarios, etc) |
| **Duplicación de Datos** | "Autor1" repetido 100x | Tabla autores única |
| **Integridad Referencial** | Ninguna | Constraints FK, PK, CHECK |
| **Redundancia Transitiva** | "Editorial → País" implícito | Tabla editoriales separada |
| **Anomalías de Update** | Cambiar editorial → 100 UPDATE | Cambiar editorial → 1 UPDATE |

### Fase 4: VALIDACIÓN DE CALIDAD (QA)

**Objetivo:** Verificar datos limpios contra reglas configurables JSON.

**Módulos:** `quality_validator.py`  
**Tecnologías:** jsonschema, regex, psycopg2  
**Entrada:** Datos normalizados + config_calidad.json  
**Salida:** Reporte de anomalías (tabla, fila, error)

#### Implementación Técnica

```python
# quality_validator.py — Validación dinámica
config = {
    "tables": {
        "Prestamos_Crudos": {
            "correo_usuario": {
                "required": true,
                "regex": "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"
            },
            "estado_prestamo": {
                "required": true,
                "allowed_values": ["ACTIVO", "DEVUELTO", "VENCIDO"]
            },
            "fecha_salida": {
                "required": true,
                "type": "date",
                "max_date": "today"
            }
        }
    }
}

def _validate_value(table: str, column: str, value: Any, rule: dict) -> list[str]:
    """Valida un valor contra reglas declarativas."""
    failures = []
    
    # Requerido
    if rule.get("required") and (value is None or str(value).strip() == ""):
        failures.append(f"{table}.{column}: valor obligatorio vacío")
    
    # Longitud máxima
    if "max_length" in rule and len(str(value)) > int(rule["max_length"]):
        failures.append(f"{table}.{column}: longitud > {rule['max_length']}")
    
    # Tipo de dato
    if rule.get("type") == "integer":
        try:
            int(value)
        except (ValueError, TypeError):
            failures.append(f"{table}.{column}: debe ser entero")
    
    # Validación regex
    if "regex" in rule and not re.match(rule["regex"], str(value)):
        failures.append(f"{table}.{column}: no cumple formato {rule['regex']}")
    
    # Valores permitidos
    if "allowed_values" in rule and str(value) not in rule["allowed_values"]:
        failures.append(f"{table}.{column}: valor no en {rule['allowed_values']}")
    
    return failures

def validate_dirty_data(conn, config_path: Path) -> dict:
    """Auditoría exhaustiva de integridad de datos."""
    config = load_json(config_path)
    report = {"total_records": 0, "invalid_records": 0, "errors": []}
    
    for table, columns in config["tables"].items():
        for row in fetch_all(conn, table):
            report["total_records"] += 1
            row_errors = []
            
            for column, rule in columns.items():
                row_errors.extend(_validate_value(table, column, row[column], rule))
            
            if row_errors:
                report["invalid_records"] += 1
                report["errors"].append({
                    "table": table,
                    "row_id": row["id"],
                    "errors": row_errors
                })
    
    return report
```

**Reglas Soportadas:**

 `required: bool` — Campo obligatorio no nulo/vacío  
 `max_length: int` — Longitud máxima de string  
 `type: "integer"|"date"|...` — Validación de tipo  
 `regex: string` — Pattern matching POSIX  
 `allowed_values: [...]` — Enum restrictivo  
 `min: int`, `max: int` — Rango numérico  
 `must_contain: string` — Substring requerido  
 `no_empty_items_csv: bool` — CSV sin elementos vacíos

### Fase 5: ENMASCARAMIENTO DE PII

**Objetivo:** Reemplazar datos sensibles (correo, teléfono, ID) con valores pseudoanonimizados.

**Módulos:** Métodos en `normalizer.py`  
**Tecnologías:** hashlib, random, secrets  
**Entrada:** Datos normalizados  
**Salida:** Datos con PII enmascarado

#### Implementación Técnica

```python
# masking.py — Pseudoanonimización de PII
import hashlib
import secrets

def mask_email(email: str) -> str:
    """Enmascara email: usuario@domain.com → ****@domain.com"""
    local, domain = email.rsplit("@", 1)
    masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"

def mask_phone(phone: str) -> str:
    """Enmascara teléfono: +57 300 123 4567 → +57 *** *** 4567"""
    return phone[:phone.rfind(" ")] + " ****" if " " in phone else "****" * len(phone) // 4

def mask_id(id_value: str) -> str:
    """Hash determinístico para ID (mantiene referencia cruzada sin revelar)"""
    return "ID_" + hashlib.sha256(id_value.encode()).hexdigest()[:8].upper()

# Aplicación selectiva por columna
SENSITIVE_COLUMNS = {
    "usuarios": ["correo"],  # Mask correo en tabla usuarios
    "Prestamos_Crudos": ["correo_usuario"],
    # ...
}

def apply_masking(conn, table: str) -> int:
    """Aplica máscaras según SENSITIVE_COLUMNS."""
    masked_count = 0
    for col in SENSITIVE_COLUMNS.get(table, []):
        col_type = detect_column_type(conn, table, col)
        
        if "email" in col.lower():
            mask_func = mask_email
        elif "phone" in col.lower() or "telefono" in col.lower():
            mask_func = mask_phone
        elif "id" in col.lower() and col_type != "integer":
            mask_func = mask_id
        else:
            continue
        
        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE "{table}"
                SET "{col}" = %s
                WHERE "{col}" IS NOT NULL
            """, (mask_func(row[col]),) for row in fetch_all(conn, table))
            masked_count += cur.rowcount
    
    return masked_count
```

### Fase 6: MIGRACIÓN A MONGODB

**Objetivo:** Replicar datos normalizados en modelo documental NoSQL.

**Módulos:** `migrator.py`  
**Tecnologías:** pymongo, mapping_mongo.json  
**Entrada:** Datos 3FN en PostgreSQL  
**Salida:** Colecciones MongoDB con índices optimizados

#### Implementación Técnica

```python
# migrator.py — Mapeo Relacional → Documental
mapping = {
    "libros": {
        "collection": "books",
        "fields": {
            "id_libro": {"map_to": "_id", "type": "ObjectId"},
            "titulo": {"map_to": "title", "type": "string"},
            "fecha_publicacion": {"map_to": "published_date", "type": "date"},
            # Denormalización controlada: incluir autores
            "autores": {
                "source": "libros_autores",
                "join": {
                    "local_field": "id_libro",
                    "foreign_field": "id_libro",
                    "nested": "autores.nombre"
                }
            }
        },
        "indexes": [
            {"key": "title", "unique": true},
            {"key": "published_date"},
            {"key": ["title", "published_date"]}  # Compound index
        ]
    }
}

def migrate_to_mongodb(conn_pg, client_mongo, mapping: dict) -> dict:
    """Migración controlada con denormalización."""
    stats = {"collections": {}, "errors": []}
    
    for table_name, config in mapping.items():
        collection_name = config["collection"]
        collection = client_mongo.db[collection_name]
        
        # Lectura desde PostgreSQL con JOIN para denormalización
        query = build_denormalization_query(table_name, config)
        records = fetch_all(conn_pg, query)
        
        # Bulk insert con error handling
        try:
            result = collection.insert_many(records, ordered=False)
            stats["collections"][collection_name] = len(result.inserted_ids)
        except Exception as e:
            stats["errors"].append({"collection": collection_name, "error": str(e)})
        
        # Crear índices
        for index_spec in config.get("indexes", []):
            collection.create_index(
                [(index_spec["key"], 1 if not isinstance(index_spec["key"], list) else 1)],
                unique=index_spec.get("unique", False)
            )
    
    return stats
```

### Fase 7-8: EXPORTACIÓN Y REPORTES

**Objetivo:** Generar salidas en múltiples formatos (Excel, CSV, logs) + auditoría.

**Módulos:** `excel_exporter.py`, `utils.py`  
**Tecnologías:** openpyxl, logging  
**Entrada:** Datos normalizados + MongoDB  
**Salida:** Archivos Excel formateados + reportes de auditoría

#### Implementación Técnica

```python
# excel_exporter.py — Exportación con formato y PII masking
def _excel_value_and_format(header: str, value):
    """Retorna valor formateado para Excel según tipo de columna."""
    if value is None:
        return value, None
    
    header_lower = header.lower()
    
    # Email: formato especial + validación
    if "correo" in header_lower:
        return str(value).strip().lower(), "@"
    
    # Fechas: convertir a strings para evitar números de serie Excel
    if header_lower.startswith("fecha") and isinstance(value, datetime):
        if header_lower == "fecha_resena":
            return value.strftime("%d/%m/%Y %H:%M:%S"), None
        else:
            return value.strftime("%d/%m/%Y"), None
    
    if header_lower.startswith("fecha") and isinstance(value, date):
        return value.strftime("%d/%m/%Y"), None
    
    return value, None

def export_normalized_to_excel(conn, output_path: Path | str) -> Path:
    """Exporta 6 tablas normalizadas a Excel con estilos."""
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)  # Eliminar hoja por defecto
    
    for table in ["libros", "autores", "usuarios", "prestamos", "inventario", "resenas"]:
        headers, rows = _fetch_table(conn, table)
        ws = workbook.create_sheet(title=table)
        
        # Escribir headers en negrita
        bold_font = Font(bold=True)
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = bold_font
        
        # Escribir datos con formato
        for row_idx, row in enumerate(rows, start=2):
            for col_idx, value in enumerate(row, start=1):
                cell_value, number_format = _excel_value_and_format(
                    headers[col_idx - 1], value
                )
                cell = ws.cell(row=row_idx, column=col_idx, value=cell_value)
                if number_format:
                    cell.number_format = number_format
        
        # Auto-ajustar ancho de columnas
        _auto_adjust_width(ws)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    return output_path
```

### Fase 9: GENERACIÓN DE EVIDENCIAS

**Objetivo:** Documentar el pipeline con reportes de auditoría y cobertura.

**Logs Generados:**

1. **reporte_calidad.log** — Transacciones del pipeline (INSERT, UPDATE, DELETE)
2. **flake8_report.txt** — Análisis de estilo PEP8 (0 errors requerido)
3. **pylint_report.txt** — Análisis avanzado de calidad
4. **pytest_coverage.txt** — Evidencia de cobertura ≥80%

---

## 6. INFRAESTRUCTURA: DOCKER COMPOSE

### Propósito y Beneficios

**Docker Compose** orquesta 3 servicios en una definición YAML declarativa, garantizando:

 **Reproducibilidad:** Mismo comportamiento dev → staging → prod  
 **Aislamiento:** Cada contenedor con su own filesystem, network, UID  
 **Health Checks:** Verificación automática de disponibilidad pre-ejecución  
 **Persistencia:** Volúmenes para datos entre ejecuciones  
 **Networking:** Comunicación intra-contenedor por nombre de servicio

### Estructura de docker-compose.yml

```yaml
version: '3.9'

services:
  # ========== SERVICIO 1: PostgreSQL 16 ==========
  postgres:
    image: postgres:16
    container_name: biblioteca_postgres
    
    # Variables de entorno (init)
    environment:
      POSTGRES_DB: biblioteca_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres  #  En producción: usar secrets
    
    # Puertos exposición
    ports:
      - "5432:5432"  # localhost:5432 → contenedor:5432
    
    # Volúmenes persistentes
    volumes:
      # Persistencia de datos entre reejecs
      - pgdata:/var/lib/postgresql/data
      
      # Inicialización automática (read-only)
      - ./sql/01_legacy_dirty_schema.sql:/docker-entrypoint-initdb.d/01_legacy_dirty_schema.sql:ro
    
    # Health check (requerido para app depends_on condition)
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d biblioteca_db"]
      interval: 5s          # Verificar cada 5s
      timeout: 5s           # Timeout de comando
      retries: 10           # Máximo 10 intentos
      start_period: 0s      # Esperar antes del 1er check

  # ========== SERVICIO 2: MongoDB 7 ==========
  mongo:
    image: mongo:7
    container_name: biblioteca_mongo
    
    ports:
      - "27017:27017"
    
    volumes:
      - mongodata:/data/db
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping').ok", "--quiet"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 10s

  # ========== SERVICIO 3: Aplicación Python ==========
  app:
    # Build desde Dockerfile local
    build:
      context: .
      dockerfile: Dockerfile
    
    container_name: biblioteca_app
    
    # Cargar variables de entorno desde .env
    env_file:
      - .env
    
    # Sobreescribir hosts para comunicación intra-contenedor
    environment:
      POSTGRES_HOST: postgres      # Resuelto por Docker DNS
      POSTGRES_PORT: 5432
      MONGO_URI: mongodb://mongo:27017
      LOG_LEVEL: INFO
    
    # Esperar a que servicios estén healthy ANTES de iniciar
    depends_on:
      postgres:
        condition: service_healthy  #  Bloquea hasta pg_isready OK
      mongo:
        condition: service_healthy  #  Bloquea hasta mongosh ping OK
    
    # Volúmenes para persistencia de logs y outputs
    volumes:
      # Reportes generados por CI
      - logs_data:/app/logs
      
      # Archivos exportados desde MongoDB
      - ./mongo_exports:/app/mongo_exports
    
    # No reiniciar si exit(0): el pipeline corre una vez
    restart: "no"

# ========== VOLÚMENES NOMBRADOS ==========
volumes:
  pgdata:           # PostgreSQL data persistence
  mongodata:        # MongoDB data persistence
  logs_data:        # Reportes y evidencia
```

### Diagrama de Secuencia de Inicialización

```

              Docker Compose Up Sequence                         


    [T=0s]
     Crear redes y volúmenes
    
     Iniciar PostgreSQL
       Esperar init scripts: 01_legacy_dirty_schema.sql
       Health check: pg_isready (retry x10, 5s interval)
       [READY] PostgreSQL accessible en postgres:5432
    
     Iniciar MongoDB
       Esperar inicialización
       Health check: mongosh ping (retry x10, 10s interval)
       [READY] MongoDB accessible en mongo:27017
    
     Iniciar App (solo si ambas BDs READY)
       Build imagen desde Dockerfile
       Cargar .env + environment
       Conectar a postgres:5432 (no localhost)
       Conectar a mongodb://mongo:27017
       Ejecutar main.py (9-fase pipeline)
    
     [T=60s] Pipeline completo
        Logs: logs_data/reporte_calidad.log
        Excel: mongo_exports/*.xlsx
        Exit(0) → app container stops (no restart)
```

### Comando de Ejecución

```bash
# Construir + iniciar todo
docker compose up --build

# Seguir logs en tiempo real
docker compose logs -f app

# Ejecutar comando en contenedor app
docker compose exec app python -c "import sys; print(sys.version)"

# Detener servicios (preserve volúmenes)
docker compose down

# Detener + eliminar volúmenes (clean slate)
docker compose down -v

# Ver estado de servicios
docker compose ps
```

### Solución de Problemas

| Problema | Causa | Solución |
|---|---|---|
| `app` no inicia | BDs no ready | Verificar health checks con `docker compose ps` |
| `ConnectionRefused postgres:5432` | Health check failed | Aumentar `retries` o `interval` |
| Volúmenes no persistidos | Ruta incorrecta | Usar volúmenes nombrados o rutas absolutas |
| Port 5432 en uso | Conflicto local | Mapear a puerto diferente: `"5433:5432"` |

---

## 7. CI/CD PIPELINE: GITHUB ACTIONS

### Arquitectura del Pipeline

El workflow `.github/workflows/ci.yml` se dispara en cada **push/PR** a main/master branches y ejecuta:

1. **Checkout del código**
2. **Setup Python 3.12** (con pip cache)
3. **Análisis de Estilo (Flake8)**
4. **Pruebas Unitarias + Cobertura (Pytest)**

### Definición de Workflow

```yaml
name: Biblioteca Quality Pipeline (CI)

# Disparadores
on:
  push:
    branches: [ "main", "master" ]
  pull_request:
    branches: [ "main", "master" ]

jobs:
  quality-assurance:
    runs-on: ubuntu-latest  # Runner: Ubuntu con GitHub Actions
    
    steps:
    # Paso 1: Clonar repositorio
    - name:  Clonar el repositorio
      uses: actions/checkout@v4
    
    # Paso 2: Setup Python con cache de pip
    - name:  Configurar Python 3.12
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"
        cache: "pip"  #  Cache de dependencies para builds más rápidos
    
    # Paso 3: Instalar dependencias
    - name:  Instalar dependencias
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    # Paso 4: Análisis de Estilo (Flake8)
    - name:  Análisis de Estilo (Flake8)
      run: |
        # Configuración: max line length 100, ignore E501, W503
        flake8 src/ tests/ \
          --count \                    # Mostrar contador de errores
          --show-source \              # Mostrar línea problemática
          --statistics                 # Mostrar estadísticas de errores
        #  Build falla si hay errores de estilo (exit code != 0)
    
    # Paso 5: Pruebas Unitarias + Cobertura
    - name:  Pruebas Unitarias y Cobertura (Pytest)
      run: |
        pytest tests/ \
          --cov=src \                  # Medir cobertura de src/
          --cov-fail-under=80 \        #  Fallar si cobertura < 80%
          --cov-report=term-missing    # Mostrar líneas no cubiertas
        #  Genera reporte HTML en htmlcov/index.html (opcional)
```

### Flujo de Ejecución Detallado

```

              GitHub Actions Workflow                            


[TRIGGER: push to main]
       ↓
[Set up runner: ubuntu-latest]
       ↓
[Checkout@v4]
   git clone https://github.com/daniquinto/...
       ↓
[Setup Python 3.12 + pip cache]
   Restaurar cache si disponible (2-5s saved)
       ↓
[Install dependencies]
   pip install -r requirements.txt (psycopg2, pytest, flake8, ...)
       ↓
[Flake8 Análisis de Estilo]
    flake8 src/ tests/
       Verificar PEP8 (line length, indentation, imports)
       Complejidad ciclomática (C901)
       Reporte: N errors, M warnings
      
      Si ERRORS > 0:
          BUILD FAILED (exit 1)
      Else:
          BUILD PASSED (continue)
       ↓
[Pytest: Unit Tests + Coverage]
    pytest tests/ --cov=src --cov-fail-under=80
       Ejecutar 97 tests
       Medir cobertura de líneas en src/
       Generar reporte:
         src/__init__.py: 100%
         src/db.py: 100%
         src/excel_exporter.py: 98%
         src/quality_validator.py: 94%
         TOTAL: 87.37%
      
      Si coverage < 80%:
          BUILD FAILED (exit 1)
         Mostrar líneas no cubiertas (Missing)
      Else:
          BUILD PASSED
       ↓
[Summary]
    All checks passed
   Crear artifact (opcional): pytest-report.html
   Enviar status a GitHub PR/commit
```

### Estadísticas de Build (Ejemplo Reciente)

```
Name                       Stmts   Miss  Cover   Missing

src/__init__.py                0      0  100%
src/db.py                     19      0  100%
src/deduplicator.py           61      0  100%
src/excel_exporter.py         57      1   98%   116
src/excel_loader.py           52      9   83%   71-75, 110-114
src/migrator.py               47      7   85%   12-14, 83, 93
src/normalizer.py            156     43   72%   27, 57-69, 135
src/populate_legacy.py        91      9   90%   44, 67-76, 106-111
src/quality_validator.py      84      5   94%   44, 59-60, 65-66
src/utils.py                 27      1   96%   19

TOTAL                        594     75   87%     PASSED (>80%)
```

### Reglas de Protección de Rama

**En GitHub:** Settings → Branches → main

```
 Require status checks to pass before merging:
   - Biblioteca Quality Pipeline (CI) [quality-assurance]
   
 Require branches to be up to date before merging
 Require code reviews before merging (≥1)
 Require conversation resolution before merging
 Restrict who can push to matching branches
```

**Resultado:** Un commit no puede mergearse a main si:
-  Análisis de estilo falla (flake8 errors)
-  Tests fallan (pytest errors)
-  Cobertura < 80%
-  No hay PR review

---

## 8. IMPLEMENTACIÓN TÉCNICA DETALLADA

### 8.1 Gestión de Conexiones (db.py)

```python
# db.py — Connection pooling y context managers
class DatabaseConnection:
    """Gestor de conexiones con timeout y error handling."""
    
    def __init__(self, host, port, database, user, password):
        self.params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password,
            'connect_timeout': 5
        }
    
    def get_pg_connection(self):
        """Retorna conexión PostgreSQL con timeout."""
        try:
            conn = psycopg2.connect(**self.params)
            conn.set_session(autocommit=False)
            return conn
        except psycopg2.OperationalError as e:
            logger.error(f"Conexión PG falló: {e}")
            raise
    
    def get_mongo_client(self):
        """Retorna cliente MongoDB con retry automático."""
        from pymongo import MongoClient
        try:
            client = MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=5000,
                retryWrites=True
            )
            # Test connection
            client.admin.command('ping')
            return client
        except Exception as e:
            logger.error(f"Conexión Mongo falló: {e}")
            raise

# Context manager usage
@contextmanager
def get_db_connection(host, port, db, user, pwd):
    """Context manager para guarantizar cierre de conexión."""
    conn = None
    try:
        conn = psycopg2.connect(host=host, port=port, database=db, 
                                user=user, password=pwd)
        yield conn
    finally:
        if conn:
            conn.close()  # Garantizar cierre incluso si error
```

### 8.2 Transformación 3FN (normalizer.py)

**Algoritmo de Normalización:**

```
Input: Tabla legacy (Biblioteca_Data) con datos denormalizados
Output: 7 tablas normalizadas con constraints e integridad referencial

Paso 1: Identificar atributos de dependencias funcionales
  autor_nombre → (id_autor)
  editorial_info → (id_editorial)
  categoria_y_descripcion → (id_categoria)

Paso 2: Crear tablas maestras (catálogos independientes)
  CREATE TABLE autores (id_autor PK, nombre UNIQUE)
  CREATE TABLE editoriales (id_editorial PK, nombre UNIQUE)
  CREATE TABLE categorias (id_categoria PK, nombre UNIQUE)

Paso 3: Crear tabla de hechos con FKs
  CREATE TABLE libros (
    id_libro PK,
    titulo UNIQUE,
    id_categoria FK → categorias.id_categoria,
    id_editorial FK → editoriales.id_editorial
  )

Paso 4: Crear relaciones N:M para romper ciclos
  CREATE TABLE libros_autores (
    id_libro FK,
    id_autor FK,
    PRIMARY KEY (id_libro, id_autor)
  )

Paso 5: Normalizar restantes entidades
  usuarios (id_usuario PK, nombre, correo UNIQUE CHECK)
  prestamos (id_prestamo PK, id_usuario FK, id_libro FK, ...)
  resenas (id_resena PK, id_usuario FK, id_libro FK, ...)

Paso 6: Validar constraints
   Todas las FKs validan
   No hay ciclos
   No hay redundancia transitiva
```

### 8.3 Deduplicación Fuzzy (deduplicator.py)

**Algoritmo de Levenshtein:**

```
Similitud entre "John Doe" y "Jon Doe":

Secuencia 1: J O H N   D O E
Secuencia 2: J O N     D O E

Distancia edit (operaciones mínimas):
  1. DELETE 'H' en posición 2
  Total: 1 operación

Similitud = 1 - (distancia / max_length)
         = 1 - (1 / 8)
         = 0.875 = 87.5%

Si threshold = 95%:
  87.5% < 95% → NO es duplicado
  
Si threshold = 85%:
  87.5% > 85% → SÍ es duplicado (agrupar)
```

**Implementación Optimizada (C nativa):**

```python
from thefuzz import fuzz

# Python puro (lento)
def py_levenshtein(s1: str, s2: str) -> int:
    # O(n*m) - crecimiento cuadrático
    pass

# Levenshtein optimizado en C (10-100x más rápido)
similarity = fuzz.ratio("John Doe", "Jon Doe")  # 87
similarity = fuzz.token_sort_ratio("Doe John", "John Doe")  # 100

# Aplicación a deduplicador
threshold = 0.95
if fuzz.ratio(record1["titulo"], record2["titulo"]) / 100 >= threshold:
    mark_as_duplicate(record1, record2)
```

### 8.4 Validación de Calidad (quality_validator.py)

**Máquina de Estado de Validación:**

```

  Valor entra a _validate_value(table, col, val, rule)  

            
            

  ¿rule.required == true?                      
   SI: ¿val is None?                         
      SI: error = "valor obligatorio vacío" 
      NO: continuar                         
   NO: continuar                             

            
            

  ¿"max_length" in rule?                        
   SI: ¿len(val) > rule["max_length"]?        
       SI: error += "longitud > max"          
       NO: continuar                         

            
            

  ¿rule.type == "integer"?                      
   SI: ¿int(val) raises?                      
       SI: error += "no es entero"            
       NO: continuar                         

            
            

  ¿"regex" in rule?                             
   SI: ¿re.match(rule.regex, val)?            
       SI: continuar                         
       NO: error += "no cumple formato"       

            
            

  Return: [errors] o []                        

```

---

## 9. ASEGURAMIENTO DE CALIDAD

### Estrategia de Testing

**Enfoque:** Pirámide de tests (base amplia, apex angosto)

```
        
        
              E2E (End-to-End)
              - Integration tests
       - Pipeline completo
            
   Integration Tests
               - Modelos interactuando


 Unit Tests (Cobertura ≥80%)
                - Funciones aisladas
 ~90 tests      - Mocks de dependencias
                - Rápidos (<1s por test)

```

### Suite de Pruebas (97 tests)

| Módulo | Tests | Cobertura | Propósito |
|--------|-------|-----------|-----------|
| test_db.py | 3 | 100% | Conexiones PostgreSQL + MongoDB |
| test_excel.py | 9 | 98% | Carga/exporta Excel, formateo de fechas |
| test_deduplicator.py | 16 | 100% | Fuzzy matching, resolución de conflictos |
| test_normalizer.py | 22 | 100% | Transformación 3FN, integridad RF |
| test_quality_validator.py | 26 | 94% | Validación de reglas (16 tipos) |
| test_migrator_mongo.py | 2 | 100% | Inserción en MongoDB, índices |
| test_populate.py | 1 | 90% | Generación sintética con Faker |
| test_masking.py | 13 | 100% | Enmascaramiento de PII |
| test_multa.py | 7 | 100% | Cálculo de multas (business logic) |
| **TOTAL** | **97** | **87.37%** |  |

### Cobertura por Línea Crítica

```
src/deduplicator.py         100%
src/normalizer.py            72%
src/quality_validator.py     94%
src/excel_exporter.py        98%
src/populate_legacy.py       90%
src/utils.py                 96%
src/migrator.py              85%
src/excel_loader.py          83%

PROMEDIO TOTAL:              87% 
```

### Comando de Ejecución

```bash
# Ejecutar todos los tests con cobertura
pytest tests/ --cov=src --cov-report=term-missing

# Tests específicos
pytest tests/test_normalizer.py -v

# Tests en paralelo (pytest-xdist)
pytest tests/ -n auto

# Coverage en HTML (para revisar líneas no cubiertas)
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

---

## 10. DECISIONES DE INGENIERÍA

### 10.1 ¿Por qué PostgreSQL + MongoDB?

| Caso de Uso | PostgreSQL | MongoDB |
|---|---|---|
| **Consultas transaccionales** |  ACID, FOREIGN KEYS |  Eventual consistency |
| **Integridad referencial** |  Native constraints |  Application-level |
| **Flexibilidad schema** |  Fixed schema |  Dynamic schema |
| **Queries complejas (JOIN)** |  Optimizadas |  Denormalización necesaria |
| **Escalabilidad horizontal** |  Sharding complejo |  Nativo sharding |

**Decisión:** Usar ambas
- PostgreSQL para datos normalizados (source of truth)
- MongoDB para read-heavy workloads (caching + denormalización)

### 10.2 ¿Por qué thefuzz + Levenshtein?

**Alternativas Evaluadas:**

1. **Exact match**  — Falla con typos ("John" vs "Jon")
2. **Soundex/Metaphone**  — Solo fonético, no orthographic
3. **Cosine similarity (TF-IDF)**  — Overhead para strings cortos
4. **Levenshtein**  — Óptimo para similitud de strings

**thefuzz + python-Levenshtein:** 10-100x más rápido que implementación Python pura.

### 10.3 ¿Por qué Docker Compose en lugar de Kubernetes?

| Aspecto | Docker Compose | Kubernetes |
|---|---|---|
| **Curva de aprendizaje** |  Moderada |  Empinada |
| **Setup inicial** |  ~10 min |  ~2 horas |
| **Producción escalada** |  Single host |  Multi-node |
| **Local development** |  Perfecto |  Overkill |
| **Requerimientos** | 1 YAML | 5-10 YAMLs |

**Decisión:** Docker Compose para dev/staging (producción: Kubernetes después).

### 10.4 ¿Cobertura >80% obligatoria?

**Justificación:**

- **Línea base:** <50% cobertura = código no confiable
- **Estándar industrial:** 80-90% cobertura para datos críticos
- **ROI:** 80% coverage cuesta 20% esfuerzo adicional
- **Diminishing returns:** >95% cobertura es costoso (test code > app code)

**Aplicado:** `pytest tests/ --cov-fail-under=80` previene merge de código sin tests.

---

## 11. GUÍA DE OPERACIÓN

### 11.1 Quick Start

```bash
# 1. Clonar repositorio
git clone https://github.com/daniquinto/biblioteca-quality-automation-framework.git
cd biblioteca_quality_framework

# 2. Crear .env
cat > .env << EOF
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=biblioteca_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
MONGO_URI=mongodb://mongo:27017
LOG_LEVEL=INFO
EOF

# 3. Ejecutar pipeline
docker compose up --build

# 4. Revisar salidas
docker compose logs -f app
ls logs/
ls mongo_exports/
```

### 11.2 Troubleshooting

#### Problema: `App container exits immediately`

```bash
# Ver logs de error
docker compose logs app

# Verificar health de PostgreSQL
docker compose ps

# Reintentar con debugging
docker compose up --no-color app 2>&1 | grep -i error
```

#### Problema: `Port 5432 already in use`

```bash
# Opción 1: Usar puerto diferente
sed -i 's/"5432:5432"/"5433:5432"/' docker-compose.yml

# Opción 2: Matar proceso
lsof -i :5432 | tail -1 | awk '{print $2}' | xargs kill -9
```

#### Problema: `Cobertura < 80% en CI`

```bash
# Local reproduction
pytest tests/ --cov=src --cov-report=term-missing

# Identificar líneas no cubiertas
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html

# Agregar test para línea faltante
# Editar tests/test_*.py
# Ejecutar nuevamente
```

### 11.3 Operación en Producción

```bash
# 1. Setup inicial (una sola vez)
docker compose up -d

# 2. Ejecutar pipeline
docker compose run --rm app python main.py

# 3. Extraer resultados
docker cp biblioteca_app:/app/logs ./outputs/logs
docker cp biblioteca_app:/app/mongo_exports ./outputs/exports

# 4. Limpiar
docker compose down -v  #  Elimina bases de datos
```

---

## CONCLUSIONES

El **Biblioteca Quality Automation Framework** implementa un pipeline ETL profesional de 9 fases que:

 **Resuelve deuda técnica:** Transforma datos legacy sucios en modelo normalizado 3FN  
 **Asegura calidad:** 97 tests unitarios con cobertura >87%  
 **Automatiza CI/CD:** GitHub Actions ejecuta análisis + tests en cada push  
 **Escala:** Docker Compose + PostgreSQL + MongoDB listos para producción  
 **Audita:** Reportes completos de transformación, anomalías y evidencia  

### Stack Final

```
Frontend: Excel I/O (openpyxl)
  ↓
Backend: Python 3.12 ETL (9 módulos, 600+ líneas)
  ↓
Data: PostgreSQL 16 (Schema 3FN) + MongoDB 7 (Documental)
  ↓
QA: pytest (97 tests, 87% cobertura) + flake8 (0 errors)
  ↓
CI/CD: GitHub Actions (auto lint + test en cada commit)
  ↓
Orchestration: Docker Compose (3 servicios, health checks)
```

---

**Documentación versión 2.0.0 — Mayo 2026**  
**Proyecto: Biblioteca Quality Automation Framework**  
**Repositorio:** https://github.com/daniquinto/biblioteca-quality-automation-framework

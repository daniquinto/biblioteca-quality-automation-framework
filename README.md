# Framework de Calidad, Automatización y Migración de Datos - Biblioteca Central

## 1. Propósito

Este proyecto implementa una solución profesional para el reto de calidad de software de la Biblioteca Central. El sistema toma una base de datos PostgreSQL legacy mal diseñada, la puebla automáticamente con datos de prueba, valida su calidad mediante reglas declaradas en JSON, normaliza el modelo en 3FN, ejecuta objetos de base de datos y migra la información consistente hacia MongoDB.

## 2. Alcance cubierto

La solución cubre estrictamente los entregables solicitados:

- `main.py`: orquestador del proceso completo.
- `sql/`: scripts SQL para modelo legacy, modelo normalizado y objetos de base de datos.
- `config/config_calidad.json`: reglas de validación de calidad.
- `config/mapping_mongo.json`: reglas de mapeo PostgreSQL -> MongoDB.
- `logs/reporte_calidad.log`: reporte generado automáticamente en ejecución.
- `guia.md`: guía para validar requerimientos y ejecutar en Linux con Visual Studio Code.

## 3. Arquitectura

```text
biblioteca_quality_framework/
├── main.py
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── config/
│   ├── config_calidad.json
│   └── mapping_mongo.json
├── sql/
│   ├── 01_legacy_dirty_schema.sql
│   ├── 02_normalized_schema.sql
│   └── 03_db_objects.sql
├── src/
│   ├── db.py
│   ├── migrator.py
│   ├── normalizer.py
│   ├── populate_legacy.py
│   ├── quality_validator.py
│   └── utils.py
├── tests/
│   └── test_quality_validator.py
├── logs/
└── mongo_exports/
```

## 4. Diseño de datos

### 4.1 Modelo legacy

El archivo `sql/01_legacy_dirty_schema.sql` reproduce el modelo inicial con problemas intencionales:

- Campos multivalorados como `libros_prestados`.
- Campos combinados como `categoria_y_descripcion`.
- Tipos inconsistentes como `fecha_publicacion VARCHAR(50)` y `calificacion VARCHAR(10)`.
- Ausencia de llaves foráneas.

### 4.2 Modelo normalizado 3FN

El archivo `sql/02_normalized_schema.sql` crea un diseño normalizado con tablas separadas para:

- `libros`
- `autores`
- `libros_autores`
- `usuarios`
- `prestamos`
- `categorias`
- `editoriales`
- `sedes`
- `inventario`
- `resenas`
- `auditoria_prestamos`

Se aplican claves primarias, claves foráneas, restricciones `CHECK`, unicidad y relaciones de integridad referencial.

## 5. Objetos de base de datos

El archivo `sql/03_db_objects.sql` implementa:

- Stored Procedures CRUD sobre la tabla principal `libros`:
  - `sp_insertar_libro`
  - `sp_actualizar_libro`
  - `sp_eliminar_libro`
- Vista `vw_libros_mas_prestados`.
- Función `fn_calcular_multa`.
- Cursor encapsulado en `sp_auditar_prestamos_activos`, que genera registros en `auditoria_prestamos`.

## 6. Automatización en Python

El orquestador `main.py` ejecuta las fases en orden:

1. Crea el modelo legacy.
2. Inserta 250 registros automáticos usando Faker.
3. Valida sintaxis y calidad usando `config_calidad.json`.
4. Aplica el modelo normalizado en 3FN.
5. Ejecuta stored procedures, vista, función y cursor.
6. Migra datos a MongoDB usando `mapping_mongo.json`.
7. Genera el log `logs/reporte_calidad.log`.

## 7. Configuración

Copie el archivo de ejemplo:

```bash
cp .env.example .env
```

Variables principales:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=biblioteca_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
MONGO_URI=mongodb://localhost:27017
MONGO_DB=biblioteca_mongo
FAKER_LOCALE=es_CO
```

## 8. Ejecución rápida con Docker

```bash
docker compose up -d
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## 9. Evidencia esperada

Al finalizar, deben existir:

- Datos en PostgreSQL en las tablas normalizadas.
- Documentos en MongoDB en las colecciones `books`, `users`, `loans` e `inventory`.
- Log de calidad en `logs/reporte_calidad.log`.
- Salida en consola con el top de libros más prestados y cálculo de multa.

## 10. Consideraciones profesionales

- La lógica está modularizada en `src/`.
- Las reglas de validación y mapeo no están quemadas en el código: se leen desde JSON.
- La solución usa transacciones en PostgreSQL.
- La migración limpia colecciones destino antes de insertar para mantener ejecuciones reproducibles.
- El proyecto incluye prueba unitaria base con `pytest`.

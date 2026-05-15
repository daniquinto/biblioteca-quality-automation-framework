# Documentación Técnica: Framework de Calidad y Migración de Datos

## 1. Introducción
Este proyecto implementa un **Framework de Automatización y Calidad de Datos** diseñado para modernizar el sistema de gestión de una biblioteca universitaria. El sistema transita desde una base de datos PostgreSQL "legacy" con deficiencias estructurales hacia un modelo normalizado (3FN) y, finalmente, hacia una arquitectura NoSQL basada en documentos en MongoDB.

## 2. Arquitectura del Sistema
El framework utiliza una arquitectura modular orquestada por Python, apoyada en contenedores Docker para los motores de base de datos:
- **PostgreSQL 16**: Motor relacional para el almacenamiento estructurado y normalizado.
- **MongoDB 7**: Motor documental para la persistencia final de alta disponibilidad.
- **Python 3.12**: Lenguaje orquestador mediante las librerías `psycopg2` (Postgres) y `pymongo` (MongoDB).

---

## 3. Fase A: Aseguramiento de Calidad (QA) y Normalización

### 3.1. Validación de Calidad mediante JSON
Se implementó un motor de validación que consume el archivo `config/config_calidad.json`. 
- **Justificación Técnica**: Al externalizar las reglas de negocio en un JSON, el framework se vuelve agnóstico a cambios en las políticas de validación sin necesidad de modificar el código fuente.
- **Validaciones Críticas**:
    - Integridad de formatos (Regex para correos).
    - Restricciones de dominio (Calificación de 1 a 5).
    - Análisis estático de SQL (Detección de campos TEXT innecesarios).

### 3.2. Normalización de Datos (3FN)
Se rediseñó el esquema `sql/01_legacy_dirty_schema.sql` (sucio) al esquema `sql/02_normalized_schema.sql` (3FN).
- **1FN**: Se eliminaron los campos multivalorados (como `libros_prestados` en formato CSV) creando relaciones de uno a muchos.
- **2FN**: Se eliminaron las dependencias parciales separando autores y editoriales del registro del libro.
- **3FN**: Se eliminaron dependencias transitivas extrayendo la información de sedes hacia una entidad independiente.

---

## 4. Fase B: Objetos Programables (Business Logic)

Para asegurar la integridad y eficiencia del lado del servidor, se implementaron los siguientes objetos en `sql/03_db_objects.sql`:

- **Stored Procedures (CRUD)**: Encapsulan la lógica de inserción compleja (`Upsert`). El procedimiento `sp_insertar_libro` garantiza que si un autor o categoría no existe, se crea automáticamente antes de registrar el libro, manteniendo la integridad referencial.
- **Vistas Analíticas**: La vista `vw_libros_mas_prestados` utiliza funciones de agregación (`STRING_AGG`) para presentar reportes consolidados, optimizando el rendimiento de las consultas frecuentes.
- **Funciones de Usuario (UDF)**: `fn_calcular_multa` automatiza el cálculo de sanciones monetarias basándose en la fecha actual y los días de mora, centralizando la regla de negocio en la DB.
- **Cursores de Auditoría**: `sp_auditar_prestamos_activos` utiliza cursores explícitos para recorrer registros activos de forma eficiente en memoria, generando alertas proactivas en una tabla de auditoría dedicada.

---

## 5. Fase C y D: Automatización y Migración NoSQL

### 5.1. Poblamiento Masivo y Estrés
Utilizando la librería `Faker`, el orquestador `main.py` genera 250 registros aleatorios por cada tabla legacy. 
- **Objetivo**: Demostrar la degradación del rendimiento en modelos no normalizados y validar la robustez del framework ante volúmenes crecientes de datos.

### 5.2. Orquestación y Transformación (ETL)
El script principal realiza el siguiente flujo:
1.  **Limpieza**: Ejecuta el script legacy.
2.  **Poblamiento**: Inserta datos sucios generados con Python.
3.  **Validación**: Contrasta los datos con `config_calidad.json`.
4.  **Normalización**: Ejecuta el script 3FN y migra los datos internamente en Postgres.
5.  **Migración NoSQL**: Extrae los datos normalizados y, mediante `mapping_mongo.json`, transforma las tablas relacionales en documentos embebidos (ej. la categoría y autor se guardan dentro del documento del libro).

---

## 6. Justificación de la Migración a MongoDB
La transformación final a MongoDB se justifica por:
- **Modelo Denormalizado**: El acceso a los datos de un libro (con su autor y editorial) es más rápido al estar embebidos en un solo documento.
- **Escalabilidad**: Permite el crecimiento horizontal del sistema de la biblioteca ante un aumento masivo de usuarios.
- **Flexibilidad**: Facilita la adición de nuevos atributos (como portadas de libros o reseñas multimedia) sin alterar esquemas rígidos.

---

## 7. Instrucciones de Uso
1. Levantar servicios: `docker compose up -d`
2. Instalar dependencias: `pip install -r requirements.txt`
3. Ejecutar orquestador: `python main.py`
4. Revisar resultados: `cat logs/reporte_calidad.log`

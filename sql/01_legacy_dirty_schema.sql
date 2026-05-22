-- =============================================================================
-- SCRIPT 01: SCHEMA LEGACY (SIN NORMALIZAR)
-- Proyecto  : Framework de Calidad – Biblioteca UNISABANETA
-- Propósito : Representar el estado inicial degradado del sistema.
--             Contiene errores de diseño intencionales que serán analizados
--             y corregidos en las fases posteriores del framework.
-- Errores documentados:
--   • Biblioteca_Data  -> campo combinado (viola 1FN), fecha como VARCHAR
--   • Prestamos_Crudos -> lista multivalorada (viola 1FN), sin PK explícita
--   • Inventario_Sedes -> sin PK, datos redundantes de libro y sede
--   • Reseñas_Usuarios -> calificacion como VARCHAR (debería ser numérico)
-- =============================================================================

-- Limpiar si ya existen (para re-ejecuciones)
DROP TABLE IF EXISTS Reseñas_Usuarios  CASCADE;
DROP TABLE IF EXISTS Inventario_Sedes  CASCADE;
DROP TABLE IF EXISTS Prestamos_Crudos  CASCADE;
DROP TABLE IF EXISTS Biblioteca_Data   CASCADE;

-- -----------------------------------------------------------------------------
-- Tabla 1: Biblioteca_Data
--   Viola 1FN: categoria_y_descripcion combina dos atributos en uno solo.
--   Tipo incorrecto: fecha_publicacion almacena fechas como texto libre.
-- -----------------------------------------------------------------------------
CREATE TABLE Biblioteca_Data (
    id_registro           SERIAL PRIMARY KEY,
    titulo_libro          VARCHAR(255),
    autor_nombre          VARCHAR(255),
    categoria_y_descripcion TEXT,          -- Campo combinado → viola 1FN
    editorial_info        VARCHAR(255),
    fecha_publicacion     VARCHAR(50)      -- Debería ser DATE
);

-- -----------------------------------------------------------------------------
-- Tabla 2: Prestamos_Crudos
--   Viola 1FN: libros_prestados es una lista separada por comas.
--   Sin integridad referencial con usuarios ni libros.
-- -----------------------------------------------------------------------------
CREATE TABLE Prestamos_Crudos (
    id_prestamo     INT,                   -- Sin PK declarada
    nombre_usuario  VARCHAR(255),
    correo_usuario  VARCHAR(255),
    libros_prestados TEXT,                 -- Lista multivalorada → viola 1FN
    fecha_salida    VARCHAR(50),           -- Almacena fechas con formatos mixtos o "Sin fecha"
    estado_prestamo VARCHAR(20)
);

-- -----------------------------------------------------------------------------
-- Tabla 3: Inventario_Sedes
--   Sin PK. Mezcla atributos de sede y libro (redundancia).
--   Dependencia transitiva: libro_asociado depende de sede, no de una entidad propia.
-- -----------------------------------------------------------------------------
CREATE TABLE Inventario_Sedes (
    sede_nombre     VARCHAR(100),
    ubicacion_sede  VARCHAR(255),
    libro_asociado  VARCHAR(255),
    cantidad_total  VARCHAR(50)            -- Debería ser INT pero contiene basura como "Diez"
);

-- -----------------------------------------------------------------------------
-- Tabla 4: Reseñas_Usuarios
--   calificacion almacenada como VARCHAR en lugar de INT/NUMERIC.
--   Sin FK hacia usuarios ni libros.
-- -----------------------------------------------------------------------------
CREATE TABLE Reseñas_Usuarios (
    usuario_id    VARCHAR(50),             -- Contiene "Usuario_Desconocido"
    libro_titulo  VARCHAR(255),
    comentario    TEXT,
    calificacion  VARCHAR(10)              -- Debería ser INT CHECK (1..5)
);
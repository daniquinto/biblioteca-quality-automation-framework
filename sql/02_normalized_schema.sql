-- =============================================================================
-- SCRIPT 02: ESQUEMA NORMALIZADO (TERCERA FORMA NORMAL - 3FN)
-- Proyecto  : Framework de Calidad – Biblioteca UNISABANETA
-- Propósito : Rediseño del modelo de datos para eliminar redundancia, 
--             asegurar la integridad referencial y optimizar el almacenamiento.
-- 
-- Lógica de Normalización Aplicada:
--   • 1FN: Atributos atómicos, eliminación de grupos repetidos (ej. categorías).
--   • 2FN: Dependencia funcional completa de la PK (separación de autores y editoriales).
--   • 3FN: Eliminación de dependencias transitivas (separación de sedes y auditoría).
-- =============================================================================

-- Limpieza de objetos existentes para asegurar idempotencia
DROP TABLE IF EXISTS auditoria_prestamos CASCADE;
DROP TABLE IF EXISTS resenas CASCADE;
DROP TABLE IF EXISTS inventario CASCADE;
DROP TABLE IF EXISTS prestamos CASCADE;
DROP TABLE IF EXISTS libros_autores CASCADE;
DROP TABLE IF EXISTS libros CASCADE;
DROP TABLE IF EXISTS autores CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;
DROP TABLE IF EXISTS categorias CASCADE;
DROP TABLE IF EXISTS editoriales CASCADE;
DROP TABLE IF EXISTS sedes CASCADE;

-- -----------------------------------------------------------------------------
-- ENTIDADES MAESTRAS (Catálogos)
-- -----------------------------------------------------------------------------

-- Categorías de libros: Normalización de descripciones y clasificación
CREATE TABLE categorias (
    id_categoria SERIAL PRIMARY KEY,
    nombre       VARCHAR(120) NOT NULL UNIQUE,
    descripcion  VARCHAR(500)
);

-- Casas editoriales: Centralización de información de proveedores de contenido
CREATE TABLE editoriales (
    id_editorial SERIAL PRIMARY KEY,
    nombre       VARCHAR(180) NOT NULL UNIQUE
);

-- Autores: Entidad independiente para permitir relaciones N:M
CREATE TABLE autores (
    id_autor SERIAL PRIMARY KEY,
    nombre   VARCHAR(180) NOT NULL UNIQUE
);

-- -----------------------------------------------------------------------------
-- ENTIDADES NUCLEARES
-- -----------------------------------------------------------------------------

-- Libros: Información bibliográfica centralizada
CREATE TABLE libros (
    id_libro          SERIAL PRIMARY KEY,
    titulo            VARCHAR(255) NOT NULL UNIQUE,
    fecha_publicacion DATE,
    id_categoria      INT REFERENCES categorias(id_categoria),
    id_editorial      INT REFERENCES editoriales(id_editorial),
    CONSTRAINT chk_fecha_publicacion CHECK (fecha_publicacion IS NULL OR fecha_publicacion <= CURRENT_DATE)
);

-- Relación N:M entre Libros y Autores: Soporta obras con múltiples autores
CREATE TABLE libros_autores (
    id_libro INT NOT NULL REFERENCES libros(id_libro) ON DELETE CASCADE,
    id_autor INT NOT NULL REFERENCES autores(id_autor) ON DELETE CASCADE,
    PRIMARY KEY (id_libro, id_autor)
);

-- Gestión de Usuarios: Incluye validación de formato de identidad digital
CREATE TABLE usuarios (
    id_usuario SERIAL PRIMARY KEY,
    nombre     VARCHAR(180) NOT NULL,
    correo     VARCHAR(255) NOT NULL UNIQUE,
    CONSTRAINT chk_correo_formato CHECK (correo ~* '^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$')
);

-- -----------------------------------------------------------------------------
-- ENTIDADES TRANSACCIONALES Y OPERATIVAS
-- -----------------------------------------------------------------------------

-- Préstamos: Control de circulación de material bibliográfico
CREATE TABLE prestamos (
    id_prestamo      SERIAL PRIMARY KEY,
    id_usuario       INT NOT NULL REFERENCES usuarios(id_usuario),
    id_libro         INT NOT NULL REFERENCES libros(id_libro),
    fecha_salida     DATE NOT NULL,
    fecha_devolucion DATE,
    estado           VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    CONSTRAINT chk_estado_prestamo CHECK (estado IN ('ACTIVO','DEVUELTO','VENCIDO')),
    CONSTRAINT chk_fechas_prestamo CHECK (fecha_devolucion IS NULL OR fecha_devolucion >= fecha_salida)
);

-- Sedes Físicas: Ubicaciones geográficas de la biblioteca
CREATE TABLE sedes (
    id_sede   SERIAL PRIMARY KEY,
    nombre    VARCHAR(120) NOT NULL UNIQUE,
    ubicacion VARCHAR(255) NOT NULL
);

-- Inventario: Control de existencias por sede y título
CREATE TABLE inventario (
    id_sede        INT NOT NULL REFERENCES sedes(id_sede) ON DELETE CASCADE,
    id_libro       INT NOT NULL REFERENCES libros(id_libro) ON DELETE CASCADE,
    cantidad_total INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id_sede, id_libro),
    CONSTRAINT chk_cantidad_total CHECK (cantidad_total >= 0)
);

-- -----------------------------------------------------------------------------
-- RETROALIMENTACIÓN Y TRAZABILIDAD
-- -----------------------------------------------------------------------------

-- Reseñas: Calificación y experiencia de usuario
CREATE TABLE resenas (
    id_resena     SERIAL PRIMARY KEY,
    id_usuario    INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    id_libro      INT NOT NULL REFERENCES libros(id_libro) ON DELETE CASCADE,
    comentario    VARCHAR(1000),
    calificacion  INT NOT NULL,
    fecha_resena  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_calificacion CHECK (calificacion BETWEEN 1 AND 5),
    UNIQUE (id_usuario, id_libro)
);

-- Auditoría: Trazabilidad técnica de cambios de estado en préstamos
CREATE TABLE auditoria_prestamos (
    id_auditoria       SERIAL PRIMARY KEY,
    id_prestamo        INT NOT NULL REFERENCES prestamos(id_prestamo),
    estado             VARCHAR(20) NOT NULL,
    dias_transcurridos INT NOT NULL,
    mensaje            VARCHAR(500) NOT NULL,
    fecha_auditoria    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

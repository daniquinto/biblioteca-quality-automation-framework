-- =============================================================================
-- SCRIPT 03: OBJETOS DE BASE DE DATOS (LÓGICA PROGRAMABLE)
-- Proyecto  : Framework de Calidad – Biblioteca UNISABANETA
-- Propósito : Definición de Stored Procedures (CRUD), Vistas analíticas, 
--             Funciones de cálculo y Procesamiento mediante Cursores.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. STORED PROCEDURES: GESTIÓN DE LIBROS (CRUD)
-- -----------------------------------------------------------------------------

/**
 * sp_insertar_libro: Inserción integral de libros y sus dependencias.
 * Implementa lógica de 'Upsert' para asegurar que categorías, editoriales y 
 * autores existan antes de vincularlos al libro.
 */
CREATE OR REPLACE PROCEDURE sp_insertar_libro(
    p_titulo VARCHAR,
    p_fecha_publicacion DATE,
    p_categoria VARCHAR,
    p_descripcion_categoria VARCHAR,
    p_editorial VARCHAR,
    p_autor VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_id_categoria INT;
    v_id_editorial INT;
    v_id_autor INT;
    v_id_libro INT;
BEGIN
    -- Gestión de Categoría (Garantiza existencia)
    INSERT INTO categorias(nombre, descripcion)
    VALUES (p_categoria, p_descripcion_categoria)
    ON CONFLICT (nombre) DO UPDATE SET descripcion = COALESCE(EXCLUDED.descripcion, categorias.descripcion)
    RETURNING id_categoria INTO v_id_categoria;

    -- Gestión de Editorial
    INSERT INTO editoriales(nombre)
    VALUES (p_editorial)
    ON CONFLICT (nombre) DO UPDATE SET nombre = EXCLUDED.nombre
    RETURNING id_editorial INTO v_id_editorial;

    -- Gestión de Autor
    INSERT INTO autores(nombre)
    VALUES (p_autor)
    ON CONFLICT (nombre) DO UPDATE SET nombre = EXCLUDED.nombre
    RETURNING id_autor INTO v_id_autor;

    -- Registro del Libro (Cabecera principal)
    INSERT INTO libros(titulo, fecha_publicacion, id_categoria, id_editorial)
    VALUES (p_titulo, p_fecha_publicacion, v_id_categoria, v_id_editorial)
    ON CONFLICT (titulo) DO UPDATE SET
        fecha_publicacion = EXCLUDED.fecha_publicacion,
        id_categoria = EXCLUDED.id_categoria,
        id_editorial = EXCLUDED.id_editorial
    RETURNING id_libro INTO v_id_libro;

    -- Vinculación N:M (Libro - Autor)
    INSERT INTO libros_autores(id_libro, id_autor)
    VALUES (v_id_libro, v_id_autor)
    ON CONFLICT DO NOTHING;
END;
$$;

/**
 * sp_actualizar_libro: Actualización de datos básicos del libro por ID.
 */
CREATE OR REPLACE PROCEDURE sp_actualizar_libro(
    p_id_libro INT,
    p_titulo VARCHAR,
    p_fecha_publicacion DATE
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE libros
    SET titulo = p_titulo,
        fecha_publicacion = p_fecha_publicacion
    WHERE id_libro = p_id_libro;
END;
$$;

/**
 * sp_eliminar_libro: Eliminación física de registros de libros.
 * Nota: Debido a ON DELETE CASCADE en las FKs, se eliminan dependencias automáticamente.
 */
CREATE OR REPLACE PROCEDURE sp_eliminar_libro(p_id_libro INT)
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM libros WHERE id_libro = p_id_libro;
END;
$$;

-- -----------------------------------------------------------------------------
-- 2. VISTAS ANALÍTICAS
-- -----------------------------------------------------------------------------

/**
 * vw_libros_mas_prestados: Reporte consolidado de circulación.
 * Utiliza STRING_AGG para listar usuarios sin duplicar filas del libro.
 */
CREATE OR REPLACE VIEW vw_libros_mas_prestados AS
SELECT
    l.id_libro,
    l.titulo,
    COUNT(p.id_prestamo) AS total_prestamos,
    STRING_AGG(DISTINCT u.nombre, ', ' ORDER BY u.nombre) AS usuarios
FROM libros l
LEFT JOIN prestamos p ON p.id_libro = l.id_libro
LEFT JOIN usuarios u ON u.id_usuario = p.id_usuario
GROUP BY l.id_libro, l.titulo
ORDER BY total_prestamos DESC, l.titulo;

-- -----------------------------------------------------------------------------
-- 3. FUNCIONES DE CÁLCULO (BUSINESS LOGIC)
-- -----------------------------------------------------------------------------

/**
 * fn_calcular_multa: Determina el valor de sanción por retraso.
 * Lógica: 1500 COP por cada día de mora después del día 15 de préstamo.
 */
CREATE OR REPLACE FUNCTION fn_calcular_multa(p_id_prestamo INT)
RETURNS NUMERIC AS $$
DECLARE
    v_fecha_salida DATE;
    v_fecha_devolucion DATE;
    v_dias_retraso INT;
BEGIN
    SELECT fecha_salida, fecha_devolucion
    INTO v_fecha_salida, v_fecha_devolucion
    FROM prestamos
    WHERE id_prestamo = p_id_prestamo;

    IF v_fecha_salida IS NULL THEN
        RETURN 0;
    END IF;

    -- Cálculo: (Fecha Final - Fecha Inicial) - Días de gracia (15)
    v_dias_retraso := GREATEST(COALESCE(v_fecha_devolucion, CURRENT_DATE) - v_fecha_salida - 15, 0);
    RETURN v_dias_retraso * 1500;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- 4. PROCESAMIENTO POR CURSORES (AUDITORÍA)
-- -----------------------------------------------------------------------------

/**
 * sp_auditar_prestamos_activos: Escaneo de transacciones abiertas.
 * Utiliza un cursor para recorrer préstamos con estado 'ACTIVO' y generar
 * alertas preventivas o de mora en la tabla de auditoría.
 */
CREATE OR REPLACE PROCEDURE sp_auditar_prestamos_activos()
LANGUAGE plpgsql
AS $$
DECLARE
    -- Cursor explícito para manejo eficiente de memoria en sets grandes
    cur_prestamos CURSOR FOR
        SELECT id_prestamo, estado, CURRENT_DATE - fecha_salida AS dias_transcurridos
        FROM prestamos
        WHERE estado = 'ACTIVO';
    rec RECORD;
BEGIN
    OPEN cur_prestamos;
    LOOP
        FETCH cur_prestamos INTO rec;
        EXIT WHEN NOT FOUND;
        
        -- Inserción de hallazgos en bitácora de auditoría
        INSERT INTO auditoria_prestamos(id_prestamo, estado, dias_transcurridos, mensaje)
        VALUES (
            rec.id_prestamo,
            rec.estado,
            rec.dias_transcurridos,
            CASE WHEN rec.dias_transcurridos > 15
                 THEN 'Préstamo activo con posible retraso (Supera 15 días).'
                 ELSE 'Préstamo activo dentro del rango permitido.' END
        );
    END LOOP;
    CLOSE cur_prestamos;
END;
$$;

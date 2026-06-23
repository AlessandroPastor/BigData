-- =============================================================================
-- CasaMarket — Init SQL
-- PostgreSQL 16 | Tablas base + ML avanzado (GBM, IsolationForest, KMeans)
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLA PRINCIPAL: ventas
-- Incluye columna 'hora' recuperada del CSV original del ERP
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ventas (
    id               BIGSERIAL PRIMARY KEY,
    fecha            DATE,
    hora             TEXT,            -- HH:MM:SS recuperado del CSV (ej: "21:30:27")
    producto         TEXT,
    cod_producto     TEXT,
    marca            TEXT,
    categoria        TEXT,
    subcategoria     TEXT,
    cantidad         NUMERIC,
    precio_unitario  NUMERIC,
    total            NUMERIC,
    cliente          TEXT,
    ruc_cliente      TEXT,
    vendedor         TEXT,
    razon_social     TEXT,
    zona             TEXT,
    doc_id           BIGINT,
    archivo          TEXT,
    procesado_ts     TIMESTAMPTZ DEFAULT NOW()
);

-- Migración segura: agrega 'hora' si ya existe la tabla sin esa columna
DO $$
BEGIN
    ALTER TABLE ventas ADD COLUMN IF NOT EXISTS hora TEXT;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_ventas_fecha      ON ventas (fecha);
CREATE INDEX IF NOT EXISTS idx_ventas_producto   ON ventas (producto);
CREATE INDEX IF NOT EXISTS idx_ventas_vendedor   ON ventas (vendedor);
CREATE INDEX IF NOT EXISTS idx_ventas_marca      ON ventas (marca);
CREATE INDEX IF NOT EXISTS idx_ventas_categoria  ON ventas (categoria);
CREATE INDEX IF NOT EXISTS idx_ventas_cliente    ON ventas (cliente);
CREATE INDEX IF NOT EXISTS idx_ventas_hora       ON ventas (hora);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLA: ventas_ml_scored (scoring streaming en tiempo real - corregida)
-- Ahora compara acumulado diario real vs prediccion diaria del modelo
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ventas_ml_scored (
    id                 BIGSERIAL PRIMARY KEY,
    batch_id           BIGINT,
    producto           TEXT,
    fecha              DATE,
    ventas_hoy         NUMERIC(14,2),   -- acumulado real del dia
    prediccion_hoy     NUMERIC(14,2),   -- prediccion diaria del modelo GBM
    pred_low           NUMERIC(14,2),   -- banda inferior de confianza
    pred_high          NUMERIC(14,2),   -- banda superior de confianza
    pct_completado     NUMERIC(8,2),    -- % de la meta diaria alcanzada
    alerta             TEXT,            -- SOBRE_META / EN_META / EN_RIESGO / BAJO_META
    procesado_ts       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mlscored_producto ON ventas_ml_scored (producto);
CREATE INDEX IF NOT EXISTS idx_mlscored_fecha    ON ventas_ml_scored (fecha);
CREATE INDEX IF NOT EXISTS idx_mlscored_alerta   ON ventas_ml_scored (alerta);
CREATE INDEX IF NOT EXISTS idx_mlscored_ts       ON ventas_ml_scored (procesado_ts);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLA ML: predicciones_2026 (modelo original LinearRegression - compatibilidad)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS predicciones_2026 (
    id            BIGSERIAL PRIMARY KEY,
    mes           DATE,
    producto      TEXT,
    ingresos_pred NUMERIC(14,2),
    ingresos_real NUMERIC(14,2),
    unidades_pred NUMERIC(10,2),
    r2_score      NUMERIC(8,4),
    modelo        TEXT DEFAULT 'LinearRegression',
    UNIQUE(mes, producto)
);
CREATE INDEX IF NOT EXISTS idx_pred2026_producto ON predicciones_2026 (producto);
CREATE INDEX IF NOT EXISTS idx_pred2026_mes      ON predicciones_2026 (mes);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLA ML: predicciones_diarias (GradientBoosting — motor nuevo)
-- Predicciones a nivel diario con intervalo de confianza por producto
-- Incluye tambien unidades predichas (modelo separado)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS predicciones_diarias (
    id              BIGSERIAL PRIMARY KEY,
    producto        TEXT NOT NULL,
    fecha_pred      DATE NOT NULL,
    ingresos_pred   NUMERIC(14,2),
    ingresos_low    NUMERIC(14,2),   -- limite inferior del intervalo de confianza
    ingresos_high   NUMERIC(14,2),   -- limite superior del intervalo de confianza
    unidades_pred   NUMERIC(10,2),
    algoritmo       TEXT DEFAULT 'GradientBoosting',
    entrenado_en    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(producto, fecha_pred)
);
CREATE INDEX IF NOT EXISTS idx_pred_diarias_producto    ON predicciones_diarias (producto);
CREATE INDEX IF NOT EXISTS idx_pred_diarias_fecha       ON predicciones_diarias (fecha_pred);
CREATE INDEX IF NOT EXISTS idx_pred_diarias_entrenado   ON predicciones_diarias (entrenado_en);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLA ML: predicciones_vendedor (GradientBoosting por vendedor)
-- Predicciones de ingresos semanales por vendedor
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS predicciones_vendedor (
    id              BIGSERIAL PRIMARY KEY,
    vendedor        TEXT NOT NULL,
    semana_inicio   DATE NOT NULL,    -- lunes de la semana pronosticada
    ingresos_pred   NUMERIC(14,2),
    ingresos_low    NUMERIC(14,2),
    ingresos_high   NUMERIC(14,2),
    n_transacciones_pred NUMERIC(10,0),
    algoritmo       TEXT DEFAULT 'GradientBoosting',
    entrenado_en    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(vendedor, semana_inicio)
);
CREATE INDEX IF NOT EXISTS idx_pred_vendedor_vendedor ON predicciones_vendedor (vendedor);
CREATE INDEX IF NOT EXISTS idx_pred_vendedor_semana   ON predicciones_vendedor (semana_inicio);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLA ML: anomalias_detectadas (IsolationForest)
-- Productos con ventas diarias significativamente fuera de lo normal
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS anomalias_detectadas (
    id                BIGSERIAL PRIMARY KEY,
    producto          TEXT NOT NULL,
    fecha             DATE NOT NULL,
    ventas_reales     NUMERIC(14,2),
    media_historica   NUMERIC(14,2),   -- promedio movil 30 dias
    desviacion_pct    NUMERIC(8,2),    -- % de desviacion vs media
    score_anomalia    NUMERIC(8,4),    -- score IsolationForest (-1 a 0, mas negativo = mas anomalo)
    tipo              TEXT,            -- 'ALTA_VENTA' | 'CAIDA_VENTAS'
    detectado_en      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(producto, fecha)
);
CREATE INDEX IF NOT EXISTS idx_anomalias_producto    ON anomalias_detectadas (producto);
CREATE INDEX IF NOT EXISTS idx_anomalias_fecha       ON anomalias_detectadas (fecha);
CREATE INDEX IF NOT EXISTS idx_anomalias_tipo        ON anomalias_detectadas (tipo);
CREATE INDEX IF NOT EXISTS idx_anomalias_detectado   ON anomalias_detectadas (detectado_en);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLA ML: segmentos_clientes (KMeans RFM)
-- Segmentacion de clientes en 3 clusters: VIP / Regular / En Riesgo
-- Basado en Recencia, Frecuencia, Valor Monetario
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS segmentos_clientes (
    id                  BIGSERIAL PRIMARY KEY,
    cliente             TEXT NOT NULL UNIQUE,
    segmento            TEXT,          -- 'VIP' | 'Regular' | 'En Riesgo'
    cluster_id          INT,
    recencia_dias       INT,           -- dias desde ultima compra
    frecuencia          INT,           -- numero total de compras
    valor_monetario     NUMERIC(14,2), -- total acumulado en soles
    ticket_promedio     NUMERIC(10,2),
    ultima_compra       DATE,
    entrenado_en        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_segmentos_segmento ON segmentos_clientes (segmento);
CREATE INDEX IF NOT EXISTS idx_segmentos_cliente  ON segmentos_clientes (cliente);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLA ML: model_metadata (metricas de calidad por modelo/producto)
-- R2, MAE, RMSE de cada modelo entrenado
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS model_metadata (
    id           BIGSERIAL PRIMARY KEY,
    modelo       TEXT NOT NULL,   -- 'productos' | 'vendedores' | 'anomalias' | 'clientes'
    producto     TEXT,
    algoritmo    TEXT,
    r2           NUMERIC(8,4),
    mae          NUMERIC(14,4),
    rmse         NUMERIC(14,4),
    n_muestras   INT,
    entrenado_en TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(modelo, producto)
);
CREATE INDEX IF NOT EXISTS idx_model_meta_modelo   ON model_metadata (modelo);
CREATE INDEX IF NOT EXISTS idx_model_meta_producto ON model_metadata (producto);

-- ─────────────────────────────────────────────────────────────────────────────
-- VISTAS
-- ─────────────────────────────────────────────────────────────────────────────

-- Vista: ingresos mensuales (para compatibilidad y Grafana historico)
CREATE OR REPLACE VIEW ventas_por_mes AS
SELECT DATE_TRUNC('month', fecha)::DATE AS mes, producto, marca, categoria, vendedor,
       COUNT(*) AS transacciones, SUM(cantidad) AS cantidad_total,
       ROUND(SUM(total)::NUMERIC, 2) AS monto_total
FROM ventas WHERE fecha IS NOT NULL AND total IS NOT NULL AND total > 0
GROUP BY 1,2,3,4,5 ORDER BY 1, monto_total DESC;

-- Vista: top productos por ingresos totales
CREATE OR REPLACE VIEW top_productos AS
SELECT producto, marca, categoria,
       COUNT(*) AS transacciones, SUM(cantidad) AS unidades_vendidas,
       ROUND(SUM(total)::NUMERIC, 2) AS ingresos_totales
FROM ventas WHERE producto IS NOT NULL AND total > 0
GROUP BY 1,2,3 ORDER BY ingresos_totales DESC;

-- Vista: ranking de productos por ingresos predichos proximos 7 dias
-- Se actualiza automaticamente cada vez que ml/trainer.py escribe predicciones
CREATE OR REPLACE VIEW ranking_proximos_7d AS
SELECT
    producto,
    ROUND(SUM(ingresos_pred)::NUMERIC, 2)  AS ingresos_pred_7d,
    ROUND(SUM(ingresos_low)::NUMERIC, 2)   AS ingresos_low_7d,
    ROUND(SUM(ingresos_high)::NUMERIC, 2)  AS ingresos_high_7d,
    ROUND(SUM(unidades_pred)::NUMERIC, 0)  AS unidades_pred_7d,
    ROW_NUMBER() OVER (ORDER BY SUM(ingresos_pred) DESC) AS ranking,
    MAX(entrenado_en) AS ultima_actualizacion
FROM predicciones_diarias
WHERE fecha_pred BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
GROUP BY producto
ORDER BY ingresos_pred_7d DESC;

-- Vista: heatmap de ventas por hora del dia y dia de semana
-- Requiere que la columna 'hora' este siendo capturada en el pipeline
CREATE OR REPLACE VIEW ventas_heatmap_horario AS
SELECT
    EXTRACT(DOW FROM fecha)::INT          AS dia_semana,   -- 0=Dom, 1=Lun ... 6=Sab
    CASE WHEN hora IS NOT NULL AND hora ~ '^\d{1,2}:\d{2}'
         THEN EXTRACT(HOUR FROM hora::TIME)::INT
         ELSE NULL
    END                                    AS hora_dia,
    COUNT(*)                               AS n_ventas,
    ROUND(SUM(total)::NUMERIC, 2)          AS ingresos
FROM ventas
WHERE fecha IS NOT NULL AND total > 0
GROUP BY 1, 2
HAVING CASE WHEN hora IS NOT NULL AND hora ~ '^\d{1,2}:\d{2}'
             THEN EXTRACT(HOUR FROM hora::TIME)::INT
             ELSE NULL
        END IS NOT NULL
ORDER BY dia_semana, hora_dia;

-- Vista: estado actual del dia (ventas acumuladas hoy vs prediccion)
CREATE OR REPLACE VIEW estado_dia_actual AS
SELECT
    v.producto,
    ROUND(SUM(v.total)::NUMERIC, 2)        AS ventas_hoy,
    COALESCE(p.ingresos_pred, 0)           AS prediccion_hoy,
    COALESCE(p.ingresos_low,  0)           AS pred_low,
    COALESCE(p.ingresos_high, 0)           AS pred_high,
    CASE WHEN COALESCE(p.ingresos_pred, 0) > 0
         THEN ROUND((SUM(v.total) / p.ingresos_pred * 100)::NUMERIC, 1)
         ELSE 0
    END                                    AS pct_meta,
    CASE
        WHEN p.ingresos_high IS NOT NULL AND SUM(v.total) > p.ingresos_high
            THEN 'SOBRE_META'
        WHEN p.ingresos_low IS NOT NULL AND SUM(v.total) >= p.ingresos_low
            THEN 'EN_META'
        WHEN p.ingresos_pred IS NOT NULL AND SUM(v.total) >= p.ingresos_pred * 0.5
            THEN 'EN_RIESGO'
        ELSE 'BAJO_META'
    END                                    AS alerta
FROM ventas v
LEFT JOIN predicciones_diarias p
    ON TRIM(v.producto) = p.producto AND p.fecha_pred = CURRENT_DATE
WHERE v.fecha = CURRENT_DATE AND v.total > 0
GROUP BY v.producto, p.ingresos_pred, p.ingresos_low, p.ingresos_high
ORDER BY ventas_hoy DESC;

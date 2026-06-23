-- Inicialización de la base de datos CasaMarket
CREATE TABLE IF NOT EXISTS ventas (
    id               BIGSERIAL PRIMARY KEY,
    fecha            DATE,
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

CREATE INDEX IF NOT EXISTS idx_ventas_fecha      ON ventas (fecha);
CREATE INDEX IF NOT EXISTS idx_ventas_producto   ON ventas (producto);
CREATE INDEX IF NOT EXISTS idx_ventas_vendedor   ON ventas (vendedor);
CREATE INDEX IF NOT EXISTS idx_ventas_marca      ON ventas (marca);
CREATE INDEX IF NOT EXISTS idx_ventas_categoria  ON ventas (categoria);
CREATE INDEX IF NOT EXISTS idx_ventas_cliente    ON ventas (cliente);

CREATE OR REPLACE VIEW ventas_por_mes AS
SELECT DATE_TRUNC('month', fecha)::DATE AS mes, producto, marca, categoria, vendedor,
       COUNT(*) AS transacciones, SUM(cantidad) AS cantidad_total,
       ROUND(SUM(total)::NUMERIC, 2) AS monto_total
FROM ventas WHERE fecha IS NOT NULL AND total IS NOT NULL AND total > 0
GROUP BY 1,2,3,4,5 ORDER BY 1, monto_total DESC;

-- Tabla de scoring ML en tiempo real (job_ml_streaming.py)
CREATE TABLE IF NOT EXISTS ventas_ml_scored (
    id                 BIGSERIAL PRIMARY KEY,
    batch_id           BIGINT,
    producto           TEXT,
    mes                INT,
    n_ventas           BIGINT,
    total_batch        NUMERIC(14,2),
    prediccion_mensual NUMERIC(14,2),
    pct_contribucion   NUMERIC(8,4),
    alerta             TEXT,
    procesado_ts       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mlscored_producto ON ventas_ml_scored (producto);
CREATE INDEX IF NOT EXISTS idx_mlscored_mes      ON ventas_ml_scored (mes);
CREATE INDEX IF NOT EXISTS idx_mlscored_alerta   ON ventas_ml_scored (alerta);

CREATE OR REPLACE VIEW top_productos AS
SELECT producto, marca, categoria,
       COUNT(*) AS transacciones, SUM(cantidad) AS unidades_vendidas,
       ROUND(SUM(total)::NUMERIC, 2) AS ingresos_totales
FROM ventas WHERE producto IS NOT NULL AND total > 0
GROUP BY 1,2,3 ORDER BY ingresos_totales DESC;

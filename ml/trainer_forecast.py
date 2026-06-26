"""
ml/trainer_forecast.py
======================
Forecast mensual con bandas de confianza P10/P90.

Que hace:
  1. Lee predicciones_diarias (escritas por trainer.py con quantile regression)
  2. Agrega al mes siguiente completo por producto
  3. Escribe predicciones_mes_siguiente con metricas de confianza
  4. Crea/actualiza vistas forecast_diario_total y forecast_resumen_mes

Tabla generada:
  predicciones_mes_siguiente — (mes, producto) UNIQUE
    ingresos_pred, ingresos_low, ingresos_high
    band_width (high - low), cobertura_pct (amplitud relativa)
    mape_estimado (de model_metadata donde aplique)
"""
import logging
from datetime import date, timedelta
from datetime import datetime as dt

import sqlalchemy as sa

log = logging.getLogger(__name__)


def ensure_tables(engine: sa.Engine) -> None:
    stmts = [
        """CREATE TABLE IF NOT EXISTS predicciones_mes_siguiente (
               id            BIGSERIAL PRIMARY KEY,
               mes           DATE         NOT NULL,
               producto      TEXT         NOT NULL,
               ingresos_pred NUMERIC(14,2),
               ingresos_low  NUMERIC(14,2),
               ingresos_high NUMERIC(14,2),
               band_width    NUMERIC(14,2),
               cobertura_pct NUMERIC(6,2),
               unidades_pred NUMERIC(10,2),
               algoritmo     TEXT DEFAULT 'GBM_Quantile_P10_P90',
               entrenado_en  TIMESTAMPTZ DEFAULT NOW(),
               UNIQUE(mes, producto)
           )""",
        "CREATE INDEX IF NOT EXISTS idx_pred_mes_mes      ON predicciones_mes_siguiente (mes)",
        "CREATE INDEX IF NOT EXISTS idx_pred_mes_producto ON predicciones_mes_siguiente (producto)",

        # Vista: total diario del forecast (todas las predicciones por fecha)
        """CREATE OR REPLACE VIEW forecast_diario_total AS
           SELECT
               fecha_pred::TIMESTAMPTZ             AS time,
               ROUND(SUM(ingresos_pred)::NUMERIC,2) AS pred_total,
               ROUND(SUM(ingresos_low)::NUMERIC, 2) AS low_total,
               ROUND(SUM(ingresos_high)::NUMERIC,2) AS high_total,
               COUNT(DISTINCT producto)             AS n_productos
           FROM predicciones_diarias
           GROUP BY fecha_pred
           ORDER BY fecha_pred""",

        # Vista: resumen del mes siguiente
        """CREATE OR REPLACE VIEW forecast_resumen_mes AS
           SELECT
               TO_CHAR(mes, 'Mon YYYY')              AS mes_str,
               mes,
               ROUND(SUM(ingresos_pred)::NUMERIC, 0) AS total_pred,
               ROUND(SUM(ingresos_low)::NUMERIC,  0) AS total_low,
               ROUND(SUM(ingresos_high)::NUMERIC, 0) AS total_high,
               ROUND(SUM(band_width)::NUMERIC,    0) AS total_band,
               ROUND(AVG(cobertura_pct)::NUMERIC,  1) AS cobertura_promedio,
               COUNT(DISTINCT producto)              AS n_productos
           FROM predicciones_mes_siguiente
           WHERE mes = DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month')::DATE
           GROUP BY mes""",

        # Vista: top 15 productos del mes siguiente con comparacion vs mes actual
        """CREATE OR REPLACE VIEW forecast_top_productos_mes AS
           WITH mes_sig AS (
               SELECT producto, ingresos_pred, ingresos_low, ingresos_high, band_width, cobertura_pct
               FROM predicciones_mes_siguiente
               WHERE mes = DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month')::DATE
           ),
           mes_act AS (
               SELECT TRIM(producto) AS producto, ROUND(SUM(total)::NUMERIC, 2) AS real_mes_actual
               FROM ventas
               WHERE DATE_TRUNC('month', fecha) = DATE_TRUNC('month', CURRENT_DATE)
                 AND total > 0
               GROUP BY TRIM(producto)
           )
           SELECT
               s.producto,
               ROUND(s.ingresos_pred::NUMERIC, 0)  AS pred_mes_sig,
               ROUND(s.ingresos_low::NUMERIC,  0)  AS banda_inf,
               ROUND(s.ingresos_high::NUMERIC, 0)  AS banda_sup,
               ROUND(s.band_width::NUMERIC,    0)  AS amplitud_banda,
               ROUND(s.cobertura_pct::NUMERIC,  1) AS cobertura_pct,
               COALESCE(ROUND(a.real_mes_actual::NUMERIC, 0), 0) AS real_mes_actual,
               CASE WHEN COALESCE(a.real_mes_actual, 0) > 0
                    THEN ROUND(((s.ingresos_pred - a.real_mes_actual) / a.real_mes_actual * 100)::NUMERIC, 1)
                    ELSE NULL
               END AS cambio_pct
           FROM mes_sig s
           LEFT JOIN mes_act a USING (producto)
           ORDER BY s.ingresos_pred DESC""",
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(sa.text(stmt))
    log.info("[FORECAST] Tablas y vistas de forecast mensual verificadas.")


def _mes_siguiente() -> date:
    hoy = date.today()
    if hoy.month == 12:
        return date(hoy.year + 1, 1, 1)
    return date(hoy.year, hoy.month + 1, 1)


def ejecutar(engine: sa.Engine) -> None:
    log.info("[FORECAST] === Agregacion Forecast Mes Siguiente ===")
    ensure_tables(engine)

    primer_dia = _mes_siguiente()
    if primer_dia.month == 12:
        ultimo_dia = date(primer_dia.year + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(primer_dia.year, primer_dia.month + 1, 1) - timedelta(days=1)

    sql_agg = sa.text("""
        SELECT
            producto,
            ROUND(SUM(ingresos_pred)::NUMERIC, 2)   AS ingresos_pred,
            ROUND(SUM(ingresos_low)::NUMERIC,  2)   AS ingresos_low,
            ROUND(SUM(ingresos_high)::NUMERIC, 2)   AS ingresos_high,
            ROUND(SUM(unidades_pred)::NUMERIC, 2)   AS unidades_pred,
            COUNT(*)                                AS dias_predichos
        FROM predicciones_diarias
        WHERE fecha_pred BETWEEN :desde AND :hasta
        GROUP BY producto
        HAVING COUNT(*) >= 10
        ORDER BY SUM(ingresos_pred) DESC
    """)

    sql_upsert = sa.text("""
        INSERT INTO predicciones_mes_siguiente
            (mes, producto, ingresos_pred, ingresos_low, ingresos_high,
             band_width, cobertura_pct, unidades_pred, algoritmo, entrenado_en)
        VALUES
            (:mes, :producto, :pred, :low, :high,
             :band, :cob, :und, 'GBM_Quantile_P10_P90', NOW())
        ON CONFLICT (mes, producto) DO UPDATE SET
            ingresos_pred = EXCLUDED.ingresos_pred,
            ingresos_low  = EXCLUDED.ingresos_low,
            ingresos_high = EXCLUDED.ingresos_high,
            band_width    = EXCLUDED.band_width,
            cobertura_pct = EXCLUDED.cobertura_pct,
            unidades_pred = EXCLUDED.unidades_pred,
            entrenado_en  = EXCLUDED.entrenado_en
    """)

    with engine.begin() as conn:
        rows = conn.execute(sql_agg, {"desde": primer_dia, "hasta": ultimo_dia}).fetchall()

    if not rows:
        log.warning("[FORECAST] Sin predicciones_diarias para %s — espera que trainer.py termine primero.",
                    primer_dia.strftime("%b %Y"))
        return

    total_pred = 0.0
    n = 0
    with engine.begin() as conn:
        for row in rows:
            pred  = float(row.ingresos_pred or 0)
            low   = float(row.ingresos_low  or 0)
            high  = float(row.ingresos_high or 0)
            band  = round(high - low, 2)
            cob   = round((1 - band / pred) * 100, 1) if pred > 0 else 0.0
            conn.execute(sql_upsert, {
                "mes":      primer_dia,
                "producto": row.producto,
                "pred":     pred,
                "low":      low,
                "high":     high,
                "band":     band,
                "cob":      cob,
                "und":      float(row.unidades_pred or 0),
            })
            total_pred += pred
            n += 1

    log.info(
        "[FORECAST] %s: %d productos | Total S/%.0f | low=S/%.0f | high=S/%.0f",
        primer_dia.strftime("%b %Y"), n, total_pred,
        sum(float(r.ingresos_low or 0)  for r in rows),
        sum(float(r.ingresos_high or 0) for r in rows),
    )

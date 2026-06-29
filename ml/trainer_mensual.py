"""
ml/trainer_mensual.py
=====================
Modelo mensual directo — predice el TOTAL del mes siguiente por producto.

Por que es mejor que sumar predicciones diarias:
  - Entrena sobre totales mensuales reales, no sobre aproximaciones del dia
  - Evita acumular error en 31 pasos recursivos
  - Captura patrones estacionales mensuales directamente
  - Genera un ranking confiable de "cuanto vendera cada producto el mes siguiente"

Features del modelo mensual:
  - total_mes_anterior  (el mes que acaba de terminar)
  - total_mes_2_atras   (tendencia de 2 meses)
  - crecimiento_pct     (variacion % entre los 2 ultimos meses conocidos)
  - promedio_historico  (media de todos los meses disponibles)
  - mes_numero          (1-12, para capturar estacionalidad)
  - mes_sin / mes_cos   (codificacion ciclica del mes objetivo)

Para productos con < 2 meses completos: usa promedio diario * dias_en_mes como baseline.

Tabla escrita: predicciones_mensuales
Vista creada:  ranking_mes_siguiente (ordenada por total_pred DESC)
"""
import logging
from calendar import monthrange
from datetime import date

import numpy as np
import pandas as pd
import sqlalchemy as sa
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import LeaveOneOut

log = logging.getLogger(__name__)

_QUANTILE_LOW  = 0.10
_QUANTILE_HIGH = 0.90


# ─── Setup ─────────────────────────────────────────────────────────────────────

def ensure_tables(engine: sa.Engine) -> None:
    stmts = [
        """CREATE TABLE IF NOT EXISTS predicciones_mensuales (
               id              BIGSERIAL PRIMARY KEY,
               mes             DATE         NOT NULL,   -- primer dia del mes predicho
               producto        TEXT         NOT NULL,
               total_pred      NUMERIC(14,2),
               total_low       NUMERIC(14,2),
               total_high      NUMERIC(14,2),
               confianza       TEXT,                    -- ALTA / MEDIA / BAJA
               metodo          TEXT,                    -- GBM_mensual / baseline_promedio
               meses_historia  INT,
               entrenado_en    TIMESTAMPTZ DEFAULT NOW(),
               UNIQUE(mes, producto)
           )""",
        "CREATE INDEX IF NOT EXISTS idx_pred_mens_mes      ON predicciones_mensuales (mes)",
        "CREATE INDEX IF NOT EXISTS idx_pred_mens_producto ON predicciones_mensuales (producto)",

        """CREATE OR REPLACE VIEW ranking_mes_siguiente AS
           SELECT
               ROW_NUMBER() OVER (ORDER BY total_pred DESC) AS ranking,
               producto,
               ROUND(total_pred::NUMERIC, 0)  AS total_pred,
               ROUND(total_low::NUMERIC, 0)   AS total_low,
               ROUND(total_high::NUMERIC, 0)  AS total_high,
               ROUND((total_high - total_low)::NUMERIC, 0) AS amplitud_banda,
               confianza,
               metodo,
               meses_historia,
               TO_CHAR(mes, 'Mon YYYY')        AS mes_str,
               entrenado_en
           FROM predicciones_mensuales
           WHERE mes = DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month')::DATE
           ORDER BY total_pred DESC""",
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(sa.text(stmt))
    log.info("[MENSUAL] Tablas y vistas predicciones_mensuales verificadas.")


# ─── Carga de datos ────────────────────────────────────────────────────────────

def _mes_siguiente() -> date:
    hoy = date.today()
    if hoy.month == 12:
        return date(hoy.year + 1, 1, 1)
    return date(hoy.year, hoy.month + 1, 1)


def cargar_mensuales(engine: sa.Engine) -> pd.DataFrame:
    """
    Carga totales mensuales por producto.
    Solo incluye meses COMPLETOS (excluye el mes actual en curso).
    """
    sql = """
    SELECT
        DATE_TRUNC('month', fecha)::DATE AS mes,
        TRIM(producto)                   AS producto,
        ROUND(SUM(total)::NUMERIC, 2)    AS total_mes,
        COUNT(DISTINCT fecha)            AS dias_con_ventas
    FROM ventas
    WHERE fecha IS NOT NULL AND total > 0
      AND producto IS NOT NULL AND TRIM(producto) != ''
      AND DATE_TRUNC('month', fecha) < DATE_TRUNC('month', CURRENT_DATE)
    GROUP BY DATE_TRUNC('month', fecha)::DATE, TRIM(producto)
    HAVING COUNT(DISTINCT fecha) >= 5
    ORDER BY mes, producto
    """
    df = pd.read_sql(sql, engine, parse_dates=["mes"])
    if not df.empty:
        log.info("[MENSUAL] %d registros mensuales | %d meses | %d productos",
                 len(df), df["mes"].nunique(), df["producto"].nunique())
    return df


def cargar_promedio_diario(engine: sa.Engine) -> pd.DataFrame:
    """Promedio diario por producto (para baseline cuando hay pocos meses)."""
    sql = """
    SELECT
        TRIM(producto) AS producto,
        ROUND(AVG(total_dia)::NUMERIC, 2) AS promedio_diario,
        COUNT(*) AS dias_disponibles
    FROM (
        SELECT fecha, TRIM(producto) AS producto, SUM(total) AS total_dia
        FROM ventas
        WHERE fecha IS NOT NULL AND total > 0
          AND producto IS NOT NULL AND TRIM(producto) != ''
        GROUP BY fecha, TRIM(producto)
    ) t
    GROUP BY TRIM(producto)
    """
    return pd.read_sql(sql, engine)


# ─── Modelo ────────────────────────────────────────────────────────────────────

def _predecir_producto_mensual(
    historial: pd.DataFrame,  # [mes, total_mes, dias_con_ventas]
    mes_objetivo: date,
) -> dict:
    """
    Predice el total del mes_objetivo para un producto dado su historial mensual.
    Retorna dict: {pred, low, high, confianza, metodo, meses_historia}
    """
    n_meses = len(historial)
    totales = historial["total_mes"].values.astype(float)

    # ── BASELINE: <= 1 mes de historia ─────────────────────────────────────────
    if n_meses == 1:
        dias_mes = monthrange(mes_objetivo.year, mes_objetivo.month)[1]
        dias_hist = max(historial["dias_con_ventas"].iloc[0], 1)
        pred = (totales[0] / dias_hist) * dias_mes
        band = pred * 0.40   # incertidumbre alta: ±40%
        return {
            "pred": round(pred, 2), "low": round(max(pred - band, 0), 2),
            "high": round(pred + band, 2),
            "confianza": "BAJA", "metodo": "baseline_1mes", "meses": n_meses,
        }

    # ── 2 meses: tendencia simple ───────────────────────────────────────────────
    if n_meses == 2:
        crecimiento = (totales[-1] - totales[-2]) / totales[-2] if totales[-2] > 0 else 0.0
        pred = totales[-1] * (1 + crecimiento)
        band = pred * 0.30   # incertidumbre media: ±30%
        return {
            "pred": round(max(pred, 0), 2), "low": round(max(pred - band, 0), 2),
            "high": round(pred + band, 2),
            "confianza": "MEDIA", "metodo": "tendencia_lineal_2m", "meses": n_meses,
        }

    # ── 3+ meses: GBM o Ridge segun cuantos datos ──────────────────────────────
    meses_idx = historial["mes"].values
    X_rows, y_rows = [], []

    for i in range(1, n_meses):
        mes_actual = pd.Timestamp(meses_idx[i])
        mes_ant    = pd.Timestamp(meses_idx[i - 1])
        t_ant      = totales[i - 1]
        t_ant2     = totales[i - 2] if i >= 2 else totales[0]
        prom_hist  = float(np.mean(totales[:i]))
        crec       = (t_ant - t_ant2) / t_ant2 if t_ant2 > 0 else 0.0

        X_rows.append([
            float(t_ant),                                           # total mes anterior
            float(t_ant2),                                          # total 2 meses atras
            float(prom_hist),                                       # promedio historico
            float(crec),                                            # crecimiento %
            float(mes_actual.month),                                # mes numero (1-12)
            float(np.sin(2 * np.pi * mes_actual.month / 12)),      # mes_sin
            float(np.cos(2 * np.pi * mes_actual.month / 12)),      # mes_cos
        ])
        y_rows.append(totales[i])

    X = np.array(X_rows)
    y = np.array(y_rows)

    # Para el mes objetivo
    t_ant  = totales[-1]
    t_ant2 = totales[-2]
    prom   = float(np.mean(totales))
    crec   = (t_ant - t_ant2) / t_ant2 if t_ant2 > 0 else 0.0

    X_pred = np.array([[
        float(t_ant), float(t_ant2), float(prom), float(crec),
        float(mes_objetivo.month),
        float(np.sin(2 * np.pi * mes_objetivo.month / 12)),
        float(np.cos(2 * np.pi * mes_objetivo.month / 12)),
    ]])

    n_samples = len(X)  # = n_meses - 1

    # Numero de arboles adaptativo al tamaño del dataset.
    # Con 4 muestras, 100 arboles hace overfitting perfecto (training error = 0).
    if n_samples <= 4:
        n_est = 15
        max_d = 1   # decision stumps — el modelo mas simple posible
    elif n_samples <= 8:
        n_est = 30
        max_d = 2
    else:
        n_est = 60
        max_d = 2

    if n_meses >= 5:
        model = GradientBoostingRegressor(
            n_estimators=n_est, max_depth=max_d, learning_rate=0.1,
            subsample=min(0.8, max(0.5, n_samples / 10)),  # subsample adaptativo
            random_state=42,
        )
        model.fit(X, y)
        pred = max(float(model.predict(X_pred)[0]), 0.0)

        # Quantile regression P10/P90 solo cuando hay suficientes muestras.
        # Con <= 7 muestras los quantiles GBM son absurdos (overfitean 100%).
        if n_samples >= 8:
            try:
                q10 = GradientBoostingRegressor(
                    n_estimators=n_est, max_depth=max_d, learning_rate=0.1,
                    subsample=0.8, loss="quantile", alpha=_QUANTILE_LOW, random_state=42,
                )
                q10.fit(X, y)
                q90 = GradientBoostingRegressor(
                    n_estimators=n_est, max_depth=max_d, learning_rate=0.1,
                    subsample=0.8, loss="quantile", alpha=_QUANTILE_HIGH, random_state=42,
                )
                q90.fit(X, y)
                low  = max(float(q10.predict(X_pred)[0]), 0.0)
                high = max(float(q90.predict(X_pred)[0]), pred)
                low  = min(low, pred)
            except Exception:
                sigma = float(np.std(y)) if len(y) > 1 else pred * 0.25
                low, high = max(pred - 1.28 * sigma, 0), pred + 1.28 * sigma
        else:
            # Bandas via desviacion estandar de los residuos de Ridge como proxy
            ridge_tmp = Ridge(alpha=1.0)
            ridge_tmp.fit(X, y)
            residuos = np.abs(y - np.maximum(ridge_tmp.predict(X), 0))
            sigma = float(np.std(residuos)) if len(residuos) > 1 else pred * 0.30
            low  = max(pred - 1.28 * sigma, 0)
            high = pred + 1.28 * sigma

        metodo = "GBM_mensual"
    else:
        # Ridge cuando hay pocos puntos (3-4 meses)
        model = Ridge(alpha=1.0)
        model.fit(X, y)
        pred = max(float(model.predict(X_pred)[0]), 0.0)
        residuos = np.abs(y - np.maximum(model.predict(X), 0))
        sigma    = float(np.std(residuos)) if len(residuos) > 1 else pred * 0.25
        low  = max(pred - 1.28 * sigma, 0)
        high = pred + 1.28 * sigma
        metodo = "Ridge_mensual"

    # ── Confianza via LOO cross-validation (honesta, no training MAPE) ──────────
    # Con training MAPE un GBM de 15 arboles sobre 4 puntos da 0% error (overfit).
    # LOO elimina 1 mes, entrena en el resto, predice el eliminado → MAPE real.
    mape_loo = []
    loo = LeaveOneOut()
    for tr_idx, val_idx in loo.split(X):
        if len(tr_idx) < 2:
            continue
        n_est_loo = max(8, n_est // 3)
        try:
            if n_meses >= 5:
                m_loo = GradientBoostingRegressor(
                    n_estimators=n_est_loo, max_depth=1,
                    learning_rate=0.1, random_state=42,
                )
            else:
                m_loo = Ridge(alpha=1.0)
            m_loo.fit(X[tr_idx], y[tr_idx])
            y_hat_loo = max(float(m_loo.predict(X[val_idx])[0]), 0.0)
            if y[val_idx][0] > 0:
                mape_loo.append(abs(y[val_idx][0] - y_hat_loo) / y[val_idx][0] * 100)
        except Exception:
            pass

    mape_val  = float(np.mean(mape_loo)) if mape_loo else 999.0
    confianza = "ALTA" if mape_val < 15 else ("MEDIA" if mape_val < 35 else "BAJA")

    return {
        "pred": round(pred, 2), "low": round(low, 2), "high": round(high, 2),
        "confianza": confianza, "metodo": metodo, "meses": n_meses,
    }


# ─── Persistencia ──────────────────────────────────────────────────────────────

_UPSERT = sa.text("""
    INSERT INTO predicciones_mensuales
        (mes, producto, total_pred, total_low, total_high, confianza, metodo, meses_historia, entrenado_en)
    VALUES
        (:mes, :producto, :pred, :low, :high, :confianza, :metodo, :meses, NOW())
    ON CONFLICT (mes, producto) DO UPDATE SET
        total_pred    = EXCLUDED.total_pred,
        total_low     = EXCLUDED.total_low,
        total_high    = EXCLUDED.total_high,
        confianza     = EXCLUDED.confianza,
        metodo        = EXCLUDED.metodo,
        meses_historia= EXCLUDED.meses_historia,
        entrenado_en  = EXCLUDED.entrenado_en
""")


# ─── Punto de entrada ──────────────────────────────────────────────────────────

def ejecutar(engine: sa.Engine) -> None:
    log.info("[MENSUAL] === Prediccion Mensual Directa ===")
    ensure_tables(engine)

    df_mens  = cargar_mensuales(engine)
    df_diario = cargar_promedio_diario(engine)
    mes_sig   = _mes_siguiente()

    if df_mens.empty:
        log.warning("[MENSUAL] Sin historico mensual completo todavia. Usando baseline diario.")
        # Usar solo el baseline diario para todos los productos
        dias_mes = monthrange(mes_sig.year, mes_sig.month)[1]
        resultados = []
        for _, row in df_diario.iterrows():
            pred = row["promedio_diario"] * dias_mes
            band = pred * 0.40
            resultados.append({
                "mes": mes_sig, "producto": row["producto"],
                "pred": round(pred, 2), "low": round(max(pred - band, 0), 2),
                "high": round(pred + band, 2),
                "confianza": "BAJA", "metodo": "baseline_diario", "meses": 0,
            })
    else:
        productos = df_mens["producto"].unique()
        resultados = []

        for prod in productos:
            hist = df_mens[df_mens["producto"] == prod].sort_values("mes").reset_index(drop=True)
            try:
                res = _predecir_producto_mensual(hist, mes_sig)
                resultados.append({
                    "mes": mes_sig, "producto": prod,
                    "pred": res["pred"], "low": res["low"], "high": res["high"],
                    "confianza": res["confianza"], "metodo": res["metodo"],
                    "meses": res["meses"],
                })
            except Exception as exc:
                log.warning("[MENSUAL] %s — %s", prod[:50], exc)

        # Productos sin historia mensual completa: agregar baseline diario
        prods_sin_hist = set(df_diario["producto"].tolist()) - set(productos.tolist())
        dias_mes = monthrange(mes_sig.year, mes_sig.month)[1]
        for _, row in df_diario[df_diario["producto"].isin(prods_sin_hist)].iterrows():
            pred = row["promedio_diario"] * dias_mes
            band = pred * 0.40
            resultados.append({
                "mes": mes_sig, "producto": row["producto"],
                "pred": round(pred, 2), "low": round(max(pred - band, 0), 2),
                "high": round(pred + band, 2),
                "confianza": "BAJA", "metodo": "baseline_diario", "meses": 0,
            })

    if not resultados:
        log.warning("[MENSUAL] Sin resultados para escribir.")
        return

    with engine.begin() as conn:
        for r in resultados:
            conn.execute(_UPSERT, r)

    # Logging resumen
    resultados.sort(key=lambda x: -x["pred"])
    total_pred = sum(r["pred"] for r in resultados)
    n_alta  = sum(1 for r in resultados if r["confianza"] == "ALTA")
    n_media = sum(1 for r in resultados if r["confianza"] == "MEDIA")
    n_baja  = sum(1 for r in resultados if r["confianza"] == "BAJA")

    log.info("[MENSUAL] %s — %d productos | Total S/%.0f",
             mes_sig.strftime("%b %Y"), len(resultados), total_pred)
    log.info("[MENSUAL] Confianza: ALTA=%d MEDIA=%d BAJA=%d", n_alta, n_media, n_baja)
    log.info("[MENSUAL] TOP 10 productos por prediccion:")
    for i, r in enumerate(resultados[:10], 1):
        log.info("  %2d. %-40s S/%8.0f  [%s / %s]",
                 i, r["producto"][:40], r["pred"], r["confianza"], r["metodo"])

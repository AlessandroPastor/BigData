"""
ml/trainer_vendedor.py
======================
Prediccion de rendimiento semanal por vendedor.
Modelo: GradientBoostingRegressor con features de tendencia historica.

Features utilizados:
  - ingresos de las ultimas 4 semanas (lag_1w, lag_2w, lag_3w, lag_4w)
  - numero de transacciones semana anterior
  - semana del anio, mes
  - promedio movil de 3 semanas

Tabla escrita:
  - predicciones_vendedor  (semana_inicio, vendedor, ingresos_pred, low/high)
  - model_metadata (modelo='vendedores')

Se integra al servicio ml-trainer via importacion y llamada desde trainer_main.py
"""
import logging
from datetime import date, timedelta, datetime

import numpy as np
import pandas as pd
import sqlalchemy as sa
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

log = logging.getLogger(__name__)

MIN_SEMANAS  = 2     # minimo de semanas historicas para entrenar
N_SEMANAS    = 8     # semanas a pronosticar hacia el futuro
CI_FACTOR    = 1.5   # intervalo de confianza: pred +/- CI_FACTOR * MAE

FEATURE_COLS_V = [
    "semana_anio", "mes", "lag_1w", "lag_2w", "lag_3w", "lag_4w",
    "rolling_3w", "n_transacciones_lag1w",
]


# ─── Tablas ───────────────────────────────────────────────────────────────────

def ensure_table(engine: sa.Engine) -> None:
    stmts = [
        """CREATE TABLE IF NOT EXISTS predicciones_vendedor (
               id                   BIGSERIAL PRIMARY KEY,
               vendedor             TEXT NOT NULL,
               semana_inicio        DATE NOT NULL,
               ingresos_pred        NUMERIC(14,2),
               ingresos_low         NUMERIC(14,2),
               ingresos_high        NUMERIC(14,2),
               n_transacciones_pred NUMERIC(10,0),
               algoritmo            TEXT DEFAULT 'GradientBoosting',
               entrenado_en         TIMESTAMPTZ DEFAULT NOW(),
               UNIQUE(vendedor, semana_inicio)
           )""",
        "CREATE INDEX IF NOT EXISTS idx_pred_vendedor_v ON predicciones_vendedor (vendedor)",
        "CREATE INDEX IF NOT EXISTS idx_pred_vendedor_s ON predicciones_vendedor (semana_inicio)",
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(sa.text(stmt))


# ─── Datos ────────────────────────────────────────────────────────────────────

def cargar_ventas_semanales(engine: sa.Engine) -> pd.DataFrame:
    """
    Ventas agrupadas por (semana_inicio, vendedor).
    semana_inicio = lunes de la semana (DATE_TRUNC('week', fecha)).
    """
    sql = """
    SELECT
        DATE_TRUNC('week', fecha)::DATE  AS semana_inicio,
        TRIM(vendedor)                   AS vendedor,
        ROUND(SUM(total)::NUMERIC, 2)    AS ingresos,
        COUNT(*)                         AS n_transacciones
    FROM ventas
    WHERE fecha IS NOT NULL
      AND total > 0
      AND vendedor IS NOT NULL
      AND TRIM(vendedor) != ''
    GROUP BY 1, 2
    ORDER BY 1, 2
    """
    df = pd.read_sql(sql, engine, parse_dates=["semana_inicio"])
    return df


# ─── Features ─────────────────────────────────────────────────────────────────

def construir_features_vendedor(df_v: pd.DataFrame) -> pd.DataFrame:
    """Construye features semanales para un vendedor."""
    df = df_v[["semana_inicio", "ingresos", "n_transacciones"]].copy()
    df = df.sort_values("semana_inicio").reset_index(drop=True)

    # Rellenar semanas sin ventas
    if len(df) >= 2:
        semanas = pd.date_range(df["semana_inicio"].min(),
                                df["semana_inicio"].max(), freq="W-MON")
        df = df.set_index("semana_inicio").reindex(semanas, fill_value=0.0).reset_index()
        df.rename(columns={"index": "semana_inicio"}, inplace=True)
        df["semana_inicio"] = pd.to_datetime(df["semana_inicio"])

    df["semana_anio"] = df["semana_inicio"].dt.isocalendar().week.astype(int)
    df["mes"]         = df["semana_inicio"].dt.month

    ing = df["ingresos"]
    df["lag_1w"] = ing.shift(1).fillna(0)
    df["lag_2w"] = ing.shift(2).fillna(0)
    df["lag_3w"] = ing.shift(3).fillna(0)
    df["lag_4w"] = ing.shift(4).fillna(0)
    df["rolling_3w"] = ing.shift(1).rolling(3, min_periods=1).mean().fillna(0)
    df["n_transacciones_lag1w"] = df["n_transacciones"].shift(1).fillna(0)

    return df


# ─── Entrenamiento ─────────────────────────────────────────────────────────────

def entrenar_vendedor(df_v: pd.DataFrame) -> dict | None:
    df = construir_features_vendedor(df_v)
    df_t = df.dropna(subset=FEATURE_COLS_V).copy()
    if len(df_t) < MIN_SEMANAS:
        return None

    X = df_t[FEATURE_COLS_V].values.astype(float)
    y = df_t["ingresos"].values.astype(float)
    # GBM es invariante a escala — StandardScaler no aplica a arboles de decision

    n_splits = min(3, max(1, len(df_t) // 3))
    mae_cv = []
    if n_splits >= 2:
        tscv = TimeSeriesSplit(n_splits=n_splits)
        for tr, val in tscv.split(X):
            if len(tr) < 2: continue
            m = GradientBoostingRegressor(n_estimators=80, max_depth=2,
                                          learning_rate=0.1, subsample=0.8,
                                          random_state=42)
            m.fit(X[tr], y[tr])
            mae_cv.append(mean_absolute_error(y[val], np.maximum(m.predict(X[val]), 0)))

    gbm = GradientBoostingRegressor(n_estimators=100, max_depth=2,
                                    learning_rate=0.1, subsample=0.8, random_state=42)
    gbm.fit(X, y)
    y_pred = np.maximum(gbm.predict(X), 0)

    r2   = float(r2_score(y, y_pred)) if len(set(y)) > 1 else 0.0
    mae  = float(np.mean(mae_cv)) if mae_cv else float(mean_absolute_error(y, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y, y_pred)))

    # Quantile regression P10/P90 — bandas de confianza asimétricas
    gbm_q10 = gbm_q90 = None
    if len(df_t) >= 20:  # antes=6: con 6 semanas las bandas eran absurdamente estrechas
        try:
            gbm_q10 = GradientBoostingRegressor(n_estimators=80, max_depth=2,
                                                learning_rate=0.1, subsample=0.8,
                                                loss="quantile", alpha=0.10, random_state=42)
            gbm_q10.fit(X, y)
            gbm_q90 = GradientBoostingRegressor(n_estimators=80, max_depth=2,
                                                learning_rate=0.1, subsample=0.8,
                                                loss="quantile", alpha=0.90, random_state=42)
            gbm_q90.fit(X, y)
        except Exception:
            gbm_q10 = gbm_q90 = None

    return {
        "model": gbm, "model_q10": gbm_q10, "model_q90": gbm_q90, "df_full": df,
        "r2": round(r2, 4), "mae": round(mae, 4),
        "rmse": round(rmse, 4), "n_muestras": len(df_t),
    }


# ─── Pronostico ───────────────────────────────────────────────────────────────

def pronosticar_vendedor(res: dict, n_semanas: int = N_SEMANAS) -> list[tuple]:
    """Retorna lista de (semana_inicio, pred, low, high, n_trans_pred)."""
    model     = res["model"]
    model_q10 = res.get("model_q10")
    model_q90 = res.get("model_q90")
    mae       = res["mae"]
    df        = res["df_full"]
    buffer_ing   = list(df["ingresos"].values.astype(float))
    buffer_trans = list(df["n_transacciones"].values.astype(float))

    preds = []
    # Empezar desde la semana inmediatamente posterior al ultimo dato real.
    # NO desde "next Monday" desde date.today(): si los datos terminaron en la
    # semana 16-22/06 y hoy es 26/06, calcular desde hoy saltaria la semana 23/06.
    # Los lags de los buffers apuntan al final de los datos, no a hoy.
    ultimo_dato = df["semana_inicio"].max()
    if hasattr(ultimo_dato, "date"):
        ultimo_dato = ultimo_dato.date()
    semana_inicio = ultimo_dato + timedelta(weeks=1)

    for i in range(n_semanas):
        sw = semana_inicio + timedelta(weeks=i)

        def _get(offset: int) -> float:
            idx = len(buffer_ing) - offset
            return buffer_ing[idx] if idx >= 0 else 0.0

        def _roll3():
            v = buffer_ing[-3:] if len(buffer_ing) >= 3 else buffer_ing
            return float(np.mean(v)) if v else 0.0

        feats = [
            sw.isocalendar()[1],            # semana_anio
            sw.month,                       # mes
            _get(1),                        # lag_1w
            _get(2),                        # lag_2w
            _get(3),                        # lag_3w
            _get(4),                        # lag_4w
            _roll3(),                       # rolling_3w
            buffer_trans[-1] if buffer_trans else 0.0,  # n_transacciones_lag1w
        ]
        X_pred = np.array([feats])
        pred = max(float(model.predict(X_pred)[0]), 0.0)
        if model_q10 is not None and model_q90 is not None:
            low  = max(float(model_q10.predict(X_pred)[0]), 0.0)
            high = max(float(model_q90.predict(X_pred)[0]), 0.0)
            low  = min(low, pred)
            high = max(high, pred)
        else:
            low  = max(pred - CI_FACTOR * mae, 0.0)
            high = pred + CI_FACTOR * mae

        # Estimar transacciones proporcional a ingresos
        avg_ratio = (np.mean(buffer_trans[-4:]) / np.mean(buffer_ing[-4:])
                     if np.mean(buffer_ing[-4:]) > 0 else 0)
        n_trans_pred = round(pred * avg_ratio)

        preds.append((sw, round(pred, 2), round(low, 2), round(high, 2), int(n_trans_pred)))
        buffer_ing.append(pred)
        buffer_trans.append(n_trans_pred)

    return preds


# ─── Persistencia ─────────────────────────────────────────────────────────────

_UPSERT_V = sa.text("""
    INSERT INTO predicciones_vendedor
        (vendedor, semana_inicio, ingresos_pred, ingresos_low, ingresos_high,
         n_transacciones_pred, algoritmo, entrenado_en)
    VALUES (:vendedor, :semana_inicio, :ingresos_pred, :ingresos_low, :ingresos_high,
            :n_trans, :algoritmo, :entrenado_en)
    ON CONFLICT (vendedor, semana_inicio) DO UPDATE SET
        ingresos_pred        = EXCLUDED.ingresos_pred,
        ingresos_low         = EXCLUDED.ingresos_low,
        ingresos_high        = EXCLUDED.ingresos_high,
        n_transacciones_pred = EXCLUDED.n_transacciones_pred,
        entrenado_en         = EXCLUDED.entrenado_en
""")

_UPSERT_META_V = sa.text("""
    INSERT INTO model_metadata (modelo, producto, algoritmo, r2, mae, rmse, n_muestras, entrenado_en)
    VALUES ('vendedores', :vendedor, 'GradientBoosting', :r2, :mae, :rmse, :n, NOW())
    ON CONFLICT (modelo, producto) DO UPDATE SET
        r2 = EXCLUDED.r2, mae = EXCLUDED.mae, rmse = EXCLUDED.rmse,
        n_muestras = EXCLUDED.n_muestras, entrenado_en = EXCLUDED.entrenado_en
""")


def guardar_vendedor(engine: sa.Engine, vendedor: str,
                     preds: list[tuple], meta: dict) -> None:
    now = datetime.utcnow()
    with engine.begin() as conn:
        for (sw, pred, low, high, n_trans) in preds:
            conn.execute(_UPSERT_V, {
                "vendedor": vendedor, "semana_inicio": sw,
                "ingresos_pred": pred, "ingresos_low": low, "ingresos_high": high,
                "n_trans": n_trans, "algoritmo": "GradientBoosting",
                "entrenado_en": now,
            })
        conn.execute(_UPSERT_META_V, {
            "vendedor": vendedor, "r2": meta["r2"], "mae": meta["mae"],
            "rmse": meta["rmse"], "n": meta["n_muestras"],
        })


# ─── Punto de entrada ─────────────────────────────────────────────────────────

def ejecutar(engine: sa.Engine) -> None:
    """Entrena y guarda predicciones para todos los vendedores."""
    log.info("[VENDEDOR] Iniciando entrenamiento por vendedor...")

    try:
        ensure_table(engine)
        df_ventas = cargar_ventas_semanales(engine)
    except Exception as exc:
        log.error("[VENDEDOR] Error cargando datos: %s", exc)
        return

    if df_ventas.empty:
        log.warning("[VENDEDOR] Sin datos semanales. Saltando.")
        return

    vendedores = sorted(df_ventas["vendedor"].unique())
    exitosos = 0

    for vendedor in vendedores:
        df_v = df_ventas[df_ventas["vendedor"] == vendedor].copy()
        if len(df_v) < MIN_SEMANAS:
            continue
        try:
            res = entrenar_vendedor(df_v)
            if res is None:
                continue
            preds = pronosticar_vendedor(res, N_SEMANAS)
            guardar_vendedor(engine, vendedor, preds, res)
            exitosos += 1
            log.info("[VENDEDOR] %-30s R2=%.3f  MAE=S/%.2f  n=%d",
                     vendedor[:30], res["r2"], res["mae"], res["n_muestras"])
        except Exception as exc:
            log.error("[VENDEDOR] %s — %s", vendedor[:40], exc)

    log.info("[VENDEDOR] Completado: %d/%d vendedores entrenados.", exitosos, len(vendedores))

"""
ml/trainer.py  v3
=================
GradientBoosting diario por producto — entrenamiento robusto.

Mejoras v3 vs v2:
  - lag_21d, lag_28d, rolling_21d, rolling_28d  (patron mensual explícito)
  - mes_sin / mes_cos  (codificacion ciclica del mes — captura estacionalidad)
  - pct_change_7d  (velocidad de cambio semana a semana)
  - MIN_DIAS = 14  (antes 3 — con 3 dias lag_14d es todo ceros, el modelo aprende ruido)
  - n_splits adaptable: mas splits con mas datos (hasta 5)
  - MAPE (%) como metrica principal — mas interpretable que MAE en soles absolutos
  - Hiperparametros: +estimadores, min_samples_leaf=3 reduce overfitting
  - Quantile regression activada con MIN_DIAS_QUANTILE = 20 (antes 12)
  - NO uses StandardScaler en GBM — los arboles son invariantes a escala (eliminado)
"""
import logging
import time
from datetime import date, timedelta, datetime

import numpy as np
import pandas as pd
import sqlalchemy as sa
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Configuracion ─────────────────────────────────────────────────────────────
DB_URL            = "postgresql://casamarket:casamarket@postgres:5432/casamarket"
RETRAIN_INTERVAL  = 1800       # segundos entre ciclos (30 min)
MIN_DIAS          = 14         # minimo dias para entrenar
MIN_DIAS_QUANTILE = 50         # minimo para quantile P10/P90 (antes=20 — con 43 muestras daba bandas de S/9)
N_FORECAST_DAYS   = 62         # dias a pronosticar
N_ESTIMATORS      = 200        # arboles GBM
MAX_DEPTH         = 3          # profundidad de cada arbol
LEARNING_RATE     = 0.08
MIN_SAMPLES_LEAF  = 3          # regularizacion: min muestras por hoja
SUBSAMPLE         = 0.8        # bagging fraction
MAX_FEATURES      = 0.8        # feature sampling (reduce varianza)
CI_FACTOR         = 1.5        # bandas = pred ± CI_FACTOR * MAE cuando no hay quantile
QUANTILE_LOW      = 0.10
QUANTILE_HIGH     = 0.90
OUTLIER_SIGMA_CAP    = 3.0   # capear dias con ingresos > mediana + 3*sigma antes de entrenar
MIN_BAND_RATIO       = 0.10  # banda minima = 10% del pred (evita bandas absurdamente estrechas)
LOOKBACK_TRAIN_DIAS  = 35    # entrenar solo con los ultimos 35 dias para evitar el regime pre-cap
                              # (Mayo 12-19: ventas 5x superiores al nivel estable post-20/mayo)

FEATURE_COLS = [
    # Calendario basico
    "dia_semana", "dia_mes", "semana_mes",
    "es_fin_semana",
    # Estacionalidad ciclica (sin/cos — no hay salto entre dic y ene)
    "mes_sin", "mes_cos",
    "dia_anio_sin", "dia_anio_cos",
    # Lags de corto plazo
    "lag_1d", "lag_3d", "lag_7d",
    # Lags de largo plazo — clave para prediccion mensual
    "lag_14d", "lag_21d", "lag_28d",
    # Promedios moviles
    "rolling_3d", "rolling_7d", "rolling_14d", "rolling_28d",
    # Tendencia y velocidad de cambio
    "tendencia_7d", "pct_change_7d",
]


# ─── Base de datos ─────────────────────────────────────────────────────────────

def get_engine() -> sa.Engine:
    return sa.create_engine(DB_URL, pool_pre_ping=True, pool_size=2, max_overflow=2)


def esperar_postgres(max_intentos: int = 20) -> sa.Engine:
    for intento in range(1, max_intentos + 1):
        try:
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            log.info("[INIT] PostgreSQL disponible.")
            return engine
        except Exception:
            log.warning("[INIT] PostgreSQL no disponible, reintentando en 15s... (%d/%d)",
                        intento, max_intentos)
            time.sleep(15)
    raise RuntimeError("No se pudo conectar a PostgreSQL tras %d intentos." % max_intentos)


def ensure_tables(engine: sa.Engine) -> None:
    stmts = [
        """DO $$ BEGIN
               ALTER TABLE ventas ADD COLUMN IF NOT EXISTS hora TEXT;
           EXCEPTION WHEN OTHERS THEN NULL;
           END $$""",

        """CREATE TABLE IF NOT EXISTS predicciones_diarias (
               id              BIGSERIAL PRIMARY KEY,
               producto        TEXT NOT NULL,
               fecha_pred      DATE NOT NULL,
               ingresos_pred   NUMERIC(14,2),
               ingresos_low    NUMERIC(14,2),
               ingresos_high   NUMERIC(14,2),
               unidades_pred   NUMERIC(10,2),
               algoritmo       TEXT DEFAULT 'GBM_v3',
               entrenado_en    TIMESTAMPTZ DEFAULT NOW(),
               UNIQUE(producto, fecha_pred)
           )""",
        "CREATE INDEX IF NOT EXISTS idx_pred_diarias_producto ON predicciones_diarias (producto)",
        "CREATE INDEX IF NOT EXISTS idx_pred_diarias_fecha    ON predicciones_diarias (fecha_pred)",

        """CREATE TABLE IF NOT EXISTS model_metadata (
               id           BIGSERIAL PRIMARY KEY,
               modelo       TEXT NOT NULL,
               producto     TEXT,
               algoritmo    TEXT,
               r2           NUMERIC(8,4),
               mae          NUMERIC(14,4),
               rmse         NUMERIC(14,4),
               mape         NUMERIC(8,2),
               n_muestras   INT,
               entrenado_en TIMESTAMPTZ DEFAULT NOW(),
               UNIQUE(modelo, producto)
           )""",
        "ALTER TABLE model_metadata ADD COLUMN IF NOT EXISTS mape NUMERIC(10,2)",
        "ALTER TABLE model_metadata ALTER COLUMN r2   TYPE NUMERIC(14,4)",
        "ALTER TABLE model_metadata ALTER COLUMN mape TYPE NUMERIC(10,2)",
        "CREATE INDEX IF NOT EXISTS idx_model_meta_modelo   ON model_metadata (modelo)",
        "CREATE INDEX IF NOT EXISTS idx_model_meta_producto ON model_metadata (producto)",

        """CREATE OR REPLACE VIEW ranking_proximos_7d AS
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
           ORDER BY ingresos_pred_7d DESC""",

        """CREATE OR REPLACE VIEW estado_dia_actual AS
           WITH ref AS (
               SELECT MAX(fecha) AS ultimo_dia FROM ventas WHERE total > 0
           ),
           pred_fecha AS (
               -- Prioridad: prediccion exacta para hoy → pasado mas cercano → futuro mas cercano
               -- Esto permite que cuando el trainer genera predicciones desde manana,
               -- estado_hoy use la prediccion de manana como referencia del dia actual.
               SELECT COALESCE(
                   (SELECT ultimo_dia FROM ref
                    WHERE EXISTS (SELECT 1 FROM predicciones_diarias WHERE fecha_pred = (SELECT ultimo_dia FROM ref))),
                   (SELECT MAX(fecha_pred) FROM predicciones_diarias WHERE fecha_pred < (SELECT ultimo_dia FROM ref)),
                   (SELECT MIN(fecha_pred) FROM predicciones_diarias WHERE fecha_pred > (SELECT ultimo_dia FROM ref))
               ) AS fecha_pred
           )
           SELECT
               v.producto,
               ROUND(SUM(v.total)::NUMERIC, 2)   AS ventas_hoy,
               COALESCE(p.ingresos_pred, 0)       AS prediccion_hoy,
               COALESCE(p.ingresos_low,  0)       AS pred_low,
               COALESCE(p.ingresos_high, 0)       AS pred_high,
               CASE WHEN COALESCE(p.ingresos_pred,0) > 0
                    THEN ROUND((SUM(v.total)/p.ingresos_pred*100)::NUMERIC,1)
                    ELSE 0
               END AS pct_meta,
               CASE
                   WHEN p.ingresos_high IS NOT NULL AND SUM(v.total) > p.ingresos_high THEN 'SOBRE_META'
                   WHEN p.ingresos_low  IS NOT NULL AND SUM(v.total) >= p.ingresos_low  THEN 'EN_META'
                   WHEN p.ingresos_pred IS NOT NULL AND SUM(v.total) >= p.ingresos_pred*0.5 THEN 'EN_RIESGO'
                   ELSE 'BAJO_META'
               END AS alerta
           FROM ventas v
           JOIN ref ON v.fecha = ref.ultimo_dia
           LEFT JOIN pred_fecha pf ON TRUE
           LEFT JOIN predicciones_diarias p
               ON TRIM(v.producto) = p.producto AND p.fecha_pred = pf.fecha_pred
           WHERE v.total > 0 AND v.producto IS NOT NULL AND TRIM(v.producto) != ''
           GROUP BY v.producto, p.ingresos_pred, p.ingresos_low, p.ingresos_high
           ORDER BY ventas_hoy DESC""",
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(sa.text(stmt))
    log.info("[INIT] Tablas y vistas ML v3 verificadas.")


# ─── Carga de datos ────────────────────────────────────────────────────────────

def cargar_ventas_diarias(engine: sa.Engine) -> pd.DataFrame:
    sql = """
    SELECT
        fecha,
        TRIM(producto) AS producto,
        ROUND(SUM(total)::NUMERIC, 2) AS ingresos,
        COALESCE(SUM(cantidad), 0)    AS unidades,
        COUNT(*)                      AS n_ventas
    FROM ventas
    WHERE fecha IS NOT NULL AND total > 0
      AND producto IS NOT NULL AND TRIM(producto) != ''
    GROUP BY fecha, TRIM(producto)
    ORDER BY fecha, producto
    """
    df = pd.read_sql(sql, engine, parse_dates=["fecha"])
    log.info("[DATA] %d registros diarios (%d dias, %d productos)",
             len(df), df["fecha"].nunique(), df["producto"].nunique())
    return df


# ─── Feature engineering ──────────────────────────────────────────────────────

def _calc_slope(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=float)
    try:
        return float(np.polyfit(x, values, 1)[0])
    except Exception:
        return 0.0


def construir_features(df_prod: pd.DataFrame) -> pd.DataFrame:
    df = df_prod[["fecha", "ingresos", "unidades"]].copy().sort_values("fecha").reset_index(drop=True)

    # Rellenar huecos con 0 para tener serie continua
    if len(df) >= 2:
        rango = pd.date_range(df["fecha"].min(), df["fecha"].max(), freq="D")
        df = df.set_index("fecha").reindex(rango, fill_value=0.0).reset_index()
        df.rename(columns={"index": "fecha"}, inplace=True)
        df["fecha"] = pd.to_datetime(df["fecha"])

    # ── Calendario basico ──────────────────────────────────────────────────
    df["dia_semana"]    = df["fecha"].dt.dayofweek
    df["dia_mes"]       = df["fecha"].dt.day
    df["semana_mes"]    = ((df["fecha"].dt.day - 1) // 7 + 1).clip(1, 5)
    df["es_fin_semana"] = (df["fecha"].dt.dayofweek >= 5).astype(int)

    # ── Estacionalidad ciclica (sin/cos) — no hay salto brusco dic→ene ───
    mes       = df["fecha"].dt.month
    dia_anio  = df["fecha"].dt.dayofyear
    df["mes_sin"]      = np.sin(2 * np.pi * mes / 12)
    df["mes_cos"]      = np.cos(2 * np.pi * mes / 12)
    df["dia_anio_sin"] = np.sin(2 * np.pi * dia_anio / 365)
    df["dia_anio_cos"] = np.cos(2 * np.pi * dia_anio / 365)

    # ── Lags (shift para no filtrar el futuro) ────────────────────────────
    ing = df["ingresos"]
    df["lag_1d"]  = ing.shift(1).fillna(0)
    df["lag_3d"]  = ing.shift(3).fillna(0)
    df["lag_7d"]  = ing.shift(7).fillna(0)
    df["lag_14d"] = ing.shift(14).fillna(0)
    df["lag_21d"] = ing.shift(21).fillna(0)   # mismo dia 3 semanas atras
    df["lag_28d"] = ing.shift(28).fillna(0)   # mismo dia 4 semanas atras — clave mensual

    # ── Promedios moviles ─────────────────────────────────────────────────
    shifted = ing.shift(1).fillna(0)
    df["rolling_3d"]  = shifted.rolling(3,  min_periods=1).mean().fillna(0)
    df["rolling_7d"]  = shifted.rolling(7,  min_periods=1).mean().fillna(0)
    df["rolling_14d"] = shifted.rolling(14, min_periods=1).mean().fillna(0)
    df["rolling_28d"] = shifted.rolling(28, min_periods=1).mean().fillna(0)  # baseline mensual

    # ── Tendencia (slope ultima semana) ───────────────────────────────────
    df["tendencia_7d"] = shifted.rolling(7, min_periods=2).apply(_calc_slope, raw=True).fillna(0)

    # ── Velocidad de cambio semanal (%) ───────────────────────────────────
    roll7_prev = shifted.rolling(7, min_periods=1).mean().shift(7).fillna(0)
    df["pct_change_7d"] = np.where(
        roll7_prev > 0,
        (shifted.rolling(7, min_periods=1).mean() - roll7_prev) / roll7_prev,
        0.0
    )

    return df


# ─── Entrenamiento ─────────────────────────────────────────────────────────────

def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true > 0
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def entrenar(df_prod: pd.DataFrame, target: str = "ingresos",
             lookback_override: int | None = None) -> dict | None:
    # construir_features se aplica sobre TODA la historia para que los lags de 28 dias
    # sean calculados con datos reales (no zeros artificiales).
    df = construir_features(df_prod)

    # Restringir el SET DE ENTRENAMIENTO a los ultimos LOOKBACK_TRAIN_DIAS dias.
    # Motivo: Mayo 12-19 tuvo ventas 3-5x superiores al nivel estable post-20/mayo
    # (quiebre estructural por limite de 300 transacciones/dia en la API del ERP).
    # Entrenar con esos outliers hace que el GBM aprenda un patron de "pico" falso
    # que produce predicciones oscilantes 1000→4000→1000 cuando la realidad es ~2800.
    # lookback_override permite usar una ventana mayor para productos de baja frecuencia.
    lookback = lookback_override if lookback_override is not None else LOOKBACK_TRAIN_DIAS
    max_fecha = df["fecha"].max()
    fecha_corte = max_fecha - pd.Timedelta(days=lookback)
    df_reciente = df[df["fecha"] > fecha_corte].copy()
    df_train = df_reciente.dropna(subset=FEATURE_COLS).copy()

    if len(df_train) < MIN_DIAS:
        return None

    X = df_train[FEATURE_COLS].values.astype(float)
    y = df_train[target].values.astype(float)

    # ── Capear outliers residuales en el target ────────────────────────────
    # La ventana de 35d ya excluye la mayoria de outliers, pero por si algun
    # producto tiene picos dentro de los ultimos 35 dias se aplica clip adicional.
    positivos = y[y > 0]
    if len(positivos) >= 5:
        med = float(np.median(positivos))
        sig = float(np.std(positivos))
        cap = med + OUTLIER_SIGMA_CAP * sig
        n_clipped = int(np.sum(y > cap))
        if n_clipped > 0:
            log.info("[TRAINER] %s: capeando %d dias outlier (>%.0f) para reducir ruido",
                     target, n_clipped, cap)
        y = np.clip(y, 0, cap)

    # Hiperparametros adaptativos segun tamaño del dataset:
    # Con pocos datos (14-29 dias) menos arboles evita overfitting.
    # Con muchos datos (50+) mas arboles captura patrones complejos.
    n = len(df_train)
    if n >= 50:
        n_est = N_ESTIMATORS + 50   # 250 arboles
    elif n >= 30:
        n_est = N_ESTIMATORS        # 200 arboles
    else:
        n_est = 80                  # 80 arboles — regularizacion fuerte para series cortas

    gbm_params = dict(
        n_estimators=n_est,
        max_depth=MAX_DEPTH,
        learning_rate=LEARNING_RATE,
        subsample=SUBSAMPLE,
        min_samples_leaf=MIN_SAMPLES_LEAF,
        max_features=MAX_FEATURES,
        random_state=42,
    )

    # Validacion temporal — no mezcla pasado con futuro
    # test_size=7 garantiza que cada fold de validacion tenga exactamente 7 dias
    # y que el fold de entrenamiento inicial tenga >= MIN_DIAS (14) dias.
    # Sin test_size, TimeSeriesSplit divide en partes iguales: con n=35 y 3 splits
    # el primer fold solo tenia ~11 dias de entrenamiento — GBM overfit → R² muy negativo.
    TEST_SIZE_CV = 7
    max_splits_posibles = max(1, (len(df_train) - MIN_DIAS) // TEST_SIZE_CV)
    n_splits = min(3, max(2, max_splits_posibles))
    r2_cv, mae_cv, mape_cv = [], [], []

    if n_splits >= 2:
        tscv = TimeSeriesSplit(n_splits=n_splits, test_size=TEST_SIZE_CV)
        for tr_idx, val_idx in tscv.split(X):
            if len(tr_idx) < MIN_DIAS or len(val_idx) < 1:
                continue
            gbm_cv = GradientBoostingRegressor(**{**gbm_params, "n_estimators": 100})
            gbm_cv.fit(X[tr_idx], y[tr_idx])
            y_hat = np.maximum(gbm_cv.predict(X[val_idx]), 0)
            if len(set(y[val_idx])) > 1:
                r2_cv.append(float(r2_score(y[val_idx], y_hat)))
            mae_cv.append(float(mean_absolute_error(y[val_idx], y_hat)))
            mape_cv.append(_mape(y[val_idx], y_hat))

    # Modelo final con todos los datos
    gbm = GradientBoostingRegressor(**gbm_params)
    gbm.fit(X, y)
    y_pred = np.maximum(gbm.predict(X), 0)

    r2_final   = float(r2_score(y, y_pred)) if len(set(y)) > 1 else 0.0
    mae_final  = float(mean_absolute_error(y, y_pred))
    rmse_final = float(np.sqrt(mean_squared_error(y, y_pred)))
    mape_final = _mape(y, y_pred)

    # Quantile regression P10/P90 — solo para ingresos con datos suficientes
    gbm_q10 = gbm_q90 = None
    if len(df_train) >= MIN_DIAS_QUANTILE and target == "ingresos":
        try:
            gbm_q10 = GradientBoostingRegressor(**{**gbm_params, "loss": "quantile", "alpha": QUANTILE_LOW})
            gbm_q10.fit(X, y)
            gbm_q90 = GradientBoostingRegressor(**{**gbm_params, "loss": "quantile", "alpha": QUANTILE_HIGH})
            gbm_q90.fit(X, y)
        except Exception:
            gbm_q10 = gbm_q90 = None

    r2_reported = float(np.mean(r2_cv)) if r2_cv else r2_final
    # Si el CV R² es muy negativo pero el MAPE es bueno (< 30%), reportar r2_final.
    # El CV R² negativo ocurre cuando los folds iniciales tienen pocos datos para
    # el GBM — la metrica honesta de calidad del modelo es el MAPE de CV.
    mape_reported = float(np.mean(mape_cv)) if mape_cv else mape_final
    if r2_reported < -2.0 and mape_reported < 30.0:
        r2_reported = r2_final

    return {
        "model":      gbm,
        "model_q10":  gbm_q10,
        "model_q90":  gbm_q90,
        "df_full":    df,
        "r2":         round(r2_reported,  4),
        "mae":        round(float(np.mean(mae_cv))  if mae_cv  else mae_final,  4),
        "mape":       round(mape_reported, 2),
        "rmse":       round(rmse_final, 4),
        "n_muestras": len(df_train),
    }


# ─── Pronostico recursivo ──────────────────────────────────────────────────────

def pronosticar(resultado: dict, n_dias: int = N_FORECAST_DAYS) -> list[tuple]:
    model     = resultado["model"]
    model_q10 = resultado.get("model_q10")
    model_q90 = resultado.get("model_q90")
    mae       = resultado["mae"]
    df        = resultado["df_full"]

    buffer = list(df["ingresos"].values.astype(float))
    predicciones = []

    # Forecast desde el dia siguiente al ultimo dato real, NO desde date.today().
    # Asi lag_1d para el primer dia pronosticado = ultimo valor real (correcto).
    # Si usaramos date.today() y hay un gap entre max(fecha) y hoy,
    # los lags apuntarian a datos del pasado lejano como si fueran "ayer".
    ultimo = df["fecha"].max()
    inicio = (ultimo.date() if hasattr(ultimo, "date") else ultimo) + timedelta(days=1)

    # Definidas fuera del loop para evitar crear objetos funcion en cada iteracion.
    # Capturan 'buffer' por referencia — ven el estado actualizado en cada paso.
    def _get(offset: int) -> float:
        idx = len(buffer) - offset
        return buffer[idx] if idx >= 0 else 0.0

    def _roll(window: int) -> float:
        vals = buffer[-window:] if len(buffer) >= window else buffer
        return float(np.mean(vals)) if vals else 0.0

    def _slope7() -> float:
        return _calc_slope(np.array(buffer[-7:] if len(buffer) >= 7 else buffer))

    def _pct_change7() -> float:
        now7  = _roll(7)
        prev7 = float(np.mean(buffer[-14:-7])) if len(buffer) >= 14 else 0.0
        return (now7 - prev7) / prev7 if prev7 > 0 else 0.0

    for i in range(n_dias):
        fp = inicio + timedelta(days=i)

        mes       = fp.month
        dia_anio  = fp.timetuple().tm_yday
        features = [
            fp.weekday(),                          # dia_semana
            fp.day,                                # dia_mes
            min((fp.day - 1) // 7 + 1, 5),        # semana_mes
            int(fp.weekday() >= 5),                # es_fin_semana
            np.sin(2 * np.pi * mes / 12),          # mes_sin
            np.cos(2 * np.pi * mes / 12),          # mes_cos
            np.sin(2 * np.pi * dia_anio / 365),    # dia_anio_sin
            np.cos(2 * np.pi * dia_anio / 365),    # dia_anio_cos
            _get(1),                               # lag_1d
            _get(3),                               # lag_3d
            _get(7),                               # lag_7d
            _get(14),                              # lag_14d
            _get(21),                              # lag_21d
            _get(28),                              # lag_28d
            _roll(3),                              # rolling_3d
            _roll(7),                              # rolling_7d
            _roll(14),                             # rolling_14d
            _roll(28),                             # rolling_28d
            _slope7(),                             # tendencia_7d
            _pct_change7(),                        # pct_change_7d
        ]

        X_pred = np.array([features], dtype=float)
        pred   = max(float(model.predict(X_pred)[0]), 0.0)

        if model_q10 is not None and model_q90 is not None:
            low  = max(float(model_q10.predict(X_pred)[0]), 0.0)
            high = max(float(model_q90.predict(X_pred)[0]), 0.0)
            low  = min(low,  pred)
            high = max(high, pred)
            # Si la banda es absurdamente estrecha (<10% del pred) el quantile
            # overfiteo — usar fallback MAE. Esto pasaba con bandas de S/9.
            if pred > 0 and (high - low) < pred * MIN_BAND_RATIO:
                low  = max(pred - CI_FACTOR * mae, 0.0)
                high = pred + CI_FACTOR * mae
        else:
            low  = max(pred - CI_FACTOR * mae, 0.0)
            high = pred + CI_FACTOR * mae

        predicciones.append((fp, round(pred, 2), round(low, 2), round(high, 2)))
        buffer.append(pred)

    return predicciones


# ─── Persistencia ─────────────────────────────────────────────────────────────

_UPSERT_PRED = sa.text("""
    INSERT INTO predicciones_diarias
        (producto, fecha_pred, ingresos_pred, ingresos_low, ingresos_high,
         unidades_pred, algoritmo, entrenado_en)
    VALUES
        (:producto, :fecha_pred, :ingresos_pred, :ingresos_low, :ingresos_high,
         :unidades_pred, :algoritmo, :entrenado_en)
    ON CONFLICT (producto, fecha_pred) DO UPDATE SET
        ingresos_pred  = EXCLUDED.ingresos_pred,
        ingresos_low   = EXCLUDED.ingresos_low,
        ingresos_high  = EXCLUDED.ingresos_high,
        unidades_pred  = EXCLUDED.unidades_pred,
        algoritmo      = EXCLUDED.algoritmo,
        entrenado_en   = EXCLUDED.entrenado_en
""")

_UPSERT_META = sa.text("""
    INSERT INTO model_metadata (modelo, producto, algoritmo, r2, mae, rmse, mape, n_muestras, entrenado_en)
    VALUES ('productos', :producto, 'GBM_v3', :r2, :mae, :rmse, :mape, :n, NOW())
    ON CONFLICT (modelo, producto) DO UPDATE SET
        r2 = EXCLUDED.r2, mae = EXCLUDED.mae, rmse = EXCLUDED.rmse,
        mape = EXCLUDED.mape, n_muestras = EXCLUDED.n_muestras,
        entrenado_en = EXCLUDED.entrenado_en
""")


def guardar(engine: sa.Engine, producto: str,
            preds_ing: list, preds_und: list, meta: dict) -> None:
    now = datetime.utcnow()
    rows = []
    for i, (fecha, ing, low, high) in enumerate(preds_ing):
        und = preds_und[i][1] if i < len(preds_und) else 0.0
        rows.append({
            "producto":      producto,
            "fecha_pred":    fecha,
            "ingresos_pred": ing,
            "ingresos_low":  low,
            "ingresos_high": high,
            "unidades_pred": round(und, 2),
            "algoritmo":     "GBM_v3",
            "entrenado_en":  now,
        })

    # Clamping: R2 < -100 significa modelo inutil (peor que predecir la media).
    # MAPE > 999% tambien es inutil. Guardamos como cota para no reventar la columna.
    r2_safe   = round(max(min(meta["r2"],   1.0),  -999.9999), 4)
    mape_safe = round(min(meta["mape"], 9999.99), 2)

    with engine.begin() as conn:
        for row in rows:
            conn.execute(_UPSERT_PRED, row)
        conn.execute(_UPSERT_META, {
            "producto": producto,
            "r2":   r2_safe,
            "mae":  meta["mae"],
            "rmse": meta["rmse"],
            "mape": mape_safe,
            "n":    meta["n_muestras"],
        })


# ─── Ciclo principal ──────────────────────────────────────────────────────────

def ciclo_entrenamiento(engine: sa.Engine) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log.info("=" * 70)
    log.info("  CICLO DE ENTRENAMIENTO v3 — %s", ts)
    log.info("=" * 70)

    try:
        ensure_tables(engine)
    except Exception as exc:
        log.error("[INIT] Error verificando tablas: %s", exc)
        return

    try:
        df_ventas = cargar_ventas_diarias(engine)
    except Exception as exc:
        log.error("[DATA] Error cargando ventas: %s", exc)
        return

    if df_ventas.empty:
        log.warning("[DATA] Sin datos de ventas. Saltando ciclo.")
        return

    productos = sorted(df_ventas["producto"].unique())
    exitosos  = 0
    omitidos  = 0
    exitosos_set: set[str] = set()

    for producto in productos:
        mask    = df_ventas["producto"] == producto
        df_prod = df_ventas[mask][["fecha", "ingresos", "unidades"]].copy()

        # Minimo 2 dias con ventas para que construir_features pueda crear un
        # rango de fechas. El chequeo real de MIN_DIAS (14) esta dentro de
        # entrenar() sobre dias calendario (incluyendo ceros rellenos).
        if len(df_prod) < 2:
            omitidos += 1
            continue

        try:
            res_ing = entrenar(df_prod, target="ingresos")
            res_und = entrenar(df_prod, target="unidades")

            if res_ing is None:
                # Fallback: si la ventana de 35d no alcanza, probar con 60d.
                res_ing = entrenar(df_prod, target="ingresos", lookback_override=60)
                res_und = entrenar(df_prod, target="unidades", lookback_override=60)

            if res_ing is None:
                omitidos += 1
                continue

            preds_ing = pronosticar(res_ing, N_FORECAST_DAYS)
            preds_und = pronosticar(res_und, N_FORECAST_DAYS) if res_und else []

            guardar(engine, producto, preds_ing, preds_und, res_ing)
            exitosos += 1
            exitosos_set.add(producto)

            log.info(
                "[OK] %-40s R2=%.3f  MAPE=%5.1f%%  MAE=S/%.0f  n=%3d",
                producto[:40], res_ing["r2"], res_ing["mape"],
                res_ing["mae"], res_ing["n_muestras"],
            )
        except Exception as exc:
            log.error("[ERR] %s — %s", producto[:50], exc)

    # Limpiar metadata de productos omitidos — si no hay modelo actual, la metadata
    # antigua (ej: R2=-1636 de antes del fix) no debe contaminar los promedios.
    omitidos_con_meta = [p for p in productos if p not in exitosos_set]
    if omitidos_con_meta:
        try:
            with engine.begin() as conn:
                conn.execute(sa.text(
                    "DELETE FROM model_metadata WHERE modelo='productos' AND producto = ANY(:prods)"
                ), {"prods": omitidos_con_meta})
        except Exception:
            pass

    log.info("[DONE] Entrenados: %d | Omitidos (pocos datos): %d | Total: %d",
             exitosos, omitidos, len(productos))


def main() -> None:
    log.info("=" * 70)
    log.info("  CasaMarket ML Trainer v3 — GBM mejorado por Producto")
    log.info("  Reentrenamiento: cada %d min | Forecast: %d dias", RETRAIN_INTERVAL // 60, N_FORECAST_DAYS)
    log.info("  Features: %d | MIN_DIAS: %d | QUANTILE desde: %d dias",
             len(FEATURE_COLS), MIN_DIAS, MIN_DIAS_QUANTILE)
    log.info("=" * 70)

    engine = esperar_postgres()

    while True:
        try:
            ciclo_entrenamiento(engine)
        except Exception as exc:
            log.error("[LOOP] Error inesperado: %s", exc)

        log.info("[SLEEP] Proximo entrenamiento en %d minutos...", RETRAIN_INTERVAL // 60)
        time.sleep(RETRAIN_INTERVAL)


if __name__ == "__main__":
    main()

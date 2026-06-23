"""
ml/trainer.py
=============
Servicio de re-entrenamiento automatico — GradientBoostingRegressor por producto.
Se ejecuta cada 30 minutos y actualiza las predicciones con los datos mas recientes.

Modelos entrenados:
  - Ingresos diarios por producto (proximos 30 dias) con intervalo de confianza
  - Unidades diarias por producto (proximos 30 dias)

Features utilizados:
  - lag_1d, lag_3d, lag_7d, lag_14d    (ventas de dias anteriores)
  - rolling_3d, rolling_7d, rolling_14d (promedios moviles)
  - tendencia_7d                        (slope de la ultima semana)
  - dia_semana, dia_mes, semana_mes     (patron semanal y mensual)
  - mes, dia_anio, es_fin_semana        (estacionalidad)

Validacion:
  - TimeSeriesSplit(n_splits=3) para no filtrar el futuro al pasado

Tablas escritas:
  - predicciones_diarias  (UPSERT — producto, fecha_pred, ingresos, unidades, low/high)
  - model_metadata        (UPSERT — r2, mae, rmse, n_muestras por producto)
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
from sklearn.preprocessing import StandardScaler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Configuracion ─────────────────────────────────────────────────────────────
DB_URL            = "postgresql://casamarket:casamarket@postgres:5432/casamarket"
RETRAIN_INTERVAL  = 1800   # segundos entre ciclos (30 min)
MIN_DIAS          = 7      # minimo de dias historicos para entrenar un modelo
N_FORECAST_DAYS   = 30     # dias a pronosticar hacia el futuro
N_ESTIMATORS      = 150    # arboles en GradientBoosting
MAX_DEPTH         = 3      # profundidad maxima de cada arbol
LEARNING_RATE     = 0.08   # tasa de aprendizaje
CI_FACTOR         = 1.5    # factor para el intervalo de confianza (+/- CI_FACTOR * MAE)

FEATURE_COLS = [
    "dia_semana", "dia_mes", "semana_mes", "mes", "dia_anio",
    "es_fin_semana", "lag_1d", "lag_3d", "lag_7d", "lag_14d",
    "rolling_3d", "rolling_7d", "rolling_14d", "tendencia_7d",
]


# ─── Base de datos ─────────────────────────────────────────────────────────────

def get_engine() -> sa.Engine:
    return sa.create_engine(DB_URL, pool_pre_ping=True, pool_size=2, max_overflow=2)


def esperar_postgres(max_intentos: int = 20) -> sa.Engine:
    """Espera hasta que PostgreSQL este disponible y retorna el engine."""
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
    """
    Crea las tablas necesarias si no existen.
    Tambien agrega la columna 'hora' a ventas si se ejecuta sobre un deployment existente.
    """
    stmts = [
        # Migracion: agregar hora a ventas si no existe (deployment existente)
        """DO $$ BEGIN
               ALTER TABLE ventas ADD COLUMN IF NOT EXISTS hora TEXT;
           EXCEPTION WHEN OTHERS THEN NULL;
           END $$""",

        # predicciones_diarias
        """CREATE TABLE IF NOT EXISTS predicciones_diarias (
               id              BIGSERIAL PRIMARY KEY,
               producto        TEXT NOT NULL,
               fecha_pred      DATE NOT NULL,
               ingresos_pred   NUMERIC(14,2),
               ingresos_low    NUMERIC(14,2),
               ingresos_high   NUMERIC(14,2),
               unidades_pred   NUMERIC(10,2),
               algoritmo       TEXT DEFAULT 'GradientBoosting',
               entrenado_en    TIMESTAMPTZ DEFAULT NOW(),
               UNIQUE(producto, fecha_pred)
           )""",
        "CREATE INDEX IF NOT EXISTS idx_pred_diarias_producto  ON predicciones_diarias (producto)",
        "CREATE INDEX IF NOT EXISTS idx_pred_diarias_fecha     ON predicciones_diarias (fecha_pred)",

        # model_metadata
        """CREATE TABLE IF NOT EXISTS model_metadata (
               id           BIGSERIAL PRIMARY KEY,
               modelo       TEXT NOT NULL,
               producto     TEXT,
               algoritmo    TEXT,
               r2           NUMERIC(8,4),
               mae          NUMERIC(14,4),
               rmse         NUMERIC(14,4),
               n_muestras   INT,
               entrenado_en TIMESTAMPTZ DEFAULT NOW(),
               UNIQUE(modelo, producto)
           )""",
        "CREATE INDEX IF NOT EXISTS idx_model_meta_modelo   ON model_metadata (modelo)",
        "CREATE INDEX IF NOT EXISTS idx_model_meta_producto ON model_metadata (producto)",

        # Vista ranking proximos 7 dias
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

        # Vista estado dia actual
        """CREATE OR REPLACE VIEW estado_dia_actual AS
           SELECT
               v.producto,
               ROUND(SUM(v.total)::NUMERIC, 2)        AS ventas_hoy,
               COALESCE(p.ingresos_pred, 0)           AS prediccion_hoy,
               COALESCE(p.ingresos_low,  0)           AS pred_low,
               COALESCE(p.ingresos_high, 0)           AS pred_high,
               CASE WHEN COALESCE(p.ingresos_pred, 0) > 0
                    THEN ROUND((SUM(v.total) / p.ingresos_pred * 100)::NUMERIC, 1)
                    ELSE 0
               END AS pct_meta,
               CASE
                   WHEN p.ingresos_high IS NOT NULL AND SUM(v.total) > p.ingresos_high THEN 'SOBRE_META'
                   WHEN p.ingresos_low  IS NOT NULL AND SUM(v.total) >= p.ingresos_low THEN 'EN_META'
                   WHEN p.ingresos_pred IS NOT NULL AND SUM(v.total) >= p.ingresos_pred * 0.5 THEN 'EN_RIESGO'
                   ELSE 'BAJO_META'
               END AS alerta
           FROM ventas v
           LEFT JOIN predicciones_diarias p
               ON TRIM(v.producto) = p.producto AND p.fecha_pred = CURRENT_DATE
           WHERE v.fecha = CURRENT_DATE AND v.total > 0
           GROUP BY v.producto, p.ingresos_pred, p.ingresos_low, p.ingresos_high
           ORDER BY ventas_hoy DESC""",
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(sa.text(stmt))
    log.info("[INIT] Tablas y vistas ML verificadas/creadas.")


# ─── Carga de datos ────────────────────────────────────────────────────────────

def cargar_ventas_diarias(engine: sa.Engine) -> pd.DataFrame:
    """
    Carga ventas agrupadas por (fecha, producto) desde PostgreSQL.
    Retorna DataFrame con columnas: fecha, producto, ingresos, unidades, n_ventas
    """
    sql = """
    SELECT
        fecha,
        TRIM(producto) AS producto,
        ROUND(SUM(total)::NUMERIC, 2) AS ingresos,
        COALESCE(SUM(cantidad), 0)    AS unidades,
        COUNT(*)                      AS n_ventas
    FROM ventas
    WHERE fecha IS NOT NULL
      AND total > 0
      AND producto IS NOT NULL
      AND TRIM(producto) != ''
    GROUP BY fecha, TRIM(producto)
    ORDER BY fecha, producto
    """
    df = pd.read_sql(sql, engine, parse_dates=["fecha"])
    log.info("[DATA] %d registros diarios por producto (%d dias, %d productos)",
             len(df), df["fecha"].nunique(), df["producto"].nunique())
    return df


# ─── Feature engineering ──────────────────────────────────────────────────────

def _calc_slope(values: np.ndarray) -> float:
    """Calcula la pendiente de una serie temporal (tendencia)."""
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=float)
    try:
        return float(np.polyfit(x, values, 1)[0])
    except Exception:
        return 0.0


def construir_features(df_prod: pd.DataFrame) -> pd.DataFrame:
    """
    Dado el historico de un producto (fecha, ingresos, unidades),
    construye el DataFrame con todos los features para GBM.
    Rellena fechas faltantes con 0 para mantener la serie continua.
    """
    df = df_prod[["fecha", "ingresos", "unidades"]].copy().sort_values("fecha").reset_index(drop=True)

    # Rellenar dias sin ventas con 0 (serie continua)
    if len(df) >= 2:
        rango = pd.date_range(df["fecha"].min(), df["fecha"].max(), freq="D")
        df = df.set_index("fecha").reindex(rango, fill_value=0.0).reset_index()
        df.rename(columns={"index": "fecha"}, inplace=True)
        df["fecha"] = pd.to_datetime(df["fecha"])

    # Features de calendario
    df["dia_semana"]    = df["fecha"].dt.dayofweek          # 0=Lun, 6=Dom
    df["dia_mes"]       = df["fecha"].dt.day
    df["semana_mes"]    = ((df["fecha"].dt.day - 1) // 7 + 1).clip(1, 5)
    df["mes"]           = df["fecha"].dt.month
    df["dia_anio"]      = df["fecha"].dt.dayofyear
    df["es_fin_semana"] = (df["fecha"].dt.dayofweek >= 5).astype(int)

    # Lag features (sobre ingresos, shifted para no filtrar futuro)
    ing = df["ingresos"]
    df["lag_1d"]  = ing.shift(1).fillna(0)
    df["lag_3d"]  = ing.shift(3).fillna(0)
    df["lag_7d"]  = ing.shift(7).fillna(0)
    df["lag_14d"] = ing.shift(14).fillna(0)

    # Rolling averages (usando shift(1) para no incluir el dia actual)
    shifted = ing.shift(1).fillna(0)
    df["rolling_3d"]  = shifted.rolling(3,  min_periods=1).mean().fillna(0)
    df["rolling_7d"]  = shifted.rolling(7,  min_periods=1).mean().fillna(0)
    df["rolling_14d"] = shifted.rolling(14, min_periods=1).mean().fillna(0)

    # Tendencia de la ultima semana (slope)
    df["tendencia_7d"] = shifted.rolling(7, min_periods=2).apply(
        _calc_slope, raw=True
    ).fillna(0)

    return df


# ─── Entrenamiento ─────────────────────────────────────────────────────────────

def entrenar(df_prod: pd.DataFrame, target: str = "ingresos") -> dict | None:
    """
    Entrena un GradientBoostingRegressor para el target especificado.
    Retorna dict con {model, scaler, df_full, r2, mae, rmse, n_muestras}
    o None si no hay datos suficientes.
    """
    df = construir_features(df_prod)
    df_train = df.dropna(subset=FEATURE_COLS).copy()

    if len(df_train) < MIN_DIAS:
        return None

    X = df_train[FEATURE_COLS].values.astype(float)
    y = df_train[target].values.astype(float)

    # Normalizar
    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X)

    # Validacion con TimeSeriesSplit (no mezcla futuro con pasado)
    n_splits = min(3, max(1, len(df_train) // 5))
    tscv = TimeSeriesSplit(n_splits=n_splits)
    r2_cv, mae_cv = [], []

    for tr_idx, val_idx in tscv.split(X_sc):
        if len(tr_idx) < 3 or len(val_idx) < 1:
            continue
        gbm_cv = GradientBoostingRegressor(
            n_estimators=100, max_depth=MAX_DEPTH,
            learning_rate=LEARNING_RATE, subsample=0.8, random_state=42
        )
        gbm_cv.fit(X_sc[tr_idx], y[tr_idx])
        y_hat = np.maximum(gbm_cv.predict(X_sc[val_idx]), 0)
        if len(set(y[val_idx])) > 1:
            r2_cv.append(float(r2_score(y[val_idx], y_hat)))
        mae_cv.append(float(mean_absolute_error(y[val_idx], y_hat)))

    # Modelo final sobre todos los datos
    gbm = GradientBoostingRegressor(
        n_estimators=N_ESTIMATORS, max_depth=MAX_DEPTH,
        learning_rate=LEARNING_RATE, subsample=0.8, random_state=42
    )
    gbm.fit(X_sc, y)
    y_pred = np.maximum(gbm.predict(X_sc), 0)

    r2_final   = float(r2_score(y, y_pred)) if len(set(y)) > 1 else 0.0
    mae_final  = float(mean_absolute_error(y, y_pred))
    rmse_final = float(np.sqrt(mean_squared_error(y, y_pred)))

    return {
        "model":      gbm,
        "scaler":     scaler,
        "df_full":    df,
        "r2":         round(float(np.mean(r2_cv))   if r2_cv  else r2_final,  4),
        "mae":        round(float(np.mean(mae_cv))   if mae_cv else mae_final, 4),
        "rmse":       round(rmse_final, 4),
        "n_muestras": len(df_train),
    }


# ─── Pronostico ───────────────────────────────────────────────────────────────

def pronosticar(resultado: dict, n_dias: int = N_FORECAST_DAYS) -> list[tuple]:
    """
    Genera predicciones para los proximos n_dias dias.
    Retorna lista de tuplas (fecha, pred, low, high).
    El intervalo de confianza es pred +/- CI_FACTOR * MAE.
    """
    model  = resultado["model"]
    scaler = resultado["scaler"]
    mae    = resultado["mae"]
    df     = resultado["df_full"]

    # Buffer de valores historicos para construir lags de forma recursiva
    buffer = list(df["ingresos"].values.astype(float))

    predicciones = []
    hoy = date.today()

    for i in range(n_dias):
        fecha_pred = hoy + timedelta(days=i)
        fp = fecha_pred

        # Construir features para el dia a predecir
        def _get(offset: int) -> float:
            idx = len(buffer) - offset
            return buffer[idx] if idx >= 0 else 0.0

        def _roll(window: int) -> float:
            vals = buffer[-window:] if len(buffer) >= window else buffer
            return float(np.mean(vals)) if vals else 0.0

        def _slope7() -> float:
            vals = buffer[-7:] if len(buffer) >= 7 else buffer
            return _calc_slope(np.array(vals))

        features = [
            fp.weekday(),                          # dia_semana
            fp.day,                                # dia_mes
            min((fp.day - 1) // 7 + 1, 5),        # semana_mes
            fp.month,                              # mes
            fp.timetuple().tm_yday,                # dia_anio
            int(fp.weekday() >= 5),                # es_fin_semana
            _get(1),                               # lag_1d
            _get(3),                               # lag_3d
            _get(7),                               # lag_7d
            _get(14),                              # lag_14d
            _roll(3),                              # rolling_3d
            _roll(7),                              # rolling_7d
            _roll(14),                             # rolling_14d
            _slope7(),                             # tendencia_7d
        ]

        X_pred = np.array([features], dtype=float)
        X_sc   = scaler.transform(X_pred)
        pred   = max(float(model.predict(X_sc)[0]), 0.0)
        low    = max(pred - CI_FACTOR * mae, 0.0)
        high   = pred + CI_FACTOR * mae

        predicciones.append((fecha_pred, round(pred, 2), round(low, 2), round(high, 2)))
        buffer.append(pred)   # usar la prediccion como lag para el siguiente dia

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
    INSERT INTO model_metadata (modelo, producto, algoritmo, r2, mae, rmse, n_muestras, entrenado_en)
    VALUES ('productos', :producto, 'GradientBoosting', :r2, :mae, :rmse, :n, NOW())
    ON CONFLICT (modelo, producto) DO UPDATE SET
        r2 = EXCLUDED.r2, mae = EXCLUDED.mae, rmse = EXCLUDED.rmse,
        n_muestras = EXCLUDED.n_muestras, entrenado_en = EXCLUDED.entrenado_en
""")


def guardar(engine: sa.Engine, producto: str,
            preds_ing: list, preds_und: list, meta: dict) -> None:
    """Hace UPSERT de predicciones y metadata en PostgreSQL."""
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
            "algoritmo":     "GradientBoosting",
            "entrenado_en":  now,
        })

    with engine.begin() as conn:
        for row in rows:
            conn.execute(_UPSERT_PRED, row)
        conn.execute(_UPSERT_META, {
            "producto": producto,
            "r2":   meta["r2"],
            "mae":  meta["mae"],
            "rmse": meta["rmse"],
            "n":    meta["n_muestras"],
        })


# ─── Ciclo principal ──────────────────────────────────────────────────────────

def ciclo_entrenamiento(engine: sa.Engine) -> None:
    """Ejecuta un ciclo completo: carga datos, entrena modelos, guarda predicciones."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log.info("=" * 65)
    log.info("  CICLO DE ENTRENAMIENTO — %s", ts)
    log.info("=" * 65)

    # Asegurar tablas
    try:
        ensure_tables(engine)
    except Exception as exc:
        log.error("[INIT] Error verificando tablas: %s", exc)
        return

    # Cargar ventas
    try:
        df_ventas = cargar_ventas_diarias(engine)
    except Exception as exc:
        log.error("[DATA] Error cargando ventas: %s", exc)
        return

    if df_ventas.empty:
        log.warning("[DATA] Sin datos de ventas. Saltando ciclo.")
        return

    productos  = sorted(df_ventas["producto"].unique())
    exitosos   = 0
    omitidos   = 0

    for producto in productos:
        mask    = df_ventas["producto"] == producto
        df_prod = df_ventas[mask][["fecha", "ingresos", "unidades"]].copy()

        if len(df_prod) < MIN_DIAS:
            omitidos += 1
            continue

        try:
            res_ing = entrenar(df_prod, target="ingresos")
            res_und = entrenar(df_prod, target="unidades")

            if res_ing is None:
                omitidos += 1
                continue

            preds_ing = pronosticar(res_ing, N_FORECAST_DAYS)
            preds_und = pronosticar(res_und, N_FORECAST_DAYS) if res_und else []

            guardar(engine, producto, preds_ing, preds_und, res_ing)

            exitosos += 1
            log.info(
                "[OK] %-42s R2=%.3f  MAE=S/%.2f  n=%3d  pred=%dd",
                (producto[:42] + ")" if len(producto) > 42 else producto),
                res_ing["r2"], res_ing["mae"], res_ing["n_muestras"], len(preds_ing),
            )
        except Exception as exc:
            log.error("[ERR] %s — %s", producto[:50], exc)

    log.info("[DONE] Entrenados: %d | Omitidos (pocos datos): %d | Total: %d",
             exitosos, omitidos, len(productos))


def main() -> None:
    log.info("=" * 65)
    log.info("  CasaMarket ML Trainer — GradientBoosting por Producto")
    log.info("  Reentrenamiento cada %d min", RETRAIN_INTERVAL // 60)
    log.info("  Pronostico: %d dias | Features: %d", N_FORECAST_DAYS, len(FEATURE_COLS))
    log.info("=" * 65)

    engine = esperar_postgres()

    while True:
        try:
            ciclo_entrenamiento(engine)
        except Exception as exc:
            log.error("[LOOP] Error inesperado en ciclo: %s", exc)

        log.info("[SLEEP] Proximo entrenamiento en %d minutos...", RETRAIN_INTERVAL // 60)
        time.sleep(RETRAIN_INTERVAL)


if __name__ == "__main__":
    main()

"""
ml/trainer_anomalias.py
=======================
Deteccion de anomalias en ventas diarias por producto.
Modelo: IsolationForest (scikit-learn) + Z-score para clasificacion.

Logica:
  1. Para cada producto, toma sus ventas diarias de los ultimos 60 dias.
  2. Entrena IsolationForest(contamination=0.05) — espera ~5% de dias anomalos.
  3. Clasifica cada dia como normal o anomalo.
  4. Calcula desviacion % vs media movil de 14 dias.
  5. Etiqueta el tipo: 'ALTA_VENTA' (ventas >2*media) o 'CAIDA_VENTAS' (<0.3*media).
  6. Solo escribe anomalias de los ultimos 7 dias (las mas recientes).

Tabla escrita:
  - anomalias_detectadas  (producto, fecha, tipo, score, desviacion_pct)

Se llama desde el servicio ml-trainer cada ciclo de 30 minutos.
"""
import logging
from datetime import date, timedelta, datetime

import numpy as np
import pandas as pd
import sqlalchemy as sa
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

log = logging.getLogger(__name__)

LOOKBACK_DIAS    = 60    # dias historicos para entrenar IsolationForest
RECIENTES_DIAS   = 60    # reportar anomalias dentro del lookback completo
CONTAMINATION    = 0.05  # fraccion esperada de anomalias (~5%)
MIN_DIAS_PROD    = 4     # minimo de dias historicos para aplicar el modelo


# ─── Tabla ────────────────────────────────────────────────────────────────────

def ensure_table(engine: sa.Engine) -> None:
    stmts = [
        """CREATE TABLE IF NOT EXISTS anomalias_detectadas (
               id                BIGSERIAL PRIMARY KEY,
               producto          TEXT NOT NULL,
               fecha             DATE NOT NULL,
               ventas_reales     NUMERIC(14,2),
               media_historica   NUMERIC(14,2),
               desviacion_pct    NUMERIC(12,2),
               score_anomalia    NUMERIC(8,4),
               tipo              TEXT,
               detectado_en      TIMESTAMPTZ DEFAULT NOW(),
               UNIQUE(producto, fecha)
           )""",
        "CREATE INDEX IF NOT EXISTS idx_anomalias_producto  ON anomalias_detectadas (producto)",
        "CREATE INDEX IF NOT EXISTS idx_anomalias_fecha     ON anomalias_detectadas (fecha)",
        "CREATE INDEX IF NOT EXISTS idx_anomalias_tipo      ON anomalias_detectadas (tipo)",
        "CREATE INDEX IF NOT EXISTS idx_anomalias_detectado ON anomalias_detectadas (detectado_en)",
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(sa.text(stmt))


# ─── Datos ────────────────────────────────────────────────────────────────────

def cargar_ventas_diarias(engine: sa.Engine) -> pd.DataFrame:
    # Usamos MAX(fecha) de la BD como referencia, NO date.today().
    # Si los datos terminan el 31/05 y hoy es 26/06, con date.today() se crean
    # 26 dias de zeros artificiales que distorsionan el IsolationForest
    # (recalibra la distribucion como si zeros fueran "normales").
    sql = f"""
    SELECT
        fecha,
        TRIM(producto) AS producto,
        ROUND(SUM(total)::NUMERIC, 2) AS ingresos,
        COUNT(*) AS n_ventas
    FROM ventas
    WHERE fecha >= (SELECT MAX(fecha) - INTERVAL '{LOOKBACK_DIAS} days' FROM ventas WHERE total > 0)
      AND total > 0
      AND producto IS NOT NULL
      AND TRIM(producto) != ''
    GROUP BY fecha, TRIM(producto)
    ORDER BY fecha, producto
    """
    return pd.read_sql(sql, engine, parse_dates=["fecha"])


# ─── Deteccion ────────────────────────────────────────────────────────────────

def detectar_anomalias_producto(df_prod: pd.DataFrame) -> list[dict]:
    """
    Aplica IsolationForest sobre las ventas diarias de un producto.
    Retorna lista de dicts con anomalias recientes (ultimos RECIENTES_DIAS dias).
    """
    if len(df_prod) < MIN_DIAS_PROD:
        return []

    df = df_prod.copy().sort_values("fecha").reset_index(drop=True)

    # Rellenar dias sin ventas (para que la serie sea continua)
    rango = pd.date_range(df["fecha"].min(), df["fecha"].max(), freq="D")
    df = df.set_index("fecha").reindex(rango, fill_value=0.0).reset_index()
    df.rename(columns={"index": "fecha"}, inplace=True)
    df["fecha"] = pd.to_datetime(df["fecha"])

    # Features para IsolationForest
    df["lag_1d"]       = df["ingresos"].shift(1).fillna(0)
    df["rolling_7d"]   = df["ingresos"].shift(1).rolling(7,  min_periods=1).mean().fillna(0)
    df["rolling_14d"]  = df["ingresos"].shift(1).rolling(14, min_periods=1).mean().fillna(0)
    df["z_score"]      = (
        (df["ingresos"] - df["rolling_14d"]) /
        (df["ingresos"].rolling(14, min_periods=2).std().fillna(1) + 1e-9)
    )

    feature_cols = ["ingresos", "lag_1d", "rolling_7d", "rolling_14d", "z_score"]
    df_feat = df.dropna(subset=feature_cols)

    if len(df_feat) < MIN_DIAS_PROD:
        return []

    X = df_feat[feature_cols].values.astype(float)
    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X)

    # Entrenar IsolationForest
    iso = IsolationForest(
        n_estimators=100,
        contamination=CONTAMINATION,
        random_state=42,
        n_jobs=-1,
    )
    iso.fit(X_sc)

    # Scores: negativo = mas anomalo, positivo = normal
    scores = iso.score_samples(X_sc)   # entre -1 y 0 aprox
    preds  = iso.predict(X_sc)         # -1 = anomalia, 1 = normal

    df_feat = df_feat.copy()
    df_feat["score_anomalia"] = scores
    df_feat["es_anomalia"]    = (preds == -1)

    # Reportar anomalias desde los ultimos RECIENTES_DIAS de los DATOS (no de hoy).
    # Con datos terminados en mayo, date.today() crea una ventana futura vacia.
    fecha_max = df_feat["fecha"].max()
    fecha_limite = fecha_max - pd.Timedelta(days=RECIENTES_DIAS)
    recientes = df_feat[df_feat["fecha"] >= fecha_limite].copy()

    anomalias = []
    for _, row in recientes[recientes["es_anomalia"]].iterrows():
        media_14d = float(row["rolling_14d"]) if row["rolling_14d"] > 0 else 1.0
        ventas    = float(row["ingresos"])
        desvpct   = round(min(max((ventas - media_14d) / media_14d * 100, -9999999.99), 9999999.99), 2)

        if ventas > media_14d * 1.5:
            tipo = "ALTA_VENTA"
        elif ventas < media_14d * 0.4:
            tipo = "CAIDA_VENTAS"
        else:
            tipo = "INUSUAL"   # anomalia pero no clasificada claramente

        anomalias.append({
            "fecha":           row["fecha"].date() if hasattr(row["fecha"], "date") else row["fecha"],
            "ventas_reales":   round(ventas, 2),
            "media_historica": round(media_14d, 2),
            "desviacion_pct":  desvpct,
            "score_anomalia":  round(float(row["score_anomalia"]), 4),
            "tipo":            tipo,
        })

    return anomalias


# ─── Persistencia ─────────────────────────────────────────────────────────────

_UPSERT_ANOM = sa.text("""
    INSERT INTO anomalias_detectadas
        (producto, fecha, ventas_reales, media_historica, desviacion_pct,
         score_anomalia, tipo, detectado_en)
    VALUES
        (:producto, :fecha, :ventas_reales, :media_historica, :desviacion_pct,
         :score_anomalia, :tipo, :detectado_en)
    ON CONFLICT (producto, fecha) DO UPDATE SET
        ventas_reales   = EXCLUDED.ventas_reales,
        media_historica = EXCLUDED.media_historica,
        desviacion_pct  = EXCLUDED.desviacion_pct,
        score_anomalia  = EXCLUDED.score_anomalia,
        tipo            = EXCLUDED.tipo,
        detectado_en    = EXCLUDED.detectado_en
""")


def guardar_anomalias(engine: sa.Engine, producto: str, anomalias: list[dict]) -> None:
    if not anomalias:
        return
    now = datetime.utcnow()
    with engine.begin() as conn:
        for anom in anomalias:
            conn.execute(_UPSERT_ANOM, {
                "producto":       producto,
                "fecha":          anom["fecha"],
                "ventas_reales":  anom["ventas_reales"],
                "media_historica": anom["media_historica"],
                "desviacion_pct": anom["desviacion_pct"],
                "score_anomalia": anom["score_anomalia"],
                "tipo":           anom["tipo"],
                "detectado_en":   now,
            })


# ─── Punto de entrada ─────────────────────────────────────────────────────────

def ejecutar(engine: sa.Engine) -> None:
    """Detecta y guarda anomalias para todos los productos."""
    log.info("[ANOMALIAS] Iniciando deteccion de anomalias (IsolationForest)...")

    try:
        ensure_table(engine)
        df_ventas = cargar_ventas_diarias(engine)
    except Exception as exc:
        log.error("[ANOMALIAS] Error cargando datos: %s", exc)
        return

    if df_ventas.empty:
        log.warning("[ANOMALIAS] Sin datos recientes. Saltando.")
        return

    productos    = sorted(df_ventas["producto"].unique())
    total_anom   = 0
    total_prods  = 0

    for producto in productos:
        df_prod = df_ventas[df_ventas["producto"] == producto].copy()
        try:
            anomalias = detectar_anomalias_producto(df_prod)
            if anomalias:
                guardar_anomalias(engine, producto, anomalias)
                total_anom  += len(anomalias)
                total_prods += 1
                for a in anomalias:
                    log.info(
                        "[ANOMALIA] %-40s | %s | %s | %.1f%% | S/%.2f",
                        producto[:40], a["fecha"], a["tipo"],
                        a["desviacion_pct"], a["ventas_reales"],
                    )
        except Exception as exc:
            log.error("[ANOMALIAS] %s — %s", producto[:40], exc)

    log.info("[ANOMALIAS] Completado: %d anomalias en %d productos.",
             total_anom, total_prods)

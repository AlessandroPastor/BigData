"""
ml/trainer_clientes.py
======================
Segmentacion de clientes usando KMeans sobre metricas RFM:
  R - Recencia:    dias desde la ultima compra (menor = mejor)
  F - Frecuencia:  numero total de transacciones
  M - Monetario:   suma total de compras en soles

Clusters generados (3):
  - VIP:       alta frecuencia + alto valor + compro recientemente
  - Regular:   frecuencia y valor medios
  - En Riesgo: no compra hace tiempo O bajo valor acumulado

El etiquetado automatico asigna 'VIP' al cluster con mayor valor_monetario promedio,
'En Riesgo' al de mayor recencia (no compra hace mas tiempo), y 'Regular' al restante.

Tabla escrita:
  - segmentos_clientes (cliente, segmento, recencia_dias, frecuencia, valor_monetario,
                        ticket_promedio, ultima_compra)
"""
import logging
from datetime import date, datetime

import numpy as np
import pandas as pd
import sqlalchemy as sa
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

log = logging.getLogger(__name__)

N_CLUSTERS    = 3    # VIP / Regular / En Riesgo
RANDOM_STATE  = 42
MIN_CLIENTES  = 10   # minimo de clientes para aplicar KMeans


# ─── Tabla ────────────────────────────────────────────────────────────────────

def ensure_table(engine: sa.Engine) -> None:
    stmts = [
        """CREATE TABLE IF NOT EXISTS segmentos_clientes (
               id              BIGSERIAL PRIMARY KEY,
               cliente         TEXT NOT NULL UNIQUE,
               segmento        TEXT,
               cluster_id      INT,
               recencia_dias   INT,
               frecuencia      INT,
               valor_monetario NUMERIC(14,2),
               ticket_promedio NUMERIC(10,2),
               ultima_compra   DATE,
               entrenado_en    TIMESTAMPTZ DEFAULT NOW()
           )""",
        "CREATE INDEX IF NOT EXISTS idx_segmentos_segmento ON segmentos_clientes (segmento)",
        "CREATE INDEX IF NOT EXISTS idx_segmentos_cliente  ON segmentos_clientes (cliente)",
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(sa.text(stmt))


# ─── Datos ────────────────────────────────────────────────────────────────────

def cargar_rfm(engine: sa.Engine) -> pd.DataFrame:
    """
    Calcula metricas RFM por cliente desde la tabla ventas.
    Retorna DataFrame con columnas:
      cliente, recencia_dias, frecuencia, valor_monetario, ticket_promedio, ultima_compra
    """
    hoy = date.today().isoformat()
    sql = f"""
    SELECT
        TRIM(cliente)                                   AS cliente,
        CURRENT_DATE - MAX(fecha)                       AS recencia_dias,
        COUNT(*)                                        AS frecuencia,
        ROUND(SUM(total)::NUMERIC, 2)                   AS valor_monetario,
        ROUND((SUM(total) / COUNT(*))::NUMERIC, 2)      AS ticket_promedio,
        MAX(fecha)                                      AS ultima_compra
    FROM ventas
    WHERE cliente IS NOT NULL
      AND TRIM(cliente) != ''
      AND total > 0
      AND fecha IS NOT NULL
    GROUP BY TRIM(cliente)
    HAVING COUNT(*) >= 1
    ORDER BY valor_monetario DESC
    """
    df = pd.read_sql(sql, engine, parse_dates=["ultima_compra"])
    # recencia_dias viene como un timedelta o intervalo de PostgreSQL, convertir a int
    if "recencia_dias" in df.columns:
        df["recencia_dias"] = pd.to_numeric(df["recencia_dias"], errors="coerce").fillna(999).astype(int)
    return df


# ─── Clustering ───────────────────────────────────────────────────────────────

def segmentar_clientes(df_rfm: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica KMeans sobre las metricas RFM escaladas.
    Agrega columna 'cluster_id' y 'segmento' al DataFrame.

    Tratamiento de mega-outliers: clientes con valor_monetario > Q3 + 3*IQR
    se etiquetan 'VIP' directamente sin entrar al clustering, para evitar que
    un solo cliente distorsione todos los centroides (ej: FERNANDEZ CALA TOMAS
    con 16,794 transacciones en 9 dias, S/406,151, que hacia que todos los demas
    quedaran en clusters sin distincion real).
    """
    if len(df_rfm) < MIN_CLIENTES:
        log.warning("[CLIENTES] Solo %d clientes — asignando todos como 'Regular'.", len(df_rfm))
        df_rfm["cluster_id"] = 0
        df_rfm["segmento"]   = "Regular"
        return df_rfm

    df_rfm = df_rfm.copy()

    # ── Detectar y separar mega-outliers antes del clustering ───────────────
    vm = df_rfm["valor_monetario"].values.astype(float)
    q1, q3 = float(np.percentile(vm, 25)), float(np.percentile(vm, 75))
    iqr = q3 - q1
    umbral_outlier = q3 + 3.0 * iqr

    mascara_outlier = df_rfm["valor_monetario"] > umbral_outlier
    n_outliers = int(mascara_outlier.sum())
    if n_outliers > 0:
        log.info("[CLIENTES] %d clientes mega-outlier (valor > S/%.0f) etiquetados VIP directamente.",
                 n_outliers, umbral_outlier)

    df_outliers = df_rfm[mascara_outlier].copy()
    df_normales = df_rfm[~mascara_outlier].copy()

    # Asignacion directa para outliers (son VIP por valor monetario extremo)
    df_outliers["cluster_id"] = -1   # cluster especial
    df_outliers["segmento"]   = "VIP"

    # ── Clustering solo sobre clientes no-outliers ───────────────────────────
    n_clusters_eff = N_CLUSTERS
    if len(df_normales) < MIN_CLIENTES:
        log.warning("[CLIENTES] Solo %d clientes normales — asignando como 'Regular'.", len(df_normales))
        df_normales["cluster_id"] = 0
        df_normales["segmento"]   = "Regular"
        return pd.concat([df_outliers, df_normales], ignore_index=True)

    # Si hay muy pocos reducir clusters para evitar clusters vacios
    n_clusters_eff = min(N_CLUSTERS, max(2, len(df_normales) // 3))

    features = df_normales[["recencia_dias", "frecuencia", "valor_monetario"]].copy()
    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(features.values.astype(float))

    kmeans = KMeans(
        n_clusters=n_clusters_eff,
        random_state=RANDOM_STATE,
        n_init=10,
        max_iter=300,
    )
    labels = kmeans.fit_predict(X_sc)
    df_normales["cluster_id"] = labels

    # ── Etiquetado automatico de segmentos ──────────────────────────────────
    perfiles = df_normales.groupby("cluster_id").agg(
        recencia_media=("recencia_dias",   "mean"),
        frecuencia_media=("frecuencia",    "mean"),
        valor_medio=("valor_monetario",    "mean"),
    ).reset_index()

    # VIP (dentro de normales): mayor valor_monetario
    # En Riesgo: mayor recencia
    # Regular: el restante
    cluster_vip = int(perfiles.loc[perfiles["valor_medio"].idxmax(), "cluster_id"])
    no_vip = perfiles[perfiles["cluster_id"] != cluster_vip]
    if len(no_vip) > 0:
        cluster_riesgo = int(no_vip.loc[no_vip["recencia_media"].idxmax(), "cluster_id"])
    else:
        cluster_riesgo = (cluster_vip + 1) % n_clusters_eff

    def asignar_segmento(cid: int) -> str:
        if cid == cluster_vip:
            return "VIP"
        elif cid == cluster_riesgo:
            return "En Riesgo"
        else:
            return "Regular"

    df_normales["segmento"] = df_normales["cluster_id"].apply(asignar_segmento)

    df_rfm = pd.concat([df_outliers, df_normales], ignore_index=True)

    # Log resumen por segmento
    for seg in ["VIP", "Regular", "En Riesgo"]:
        sub = df_rfm[df_rfm["segmento"] == seg]
        if len(sub) > 0:
            log.info(
                "[CLIENTES] %-10s %4d clientes | recencia=%.0fd | "
                "frecuencia=%.1f | valor=S/%.2f | ticket=S/%.2f",
                seg, len(sub),
                sub["recencia_dias"].mean(),
                sub["frecuencia"].mean(),
                sub["valor_monetario"].mean(),
                sub["ticket_promedio"].mean(),
            )

    return df_rfm


# ─── Persistencia ─────────────────────────────────────────────────────────────

_UPSERT_CLI = sa.text("""
    INSERT INTO segmentos_clientes
        (cliente, segmento, cluster_id, recencia_dias, frecuencia,
         valor_monetario, ticket_promedio, ultima_compra, entrenado_en)
    VALUES
        (:cliente, :segmento, :cluster_id, :recencia_dias, :frecuencia,
         :valor_monetario, :ticket_promedio, :ultima_compra, :entrenado_en)
    ON CONFLICT (cliente) DO UPDATE SET
        segmento        = EXCLUDED.segmento,
        cluster_id      = EXCLUDED.cluster_id,
        recencia_dias   = EXCLUDED.recencia_dias,
        frecuencia      = EXCLUDED.frecuencia,
        valor_monetario = EXCLUDED.valor_monetario,
        ticket_promedio = EXCLUDED.ticket_promedio,
        ultima_compra   = EXCLUDED.ultima_compra,
        entrenado_en    = EXCLUDED.entrenado_en
""")


def guardar_segmentos(engine: sa.Engine, df: pd.DataFrame) -> None:
    now = datetime.utcnow()
    with engine.begin() as conn:
        for _, row in df.iterrows():
            ultima = row["ultima_compra"]
            if hasattr(ultima, "date"):
                ultima = ultima.date()
            conn.execute(_UPSERT_CLI, {
                "cliente":        str(row["cliente"]),
                "segmento":       str(row["segmento"]),
                "cluster_id":     int(row["cluster_id"]),
                "recencia_dias":  int(row["recencia_dias"]),
                "frecuencia":     int(row["frecuencia"]),
                "valor_monetario": float(row["valor_monetario"]),
                "ticket_promedio": float(row["ticket_promedio"]),
                "ultima_compra":  ultima,
                "entrenado_en":   now,
            })


# ─── Punto de entrada ─────────────────────────────────────────────────────────

def ejecutar(engine: sa.Engine) -> None:
    """Calcula RFM, aplica KMeans y guarda segmentos de clientes."""
    log.info("[CLIENTES] Iniciando segmentacion RFM (KMeans n=%d)...", N_CLUSTERS)

    try:
        ensure_table(engine)
        df_rfm = cargar_rfm(engine)
    except Exception as exc:
        log.error("[CLIENTES] Error cargando datos RFM: %s", exc)
        return

    if df_rfm.empty:
        log.warning("[CLIENTES] Sin datos de clientes. Saltando.")
        return

    log.info("[CLIENTES] %d clientes unicos encontrados.", len(df_rfm))

    try:
        df_seg = segmentar_clientes(df_rfm)
        guardar_segmentos(engine, df_seg)
        conteo = df_seg["segmento"].value_counts().to_dict()
        log.info("[CLIENTES] Guardados: VIP=%d | Regular=%d | En Riesgo=%d",
                 conteo.get("VIP", 0), conteo.get("Regular", 0), conteo.get("En Riesgo", 0))
    except Exception as exc:
        log.error("[CLIENTES] Error en clustering: %s", exc)

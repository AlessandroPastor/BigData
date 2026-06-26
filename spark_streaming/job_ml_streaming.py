"""
job_ml_streaming.py  (v2 — corregido)
======================================
Spark Structured Streaming — Scoring ML en tiempo real
=======================================================

Mejoras respecto a la version original:
  - Comparacion CORRECTA: acumulado real del dia vs prediccion DIARIA del modelo GBM
  - Umbrales con sentido de negocio basados en intervalo de confianza del modelo:
      SOBRE_META : ventas_hoy > ingresos_high (supero la banda superior)
      EN_META    : ingresos_low <= ventas_hoy <= ingresos_high (dentro del intervalo)
      EN_RIESGO  : 0.5 * prediccion <= ventas_hoy < ingresos_low (por debajo pero cercano)
      BAJO_META  : ventas_hoy < 0.5 * prediccion (muy por debajo de lo esperado)
  - Lee predicciones de 'predicciones_diarias' (GBM diario) en lugar de 'predicciones_2026'
  - Recarga predicciones del dia desde PostgreSQL en cada batch (siempre frescas)
  - Escribe ventas_ml_scored con: ventas_hoy, prediccion_hoy, pred_low, pred_high, pct_completado
  - startingOffsets cambiado a 'latest' para evitar duplicados al reiniciar

Flujo:
  1. Por cada micro-batch de Kafka (30s), los registros se agregan en Spark.
  2. foreachBatch consulta PostgreSQL para obtener el acumulado del DIA ACTUAL.
  3. Compara acumulado real vs prediccion diaria del modelo GBM.
  4. Escribe resultado en ventas_ml_scored.
  5. Imprime alertas significativas en consola.

Levantar con:
    docker compose up -d spark-ml
"""
import logging
from datetime import date, datetime, timezone

import sqlalchemy as sa
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, current_timestamp, from_json, month as spark_month,
    sum as spark_sum, to_date,
)
from pyspark.sql.types import (
    DoubleType, LongType, StringType, StructField, StructType,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Configuracion ─────────────────────────────────────────────────────────────
KAFKA_BROKER = "ec-kafka:9092"
TOPIC        = "casamarket.ventas.raw"
OUTPUT_BASE  = "/home/jovyan/output"
CHECKPOINT   = f"{OUTPUT_BASE}/checkpoints/ml_streaming_v2"
TRIGGER      = "30 seconds"

PG_URL     = "jdbc:postgresql://postgres:5432/casamarket"
PG_SA_URL  = "postgresql://casamarket:casamarket@postgres:5432/casamarket"
PG_PROPS   = {
    "user":     "casamarket",
    "password": "casamarket",
    "driver":   "org.postgresql.Driver",
}

# Schema actualizado — incluye 'hora'
SCHEMA = StructType([
    StructField("fecha",           StringType(), True),
    StructField("hora",            StringType(), True),
    StructField("producto",        StringType(), True),
    StructField("cod_producto",    StringType(), True),
    StructField("marca",           StringType(), True),
    StructField("categoria",       StringType(), True),
    StructField("subcategoria",    StringType(), True),
    StructField("cantidad",        StringType(), True),
    StructField("precio_unitario", StringType(), True),
    StructField("total",           StringType(), True),
    StructField("cliente",         StringType(), True),
    StructField("ruc_cliente",     StringType(), True),
    StructField("vendedor",        StringType(), True),
    StructField("razon_social",    StringType(), True),
    StructField("zona",            StringType(), True),
    StructField("_doc_id",         LongType(),   True),
    StructField("_archivo",        StringType(), True),
    StructField("_parseado_en",    StringType(), True),
])

# DDL de la tabla corregida (columnas nuevas)
DDL_SCORED_V2 = """
CREATE TABLE IF NOT EXISTS ventas_ml_scored (
    id                 BIGSERIAL PRIMARY KEY,
    batch_id           BIGINT,
    producto           TEXT,
    fecha              DATE,
    ventas_hoy         NUMERIC(14,2),
    prediccion_hoy     NUMERIC(14,2),
    pred_low           NUMERIC(14,2),
    pred_high          NUMERIC(14,2),
    pct_completado     NUMERIC(8,2),
    alerta             TEXT,
    procesado_ts       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mlscored_producto ON ventas_ml_scored (producto);
CREATE INDEX IF NOT EXISTS idx_mlscored_fecha    ON ventas_ml_scored (fecha);
CREATE INDEX IF NOT EXISTS idx_mlscored_alerta   ON ventas_ml_scored (alerta);
CREATE INDEX IF NOT EXISTS idx_mlscored_ts       ON ventas_ml_scored (procesado_ts)
"""


# ── Spark ─────────────────────────────────────────────────────────────────────

def build_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("CasaMarket-ML-Streaming-v2")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.port", "4040")
        .getOrCreate()
    )


# ── Setup de tablas ───────────────────────────────────────────────────────────

def ensure_table() -> None:
    """Crea o migra ventas_ml_scored a la nueva estructura."""
    try:
        engine = sa.create_engine(PG_SA_URL)

        # 1. Crear tabla base + migrar columnas (en una sola transacción)
        with engine.begin() as conn:
            conn.execute(sa.text("""
                CREATE TABLE IF NOT EXISTS ventas_ml_scored (
                    id             BIGSERIAL PRIMARY KEY,
                    batch_id       BIGINT,
                    producto       TEXT,
                    fecha          DATE,
                    ventas_hoy     NUMERIC(14,2),
                    prediccion_hoy NUMERIC(14,2),
                    pred_low       NUMERIC(14,2),
                    pred_high      NUMERIC(14,2),
                    pct_completado NUMERIC(8,2),
                    alerta         TEXT,
                    procesado_ts   TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            # Migrar columnas si la tabla ya existía con estructura vieja
            for stmt in [
                "ALTER TABLE ventas_ml_scored ADD COLUMN IF NOT EXISTS fecha DATE",
                "ALTER TABLE ventas_ml_scored ADD COLUMN IF NOT EXISTS ventas_hoy NUMERIC(14,2)",
                "ALTER TABLE ventas_ml_scored ADD COLUMN IF NOT EXISTS prediccion_hoy NUMERIC(14,2)",
                "ALTER TABLE ventas_ml_scored ADD COLUMN IF NOT EXISTS pred_low NUMERIC(14,2)",
                "ALTER TABLE ventas_ml_scored ADD COLUMN IF NOT EXISTS pred_high NUMERIC(14,2)",
                "ALTER TABLE ventas_ml_scored ADD COLUMN IF NOT EXISTS pct_completado NUMERIC(8,2)",
            ]:
                try:
                    conn.execute(sa.text(stmt))
                except Exception:
                    pass

        # 2. Crear índices en transacción separada (columnas ya garantizadas)
        with engine.begin() as conn:
            for idx in [
                "CREATE INDEX IF NOT EXISTS idx_mlscored_producto ON ventas_ml_scored (producto)",
                "CREATE INDEX IF NOT EXISTS idx_mlscored_fecha    ON ventas_ml_scored (fecha)",
                "CREATE INDEX IF NOT EXISTS idx_mlscored_alerta   ON ventas_ml_scored (alerta)",
                "CREATE INDEX IF NOT EXISTS idx_mlscored_ts       ON ventas_ml_scored (procesado_ts)",
            ]:
                try:
                    conn.execute(sa.text(idx))
                except Exception:
                    pass

        engine.dispose()
        log.info("[INIT] Tabla ventas_ml_scored verificada/migrada.")
    except Exception as exc:
        log.warning("[INIT] %s", exc)


# ── Carga de predicciones diarias ─────────────────────────────────────────────

def cargar_predicciones_hoy() -> dict:
    """
    Lee predicciones para HOY desde predicciones_diarias.
    Retorna dict: { producto: {pred, low, high} }
    """
    hoy = date.today().isoformat()
    try:
        engine = sa.create_engine(PG_SA_URL)
        with engine.connect() as conn:
            rows = conn.execute(sa.text("""
                SELECT producto, ingresos_pred, ingresos_low, ingresos_high
                FROM predicciones_diarias
                WHERE fecha_pred = :hoy
            """), {"hoy": hoy}).fetchall()
        engine.dispose()

        preds = {}
        for row in rows:
            preds[str(row[0]).strip()] = {
                "pred": float(row[1] or 0),
                "low":  float(row[2] or 0),
                "high": float(row[3] or 0),
            }
        log.info("[MODELO] %d predicciones diarias cargadas para %s", len(preds), hoy)
        return preds

    except Exception as exc:
        log.error("[MODELO] Error cargando predicciones_diarias: %s", exc)
        log.warning("[MODELO] Asegurate de que ml/trainer.py haya corrido al menos una vez.")
        return {}


def cargar_acumulado_hoy() -> dict:
    """
    Consulta el acumulado real de ventas del dia actual desde la tabla ventas.
    Retorna dict: { producto: total_soles }
    Este enfoque es mas correcto que sumar solo el micro-batch.
    """
    hoy = date.today().isoformat()
    try:
        engine = sa.create_engine(PG_SA_URL)
        with engine.connect() as conn:
            rows = conn.execute(sa.text("""
                SELECT TRIM(producto) AS producto, ROUND(SUM(total)::NUMERIC, 2) AS ventas_hoy
                FROM ventas
                WHERE fecha = :hoy AND total > 0
                GROUP BY TRIM(producto)
            """), {"hoy": hoy}).fetchall()
        engine.dispose()
        return {str(r[0]).strip(): float(r[1] or 0) for r in rows}
    except Exception as exc:
        log.error("[ACUMULADO] Error: %s", exc)
        return {}


# ── foreachBatch ──────────────────────────────────────────────────────────────

def make_batch_fn(spark: SparkSession):
    """Genera la funcion foreachBatch con logica de scoring corregida."""

    def process_batch(batch_df, batch_id: int):
        if batch_df.isEmpty():
            log.info("[batch=%d] vacio, saltando.", batch_id)
            return

        # 1. Obtener predicciones del dia y acumulado real desde PostgreSQL
        preds       = cargar_predicciones_hoy()
        acumulado   = cargar_acumulado_hoy()
        hoy         = date.today()

        if not preds:
            log.warning("[batch=%d] Sin predicciones diarias — el scoring no puede ejecutarse.", batch_id)
            return

        # 2. Construir scored list comparando acumulado vs prediccion
        scored = []
        # Union de productos con prediccion y/o ventas hoy
        productos = set(preds.keys()) | set(acumulado.keys())

        for producto in productos:
            ventas_hoy   = acumulado.get(producto, 0.0)
            pred_info    = preds.get(producto, {"pred": 0, "low": 0, "high": 0})
            pred_hoy     = pred_info["pred"]
            pred_low     = pred_info["low"]
            pred_high    = pred_info["high"]

            if ventas_hoy <= 0:
                continue   # sin ventas hoy, no tiene sentido mostrar la alerta

            # Porcentaje de la meta diaria alcanzado
            pct = round((ventas_hoy / pred_hoy * 100), 2) if pred_hoy > 0 else 0.0

            # Clasificacion basada en intervalo de confianza
            if pred_high > 0 and ventas_hoy > pred_high:
                alerta = "SOBRE_META"
            elif pred_low > 0 and ventas_hoy >= pred_low:
                alerta = "EN_META"
            elif pred_hoy > 0 and ventas_hoy >= pred_hoy * 0.5:
                alerta = "EN_RIESGO"
            else:
                alerta = "BAJO_META"

            scored.append({
                "batch_id":        batch_id,
                "producto":        producto,
                "fecha":           hoy,
                "ventas_hoy":      round(ventas_hoy, 2),
                "prediccion_hoy":  round(pred_hoy, 2),
                "pred_low":        round(pred_low, 2),
                "pred_high":       round(pred_high, 2),
                "pct_completado":  pct,
                "alerta":          alerta,
                "procesado_ts":    datetime.now(timezone.utc),
            })

        if not scored:
            return

        # 3. Escribir en PostgreSQL via SQLAlchemy (mas confiable que JDBC para Pandas DF)
        try:
            import pandas as pd
            df_scored = pd.DataFrame(scored)
            engine = sa.create_engine(PG_SA_URL)
            df_scored.to_sql("ventas_ml_scored", engine, if_exists="append", index=False)
            engine.dispose()
            log.info(
                "[ML] batch=%d | %d productos evaluados | escritos en ventas_ml_scored",
                batch_id, len(scored),
            )
        except Exception as exc:
            log.error("[ML] batch=%d ERROR PostgreSQL: %s", batch_id, exc)

        # 4. Imprimir alertas relevantes en consola
        sobre = [r for r in scored if r["alerta"] == "SOBRE_META"]
        meta  = [r for r in scored if r["alerta"] == "EN_META"]
        risg  = [r for r in scored if r["alerta"] == "EN_RIESGO"]
        bajo  = [r for r in scored if r["alerta"] == "BAJO_META"]

        log.info("=" * 70)
        log.info("  SCORING DIARIO — batch %d | %s", batch_id, hoy.strftime("%Y-%m-%d"))
        log.info("  SOBRE_META=%d  EN_META=%d  EN_RIESGO=%d  BAJO_META=%d",
                 len(sobre), len(meta), len(risg), len(bajo))
        log.info("  %-38s %10s %10s %8s %s",
                 "PRODUCTO", "REAL S/", "PRED S/", "% META", "ESTADO")
        log.info("-" * 70)
        for r in sorted(scored, key=lambda x: -x["pct_completado"])[:15]:
            log.info("  %-38s %10.2f %10.2f %7.1f%%  %s",
                     r["producto"][:38], r["ventas_hoy"],
                     r["prediccion_hoy"], r["pct_completado"], r["alerta"])
        log.info("=" * 70)

    return process_batch


# ── Stream ────────────────────────────────────────────────────────────────────

def parse_stream(spark: SparkSession):
    raw = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BROKER)
        .option("subscribe", TOPIC)
        .option("startingOffsets", "latest")   # evitar duplicados al reiniciar
        .option("failOnDataLoss", "false")
        .load()
    )
    return (
        raw
        .select(from_json(col("value").cast("string"), SCHEMA).alias("v"))
        .select("v.*")
        .withColumn("total_num",    col("total").cast(DoubleType()))
        .withColumn("fecha_dt",     to_date(col("fecha")))
        .withColumn("mes_num",      spark_month(col("fecha_dt")))
        .withColumn("procesado_ts", current_timestamp())
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    log.info("=" * 70)
    log.info("  CasaMarket ML Streaming v2 — Scoring en Tiempo Real")
    log.info("  Modelo: GradientBoosting diario (predicciones_diarias)")
    log.info("  Comparacion: acumulado real del dia vs prediccion diaria")
    log.info("  Umbrales: basados en intervalo de confianza del modelo")
    log.info("  Topic : %s", TOPIC)
    log.info("=" * 70)

    ensure_table()

    df = parse_stream(spark)

    query = (
        df
        .writeStream
        .outputMode("append")
        .foreachBatch(make_batch_fn(spark))
        .option("checkpointLocation", CHECKPOINT)
        .trigger(processingTime=TRIGGER)
        .start()
    )

    log.info("Streaming ML v2 activo — esperando ventas... (Ctrl+C para salir)")
    query.awaitTermination()


if __name__ == "__main__":
    main()

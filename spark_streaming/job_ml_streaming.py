"""
job_ml_streaming.py
===================
Spark Structured Streaming — Inferencia en tiempo real con el modelo ML
=======================================================================

Flujo:
  1. Al arrancar carga las predicciones mensuales 2026 (LinearRegression
     ya entrenado) desde PostgreSQL → predicciones_2026
  2. Consume casamarket.ventas.raw en tiempo real (micro-batch 30 s)
  3. Por cada batch agrega ventas por (producto, mes) y compara contra
     la predicción del modelo:
       - prediccion_mensual  → lo que el modelo esperaba para ese mes
       - total_batch         → lo que llegó en este micro-batch
       - pct_contribucion    → total_batch / prediccion_mensual * 100
       - alerta              → SOBRE_META / EN_META / BAJO_META
  4. Escribe en PostgreSQL → tabla ventas_ml_scored  (NO toca ventas)
  5. Imprime en consola las alertas más importantes cada 30 s

Levantar con:
    docker compose up -d spark-ml
"""
import logging
from datetime import datetime, timezone

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

# ── Configuración ─────────────────────────────────────────────────────────────
KAFKA_BROKER   = "ec-kafka:9092"
TOPIC          = "casamarket.ventas.raw"
OUTPUT_BASE    = "/home/jovyan/output"
CHECKPOINT     = f"{OUTPUT_BASE}/checkpoints/ml_streaming"
TRIGGER        = "30 seconds"

PG_URL   = "jdbc:postgresql://postgres:5432/casamarket"
PG_PROPS = {
    "user":     "casamarket",
    "password": "casamarket",
    "driver":   "org.postgresql.Driver",
}

# Schema igual al del parser existente (job_ventas.py)
SCHEMA = StructType([
    StructField("fecha",           StringType(), True),
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


# ── Spark ─────────────────────────────────────────────────────────────────────
def build_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("CasaMarket-ML-Streaming")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.port", "4040")
        .getOrCreate()
    )


# ── Tabla de salida ───────────────────────────────────────────────────────────
DDL_SCORED = """
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
"""


def ensure_table(spark: SparkSession) -> None:
    """Crea ventas_ml_scored si no existe usando SQLAlchemy."""
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(
            "postgresql://casamarket:casamarket@postgres:5432/casamarket"
        )
        with engine.begin() as conn:
            for stmt in DDL_SCORED.split(";"):
                s = stmt.strip()
                if s:
                    conn.execute(text(s))
        log.info("[INIT] Tabla ventas_ml_scored verificada/creada.")
    except Exception as e:
        log.warning("[INIT] No se pudo crear tabla via SQLAlchemy: %s", e)
        log.warning("[INIT] Asegúrate de que ventas_ml_scored exista en PostgreSQL.")


# ── Carga de predicciones del modelo ─────────────────────────────────────────
def load_predictions(spark: SparkSession) -> dict:
    """
    Lee predicciones_2026 desde PostgreSQL y devuelve un dict:
        { (producto, mes_int): ingresos_pred_float }

    Ejemplo: ("PEPSI 2000ML", 5) -> 8500.0
    """
    try:
        df = spark.read.jdbc(
            url=PG_URL,
            table="predicciones_2026",
            properties=PG_PROPS,
        )
        rows = df.select("producto", "mes", "ingresos_pred").collect()
        preds = {}
        for row in rows:
            if row["mes"] and row["producto"]:
                key = (str(row["producto"]).strip(), int(row["mes"].month))
                preds[key] = float(row["ingresos_pred"] or 0.0)
        n_prods = len({k[0] for k in preds})
        log.info(
            "[MODELO] Predicciones cargadas: %d entradas para %d productos",
            len(preds), n_prods,
        )
        return preds
    except Exception as e:
        log.error("[MODELO] No se pudieron cargar predicciones: %s", e)
        log.error("[MODELO] Ejecuta primero: ml/prediccion_ventas.py")
        return {}


# ── Stream ────────────────────────────────────────────────────────────────────
def parse_stream(spark: SparkSession):
    raw = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BROKER)
        .option("subscribe", TOPIC)
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "false")
        .load()
    )
    df = (
        raw
        .select(from_json(col("value").cast("string"), SCHEMA).alias("v"))
        .select("v.*")
        .withColumn("total_num",  col("total").cast(DoubleType()))
        .withColumn("fecha_dt",   to_date(col("fecha")))
        .withColumn("mes_num",    spark_month(col("fecha_dt")))
        .withColumn("procesado_ts", current_timestamp())
    )
    return df


# ── foreachBatch: aplica modelo y escribe ─────────────────────────────────────
def make_batch_fn(spark: SparkSession, preds_bc):
    """Genera la función foreachBatch con las predicciones en broadcast."""

    def process_batch(batch_df, batch_id: int):
        if batch_df.isEmpty():
            log.info("[batch=%d] vacío, saltando.", batch_id)
            return

        preds = preds_bc.value  # {(producto, mes): ingresos_pred}

        # Agrega ventas del batch por (producto, mes)
        agg_rows = (
            batch_df
            .filter(col("producto").isNotNull() & col("total_num").isNotNull())
            .filter(col("total_num") > 0)
            .groupBy("producto", "mes_num")
            .agg(
                count("*").alias("n_ventas"),
                spark_sum("total_num").alias("total_batch"),
            )
            .collect()
        )

        scored = []
        for row in agg_rows:
            producto  = str(row["producto"]).strip()
            mes       = int(row["mes_num"]) if row["mes_num"] else 0
            total     = float(row["total_batch"] or 0)
            n_ventas  = int(row["n_ventas"] or 0)
            pred      = preds.get((producto, mes), 0.0)

            pct = round((total / pred) * 100, 4) if pred > 0 else 0.0

            # Clasificación según modelo
            if pct >= 5.0:
                alerta = "SOBRE_META"
            elif pct >= 1.0:
                alerta = "EN_META"
            else:
                alerta = "BAJO_META"

            scored.append({
                "batch_id":           batch_id,
                "producto":           producto,
                "mes":                mes,
                "n_ventas":           n_ventas,
                "total_batch":        round(total, 2),
                "prediccion_mensual": round(pred, 2),
                "pct_contribucion":   pct,
                "alerta":             alerta,
                "procesado_ts":       datetime.now(timezone.utc),
            })

        if not scored:
            return

        import pandas as pd
        result_df = spark.createDataFrame(pd.DataFrame(scored))

        # ── Escribir en PostgreSQL ─────────────────────────────────────────
        try:
            result_df.write.jdbc(
                url=PG_URL,
                table="ventas_ml_scored",
                mode="append",
                properties=PG_PROPS,
            )
            log.info(
                "[ML] batch=%d | %d productos evaluados | escritos en ventas_ml_scored",
                batch_id, len(scored),
            )
        except Exception as e:
            log.error("[ML] batch=%d ERROR PostgreSQL: %s", batch_id, e)

        # ── Alertas en consola ─────────────────────────────────────────────
        sobre_meta = [r for r in scored if r["alerta"] == "SOBRE_META"]
        en_meta    = [r for r in scored if r["alerta"] == "EN_META"]

        if sobre_meta or en_meta:
            log.info("=" * 65)
            log.info("  ALERTAS ML — batch %d", batch_id)
            log.info("  %-35s %6s %10s %8s %s",
                     "PRODUCTO", "MES", "BATCH S/", "% MES", "ESTADO")
            log.info("-" * 65)
            for r in sorted(scored, key=lambda x: -x["pct_contribucion"])[:15]:
                log.info("  %-35s %6d %10.2f %7.2f%%  %s",
                         r["producto"][:35], r["mes"],
                         r["total_batch"], r["pct_contribucion"],
                         r["alerta"])
            log.info("=" * 65)

    return process_batch


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    log.info("=" * 65)
    log.info("  CasaMarket — ML Streaming (inferencia en tiempo real)")
    log.info("  Modelo: LinearRegression por producto (predicciones_2026)")
    log.info("  Topic : %s", TOPIC)
    log.info("=" * 65)

    # 1. Crear tabla de salida si no existe
    ensure_table(spark)

    # 2. Cargar predicciones del modelo entrenado
    preds = load_predictions(spark)
    if not preds:
        log.warning("[MODELO] Sin predicciones — el job correrá pero sin scoring.")
    preds_bc = spark.sparkContext.broadcast(preds)

    # 3. Leer stream de Kafka
    df = parse_stream(spark)

    # 4. Aplicar modelo en foreachBatch y escribir en PostgreSQL
    query = (
        df
        .writeStream
        .outputMode("append")
        .foreachBatch(make_batch_fn(spark, preds_bc))
        .option("checkpointLocation", CHECKPOINT)
        .trigger(processingTime=TRIGGER)
        .start()
    )

    log.info("Streaming ML activo — esperando ventas... (Ctrl+C para salir)")
    query.awaitTermination()


if __name__ == "__main__":
    main()

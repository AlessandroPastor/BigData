"""
S7/S9 — Spark Streaming: casamarket.ventas.raw → Parquet + PostgreSQL + MySQL
===============================================================================
Consume las filas de ventas parseadas del Excel y las escribe en:
  - Parquet     → output/parquet/ventas/        (para S9 ML)
  - PostgreSQL  → tabla ventas                  (para Grafana dashboards)
  - MySQL       → tabla ventas_ifersan          (GestPPP en Laragon)
  - Consola     → resumen por producto cada 30s
"""
import logging

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, current_timestamp, round as spark_round,
    sum as spark_sum, to_date, to_timestamp, window,
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

KAFKA_BROKER = "ec-kafka:9092"
TOPIC        = "casamarket.ventas.raw"
OUTPUT_BASE  = "/home/jovyan/output"

PG_URL   = "jdbc:postgresql://postgres:5432/casamarket"
PG_PROPS = {"user": "casamarket", "password": "casamarket", "driver": "org.postgresql.Driver"}

# MySQL en Laragon — host.docker.internal apunta al localhost de Windows desde Docker
MYSQL_URL   = "jdbc:mysql://host.docker.internal:3306/GestPPP?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC"
MYSQL_PROPS = {"user": "root", "password": "", "driver": "com.mysql.cj.jdbc.Driver"}

CHECKPOINT_RAW   = f"{OUTPUT_BASE}/checkpoints/ventas_raw"
CHECKPOINT_AGG   = f"{OUTPUT_BASE}/checkpoints/ventas_agg"
TRIGGER_SECS     = "30 seconds"

# Schema flexible — capturamos los campos estándar normalizados por el parser
SCHEMA = StructType([
    StructField("fecha",          StringType(), True),
    StructField("producto",       StringType(), True),
    StructField("cod_producto",   StringType(), True),
    StructField("marca",          StringType(), True),
    StructField("categoria",      StringType(), True),
    StructField("subcategoria",   StringType(), True),
    StructField("cantidad",       StringType(), True),
    StructField("precio_unitario", StringType(), True),
    StructField("total",          StringType(), True),
    StructField("cliente",        StringType(), True),
    StructField("ruc_cliente",    StringType(), True),
    StructField("vendedor",       StringType(), True),
    StructField("razon_social",   StringType(), True),
    StructField("zona",           StringType(), True),
    StructField("_doc_id",        LongType(),   True),
    StructField("_archivo",       StringType(), True),
    StructField("_parseado_en",   StringType(), True),
])


def build_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("CasaMarket-Ventas-Streaming")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.port", "4040")
        .getOrCreate()
    )


def parse_stream(spark: SparkSession):
    from pyspark.sql.functions import from_json
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
        .withColumn("procesado_ts", current_timestamp())
        .withColumn("cantidad_num",  col("cantidad").cast(DoubleType()))
        .withColumn("precio_num",    col("precio_unitario").cast(DoubleType()))
        .withColumn("total_num",     col("total").cast(DoubleType()))
        .withColumn("fecha_dt",      to_date(col("fecha")))
    )
    return df


def _preparar_ventas(batch_df):
    """Selecciona y renombra columnas comunes para ambos sinks."""
    return (
        batch_df
        .select(
            col("fecha_dt").alias("fecha"),
            col("producto"),
            col("cod_producto"),
            col("marca"),
            col("categoria"),
            col("subcategoria"),
            col("cantidad_num").alias("cantidad"),
            col("precio_num").alias("precio_unitario"),
            col("total_num").alias("total"),
            col("cliente"),
            col("ruc_cliente"),
            col("vendedor"),
            col("razon_social"),
            col("zona"),
            col("_doc_id").alias("doc_id"),
            col("_archivo").alias("archivo"),
            col("procesado_ts"),
        )
    )


def write_to_postgres_and_mysql(batch_df, batch_id):
    """Escribe cada micro-batch en PostgreSQL y MySQL simultáneamente."""
    if batch_df.isEmpty():
        return

    ventas = _preparar_ventas(batch_df)
    # cache para no releer Kafka dos veces
    ventas.cache()
    n = ventas.count()

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    try:
        ventas.write.jdbc(url=PG_URL, table="ventas", mode="append", properties=PG_PROPS)
        log.info("[PG]    batch=%d  filas=%d → ventas", batch_id, n)
    except Exception as e:
        log.error("[PG]    batch=%d  ERROR: %s", batch_id, e)

    # ── MySQL (Laragon / GestPPP) ─────────────────────────────────────────────
    try:
        ventas.write.jdbc(url=MYSQL_URL, table="ventas_ifersan", mode="append", properties=MYSQL_PROPS)
        log.info("[MySQL] batch=%d  filas=%d → ventas_ifersan", batch_id, n)
    except Exception as e:
        log.error("[MySQL] batch=%d  ERROR: %s", batch_id, e)

    ventas.unpersist()


def main():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    log.info("=== Spark Ventas Streaming ===")
    log.info("Topic  : %s", TOPIC)
    log.info("Output : %s", OUTPUT_BASE)

    df = parse_stream(spark)

    # ── Sink 1: ventas raw → Parquet (para ML en S9) ─────────────────────────
    q_parquet = (
        df
        .writeStream
        .outputMode("append")
        .format("parquet")
        .option("path", f"{OUTPUT_BASE}/parquet/ventas/")
        .option("checkpointLocation", CHECKPOINT_RAW)
        .trigger(processingTime=TRIGGER_SECS)
        .start()
    )
    log.info("Query 1: ventas raw → Parquet")

    # ── Sink 2: ventas → PostgreSQL + MySQL (foreachBatch) ──────────────────
    q_postgres = (
        df
        .writeStream
        .outputMode("append")
        .foreachBatch(write_to_postgres_and_mysql)
        .option("checkpointLocation", CHECKPOINT_AGG)
        .trigger(processingTime=TRIGGER_SECS)
        .start()
    )
    log.info("Query 2: ventas → PostgreSQL + MySQL (GestPPP)")

    # ── Sink 3: top productos → consola ──────────────────────────────────────
    q_console = (
        df
        .filter(col("producto").isNotNull())
        .groupBy("producto")
        .agg(
            count("*").alias("transacciones"),
            spark_round(spark_sum("total_num"), 2).alias("total_soles"),
        )
        .orderBy(col("total_soles").desc())
        .writeStream
        .outputMode("complete")
        .format("console")
        .option("truncate", "false")
        .option("numRows", "15")
        .trigger(processingTime=TRIGGER_SECS)
        .start()
    )
    log.info("Query 3: top productos → consola")

    log.info("Esperando ventas... (Ctrl+C para salir)")
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()

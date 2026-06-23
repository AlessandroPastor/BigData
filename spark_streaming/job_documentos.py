"""
S7 — Spark Structured Streaming
Consume topic 'casamarket.documento.detectado' y escribe:
  - Parquet raw   → output/parquet/documentos/   (para S9 ML)
  - Parquet aggs  → output/parquet/por_extension/ (agregaciones por fecha/extensión)
  - Consola       → resumen por extensión cada 30 s
  - Métricas S8   → output/parquet/metricas/      (latencia, throughput, errores)
"""
import logging

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, current_timestamp, expr, from_json,
    to_date, to_timestamp, unix_timestamp, window,
)
from pyspark.sql.types import LongType, StringType, StructField, StructType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

KAFKA_BROKER     = "ec-kafka:9092"
TOPIC            = "casamarket.documento.detectado"
OUTPUT_BASE      = "/home/jovyan/output"
CHECKPOINT_RAW   = f"{OUTPUT_BASE}/checkpoints/raw"
CHECKPOINT_AGG   = f"{OUTPUT_BASE}/checkpoints/agg"
CHECKPOINT_WIN   = f"{OUTPUT_BASE}/checkpoints/ventanas"
CHECKPOINT_MET   = f"{OUTPUT_BASE}/checkpoints/metricas"
TRIGGER_SECS     = "30 seconds"

SCHEMA = StructType([
    StructField("id",           LongType(),   True),
    StructField("filename",     StringType(), True),
    StructField("extension",    StringType(), True),
    StructField("status",       StringType(), True),
    StructField("url_file",     StringType(), True),
    StructField("created_at",   StringType(), True),
    StructField("usuario",      StringType(), True),
    StructField("detectado_en", StringType(), True),
])


def build_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("CasaMarket-S7-Streaming")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.port", "4040")
        .getOrCreate()
    )


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
    return (
        raw
        .withColumn("kafka_ts",     col("timestamp"))           # timestamp Kafka
        .withColumn("procesado_ts", current_timestamp())        # timestamp Spark
        .select(
            from_json(col("value").cast("string"), SCHEMA).alias("d"),
            col("kafka_ts"),
            col("procesado_ts"),
        )
        .select("d.*", "kafka_ts", "procesado_ts")
        .withColumn("fecha",         to_date(col("created_at")))
        .withColumn("detectado_ts",  to_timestamp(col("detectado_en")))
        # latencia = segundos entre que Kafka recibió el mensaje y Spark lo procesó
        .withColumn("latencia_ms", (
            unix_timestamp(col("procesado_ts")) - unix_timestamp(col("kafka_ts"))
        ).cast("long") * 1000)
    )


def main():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    log.info("=== Spark Structured Streaming — S7 + S8 ===")
    log.info("Topic  : %s", TOPIC)
    log.info("Broker : %s", KAFKA_BROKER)
    log.info("Output : %s", OUTPUT_BASE)
    log.info("Spark UI -> http://localhost:4041")

    df = parse_stream(spark)

    # ── Sink 1: eventos raw → Parquet (sin url_file) ──────────────────────────
    q_parquet = (
        df
        .drop("url_file")
        .writeStream
        .outputMode("append")
        .format("parquet")
        .option("path", f"{OUTPUT_BASE}/parquet/documentos/")
        .option("checkpointLocation", CHECKPOINT_RAW)
        .trigger(processingTime=TRIGGER_SECS)
        .start()
    )
    log.info("Query 1 activa: raw → Parquet")

    # ── Sink 2: conteo por extensión → consola ────────────────────────────────
    q_console = (
        df
        .groupBy("extension")
        .agg(count("*").alias("total"))
        .orderBy(col("total").desc())
        .writeStream
        .outputMode("complete")
        .format("console")
        .option("truncate", "false")
        .option("numRows", "20")
        .trigger(processingTime=TRIGGER_SECS)
        .start()
    )
    log.info("Query 2 activa: conteo por extensión → consola")

    # ── Sink 3: ventana de tiempo + watermark → Parquet ───────────────────────
    # Cuenta eventos por ventana de 5 min con watermark de 10 min
    q_ventanas = (
        df
        .withWatermark("detectado_ts", "10 minutes")
        .groupBy(
            window(col("detectado_ts"), "5 minutes"),
            col("extension"),
        )
        .agg(count("*").alias("eventos_ventana"))
        .writeStream
        .outputMode("append")
        .format("parquet")
        .option("path", f"{OUTPUT_BASE}/parquet/por_extension/")
        .option("checkpointLocation", CHECKPOINT_WIN)
        .trigger(processingTime=TRIGGER_SECS)
        .start()
    )
    log.info("Query 3 activa: ventanas 5 min + watermark 10 min → Parquet")

    # ── Sink 4 (S8): métricas de latencia → Parquet ──────────────────────────
    q_metricas = (
        df
        .select("id", "extension", "kafka_ts", "procesado_ts", "latencia_ms")
        .writeStream
        .outputMode("append")
        .format("parquet")
        .option("path", f"{OUTPUT_BASE}/parquet/metricas/")
        .option("checkpointLocation", CHECKPOINT_MET)
        .trigger(processingTime=TRIGGER_SECS)
        .start()
    )
    log.info("Query 4 activa: métricas latencia → Parquet  (para S9 ML)")

    log.info("Esperando mensajes... (Ctrl+C para salir)")
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()

"""
replay_ventas.py
================
Re-inyecta las ventas históricas de PostgreSQL → casamarket.ventas.raw
para que el job_ml_streaming.py tenga datos que procesar.

Uso rápido:
    docker compose exec producer python /app/producer/replay_ventas.py

O desde fuera del contenedor:
    docker run --rm --network ec-kafka-dev-net \
        -v $(pwd)/producer:/app/producer \
        casamarket-python:latest \
        python /app/producer/replay_ventas.py
"""
import json
import logging
import time

import psycopg2
from kafka import KafkaProducer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = "ec-kafka:9092"
TOPIC           = "casamarket.ventas.raw"
BATCH_SIZE      = 500      # filas por lote
DELAY_BETWEEN   = 0.5      # segundos entre lotes (para que Spark los procese)

PG_CONN = {
    "host":     "postgres",
    "port":     5432,
    "dbname":   "casamarket",
    "user":     "casamarket",
    "password": "casamarket",
}

SQL = """
SELECT
    fecha::TEXT          AS fecha,
    producto,
    cod_producto,
    marca,
    categoria,
    subcategoria,
    cantidad::TEXT       AS cantidad,
    precio_unitario::TEXT AS precio_unitario,
    total::TEXT          AS total,
    cliente,
    ruc_cliente,
    vendedor,
    razon_social,
    zona,
    doc_id               AS _doc_id,
    archivo              AS _archivo,
    procesado_ts::TEXT   AS _parseado_en
FROM ventas
WHERE total > 0
ORDER BY fecha, id
"""


def main():
    log.info("=== Replay Ventas PostgreSQL → Kafka ===")
    log.info("Topic destino: %s", TOPIC)

    # ── Conectar a PostgreSQL ─────────────────────────────────────────────────
    try:
        conn = psycopg2.connect(**PG_CONN)
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ventas WHERE total > 0")
        total_rows = cur.fetchone()[0]
        log.info("Ventas a re-publicar: %d filas", total_rows)
    except Exception as e:
        log.error("No se pudo conectar a PostgreSQL: %s", e)
        return

    # ── Conectar a Kafka ──────────────────────────────────────────────────────
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            acks="all",
            retries=3,
        )
        log.info("Conectado a Kafka: %s", KAFKA_BOOTSTRAP)
    except Exception as e:
        log.error("No se pudo conectar a Kafka: %s", e)
        conn.close()
        return

    # ── Publicar en lotes ─────────────────────────────────────────────────────
    cur.execute(SQL)
    cols = [desc[0] for desc in cur.description]

    publicados  = 0
    lote_actual = 0

    while True:
        rows = cur.fetchmany(BATCH_SIZE)
        if not rows:
            break

        lote_actual += 1
        for row in rows:
            msg = dict(zip(cols, row))
            producer.send(TOPIC, value=msg)
            publicados += 1

        producer.flush()
        log.info(
            "[lote=%d] publicados: %d / %d",
            lote_actual, publicados, total_rows,
        )

        if lote_actual % 5 == 0:
            time.sleep(DELAY_BETWEEN)

    producer.flush()
    producer.close()
    cur.close()
    conn.close()

    log.info("=" * 55)
    log.info("  DONE — %d mensajes publicados en '%s'", publicados, TOPIC)
    log.info("  El job_ml_streaming los procesará en el próximo trigger.")
    log.info("=" * 55)


if __name__ == "__main__":
    main()

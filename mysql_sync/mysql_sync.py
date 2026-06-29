"""
MySQL Sync — Consume topic Debezium de PostgreSQL → inserta en MySQL (Laragon)
==============================================================================
Escucha: casamarket.public.ventas  (topic generado por Debezium)
Escribe: MySQL  casamarket_mysql.ventas
"""
import json
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone

import pymysql
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "ec-kafka:9092")
TOPIC           = "casamarket.public.ventas"   # generado por Debezium automáticamente

MYSQL_HOST      = os.getenv("MYSQL_HOST",     "host.docker.internal")
MYSQL_PORT      = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DB        = os.getenv("MYSQL_DB",       "casamarket_mysql")
MYSQL_USER      = os.getenv("MYSQL_USER",     "root")
MYSQL_PASSWORD  = os.getenv("MYSQL_PASSWORD", "")

INSERT_SQL = """
INSERT INTO ventas (
    fecha, producto, cod_producto, marca, categoria, subcategoria,
    cantidad, precio_unitario, total, cliente, ruc_cliente,
    vendedor, razon_social, zona, doc_id, archivo, procesado_ts
) VALUES (
    %(fecha)s, %(producto)s, %(cod_producto)s, %(marca)s, %(categoria)s, %(subcategoria)s,
    %(cantidad)s, %(precio_unitario)s, %(total)s, %(cliente)s, %(ruc_cliente)s,
    %(vendedor)s, %(razon_social)s, %(zona)s, %(doc_id)s, %(archivo)s, %(procesado_ts)s
)
"""


def connect_mysql(retries: int = 0, max_retries: int = 0):
    """Conecta a MySQL. Con max_retries>0 reintenta con backoff exponencial."""
    attempt = 0
    while True:
        try:
            return pymysql.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                database=MYSQL_DB,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                charset="utf8mb4",
                autocommit=False,
                connect_timeout=10,
            )
        except pymysql.err.OperationalError as exc:
            attempt += 1
            if max_retries > 0 and attempt > max_retries:
                raise
            wait = min(30, 5 * attempt)
            log.warning("[MySQL] No disponible (%s). Reintentando en %ds... (%d)", exc.args[1], wait, attempt)
            time.sleep(wait)


def connect_kafka():
    for i in range(15):
        try:
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id="mysql-sync-group",
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None,
                consumer_timeout_ms=5000,
            )
            log.info("Kafka conectado. Escuchando: %s", TOPIC)
            return consumer
        except NoBrokersAvailable:
            log.warning("Kafka no disponible, reintentando en 10s... (%d/15)", i + 1)
            time.sleep(10)
    raise RuntimeError("No se pudo conectar a Kafka.")


EPOCH = date(1970, 1, 1)

def conv_fecha(val):
    """Debezium DATE → días desde epoch → 'YYYY-MM-DD'."""
    if val is None:
        return None
    if isinstance(val, int):
        return (EPOCH + timedelta(days=val)).strftime("%Y-%m-%d")
    # ya es string como '2026-05-15'
    return str(val)[:10]

def conv_ts(val):
    """Debezium TIMESTAMPTZ → microsegundos epoch o string ISO → 'YYYY-MM-DD HH:MM:SS'."""
    if val is None:
        return None
    if isinstance(val, int):
        # microsegundos desde epoch
        return datetime.fromtimestamp(val / 1_000_000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(val, str):
        # '2026-05-26T04:25:43.897000Z'  →  '2026-05-26 04:25:43'
        return val.replace("T", " ").replace("Z", "")[:19]
    return str(val)


def extraer_fila(payload_after: dict) -> dict:
    """Mapea el payload de Debezium al dict para MySQL convirtiendo tipos."""
    return {
        "fecha":           conv_fecha(payload_after.get("fecha")),
        "producto":        payload_after.get("producto"),
        "cod_producto":    payload_after.get("cod_producto"),
        "marca":           payload_after.get("marca"),
        "categoria":       payload_after.get("categoria"),
        "subcategoria":    payload_after.get("subcategoria"),
        "cantidad":        payload_after.get("cantidad"),
        "precio_unitario": payload_after.get("precio_unitario"),
        "total":           payload_after.get("total"),
        "cliente":         payload_after.get("cliente"),
        "ruc_cliente":     payload_after.get("ruc_cliente"),
        "vendedor":        payload_after.get("vendedor"),
        "razon_social":    payload_after.get("razon_social"),
        "zona":            payload_after.get("zona"),
        "doc_id":          payload_after.get("doc_id"),
        "archivo":         payload_after.get("archivo"),
        "procesado_ts":    conv_ts(payload_after.get("procesado_ts")),
    }


def main():
    log.info("=== MySQL Sync — Debezium CDC ===")
    log.info("Topic  : %s", TOPIC)
    log.info("MySQL  : %s:%d / %s", MYSQL_HOST, MYSQL_PORT, MYSQL_DB)

    consumer = connect_kafka()
    mysql    = connect_mysql(max_retries=0)   # retry infinito hasta que MySQL esté disponible
    cursor   = mysql.cursor()

    insertados = 0
    log.info("Sincronizando... (Ctrl+C para salir)")

    try:
        while True:
            try:
                batch = consumer.poll(timeout_ms=5000, max_records=200)

                if not batch:
                    continue

                filas = []
                for tp, mensajes in batch.items():
                    for msg in mensajes:
                        if not msg.value:
                            continue
                        payload = msg.value.get("payload", {})
                        op      = payload.get("op")          # c=insert, u=update, d=delete, r=snapshot

                        if op in ("c", "r", "u") and payload.get("after"):
                            filas.append(extraer_fila(payload["after"]))
                        elif op == "d":
                            log.debug("DELETE ignorado — id en after=None")

                if filas:
                    cursor.executemany(INSERT_SQL, filas)
                    mysql.commit()
                    insertados += len(filas)
                    log.info("[MySQL] +%d filas insertadas | Total acumulado: %d", len(filas), insertados)

                consumer.commit()

            except pymysql.Error as e:
                log.error("Error MySQL: %s — reconectando...", e)
                mysql.rollback()
                try:
                    mysql = connect_mysql()
                    cursor = mysql.cursor()
                except Exception:
                    time.sleep(5)

            except Exception as e:
                log.error("Error inesperado: %s", e)
                time.sleep(3)

    except KeyboardInterrupt:
        log.info("Detenido. Total insertado en MySQL: %d filas", insertados)
    finally:
        cursor.close()
        mysql.close()
        consumer.close()


if __name__ == "__main__":
    main()

"""
Consumer Downloader
Escucha 'casamarket.documento.detectado' y descarga cada archivo
nuevo desde su URL S3 a output/descargas/.

Ejecutar desde la raíz del proyecto:
    .venv\Scripts\python consumer\consumer_downloader.py
"""
import json
import logging
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

TOPIC        = "casamarket.documento.detectado"
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "output/descargas"))
STATE_FILE   = Path(__file__).parent / "state_downloads.json"


# ── Estado persistente ─────────────────────────────────────────────────────────

def load_downloaded() -> set[int]:
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return set(data.get("ids", []))
    return set()


def save_downloaded(ids: set[int]) -> None:
    STATE_FILE.write_text(
        json.dumps({"ids": sorted(ids)}, indent=2),
        encoding="utf-8",
    )


# ── Descarga ───────────────────────────────────────────────────────────────────

def download_file(url: str, filename: str, extension: str) -> Path:
    safe_name = re.sub(r'[<>:"/\\|?*]', "_", filename)
    output_path = DOWNLOAD_DIR / f"{safe_name}.{extension}"

    if output_path.exists():
        return output_path

    resp = requests.get(url, timeout=60, stream=True)
    resp.raise_for_status()

    with output_path.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return output_path


# ── Kafka ──────────────────────────────────────────────────────────────────────

def make_consumer(bootstrap: str) -> KafkaConsumer:
    return KafkaConsumer(
        TOPIC,
        bootstrap_servers=bootstrap,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="casamarket-downloader",
    )


# ── Loop principal ─────────────────────────────────────────────────────────────

def main() -> None:
    load_dotenv()

    bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:19092")
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    log.info("=== Consumer Downloader ===")
    log.info("Broker  : %s", bootstrap)
    log.info("Topic   : %s", TOPIC)
    log.info("Destino : %s", DOWNLOAD_DIR.resolve())

    consumer = None
    for intento in range(10):
        try:
            consumer = make_consumer(bootstrap)
            log.info("Conectado a Kafka.")
            break
        except NoBrokersAvailable:
            log.warning("Kafka no disponible, reintentando en 10s... (%d/10)", intento + 1)
            time.sleep(10)
    if consumer is None:
        raise RuntimeError("No se pudo conectar a Kafka tras 10 intentos.")

    descargados = load_downloaded()
    log.info("Ya descargados: %d archivos", len(descargados))

    for message in consumer:
        evento  = message.value
        doc_id  = evento.get("id")
        url     = evento.get("url_file", "")
        filename  = evento.get("filename", f"doc_{doc_id}")
        extension = evento.get("extension", "xlsx")
        usuario   = evento.get("usuario", "")

        if doc_id in descargados:
            continue

        # Solo descargar documentos finalizados (status=2 → "Finalizado")
        # Los demás están incompletos y el Excel puede estar vacío
        status = evento.get("status")
        if status != 2:
            log.debug("Omitiendo id=%-8s status=%s (no Finalizado)", doc_id, status)
            continue

        if not url:
            log.warning("Sin url_file id=%-8s  %s — omitiendo", doc_id, filename[:50])
            descargados.add(doc_id)
            save_downloaded(descargados)
            continue

        try:
            saved = download_file(url, filename, extension)
            size_kb = saved.stat().st_size / 1024
            log.info(
                "  [OK] id=%-8s  %-6s  %5.1f KB  %s",
                doc_id, extension.upper(), size_kb, saved.name[:60],
            )
            descargados.add(doc_id)
            save_downloaded(descargados)
        except Exception as exc:
            log.error("  [ERR] id=%-8s  %s -> %s", doc_id, filename[:50], exc)


if __name__ == "__main__":
    main()

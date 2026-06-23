"""
Producer: monitorea la API de Casa Market y publica eventos
de documentos nuevos al topic Kafka 'casamarket.documento.detectado'.

Ejecutar desde la raiz del proyecto:
    .venv\Scripts\python producer\producer.py
"""
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

TOPIC      = "casamarket.documento.detectado"
STATE_FILE = Path(__file__).parent / "state_documentos.json"
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))

AUTH_URL      = "https://acl.casamarketapp.com/api/authenticate"
DOCUMENTS_URL = "https://n5.report.casamarketapp.com/documents"


# ── Estado persistente ─────────────────────────────────────────────────────────

def load_state() -> set[int]:
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return set(data.get("ids", []))
    return set()


def save_state(ids: set[int]) -> None:
    STATE_FILE.write_text(
        json.dumps({"ids": sorted(ids)}, indent=2),
        encoding="utf-8",
    )


# ── API Casa Market ────────────────────────────────────────────────────────────

def get_token(email: str, password: str) -> str:
    resp = requests.post(
        AUTH_URL,
        json={"email": email, "password": password, "codeApp": "quipuadmin"},
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json().get("token")
    if not token:
        raise RuntimeError("No se recibió token del servidor.")
    log.info("Autenticado. Token JWT obtenido.")
    return token


def fetch_all_documents(token: str, days_back: int = 30) -> list[dict]:
    end_date   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Origin": "https://admin.casamarket.la",
    }

    all_docs: list[dict] = []
    page = 1
    last_page = 1

    while page <= last_page:
        resp = requests.get(
            DOCUMENTS_URL,
            headers=headers,
            params={"startDate": start_date, "endDate": end_date, "limit": 50, "page": page},
            timeout=30,
        )
        resp.raise_for_status()
        last_page = int(resp.headers.get("x-last-page", 1))
        all_docs.extend(resp.json())
        log.debug("Página %d/%d — %d docs acumulados", page, last_page, len(all_docs))
        page += 1

    return all_docs


# ── Kafka ──────────────────────────────────────────────────────────────────────

def make_producer(bootstrap: str) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=bootstrap,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        key_serializer=lambda k: str(k).encode("utf-8"),
        acks="all",
        retries=3,
    )


def publicar(producer: KafkaProducer, doc: dict) -> None:
    evento = {
        "id":          doc["id"],
        "filename":    doc["filename"],
        "extension":   doc["extension"],
        "status":      doc.get("statusName", ""),
        "url_file":    doc.get("urlFile", ""),
        "created_at":  doc.get("createdAt", ""),
        "usuario":     doc.get("user", {}).get("email", ""),
        "detectado_en": datetime.now(timezone.utc).isoformat(),
    }
    producer.send(TOPIC, key=doc["id"], value=evento).get(timeout=10)
    log.info("  [Kafka] id=%-8d  %s", doc["id"], doc["filename"][:70])


# ── Loop principal ─────────────────────────────────────────────────────────────

def main() -> None:
    load_dotenv()

    email    = os.getenv("gmail", "").strip()
    password = os.getenv("password", "").strip()
    if not email or not password:
        raise ValueError("Faltan gmail/password en .env")

    bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:19092")
    days_back = int(os.getenv("DAYS_BACK", "30"))

    log.info("=== Producer Casa Market ===")
    log.info("Broker   : %s", bootstrap)
    log.info("Topic    : %s", TOPIC)
    log.info("Intervalo: %ds", POLL_INTERVAL_SECONDS)
    log.info("Rango    : últimos %d días", days_back)

    producer = None
    for intento in range(10):
        try:
            producer = make_producer(bootstrap)
            log.info("Conectado a Kafka.")
            break
        except NoBrokersAvailable:
            log.warning("Kafka no disponible, reintentando en 10s... (%d/10)", intento + 1)
            time.sleep(10)
    if producer is None:
        raise RuntimeError("No se pudo conectar a Kafka tras 10 intentos.")

    vistos = load_state()
    log.info("IDs ya conocidos: %d", len(vistos))

    while True:
        try:
            token = get_token(email, password)
            docs  = fetch_all_documents(token, days_back=days_back)
            log.info("Total en API: %d | Conocidos: %d", len(docs), len(vistos))

            nuevos = [d for d in docs if d["id"] not in vistos]

            # Log para verificar qué valores de status devuelve la API
            if nuevos:
                sample = nuevos[0]
                log.info("  [DEBUG] Campos status del primer doc nuevo: status=%r  statusName=%r",
                         sample.get("status"), sample.get("statusName"))

            STATUS_LISTO = 2   # ajustar si el log muestra un valor diferente
            listos     = [d for d in nuevos if d.get("status") == STATUS_LISTO]
            pendientes = [d for d in nuevos if d.get("status") != STATUS_LISTO]

            log.info("Nuevos: %d  |  Listos (status=%d): %d  |  Pendientes: %d",
                     len(nuevos), STATUS_LISTO, len(listos), len(pendientes))

            if pendientes:
                for d in pendientes:
                    log.info("  [SKIP] id=%-8d  status=%r  %s",
                             d["id"], d.get("status"), d["filename"][:60])

            if listos:
                for doc in listos:
                    publicar(producer, doc)
                    vistos.add(doc["id"])
                producer.flush()
                save_state(vistos)
            elif not nuevos:
                log.info("Sin cambios.")

        except Exception as exc:
            log.error("Error en ciclo: %s", exc)

        log.info("Próxima revisión en %ds...\n", POLL_INTERVAL_SECONDS)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

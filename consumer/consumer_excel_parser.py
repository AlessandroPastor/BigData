"""
Consumer Excel/HTML Parser  (S8 → S9 input)
=============================================
Escanea DOWNLOAD_DIR buscando archivos .xlsx y .html,
lee las filas de datos con pandas, y publica cada registro
como JSON en 'casamarket.ventas.raw'.

NO depende de que Kafka tenga mensajes previos para activarse:
escanea el directorio cada SCAN_INTERVAL segundos de forma continua.

Ejecutar local:
    .venv\\Scripts\\python consumer\\consumer_excel_parser.py
"""
import json
import logging
import os
import re
import time
import unicodedata
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

TOPIC_OUT     = "casamarket.ventas.raw"
DOWNLOAD_DIR  = Path(os.getenv("DOWNLOAD_DIR", "output/descargas"))
STATE_FILE    = Path(__file__).parent / "state_excel_parsed.json"
SCAN_INTERVAL = 60       # segundos entre escaneos del directorio
MIN_ROWS      = 1        # ignorar archivos sin filas de datos


# ── Normalización de columnas ──────────────────────────────────────────────────

_ALIAS = {
    # fecha
    "fecha": "fecha", "fecha_de_venta": "fecha", "date": "fecha",
    "fec": "fecha", "fecha_emision": "fecha", "fecharegistro": "fecha",
    "fecha_de_emision": "fecha", "fecha_doc": "fecha",
    # producto — solo mapear el nombre directo, no descripción
    "producto": "producto", "articulo": "producto", "item": "producto",
    "nombre_producto": "producto", "nombre": "producto",
    "descripcion_producto": "producto",
    # descripcion la dejamos como descripcion (NO sobreescribe producto)
    "cod_producto": "cod_producto", "codigo_producto": "cod_producto",
    "codigo": "cod_producto", "codigo_de_producto": "cod_producto",
    "codigo_sku": "cod_producto", "codigo_de_barra": "cod_producto",
    # cantidad
    "cantidad": "cantidad", "qty": "cantidad", "cant": "cantidad",
    "unidades": "cantidad", "cantidad_vendida": "cantidad",
    # precio / total
    "precio_unitario": "precio_unitario", "precio": "precio_unitario",
    "p_unit": "precio_unitario", "precio_unit": "precio_unitario",
    "costo_unitario": "precio_unitario",
    "total": "total", "monto_total": "total", "importe": "total",
    "total_venta": "total", "valor_total": "total", "subtotal": "total",
    "monto": "total", "importe_total": "total", "sub_total": "total",
    # cliente
    "cliente": "cliente", "nombre_cliente": "cliente",
    "cliente_nombre": "cliente",                 # ← "Cliente Nombre" del Excel
    "ruc": "ruc_cliente", "ruc_cliente": "ruc_cliente",
    "cliente_doc": "ruc_cliente", "dni": "ruc_cliente",
    # vendedor
    "vendedor": "vendedor", "preventista": "vendedor", "agente": "vendedor",
    "nombre_vendedor": "vendedor", "empleado": "vendedor",
    "empleado_nombre": "vendedor",               # ← "Empleado Nombre" del Excel
    # zona
    "zona": "zona", "region": "zona", "sucursal": "zona", "tienda": "zona",
    "distrito": "zona", "provincia": "zona",
    # campos extra de Casa Market
    "razon_social": "razon_social",
    "marca": "marca",
    "categoria": "categoria",
    "sub_categoria": "subcategoria",
}


def _norm(col: str) -> str:
    col = unicodedata.normalize("NFKD", str(col)).encode("ascii", "ignore").decode()
    col = col.lower().strip()
    col = re.sub(r"[^a-z0-9]+", "_", col).strip("_")
    return _ALIAS.get(col, col)


def limpiar_df(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [_norm(c) for c in df.columns]
    df = df.loc[:, ~df.columns.str.startswith("unnamed")]
    df = df.loc[:, df.columns != ""]
    df = df.dropna(how="all")
    df = df[df.apply(lambda r: r.astype(str).str.strip().ne("").any(), axis=1)]
    return df


# ── Lectura de archivos ────────────────────────────────────────────────────────

def leer_xlsx(path: Path) -> pd.DataFrame | None:
    try:
        df = pd.read_excel(path, engine="openpyxl", dtype=str)
        df = limpiar_df(df)
        if df.empty or len(df) < MIN_ROWS:
            return None
        return df
    except Exception as exc:
        log.warning("  [ERR-XLSX] %s → %s", path.name[:60], exc)
        return None


def leer_html(path: Path) -> pd.DataFrame | None:
    try:
        tablas = pd.read_html(str(path), flavor="lxml")
    except Exception:
        try:
            tablas = pd.read_html(str(path))
        except Exception as exc:
            log.warning("  [ERR-HTML] %s → %s", path.name[:60], exc)
            return None

    if not tablas:
        return None

    # Elegir la tabla más grande (más filas → más datos)
    mejor = max(tablas, key=len)
    mejor = limpiar_df(mejor)
    if mejor.empty or len(mejor) < MIN_ROWS:
        return None
    return mejor


def leer_archivo(path: Path) -> pd.DataFrame | None:
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xls"):
        return leer_xlsx(path)
    if ext == ".html":
        return leer_html(path)
    return None


# ── Estado persistente ─────────────────────────────────────────────────────────

def load_parsed() -> set[str]:
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text(encoding="utf-8-sig"))
        return set(data.get("archivos", []))
    return set()


def save_parsed(archivos: set[str]) -> None:
    STATE_FILE.write_text(
        json.dumps({"archivos": sorted(archivos)}, indent=2),
        encoding="utf-8",
    )


# ── Kafka producer ─────────────────────────────────────────────────────────────

def make_producer(bootstrap: str) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=bootstrap,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False, default=str).encode("utf-8"),
    )


# ── Procesar un archivo ────────────────────────────────────────────────────────

def procesar_archivo(path: Path, producer: KafkaProducer) -> int:
    df = leer_archivo(path)
    if df is None:
        log.warning("  [VACÍO/ERR] %s — sin filas válidas", path.name[:60])
        return 0

    ts = pd.Timestamp.now(tz="UTC").isoformat()
    publicados = 0
    for _, row in df.iterrows():
        registro = {k: v for k, v in row.to_dict().items() if pd.notna(v) and str(v).strip()}
        registro["_archivo"]    = path.name
        registro["_tipo"]       = path.suffix.lower().lstrip(".")
        registro["_parseado_en"] = ts
        producer.send(TOPIC_OUT, value=registro)
        publicados += 1

    producer.flush()
    size_kb = path.stat().st_size / 1024
    log.info(
        "  [OK] %-6s  %5.1f KB  %4d filas → %s | %s",
        path.suffix.upper(), size_kb, publicados, TOPIC_OUT, path.name[:55],
    )
    return publicados


# ── Escaneo del directorio ─────────────────────────────────────────────────────

def escanear_y_procesar(producer: KafkaProducer, procesados: set[str]) -> int:
    extensiones = {".xlsx", ".xls", ".html"}
    candidatos  = [
        f for f in DOWNLOAD_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in extensiones and f.name not in procesados
    ]

    if not candidatos:
        return 0

    log.info("Escaneando %d archivos nuevos en %s ...", len(candidatos), DOWNLOAD_DIR)
    total = 0
    for path in sorted(candidatos):
        filas = procesar_archivo(path, producer)
        procesados.add(path.name)
        save_parsed(procesados)
        total += filas

    return total


# ── Loop principal ─────────────────────────────────────────────────────────────

def main() -> None:
    load_dotenv()

    bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:19092")
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    log.info("=== Consumer Excel/HTML Parser ===")
    log.info("Broker       : %s", bootstrap)
    log.info("Directorio   : %s", DOWNLOAD_DIR.resolve())
    log.info("Topic salida : %s", TOPIC_OUT)
    log.info("Scan cada    : %ds", SCAN_INTERVAL)

    producer = None
    for intento in range(10):
        try:
            producer = make_producer(bootstrap)
            log.info("Conectado a Kafka OK.")
            break
        except NoBrokersAvailable:
            log.warning("Kafka no disponible, reintentando en 10s... (%d/10)", intento + 1)
            time.sleep(10)
    if producer is None:
        raise RuntimeError("No se pudo conectar a Kafka tras 10 intentos.")

    procesados  = load_parsed()
    total_filas = 0

    log.info("Archivos ya procesados: %d", len(procesados))
    log.info("Iniciando primer escaneo...")

    while True:
        nuevas = escanear_y_procesar(producer, procesados)
        total_filas += nuevas
        if nuevas:
            log.info("Escaneo completado: %d filas nuevas publicadas (total: %d)", nuevas, total_filas)
        else:
            log.info("Sin archivos nuevos. Próximo escaneo en %ds...", SCAN_INTERVAL)
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()

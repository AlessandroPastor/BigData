# Producer

**Archivo:** `producer/producer.py` — 202 lineas  
**Imagen Docker:** `casamarket-python:latest`  
**Topic de salida:** `casamarket.documento.detectado`

---

## Responsabilidad

Monitorea periodicamente la API REST del ERP CasaMarket, detecta documentos nuevos con status finalizado (`status = 2`) y publica un evento por cada documento al broker Kafka. Mantiene estado persistente en `state_documentos.json` para garantizar exactamente una publicacion por documento.

---

## Flujo Interno

```mermaid
flowchart TD
    START([Inicio]) --> LOAD_ENV["load_dotenv()\nlee gmail, password, KAFKA_BOOTSTRAP"]
    LOAD_ENV --> CONNECT_KAFKA["make_producer(bootstrap)\nacks=all | retries=3"]
    CONNECT_KAFKA -->|"NoBrokersAvailable"| RETRY{"Intento < 10?"}
    RETRY -->|"Si"| WAIT["sleep(10s)"] --> CONNECT_KAFKA
    RETRY -->|"No"| ERROR([RuntimeError])
    CONNECT_KAFKA -->|"OK"| LOAD_STATE["load_state()\nlee state_documentos.json\n→ set de IDs vistos"]
    LOAD_STATE --> LOOP

    subgraph LOOP["Ciclo cada 300s"]
        AUTH["get_token(email, password)\nPOST /api/authenticate\ncodeApp=quipuadmin"]
        FETCH["fetch_all_documents(token)\nGET /documents?startDate&endDate\npaginacion por x-last-page"]
        FILTER["Filtrar docs nuevos\nid NOT IN vistos"]
        STATUS["Separar por status\nlistos (==2) | pendientes (!=2)"]
        PUB["publicar(producer, doc)\nsend(key=id, value=evento)\nget(timeout=10)"]
        FLUSH["producer.flush()\nsave_state(vistos)"]

        AUTH --> FETCH --> FILTER --> STATUS
        STATUS -->|"listos > 0"| PUB --> FLUSH
        STATUS -->|"sin cambios"| LOG["log: Sin cambios"]
        FLUSH --> SLEEP["sleep(300s)"]
        LOG --> SLEEP
    end

    LOAD_STATE --> LOOP

    style START fill:#E8F5E9,stroke:#2E7D32
    style ERROR fill:#FFEBEE,stroke:#C62828
    style LOOP fill:#FFF8E1,stroke:#F57F17
```

---

## Autenticacion con el ERP

```python
POST https://acl.casamarketapp.com/api/authenticate
Content-Type: application/json

{
  "email":   "admin1@tomas.com",
  "password": "76284084",
  "codeApp":  "quipuadmin"
}
```

**Respuesta:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "domains": [...]
}
```

> El token JWT se usa en el header `Authorization: Bearer <token>` para todas las llamadas posteriores.

---

## Consulta de Documentos

```
GET https://n5.report.casamarketapp.com/documents
Authorization: Bearer <token>
Origin: https://admin.casamarket.la

Params:
  startDate = YYYY-MM-DD   (hoy - DAYS_BACK dias)
  endDate   = YYYY-MM-DD   (hoy)
  limit     = 50
  page      = 1..N
```

**Headers de paginacion en la respuesta:**
- `x-last-page`: numero total de paginas
- `x-quantity`: total de documentos

---

## Evento Publicado en Kafka

```json
{
  "id":           180472,
  "filename":     "detalle_de_ventas__2026_05_19_10_02_47_xlsx_5588.xlsx",
  "extension":    "xlsx",
  "status":       "Finalizado",
  "url_file":     "https://s3.amazonaws.com/casamarket-prod/...",
  "created_at":   "2026-04-27T07:32:51Z",
  "usuario":      "admin1@tomas.com",
  "detectado_en": "2026-05-26T03:47:28.000000+00:00"
}
```

> **Importante:** Se usa el campo `urlFile` de la API (no `downloadUrl`). El campo `downloadUrl` contiene `undefined` en la ruta y genera errores de descarga.

---

## Configuracion de Variables de Entorno

| Variable | Valor por defecto | Descripcion |
|---------|------------------|-------------|
| `gmail` | — (requerido en .env) | Email de acceso al ERP |
| `password` | — (requerido en .env) | Password del ERP |
| `KAFKA_BOOTSTRAP` | `localhost:19092` | Bootstrap del broker |
| `POLL_INTERVAL_SECONDS` | `300` | Segundos entre ciclos |
| `DAYS_BACK` | `30` | Ventana de busqueda de documentos |

---

## Configuracion del KafkaProducer

```python
KafkaProducer(
    bootstrap_servers = "ec-kafka:9092",
    value_serializer  = lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
    key_serializer    = lambda k: str(k).encode("utf-8"),
    acks              = "all",   # confirmacion de todos los ISR replicas
    retries           = 3,
)
```

---

## Estado Persistente

**Archivo:** `producer/state_documentos.json`

```json
{
  "ids": [180472, 180473, ..., 183454]
}
```

- 175 IDs almacenados (rango `180472 — 183454`)
- Se actualiza en cada ciclo exitoso
- Garantiza idempotencia ante reinicios del contenedor

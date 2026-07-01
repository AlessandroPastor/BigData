# Arquitectura del Sistema

## Patrón arquitectónico: Kappa Architecture

El pipeline implementa **arquitectura Kappa**: todo el procesamiento ocurre en la capa de streaming, no existe una capa batch separada. Si hay que reprocesar datos, se vuelve a leer Kafka desde el offset que haga falta (`startingOffsets=earliest`) en vez de mantener dos pipelines distintos (uno batch y uno streaming) como en Lambda.

```mermaid
flowchart TD
    subgraph FUENTE["Fuente de datos"]
        ERP["ERP CasaMarket\nadmin.casamarket.la\ncuenta real: IFERSAN"]
    end

    subgraph INGESTA["Capa de ingesta"]
        PROD["producer.py\npoll cada 300s"]
        DL["consumer_downloader.py\ngroup: casamarket-downloader"]
        PARSE["consumer_excel_parser.py\nscan cada 60s"]
    end

    subgraph BROKER["Apache Kafka 3.7.0 — KRaft (sin ZooKeeper)"]
        T1["casamarket.documento.detectado\n30,372 mensajes"]
        T2["casamarket.ventas.raw\n16,794 mensajes"]
        T3["casamarket.public.ventas\nDebezium CDC — opcional, no automático"]
    end

    subgraph STORAGE["Almacenamiento en caliente"]
        FILES["output/descargas/\n84 archivos · 44 MB"]
        PARQUET["output/parquet/\nApache Parquet"]
    end

    subgraph PROCESAMIENTO["Capa de procesamiento — Spark Structured Streaming"]
        SP1["job_documentos.py\ntrigger 30s"]
        SP2["job_ventas.py\ntrigger 30s"]
        SP3["job_ml_streaming.py\nscoring en tiempo real\ntrigger 30s"]
    end

    subgraph BASES["Bases de datos"]
        PG["PostgreSQL 16\nventas + 7 tablas ML\n16,794 filas reales"]
        MY["MySQL (Laragon, host Windows)\nescritura directa JDBC\n+ ruta CDC opcional"]
    end

    subgraph ML_LAYER["Machine Learning — 6 modelos cada 30 min"]
        MLT["ml-trainer\nGBM · KMeans · IsolationForest · Ridge"]
        MLW["ml-web\nFastAPI + Chart.js · :8501"]
    end

    subgraph OBS["Observabilidad"]
        EXP["kafka-exporter"]
        PROM["Prometheus"]
        GF["Grafana — 2 dashboards"]
    end

    ERP -->|"JWT REST API\nstartDate / endDate"| PROD
    PROD -->|"evento JSON\nstatus=2 Finalizado"| T1
    T1 -->|"consume"| DL
    DL -->|"descarga HTTPS\nchunks 8KB"| FILES
    FILES -->|"scan filesystem"| PARSE
    PARSE -->|"1 msg/fila"| T2

    T1 --> SP1
    SP1 --> PARQUET
    T2 --> SP2
    T2 --> SP3
    SP2 -->|"foreachBatch append"| PG
    SP2 -->|"foreachBatch append\nGestPPP.ventas_ifersan"| MY
    SP2 --> PARQUET
    SP3 -->|"consulta + escribe\nventas_ml_scored"| PG

    PG -->|"SELECT diario"| MLT
    MLT -->|"INSERT/UPSERT\npredicciones_*"| PG
    PG --> MLW
    PG --> GF

    EXP -->|"scrape 15s"| PROM
    PROM --> GF

    style FUENTE fill:#E3F2FD,stroke:#1565C0
    style INGESTA fill:#FFF8E1,stroke:#F57F17
    style BROKER fill:#FFF3E0,stroke:#E65100
    style PROCESAMIENTO fill:#E8F5E9,stroke:#1B5E20
    style BASES fill:#F3E5F5,stroke:#4A148C
    style ML_LAYER fill:#FCE4EC,stroke:#880E4F
    style OBS fill:#E0F2F1,stroke:#004D40
    style STORAGE fill:#ECEFF1,stroke:#37474F
```

---

## Tres jobs de Spark, no dos

Una particularidad de este pipeline frente a una arquitectura Kappa "de libro" es que hay **tres** jobs de Spark Structured Streaming corriendo en paralelo sobre los mismos topics, cada uno con una responsabilidad distinta:

| Job | Lee de | Hace | Escribe en |
|---|---|---|---|
| `job_documentos.py` | `documento.detectado` | Cuenta documentos, calcula latencia ERP→Spark, agrega por ventanas de 5 min | Parquet (4 sinks) |
| `job_ventas.py` | `ventas.raw` | Castea tipos, persiste cada venta | PostgreSQL `ventas` + MySQL `ventas_ifersan` + Parquet |
| `job_ml_streaming.py` | `ventas.raw` | Por cada micro-batch, **vuelve a consultar PostgreSQL** (no usa el batch en sí) para comparar el acumulado real del día contra la predicción GBM y clasificar el estado de cada producto | PostgreSQL `ventas_ml_scored` |

`job_ml_streaming.py` es el componente más fácil de pasar por alto: no entrena ni carga ningún modelo de ML dentro de Spark — usa Kafka únicamente como "heartbeat" cada 30s para disparar una consulta SQL que compara `SUM(ventas de hoy)` contra la fila de `predicciones_diarias` que generó `ml-trainer`. El detalle completo está en [Spark Streaming](../componentes/spark-streaming.md).

---

## Principios de diseño

### Idempotencia mediante estado persistente

Cada componente Python mantiene un archivo JSON con los IDs o nombres ya procesados, para que un reinicio del contenedor no duplique mensajes en Kafka ni filas en PostgreSQL.

| Componente | Archivo de estado | Contenido |
|-----------|------------------|-----------|
| Producer | `producer/state_documentos.json` | IDs de documentos ya publicados a Kafka |
| Downloader | `consumer/state_downloads.json` | IDs de documentos ya descargados |
| Parser | `consumer/state_excel_parsed.json` | Nombres de archivo ya parseados |

Esto es deduplicación a nivel de aplicación, no la garantía nativa de productor idempotente de Kafka (el `KafkaProducer` del producer usa `acks="all", retries=3`, sin `enable_idempotence`). En la práctica el resultado es **at-least-once delivery + dedup por estado**, que es indistinguible de exactly-once para este caso de uso.

### Tolerancia a fallos con retry

Todos los componentes Python reintentan la conexión a Kafka con backoff lineal de 10 segundos antes de fallar definitivamente (hasta 10–15 intentos según el componente).

### Checkpointing de Spark

Cada query de Structured Streaming tiene su propio directorio de checkpoint, para que un reinicio retome exactamente donde se quedó:

```
output/checkpoints/
├── raw/                  # job_documentos.py — eventos raw
├── agg/                  # job_documentos.py — conteo por extensión
├── ventanas/             # job_documentos.py — ventanas de 5 min
├── metricas/             # job_documentos.py — latencia
├── ventas_raw/           # job_ventas.py — ventas → Parquet
├── ventas_agg/           # job_ventas.py — ventas → PostgreSQL/MySQL
└── ml_streaming_v2/      # job_ml_streaming.py — scoring en tiempo real
```

---

## Red Docker

Todos los servicios comparten la red bridge `ec-kafka-dev-net`. El servicio `mysql-sync` (componente CDC opcional) usa `host.docker.internal:3306` para alcanzar una instancia de MySQL en el host Windows (Laragon).

```mermaid
graph LR
    subgraph HOST["Host Windows"]
        LARAGON["MySQL Laragon\n:3306"]
        BROWSER["Navegador\nGrafana / ml-web / Kafka UI"]
    end

    subgraph DOCKER["ec-kafka-dev-net (bridge) — 17 contenedores"]
        KAFKA["ec-kafka\n:9092 interno / :19092 host"]
        KUI["kafka-ui\n:18085"]
        PROD2["producer"]
        CDL["consumer-downloader"]
        CPR["consumer-excel-parser"]
        PG2["postgres\n:15432"]
        SP1B["spark-streaming (docs)\n:4041"]
        SP2B["spark-ventas\n:4042"]
        SP3B["spark-ml\n:4043"]
        JUP["jupyter\n:8888"]
        EXP2["kafka-exporter\n:49308"]
        PROM2["prometheus\n:49090"]
        GF2["grafana\n:43000"]
        KC2["kafka-connect (Debezium)\n:8083"]
        MS["mysql-sync"]
        MLT2["ml-trainer"]
        MLW2["ml-web\n:8501"]
    end

    HOST -->|"19092"| KAFKA
    HOST -->|"18085"| KUI
    HOST -->|"15432"| PG2
    HOST -->|"4041 / 4042 / 4043"| SP1B
    HOST -->|"8888"| JUP
    HOST -->|"49308"| EXP2
    HOST -->|"49090"| PROM2
    HOST -->|"43000"| GF2
    HOST -->|"8501"| MLW2
    MS -->|"host.docker.internal:3306"| LARAGON

    style HOST fill:#E3F2FD,stroke:#1565C0
    style DOCKER fill:#F9FBE7,stroke:#827717
```

El detalle de cada uno de los 17 servicios (imagen, puertos, healthchecks) está en [Infraestructura Docker](infraestructura.md).

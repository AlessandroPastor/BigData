# Arquitectura del Sistema

## Patron Arquitectonico: Kappa Architecture

El pipeline implementa la **arquitectura Kappa**, donde todo el procesamiento ocurre en la capa de streaming. No existe una capa batch separada; el reprocessing se logra recreando los jobs de Spark desde los offsets de Kafka.

```mermaid
flowchart TD
    subgraph FUENTE["Fuente de Datos"]
        ERP["ERP CasaMarket\nhttps://admin.casamarket.la"]
    end

    subgraph INGESTA["Capa de Ingesta — S6"]
        PROD["producer.py\nPoll cada 300s"]
        DL["consumer_downloader.py\nGroup: casamarket-downloader"]
        PARSE["consumer_excel_parser.py\nScan cada 60s"]
    end

    subgraph BROKER["Broker de Mensajes — Apache Kafka 3.7.0 KRaft"]
        T1["casamarket.documento.detectado\n1 particion | 30.372 mensajes"]
        T2["casamarket.ventas.raw\n1 particion | 16.794 mensajes"]
        T3["casamarket.public.ventas\nDebezium CDC"]
    end

    subgraph STORAGE["Almacenamiento en Caliente"]
        S3["Amazon S3\nURLs firmadas"]
        FILES["/output/descargas/\n84 archivos | 44 MB"]
        PARQUET["/output/parquet/\nApache Parquet"]
    end

    subgraph PROCESAMIENTO["Capa de Procesamiento — S7"]
        SP1["job_documentos.py\nSpark local 2\nTrigger 30s"]
        SP2["job_ventas.py\nSpark local 2\nTrigger 30s"]
    end

    subgraph BASES["Bases de Datos"]
        PG["PostgreSQL 16\nventas | predicciones_2026\n16.794 filas"]
        MY["MySQL Laragon\nventas_ifersan\nCDC replica"]
    end

    subgraph ML_LAYER["Machine Learning — S9"]
        ML["prediccion_ventas.py\nLinearRegression x 15 productos\n180 predicciones 2026"]
    end

    subgraph OBS["Observabilidad — S8"]
        EXP["kafka-exporter\n:49308/metrics"]
        PROM["Prometheus\n:49090"]
        GF["Grafana\n:43000\n2 Dashboards"]
    end

    subgraph CDC["CDC — Debezium 2.7"]
        KC["kafka-connect\n:8083"]
        MYSQL_SYNC["mysql_sync.py"]
    end

    ERP -->|"JWT REST API\nstartDate / endDate"| PROD
    PROD -->|"evento JSON\nstatus=2"| T1
    T1 -->|"consume"| DL
    DL -->|"HTTPS stream\n8192 bytes chunks"| S3
    S3 --> FILES
    FILES -->|"scan filesystem"| PARSE
    PARSE -->|"1 msg/fila\n83 alias columnas"| T2

    T1 --> SP1
    SP1 --> PARQUET
    SP2 --> PARQUET
    T2 --> SP2
    SP2 -->|"foreachBatch\nappend"| PG
    SP2 -->|"foreachBatch\nappend"| MY

    PG -->|"SELECT ventas\nagrupa por mes/producto"| ML
    ML -->|"INSERT INTO\npredicciones_2026"| PG
    PG --> GF

    EXP -->|"scrape 15s"| PROM
    PROM --> GF
    KC -->|"WAL logical\npgoutput"| T3
    T3 --> MYSQL_SYNC
    MYSQL_SYNC --> MY

    style FUENTE fill:#E3F2FD,stroke:#1565C0
    style INGESTA fill:#FFF8E1,stroke:#F57F17
    style BROKER fill:#FFF3E0,stroke:#E65100
    style PROCESAMIENTO fill:#E8F5E9,stroke:#1B5E20
    style BASES fill:#F3E5F5,stroke:#4A148C
    style ML_LAYER fill:#FCE4EC,stroke:#880E4F
    style OBS fill:#E0F2F1,stroke:#004D40
    style CDC fill:#EDE7F6,stroke:#311B92
    style STORAGE fill:#ECEFF1,stroke:#37474F
```

---

## Principios de Diseno

### Idempotencia mediante estado persistente
Cada componente mantiene un archivo JSON de IDs o nombres ya procesados. Esto garantiza que reinicios del sistema no generen duplicados en Kafka ni en la base de datos.

| Componente | Archivo de estado | Contenido |
|-----------|------------------|-----------|
| Producer | `producer/state_documentos.json` | 175 IDs de documentos publicados |
| Downloader | `consumer/state_downloads.json` | 175 IDs de documentos descargados |
| Parser | `consumer/state_excel_parsed.json` | 215 nombres de archivos parseados |

### Tolerancia a fallos con retry
Todos los componentes Python implementan retry con backoff lineal de 10 segundos antes de declarar fallo definitivo.

| Componente | Intentos max | Delay |
|-----------|-------------|-------|
| Producer → Kafka | 10 | 10s |
| Downloader → Kafka | 15 | 10s |
| mysql_sync → MySQL | 15 | 10s |
| registrar_conector → Kafka Connect | 20 | 10s |

### Checkpointing de Spark
Spark Structured Streaming persiste sus offsets y estado en directorios locales:

```
output/checkpoints/
├── raw/        # job_ventas.py — ventas raw
├── ventanas/   # job_documentos.py — windowed aggregations
├── metricas/   # job_documentos.py — metricas de latencia
└── agg/        # job_documentos.py — aggregations por extension
```

---

## Red Docker

Todos los servicios comparten la red `ec-kafka-dev-net` (bridge). El servicio `mysql-sync` usa `host.docker.internal:3306` para alcanzar MySQL Laragon en el host Windows.

```mermaid
graph LR
    subgraph HOST["Host Windows"]
        LARAGON["MySQL Laragon\n:3306"]
        BROWSER["Navegador\nGrafana / Jupyter / KafkaUI"]
    end

    subgraph DOCKER["ec-kafka-dev-net (bridge)"]
        KAFKA["ec-kafka\n:9092 interno\n:19092 externo"]
        KUI["kafka-ui\n:8080"]
        PROD2["producer"]
        CDL["consumer-downloader"]
        CPR["consumer-excel-parser"]
        PG2["postgres\n:5432"]
        SP1B["spark-streaming\n:4040"]
        SP2B["spark-ventas\n:4040"]
        JUP["jupyter\n:8888"]
        EXP2["kafka-exporter\n:9308"]
        PROM2["prometheus\n:9090"]
        GF2["grafana\n:3000"]
        KC2["kafka-connect\n:8083"]
        MS["mysql-sync"]
    end

    HOST -->|"19092"| KAFKA
    HOST -->|"18085"| KUI
    HOST -->|"15432"| PG2
    HOST -->|"4041"| SP1B
    HOST -->|"4042"| SP2B
    HOST -->|"8888"| JUP
    HOST -->|"49308"| EXP2
    HOST -->|"49090"| PROM2
    HOST -->|"43000"| GF2
    HOST -->|"8083"| KC2
    MS -->|"host.docker.internal:3306"| LARAGON

    style HOST fill:#E3F2FD,stroke:#1565C0
    style DOCKER fill:#F9FBE7,stroke:#827717
```

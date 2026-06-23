# Spark Structured Streaming

El sistema cuenta con **dos jobs de Spark** que consumen topics de Kafka en tiempo real con trigger de 30 segundos.

---

## job_ventas.py — Procesamiento de Ventas

**Archivo:** `spark_streaming/job_ventas.py`  
**Contenedor:** `spark-ventas` — Spark UI en `http://localhost:4042`  
**Topic de entrada:** `casamarket.ventas.raw`

### Diagrama de Flujo

```mermaid
flowchart TD
    K2["Topic: casamarket.ventas.raw\n16.794 mensajes"]

    subgraph SPARK_SESSION["SparkSession\nmaster=local[2]\nshuffle.partitions=2"]
        READ["readStream\nformat=kafka\nstartingOffsets=earliest"]
        SCHEMA["Schema (17 campos, todos StringType):\nfecha, producto, cod_producto, marca,\ncategoria, subcategoria, cantidad,\nprecio_unitario, total, cliente,\nruc_cliente, vendedor, razon_social,\nzona, _archivo, _tipo, _parseado_en"]
        CAST["Transformaciones:\ncantidad → DoubleType\nprecio_unitario → DoubleType\ntotal → DoubleType\nfecha → DateType\ncurrent_timestamp → procesado_ts"]
    end

    subgraph SINKS["Sinks — foreachBatch"]
        PARQUET["Sink 1: Parquet\n/output/parquet/ventas/\nmode=append\ntrigger 30s"]
        PG["Sink 2: PostgreSQL\nJDBC: postgres:5432/casamarket\ntabla ventas\nmode=append"]
        MY["Sink 3: MySQL Laragon\nJDBC: host.docker.internal:3306\ntabla ventas_ifersan\nmode=append"]
        CONSOLE["Sink 4: Console\nTop 15 productos\nagrupa por producto\nsuma total"]
    end

    K2 --> READ
    READ --> SCHEMA --> CAST
    CAST -->|"foreachBatch\ncache()"| PG
    CAST -->|"foreachBatch\ncache()"| MY
    CAST --> PARQUET
    CAST --> CONSOLE

    style K2 fill:#FFF3E0,stroke:#E65100
    style SPARK_SESSION fill:#E8F5E9,stroke:#1B5E20
    style SINKS fill:#E3F2FD,stroke:#1565C0
```

### Configuracion de Spark

```python
spark = SparkSession.builder \
    .appName("CasaMarket-Ventas-Streaming") \
    .config("spark.sql.shuffle.partitions", "2") \
    .config("spark.streaming.stopGracefullyOnShutdown", "true") \
    .getOrCreate()
```

### Checkpoints

```
output/checkpoints/
├── raw/          # checkpoint del sink Parquet
│   ├── commits/
│   ├── offsets/
│   └── sources/0/
└── agg/          # checkpoint del sink PostgreSQL/MySQL
    ├── commits/
    ├── offsets/
    └── sources/0/
```

### Dependencias Maven (spark-submit)

```
--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,
           org.postgresql:postgresql:42.7.3,
           mysql:mysql-connector-java:8.0.33
```

---

## job_documentos.py — Metricas de Documentos

**Archivo:** `spark_streaming/job_documentos.py`  
**Contenedor:** `spark-streaming` — Spark UI en `http://localhost:4041`  
**Topic de entrada:** `casamarket.documento.detectado`

### Diagrama de Flujo

```mermaid
flowchart TD
    K1["Topic: casamarket.documento.detectado\n30.372 mensajes"]

    subgraph PROC["Procesamiento con Watermark"]
        READ2["readStream format=kafka"]
        SCHEMA2["Schema (8 campos):\nid, filename, extension, status,\nurl_file, created_at,\nusuario, detectado_en"]
        WATERMARK["withWatermark('detectado_en', '10 minutes')"]
        WINDOW["window('detectado_en', '5 minutes')"]
        LAT["latencia_ms =\ncurrent_timestamp - detectado_en_ts"]
    end

    subgraph SINKS2["Sinks en Parquet"]
        RAW["Sink 1: Raw\n/output/parquet/documentos/\nappend"]
        AGG["Sink 2: Agregaciones\n/output/parquet/por_extension/\ncuenta por extension\nappend"]
        VENTANAS["Sink 3: Ventanas\n/output/parquet/ventanas/\nventana 5 min\nappend"]
        MET["Sink 4: Metricas\n/output/parquet/metricas/\nmin/avg/max latencia_ms\nappend"]
    end

    K1 --> READ2 --> SCHEMA2 --> WATERMARK --> LAT
    LAT --> RAW
    WATERMARK --> WINDOW --> AGG
    WATERMARK --> VENTANAS
    LAT --> MET

    style K1 fill:#FFF3E0,stroke:#E65100
    style PROC fill:#E8F5E9,stroke:#1B5E20
    style SINKS2 fill:#E3F2FD,stroke:#1565C0
```

### Calculo de Latencia

El job calcula la latencia de extremo a extremo entre el momento en que el Producer detecta el documento y el momento en que Spark lo procesa:

```python
df = df.withColumn(
    "latencia_ms",
    (col("procesado_ts").cast("long") - col("detectado_en_ts").cast("long")) * 1000
)
```

### Configuracion

```
Watermark:  10 minutos  (tolerancia para datos tardios)
Window:     5 minutos   (agregacion por ventana de tiempo)
Trigger:    30 segundos (processBatch)
Checkpoints:
  /output/checkpoints/raw/
  /output/checkpoints/agg/
  /output/checkpoints/ventanas/
  /output/checkpoints/metricas/
```

---

## Rendimiento Observado

| Metrica | Valor |
|---------|-------|
| Throughput carga inicial | ~506 msg/s |
| Throughput re-proceso (desde checkpoint) | **~6.074 msg/s** |
| Latencia de batch | ~30 s |
| Consumer lag al finalizar | **0 mensajes** |
| Particiones shuffle | 2 (optimizado para local[2]) |
| Modo master | `local[2]` |

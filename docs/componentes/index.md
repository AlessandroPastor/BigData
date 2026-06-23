# Componentes del Sistema

## Mapa de Componentes

```mermaid
flowchart LR
    subgraph PYTHON["Servicios Python"]
        P["producer.py\n202 lineas"]
        D["consumer_downloader.py\n149 lineas"]
        E["consumer_excel_parser.py\n265 lineas"]
        M["mysql_sync.py"]
        R["registrar_conector.py\n68 lineas"]
        ML["prediccion_ventas.py\n154 lineas"]
    end

    subgraph SPARK["Jobs PySpark"]
        JD["job_documentos.py"]
        JV["job_ventas.py"]
    end

    subgraph NOTEBOOKS["JupyterLab"]
        N1["01_explorar_kafka.ipynb"]
        N2["02_ml_prediccion_ventas.ipynb"]
    end

    P --> D
    D --> E
    E --> JV
    P --> JD
    JV --> ML
    R --> M
```

## Resumen por Componente

| Componente | Archivo | Lineas | Entrada | Salida |
|-----------|---------|--------|---------|--------|
| Producer | `producer/producer.py` | 202 | API REST ERP | Topic `documento.detectado` |
| Downloader | `consumer/consumer_downloader.py` | 149 | Topic Kafka | Archivos en `/output/descargas/` |
| Parser | `consumer/consumer_excel_parser.py` | 265 | Filesystem | Topic `ventas.raw` |
| Spark Docs | `spark_streaming/job_documentos.py` | ~80 | Topic Kafka | Parquet + metricas |
| Spark Ventas | `spark_streaming/job_ventas.py` | ~200 | Topic Kafka | Parquet + PostgreSQL + MySQL |
| ML | `ml/prediccion_ventas.py` | 154 | PostgreSQL | `predicciones_2026` (180 filas) |
| MySQL Sync | `mysql_sync/mysql_sync.py` | ~80 | Topic CDC | MySQL Laragon |
| Registrar CDC | `mysql_sync/registrar_conector.py` | 68 | — | Conector Debezium activo |

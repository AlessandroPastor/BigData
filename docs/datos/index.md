# Datos del Sistema

> Si buscas la explicación de dónde sale cada dato desde el negocio real hasta el modelo de ML, empieza por [¿De dónde viene la data?](origen-datos.md). Esta página es el mapa técnico de dónde vive cada dato *dentro* de la infraestructura.

## Mapa de datos

```mermaid
flowchart LR
    subgraph KAFKA["Apache Kafka — Topics"]
        T1["casamarket.documento.detectado\n30,372 mensajes"]
        T2["casamarket.ventas.raw\n16,794 mensajes"]
        T3["casamarket.public.ventas\nDebezium CDC — opcional"]
    end

    subgraph PG["PostgreSQL 16"]
        V["ventas\n16,794 filas"]
        PD["predicciones_diarias\nGBM · 62 días × producto"]
        PM["predicciones_mensuales\nmodelo mensual directo"]
        SC["segmentos_clientes\nKMeans RFM"]
        AD["anomalias_detectadas\nIsolationForest"]
        PV["predicciones_vendedor\nGBM semanal"]
        MM["model_metadata\nR², MAE, MAPE por modelo"]
        VMS["ventas_ml_scored\nscoring en tiempo real"]
    end

    subgraph PARQUET["Apache Parquet"]
        PVV["/parquet/ventas/"]
        PDD["/parquet/documentos/"]
        PE["/parquet/por_extension/"]
        PMM["/parquet/metricas/"]
    end

    subgraph MYSQL["MySQL (opcional)"]
        MV1["GestPPP.ventas_ifersan\nJDBC directo desde Spark"]
        MV2["casamarket_mysql.ventas\nvía Debezium CDC"]
    end

    subgraph FS["Filesystem"]
        DL["output/descargas/\n84 archivos · 44 MB"]
    end

    T1 --> PDD
    T1 --> PE
    T1 --> PMM
    T2 --> PVV
    T2 --> V
    T2 --> VMS
    V -->|"CDC opcional"| T3
    T3 --> MV2
    V --> MV1
    V --> PD --> PM
    V --> SC
    V --> AD
    V --> PV

    style KAFKA fill:#FFF3E0,stroke:#E65100
    style PG fill:#F3E5F5,stroke:#4A148C
    style PARQUET fill:#E8F5E9,stroke:#1B5E20
    style MYSQL fill:#E8EAF6,stroke:#283593
    style FS fill:#ECEFF1,stroke:#37474F
```

## Volúmenes de datos

| Almacén | Formato | Filas/Mensajes | Tamaño |
|---------|---------|----------------|--------|
| Topic `documento.detectado` | JSON en Kafka | 30,372 msgs | — |
| Topic `ventas.raw` | JSON en Kafka | 16,794 msgs | — |
| PostgreSQL: `ventas` | Relacional | 16,794 filas | ~5 MB |
| PostgreSQL: 6 tablas de ML + `model_metadata` | Relacional | miles de filas (predicciones diarias × producto × 62 días, etc.) | &lt; 5 MB |
| Parquet: `ventas` | Columnar | ~16,794 filas | ~2 MB |
| Archivos descargados | Excel/HTML/PDF | 84 archivos | 44 MB |
| Estado persistente JSON | JSON | 3 archivos | &lt; 50 KB |

## Páginas de esta sección

| Página | Contenido |
|---|---|
| [¿De dónde viene la data?](origen-datos.md) | El recorrido completo desde la venta real hasta el modelo de ML |
| [Tópicos Kafka](kafka-topics.md) | Esquema de cada mensaje, consumidores, offsets |
| [PostgreSQL](postgresql.md) | Esquema completo de las 8 tablas y vistas |
| [Sincronización MySQL (opcional)](mysql-sync.md) | El componente CDC vía Debezium, cómo activarlo |

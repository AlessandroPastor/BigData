# Datos del Sistema

## Mapa de Datos

```mermaid
flowchart LR
    subgraph KAFKA["Apache Kafka — Topics"]
        T1["casamarket.documento.detectado\n30.372 mensajes\n1 particion | replication=1"]
        T2["casamarket.ventas.raw\n16.794 mensajes\n1 particion | replication=1"]
        T3["casamarket.public.ventas\nDebezium CDC\nWAL PostgreSQL"]
    end

    subgraph PG["PostgreSQL 16"]
        V["ventas\n16.794 filas\n18 columnas + 6 indices"]
        P["predicciones_2026\n180 filas\n9 columnas"]
        VPM["VIEW: ventas_por_mes\ngrupa por mes/producto/vendedor"]
        TOP["VIEW: top_productos\nranking por ingresos"]
    end

    subgraph PARQUET["Apache Parquet"]
        PV["/parquet/ventas/"]
        PD["/parquet/documentos/"]
        PE["/parquet/por_extension/"]
        PM["/parquet/metricas/"]
    end

    subgraph MYSQL["MySQL Laragon"]
        MV["ventas_ifersan\nreplica CDC"]
    end

    subgraph FS["Filesystem"]
        DL["/output/descargas/\n84 archivos | 44 MB"]
        SD["state_documentos.json\n175 IDs"]
        SR["state_downloads.json\n175 IDs"]
        SE["state_excel_parsed.json\n215 filenames"]
    end

    T1 --> PD
    T1 --> PE
    T1 --> PM
    T2 --> PV
    T2 --> V
    V -->|"CDC"| T3
    T3 --> MV
    V --> P
    V --> VPM
    V --> TOP

    style KAFKA fill:#FFF3E0,stroke:#E65100
    style PG fill:#F3E5F5,stroke:#4A148C
    style PARQUET fill:#E8F5E9,stroke:#1B5E20
    style MYSQL fill:#E8EAF6,stroke:#283593
    style FS fill:#ECEFF1,stroke:#37474F
```

## Volumenes de Datos

| Almacen | Formato | Filas/Mensajes | Tamano |
|---------|---------|----------------|--------|
| Topic: documento.detectado | JSON en Kafka | 30.372 msgs | — |
| Topic: ventas.raw | JSON en Kafka | 16.794 msgs | — |
| PostgreSQL: ventas | Relacional | 16.794 filas | ~5 MB |
| PostgreSQL: predicciones_2026 | Relacional | 180 filas | < 1 MB |
| Parquet: ventas | Columnar | ~16.794 filas | ~2 MB |
| Archivos descargados | Excel/HTML/PDF | 84 archivos | 44 MB |
| Estado persistente JSON | JSON | 3 archivos | < 50 KB |

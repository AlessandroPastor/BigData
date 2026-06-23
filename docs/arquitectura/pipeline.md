# Pipeline de Datos — Flujo Completo

## Ciclo de Vida de un Documento

Desde que un vendedor genera un reporte en el ERP hasta que los datos aparecen en Grafana, el documento pasa por los siguientes estados:

```mermaid
stateDiagram-v2
    [*] --> EnERP : Vendedor genera reporte en ERP

    EnERP --> Detectado : Producer consulta API\ncada 300s\nstatus = 2 (Finalizado)

    Detectado --> PublicadoKafka : Producer publica evento\ncasamarket.documento.detectado

    PublicadoKafka --> Descargado : Consumer Downloader\ndescarga desde S3\nstream 8192 bytes

    Descargado --> Parseado : Consumer Excel Parser\nlee filas con openpyxl\ncada columna = 1 mensaje Kafka

    Parseado --> PublicadoVentas : Mensajes en\ncasamarket.ventas.raw

    PublicadoVentas --> EnSpark : Spark consume batch\ncada 30 segundos

    EnSpark --> EnParquet : Escrito en\n/output/parquet/ventas/

    EnSpark --> EnPostgres : Insertado en\ntabla ventas

    EnPostgres --> EnMySQL : Debezium CDC\ncaptura WAL\n→ Topic → MySQL

    EnPostgres --> EnML : prediccion_ventas.py\nagrupa por mes/producto

    EnML --> Prediccion : INSERT INTO\npredicciones_2026\n180 registros

    Prediccion --> EnGrafana : Dashboard S9\nvisualiza ventas\ny proyecciones

    EnGrafana --> [*]
```

---

## Secuencia de Mensajes Kafka

```mermaid
sequenceDiagram
    participant ERP as ERP CasaMarket
    participant PROD as Producer
    participant K1 as Topic: documento.detectado
    participant DL as Consumer Downloader
    participant S3 as Amazon S3
    participant FS as Filesystem
    participant PARSE as Consumer Excel Parser
    participant K2 as Topic: ventas.raw
    participant SP as Spark Streaming
    participant PG as PostgreSQL

    Note over PROD: Cada 300 segundos
    PROD->>ERP: POST /api/authenticate (JWT)
    ERP-->>PROD: token JWT
    PROD->>ERP: GET /documents?startDate=...&endDate=...&page=1
    ERP-->>PROD: [ {id, filename, status=2, urlFile, ...} ]
    PROD->>K1: send(key=id, value={evento}) acks=all

    Note over DL: Consumer group: casamarket-downloader
    K1->>DL: poll() → evento{url_file, filename}
    DL->>S3: GET url_file (stream)
    S3-->>DL: binario en chunks 8192 bytes
    DL->>FS: write /output/descargas/filename.xlsx
    DL->>DL: state_downloads.json += id

    Note over PARSE: Scan cada 60 segundos
    PARSE->>FS: scandir /output/descargas/
    FS-->>PARSE: [archivo_nuevo.xlsx]
    PARSE->>PARSE: openpyxl.load_workbook()\nnormalizar columnas (83 alias)
    loop Por cada fila
        PARSE->>K2: send(value={fecha, producto, cantidad, total, ...})
    end
    PARSE->>PARSE: state_excel_parsed.json += filename

    Note over SP: Trigger: processBatch 30s
    K2->>SP: readStream (startingOffsets=earliest)
    SP->>SP: cast(cantidad→Double)\ncast(precio_unitario→Double)\ncast(total→Double)\ncast(fecha→Date)
    SP->>PG: foreachBatch → INSERT INTO ventas (append)
    SP->>FS: writeStream format=parquet (append)
```

---

## Esquema de Datos — JSON en Kafka

### Topic: casamarket.documento.detectado

```json
{
  "id": 180472,
  "filename": "Reporte_de_producto_por_vendedor_agrupado_5588.xlsx",
  "extension": "xlsx",
  "status": "Finalizado",
  "url_file": "https://s3.amazonaws.com/casamarket-prod/docs/...",
  "created_at": "2026-04-27T07:32:51Z",
  "usuario": "admin1@tomas.com",
  "detectado_en": "2026-05-26T03:47:28Z"
}
```

### Topic: casamarket.ventas.raw

```json
{
  "fecha": "2026-05-12",
  "producto": "PEPSI 2000ML",
  "cod_producto": "PEP-001",
  "marca": "LINEA PEPSI",
  "categoria": "GASEOSAS PEPSI",
  "subcategoria": "RETORNABLE 2L",
  "cantidad": "6",
  "precio_unitario": "19.07",
  "total": "144.0",
  "cliente": "YOLANDA GONZA HUANCA",
  "ruc_cliente": "17107",
  "vendedor": "ROSA CUSILAYME",
  "razon_social": "FERNANDEZ CALA TOMAS",
  "zona": "ZONA NORTE",
  "_archivo": "detalle_de_ventas__2026_05_19_xlsx.xlsx",
  "_tipo": "xlsx",
  "_parseado_en": "2026-05-26T03:47:28Z"
}
```

---

## Throughput del Sistema

```mermaid
xychart-beta
    title "Mensajes Kafka por Topic"
    x-axis ["documento.detectado", "ventas.raw", "public.ventas (CDC)"]
    y-axis "Mensajes" 0 --> 35000
    bar [30372, 16794, 16794]
```

| Etapa | Volumen | Velocidad |
|-------|---------|-----------|
| Documentos detectados | 175 documentos | 300 s/ciclo |
| Mensajes en documento.detectado | 30.372 msgs | — |
| Archivos descargados | 84 archivos / 44 MB | ~8192 bytes/chunk |
| Ventas parseadas | 16.794 filas | — |
| Throughput Spark (carga inicial) | — | 506 msg/s |
| Throughput Spark (re-proceso) | — | **6.074 msg/s** |
| Latencia batch Spark | — | 30 s (trigger) |
| Consumer lag final | — | **0 mensajes** |

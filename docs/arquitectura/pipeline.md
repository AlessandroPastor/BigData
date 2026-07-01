# Pipeline de Datos — Flujo Completo

## Ciclo de vida de una venta

Desde que un vendedor de IFERSAN cierra una venta en CasaMarket hasta que esa venta influye en una predicción visible en Grafana, el dato pasa por los siguientes estados:

```mermaid
stateDiagram-v2
    [*] --> EnERP : Vendedor registra la venta\nen CasaMarket (campo)

    EnERP --> Detectado : Producer consulta la API\ncada 300s · status=2 (Finalizado)

    Detectado --> PublicadoKafka : Producer publica evento\ncasamarket.documento.detectado

    PublicadoKafka --> Descargado : Consumer Downloader\ndescarga el Excel/HTML\nstream 8KB por chunk

    Descargado --> Parseado : Consumer Excel Parser\nescanea la carpeta cada 60s\nnormaliza columnas (alias)

    Parseado --> PublicadoVentas : Una fila del Excel =\nun mensaje en casamarket.ventas.raw

    PublicadoVentas --> EnSpark : 3 jobs de Spark consumen\nel mismo topic cada 30s

    EnSpark --> EnPostgres : job_ventas.py inserta\nen la tabla ventas

    EnSpark --> EnParquet : job_ventas.py escribe\noutput/parquet/ventas/

    EnSpark --> EnMySQL : job_ventas.py escribe\nGestPPP.ventas_ifersan (JDBC directo)

    EnPostgres --> EnTrainer : ml-trainer lee ventas\ncada 30 minutos

    EnTrainer --> Prediccion : 6 modelos escriben\npredicciones_diarias y otras tablas

    EnPostgres --> EnScoring : job_ml_streaming.py compara\nventas de hoy vs predicción GBM

    EnScoring --> EnGrafana : ventas_ml_scored\nalimenta el panel de alertas

    Prediccion --> EnGrafana : Dashboard de negocio\nventas reales + forecast

    Prediccion --> EnWeb : ml-web (FastAPI) sirve\nranking y forecast por producto

    EnGrafana --> [*]
    EnWeb --> [*]
```

---

## Secuencia de mensajes

```mermaid
sequenceDiagram
    participant ERP as ERP CasaMarket
    participant PROD as Producer
    participant K1 as Topic: documento.detectado
    participant DL as Consumer Downloader
    participant FS as Filesystem (output/descargas)
    participant PARSE as Consumer Excel Parser
    participant K2 as Topic: ventas.raw
    participant SP as Spark (3 jobs)
    participant PG as PostgreSQL
    participant MLT as ml-trainer

    Note over PROD: Cada 300 segundos
    PROD->>ERP: POST /api/authenticate (email + password + codeApp)
    ERP-->>PROD: token JWT
    PROD->>ERP: GET /documents?startDate=...&endDate=...&page=1..N
    ERP-->>PROD: documentos paginados (header x-last-page)
    PROD->>PROD: filtra: id no visto AND status==2 (Finalizado)
    PROD->>K1: send(key=id, value=evento) acks=all

    Note over DL: group_id=casamarket-downloader
    K1->>DL: poll() -> evento{url_file, filename}
    DL->>FS: GET url_file (stream, chunks de 8KB) -> escribe archivo
    DL->>DL: state_downloads.json += id

    Note over PARSE: Escanea la carpeta cada 60s (no depende de Kafka)
    PARSE->>FS: scandir(output/descargas/)
    FS-->>PARSE: archivos nuevos .xlsx / .html
    PARSE->>PARSE: pandas.read_excel / read_html\nnormaliza columnas con diccionario de alias
    loop Por cada fila valida
        PARSE->>K2: send(value={fecha, producto, cantidad, total, ...})
    end
    PARSE->>PARSE: state_excel_parsed.json += filename

    Note over SP: 3 queries de Structured Streaming, trigger 30s
    K2->>SP: readStream (job_ventas: startingOffsets=earliest)
    SP->>SP: cast cantidad/precio/total -> Double, fecha -> Date
    SP->>PG: foreachBatch -> INSERT INTO ventas (append)
    K2->>SP: readStream (job_ml_streaming: startingOffsets=latest)
    SP->>PG: SELECT SUM(total) FROM ventas WHERE fecha=hoy
    SP->>PG: SELECT predicciones_diarias WHERE fecha_pred=hoy
    SP->>PG: INSERT INTO ventas_ml_scored (comparacion + alerta)

    Note over MLT: Cada 30 minutos
    MLT->>PG: SELECT ventas agrupadas por dia/producto
    MLT->>MLT: entrena 6 modelos (GBM, KMeans, IsolationForest, Ridge)
    MLT->>PG: UPSERT predicciones_diarias, segmentos_clientes, anomalias_detectadas, ...
```

---

## Esquema de datos — JSON en Kafka

### Topic `casamarket.documento.detectado`

```json
{
  "id": 180472,
  "filename": "detalle_de_ventas__2026_05_19_10_02_47_xlsx_5588.xlsx",
  "extension": "xlsx",
  "status": "Finalizado",
  "url_file": "https://s3.amazonaws.com/casamarket-prod/.../archivo.xlsx",
  "created_at": "2026-04-27T07:32:51Z",
  "usuario": "vendedor@ifersan.example",
  "detectado_en": "2026-05-26T03:47:28.000000+00:00"
}
```

`status` y `url_file` vienen de los campos `statusName` y `urlFile` de la respuesta del API — el código usa explícitamente `urlFile` y no `downloadUrl`, porque este último venía vacío en pruebas.

### Topic `casamarket.ventas.raw`

```json
{
  "fecha": "2026-05-12",
  "hora": "21:30:27",
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
  "_parseado_en": "2026-05-26T03:47:28.000000+00:00"
}
```

Todos los campos numéricos viajan como **strings** — el parser de Excel los lee con `dtype=str` para no perder precisión, y es Spark quien los castea a `DoubleType`/`DateType` en `job_ventas.py`. Solo se incluyen los campos no vacíos de cada fila (`pd.notna(v) and str(v).strip()`), así que el esquema real puede variar ligeramente de un archivo a otro.

---

## Throughput del sistema

```mermaid
xychart-beta
    title "Mensajes Kafka por Topic"
    x-axis ["documento.detectado", "ventas.raw"]
    y-axis "Mensajes" 0 --> 35000
    bar [30372, 16794]
```

| Etapa | Volumen | Velocidad |
|-------|---------|-----------|
| Documentos detectados (únicos) | 175 documentos | ciclo de 300s |
| Mensajes en `documento.detectado` | 30,372 msgs | — |
| Archivos descargados | 84 archivos / 44 MB | chunks de 8 KB |
| Ventas parseadas | 16,794 filas | — |
| Throughput Spark (carga inicial, con checkpoint) | — | ~506 msg/s |
| Throughput Spark (re-proceso completo) | — | **6,074 msg/s** |
| Trigger de los 3 jobs de Spark | — | 30 s |
| Consumer lag final | — | **0 mensajes** |

La diferencia entre 175 documentos únicos y 30,372 mensajes en el topic se debe a que el producer ejecutó muchos ciclos de polling durante desarrollo y pruebas — el downloader evita re-descargar gracias a `state_downloads.json`.

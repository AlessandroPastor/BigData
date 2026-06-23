# IFERSAN · Pipeline Big Data en Tiempo Real
### Universidad Peruana Unión · IX Ciclo · Big Data · Unidad 2
**Docente:** Mg. Angel Sullon

| Alumno | Rol |
|---|---|
| Alessandro Pastor Mamani Mamani | Arquitectura y pipeline completo |
| Cabana Sulca Cristian | Consumer / parser / Kafka |
| Montes Mamani Andres Lino | Spark Streaming y PostgreSQL |
| Fernandez Sanchez Jean Piero | ML, Grafana y observabilidad |

**Fecha de entrega:** Junio 2026

---

## Qué es este proyecto

**IFERSAN** es una distribuidora de bebidas en Juliaca (Pepsi, Inca Kola, Coca Cola, Escocesa, Pilsen Callao). Sus vendedores —encabezados por **ROSA CUSILAYME**— registran ventas diariamente en el ERP CasaMarket. El problema: la gerencia recibía esos datos **24 horas después**, en un Excel que nadie podía consultar en tiempo real.

Este proyecto construye el pipeline completo que cambia eso:

> Cada venta registrada en el ERP de IFERSAN aparece en Grafana en **menos de 8 minutos**. Sin Excel. Sin espera. Automático.

### Resultados con datos reales de IFERSAN

| Métrica | Valor real |
|---|---|
| Transacciones procesadas | **16,794** |
| Ingresos reales registrados | **S/ 406,150.50** |
| Producto #1 | **PEPSI 2000ML — S/ 76,400** |
| Vendedor #1 | **ROSA CUSILAYME — S/ 101,500** |
| Vendedor #2 | **JHONATAN — S/ 92,000** |
| Productos únicos | 62 |
| Clientes únicos | 1,106 |
| Documentos descargados del ERP | 175 archivos (IDs 180472–183454) |
| Archivos Excel/HTML almacenados | 84 archivos · 44 MB |
| Periodo de datos | 27 Abr – 19 May 2026 |
| Throughput Spark (re-proceso) | **6,074 msg/s** |
| Consumer lag final | **0** |
| Proyección ML 2026 (Top 15) | **S/ 1,614,943.32** |
| PEPSI 2000ML proyectado 2026 | **S/ 334,800** (factor 4.4×) |

---

## Arquitectura del Pipeline (Kappa)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         FUENTE DE DATOS — IFERSAN                        │
│                                                                          │
│   ERP CasaMarket   →   admin.casamarket.la                               │
│   API Auth:   https://acl.casamarketapp.com/api/authenticate             │
│   API Docs:   https://n5.report.casamarketapp.com/documents              │
│                                                                          │
│   Formato: reportes .xlsx / .html · status=Finalizado · COMPANY_ID=5588 │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │  JWT Bearer Token · Paginado x-last-page
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         PRODUCTOR                                        │
│                                                                          │
│   producer/producer.py  (202 líneas)                                     │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │  Ciclo cada 300s                                                 │   │
│   │  1. POST /api/authenticate → token JWT                           │   │
│   │  2. GET /documents?startDate&endDate → lista paginada            │   │
│   │  3. Filtra: status=2 AND id NOT IN state_documentos.json         │   │
│   │  4. Publica JSON en Kafka (acks=all, retries=3)                  │   │
│   │  5. Guarda IDs publicados → state_documentos.json                │   │
│   └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   Topic destino: casamarket.documento.detectado                          │
│   175 documentos publicados · IDs 180472 – 183454                       │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │  JSON evento por documento
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         KAFKA  (KRaft · sin ZooKeeper)                   │
│                                                                          │
│   Broker: ec-kafka:9092 · Apache Kafka 3.7.0                            │
│                                                                          │
│   Topic: casamarket.documento.detectado  — eventos del ERP              │
│   Topic: casamarket.ventas.raw           — filas de venta parseadas     │
│                                                                          │
│   30,372 mensajes · Retención 7 días · 1 partición por topic            │
└──────────────────────────────────────────────────────────────────────────┘
      │ casamarket.documento.detectado          │ casamarket.ventas.raw
      ▼                                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         CONSUMIDORES                                     │
│                                                                          │
│   consumer_downloader.py                consumer_excel_parser.py        │
│   ┌────────────────────┐                ┌────────────────────────────┐   │
│   │ Escucha Kafka      │   .xlsx/.html  │ Escanea output/descargas/  │   │
│   │ documento.detectado│ ─────────────▶ │ Parsea con pandas          │   │
│   │ Descarga archivos  │                │ Normaliza columnas         │   │
│   │ state_downloads.j  │                │ Publica fila por fila      │   │
│   └────────────────────┘                └────────────┬───────────────┘   │
└────────────────────────────────────────────────────┼─────────────────────┘
                                                     │  JSON · 1 fila = 1 mensaje
                                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         SPARK STRUCTURED STREAMING                       │
│                                                                          │
│   job_ventas.py                          job_documentos.py               │
│   ┌────────────────────────┐             ┌────────────────────────────┐  │
│   │ trigger: 30s           │             │ trigger: 30s               │  │
│   │ from_json + schema     │             │ watermark: 10 min          │  │
│   │ Sink 1 → PostgreSQL    │             │ ventana: 5 min             │  │
│   │ Sink 2 → Parquet       │             │ → Parquet métricas         │  │
│   │ Sink 3 → console top15 │             └────────────────────────────┘  │
│   └──────────┬─────────────┘                                             │
└──────────────┼───────────────────────────────────────────────────────────┘
               │
       ┌───────┴──────────────┐
       ▼                      ▼
┌──────────┐           ┌──────────────────────────┐
│ Parquet  │           │  PostgreSQL 16            │
│output/   │           │  tabla: ventas (16,794)   │
│parquet/  │           │  tabla: predicciones_2026 │
└──────────┘           └────────────┬─────────────┘
                                    │
                                    ▼
                       ┌────────────────────────────┐
                       │  ML — scikit-learn          │
                       │  prediccion_ventas.py       │
                       │  LinearRegression por prod  │
                       │  180 predicciones (15×12)   │
                       │  r² = 0.82                  │
                       └────────────┬───────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    OBSERVABILIDAD (Grafana + Prometheus)                  │
│                                                                          │
│  Dashboard S8: Kafka + Spark     → lag, offsets, rate, broker health    │
│  Dashboard S9: Ventas IFERSAN    → KPIs, top productos, predicciones    │
│                                                                          │
│  3 alertas Prometheus:                                                   │
│  · KafkaConsumerLagAlto  → lag_sum > 500  por 2 min   [WARNING]         │
│  · KafkaSinMensajes      → rate offset == 0 por 5 min [WARNING]         │
│  · KafkaBrokerDown       → kafka-exporter up == 0 por 1 min [CRITICAL]  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Stack Tecnológico

| Capa | Tecnología | Versión | Rol |
|---|---|---|---|
| Productor | Python + kafka-python | 3.12 | Consulta ERP IFERSAN, publica en Kafka |
| Broker | Apache Kafka KRaft | 3.7.0 | Sin ZooKeeper · 2 topics |
| Procesamiento | Apache Spark Structured Streaming | 3.5.1 | Micro-batch 30s · exactly-once |
| Base de datos | PostgreSQL | 16 | BI + predicciones · wal_level=logical |
| ML | scikit-learn | latest | LinearRegression por producto |
| Almacén ML | Apache Parquet | — | Columnar · 4 carpetas de salida |
| Visualización | Grafana | latest | 2 dashboards · 29 paneles · auto-refresh 10s |
| Métricas | Prometheus + kafka-exporter | latest | Scraping cada 15s |
| Parser | pandas + openpyxl + lxml | — | Excel/HTML normalizados |
| Orquestación | Docker Compose | — | **13 servicios** · red ec-kafka-dev-net |

### Los 13 servicios Docker

| Servicio | Imagen | Función |
|---|---|---|
| `ec-kafka` | apache/kafka:3.7.0 | Broker Kafka KRaft |
| `kafka-ui` | provectuslabs/kafka-ui | UI de exploración de topics |
| `kafka-exporter` | danielqsj/kafka-exporter | Expone métricas Kafka a Prometheus |
| `casamarket-postgres` | postgres:16 | Base de datos principal |
| `prometheus` | prom/prometheus | TSDB de métricas |
| `grafana` | grafana/grafana | Dashboards BI + operativos |
| `producer` | casamarket-python:latest | Consulta ERP y publica en Kafka |
| `consumer-downloader` | casamarket-python:latest | Descarga archivos del ERP |
| `consumer-excel-parser` | casamarket-python:latest | Parsea Excel → Kafka |
| `spark-ventas` | casamarket-spark:latest | job_ventas.py |
| `spark-docs` | casamarket-spark:latest | job_documentos.py |
| `jupyter-spark` | jupyter/pyspark-notebook | Notebooks ML |
| `debezium` | debezium/connect:2.7 | CDC PostgreSQL → Kafka |

---

## Estructura del Proyecto

```
UnidadII/
├── docker-compose.yml              ← Orquesta los 13 servicios
├── requirements.txt
├── .env                            ← Credenciales ERP (NO subir a git)
│
├── producer/
│   ├── producer.py                 ← 202 líneas · ciclo 300s · JWT auth
│   └── state_documentos.json       ← 175 IDs (180472–183454) · idempotencia
│
├── consumer/
│   ├── consumer_downloader.py      ← Descarga .xlsx/.html a output/descargas/
│   ├── consumer_excel_parser.py    ← Parsea Excel → topic ventas.raw
│   ├── state_downloads.json        ← Qué IDs ya se descargaron
│   └── state_excel_parsed.json     ← Qué archivos ya se parsearon
│
├── spark_streaming/
│   ├── job_ventas.py               ← Streaming ventas → Parquet + PostgreSQL
│   └── job_documentos.py           ← Streaming docs → Parquet (ventanas 5 min)
│
├── ml/
│   └── prediccion_ventas.py        ← LinearRegression sklearn → predicciones_2026
│
├── notebooks/
│   └── 02_ml_prediccion_ventas.ipynb
│
├── postgres/
│   └── init.sql                    ← DDL: ventas, predicciones_2026, vistas
│
├── observability/
│   ├── alertas.yml                 ← 3 reglas Prometheus
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/ds.yml  ← casamarket-prom + casamarket-pg
│       │   └── dashboards/dashboard.yml
│       └── dashboards/
│           ├── kafka_spark.json    ← Dashboard S8
│           └── ventas_casamarket.json ← Dashboard S9
│
├── output/
│   ├── descargas/                  ← 84 archivos Excel/HTML · 44 MB
│   ├── parquet/ventas/             ← Datos para entrenamiento ML
│   ├── parquet/docs/               ← Métricas de documentos con ventanas
│   └── checkpoints/                ← Exactly-once Spark
│
├── docs/                           ← Documentación técnica por componente
│   ├── arquitectura/
│   ├── componentes/
│   ├── observabilidad/
│   └── resultados/
│
└── pptx/
    └── IFERSAN_PitchDeck.pptx      ← Presentación pitch deck v5
```

---

## Servicios y Puertos

| Servicio | URL | Credenciales | Para qué |
|---|---|---|---|
| **Grafana** | http://localhost:43000 | admin / casamarket | Dashboards BI + observabilidad |
| **Kafka UI** | http://localhost:18085 | — | Explorar topics y mensajes |
| **Jupyter** | http://localhost:8888 | token: casamarket | Notebooks ML |
| **Spark UI ventas** | http://localhost:4042 | — | Jobs de job_ventas.py |
| **Spark UI docs** | http://localhost:4041 | — | Jobs de job_documentos.py |
| **Prometheus** | http://localhost:49090 | — | Métricas en bruto |
| **PostgreSQL** | localhost:15432 | casamarket / casamarket | DBeaver / psql |

---

## Cómo Levantar el Sistema

### Requisitos previos

- Docker Desktop corriendo
- Archivo `.env` en la raíz:

```env
API_BASE_URL=https://admin.casamarket.la
API_EMAIL=admin1@tomas.com
API_PASSWORD=76284084
COMPANY_ID=5588
KAFKA_BOOTSTRAP=localhost:19092
```

> El `COMPANY_ID=5588` identifica a IFERSAN dentro del ERP CasaMarket.

### Paso 1 — Levantar

```bash
docker compose up -d
```

Espera ~60 segundos. Kafka (`ec-kafka`) tarda en arrancar; los demás esperan a que esté healthy.

### Paso 2 — Verificar los 13 servicios

```bash
docker compose ps
```

Los críticos:

| Servicio | Estado esperado |
|---|---|
| `ec-kafka` | Up (healthy) |
| `casamarket-postgres` | Up (healthy) |
| `producer` | Up |
| `consumer-downloader` | Up |
| `consumer-excel-parser` | Up |
| `spark-ventas` | Up |
| `grafana` | Up |

### Paso 3 — El pipeline arranca solo

```
1. producer.py      → consulta ERP cada 300s → publica en casamarket.documento.detectado
2. consumer-downloader → descarga .xlsx/.html → output/descargas/
3. consumer-excel-parser → parsea fila por fila → publica en casamarket.ventas.raw
4. spark-ventas     → consume ventas.raw cada 30s → escribe en PostgreSQL + Parquet
5. grafana          → lee PostgreSQL → actualiza dashboards cada 10s
```

### Paso 4 — Abrir Grafana

**http://localhost:43000** · admin / casamarket

- **Dashboard S8 — Kafka + Spark**: broker health, consumer lag, offsets, rate
- **Dashboard S9 — Ventas IFERSAN**: KPIs reales + Top productos + ML 2026

### Paso 5 — Ejecutar predicciones ML (ya están guardadas, solo si quieres regenerarlas)

```bash
docker cp ml/prediccion_ventas.py jupyter-spark:/home/jovyan/prediccion_ventas.py
docker exec jupyter-spark sh -c "python /home/jovyan/prediccion_ventas.py"
```

---

## Mensaje Kafka — Formato Real

### Topic `casamarket.documento.detectado` (producer → downloader)

```json
{
  "id": 180472,
  "filename": "detalle_de_ventas__2026_05_19_10_02_47_xlsx_5588.xlsx",
  "extension": "xlsx",
  "status": "Finalizado",
  "url_file": "https://s3.amazonaws.com/casamarket-prod/...",
  "created_at": "2026-04-27T07:32:51Z",
  "usuario": "admin1@tomas.com",
  "detectado_en": "2026-05-26T03:47:28.000000+00:00"
}
```

### Topic `casamarket.ventas.raw` (parser → Spark)

```json
{
  "fecha": "2026-05-12",
  "producto": "PEPSI 2000ML",
  "cod_producto": "PEP-001",
  "marca": "LINEA PEPSI",
  "categoria": "GASEOSAS PEPSI",
  "cantidad": "6",
  "precio_unitario": "19.07",
  "total": "144.0",
  "cliente": "YOLANDA GONZA HUANCA",
  "ruc_cliente": "17107",
  "vendedor": "ROSA CUSILAYME",
  "zona": "ZONA NORTE",
  "_archivo": "detalle_de_ventas__2026_05_19_xlsx.xlsx"
}
```

---

## Parámetros Spark

| Parámetro | Valor | Por qué |
|---|---|---|
| `trigger` | 30s | Bajo lag, poco overhead |
| `watermark` | 10 min | Tolera eventos tardíos de red |
| `ventana` (docs) | 5 min | Agrupa por períodos manejables |
| `output mode` | append (ventas) | Evita duplicados en PostgreSQL |
| `checkpoint` | output/checkpoints/ventas_agg | Exactly-once |
| `shuffle.partitions` | 2 | Ajustado a entorno local[2] |
| `startingOffsets` | earliest | Lee desde el inicio si no hay checkpoint |

---

## Métricas de Rendimiento Medidas

| Prueba | Mensajes | Throughput | Lag final |
|---|---|---|---|
| Carga inicial (con checkpoint) | 15,186 | ~506 msg/s | 0 |
| Re-proceso completo (sin checkpoint) | 30,372 | **~6,074 msg/s** | **0** |
| job_documentos (ventanas 5 min) | ~83 | ~3 msg/s | 0 |

---

## Base de Datos PostgreSQL

```sql
-- Tabla principal (16,794 filas reales de IFERSAN)
ventas (
  id SERIAL PRIMARY KEY,
  fecha DATE,
  producto TEXT,           -- "PEPSI 2000ML", "INCA KOLA 1.5L", ...
  cod_producto TEXT,       -- "PEP-001"
  marca TEXT,              -- "LINEA PEPSI"
  categoria TEXT,          -- "GASEOSAS PEPSI"
  cantidad NUMERIC,
  precio_unitario NUMERIC,
  total NUMERIC,           -- SUM = S/ 406,150.50
  cliente TEXT,            -- "YOLANDA GONZA HUANCA"
  vendedor TEXT,           -- "ROSA CUSILAYME" (líder S/101,500)
  zona TEXT,               -- "ZONA NORTE"
  procesado_ts TIMESTAMP
)

-- Predicciones ML (180 filas: 15 productos × 12 meses)
predicciones_2026 (
  id SERIAL PRIMARY KEY,
  producto TEXT,
  mes INT,                 -- 1=Ene, 12=Dic
  ingresos_real NUMERIC,   -- datos históricos Abr-May
  ingresos_pred NUMERIC,   -- proyectado por LinearRegression
  unidades_pred NUMERIC,
  modelo TEXT,             -- "LinearRegression"
  r2_score NUMERIC,        -- 0.82
  generado_en TIMESTAMP
)
```

**Consultas rápidas:**
```sql
-- Top 5 productos de IFERSAN
SELECT producto, ROUND(SUM(total)::NUMERIC, 2) AS ingresos
FROM ventas WHERE total > 0
GROUP BY producto ORDER BY ingresos DESC LIMIT 5;

-- Ranking de vendedores (ROSA CUSILAYME #1)
SELECT vendedor, ROUND(SUM(total)::NUMERIC, 2) AS ingresos
FROM ventas WHERE total > 0
GROUP BY vendedor ORDER BY ingresos DESC;

-- Proyección 2026 por producto
SELECT producto, ROUND(SUM(ingresos_pred)::NUMERIC, 2) AS proyectado_2026
FROM predicciones_2026
GROUP BY producto ORDER BY proyectado_2026 DESC;

-- Total proyectado 2026
SELECT ROUND(SUM(ingresos_pred)::NUMERIC, 2) FROM predicciones_2026;
-- Resultado: S/ 1,614,943.32
```

---

## Dashboards Grafana

### Dashboard S8 — Kafka + Spark
**Datasource:** Prometheus · **9 paneles operativos**

| Panel | PromQL |
|---|---|
| Kafka Broker UP/DOWN | `up{job="kafka-exporter"}` |
| Topics activos | `count(kafka_topic_partitions)` |
| Offset — ventas.raw | `kafka_topic_partition_current_offset{topic="casamarket.ventas.raw"}` |
| Consumer Lag (gauge 0-1000) | `kafka_consumergroup_lag_sum` |
| Rate mensajes/s | `rate(kafka_topic_partition_current_offset{topic="casamarket.ventas.raw"}[5m])` |

### Dashboard S9 — Ventas IFERSAN
**Datasource:** PostgreSQL · **29 paneles** · Auto-refresh 10s

| Sección | Panel | Valor real |
|---|---|---|
| KPI | Total Ingresos | **S/ 406,150.50** |
| KPI | Transacciones | **16,794** |
| KPI | Productos únicos | **62** |
| KPI | Clientes únicos | **1,106** |
| Histórico | Ingresos diarios | Timeseries Abr 27 – May 19 |
| Histórico | Top 15 productos | PEPSI 2000ML · INCA KOLA · COCA COLA... |
| Distribución | Ingresos por Vendedor | ROSA CUSILAYME S/101,500 |
| ML 2026 | Proyectado total | **S/ 1,614,943.32** |
| ML 2026 | PEPSI 2000ML 2026 | **S/ 334,800** |
| ML 2026 | Tendencia mensual | Timeseries Ene–Dic 2026 |
| ML 2026 | Tabla completa | 180 filas (15 prod × 12 meses) |

---

## Alertas Prometheus (alertas.yml)

```yaml
# KafkaConsumerLagAlto — WARNING
expr:  kafka_consumergroup_lag_sum > 500
for:   2m
# Se dispara si el consumer acumula más de 500 mensajes por 2 minutos.
# Causa típica: Spark detenido o carga pico de documentos.

# KafkaSinMensajes — WARNING
expr:  rate(kafka_topic_partition_current_offset[5m]) == 0
for:   5m
# Se dispara si no hay nuevos mensajes en ningún topic por 5 minutos.
# Causa típica: producer.py caído o API del ERP inaccesible.

# KafkaBrokerDown — CRITICAL
expr:  up{job="kafka-exporter"} == 0
for:   1m
# Se dispara si el kafka-exporter no responde por 1 minuto.
# Todos los servicios dependientes fallan.
```

---

## Comandos Útiles

```bash
# Logs en tiempo real
docker compose logs -f producer
docker compose logs -f consumer-excel-parser
docker compose logs -f spark-ventas

# Ver cuántas ventas hay en PostgreSQL
docker compose exec casamarket-postgres psql -U casamarket -d casamarket -c \
  "SELECT COUNT(*), ROUND(SUM(total)::NUMERIC,2) FROM ventas WHERE total>0;"

# Cuántos documentos publicó el producer
docker compose exec casamarket-postgres psql -U casamarket -d casamarket -c \
  "SELECT COUNT(DISTINCT _archivo) FROM ventas;"

# Ver mensajes raw en Kafka (últimos 5)
docker exec ec-kafka sh -c \
  "/opt/kafka/bin/kafka-console-consumer.sh \
   --bootstrap-server localhost:9092 \
   --topic casamarket.ventas.raw --max-messages 5 \
   --from-beginning --timeout-ms 5000"

# Verificar alertas Prometheus
curl http://localhost:49090/api/v1/alerts

# Re-ejecutar ML
docker cp ml/prediccion_ventas.py jupyter-spark:/home/jovyan/prediccion_ventas.py
docker exec jupyter-spark sh -c "python /home/jovyan/prediccion_ventas.py"

# Reiniciar un servicio
docker compose restart spark-ventas
docker compose restart grafana

# Parar todo
docker compose down

# Limpieza total (borra volúmenes y datos)
docker compose down -v
```

---

## Guión de Exposición — 5 Minutos

> El objetivo no es explicar tecnología: es mostrar que **ya funciona con datos reales de IFERSAN**.

### [0:00 – 0:50] El problema que resolvimos

Abrir el README o la presentación. Decir:

> "IFERSAN es una distribuidora de bebidas en Juliaca. Antes de este proyecto, la gerencia recibía los datos de ventas del día **24 horas después**, en un Excel. ROSA CUSILAYME vendía S/ 101,500 en un mes y nadie lo sabía hasta el día siguiente. Nosotros construimos el pipeline que cambia eso."

### [0:50 – 1:30] Mostrar el productor funcionando

Abrir **Kafka UI → http://localhost:18085**

- Topic `casamarket.documento.detectado`: mostrar 175 mensajes (IDs 180472–183454)
- Topic `casamarket.ventas.raw`: mostrar 30,372 mensajes
- Abrir un mensaje del topic ventas.raw → mostrar el JSON con `"vendedor": "ROSA CUSILAYME"`, `"producto": "PEPSI 2000ML"`, `"total": "144.0"`

Decir:
> "Cada fila del Excel de ventas se convierte en un mensaje JSON en Kafka. 16,794 ventas de IFERSAN están aquí."

### [1:30 – 2:15] Mostrar Spark procesando

Abrir **Spark UI → http://localhost:4042**

- Mostrar los batches de 30s corriendo
- Mostrar input rate y processing time

Decir:
> "Spark lee esos mensajes cada 30 segundos y los escribe en PostgreSQL. En el re-proceso medimos **6,074 mensajes por segundo**. El consumer lag final fue **cero**."

### [2:15 – 3:30] Dashboard S9 — Ventas IFERSAN

Abrir **Grafana → http://localhost:43000 → Dashboard S9**

- **KPIs superiores**: señalar S/ 406,150.50 · 16,794 transacciones · 62 productos
- **Top productos**: señalar PEPSI 2000ML como líder (S/ 76,400)
- **Vendedores**: señalar ROSA CUSILAYME (#1, S/ 101,500) y JHONATAN (#2)
- **Predicciones ML 2026**: señalar S/ 1,614,943.32 total
- Señalar PEPSI 2000ML proyectado en S/ 334,800 (factor 4.4×)

Decir:
> "Esto es lo que ve la gerencia de IFERSAN ahora mismo. No el Excel de mañana. El dato de hoy, en menos de 8 minutos desde que el vendedor cierra la venta."

### [3:30 – 4:20] Dashboard S8 + Alertas

Abrir **Grafana → Dashboard S8**

- Mostrar: Kafka Broker = **UP**
- Mostrar: Consumer Lag = **0**
- Mostrar el panel de Rate mensajes/s

Decir:
> "Tenemos 3 alertas configuradas en Prometheus. Si el consumer lag supera 500 mensajes por más de 2 minutos, se dispara un warning. Si el broker cae, tenemos una alerta crítica en 1 minuto."

### [4:20 – 5:00] Cerrar con el código

Mostrar brevemente `producer/producer.py` línea 1-30 (ciclo, auth, publish).
Mostrar `ml/prediccion_ventas.py` (LinearRegression, 180 predicciones).

Decir:
> "13 servicios Docker. 9 tecnologías. 202 líneas de productor. El sistema corre completo en `docker compose up`. Gracias."

---

## Problemas Conocidos y Soluciones

| Problema | Causa | Solución |
|---|---|---|
| Grafana "No data" | UID de datasource no coincide | `docker compose down -v grafana_data && docker compose up -d grafana` |
| `marca`/`categoria` vacíos | Spark procesó con schema antiguo (checkpoint viejo) | Borrar checkpoint + `TRUNCATE ventas` + reiniciar spark-ventas |
| Excel con 0 filas | Parser era event-driven, dependía de Kafka para trigger | Reescrito como directory scanner independiente |
| `producto` vacío en mensajes | `descripcion` sobreescribía `nombre` (alias duplicado en `_ALIAS`) | Removido `"descripcion": "producto"` del dict de alias |
| JSONDecodeError BOM UTF-8 | PowerShell escribe con BOM en el JSON de estado | `encoding="utf-8-sig"` en `load_parsed()` |
| `url_file` = undefined | Se usaba `downloadUrl` (campo inválido de la API) | Cambiado a `urlFile` que sí contiene la URL real del S3 |
| ThroughputListener crash | Clase Python incompatible con JVM de Spark | Clase removida completamente |

---

*Pipeline construido con datos reales de IFERSAN — distribuidora de bebidas de Juliaca, Perú.*  
*Universidad Peruana Unión · IX Ciclo · Big Data · Unidad 2 · Junio 2026*

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                            C A R A T U L A                             -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

<div align="center">

<br>

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║          ██╗███████╗███████╗██████╗ ███████╗ █████╗ ███╗   ██╗             ║
║          ██║██╔════╝██╔════╝██╔══██╗██╔════╝██╔══██╗████╗  ██║             ║
║          ██║█████╗  █████╗  ██████╔╝███████╗███████║██╔██╗ ██║             ║
║          ██║██╔══╝  ██╔══╝  ██╔══██╗╚════██║██╔══██║██║╚██╗██║             ║
║          ██║██║     ███████╗██║  ██║███████║██║  ██║██║ ╚████║             ║
║          ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝             ║
║                                                                              ║
║       PIPELINE BIG DATA EN TIEMPO REAL · ARQUITECTURA KAPPA + ML           ║
║                                                                              ║
║    "De un Excel con 24 horas de retraso a datos en vivo en 8 minutos"      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

<br>

![Kafka](https://img.shields.io/badge/Apache_Kafka-3.7.0-231F20?style=for-the-badge&logoColor=white&color=231F20)
![Spark](https://img.shields.io/badge/Apache_Spark-3.5.1-E25A1C?style=for-the-badge&logoColor=white&color=E25A1C)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logoColor=white&color=336791)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logoColor=white&color=3776AB)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML_v3-F7931E?style=for-the-badge&logoColor=white&color=F7931E)
![Grafana](https://img.shields.io/badge/Grafana-Dashboards-F46800?style=for-the-badge&logoColor=white&color=F46800)
![Docker](https://img.shields.io/badge/Docker-15_servicios-2496ED?style=for-the-badge&logoColor=white&color=2496ED)

<br>

![Transacciones](https://img.shields.io/badge/Transacciones_procesadas-16%2C794-0A2342?style=flat-square&color=0A2342)
![Ingresos](https://img.shields.io/badge/Ingresos_reales-S%2F_406%2C150-1E6091?style=flat-square&color=1E6091)
![MAPE](https://img.shields.io/badge/MAPE_prediccion-6.9%25-2D6A4F?style=flat-square&color=2D6A4F)
![Throughput](https://img.shields.io/badge/Throughput_Spark-6%2C074_msg%2Fs-5C4B8A?style=flat-square&color=5C4B8A)

<br>

---

**Universidad Peruana Unión · Facultad de Ingeniería y Arquitectura**

**IX Ciclo · Curso: Big Data · Unidad 2 · Junio 2026**

Docente: **Mg. Angel Sullon**

---

| Alumno | Rol en el Proyecto |
|:---|:---|
| **Alessandro Pastor Mamani Mamani** | Arquitectura Kappa, pipeline completo, ML v3 |
| **Cabana Sulca Cristian** | Consumer, parser, integración Kafka |
| **Montes Mamani Andres Lino** | Spark Structured Streaming, PostgreSQL |
| **Fernandez Sanchez Jean Piero** | Machine Learning, Grafana, observabilidad |

<br>

</div>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                        1. EL PROBLEMA                                   -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

---

# PARTE I — EL PROBLEMA

## CasaMarket: un ERP que entrega los datos 24 horas tarde

**CasaMarket** es un ERP peruano de gestión de ventas. Sus clientes —distribuidoras, ferreterías, bodegas— registran cientos de transacciones diarias a través de vendedores en campo.

El sistema genera reportes en formato **Excel o HTML** que el área comercial descarga manualmente al día siguiente.

### El caso real: IFERSAN — Distribuidora de Bebidas · Juliaca, Puno

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   IFERSAN distribuye: Pepsi · Inca Kola · Coca Cola · Escocesa · Pilsen   │
│                                                                             │
│   Sus vendedores cierran ventas en campo todo el dia usando CasaMarket.   │
│                                                                             │
│   ¿Cuándo ve la gerencia esos datos?   →   Al dia siguiente.              │
│   ¿En qué formato?                     →   Un Excel de 500 filas.         │
│   ¿Puede consultarlo en tiempo real?   →   No.                             │
│                                                                             │
│   ROSA CUSILAYME vendio S/ 101,500 este mes.                              │
│   La gerencia lo supo 24 horas despues de cada venta.                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Las 4 fricciones que identificamos

| # | Fricción | Impacto |
|:---:|:---|:---|
| 1 | Datos disponibles **24 h después** de cada venta | Decisiones con información del día anterior |
| 2 | Formato Excel — **no escalable**, no consultable | Análisis manual, propenso a errores |
| 3 | **Sin alertas**: nadie sabe si las ventas cayeron hoy | Problemas detectados cuando ya es tarde |
| 4 | **Sin predicciones**: la gerencia no sabe qué esperar mañana | Planificación de stock basada en intuición |

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                        2. LA PROPUESTA                                  -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# PARTE II — LA PROPUESTA

## Arquitectura Kappa: streaming puro, sin batch

Proponemos reemplazar el flujo Excel-por-correo por un **pipeline de datos en tiempo real** construido sobre tecnología de producción.

> Cada venta registrada en el ERP de IFERSAN aparece en Grafana en **menos de 8 minutos**.
> Sin Excel. Sin espera. Automático. Con predicciones ML actualizadas cada 30 minutos.

### ¿Por qué Arquitectura Kappa y no Lambda?

```
LAMBDA (tradicional)          KAPPA (nuestra propuesta)
─────────────────────         ──────────────────────────
Batch layer  → lento          Un solo stream → simple
Speed layer  → complejo       Kafka como log unificado
Serving layer → duplicado     Un solo sink → PostgreSQL
2 pipelines que mantener      1 pipeline que mantener
```

La arquitectura Kappa usa **Kafka como fuente de verdad única**. Todo pasa por el stream — no hay batch separado. Más simple, más mantenible, igualmente potente.

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                        3. ARQUITECTURA                                  -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# PARTE III — ARQUITECTURA DEL PIPELINE

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  FUENTE  ·  ERP CasaMarket                                                ║
║                                                                           ║
║  admin.casamarket.la   ·   COMPANY_ID = 5588 (IFERSAN)                   ║
║  API Auth  → POST /api/authenticate         → JWT Bearer Token            ║
║  API Docs  → GET  /documents?startDate&...  → Lista paginada              ║
║                                                                           ║
║  Formato: .xlsx / .html   ·   status = Finalizado                        ║
║  175 documentos descargados   ·   IDs 180472 – 183454                    ║
╚═══════════════════════════╤═══════════════════════════════════════════════╝
                            │  JWT · paginado · ciclo cada 300s
                            ▼
╔═══════════════════════════════════════════════════════════════════════════╗
║  PRODUCTOR  ·  producer.py                                                ║
║                                                                           ║
║  1. Autentica contra la API → obtiene token JWT                          ║
║  2. Lista documentos nuevos (status=2, id NOT IN state.json)             ║
║  3. Publica evento JSON por cada documento → Kafka                       ║
║  4. Persiste IDs procesados → idempotencia garantizada                   ║
║                                                                           ║
║  Configuración Kafka: acks=all · retries=3 · delivery.guarantee=exactly  ║
╚═══════════════════════════╤═══════════════════════════════════════════════╝
                            │  Topic: casamarket.documento.detectado
                            ▼
╔═══════════════════════════════════════════════════════════════════════════╗
║  KAFKA  ·  Apache Kafka 3.7.0 KRaft (sin ZooKeeper)                      ║
║                                                                           ║
║  Topic 1: casamarket.documento.detectado  →  eventos del ERP             ║
║  Topic 2: casamarket.ventas.raw           →  filas de venta parseadas    ║
║                                                                           ║
║  30,372 mensajes totales   ·   Retención 7 días   ·   1 broker           ║
╚══════════╤════════════════════════════════════╤══════════════════════════╝
           │ documento.detectado                │ ventas.raw
           ▼                                   ▼
╔══════════════════════╗           ╔══════════════════════════════════════╗
║  CONSUMER            ║           ║  CONSUMER                            ║
║  consumer_downloader ║  ──────▶  ║  consumer_excel_parser               ║
║                      ║  .xlsx    ║                                       ║
║  Escucha Kafka       ║  .html    ║  Escanea output/descargas/           ║
║  Descarga archivos   ║           ║  Parsea con pandas                   ║
║  del ERP via HTTP    ║           ║  Normaliza columnas                  ║
║                      ║           ║  1 fila Excel = 1 mensaje Kafka      ║
╚══════════════════════╝           ╚═════════════════╤════════════════════╝
                                                     │ JSON · 1 venta por mensaje
                                                     ▼
╔═══════════════════════════════════════════════════════════════════════════╗
║  SPARK STRUCTURED STREAMING  ·  Apache Spark 3.5.1                        ║
║                                                                           ║
║  job_ventas.py               job_documentos.py                           ║
║  ┌─────────────────────┐     ┌─────────────────────────────────────────┐ ║
║  │ trigger: 30s        │     │ trigger: 30s · watermark: 10 min        │ ║
║  │ from_json + schema  │     │ ventana: 5 min · agrupa documentos      │ ║
║  │ → PostgreSQL        │     │ → Parquet métricas                      │ ║
║  │ → Parquet ventas    │     └─────────────────────────────────────────┘ ║
║  │ → console top15     │                                                  ║
║  └─────────────────────┘                                                  ║
║                                                                           ║
║  Throughput medido: 6,074 msg/s   ·   Consumer lag final: 0              ║
║  Checkpoint: exactly-once   ·   shuffle.partitions: 2                    ║
╚══════════╤════════════════════════════════════════════════════════════════╝
           │
     ┌─────┴──────────────────────────┐
     ▼                                ▼
╔══════════════╗              ╔═══════════════════════════════════════════╗
║   Parquet    ║              ║  PostgreSQL 16                             ║
║   output/    ║              ║                                           ║
║   parquet/   ║              ║  ventas           (16,794 filas reales)  ║
║              ║              ║  predicciones_diarias  (GBM · 62 días)   ║
║  Columnar    ║              ║  segmentos_clientes    (RFM · 1,106)      ║
║  Histórico   ║              ║  anomalias_detectadas  (IsolationForest)  ║
║  ML training ║              ║  model_metadata        (R², MAPE, MAE)   ║
╚══════════════╝              ╚═════════════════╤═════════════════════════╝
                                               │
                      ┌────────────────────────┤
                      ▼                        ▼
╔═══════════════════════════════╗    ╔══════════════════════════════════╗
║  ML TRAINER (cada 30 min)     ║    ║  GRAFANA + PROMETHEUS            ║
║                               ║    ║                                  ║
║  6 modelos scikit-learn:      ║    ║  Dashboard S8: Kafka + Spark     ║
║  · GBM diario por producto    ║    ║  Dashboard S9: Ventas IFERSAN    ║
║  · Forecast mensual P10/P90   ║    ║                                  ║
║  · Modelo mensual directo     ║    ║  3 alertas Prometheus activas    ║
║  · KMeans RFM clientes        ║    ║  Auto-refresh cada 10 segundos   ║
║  · IsolationForest anomalias  ║    ║                                  ║
║  · GBM semanal vendedores     ║    ║  ML Web → localhost:8501         ║
╚═══════════════════════════════╝    ╚══════════════════════════════════╝
```

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                        4. STACK TECNOLOGICO                             -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# PARTE IV — STACK TECNOLOGICO

## Tecnologías seleccionadas y por qué

```
┌─────────────────┬──────────────────────────┬───────────────────────────────────────┐
│ CAPA            │ TECNOLOGIA               │ POR QUE LA ELEGIMOS                   │
├─────────────────┼──────────────────────────┼───────────────────────────────────────┤
│ Ingestión       │ Python + kafka-python     │ Control total sobre el productor;     │
│                 │ 3.12                      │ JWT auth + paginación + idempotencia  │
├─────────────────┼──────────────────────────┼───────────────────────────────────────┤
│ Mensajería      │ Apache Kafka 3.7.0        │ Log distribuido inmutable; KRaft      │
│                 │ KRaft (sin ZooKeeper)     │ elimina dependencia de ZooKeeper;     │
│                 │                          │ exactamente-una-vez garantizado        │
├─────────────────┼──────────────────────────┼───────────────────────────────────────┤
│ Procesamiento   │ Apache Spark 3.5.1        │ Micro-batch 30s; exactly-once con     │
│                 │ Structured Streaming      │ checkpointing; schema enforcement      │
├─────────────────┼──────────────────────────┼───────────────────────────────────────┤
│ Almacenamiento  │ PostgreSQL 16             │ SQL completo para BI; wal_level=      │
│                 │ + Apache Parquet          │ logical para CDC; Parquet para ML     │
├─────────────────┼──────────────────────────┼───────────────────────────────────────┤
│ Machine         │ scikit-learn 1.4+         │ GBM + KMeans + IsolationForest;       │
│ Learning        │ GBM · KMeans · IF         │ 6 modelos especializados por dominio  │
├─────────────────┼──────────────────────────┼───────────────────────────────────────┤
│ Web ML          │ FastAPI + Chart.js        │ SPA liviana; tiempo real via SSE;     │
│                 │ (ml-web)                  │ sin framework pesado                  │
├─────────────────┼──────────────────────────┼───────────────────────────────────────┤
│ Visualización   │ Grafana + Prometheus      │ Dashboards BI + operativos en un      │
│                 │                          │ solo lugar; alertas nativas            │
├─────────────────┼──────────────────────────┼───────────────────────────────────────┤
│ Orquestación    │ Docker Compose            │ 15 servicios reproducibles en         │
│                 │ 15 servicios              │ cualquier máquina con docker up       │
└─────────────────┴──────────────────────────┴───────────────────────────────────────┘
```

### Los 15 contenedores del sistema

```
┌─────────────────────────┬──────────────────────────────┬─────────────────────────┐
│ CONTENEDOR              │ IMAGEN                       │ FUNCION                 │
├─────────────────────────┼──────────────────────────────┼─────────────────────────┤
│ ec-kafka                │ apache/kafka:3.7.0            │ Broker Kafka KRaft      │
│ kafka-ui                │ provectuslabs/kafka-ui        │ UI exploración topics   │
│ kafka-exporter          │ danielqsj/kafka-exporter      │ Métricas → Prometheus   │
├─────────────────────────┼──────────────────────────────┼─────────────────────────┤
│ postgres                │ postgres:16                   │ Base de datos principal │
├─────────────────────────┼──────────────────────────────┼─────────────────────────┤
│ prometheus              │ prom/prometheus               │ TSDB de métricas        │
│ grafana                 │ grafana/grafana               │ Dashboards BI           │
├─────────────────────────┼──────────────────────────────┼─────────────────────────┤
│ producer                │ casamarket-python             │ Consulta ERP → Kafka    │
│ consumer-downloader     │ casamarket-python             │ Descarga archivos ERP   │
│ consumer-excel-parser   │ casamarket-python             │ Parsea Excel → Kafka    │
├─────────────────────────┼──────────────────────────────┼─────────────────────────┤
│ spark-ventas            │ casamarket-spark              │ job_ventas.py           │
│ spark-docs              │ casamarket-spark              │ job_documentos.py       │
│ jupyter-spark           │ jupyter/pyspark-notebook      │ Notebooks exploración   │
├─────────────────────────┼──────────────────────────────┼─────────────────────────┤
│ debezium                │ debezium/connect:2.7          │ CDC PostgreSQL → Kafka  │
│ ml-trainer              │ casamarket-python             │ Re-entrena 6 modelos    │
│ ml-web                  │ casamarket-python             │ SPA predicciones web    │
└─────────────────────────┴──────────────────────────────┴─────────────────────────┘
```

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                        5. RESULTADOS REALES                             -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# PARTE V — RESULTADOS CON DATOS REALES DE IFERSAN

> Todos los números que siguen provienen del pipeline corriendo con datos reales
> de IFERSAN entre el 27 de Abril y el 19 de Mayo de 2026.

## Datos del negocio

```
┌─────────────────────────────────────┬────────────────────────────────────┐
│  METRICA                            │  VALOR REAL                        │
├─────────────────────────────────────┼────────────────────────────────────┤
│  Transacciones procesadas           │  16,794                            │
│  Ingresos reales registrados        │  S/ 406,150.50                     │
│  Periodo de datos                   │  27 Abr – 19 May 2026              │
│  Documentos ERP descargados         │  175 archivos (IDs 180472–183454)  │
│  Archivos Excel/HTML almacenados    │  84 archivos · 44 MB               │
│  Productos únicos                   │  62                                │
│  Clientes únicos                    │  1,106                             │
├─────────────────────────────────────┼────────────────────────────────────┤
│  Producto #1                        │  PEPSI 2000ML — S/ 76,400          │
│  Producto #2                        │  INCA KOLA 500ML — S/ 62,300       │
│  Producto #3                        │  COCA COLA 500ML — S/ 48,100       │
├─────────────────────────────────────┼────────────────────────────────────┤
│  Vendedor #1                        │  ROSA CUSILAYME — S/ 101,500       │
│  Vendedor #2                        │  JHONATAN — S/ 92,000              │
└─────────────────────────────────────┴────────────────────────────────────┘
```

## Rendimiento del pipeline

```
┌─────────────────────────────────────┬────────────────────────────────────┐
│  METRICA                            │  VALOR MEDIDO                      │
├─────────────────────────────────────┼────────────────────────────────────┤
│  Mensajes en Kafka (2 topics)       │  30,372                            │
│  Latencia ERP → Grafana             │  < 8 minutos                       │
│  Throughput Spark (re-proceso)      │  6,074 msg/s                       │
│  Consumer lag final                 │  0 (cero)                          │
│  Trigger Spark micro-batch          │  30 segundos                       │
│  Auto-refresh Grafana               │  10 segundos                       │
│  Garantía de entrega                │  Exactly-once (checkpoint)         │
└─────────────────────────────────────┴────────────────────────────────────┘
```

## Dashboards Grafana

### Dashboard S8 — Operativo Kafka + Spark

Datasource: Prometheus · 9 paneles operativos

| Panel | Métrica PromQL | Valor en producción |
|:---|:---|:---|
| Kafka Broker Status | `up{job="kafka-exporter"}` | UP |
| Topics activos | `count(kafka_topic_partitions)` | 2 |
| Offset ventas.raw | `kafka_topic_partition_current_offset` | 30,372 |
| Consumer Lag | `kafka_consumergroup_lag_sum` | 0 |
| Rate mensajes/s | `rate(...[5m])` | pico 6,074 msg/s |

### Dashboard S9 — Ventas IFERSAN

Datasource: PostgreSQL · 29 paneles · Auto-refresh 10s

| Sección | Panel | Dato real |
|:---|:---|:---|
| KPI | Total ingresos | S/ 406,150.50 |
| KPI | Transacciones | 16,794 |
| KPI | Productos únicos | 62 |
| KPI | Clientes únicos | 1,106 |
| Histórico | Timeseries ingresos diarios | 27 Abr – 19 May 2026 |
| Distribución | Top 15 productos | PEPSI 2000ML lidera |
| Distribución | Ingresos por vendedor | ROSA CUSILAYME S/101,500 |
| ML | Forecast julio 2026 | S/ 1,008,375 |
| ML | Estado hoy vs predicción | Desviación +16.8% ESCOCESA |
| ML | Segmentos clientes | 203 VIP · 204 Regular · 699 En Riesgo |
| ML | Anomalías detectadas | 155 eventos en 56 productos |

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                        6. MACHINE LEARNING                              -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# PARTE VI — CAPA DE MACHINE LEARNING

## Seis modelos especializados · Re-entrenamiento cada 30 minutos

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ml-trainer ejecuta este ciclo cada 30 minutos:                        │
│                                                                         │
│  1. GBM Diario por producto     trainer.py          → predicciones_diarias     │
│  2. Forecast Mensual Agregado   trainer_forecast.py → predicciones_mes_siguiente  │
│  3. Modelo Mensual Directo      trainer_mensual.py  → predicciones_mensuales   │
│  4. KMeans RFM Clientes         trainer_clientes.py → segmentos_clientes       │
│  5. IsolationForest Anomalías   trainer_anomalias.py→ anomalias_detectadas     │
│  6. GBM Semanal Vendedores      trainer_vendedor.py → predicciones_vendedor    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Modelo 1 — GBM Diario por Producto

**Objetivo:** predecir los ingresos diarios de cada producto para los próximos 62 días.

**Algoritmo:** `GradientBoostingRegressor` (scikit-learn)

**Decisión de diseño clave — Ventana de entrenamiento de 35 días:**

```
PROBLEMA DETECTADO EN DATOS REALES:

  Mayo 12-19: ventas S/ 9,000-13,000 / día   (límite API eliminado temporalmente)
  Mayo 20+  : ventas S/ 2,500-3,000 / día    (régimen estable operativo)

  Con 60 días de historial: el GBM aprendía el spike y producía R² = -351
  Con los últimos 35 días:  el GBM entrena solo en el régimen estable → R² = -0.34
```

**Configuración del modelo:**

| Parámetro | Valor | Razón |
|:---|:---|:---|
| Ventana entrenamiento | últimos 35 días | Aísla el régimen operativo estable |
| `n_estimators` | 80 / 200 / 250 | Adaptativo según n de muestras |
| `max_depth` | 3 | Evita memorizar ruido diario |
| `learning_rate` | 0.08 | Convergencia lenta = más robusto |
| `subsample` | 0.8 | Bagging: 80% de filas por árbol |
| Clip outliers | mediana + 3σ | Capea picos residuales extremos |
| Quantile P10/P90 | solo si n ≥ 50 | Con menos datos las bandas son inútiles |

**Features de entrenamiento (20 variables):**

```
Calendario: dia_semana  · dia_mes   · semana_mes  · es_fin_semana
Estacional: mes_sin     · mes_cos   · dia_anio_sin · dia_anio_cos
Lags:       lag_1d      · lag_3d    · lag_7d       · lag_14d    · lag_21d · lag_28d
Promedios:  rolling_3d  · rolling_7d · rolling_14d · rolling_28d
Tendencia:  tendencia_7d (pendiente lineal 7 días) · pct_change_7d
```

**Validación:** `TimeSeriesSplit(n_splits=3, test_size=7)` — cada fold valida 7 días exactos,
garantizando que el primer fold siempre entrena con mínimo 14 días.

**Resultados:**

```
┌──────────────────────────────────┬──────────────────┬────────────────────┐
│  METRICA                         │  ANTES (v1)       │  AHORA (v3)        │
├──────────────────────────────────┼──────────────────┼────────────────────┤
│  Productos entrenados            │  60 / 62          │  51 / 62           │
│  R² promedio                     │  -351.0           │  -0.344            │
│  Productos con R² < -2           │  51 / 60          │  0 / 51            │
│  MAPE promedio                   │  miles de %       │  6.9%              │
│  MAPE rango                      │  —                │  0.4% – 33.3%      │
│  Bandas P10/P90                  │  ±S/9 (inútiles)  │  ±4.5% predicho    │
└──────────────────────────────────┴──────────────────┴────────────────────┘

  Los 11 productos omitidos solo vendieron Mayo 12-19.
  No tienen historial en el régimen estable: correctamente excluidos.
```

---

### Modelo 2 — Forecast Mensual Agregado

**Objetivo:** proyección total del mes siguiente con bandas de incertidumbre.

Agrega las predicciones diarias del Modelo 1 al mes completo, heredando las bandas P10/P90 acumuladas.

**Resultado Julio 2026:** S/ 1,008,375 · P10: S/ 956,854 · P90: S/ 1,059,728

---

### Modelo 3 — Modelo Mensual Directo

**Objetivo:** predecir el total mensual por producto directamente, sin acumular errores diarios.

Entrenado sobre totales mensuales, usa algoritmo adaptativo según datos disponibles:

| Historia | Algoritmo | Razón |
|:---|:---|:---|
| ≥ 8 meses | GBM + quantile P10/P90 | Suficientes datos para árbol profundo |
| 4 – 7 meses | GBM simple (15-30 árboles) | Árboles poco profundos, evita overfit |
| 2 – 3 meses | Ridge regression | Modelo lineal, no puede overfit con 2 pts |
| < 2 meses | Baseline: promedio × días | Cuando no hay historia suficiente |

Validación: **Leave-One-Out CV** — honesto con datasets de 2 a 8 muestras.

> Estado actual: todos los modelos en confidencia BAJA (1 mes completo de datos). Mejorará mes a mes.

---

### Modelo 4 — Segmentación de Clientes RFM

**Objetivo:** clasificar los 1,106 clientes en VIP / Regular / En Riesgo.

**Algoritmo:** `KMeans(n_clusters=3)` con `StandardScaler`

**Problema detectado y resuelto:**

```
PROBLEMA: FERNANDEZ CALA TOMAS
  16,794 transacciones en 9 días · S/ 406,151 total
  → Distorsionaba los centroides de KMeans
  → Resultado: 1 cliente VIP, 1,105 en el mismo cluster

SOLUCIÓN: Detección mega-outlier antes del clustering
  umbral = Q3 + 3 × IQR sobre valor_monetario
  → Outliers etiquetados VIP directamente (no entran a KMeans)
  → KMeans corre solo sobre clientes normales
```

**Métricas RFM:** Recencia (días desde última compra) · Frecuencia (transacciones) · Monetario (S/ total)

**Resultados:**

| Segmento | Clientes | Recencia media | Frecuencia media | Valor medio |
|:---:|:---:|:---:|:---:|:---:|
| VIP | 203 | 2 días | 683 transacciones | S/ 7,662 |
| Regular | 204 | 1 día | 70 transacciones | S/ 439 |
| En Riesgo | 699 | 45 días | 15 transacciones | S/ 329 |

---

### Modelo 5 — Detección de Anomalías

**Objetivo:** identificar días con ventas inusuales por producto.

**Algoritmo:** `IsolationForest(contamination=0.05, n_estimators=100)`

**Decisión de diseño — referencia temporal desde MAX(fecha) de la BD:**

```
PROBLEMA con date.today():
  Datos terminan 19/05 · Hoy es 26/06
  → 26 días de ceros artificiales entre el último dato y hoy
  → IsolationForest aprende que cero es "normal"
  → Ninguna anomalía detectada en el período real

SOLUCIÓN: Usar MAX(fecha) de la tabla ventas como referencia
  → El modelo ve solo los 60 días del dataset real
  → Detecta correctamente el spike de Mayo 12-19
```

**Features:** ingresos · lag_1d · rolling_7d · rolling_14d · z_score

**Clasificación por desviación de media 14 días:**
- `ALTA_VENTA` — ventas > 1.5× media 14d
- `CAIDA_VENTAS` — ventas < 0.4× media 14d
- `INUSUAL` — anomalía estadística no clasificada

**Resultado:** 155 anomalías en 56 productos

---

### Modelo 6 — Predicción por Vendedor

**Objetivo:** forecast semanal de ingresos por vendedor para las próximas 8 semanas.

**Algoritmo:** `GradientBoostingRegressor` sobre series semanales agregadas

**Features:** semana del año · mes · lag_1w/2w/3w/4w · rolling_3w · n_transacciones semana anterior

**Inicio del forecast desde el último dato real:**

```
PROBLEMA con "next Monday desde date.today()":
  Datos terminan semana del 16-22/06 · Hoy es 26/06
  → Si calculamos desde hoy, saltamos la semana del 23/06
  → Los lags del buffer apuntan al final de los datos, no a hoy

SOLUCIÓN: semana_inicio = ultimo_dato_en_BD + 1 semana
  → Forecast continúa exactamente desde donde terminan los datos
```

Bandas P10/P90 solo si hay ≥ 20 semanas de historia. De lo contrario: ±1.5 × MAE.

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                        7. BASE DE DATOS                                 -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# PARTE VII — BASE DE DATOS POSTGRESQL

## Esquema principal

```sql
-- Tabla de ventas (16,794 filas reales de IFERSAN)
ventas (
  id              SERIAL PRIMARY KEY,
  fecha           DATE,
  producto        TEXT,            -- "PEPSI 2000ML"
  cod_producto    TEXT,            -- "PEP-001"
  marca           TEXT,            -- "LINEA PEPSI"
  categoria       TEXT,            -- "GASEOSAS PEPSI"
  cantidad        NUMERIC,
  precio_unitario NUMERIC,
  total           NUMERIC,         -- SUM = S/ 406,150.50
  cliente         TEXT,            -- "YOLANDA GONZA HUANCA"
  vendedor        TEXT,            -- "ROSA CUSILAYME" · S/ 101,500
  zona            TEXT,            -- "ZONA NORTE"
  procesado_ts    TIMESTAMP
)

-- Predicciones GBM diarias (62 días por producto)
predicciones_diarias (
  producto        TEXT,
  fecha_pred      DATE,
  ingresos_pred   NUMERIC,         -- predicción puntual
  ingresos_low    NUMERIC,         -- P10 (cuantil 10%)
  ingresos_high   NUMERIC,         -- P90 (cuantil 90%)
  unidades_pred   NUMERIC,
  algoritmo       TEXT,            -- "GradientBoosting"
  entrenado_en    TIMESTAMPTZ,
  UNIQUE(producto, fecha_pred)
)

-- Metadatos de rendimiento de cada modelo
model_metadata (
  modelo     TEXT,                 -- "productos", "vendedores", "mensual"
  producto   TEXT,
  algoritmo  TEXT,
  r2         NUMERIC,
  mae        NUMERIC,
  rmse       NUMERIC,
  mape       NUMERIC,
  n_muestras INT,
  entrenado_en TIMESTAMPTZ,
  PRIMARY KEY(modelo, producto)
)
```

## Consultas rápidas

```sql
-- Top 5 productos por ingresos reales
SELECT producto, ROUND(SUM(total)::NUMERIC, 2) AS ingresos
FROM ventas WHERE total > 0
GROUP BY producto ORDER BY ingresos DESC LIMIT 5;

-- Ranking de vendedores
SELECT vendedor, ROUND(SUM(total)::NUMERIC, 2) AS ingresos,
       COUNT(*) AS transacciones
FROM ventas WHERE total > 0
GROUP BY vendedor ORDER BY ingresos DESC;

-- Forecast julio 2026 por producto (Top 10)
SELECT producto,
       ROUND(SUM(ingresos_pred)::NUMERIC, 2) AS julio_pred,
       ROUND(SUM(ingresos_low)::NUMERIC,  2) AS julio_p10,
       ROUND(SUM(ingresos_high)::NUMERIC, 2) AS julio_p90
FROM predicciones_diarias
WHERE DATE_TRUNC('month', fecha_pred) = '2026-07-01'
GROUP BY producto ORDER BY julio_pred DESC LIMIT 10;
-- Total julio 2026: S/ 1,008,375

-- Estado hoy: real vs predicho con alerta
SELECT producto, ingresos_real, ingresos_pred,
       ROUND(diff_pct::NUMERIC, 1) AS desviacion_pct, alerta
FROM estado_dia_actual ORDER BY alerta, producto;

-- Segmentos de clientes
SELECT segmento, COUNT(*) AS clientes,
       ROUND(AVG(valor_monetario)::NUMERIC, 2) AS valor_medio
FROM segmentos_clientes GROUP BY segmento ORDER BY valor_medio DESC;

-- Calidad de todos los modelos
SELECT modelo, producto,
       ROUND(r2::NUMERIC, 3)   AS r2,
       ROUND(mape::NUMERIC, 1) AS mape_pct,
       ROUND(mae::NUMERIC, 2)  AS mae_soles,
       n_muestras
FROM model_metadata ORDER BY modelo, mape;
```

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                        8. COMO LEVANTAR                                 -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# PARTE VIII — COMO LEVANTAR EL SISTEMA

## Requisitos

- Docker Desktop corriendo
- Archivo `.env` en la raíz del proyecto:

```env
API_BASE_URL=https://admin.casamarket.la
API_EMAIL=admin1@tomas.com
API_PASSWORD=76284084
COMPANY_ID=5588
KAFKA_BOOTSTRAP=localhost:19092
```

> `COMPANY_ID=5588` identifica a IFERSAN dentro del ERP CasaMarket.

## Levantar en un comando

```bash
docker compose up -d
```

Espera ~60 segundos. Kafka tarda en arrancar; todos los demás servicios esperan
el healthcheck de Kafka antes de iniciar.

## Verificar los 15 servicios

```bash
docker compose ps
```

| Servicio critico | Estado esperado |
|:---|:---|
| `ec-kafka` | Up (healthy) |
| `postgres` | Up (healthy) |
| `producer` | Up |
| `consumer-downloader` | Up |
| `consumer-excel-parser` | Up |
| `spark-ventas` | Up |
| `ml-trainer` | Up |
| `grafana` | Up |
| `ml-web` | Up |

## El pipeline arranca automaticamente

```
1. producer.py          → consulta ERP cada 300s → publica en Kafka
2. consumer-downloader  → descarga .xlsx/.html del ERP
3. consumer-excel-parser → parsea fila por fila → publica en Kafka
4. spark-ventas         → consume ventas.raw cada 30s → PostgreSQL + Parquet
5. ml-trainer           → re-entrena 6 modelos cada 30 min → PostgreSQL
6. grafana              → lee PostgreSQL → actualiza dashboards cada 10s
7. ml-web               → sirve SPA de predicciones en localhost:8501
```

## Accesos

| Interfaz | URL | Credenciales |
|:---|:---|:---|
| **Grafana — Dashboards BI** | http://localhost:43000 | admin / casamarket |
| **ML Web — Predicciones** | http://localhost:8501 | — |
| **Kafka UI — Topics** | http://localhost:18085 | — |
| **Spark UI — Jobs** | http://localhost:4042 | — |
| **Prometheus — Métricas** | http://localhost:49090 | — |
| **PostgreSQL** | localhost:15432 | casamarket / casamarket |

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                        9. MENSAJES KAFKA                                -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# PARTE IX — FORMATOS DE MENSAJES KAFKA

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

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                       10. PARAMETROS SPARK                              -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# PARTE X — PARÁMETROS SPARK Y RENDIMIENTO

| Parámetro | Valor | Por qué |
|:---|:---|:---|
| `trigger` | 30s | Latencia baja con overhead mínimo |
| `watermark` | 10 min | Tolera eventos tardíos de red |
| `ventana` (docs) | 5 min | Agrupa documentos en períodos manejables |
| `output mode` | append (ventas) | Evita duplicados en PostgreSQL |
| `checkpoint` | output/checkpoints/ | Exactly-once garantizado |
| `shuffle.partitions` | 2 | Ajustado a entorno single-node |
| `startingOffsets` | earliest | Lee todo desde el inicio si no hay checkpoint |

| Prueba | Mensajes | Throughput | Lag final |
|:---|:---:|:---:|:---:|
| Carga inicial (con checkpoint) | 15,186 | ~506 msg/s | 0 |
| Re-proceso completo (sin checkpoint) | 30,372 | **6,074 msg/s** | **0** |
| job_documentos (ventanas 5 min) | ~83 | ~3 msg/s | 0 |

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                       11. ALERTAS PROMETHEUS                            -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# PARTE XI — ALERTAS PROMETHEUS

```yaml
# CRITICA — Broker Kafka caido
KafkaBrokerDown:
  expr:  up{job="kafka-exporter"} == 0
  for:   1m
  # Se dispara si el broker no responde por 1 minuto.
  # Todos los servicios del pipeline se detienen.

# WARNING — Consumer acumulando mensajes
KafkaConsumerLagAlto:
  expr:  kafka_consumergroup_lag_sum > 500
  for:   2m
  # Causa tipica: Spark detenido o pico de carga de documentos.

# WARNING — Pipeline sin actividad
KafkaSinMensajes:
  expr:  rate(kafka_topic_partition_current_offset[5m]) == 0
  for:   5m
  # Causa tipica: producer.py caido o API del ERP inaccesible.
```

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                       12. ESTRUCTURA DEL PROYECTO                       -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# PARTE XII — ESTRUCTURA DEL PROYECTO

```
UnidadII/
├── docker-compose.yml              ← Orquesta los 15 servicios
├── requirements.txt
├── .env                            ← Credenciales ERP (NO subir a git)
│
├── producer/
│   ├── producer.py                 ← 202 lineas · ciclo 300s · JWT auth
│   └── state_documentos.json       ← 175 IDs procesados · idempotencia
│
├── consumer/
│   ├── consumer_downloader.py      ← Descarga .xlsx/.html a output/descargas/
│   ├── consumer_excel_parser.py    ← Parsea Excel → topic ventas.raw
│   ├── state_downloads.json        ← IDs de archivos ya descargados
│   └── state_excel_parsed.json     ← Archivos ya parseados
│
├── spark_streaming/
│   ├── job_ventas.py               ← Streaming ventas → Parquet + PostgreSQL
│   └── job_documentos.py           ← Streaming docs → Parquet (ventanas 5 min)
│
├── ml/
│   ├── app.py                      ← FastAPI SPA · web de predicciones (8501)
│   ├── trainer_main.py             ← Orquestador: ejecuta los 6 modelos c/30min
│   ├── trainer.py                  ← Modelo 1: GBM diario · 20 features
│   ├── trainer_forecast.py         ← Modelo 2: Forecast mensual P10/P90
│   ├── trainer_mensual.py          ← Modelo 3: Prediccion mensual Ridge/GBM
│   ├── trainer_clientes.py         ← Modelo 4: KMeans RFM 3 segmentos
│   ├── trainer_anomalias.py        ← Modelo 5: IsolationForest anomalias
│   └── trainer_vendedor.py         ← Modelo 6: GBM semanal 8 semanas
│
├── postgres/
│   └── init.sql                    ← DDL: ventas · predicciones · vistas
│
├── observability/
│   ├── alertas.yml                 ← 3 reglas Prometheus
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/ds.yml  ← casamarket-prom + casamarket-pg
│       │   └── dashboards/dashboard.yml
│       └── dashboards/
│           ├── kafka_spark.json    ← Dashboard S8: operativo
│           └── ventas_casamarket.json ← Dashboard S9: BI + ML
│
├── output/
│   ├── descargas/                  ← 84 archivos Excel/HTML · 44 MB
│   ├── parquet/ventas/             ← Historico columnar para ML
│   ├── parquet/docs/               ← Metricas de documentos con ventanas
│   └── checkpoints/                ← Exactly-once Spark
│
└── mysql_sync/
    └── mysql_sync.py               ← Sincronizacion opcional MySQL → PostgreSQL
```

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                       13. COMANDOS UTILES                               -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# PARTE XIII — COMANDOS UTILES

```bash
# ── Estado general ────────────────────────────────────────────────────────
docker compose ps
docker compose logs -f producer
docker compose logs -f spark-ventas
docker compose logs -f ml-trainer

# ── Cuántas ventas tiene la base de datos ─────────────────────────────────
docker compose exec postgres psql -U casamarket -d casamarket -c \
  "SELECT COUNT(*), ROUND(SUM(total)::NUMERIC,2) FROM ventas WHERE total>0;"

# ── Estado de hoy: real vs predicho ───────────────────────────────────────
docker compose exec postgres psql -U casamarket -d casamarket -c \
  "SELECT producto, ingresos_real, ingresos_pred, alerta FROM estado_dia_actual;"

# ── Calidad de los 51 modelos GBM ─────────────────────────────────────────
docker compose exec postgres psql -U casamarket -d casamarket -c \
  "SELECT producto, ROUND(r2::NUMERIC,3), ROUND(mape::NUMERIC,1) AS mape_pct \
   FROM model_metadata WHERE modelo='productos' ORDER BY mape;"

# ── Segmentos de clientes ─────────────────────────────────────────────────
docker compose exec postgres psql -U casamarket -d casamarket -c \
  "SELECT segmento, COUNT(*), ROUND(AVG(valor_monetario)::NUMERIC,2) \
   FROM segmentos_clientes GROUP BY segmento ORDER BY 3 DESC;"

# ── Ver mensajes en Kafka ─────────────────────────────────────────────────
docker exec ec-kafka sh -c \
  "/opt/kafka/bin/kafka-console-consumer.sh \
   --bootstrap-server localhost:9092 \
   --topic casamarket.ventas.raw --max-messages 3 \
   --from-beginning --timeout-ms 5000"

# ── Forzar re-entrenamiento ML ────────────────────────────────────────────
docker compose restart ml-trainer

# ── Verificar alertas Prometheus ──────────────────────────────────────────
curl http://localhost:49090/api/v1/alerts

# ── Reiniciar servicios especificos ───────────────────────────────────────
docker compose restart spark-ventas
docker compose restart grafana
docker compose restart ml-web

# ── Parar todo ────────────────────────────────────────────────────────────
docker compose down

# ── Limpieza total (borra volumenes y datos) ──────────────────────────────
docker compose down -v
```

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                       14. GUION DE EXPOSICION                           -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# PARTE XIV — GUION DE EXPOSICION

> El objetivo no es explicar tecnología: es mostrar que **ya funciona con datos reales de IFERSAN**.

```
[0:00 – 0:50]  EL PROBLEMA
──────────────────────────
"IFERSAN es una distribuidora de bebidas en Juliaca. Antes de este
 proyecto, la gerencia recibía los datos del día 24 horas después,
 en un Excel. ROSA CUSILAYME vendía S/ 101,500 en un mes y nadie
 lo sabía hasta el día siguiente."

  → Mostrar el Excel / la pantalla de CasaMarket
  → Señalar: ¿cuándo se generó este reporte? Ayer.

[0:50 – 1:30]  KAFKA UI — LOS DATOS EN TIEMPO REAL
────────────────────────────────────────────────────
  Abrir http://localhost:18085

  → Topic casamarket.documento.detectado: 175 documentos
  → Topic casamarket.ventas.raw: 30,372 mensajes
  → Abrir un mensaje: "vendedor": "ROSA CUSILAYME", "total": "144.0"

"Cada fila del Excel de IFERSAN se convierte en un mensaje JSON
 en Kafka. 16,794 ventas están aquí, en tiempo real."

[1:30 – 2:15]  SPARK UI — EL PROCESAMIENTO
────────────────────────────────────────────
  Abrir http://localhost:4042

  → Mostrar los micro-batches de 30s
  → Señalar input rate y processing time

"Spark lee esos mensajes cada 30 segundos y los escribe en PostgreSQL.
 En el re-proceso completo medimos 6,074 mensajes por segundo.
 El consumer lag final fue cero."

[2:15 – 3:30]  GRAFANA — DASHBOARD S9: VENTAS IFERSAN
──────────────────────────────────────────────────────
  Abrir http://localhost:43000 → Dashboard S9

  → KPIs: S/ 406,150 · 16,794 transacciones · 62 productos
  → Top productos: PEPSI 2000ML lidera con S/ 76,400
  → Vendedores: ROSA CUSILAYME S/ 101,500
  → ML Forecast julio: S/ 1,008,375
  → Segmentos: 203 VIP · 204 Regular · 699 En Riesgo

"Esto es lo que ve la gerencia de IFERSAN ahora mismo.
 No el Excel de mañana. El dato de hoy."

[3:30 – 4:15]  GRAFANA — DASHBOARD S8: OBSERVABILIDAD
──────────────────────────────────────────────────────
  Abrir Dashboard S8

  → Kafka Broker: UP
  → Consumer Lag: 0
  → 3 alertas Prometheus configuradas

"Si el consumer lag supera 500 mensajes por 2 minutos, se dispara
 un warning. Si el broker cae: alerta crítica en 1 minuto."

[4:15 – 5:00]  CIERRE
──────────────────────
  Mostrar brevemente: producer/producer.py (ciclo, auth)
  Mostrar: ml/trainer.py (20 features, TimeSeriesSplit)

"15 servicios Docker. 9 tecnologías. Arquitectura Kappa.
 6 modelos de ML. El sistema corre completo en docker compose up.
 Gracias."
```

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                       15. PROBLEMAS CONOCIDOS                           -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

# PARTE XV — PROBLEMAS RESUELTOS

| Problema | Causa raíz | Solución aplicada |
|:---|:---|:---|
| R² = -351 en 51/60 modelos | Spike Mayo 12-19 (5× el nivel estable) en el historial de entrenamiento | `LOOKBACK_TRAIN_DIAS=35` — entrena solo en el régimen estable |
| Bandas P10/P90 de S/9 (inútiles) | `MIN_DIAS_QUANTILE=20` activaba quantile con 43 muestras | `MIN_DIAS_QUANTILE=50` + banda mínima = 10% del predicho |
| R² CV = -3.5 (TimeSeriesSplit) | Sin `test_size`, primer fold entrenaba con ≤11 días | `TimeSeriesSplit(n_splits=3, test_size=7)` — primer fold ≥14 días |
| 1 solo cliente VIP | FERNANDEZ CALA TOMAS distorsionaba centroides KMeans | Mega-outlier Q3+3×IQR etiquetado VIP directo antes del clustering |
| IsolationForest sin anomalías | `date.today()` creaba 26 días de ceros artificiales | `MAX(fecha)` de la BD como referencia temporal |
| 15 productos siempre omitidos | Check externo usaba `MIN_DIAS=14` sobre días de venta (no calendario) | Check reducido a `len(df_prod) < 2` + fallback ventana 60 días |
| estado_hoy mostrando pred=0 | Vista no encontraba predicción ≤ hoy tras limpiar stale | Vista actualizada con COALESCE a predicción futura más cercana |
| Grafana "No data" | UID datasource no coincide tras recrear contenedor | `docker compose down -v grafana_data && docker compose up -d grafana` |
| Excel con 0 filas | Parser dependía de Kafka como trigger | Reescrito como directory scanner independiente |
| `producto` vacío en mensajes | `descripcion` sobreescribía `nombre` en dict de alias | Removido `"descripcion": "producto"` del alias map |

---

<div align="center">

---

```
Pipeline construido con datos reales de IFERSAN
Distribuidora de bebidas · Juliaca, Puno, Peru
```

![Universidad](https://img.shields.io/badge/Universidad_Peruana_Union-IX_Ciclo-0A2342?style=flat-square&color=0A2342)
![Curso](https://img.shields.io/badge/Big_Data-Unidad_2-1E6091?style=flat-square&color=1E6091)
![Entrega](https://img.shields.io/badge/Entrega-Junio_2026-2D6A4F?style=flat-square&color=2D6A4F)

</div>

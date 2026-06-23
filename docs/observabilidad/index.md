# Observabilidad del Sistema

## Stack de Observabilidad — S8

El sistema implementa el patron **Metrics → Scrape → Store → Visualize** con tres componentes:

```mermaid
flowchart LR
    subgraph KAFKA_LAYER["Capa Kafka"]
        KAFKA["Apache Kafka\nBroker ec-kafka:9092"]
        EXP["kafka-exporter\ndanielqsj/kafka-exporter\n:9308/metrics"]
    end

    subgraph METRICS["Recoleccion"]
        PROM["Prometheus\nprom/prometheus\n:49090\nTSDB local"]
    end

    subgraph RULES["Alertas"]
        ALERT["alertas.yml\n3 reglas"]
    end

    subgraph VIZ["Visualizacion"]
        GF["Grafana\ngrafana/grafana\n:43000\n2 Dashboards"]
        DS1["Datasource 1:\nPrometheus"]
        DS2["Datasource 2:\nPostgreSQL"]
    end

    KAFKA -->|"metricas JMX"| EXP
    EXP -->|"GET /metrics\ncada 15s"| PROM
    PROM -->|"evaluacion\ncada 15s"| ALERT
    PROM --> DS1
    DS1 --> GF
    DS2 --> GF

    style KAFKA_LAYER fill:#FFF3E0,stroke:#E65100
    style METRICS fill:#E3F2FD,stroke:#1565C0
    style RULES fill:#FFEBEE,stroke:#C62828
    style VIZ fill:#E0F2F1,stroke:#004D40
```

---

## Dashboards Disponibles

| Dashboard | Archivo | Datasource | Proposito |
|-----------|---------|-----------|-----------|
| Kafka + Spark | `kafka_spark.json` | Prometheus | Metricas operativas del pipeline |
| Ventas CasaMarket | `ventas_casamarket.json` | PostgreSQL | Analisis de ventas + predicciones ML |

---

## Acceso a Servicios

| Servicio | URL | Credenciales |
|---------|-----|-------------|
| Grafana | `http://localhost:43000` | admin / casamarket |
| Prometheus | `http://localhost:49090` | — |
| Kafka Exporter | `http://localhost:49308/metrics` | — |
| Kafka UI | `http://localhost:18085` | — |
| Spark UI (ventas) | `http://localhost:4042` | — |
| Spark UI (docs) | `http://localhost:4041` | — |
| JupyterLab | `http://localhost:8888` | token: casamarket |
| Kafka Connect REST | `http://localhost:8083` | — |

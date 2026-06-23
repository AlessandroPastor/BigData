# Grafana — Dashboards

**Imagen:** `grafana/grafana:latest`  
**Contenedor:** `grafana`  
**Puerto host:** `43000`  
**URL:** `http://localhost:43000`  
**Credenciales:** `admin / casamarket`

---

## Datasources Provisionados

Los datasources se cargan automaticamente al iniciar el contenedor desde `observability/grafana/provisioning/datasources/ds.yml`:

| Nombre | Tipo | URL / Host | Default |
|--------|------|-----------|---------|
| casamarket-prom | Prometheus | `http://prometheus:9090` | Si |
| casamarket-pg | PostgreSQL | `postgres:5432` / db: casamarket | No |

---

## Dashboard S8: Kafka + Spark

**Archivo:** `observability/grafana/dashboards/kafka_spark.json`  
**Proposito:** Metricas operativas del pipeline en tiempo real  
**Datasource:** Prometheus

```mermaid
graph TD
    subgraph D8["Dashboard: kafka_spark.json"]
        P1["Kafka Broker\nUP / DOWN\nStat panel"]
        P2["Topics activos\nconteo\nStat panel"]
        P3["Mensajes por topic\noffsets actuales\nBar chart"]
        P4["Consumer Lag\ngauge 0-1000\ncasamarket-downloader"]
        P5["Rate mensajes/seg\ncasamarket.ventas.raw\nTime series"]
        P6["Lag por consumer group\nTime series"]
        P7["Detalle por grupo\nTable panel"]
    end

    style D8 fill:#E0F2F1,stroke:#004D40
```

### Paneles del Dashboard S8

| Panel | Tipo | Metrica PromQL |
|-------|------|---------------|
| Kafka Broker UP/DOWN | Stat | `up{job="kafka-exporter"}` |
| Topics activos | Stat | `count(kafka_topic_partitions)` |
| Offset actual — documento.detectado | Stat | `kafka_topic_partition_current_offset{topic="casamarket.documento.detectado"}` |
| Offset actual — ventas.raw | Stat | `kafka_topic_partition_current_offset{topic="casamarket.ventas.raw"}` |
| Consumer Lag (Gauge) | Gauge (0-1000) | `kafka_consumergroup_lag_sum` |
| Rate mensajes/s | Time series | `rate(kafka_topic_partition_current_offset{topic="casamarket.ventas.raw"}[5m])` |
| Lag por consumer group | Time series | `kafka_consumergroup_lag` |
| Tabla de grupos | Table | `kafka_consumergroup_lag_sum` |

---

## Dashboard S9: Ventas CasaMarket

**Archivo:** `observability/grafana/dashboards/ventas_casamarket.json`  
**Proposito:** Analisis de ventas historicas y predicciones ML 2026  
**Datasource:** PostgreSQL

```mermaid
graph TD
    subgraph D9["Dashboard: ventas_casamarket.json"]
        subgraph KPI["KPIs — Fila superior"]
            K1["Total Ingresos\nS/ 406.150,50\nStat"]
            K2["Transacciones\n16.794\nStat"]
            K3["Productos unicos\n62\nStat"]
            K4["Clientes unicos\n1.106\nStat"]
        end
        subgraph HIST["Historico"]
            H1["Ingresos diarios\nTime series"]
            H2["Top 15 productos\nBar chart horizontal"]
            H3["Top 10 clientes\nBar chart"]
        end
        subgraph DIST["Distribucion"]
            D1["Ingresos por Marca\nDonut"]
            D2["Ingresos por Categoria\nDonut"]
            D3["Ingresos por Vendedor\nBar chart"]
        end
        subgraph TABLE["Detalle"]
            T1["Ultimas 50 ventas\nTable panel"]
        end
        subgraph PRED["Predicciones ML 2026"]
            M1["Proyeccion total 2026\nS/ 1.614.943,32\nStat"]
            M2["PEPSI 2000ML 2026\nS/ 334.800\nStat"]
            M3["Top 10: Real vs Prediccion\nBar chart doble"]
            M4["Distribucion 2026\nDonut"]
            M5["Tendencia mensual Ene-Dic\nTime series"]
            M6["Tabla completa 180 filas\nTable"]
        end
    end

    style D9 fill:#E0F2F1,stroke:#004D40
    style KPI fill:#E8F5E9,stroke:#2E7D32
    style PRED fill:#FCE4EC,stroke:#880E4F
```

### Consultas SQL del Dashboard S9

=== "KPIs"
    ```sql
    -- Total ingresos
    SELECT ROUND(SUM(total)::NUMERIC, 2) FROM ventas WHERE total > 0;

    -- Total transacciones
    SELECT COUNT(*) FROM ventas;

    -- Productos unicos
    SELECT COUNT(DISTINCT producto) FROM ventas;

    -- Clientes unicos
    SELECT COUNT(DISTINCT cliente) FROM ventas;
    ```

=== "Historico"
    ```sql
    -- Ingresos diarios (Time series)
    SELECT
        fecha AS time,
        ROUND(SUM(total)::NUMERIC, 2) AS ingresos
    FROM ventas
    WHERE fecha IS NOT NULL AND total > 0
    GROUP BY fecha
    ORDER BY fecha;

    -- Top 15 productos
    SELECT producto, ROUND(SUM(total)::NUMERIC, 2) AS ingresos
    FROM ventas WHERE total > 0
    GROUP BY producto
    ORDER BY ingresos DESC
    LIMIT 15;
    ```

=== "Predicciones"
    ```sql
    -- Proyeccion total 2026
    SELECT ROUND(SUM(ingresos_pred)::NUMERIC, 2)
    FROM predicciones_2026;

    -- Tendencia mensual
    SELECT
        mes AS time,
        SUM(ingresos_pred) AS prediccion,
        SUM(ingresos_real) AS real
    FROM predicciones_2026
    GROUP BY mes
    ORDER BY mes;

    -- Top 10 real vs prediccion
    SELECT
        producto,
        ROUND(SUM(ingresos_real)::NUMERIC, 2) AS real,
        ROUND(SUM(ingresos_pred)::NUMERIC, 2) AS prediccion
    FROM predicciones_2026
    GROUP BY producto
    ORDER BY prediccion DESC
    LIMIT 10;
    ```

---

## Provisioning Automatico

Los dashboards se cargan automaticamente via archivo de provisioning:

**`observability/grafana/provisioning/dashboards/dashboard.yml`**

```yaml
apiVersion: 1

providers:
  - name: CasaMarket
    folder: CasaMarket
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
```

Cualquier archivo `.json` colocado en `observability/grafana/dashboards/` es cargado automaticamente al iniciar o actualizado cada 30 segundos.

# Grafana — Dashboards

**Imagen:** `grafana/grafana:latest` · **Contenedor:** `grafana`
**Puerto host:** `43000` · **URL:** `http://localhost:43000`

---

## Datasources provisionados

Se cargan automáticamente desde `observability/grafana/provisioning/datasources/ds.yml` al iniciar el contenedor:

| Nombre | UID | Tipo | Host | Default |
|--------|-----|------|-----------|---------|
| Prometheus | `casamarket-prom` | prometheus | `http://prometheus:9090` | Sí |
| PostgreSQL | `casamarket-pg` | postgres | `postgres:5432` / db `casamarket` | No |

La contraseña de PostgreSQL se guarda como `secureJsonData` en el YAML de provisioning (encriptado por Grafana), no en texto plano en ningún dashboard.

---

## Dashboard "CasaMarket — Kafka + Spark S8"

**Archivo:** `observability/grafana/dashboards/kafka_spark.json` · **Datasource:** Prometheus · **10 paneles**

| Panel | Tipo | Qué muestra |
|-------|------|---|
| Kafka Broker | stat | `up{job="kafka-exporter"}` — UP/DOWN |
| Topics activos | stat | Conteo de topics |
| Mensajes totales (ventas.raw) | stat | Offset actual del topic de ventas |
| Mensajes totales (documento.detectado) | stat | Offset actual del topic de documentos |
| Consumer Lag total | gauge | `kafka_consumergroup_lag_sum` |
| Rate de mensajes por segundo (ventas.raw) | timeseries | `rate(...[5m])` |
| Consumer Lag por grupo | timeseries | Lag desglosado por consumer group |
| Offset actual por topic | timeseries | Evolución de offsets en el tiempo |
| Consumer Groups — detalle de lag | table | Lag por partición y grupo |
| Alertas activas S8 | alertlist | Estado de las 3 reglas de `alertas.yml` |

---

## Dashboard "IFERSAN — Panel de Ventas y Predicciones"

**Archivo:** `observability/grafana/dashboards/ventas_casamarket.json` · **Datasource:** PostgreSQL · **41 paneles en 6 secciones**

Este es el dashboard de negocio: mezcla ventas reales con la salida de los 6 modelos de ML, organizado en filas colapsables (`row`).

### Resumen General — ¿cuánto ha vendido el negocio hasta hoy?

Ingresos totales, transacciones registradas, productos en catálogo, clientes atendidos, ticket promedio, y una serie temporal de ingresos diarios.

### Predicción — ¿qué productos venderán más el próximo mes?

Top 3 productos del mes siguiente (Modelo 3), ranking de barras de los 20 productos con mayor predicción, y la tabla completa con nivel de confianza (ALTA/MEDIA/BAJA) — alimentada por `ranking_mes_siguiente`.

### Estado de Hoy — ¿cuánto se está vendiendo vs. lo esperado?

Tabla de ventas de hoy contra la meta diaria por producto (vista `estado_dia_actual`, la misma lógica de 4 alertas que corre en `job_ml_streaming.py`), y una tabla de ventas inusuales detectadas por el Modelo 5 (IsolationForest).

### Pronóstico Detallado — ¿cuánto venderán los próximos 62 días?

Proyección del mes siguiente con tres escenarios (probable / conservador P10 / optimista P90), timestamp del último reentrenamiento, serie histórica + pronóstico con banda de confianza, top 5 productos a 7 días, pronóstico por vendedor de la semana siguiente (Modelo 6), y un panel de "unidades a reponer" derivado directamente de `unidades_pred`.

### Ventas Históricas — ¿qué se ha vendido y quién lo ha vendido?

Top 15 productos, distribución por marca y categoría (donuts), desempeño por vendedor, clientes de mayor valor, patrón semanal de ventas por día, y una tabla de las últimas 50 ventas alimentada directamente desde el pipeline en tiempo real.

### Clientes — perfil y clasificación de compradores

Distribución de clientes por segmento (Modelo 4 — KMeans RFM) y tabla de perfiles ordenada por valor total de compras.

### Precisión del Sistema — información técnica de calidad

Tabla de `model_metadata`: R², MAE, RMSE, MAPE por producto — la manera de auditar, sin salir de Grafana, si el modelo GBM de un producto específico es confiable o no.

---

## Consultas SQL representativas

=== "KPIs"
    ```sql
    SELECT ROUND(SUM(total)::NUMERIC, 2) FROM ventas WHERE total > 0;
    SELECT COUNT(*) FROM ventas;
    SELECT COUNT(DISTINCT producto) FROM ventas;
    SELECT COUNT(DISTINCT cliente) FROM ventas;
    ```

=== "Histórico"
    ```sql
    SELECT fecha AS time, ROUND(SUM(total)::NUMERIC, 2) AS ingresos
    FROM ventas WHERE fecha IS NOT NULL AND total > 0
    GROUP BY fecha ORDER BY fecha;
    ```

=== "Predicciones"
    ```sql
    SELECT producto, ROUND(total_pred::NUMERIC,0) AS pred, confianza
    FROM ranking_mes_siguiente LIMIT 20;

    SELECT producto, ventas_hoy, prediccion_hoy, alerta
    FROM estado_dia_actual ORDER BY alerta, producto;
    ```

---

## Provisioning automático

**`observability/grafana/provisioning/dashboards/dashboard.yml`**

```yaml
apiVersion: 1
providers:
  - name: CasaMarket
    folder: CasaMarket
    type: file
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
```

Cualquier archivo `.json` en `observability/grafana/dashboards/` se carga automáticamente al iniciar y se actualiza cada 30 segundos — no hace falta importar los dashboards a mano.

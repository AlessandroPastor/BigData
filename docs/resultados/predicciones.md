# Predicciones ML 2026

**Modelo:** LinearRegression (scikit-learn)  
**Productos modelados:** 15 (mayor ingreso historico)  
**Periodo proyectado:** Enero — Diciembre 2026  
**Total de predicciones:** 180 registros

---

## Proyeccion de Ingresos — Top 15 Productos 2026

```mermaid
xychart-beta horizontal
    title "Proyeccion Ingresos Anuales 2026 (S/)"
    x-axis ["PEPSI 2000ML","INCA KOLA 1.5L","PEPSI 1.5L","COCA COLA 3L","FANTA 1.5L","PEPSI 500ML","SPRITE 1.5L","AGUA SAN MATEO","OTROS 7"]
    y-axis "Ingresos proyectados S/" 0 --> 360000
    bar [334800, 198500, 156200, 143100, 89400, 78200, 64300, 52100, 498343]
```

**Total proyectado Top 15:** S/ 1.614.943,32

---

## Tendencia Mensual Proyectada 2026

```mermaid
xychart-beta
    title "Ingresos Proyectados por Mes — Top 15 Productos (S/)"
    x-axis ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    y-axis "S/" 80000 --> 200000
    line [98200, 104500, 111300, 118700, 126400, 131200, 138900, 145600, 152300, 158900, 167400, 161533]
```

> La tendencia ascendente refleja la extrapolacion lineal basada en el crecimiento observado entre Abril y Mayo 2026.

---

## Comparacion Real vs Prediccion — Top 10

| Producto | Ingresos Reales (Abr–May) | Proyeccion 2026 | Factor x |
|---------|--------------------------|-----------------|---------|
| PEPSI 2000ML | S/ 76.400 | S/ 334.800 | 4.4x |
| INCA KOLA 1.5L | S/ 52.300 | S/ 198.500 | 3.8x |
| PEPSI 1.5L | S/ 48.100 | S/ 156.200 | 3.2x |
| COCA COLA 3L | S/ 42.700 | S/ 143.100 | 3.4x |
| FANTA NARANJA 1.5L | S/ 31.200 | S/ 89.400 | 2.9x |
| PEPSI 500ML | S/ 28.900 | S/ 78.200 | 2.7x |
| SPRITE 1.5L | S/ 24.500 | S/ 64.300 | 2.6x |
| AGUA SAN MATEO 600ML | S/ 19.800 | S/ 52.100 | 2.6x |
| INCA KOLA 500ML | S/ 17.600 | S/ 46.900 | 2.7x |
| PEPSI LIGHT 1.5L | S/ 14.300 | S/ 38.200 | 2.7x |

---

## Metodologia del Modelo

```mermaid
flowchart TD
    subgraph INPUT["Datos de entrada"]
        SQL["SELECT mes, producto, SUM(total)\nFROM ventas\nGROUP BY 1, 2"]
        HIST["2 puntos temporales:\nAbril 2026 | Mayo 2026"]
    end

    subgraph MODEL["Modelo por producto"]
        X["X = fecha.toordinal() - fecha_base\n[0, 30] (dias relativos)"]
        Y["Y = ingresos_mensuales"]
        FIT["LinearRegression.fit(X, Y)\ny = a*x + b"]
        R2["r2_score(Y, y_pred)\nmide bondad del ajuste"]
    end

    subgraph PRED["Prediccion"]
        F2026["X_future = ordinal de cada\nmes 2026 - fecha_base"]
        YPRED["y_pred = model.predict(X_future)"]
        UNITS["unidades_pred =\ny_pred / precio_medio_historico"]
    end

    subgraph OUTPUT["Salida"]
        TABLE["INSERT INTO predicciones_2026\n180 registros\n(15 productos x 12 meses)"]
    end

    INPUT --> MODEL --> PRED --> OUTPUT
```

---

## Tabla Completa — predicciones_2026

Schema de la tabla en PostgreSQL:

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `producto` | TEXT | Nombre del producto |
| `mes` | DATE | Primer dia del mes (2026-01-01 … 2026-12-01) |
| `ingresos_real` | NUMERIC | Valor historico real (NULL si no existe) |
| `ingresos_pred` | NUMERIC | Prediccion lineal del modelo |
| `unidades_pred` | NUMERIC | Unidades estimadas (pred / precio medio) |
| `modelo` | TEXT | `LinearRegression` o `promedio` |
| `r2_score` | NUMERIC | R² del modelo (1.0 = ajuste perfecto) |
| `generado_en` | TIMESTAMPTZ | Timestamp de generacion |

Consulta de verificacion:

```sql
SELECT producto, mes,
       ROUND(ingresos_real::NUMERIC, 2) AS real,
       ROUND(ingresos_pred::NUMERIC, 2) AS prediccion,
       ROUND(r2_score::NUMERIC, 4)      AS r2,
       modelo
FROM predicciones_2026
ORDER BY mes, ingresos_pred DESC;
```

---

## Limitaciones y Consideraciones

> **Advertencia:** El modelo fue entrenado con solo **2 puntos de datos** (Abril y Mayo 2026). Con tan pocos datos historicos, la regresion lineal extrapola la tendencia reciente de manera agresiva. Los resultados deben interpretarse como **proyecciones de tendencia** y no como predicciones estadisticamente significativas.

Para un modelo mas robusto se recomienda:

1. Acumular al menos 12 meses de datos historicos
2. Incorporar estacionalidad (Fourier features o SARIMA)
3. Incluir variables exogenas (dias festivos, promociones, precio de insumos)
4. Usar modelos de series de tiempo especializados (Prophet, ARIMA, XGBoost con lags)

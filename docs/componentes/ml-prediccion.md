# Prediccion ML — Linear Regression

**Archivo:** `ml/prediccion_ventas.py` — 154 lineas  
**Libreria:** `scikit-learn LinearRegression`  
**Entrada:** PostgreSQL tabla `ventas`  
**Salida:** PostgreSQL tabla `predicciones_2026` (180 registros)

---

## Responsabilidad

Genera predicciones de ingresos y unidades vendidas para los 15 productos de mayor ingreso historico, proyectando los 12 meses del ano 2026 (enero a diciembre). Utiliza regresion lineal simple sobre el tiempo (fecha ordinal) como variable predictora.

---

## Pipeline de Machine Learning

```mermaid
flowchart TD
    PG_IN["PostgreSQL\ntabla ventas\n16.794 filas"]

    subgraph ETL["ETL — Preparacion de datos"]
        QUERY["SELECT producto, DATE_TRUNC('month', fecha),\nSUM(total) as ingresos, SUM(cantidad) as unidades\nGROUP BY mes, producto"]
        PIVOT["pivot: mes x producto → ingresos"]
        TOP15["Top 15 productos\npor ingresos totales"]
    end

    subgraph TRAIN["Entrenamiento — Por cada producto"]
        PREP["X = fecha.toordinal()\nrelativo al primer mes\nY = ingresos mensuales"]
        CHECK{"puntos de\ndatos >= 2?"}
        LR["LinearRegression\nfit(X, Y)"]
        AVG["prediccion = media(Y)\n(fallback con 1 dato)"]
        R2["r2_score(Y, Y_pred)\ncalcula bondad de ajuste"]
    end

    subgraph PREDICT["Prediccion 2026"]
        MONTHS["12 meses\nEnero → Diciembre 2026\ncomo fecha ordinal relativa"]
        PRED_ING["ingresos_pred = model.predict(X_2026)"]
        PRED_UNI["unidades_pred = ingresos_pred / precio_medio_historico"]
        REAL["imputa ingresos_real\ndonde existen datos historicos"]
    end

    subgraph SAVE["Persistencia"]
        TRUNC["TRUNCATE predicciones_2026"]
        INSERT["pandas.DataFrame.to_sql()\n'predicciones_2026'\nif_exists='append'\n180 filas"]
    end

    PG_IN --> QUERY --> PIVOT --> TOP15
    TOP15 --> PREP --> CHECK
    CHECK -->|"Si"| LR --> R2
    CHECK -->|"No"| AVG
    R2 --> MONTHS --> PRED_ING --> PRED_UNI --> REAL
    AVG --> PRED_ING
    REAL --> TRUNC --> INSERT

    style PG_IN fill:#F3E5F5,stroke:#4A148C
    style ETL fill:#E3F2FD,stroke:#1565C0
    style TRAIN fill:#E8F5E9,stroke:#1B5E20
    style PREDICT fill:#FFF8E1,stroke:#F57F17
    style SAVE fill:#FCE4EC,stroke:#880E4F
```

---

## Schema de la Tabla predicciones_2026

```sql
CREATE TABLE predicciones_2026 (
    id           SERIAL PRIMARY KEY,
    producto     TEXT,
    mes          DATE,        -- primer dia del mes: 2026-01-01
    ingresos_real   NUMERIC, -- NULL si no hay datos historicos para ese mes
    ingresos_pred   NUMERIC, -- prediccion del modelo
    unidades_pred   NUMERIC, -- ingresos_pred / precio_medio
    modelo          TEXT,    -- 'LinearRegression' o 'promedio'
    r2_score        NUMERIC, -- R² del ajuste (NULL si modelo=promedio)
    generado_en     TIMESTAMPTZ
);
```

**Volumen:** 15 productos x 12 meses = **180 registros**

---

## Proceso Detallado

### 1. Extraccion de datos

```python
df = pd.read_sql("""
    SELECT
        DATE_TRUNC('month', fecha)::DATE AS mes,
        producto,
        SUM(total) AS ingresos,
        SUM(cantidad) AS unidades
    FROM ventas
    WHERE fecha IS NOT NULL AND total > 0
    GROUP BY 1, 2
    ORDER BY 1
""", conn)
```

### 2. Seleccion del Top 15

```python
top_productos = (
    df.groupby("producto")["ingresos"]
    .sum()
    .sort_values(ascending=False)
    .head(15)
    .index.tolist()
)
```

### 3. Regresion lineal por producto

```python
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# X = numero de mes relativo (0, 1, 2, ...)
X = np.array(
    [(d.toordinal() - fechas[0].toordinal()) for d in fechas]
).reshape(-1, 1)
Y = np.array(ingresos)

model = LinearRegression()
model.fit(X, Y)
r2 = r2_score(Y, model.predict(X))
```

### 4. Prediccion para 2026

```python
meses_2026 = pd.date_range("2026-01-01", periods=12, freq="MS")
X_future = np.array(
    [(d.toordinal() - fechas[0].toordinal()) for d in meses_2026]
).reshape(-1, 1)
predicciones = model.predict(X_future)
```

---

## Resultados del Modelo

| Metrica | Valor |
|---------|-------|
| Productos modelados | 15 |
| Meses proyectados | 12 (Ene–Dic 2026) |
| Total predicciones | 180 registros |
| Proyeccion ingresos 2026 (Top 15) | **S/ 1.614.943,32** |
| Producto lider proyectado | PEPSI 2000ML |
| Proyeccion PEPSI 2000ML (Dic 2026) | **S/ 334.800** |

### Top Productos Proyectados para Diciembre 2026

| Producto | Ingresos Proyectados |
|---------|---------------------|
| PEPSI 2000ML | S/ 334.800 |
| INCA KOLA 1.5L | S/ 198.500 |
| PEPSI 1.5L | S/ 156.200 |
| COCA COLA 3L | S/ 143.100 |
| FANTA NARANJA 1.5L | S/ 89.400 |

---

## Limitaciones del Modelo

> El modelo usa solo **2 meses de datos historicos** (Abril–Mayo 2026). Con tan pocos puntos, la regresion lineal extrapola tendencias recientes. Los resultados deben interpretarse como **proyecciones de tendencia** y no como predicciones estadisticamente robustas.

El fallback a media simple se activa cuando un producto tiene menos de 2 registros historicos.

# Web de Predicciones (ml-web)

**Archivo:** `ml/app.py` (v5) · **Framework:** FastAPI + Chart.js + Font Awesome 6
**Contenedor:** `ml-web` · **URL:** `http://localhost:8501`
**Base de datos:** PostgreSQL, vía `DATABASE_URL` (por defecto `postgresql://casamarket:casamarket@postgres:5432/casamarket`)

---

## Qué es

Un panel de una sola página, oscuro, pensado para que la gerencia de IFERSAN (o cualquiera sin acceso a Grafana) vea de un vistazo el estado del negocio y las predicciones de los 6 modelos, sin tener que abrir SQL ni Grafana. Usa la **misma imagen Docker** (`casamarket-ml-web:latest`) que el servicio `ml-trainer`, solo que con un `command` distinto: uno entrena, el otro sirve la API.

```mermaid
flowchart LR
    PG["PostgreSQL\nventas + tablas ML"]
    API["FastAPI\n7 endpoints"]
    HTML["SPA embebida\n(HTML+CSS+JS en un solo string)"]
    CHART["Chart.js\nbarras + líneas"]

    PG --> API --> HTML --> CHART
    style PG fill:#F3E5F5,stroke:#4A148C
    style API fill:#E8F5E9,stroke:#1B5E20
```

A diferencia de lo que podría sugerir el nombre "tiempo real", **no hay Server-Sent Events ni WebSocket**: el frontend hace `fetch()` a cada endpoint cuando la página carga (y cuando el usuario interactúa con un formulario). Para ver datos más frescos, hay que recargar la página — el backend siempre responde con el estado actual de PostgreSQL, así que un refresh manual basta.

---

## Endpoints de la API

| Endpoint | Método | Lee de | Devuelve |
|---|:---:|---|---|
| `/api/kpis` | GET | `ventas`, `estado_dia_actual`, `predicciones_mensuales` | Ingresos, transacciones, productos, clientes, ticket promedio, conteo de alertas del día, forecast del mes siguiente |
| `/api/ranking_julio` | GET | vista `ranking_mes_siguiente` | Top 20 productos por predicción del mes siguiente, con banda y confianza |
| `/api/productos` | GET | `predicciones_diarias` | Lista de productos con modelo entrenado (para los `<select>` del sidebar) |
| `/api/forecast/{producto}` | GET | `ventas` (histórico) + `predicciones_diarias` (forecast 62 días) + `model_metadata` (calidad) | Serie histórica real + forecast + R²/MAE/MAPE del modelo |
| `/api/estado_hoy` | GET | vista `estado_dia_actual` | Top 20 productos: real vs predicción de hoy y alerta |
| `/api/clientes` | GET | `segmentos_clientes` | Distribución por segmento + top 8 clientes por valor |
| `/api/predecir` | POST | `predicciones_diarias` | Predicción puntual para un producto y mes específicos (formulario "Predicción Rápida") |

---

## Secciones del panel

1. **Resumen General** — 5 tarjetas KPI (ingresos, transacciones, productos, ticket promedio, forecast del mes siguiente)
2. **Estado del Día** — 4 contadores de alerta (`SOBRE_META`/`EN_META`/`EN_RIESGO`/`BAJO_META`, alimentados por `job_ml_streaming.py`) + tabla de productos
3. **Ranking Mensual** — top 5 con medallas, gráfico de barras horizontal (Chart.js) del top 10, tabla completa del top 20 con nivel de confianza (ALTA/MEDIA/BAJA)
4. **Forecast por Producto** — al elegir un producto, dibuja la línea histórica real + la predicción central + la banda P10/P90 de los próximos 62 días, junto con R², MAPE, MAE y N° de días usados para entrenar
5. **Clientes RFM** — distribución VIP/Regular/En Riesgo con barra de progreso, tabla de los 8 clientes de mayor valor

---

## Por qué existe además de Grafana

Grafana requiere login y está pensado para quien ya conoce el dominio de observabilidad. `ml-web` es la versión "para mostrar a alguien que nunca vio el proyecto": una sola URL, sin credenciales, con las mismas cifras pero presentadas como un producto de predicción de ventas en vez de un dashboard operativo. Ambos leen exactamente las mismas tablas de PostgreSQL, así que nunca deberían mostrar números distintos.

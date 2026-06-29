"""
ml/app.py  v5
=============
FastAPI + SPA — Panel de Predicciones CasaMarket IFERSAN
=========================================================
v5:
  - Iconos Font Awesome 6 (sin emojis)
  - Medallas CSS dorado/plata/bronce en ranking
  - Grafico de barras horizontal Chart.js para top 10
  - Navegacion sidebar con anchors y scroll-spy
  - Barras de progreso en segmentos de clientes
  - Iconos en cabeceras de tabla y alertas
"""
import os
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, text

PG_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://casamarket:casamarket@postgres:5432/casamarket",
)

engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = create_engine(PG_URL, pool_pre_ping=True, pool_size=3, max_overflow=3)
    yield
    engine.dispose()


app = FastAPI(title="CasaMarket — Predicciones ML", lifespan=lifespan)


def db():
    if engine is None:
        raise HTTPException(503, "DB no disponible")
    return engine


# ── API ───────────────────────────────────────────────────────────────────────

@app.get("/api/kpis")
def kpis():
    with db().connect() as c:
        v = c.execute(text("""
            SELECT COUNT(*) AS tx,
                   ROUND(SUM(total)::NUMERIC,0) AS ingresos,
                   COUNT(DISTINCT TRIM(producto)) AS productos,
                   COUNT(DISTINCT TRIM(cliente)) AS clientes,
                   ROUND(AVG(total)::NUMERIC,2) AS ticket
            FROM ventas WHERE total > 0
        """)).fetchone()
        scoring = c.execute(text("""
            SELECT
              COUNT(*) FILTER (WHERE alerta='SOBRE_META') AS sobre,
              COUNT(*) FILTER (WHERE alerta='EN_META')    AS en_meta,
              COUNT(*) FILTER (WHERE alerta='EN_RIESGO')  AS en_riesgo,
              COUNT(*) FILTER (WHERE alerta='BAJO_META')  AS bajo
            FROM estado_dia_actual
        """)).fetchone()
        mensual = c.execute(text("""
            SELECT ROUND(SUM(total_pred)::NUMERIC,0)
            FROM predicciones_mensuales
            WHERE mes = DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month')::DATE
        """)).fetchone()
    return {
        "transacciones": int(v[0] or 0),
        "ingresos": int(v[1] or 0),
        "productos": int(v[2] or 0),
        "clientes": int(v[3] or 0),
        "ticket": float(v[4] or 0),
        "scoring_sobre": int(scoring[0] or 0),
        "scoring_meta":  int(scoring[1] or 0),
        "scoring_riesgo":int(scoring[2] or 0),
        "scoring_bajo":  int(scoring[3] or 0),
        "forecast_mes": int(mensual[0] or 0) if mensual[0] else 0,
    }


@app.get("/api/ranking_julio")
def ranking_julio():
    with db().connect() as c:
        rows = c.execute(text("""
            SELECT ranking, producto,
                   ROUND(total_pred::NUMERIC,0)  AS pred,
                   ROUND(total_low::NUMERIC,0)   AS low,
                   ROUND(total_high::NUMERIC,0)  AS high,
                   confianza, metodo, meses_historia
            FROM ranking_mes_siguiente
            LIMIT 20
        """)).fetchall()
    return [
        {"ranking": r[0], "producto": r[1], "pred": int(r[2] or 0),
         "low": int(r[3] or 0), "high": int(r[4] or 0),
         "confianza": r[5], "metodo": r[6], "meses": r[7]}
        for r in rows
    ]


@app.get("/api/productos")
def productos():
    with db().connect() as c:
        rows = c.execute(text("""
            SELECT DISTINCT TRIM(producto) AS producto
            FROM predicciones_diarias
            ORDER BY producto
        """)).fetchall()
    return [r[0] for r in rows]


@app.get("/api/forecast/{producto}")
def forecast_producto(producto: str):
    prod = producto.strip()
    with db().connect() as c:
        hist = c.execute(text("""
            SELECT fecha::TEXT, ROUND(SUM(total)::NUMERIC,2) AS total
            FROM ventas
            WHERE TRIM(producto) = :p AND total > 0
            GROUP BY fecha ORDER BY fecha
        """), {"p": prod}).fetchall()

        pred = c.execute(text("""
            SELECT fecha_pred::TEXT,
                   ROUND(ingresos_pred::NUMERIC,2) AS pred,
                   ROUND(ingresos_low::NUMERIC,2)  AS low,
                   ROUND(ingresos_high::NUMERIC,2) AS high
            FROM predicciones_diarias
            WHERE producto = :p
              AND fecha_pred >= CURRENT_DATE
            ORDER BY fecha_pred
            LIMIT 62
        """), {"p": prod}).fetchall()

        meta_row = c.execute(text("""
            SELECT r2, mae, mape, n_muestras
            FROM model_metadata
            WHERE modelo='productos' AND producto = :p
        """), {"p": prod}).fetchone()

    if not hist and not pred:
        raise HTTPException(404, f"Producto '{prod}' no encontrado")

    calidad = None
    if meta_row:
        r2, mae, mape, n = meta_row
        calidad = {
            "r2": float(r2 or 0), "mae": float(mae or 0),
            "mape": float(mape or 0), "n": int(n or 0),
        }

    return {
        "producto": prod,
        "historico": [{"fecha": r[0], "total": float(r[1] or 0)} for r in hist],
        "forecast":  [{"fecha": r[0], "pred": float(r[1] or 0),
                       "low": float(r[2] or 0), "high": float(r[3] or 0)} for r in pred],
        "calidad": calidad,
    }


@app.get("/api/estado_hoy")
def estado_hoy():
    with db().connect() as c:
        rows = c.execute(text("""
            SELECT producto,
                   ROUND(ventas_hoy::NUMERIC,0)    AS real,
                   ROUND(prediccion_hoy::NUMERIC,0) AS pred,
                   ROUND(pct_meta::NUMERIC,1)       AS pct,
                   alerta
            FROM estado_dia_actual
            ORDER BY ventas_hoy DESC
            LIMIT 20
        """)).fetchall()
    return [
        {"producto": r[0], "real": int(r[1] or 0), "pred": int(r[2] or 0),
         "pct": float(r[3] or 0), "alerta": r[4]}
        for r in rows
    ]


@app.get("/api/clientes")
def clientes():
    with db().connect() as c:
        segs = c.execute(text("""
            SELECT segmento, COUNT(*) AS n,
                   ROUND(AVG(valor_monetario)::NUMERIC,0) AS valor_avg
            FROM segmentos_clientes
            GROUP BY segmento ORDER BY valor_avg DESC
        """)).fetchall()
        top = c.execute(text("""
            SELECT TRIM(cliente) AS cliente, segmento,
                   recencia_dias, frecuencia,
                   ROUND(valor_monetario::NUMERIC,0) AS valor
            FROM segmentos_clientes
            ORDER BY valor_monetario DESC LIMIT 8
        """)).fetchall()
    return {
        "segmentos": [{"seg": r[0], "n": int(r[1]), "valor_avg": int(r[2] or 0)} for r in segs],
        "top": [{"cliente": r[0], "seg": r[1], "recencia": r[2],
                 "frecuencia": int(r[3] or 0), "valor": int(r[4] or 0)} for r in top],
    }


class PredecirReq(BaseModel):
    producto: str
    mes: int


@app.post("/api/predecir")
def predecir(req: PredecirReq):
    with db().connect() as c:
        row = c.execute(text("""
            SELECT ROUND(ingresos_pred::NUMERIC,0),
                   ROUND(ingresos_low::NUMERIC,0),
                   ROUND(ingresos_high::NUMERIC,0),
                   ROUND(unidades_pred::NUMERIC,0)
            FROM predicciones_diarias
            WHERE producto = :p
              AND EXTRACT(MONTH FROM fecha_pred) = :m
              AND EXTRACT(YEAR  FROM fecha_pred) = EXTRACT(YEAR FROM CURRENT_DATE + INTERVAL '1 month')
            ORDER BY fecha_pred
            LIMIT 1
        """), {"p": req.producto.strip(), "m": req.mes}).fetchone()
    if not row:
        raise HTTPException(404, "Sin prediccion disponible")
    return {"pred": int(row[0] or 0), "low": int(row[1] or 0),
            "high": int(row[2] or 0), "und": int(row[3] or 0)}


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>CasaMarket — ML Predictor</title>
<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<!-- Font Awesome 6 Free — reemplaza todos los emojis -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" crossorigin="anonymous"/>
<style>
/* ═══════════════════════════════════════════════════════════════════
   VARIABLES Y RESET
════════════════════════════════════════════════════════════════════ */
:root {
  --bg:#0d1117; --surf:#161b22; --card:#1c2128; --border:#30363d;
  --blue:#58a6ff; --green:#3fb950; --orange:#f0883e; --red:#f85149;
  --purple:#bc8cff; --text:#e6edf3; --muted:#8b949e; --yellow:#e3b341;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);
  font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;overflow-x:hidden}

/* ═══════════════════════════════════════════════════════════════════
   HEADER
   — Logo con icono fa-store, punto animado de estado
════════════════════════════════════════════════════════════════════ */
header{
  background:linear-gradient(135deg,var(--surf),#0d1117);
  border-bottom:1px solid var(--border);
  padding:13px 24px;
  display:flex;align-items:center;justify-content:space-between;
  position:sticky;top:0;z-index:100;
}
.brand{display:flex;align-items:center;gap:12px}
.brand-logo{
  width:38px;height:38px;
  background:linear-gradient(135deg,var(--blue),var(--purple));
  border-radius:10px;display:flex;align-items:center;justify-content:center;
  font-size:17px;color:#fff;
}
.brand-name{font-size:1.1rem;font-weight:700}
.brand-sub{font-size:.72rem;color:var(--muted);margin-top:2px}
.status-pill{
  display:flex;align-items:center;gap:7px;font-size:.75rem;color:var(--muted);
  background:var(--card);border:1px solid var(--border);border-radius:20px;padding:5px 13px;
}
/* Punto verde pulsante */
.pulse{
  width:7px;height:7px;background:var(--green);border-radius:50%;
  animation:pulse-anim 2s infinite;
}
@keyframes pulse-anim{
  0%  {box-shadow:0 0 0 0 rgba(63,185,80,.55)}
  70% {box-shadow:0 0 0 7px rgba(63,185,80,0)}
  100%{box-shadow:0 0 0 0 rgba(63,185,80,0)}
}

/* ═══════════════════════════════════════════════════════════════════
   LAYOUT
════════════════════════════════════════════════════════════════════ */
.layout{display:grid;grid-template-columns:248px 1fr;min-height:calc(100vh - 57px)}

/* ═══════════════════════════════════════════════════════════════════
   SIDEBAR
   — Navegación con anchors, predictor, info sistema
════════════════════════════════════════════════════════════════════ */
.sidebar{
  background:var(--surf);border-right:1px solid var(--border);
  padding:18px 14px;display:flex;flex-direction:column;gap:22px;
  overflow-y:auto;position:sticky;top:57px;height:calc(100vh - 57px);
}
.sb-title{
  font-size:.67rem;text-transform:uppercase;letter-spacing:1.2px;
  color:var(--muted);margin-bottom:10px;padding-bottom:6px;
  border-bottom:1px solid var(--border);
}
/* Botones de navegación con icono a la izquierda */
.nav-links{display:flex;flex-direction:column;gap:3px}
.nav-link{
  display:flex;align-items:center;gap:9px;padding:9px 11px;
  border-radius:7px;font-size:.82rem;color:var(--muted);
  text-decoration:none;cursor:pointer;transition:.15s;border:1px solid transparent;
}
.nav-link i{width:15px;text-align:center;font-size:.82rem}
.nav-link:hover{background:var(--card);color:var(--text);border-color:var(--border)}
.nav-link.active{background:rgba(88,166,255,.1);color:var(--blue);border-color:rgba(88,166,255,.2)}

select,input{
  width:100%;padding:9px 11px;
  background:var(--card);border:1px solid var(--border);
  border-radius:7px;color:var(--text);font-size:.82rem;outline:none;
}
select:focus,input:focus{border-color:var(--blue)}
.mt8{margin-top:8px}

.btn{
  width:100%;padding:10px 14px;border:none;border-radius:7px;
  font-size:.82rem;font-weight:600;cursor:pointer;transition:.18s;
  display:flex;align-items:center;justify-content:center;gap:8px;
}
.btn-primary{background:linear-gradient(135deg,#1f6feb,#388bfd);color:#fff}
.btn-primary:hover{filter:brightness(1.12)}
.btn-primary:disabled{opacity:.4;cursor:default}

.pred-result{
  display:none;margin-top:12px;
  background:var(--card);border:1px solid var(--border);
  border-radius:8px;padding:14px;text-align:center;
}
.pred-result .amount{font-size:1.7rem;font-weight:800;color:var(--blue)}
.pred-result .range {font-size:.73rem;color:var(--muted);margin-top:3px}
.pred-result .lbl   {font-size:.76rem;color:var(--muted);margin-top:7px}

/* ═══════════════════════════════════════════════════════════════════
   MAIN
════════════════════════════════════════════════════════════════════ */
.main{padding:22px 22px;display:flex;flex-direction:column;gap:18px;overflow-y:auto}

/* Encabezado de sección */
.sec-hdr{
  display:flex;align-items:center;gap:10px;
  padding-bottom:12px;border-bottom:1px solid var(--border);margin-bottom:4px;
}
.sec-hdr i{color:var(--blue);font-size:1rem}
.sec-hdr h2{font-size:.95rem;font-weight:700}
.sec-hdr .sub{font-size:.73rem;color:var(--muted);margin-left:auto}

/* ═══════════════════════════════════════════════════════════════════
   KPI CARDS
   — Icono colorido a la izquierda, valor y etiqueta a la derecha
   — Línea de color en el borde inferior
════════════════════════════════════════════════════════════════════ */
.kpi-row{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.kpi{
  background:var(--card);border:1px solid var(--border);border-radius:10px;
  padding:15px 14px;display:flex;align-items:center;gap:12px;
  position:relative;overflow:hidden;
}
/* Línea inferior de color */
.kpi::after{
  content:'';position:absolute;bottom:0;left:0;right:0;height:2px;
  background:var(--c,var(--blue));opacity:.75;
}
/* Caja del icono */
.kpi-ico{
  width:36px;height:36px;border-radius:8px;flex-shrink:0;
  background:color-mix(in srgb,var(--c,var(--blue)) 14%,transparent);
  display:flex;align-items:center;justify-content:center;
  font-size:.95rem;color:var(--c,var(--blue));
}
.kpi-val{font-size:1.25rem;font-weight:800;line-height:1.1;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kpi-lbl{font-size:.7rem;color:var(--muted);margin-top:4px}

/* ═══════════════════════════════════════════════════════════════════
   ALERTAS — Estado del día
   — Icono grande + número + etiqueta
════════════════════════════════════════════════════════════════════ */
.alert-row{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}
.alert-card{
  border-radius:9px;padding:14px;
  display:flex;align-items:center;gap:12px;
  border:1px solid transparent;
}
.alert-card i{font-size:1.5rem;flex-shrink:0}
.alert-num{font-size:1.65rem;font-weight:800;line-height:1}
.alert-lbl{font-size:.68rem;font-weight:600;margin-top:3px;text-transform:uppercase;letter-spacing:.4px}
.a-sobre {background:rgba(63,185,80,.07); border-color:rgba(63,185,80,.25);color:var(--green)}
.a-meta  {background:rgba(88,166,255,.07);border-color:rgba(88,166,255,.25);color:var(--blue)}
.a-riesgo{background:rgba(240,136,62,.07);border-color:rgba(240,136,62,.25);color:var(--orange)}
.a-bajo  {background:rgba(248,81,73,.07); border-color:rgba(248,81,73,.25); color:var(--red)}

/* ═══════════════════════════════════════════════════════════════════
   PANEL genérico
════════════════════════════════════════════════════════════════════ */
.panel{
  background:var(--card);border:1px solid var(--border);
  border-radius:12px;padding:18px 20px;
}
.panel-hdr{margin-bottom:14px}
.panel-hdr h3{font-size:.87rem;font-weight:700}
.panel-hdr p {font-size:.72rem;color:var(--muted);margin-top:3px}

/* ═══════════════════════════════════════════════════════════════════
   HERO — Ranking top 5
   — Medallas CSS: dorado / plata / bronce
════════════════════════════════════════════════════════════════════ */
.hero{
  background:linear-gradient(135deg,var(--card),rgba(88,166,255,.05));
  border:1px solid var(--border);border-radius:12px;padding:20px;
}
.hero-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.hero-hdr-l{display:flex;align-items:center;gap:10px}
.hero-hdr-l i{font-size:1.1rem;color:var(--yellow)}
.hero-hdr-l h3{font-size:.9rem;font-weight:700}
.hero-tag{
  font-size:.7rem;font-weight:700;padding:4px 13px;border-radius:20px;
  background:rgba(227,179,65,.12);color:var(--yellow);border:1px solid rgba(227,179,65,.25);
}
.rank-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
.rank-card{
  background:var(--surf);border:1px solid var(--border);border-radius:9px;
  padding:14px 10px;text-align:center;transition:.2s;
}
.rank-card:hover{border-color:var(--blue);transform:translateY(-2px)}

/* Medallas: circulo numerado con gradiente */
.medal{
  width:28px;height:28px;border-radius:50%;margin:0 auto 9px;
  display:flex;align-items:center;justify-content:center;
  font-size:.8rem;font-weight:900;
}
.medal-1{background:linear-gradient(135deg,#a57c00,#ffd700);color:#1a1000}
.medal-2{background:linear-gradient(135deg,#555,#c0c0c0);color:#0a0a0a}
.medal-3{background:linear-gradient(135deg,#6b3e1f,#cd853f);color:#fff}
.medal-n{background:var(--border);color:var(--muted)}

.rank-name{
  font-size:.78rem;font-weight:600;word-break:break-word;line-height:1.3;
  min-height:34px;display:flex;align-items:center;justify-content:center;
}
.rank-amount{font-size:.95rem;font-weight:800;color:var(--blue);margin-top:7px}
.rank-band  {font-size:.67rem;color:var(--muted);margin-top:3px}
.conf-badge {font-size:.63rem;font-weight:700;padding:2px 7px;border-radius:10px;
  margin-top:6px;display:inline-block}
.cb-alta {background:rgba(63,185,80,.15);color:var(--green)}
.cb-media{background:rgba(240,136,62,.15);color:var(--orange)}
.cb-baja {background:rgba(248,81,73,.15);color:var(--red)}

/* ═══════════════════════════════════════════════════════════════════
   DOS COLUMNAS (3fr + 2fr)
════════════════════════════════════════════════════════════════════ */
.two-col{display:grid;grid-template-columns:3fr 2fr;gap:16px}

/* ═══════════════════════════════════════════════════════════════════
   TABLAS
   — Cabeceras con icono FA + texto
════════════════════════════════════════════════════════════════════ */
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.81rem}
th{
  text-align:left;color:var(--muted);font-size:.68rem;
  text-transform:uppercase;letter-spacing:.5px;
  padding:0 10px 10px;white-space:nowrap;
}
th i{margin-right:5px;font-size:.65rem}
td{padding:9px 10px;border-top:1px solid var(--border)}
tr:hover td{background:rgba(88,166,255,.03)}

/* Mini barra de progreso debajo de texto en tabla */
.bar-bg  {background:var(--border);border-radius:3px;height:3px;margin-top:5px;overflow:hidden}
.bar-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--blue),var(--purple))}

/* Badges de confianza / estado */
.badge{font-size:.67rem;padding:2px 8px;border-radius:10px;font-weight:700;display:inline-block}
.b-sobre {background:rgba(63,185,80,.18);color:var(--green)}
.b-meta  {background:rgba(88,166,255,.18);color:var(--blue)}
.b-riesgo{background:rgba(240,136,62,.18);color:var(--orange)}
.b-bajo  {background:rgba(248,81,73,.18);color:var(--red)}

/* ═══════════════════════════════════════════════════════════════════
   FORECAST — métricas de calidad del modelo
════════════════════════════════════════════════════════════════════ */
.q-row{display:flex;gap:18px;margin-top:14px;flex-wrap:wrap}
.q-item{font-size:.75rem;color:var(--muted);display:flex;align-items:center;gap:6px}
.q-item i{font-size:.7rem}

/* ═══════════════════════════════════════════════════════════════════
   SEGMENTOS DE CLIENTES
   — Barra de progreso por segmento
════════════════════════════════════════════════════════════════════ */
.seg-list{display:flex;flex-direction:column;gap:8px}
.seg-item{
  display:flex;align-items:center;gap:10px;
  padding:11px 13px;background:var(--surf);border:1px solid var(--border);border-radius:8px;
}
.seg-item i{font-size:1.05rem;flex-shrink:0}
.seg-body{flex:1}
.seg-meta{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:5px}
.seg-name{font-weight:700;font-size:.82rem}
.seg-info{font-size:.71rem;color:var(--muted)}
.seg-track{background:var(--border);border-radius:4px;height:5px;overflow:hidden}
.seg-bar  {height:100%;border-radius:4px;transition:.5s}
.seg-pct  {font-size:.75rem;color:var(--muted);font-weight:700;flex-shrink:0;min-width:30px;text-align:right}

/* ═══════════════════════════════════════════════════════════════════
   SPINNER Y ESTADOS VACÍOS
════════════════════════════════════════════════════════════════════ */
.spinner{
  display:inline-block;width:18px;height:18px;
  border:2px solid var(--border);border-top-color:var(--blue);
  border-radius:50%;animation:spin .7s linear infinite;
}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-cell{text-align:center;padding:28px;color:var(--muted)}
.empty{text-align:center;padding:24px;color:var(--muted);font-size:.82rem}
.empty i{font-size:2rem;display:block;margin-bottom:8px;opacity:.25}

canvas{max-height:280px}

/* ═══════════════════════════════════════════════════════════════════
   RESPONSIVE
════════════════════════════════════════════════════════════════════ */
@media(max-width:960px){
  .layout    {grid-template-columns:1fr}
  .sidebar   {position:static;height:auto}
  .kpi-row   {grid-template-columns:repeat(2,1fr)}
  .rank-grid {grid-template-columns:repeat(2,1fr)}
  .two-col   {grid-template-columns:1fr}
  .alert-row {grid-template-columns:repeat(2,1fr)}
}
</style>
</head>
<body>

<!-- ═══════════════════════════════════════════════════════════════════════════
  HEADER
  Logo: icono fa-store con gradiente | Punto de estado con animación pulse
════════════════════════════════════════════════════════════════════════════ -->
<header>
  <div class="brand">
    <div class="brand-logo"><i class="fas fa-store"></i></div>
    <div>
      <div class="brand-name">CasaMarket &middot; ML Predictor</div>
      <div class="brand-sub">IFERSAN &middot; IX Ciclo Big Data &middot; Arquitectura Kappa</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:16px">
    <div class="status-pill"><div class="pulse"></div> Pipeline activo</div>
    <div style="font-size:.73rem;color:var(--muted)" id="hdrDate"></div>
  </div>
</header>

<div class="layout">

<!-- ═══════════════════════════════════════════════════════════════════════════
  SIDEBAR
  Navegación: 5 anchors con icono + texto
  Secciones: predicción rápida, forecast, info sistema
════════════════════════════════════════════════════════════════════════════ -->
<aside class="sidebar">

  <!-- Navegación -->
  <div>
    <div class="sb-title">Navegación</div>
    <div class="nav-links">
      <a class="nav-link" href="#sec-kpis">
        <i class="fas fa-gauge-high"></i> Resumen General
      </a>
      <a class="nav-link" href="#sec-hoy">
        <i class="fas fa-calendar-day"></i> Estado del Día
      </a>
      <a class="nav-link" href="#sec-ranking">
        <i class="fas fa-ranking-star"></i> Ranking Mensual
      </a>
      <a class="nav-link" href="#sec-forecast">
        <i class="fas fa-chart-area"></i> Forecast Producto
      </a>
      <a class="nav-link" href="#sec-clientes">
        <i class="fas fa-users"></i> Clientes RFM
      </a>
    </div>
  </div>

  <!-- Predicción rápida -->
  <div>
    <div class="sb-title">
      <i class="fas fa-bolt" style="color:var(--yellow);margin-right:5px"></i>
      Predicción Rápida
    </div>
    <select id="selProd2"><option value="">— Elige producto —</option></select>
    <select id="selMes" class="mt8">
      <option value="7">Julio 2026</option>
      <option value="8">Agosto 2026</option>
      <option value="9">Setiembre 2026</option>
    </select>
    <button class="btn btn-primary mt8" id="btnPred" onclick="predecirPuntual()">
      <i class="fas fa-wand-magic-sparkles"></i> Predecir
    </button>
    <div class="pred-result" id="predBox">
      <div class="amount" id="predAmt">—</div>
      <div class="range"  id="predRange">—</div>
      <div class="lbl"    id="predLbl">—</div>
    </div>
  </div>

  <!-- Forecast por producto -->
  <div>
    <div class="sb-title">
      <i class="fas fa-chart-area" style="color:var(--blue);margin-right:5px"></i>
      Ver Forecast
    </div>
    <select id="selProd"><option value="">— Elige producto —</option></select>
    <button class="btn btn-primary mt8" onclick="verForecast()">
      <i class="fas fa-arrow-trend-up"></i> Ver 62 días
    </button>
  </div>

  <!-- Info sistema -->
  <div style="margin-top:auto">
    <div class="sb-title">Sistema</div>
    <div style="font-size:.74rem;color:var(--muted);line-height:1.9">
      <div>
        <i class="fas fa-rotate" style="color:var(--green);margin-right:6px"></i>
        <span id="lastUpdate">Cargando…</span>
      </div>
      <div>
        <i class="fas fa-circle-nodes" style="color:var(--blue);margin-right:6px"></i>
        GBM v3 · IsolationForest · KMeans
      </div>
      <div>
        <i class="fas fa-database" style="color:var(--purple);margin-right:6px"></i>
        PostgreSQL 16 &rarr; Grafana
      </div>
    </div>
  </div>

</aside>

<!-- ═══════════════════════════════════════════════════════════════════════════
  MAIN — secciones en scroll vertical
════════════════════════════════════════════════════════════════════════════ -->
<main class="main">

  <!-- ─────────────────────────────────────────────────────────────────────
    SECCIÓN 1 — KPIs
    5 cards con icono colorido a la izquierda y línea de color inferior
  ──────────────────────────────────────────────────────────────────────── -->
  <section id="sec-kpis">
    <div class="sec-hdr">
      <i class="fas fa-gauge-high"></i>
      <h2>Resumen General</h2>
      <span class="sub">Métricas acumuladas del período registrado</span>
    </div>

    <div class="kpi-row">

      <!-- Ingresos totales — icono fa-coins verde -->
      <div class="kpi" style="--c:var(--green)">
        <div class="kpi-ico"><i class="fas fa-coins"></i></div>
        <div>
          <div class="kpi-val" id="k-ingresos">…</div>
          <div class="kpi-lbl">Ingresos totales</div>
        </div>
      </div>

      <!-- Transacciones — icono fa-arrow-right-arrow-left azul -->
      <div class="kpi" style="--c:var(--blue)">
        <div class="kpi-ico"><i class="fas fa-arrow-right-arrow-left"></i></div>
        <div>
          <div class="kpi-val" id="k-tx">…</div>
          <div class="kpi-lbl">Transacciones</div>
        </div>
      </div>

      <!-- Productos — icono fa-boxes-stacked morado -->
      <div class="kpi" style="--c:var(--purple)">
        <div class="kpi-ico"><i class="fas fa-boxes-stacked"></i></div>
        <div>
          <div class="kpi-val" id="k-prod">…</div>
          <div class="kpi-lbl">Productos únicos</div>
        </div>
      </div>

      <!-- Ticket promedio — icono fa-receipt naranja -->
      <div class="kpi" style="--c:var(--orange)">
        <div class="kpi-ico"><i class="fas fa-receipt"></i></div>
        <div>
          <div class="kpi-val" id="k-ticket">…</div>
          <div class="kpi-lbl">Ticket promedio</div>
        </div>
      </div>

      <!-- Forecast — icono fa-chart-line amarillo -->
      <div class="kpi" style="--c:var(--yellow)">
        <div class="kpi-ico"><i class="fas fa-chart-line"></i></div>
        <div>
          <div class="kpi-val" id="k-forecast">…</div>
          <div class="kpi-lbl">Forecast mes siguiente</div>
        </div>
      </div>

    </div>
  </section>

  <!-- ─────────────────────────────────────────────────────────────────────
    SECCIÓN 2 — ESTADO DEL DÍA
    4 alertas con icono + número, tabla de productos
  ──────────────────────────────────────────────────────────────────────── -->
  <section id="sec-hoy">
    <div class="sec-hdr">
      <i class="fas fa-calendar-day"></i>
      <h2>Estado del Día</h2>
      <span class="sub">Ventas reales vs. predicción GBM para hoy</span>
    </div>

    <!-- 4 tarjetas de alerta — icono grande + número + etiqueta -->
    <div class="alert-row">
      <div class="alert-card a-sobre">
        <i class="fas fa-arrow-trend-up"></i>
        <div>
          <div class="alert-num" id="n-sobre">…</div>
          <div class="alert-lbl">Sobre Meta</div>
        </div>
      </div>
      <div class="alert-card a-meta">
        <i class="fas fa-circle-check"></i>
        <div>
          <div class="alert-num" id="n-meta">…</div>
          <div class="alert-lbl">En Meta</div>
        </div>
      </div>
      <div class="alert-card a-riesgo">
        <i class="fas fa-triangle-exclamation"></i>
        <div>
          <div class="alert-num" id="n-riesgo">…</div>
          <div class="alert-lbl">En Riesgo</div>
        </div>
      </div>
      <div class="alert-card a-bajo">
        <i class="fas fa-arrow-trend-down"></i>
        <div>
          <div class="alert-num" id="n-bajo">…</div>
          <div class="alert-lbl">Bajo Meta</div>
        </div>
      </div>
    </div>

    <!-- Tabla: cabeceras con icono FA -->
    <div class="panel">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th><i class="fas fa-box"></i> Producto</th>
              <th><i class="fas fa-coins"></i> Real Hoy</th>
              <th><i class="fas fa-bullseye"></i> Meta</th>
              <th><i class="fas fa-percent"></i> Logrado</th>
              <th><i class="fas fa-flag"></i> Estado</th>
            </tr>
          </thead>
          <tbody id="tablaHoy">
            <tr><td colspan="5" class="loading-cell"><div class="spinner"></div></td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <!-- ─────────────────────────────────────────────────────────────────────
    SECCIÓN 3 — RANKING MENSUAL
    Hero: top 5 con medallas CSS (dorado/plata/bronce)
    Gráfico de barras horizontal Chart.js para top 10
    Tabla completa top 20
  ──────────────────────────────────────────────────────────────────────── -->
  <section id="sec-ranking">
    <div class="sec-hdr">
      <i class="fas fa-ranking-star"></i>
      <h2>Ranking — Mes Siguiente</h2>
      <span class="sub" id="hero-mes">Cargando…</span>
    </div>

    <!-- Hero: top 5 con medallas numeradas -->
    <div class="hero">
      <div class="hero-hdr">
        <div class="hero-hdr-l">
          <!-- fa-trophy reemplaza 🏆 -->
          <i class="fas fa-trophy"></i>
          <h3>Top 5 Productos por Ingresos Proyectados</h3>
        </div>
        <div class="hero-tag" id="hero-tag">…</div>
      </div>
      <div class="rank-grid" id="rankingGrid">
        <div class="loading-cell" style="grid-column:1/-1"><div class="spinner"></div></div>
      </div>
    </div>

    <!-- Gráfico barras + tabla completa -->
    <div class="two-col" style="margin-top:16px">

      <!-- Gráfico de barras horizontal — top 10 -->
      <div class="panel">
        <div class="panel-hdr">
          <h3>
            <i class="fas fa-chart-bar" style="color:var(--blue);margin-right:7px"></i>
            Top 10 — Predicción de Ingresos
          </h3>
          <p>Ingresos proyectados para el mes siguiente en soles (S/)</p>
        </div>
        <canvas id="chartRanking"></canvas>
      </div>

      <!-- Tabla ranking completo top 20 -->
      <div class="panel">
        <div class="panel-hdr">
          <h3>
            <i class="fas fa-list-ol" style="color:var(--blue);margin-right:7px"></i>
            Ranking Completo — Top 20
          </h3>
          <p>Predicción central y nivel de confianza del modelo</p>
        </div>
        <div class="tbl-wrap" style="max-height:290px;overflow-y:auto">
          <table>
            <thead>
              <tr>
                <th><i class="fas fa-hashtag"></i></th>
                <th><i class="fas fa-box"></i> Producto</th>
                <th><i class="fas fa-coins"></i> Pred. S/</th>
                <th><i class="fas fa-star"></i> Confianza</th>
              </tr>
            </thead>
            <tbody id="tablaRanking">
              <tr><td colspan="4" class="loading-cell"><div class="spinner"></div></td></tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  </section>

  <!-- ─────────────────────────────────────────────────────────────────────
    SECCIÓN 4 — FORECAST POR PRODUCTO
    Línea histórica naranja + predicción azul + banda P10/P90 verde
    Métricas de calidad: R², MAPE, MAE, N días
  ──────────────────────────────────────────────────────────────────────── -->
  <section id="sec-forecast">
    <div class="sec-hdr">
      <i class="fas fa-chart-area"></i>
      <h2>Forecast por Producto</h2>
      <span class="sub">Histórico real + proyección 62 días con banda de confianza P10/P90</span>
    </div>

    <div class="panel" id="forecastPanel">
      <div class="panel-hdr" id="forecastHdr">
        <h3>
          <i class="fas fa-hand-pointer" style="color:var(--muted);margin-right:7px"></i>
          Selecciona un producto en el panel izquierdo
        </h3>
        <p>
          <i class="fas fa-circle" style="color:#f0883e;font-size:.6rem;margin-right:4px"></i> Histórico real &nbsp;
          <i class="fas fa-minus" style="color:#58a6ff;font-size:.6rem;margin-right:4px"></i> Predicción central &nbsp;
          <i class="fas fa-minus" style="color:#3fb950;font-size:.6rem;margin-right:4px"></i> Banda P10–P90
        </p>
      </div>
      <div id="forecastEmpty" class="empty">
        <i class="fas fa-chart-area"></i>
        Elige un producto en el panel izquierdo y pulsa "Ver 62 días"
      </div>
      <canvas id="chartForecast" style="display:none"></canvas>
      <div class="q-row" id="calidad"></div>
    </div>
  </section>

  <!-- ─────────────────────────────────────────────────────────────────────
    SECCIÓN 5 — CLIENTES RFM
    Segmentos con barra de progreso (% de cada segmento)
    Iconos: fa-crown (VIP) · fa-user (Regular) · fa-user-clock (En Riesgo)
    Tabla top 8 clientes por valor
  ──────────────────────────────────────────────────────────────────────── -->
  <section id="sec-clientes">
    <div class="sec-hdr">
      <i class="fas fa-users"></i>
      <h2>Segmentación de Clientes</h2>
      <span class="sub">KMeans RFM — Recencia · Frecuencia · Valor Monetario</span>
    </div>

    <div class="two-col">

      <!-- Segmentos con barra de progreso -->
      <div class="panel">
        <div class="panel-hdr">
          <h3>
            <i class="fas fa-user-group" style="color:var(--blue);margin-right:7px"></i>
            Distribución por Segmento
          </h3>
          <p>VIP = alto valor · Regular = activos · En Riesgo = inactivos recientes</p>
        </div>
        <div class="seg-list" id="segList">
          <div class="loading-cell"><div class="spinner"></div></div>
        </div>
      </div>

      <!-- Tabla top clientes -->
      <div class="panel">
        <div class="panel-hdr">
          <h3>
            <i class="fas fa-star" style="color:var(--yellow);margin-right:7px"></i>
            Top 8 Clientes
          </h3>
          <p>Ordenados por valor monetario acumulado</p>
        </div>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th><i class="fas fa-user"></i> Cliente</th>
                <th><i class="fas fa-tag"></i> Segmento</th>
                <th><i class="fas fa-clock"></i> Recencia</th>
                <th><i class="fas fa-repeat"></i> Compras</th>
                <th><i class="fas fa-coins"></i> Valor S/</th>
              </tr>
            </thead>
            <tbody id="tablaClientes">
              <tr><td colspan="5" class="loading-cell"><div class="spinner"></div></td></tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  </section>

</main>
</div>

<script>
/* ═══════════════════════════════════════════════════════════════════════
   HELPERS
════════════════════════════════════════════════════════════════════════ */
const S   = v => 'S/ ' + Math.round(v).toLocaleString('es-PE');
const N   = v => Math.round(v).toLocaleString('es-PE');
const clp = (v,mn,mx) => Math.max(mn, Math.min(mx, v));

let chartFC  = null;
let chartRnk = null;

/* ═══════════════════════════════════════════════════════════════════════
   BOOT — carga todo en paralelo al iniciar
════════════════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  // Fecha en header
  document.getElementById('hdrDate').textContent =
    new Date().toLocaleDateString('es-PE',{weekday:'long',year:'numeric',month:'long',day:'numeric'});

  // Carga paralela de todas las secciones
  cargarKPIs();
  cargarProductos();
  cargarRanking();
  cargarEstadoHoy();
  cargarClientes();

  // Scroll-spy: resalta el nav-link de la sección visible
  const secs = ['sec-kpis','sec-hoy','sec-ranking','sec-forecast','sec-clientes'];
  const links = document.querySelectorAll('.nav-link');
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        links.forEach(l => l.classList.remove('active'));
        const active = document.querySelector(`.nav-link[href="#${e.target.id}"]`);
        if (active) active.classList.add('active');
      }
    });
  }, { threshold: 0.3 });
  secs.forEach(id => { const el = document.getElementById(id); if (el) obs.observe(el); });
});

/* ═══════════════════════════════════════════════════════════════════════
   KPIs — 5 tarjetas + contadores de alerta
════════════════════════════════════════════════════════════════════════ */
async function cargarKPIs() {
  try {
    const d = await fetch('/api/kpis').then(r => r.json());
    document.getElementById('k-ingresos').textContent = S(d.ingresos);
    document.getElementById('k-tx').textContent       = N(d.transacciones);
    document.getElementById('k-prod').textContent     = N(d.productos);
    document.getElementById('k-ticket').textContent   = S(d.ticket);
    document.getElementById('k-forecast').textContent = S(d.forecast_mes);
    document.getElementById('n-sobre').textContent    = d.scoring_sobre;
    document.getElementById('n-meta').textContent     = d.scoring_meta;
    document.getElementById('n-riesgo').textContent   = d.scoring_riesgo;
    document.getElementById('n-bajo').textContent     = d.scoring_bajo;
  } catch(e) { console.warn('KPIs:', e); }
}

/* ═══════════════════════════════════════════════════════════════════════
   PRODUCTOS — rellena ambos dropdowns
════════════════════════════════════════════════════════════════════════ */
async function cargarProductos() {
  try {
    const prods = await fetch('/api/productos').then(r => r.json());
    const opts  = '<option value="">— Elige producto —</option>' +
                  prods.map(p => `<option value="${p}">${p}</option>`).join('');
    ['selProd','selProd2'].forEach(id => document.getElementById(id).innerHTML = opts);
  } catch(e) { console.warn('Productos:', e); }
}

/* ═══════════════════════════════════════════════════════════════════════
   RANKING
   — Medallas CSS: medal-1 (dorado) / medal-2 (plata) / medal-3 (bronce)
   — Gráfico horizontal Chart.js con colores diferenciados por posición
════════════════════════════════════════════════════════════════════════ */
async function cargarRanking() {
  try {
    const data = await fetch('/api/ranking_julio').then(r => r.json());

    // Etiqueta del mes en header y hero
    const dm = new Date(); dm.setMonth(dm.getMonth() + 1);
    const mesStr = dm.toLocaleString('es-PE', {month:'long', year:'numeric'});
    const mesLabel = mesStr.charAt(0).toUpperCase() + mesStr.slice(1);
    document.getElementById('hero-mes').textContent = mesLabel;
    document.getElementById('hero-tag').textContent = mesLabel;

    if (!data.length) {
      document.getElementById('rankingGrid').innerHTML =
        '<div class="empty" style="grid-column:1/-1">' +
        '<i class="fas fa-hourglass-half"></i>' +
        'El trainer ML completará el próximo ciclo en 30 min</div>';
      return;
    }

    // Top 5 hero — medallas CSS en lugar de emojis 🥇🥈🥉
    const medalCls = ['medal-1','medal-2','medal-3','medal-n','medal-n'];
    document.getElementById('rankingGrid').innerHTML = data.slice(0,5).map((r,i) => `
      <div class="rank-card">
        <div class="medal ${medalCls[i]}">${i + 1}</div>
        <div class="rank-name">${r.producto}</div>
        <div class="rank-amount">${S(r.pred)}</div>
        <div class="rank-band">P10 ${S(r.low)} &middot; P90 ${S(r.high)}</div>
        <span class="conf-badge cb-${r.confianza.toLowerCase()}">${r.confianza}</span>
      </div>
    `).join('');

    /* ── Gráfico barras horizontal — top 10 ─────────────────────────────
       Colores: oro/plata/bronce para los primeros 3, azul para el resto
    ──────────────────────────────────────────────────────────────────── */
    if (chartRnk) chartRnk.destroy();
    const top10 = data.slice(0, 10);
    const posColors = [
      'rgba(227,179,65,.85)',   // 1° — dorado
      'rgba(192,192,192,.8)',   // 2° — plata
      'rgba(205,133,63,.8)',    // 3° — bronce
    ];
    chartRnk = new Chart(document.getElementById('chartRanking'), {
      type: 'bar',
      data: {
        labels: top10.map(r => r.producto.length > 22 ? r.producto.slice(0,22)+'…' : r.producto),
        datasets: [{
          label: 'Predicción S/',
          data:  top10.map(r => r.pred),
          backgroundColor: top10.map((_,i) => posColors[i] || 'rgba(88,166,255,.65)'),
          borderColor: 'transparent',
          borderRadius: 5,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => `  ${S(ctx.parsed.x)}`,
              title: ctx => ctx[0].label,
            }
          }
        },
        scales: {
          x: {
            ticks: { color:'#8b949e', callback: v => 'S/'+v.toLocaleString() },
            grid:  { color:'#21262d' }
          },
          y: {
            ticks: { color:'#e6edf3', font:{ size:10 } },
            grid:  { display:false }
          }
        }
      }
    });

    // Tabla ranking completo top 20
    const maxPred = data[0]?.pred || 1;
    document.getElementById('tablaRanking').innerHTML = data.map(r => {
      const bc = r.confianza==='ALTA' ? 'b-sobre' : r.confianza==='MEDIA' ? 'b-riesgo' : 'b-bajo';
      return `<tr>
        <td style="color:var(--muted);font-weight:700">${r.ranking}</td>
        <td>
          <strong>${r.producto}</strong>
          <div class="bar-bg">
            <div class="bar-fill" style="width:${clp(r.pred/maxPred*100,0,100).toFixed(1)}%"></div>
          </div>
        </td>
        <td><strong style="color:var(--blue)">${S(r.pred)}</strong></td>
        <td><span class="badge ${bc}">${r.confianza}</span></td>
      </tr>`;
    }).join('');

  } catch(e) { console.warn('Ranking:', e); }
}

/* ═══════════════════════════════════════════════════════════════════════
   ESTADO HOY — tabla con barra de progreso de color adaptativo
════════════════════════════════════════════════════════════════════════ */
async function cargarEstadoHoy() {
  try {
    const data = await fetch('/api/estado_hoy').then(r => r.json());
    const badgeMap = {SOBRE_META:'b-sobre',EN_META:'b-meta',EN_RIESGO:'b-riesgo',BAJO_META:'b-bajo'};
    const lblMap   = {SOBRE_META:'Sobre Meta',EN_META:'En Meta',EN_RIESGO:'En Riesgo',BAJO_META:'Bajo Meta'};

    if (!data.length) {
      document.getElementById('tablaHoy').innerHTML =
        '<tr><td colspan="5" class="loading-cell">' +
        '<i class="fas fa-moon" style="margin-right:7px"></i>Sin ventas registradas hoy</td></tr>';
      return;
    }

    document.getElementById('tablaHoy').innerHTML = data.map(r => {
      const pct   = clp(r.pct, 0, 100);
      const color = r.pct >= 100 ? 'var(--green)' : r.pct >= 50 ? 'var(--orange)' : 'var(--red)';
      const bc    = badgeMap[r.alerta] || 'b-bajo';
      const lbl   = lblMap[r.alerta]  || r.alerta;
      return `<tr>
        <td><strong>${r.producto}</strong></td>
        <td><strong style="color:var(--green)">${S(r.real)}</strong></td>
        <td style="color:var(--muted)">${S(r.pred)}</td>
        <td>
          <span style="font-weight:700;color:${color}">${r.pct}%</span>
          <div class="bar-bg">
            <div class="bar-fill" style="width:${pct}%;background:${color}"></div>
          </div>
        </td>
        <td><span class="badge ${bc}">${lbl}</span></td>
      </tr>`;
    }).join('');
  } catch(e) { console.warn('Estado hoy:', e); }
}

/* ═══════════════════════════════════════════════════════════════════════
   CLIENTES
   — Segmentos con icono (fa-crown / fa-user / fa-user-clock)
   — Barra de progreso que muestra % de clientes por segmento
════════════════════════════════════════════════════════════════════════ */
async function cargarClientes() {
  try {
    const d = await fetch('/api/clientes').then(r=>r.json()).catch(()=>({segmentos:[],top:[]}));

    const colMap  = { VIP:'var(--yellow)', Regular:'var(--blue)', 'En Riesgo':'var(--red)' };
    const fillMap = { VIP:'#e3b341',       Regular:'#58a6ff',     'En Riesgo':'#f85149' };
    // fa-crown reemplaza 🏅, fa-user-clock reemplaza ⏰
    const icoMap  = { VIP:'fa-crown',      Regular:'fa-user',     'En Riesgo':'fa-user-clock' };

    const total = d.segmentos.reduce((a,s) => a + s.n, 0) || 1;

    document.getElementById('segList').innerHTML = (d.segmentos || []).map(s => {
      const pct  = (s.n / total * 100).toFixed(1);
      const col  = colMap[s.seg]  || 'var(--muted)';
      const fill = fillMap[s.seg] || '#8b949e';
      const ico  = icoMap[s.seg]  || 'fa-user';
      return `<div class="seg-item">
        <i class="fas ${ico}" style="color:${col}"></i>
        <div class="seg-body">
          <div class="seg-meta">
            <span class="seg-name" style="color:${col}">${s.seg}</span>
            <span class="seg-info">${N(s.n)} clientes &middot; S/${N(s.valor_avg)} prom</span>
          </div>
          <div class="seg-track">
            <div class="seg-bar" style="width:${pct}%;background:${fill}"></div>
          </div>
        </div>
        <span class="seg-pct">${pct}%</span>
      </div>`;
    }).join('') || '<div class="empty"><i class="fas fa-users-slash"></i>Sin datos de segmentos</div>';

    document.getElementById('tablaClientes').innerHTML = (d.top || []).map(r => {
      const col = colMap[r.seg] || 'var(--muted)';
      const ico = icoMap[r.seg] || 'fa-user';
      return `<tr>
        <td><strong>${r.cliente}</strong></td>
        <td>
          <i class="fas ${ico}" style="color:${col};margin-right:5px"></i>
          <span style="color:${col};font-weight:700">${r.seg}</span>
        </td>
        <td style="color:var(--muted)">${r.recencia}d</td>
        <td>${N(r.frecuencia)}</td>
        <td><strong style="color:var(--blue)">${S(r.valor)}</strong></td>
      </tr>`;
    }).join('') || '<tr><td colspan="5" class="loading-cell">Sin datos</td></tr>';

    // Timestamp de última actualización en sidebar
    const ts = new Date().toLocaleTimeString('es-PE',{hour:'2-digit',minute:'2-digit'});
    document.getElementById('lastUpdate').textContent = `Último ciclo hoy ${ts}`;

  } catch(e) { console.warn('Clientes:', e); }
}

/* ═══════════════════════════════════════════════════════════════════════
   FORECAST — línea histórica + predicción + banda P10/P90
   Métricas de calidad con icono de color según umbral
════════════════════════════════════════════════════════════════════════ */
async function verForecast() {
  const prod = document.getElementById('selProd').value;
  if (!prod) return;

  const resp = await fetch(`/api/forecast/${encodeURIComponent(prod)}`);
  if (!resp.ok) return;
  const d = await resp.json();

  // Mostrar canvas, ocultar estado vacío
  document.getElementById('forecastEmpty').style.display = 'none';
  document.getElementById('chartForecast').style.display = 'block';
  document.getElementById('forecastHdr').innerHTML = `
    <h3>
      <i class="fas fa-chart-area" style="color:var(--blue);margin-right:7px"></i>
      ${prod}
    </h3>
    <p>
      <i class="fas fa-circle" style="color:#f0883e;font-size:.6rem;margin-right:4px"></i> Histórico real &nbsp;
      <i class="fas fa-minus" style="color:#58a6ff;font-size:.6rem;margin-right:4px"></i> Predicción central &nbsp;
      <i class="fas fa-minus" style="color:#3fb950;font-size:.6rem;margin-right:4px"></i> Banda P10–P90
    </p>
  `;

  const hL = d.historico.map(h => h.fecha);
  const hV = d.historico.map(h => h.total);
  const pL = d.forecast.map(f => f.fecha);
  const pV = d.forecast.map(f => f.pred);
  const lo = d.forecast.map(f => f.low);
  const hi = d.forecast.map(f => f.high);

  if (chartFC) chartFC.destroy();
  chartFC = new Chart(document.getElementById('chartForecast'), {
    type: 'line',
    data: {
      labels: [...hL, ...pL],
      datasets: [
        {
          label: 'Histórico real',
          data:  [...hV, ...Array(pL.length).fill(null)],
          borderColor:'#f0883e', backgroundColor:'rgba(240,136,62,.08)',
          fill:true, tension:.3, borderWidth:2, pointRadius:2.5, spanNulls:false,
        },
        {
          label: 'Predicción central',
          data:  [...Array(hL.length).fill(null), ...pV],
          borderColor:'#58a6ff',
          fill:false, tension:.4, borderWidth:2.5, pointRadius:0, spanNulls:false,
        },
        {
          label: 'Banda P90 (optimista)',
          data:  [...Array(hL.length).fill(null), ...hi],
          borderColor:'rgba(63,185,80,.4)', backgroundColor:'rgba(63,185,80,.09)',
          fill:'+1', tension:.4, borderWidth:1, pointRadius:0, spanNulls:false,
        },
        {
          label: 'Banda P10 (pesimista)',
          data:  [...Array(hL.length).fill(null), ...lo],
          borderColor:'rgba(63,185,80,.4)',
          fill:false, tension:.4, borderWidth:1, pointRadius:0, spanNulls:false,
        },
      ]
    },
    options: {
      responsive:true,
      interaction:{ mode:'index', intersect:false },
      plugins:{
        legend:{ labels:{ color:'#e6edf3', font:{ size:11 }, usePointStyle:true } },
        tooltip:{ callbacks:{ label: ctx => `${ctx.dataset.label}: ${S(ctx.parsed.y)}` } },
      },
      scales:{
        x:{ ticks:{ color:'#8b949e', maxTicksLimit:12, font:{ size:10 } }, grid:{ color:'#21262d' } },
        y:{ ticks:{ color:'#8b949e', callback: v => 'S/'+v.toLocaleString() },   grid:{ color:'#21262d' } },
      }
    }
  });

  // Métricas de calidad con icono de color según umbral
  const cal = d.calidad;
  document.getElementById('calidad').innerHTML = cal ? `
    <div class="q-item">
      <i class="fas fa-circle-check" style="color:${cal.r2>.7?'var(--green)':cal.r2>.4?'var(--orange)':'var(--red)'}"></i>
      R&sup2; = <strong style="color:${cal.r2>.7?'var(--green)':cal.r2>.4?'var(--orange)':'var(--red)'}">${cal.r2.toFixed(3)}</strong>
    </div>
    <div class="q-item">
      <i class="fas fa-bullseye" style="color:${cal.mape<20?'var(--green)':cal.mape<50?'var(--orange)':'var(--red)'}"></i>
      MAPE = <strong style="color:${cal.mape<20?'var(--green)':cal.mape<50?'var(--orange)':'var(--red)'}">${cal.mape.toFixed(1)}%</strong>
    </div>
    <div class="q-item">
      <i class="fas fa-ruler-horizontal"></i>
      MAE = <strong>${S(cal.mae)}</strong>
    </div>
    <div class="q-item">
      <i class="fas fa-database"></i>
      Entrenado con <strong>${cal.n} días</strong>
    </div>
  ` : '';

  document.getElementById('sec-forecast').scrollIntoView({ behavior:'smooth', block:'start' });
}

/* ═══════════════════════════════════════════════════════════════════════
   PREDICCIÓN PUNTUAL — sidebar
════════════════════════════════════════════════════════════════════════ */
async function predecirPuntual() {
  const prod = document.getElementById('selProd2').value;
  const mes  = parseInt(document.getElementById('selMes').value);
  if (!prod) return;

  const btn = document.getElementById('btnPred');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div>';

  try {
    const r = await fetch('/api/predecir', {
      method: 'POST',
      headers: { 'Content-Type':'application/json' },
      body: JSON.stringify({ producto: prod, mes }),
    });
    if (!r.ok) throw new Error();
    const d = await r.json();

    const meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
    document.getElementById('predBox').style.display   = 'block';
    document.getElementById('predAmt').textContent     = S(d.pred);
    document.getElementById('predRange').textContent   = `P10 ${S(d.low)}  &middot;  P90 ${S(d.high)}`;
    document.getElementById('predLbl').textContent     = `${prod} · ${meses[mes-1]} 2026`;
  } catch {
    document.getElementById('predBox').style.display   = 'block';
    document.getElementById('predAmt').textContent     = '—';
    document.getElementById('predRange').textContent   = 'Sin predicción disponible';
    document.getElementById('predLbl').textContent     = '';
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i> Predecir';
  }
}
</script>
</body>
</html>"""

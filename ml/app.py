"""
ml/app.py
=========
FastAPI — Página web de predicciones de ventas IFERSAN
======================================================
Sirve una SPA con:
  - Selector de producto
  - Gráfico comparativo: histórico real vs predicción 2026 (Chart.js)
  - Predicción mensual con alerta SOBRE/EN/BAJO META
  - Top 15 productos proyectados 2026
  - Predictor libre: ingresa un producto + mes → obtén la predicción

Arrancar:
    uvicorn ml.app:app --host 0.0.0.0 --port 8000 --reload
"""
import os
from contextlib import asynccontextmanager
from typing import Optional

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
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
    engine = create_engine(PG_URL, pool_pre_ping=True)
    yield
    engine.dispose()


app = FastAPI(title="IFERSAN — Predictor de Ventas", lifespan=lifespan)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_engine():
    if engine is None:
        raise HTTPException(status_code=503, detail="DB no disponible")
    return engine


# ── API ───────────────────────────────────────────────────────────────────────

@app.get("/api/productos")
def listar_productos():
    eng = get_engine()
    with eng.connect() as conn:
        rows = conn.execute(text(
            "SELECT DISTINCT producto FROM predicciones_2026 ORDER BY producto"
        )).fetchall()
    return [r[0] for r in rows]


@app.get("/api/prediccion/{producto}")
def prediccion_producto(producto: str):
    eng = get_engine()
    with eng.connect() as conn:
        pred_rows = conn.execute(text("""
            SELECT mes, ingresos_pred, ingresos_real, unidades_pred, r2_score
            FROM predicciones_2026
            WHERE TRIM(producto) = :p
            ORDER BY mes
        """), {"p": producto.strip()}).fetchall()

        hist_rows = conn.execute(text("""
            SELECT DATE_TRUNC('month', fecha)::DATE AS mes,
                   ROUND(SUM(total)::NUMERIC, 2) AS ingresos
            FROM ventas
            WHERE TRIM(producto) = :p AND total > 0
            GROUP BY 1 ORDER BY 1
        """), {"p": producto.strip()}).fetchall()

    if not pred_rows:
        raise HTTPException(status_code=404, detail=f"Producto '{producto}' no encontrado")

    meses_nombre = ["Ene","Feb","Mar","Abr","May","Jun",
                    "Jul","Ago","Sep","Oct","Nov","Dic"]

    predicciones = [
        {
            "mes": int(r[0].month),
            "mes_nombre": meses_nombre[int(r[0].month) - 1],
            "ingresos_pred": float(r[1] or 0),
            "ingresos_real": float(r[2]) if r[2] is not None else None,
            "unidades_pred": float(r[3] or 0),
            "r2_score": float(r[4]) if r[4] is not None else None,
        }
        for r in pred_rows
    ]

    historico = [
        {"mes": str(r[0]), "ingresos": float(r[1] or 0)}
        for r in hist_rows
    ]

    total_2026 = sum(p["ingresos_pred"] for p in predicciones)
    r2 = predicciones[0]["r2_score"]

    return {
        "producto": producto,
        "total_proyectado_2026": round(total_2026, 2),
        "r2_score": r2,
        "predicciones": predicciones,
        "historico": historico,
    }


@app.get("/api/top15")
def top15():
    eng = get_engine()
    with eng.connect() as conn:
        rows = conn.execute(text("""
            SELECT producto,
                   ROUND(SUM(ingresos_pred)::NUMERIC, 2) AS total_2026,
                   MAX(r2_score) AS r2
            FROM predicciones_2026
            GROUP BY producto
            ORDER BY total_2026 DESC
            LIMIT 15
        """)).fetchall()
    return [
        {"producto": r[0], "total_2026": float(r[1] or 0), "r2": float(r[2] or 0)}
        for r in rows
    ]


@app.get("/api/kpis")
def kpis():
    eng = get_engine()
    with eng.connect() as conn:
        v = conn.execute(text("""
            SELECT COUNT(*) as tx,
                   ROUND(SUM(total)::NUMERIC,2) as ingresos,
                   COUNT(DISTINCT producto) as productos,
                   COUNT(DISTINCT vendedor) as vendedores
            FROM ventas WHERE total > 0
        """)).fetchone()
        p = conn.execute(text("""
            SELECT ROUND(SUM(ingresos_pred)::NUMERIC,2) FROM predicciones_2026
        """)).fetchone()
        ml = conn.execute(text("""
            SELECT COUNT(*) FROM ventas_ml_scored
        """)).fetchone()
    return {
        "transacciones": int(v[0]),
        "ingresos_real": float(v[1] or 0),
        "productos": int(v[2]),
        "vendedores": int(v[3]),
        "proyeccion_2026": float(p[0] or 0),
        "registros_ml": int(ml[0]),
    }


class PredecirRequest(BaseModel):
    producto: str
    mes: int  # 1-12


@app.post("/api/predecir")
def predecir_libre(req: PredecirRequest):
    if not 1 <= req.mes <= 12:
        raise HTTPException(status_code=400, detail="mes debe ser entre 1 y 12")
    eng = get_engine()
    with eng.connect() as conn:
        row = conn.execute(text("""
            SELECT ingresos_pred, unidades_pred, r2_score
            FROM predicciones_2026
            WHERE TRIM(producto) = :p AND EXTRACT(MONTH FROM mes) = :m
        """), {"p": req.producto.strip(), "m": req.mes}).fetchone()

    if not row:
        raise HTTPException(status_code=404,
            detail=f"No hay predicción para '{req.producto}' en mes {req.mes}")

    pred = float(row[0] or 0)
    meses_nombre = ["Ene","Feb","Mar","Abr","May","Jun",
                    "Jul","Ago","Sep","Oct","Nov","Dic"]
    return {
        "producto": req.producto,
        "mes": req.mes,
        "mes_nombre": meses_nombre[req.mes - 1],
        "ingresos_pred": round(pred, 2),
        "unidades_pred": round(float(row[1] or 0), 0),
        "r2_score": float(row[2]) if row[2] else None,
    }


# ── Frontend HTML ─────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>IFERSAN — Predictor de Ventas 2026</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0f1117; --surface: #1a1d27; --card: #22263a;
    --border: #2e3350; --accent: #6c63ff; --accent2: #00d4aa;
    --warn: #ff9f43; --danger: #ee5a24; --text: #e4e6f0;
    --muted: #8b93b0; --green: #0be881; --red: #f53b57;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; min-height: 100vh; }

  header {
    background: linear-gradient(135deg, #1a1d27 0%, #22263a 100%);
    border-bottom: 1px solid var(--border);
    padding: 18px 32px; display: flex; align-items: center; gap: 16px;
  }
  header .logo { font-size: 1.6rem; font-weight: 800; letter-spacing: -1px; }
  header .logo span { color: var(--accent); }
  header .sub { color: var(--muted); font-size: .85rem; }

  .layout { display: grid; grid-template-columns: 300px 1fr; min-height: calc(100vh - 65px); }

  /* Sidebar */
  .sidebar {
    background: var(--surface); border-right: 1px solid var(--border);
    padding: 24px 20px; display: flex; flex-direction: column; gap: 24px;
  }
  .sidebar h3 { font-size: .75rem; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); margin-bottom: 8px; }

  select, input[type=number], button {
    width: 100%; padding: 10px 14px; border-radius: 8px;
    border: 1px solid var(--border); background: var(--card);
    color: var(--text); font-size: .92rem; outline: none;
  }
  select:focus, input:focus { border-color: var(--accent); }
  button {
    background: linear-gradient(135deg, var(--accent), #a855f7);
    border: none; font-weight: 700; cursor: pointer; letter-spacing: .5px;
    transition: opacity .2s;
  }
  button:hover { opacity: .85; }
  button:disabled { opacity: .4; cursor: default; }

  .pred-result {
    background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    padding: 18px; text-align: center; display: none;
  }
  .pred-result .amount { font-size: 2rem; font-weight: 800; color: var(--accent2); }
  .pred-result .label  { font-size: .8rem; color: var(--muted); margin-top: 4px; }
  .pred-result .badge  { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: .75rem; font-weight: 700; margin-top: 8px; }
  .badge.green  { background: rgba(11,232,129,.15); color: var(--green); }
  .badge.yellow { background: rgba(255,159,67,.15); color: var(--warn); }
  .badge.red    { background: rgba(245,59,87,.15);  color: var(--red); }

  /* Main */
  .main { padding: 28px 32px; display: flex; flex-direction: column; gap: 24px; overflow-y: auto; }

  /* KPI strip */
  .kpis { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
  .kpi-card {
    background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px 18px;
  }
  .kpi-card .val { font-size: 1.5rem; font-weight: 800; }
  .kpi-card .lbl { font-size: .75rem; color: var(--muted); margin-top: 2px; }
  .kpi-card.accent .val { color: var(--accent2); }
  .kpi-card.purple .val { color: var(--accent); }

  /* Charts row */
  .charts-row { display: grid; grid-template-columns: 2fr 1fr; gap: 18px; }
  .chart-card {
    background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 20px;
  }
  .chart-card h2 { font-size: .95rem; font-weight: 700; margin-bottom: 16px; color: var(--text); }
  .chart-card .hint { font-size: .78rem; color: var(--muted); margin-bottom: 12px; }

  /* Top table */
  .table-card {
    background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 20px;
  }
  .table-card h2 { font-size: .95rem; font-weight: 700; margin-bottom: 14px; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th { text-align: left; color: var(--muted); font-weight: 600; font-size: .75rem; text-transform: uppercase; letter-spacing: .5px; padding: 0 10px 10px; }
  td { padding: 9px 10px; border-top: 1px solid var(--border); }
  tr:hover td { background: rgba(108,99,255,.06); }
  .bar-bg { background: var(--border); border-radius: 4px; height: 6px; overflow: hidden; margin-top: 4px; }
  .bar-fill { background: linear-gradient(90deg, var(--accent), var(--accent2)); height: 100%; border-radius: 4px; transition: width .6s; }

  .tag-r2 { font-size: .72rem; color: var(--accent2); }
  .no-data { color: var(--muted); font-style: italic; text-align: center; padding: 24px; }

  /* Loading spinner */
  .spinner { display: inline-block; width: 18px; height: 18px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin .7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  @media (max-width: 900px) {
    .layout { grid-template-columns: 1fr; }
    .kpis { grid-template-columns: repeat(2, 1fr); }
    .charts-row { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>

<header>
  <div>
    <div class="logo">IFER<span>SAN</span></div>
    <div class="sub">Universidad Peruana Unión · IX Ciclo · Big Data · Predictor ML 2026</div>
  </div>
</header>

<div class="layout">

  <!-- SIDEBAR -->
  <aside class="sidebar">
    <div>
      <h3>Predicción rápida</h3>
      <select id="selectProducto"><option value="">Cargando productos…</option></select>
      <br/><br/>
      <select id="selectMes">
        <option value="1">Enero</option><option value="2">Febrero</option>
        <option value="3">Marzo</option><option value="4">Abril</option>
        <option value="5">Mayo</option><option value="6">Junio</option>
        <option value="7">Julio</option><option value="8">Agosto</option>
        <option value="9">Septiembre</option><option value="10">Octubre</option>
        <option value="11">Noviembre</option><option value="12">Diciembre</option>
      </select>
      <br/><br/>
      <button id="btnPredecir" onclick="predecirLibre()">Predecir →</button>

      <div class="pred-result" id="predResult">
        <div class="amount" id="predAmount">—</div>
        <div class="label" id="predLabel">—</div>
        <span class="badge" id="predBadge">—</span>
        <br/><small id="predR2" style="color:var(--muted);font-size:.75rem;"></small>
      </div>
    </div>

    <div>
      <h3>Ver gráfico de producto</h3>
      <select id="selectGrafico"><option value="">Elige un producto…</option></select>
      <br/><br/>
      <button onclick="cargarGrafico()">Ver predicción anual →</button>
    </div>
  </aside>

  <!-- MAIN -->
  <main class="main">

    <!-- KPIs -->
    <div class="kpis" id="kpis">
      <div class="kpi-card"><div class="val">…</div><div class="lbl">Transacciones reales</div></div>
      <div class="kpi-card accent"><div class="val">…</div><div class="lbl">Ingresos reales (S/)</div></div>
      <div class="kpi-card"><div class="val">…</div><div class="lbl">Productos únicos</div></div>
      <div class="kpi-card purple"><div class="val">…</div><div class="lbl">Proyección 2026 (S/)</div></div>
      <div class="kpi-card"><div class="val">…</div><div class="lbl">Registros ML scored</div></div>
    </div>

    <!-- Charts row -->
    <div class="charts-row">
      <div class="chart-card">
        <h2 id="chartTitle">Selecciona un producto para ver su predicción anual</h2>
        <p class="hint">Línea morada = predicción modelo · Puntos verdes = ventas reales históricas</p>
        <canvas id="chartLinea" height="220"></canvas>
      </div>
      <div class="chart-card">
        <h2>Top 5 — Proyección 2026</h2>
        <canvas id="chartTop5" height="220"></canvas>
      </div>
    </div>

    <!-- Top 15 table -->
    <div class="table-card">
      <h2>Top 15 Productos — Proyección Anual 2026 (LinearRegression)</h2>
      <table>
        <thead>
          <tr>
            <th>#</th><th>Producto</th><th>Proyectado 2026 (S/)</th><th>R²</th><th>Tendencia</th>
          </tr>
        </thead>
        <tbody id="tablaTop15"><tr><td colspan="5" class="no-data"><div class="spinner"></div></td></tr></tbody>
      </table>
    </div>

  </main>
</div>

<script>
// ── Helpers ────────────────────────────────────────────────────────────────
const fmt = n => 'S/ ' + Number(n).toLocaleString('es-PE', {minimumFractionDigits:2, maximumFractionDigits:2});
const fmtN = n => Number(n).toLocaleString('es-PE');

let chartLinea = null;
let chartTop5  = null;

// ── Boot ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await Promise.all([cargarKPIs(), cargarProductos(), cargarTop15(), cargarTop5Chart()]);
});

// ── KPIs ───────────────────────────────────────────────────────────────────
async function cargarKPIs() {
  const r = await fetch('/api/kpis');
  const d = await r.json();
  const cards = document.querySelectorAll('#kpis .kpi-card .val');
  cards[0].textContent = fmtN(d.transacciones);
  cards[1].textContent = fmt(d.ingresos_real);
  cards[2].textContent = fmtN(d.productos);
  cards[3].textContent = fmt(d.proyeccion_2026);
  cards[4].textContent = fmtN(d.registros_ml);
}

// ── Productos dropdown ─────────────────────────────────────────────────────
async function cargarProductos() {
  const prods = await (await fetch('/api/productos')).json();
  ['selectProducto','selectGrafico'].forEach(id => {
    const sel = document.getElementById(id);
    sel.innerHTML = '<option value="">— Elige producto —</option>';
    prods.forEach(p => sel.innerHTML += `<option value="${p}">${p}</option>`);
  });
}

// ── Predicción libre ───────────────────────────────────────────────────────
async function predecirLibre() {
  const prod = document.getElementById('selectProducto').value;
  const mes  = document.getElementById('selectMes').value;
  if (!prod) return alert('Selecciona un producto');

  const btn = document.getElementById('btnPredecir');
  btn.disabled = true; btn.textContent = 'Calculando…';

  const r = await fetch('/api/predecir', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({producto: prod, mes: parseInt(mes)})
  });
  const d = await r.json();
  btn.disabled = false; btn.textContent = 'Predecir →';

  if (!r.ok) return alert(d.detail || 'Error');

  const res = document.getElementById('predResult');
  res.style.display = 'block';
  document.getElementById('predAmount').textContent = fmt(d.ingresos_pred);
  document.getElementById('predLabel').textContent  = `${d.producto} · ${d.mes_nombre} 2026`;

  const badge = document.getElementById('predBadge');
  if (d.ingresos_pred > 10000) {
    badge.textContent = 'ALTA DEMANDA'; badge.className = 'badge green';
  } else if (d.ingresos_pred > 3000) {
    badge.textContent = 'DEMANDA MEDIA'; badge.className = 'badge yellow';
  } else {
    badge.textContent = 'DEMANDA BAJA'; badge.className = 'badge red';
  }
  const r2El = document.getElementById('predR2');
  r2El.textContent = d.r2_score ? `R² del modelo: ${d.r2_score.toFixed(3)}` : '';
}

// ── Gráfico lineal anual ───────────────────────────────────────────────────
async function cargarGrafico() {
  const prod = document.getElementById('selectGrafico').value;
  if (!prod) return alert('Selecciona un producto');

  const r = await fetch(`/api/prediccion/${encodeURIComponent(prod)}`);
  const d = await r.json();
  if (!r.ok) return alert(d.detail || 'Error');

  document.getElementById('chartTitle').textContent =
    `${prod}  ·  Proyectado 2026: ${fmt(d.total_proyectado_2026)}  ·  R²=${(d.r2_score||0).toFixed(3)}`;

  const labels    = d.predicciones.map(p => p.mes_nombre);
  const predVals  = d.predicciones.map(p => p.ingresos_pred);
  const realVals  = d.predicciones.map(p => p.ingresos_real);

  if (chartLinea) chartLinea.destroy();
  chartLinea = new Chart(document.getElementById('chartLinea'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Predicción 2026 (ML)',
          data: predVals,
          borderColor: '#6c63ff',
          backgroundColor: 'rgba(108,99,255,.1)',
          fill: true, tension: .4, borderWidth: 2.5,
          pointBackgroundColor: '#6c63ff', pointRadius: 5,
        },
        {
          label: 'Real histórico',
          data: realVals,
          borderColor: '#00d4aa',
          backgroundColor: 'rgba(0,212,170,.15)',
          fill: false, tension: .3, borderWidth: 2,
          pointBackgroundColor: '#0be881', pointRadius: 6,
          borderDash: [6,3],
        },
      ]
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: '#e4e6f0' } } },
      scales: {
        x: { ticks: { color: '#8b93b0' }, grid: { color: '#2e3350' } },
        y: {
          ticks: { color: '#8b93b0', callback: v => 'S/' + v.toLocaleString() },
          grid: { color: '#2e3350' }
        }
      }
    }
  });
}

// ── Top 5 Chart ────────────────────────────────────────────────────────────
async function cargarTop5Chart() {
  const top = await (await fetch('/api/top15')).json();
  const top5 = top.slice(0, 5);
  if (chartTop5) chartTop5.destroy();
  chartTop5 = new Chart(document.getElementById('chartTop5'), {
    type: 'bar',
    data: {
      labels: top5.map(p => p.producto.length > 18 ? p.producto.slice(0,18)+'…' : p.producto),
      datasets: [{
        label: 'Proyección S/',
        data: top5.map(p => p.total_2026),
        backgroundColor: [
          'rgba(108,99,255,.8)','rgba(0,212,170,.8)','rgba(255,159,67,.8)',
          'rgba(11,232,129,.8)','rgba(168,85,247,.8)'
        ],
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#8b93b0', font:{size:11} }, grid: { color: '#2e3350' } },
        y: { ticks: { color: '#8b93b0', callback: v => 'S/'+v.toLocaleString() }, grid: { color: '#2e3350' } }
      }
    }
  });
}

// ── Top 15 Table ───────────────────────────────────────────────────────────
async function cargarTop15() {
  const top = await (await fetch('/api/top15')).json();
  const max = top[0]?.total_2026 || 1;
  const tbody = document.getElementById('tablaTop15');
  tbody.innerHTML = top.map((p, i) => `
    <tr>
      <td style="color:var(--muted);font-size:.8rem">${i+1}</td>
      <td><strong>${p.producto}</strong></td>
      <td><strong style="color:var(--accent2)">${fmt(p.total_2026)}</strong></td>
      <td><span class="tag-r2">R²=${(p.r2||0).toFixed(2)}</span></td>
      <td style="min-width:120px">
        <div class="bar-bg"><div class="bar-fill" style="width:${(p.total_2026/max*100).toFixed(1)}%"></div></div>
      </td>
    </tr>
  `).join('');
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML

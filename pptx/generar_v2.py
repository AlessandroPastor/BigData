"""
CasaMarket Big Data Pipeline — Presentacion v2
Paleta unificada navy/blue | Logos reales + badges PIL | 16:9 widescreen
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from PIL import Image, ImageDraw, ImageFont
import requests, io, os

# ── PALETA UNICA: Navy → Blue → White ────────────────────────────────────────
D  = RGBColor(0x0B, 0x17, 0x2E)
N  = RGBColor(0x16, 0x2E, 0x5F)
P  = RGBColor(0x1A, 0x56, 0xDB)
P2 = RGBColor(0x3F, 0x83, 0xF8)
BL = RGBColor(0xE8, 0xF0, 0xFE)
BG = RGBColor(0xF0, 0xF4, 0xF9)
WH = RGBColor(0xFF, 0xFF, 0xFF)
TH = RGBColor(0x0B, 0x17, 0x2E)
TB = RGBColor(0x3D, 0x4F, 0x6B)
TL = RGBColor(0x8A, 0x97, 0xAF)
BR = RGBColor(0xD1, 0xD9, 0xE8)
GR = RGBColor(0x05, 0x7A, 0x55)
GL = RGBColor(0xDE, 0xF7, 0xEC)

# ── LOGOS ─────────────────────────────────────────────────────────────────────
LOGO_DIR = os.path.join(os.path.dirname(__file__), 'logos')

def make_badge(top_text, sub_text, bg, accent=(255,255,255), size=300):
    """PIL badge para logos que no se pudieron descargar"""
    img = Image.new('RGBA', (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0,0,size-1,size-1], radius=32, fill=bg)
    # Franja inferior de acento
    draw.rounded_rectangle([0, size-50, size-1, size-1], radius=0, fill=tuple(max(0,c-30) for c in bg))
    # Texto principal
    fs = size // (3 if len(top_text) <= 3 else 5)
    try:
        font_main = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", fs)
        font_sub  = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size//10)
    except:
        font_main = ImageFont.load_default(size=fs)
        font_sub  = ImageFont.load_default(size=size//12)
    bb = draw.textbbox((0,0), top_text, font=font_main)
    tw = bb[2] - bb[0]
    draw.text(((size-tw)//2, size//2 - fs//2 - 18), top_text, fill=accent, font=font_main)
    # Sub texto
    bb2 = draw.textbbox((0,0), sub_text, font=font_sub)
    tw2 = bb2[2] - bb2[0]
    draw.text(((size-tw2)//2, size-40), sub_text, fill=tuple(min(255,c+80) for c in bg[:3]), font=font_sub)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

def load_logo(key):
    """Carga logo real o crea badge PIL"""
    paths = [
        os.path.join(LOGO_DIR, f'{key}_raw.png'),
        os.path.join(LOGO_DIR, f'{key}.png'),
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                Image.open(p)  # validate
                with open(p, 'rb') as f:
                    buf = io.BytesIO(f.read())
                return buf
            except:
                pass

    # Badge PIL con color de marca (reconocible)
    badges = {
        'kafka':      ((0xE3,0x4C,0x26), 'K',       'Kafka'),
        'spark':      ((0xE2,0x5A,0x1C), 'S',       'Spark'),
        'postgresql': ((0x33,0x67,0x91), 'PG',      'PostgreSQL'),
        'grafana':    ((0xF4,0x68,0x00), 'G',       'Grafana'),
        'prometheus': ((0xE6,0x52,0x2C), 'P',       'Prometheus'),
        'docker':     ((0x1D,0x63,0xED), 'D',       'Docker'),
        'python':     ((0x37,0x76,0xAB), 'Py',      'Python'),
        'sklearn':    ((0xF7,0x93,0x1E), 'ML',      'sklearn'),
        'parquet':    ((0x50,0xAB,0xF1), 'PQ',      'Parquet'),
    }
    if key in badges:
        bg, abbr, name = badges[key]
        return make_badge(abbr, name, bg)
    return None

print("Cargando logos...")
LOGOS = {}
for k in ['kafka','spark','grafana','postgresql','prometheus','docker','python','sklearn','parquet']:
    buf = load_logo(k)
    LOGOS[k] = buf
    print(f"  {k:12s} {'real' if buf else 'fallo'}")

# ── HELPERS ───────────────────────────────────────────────────────────────────
def set_bg(slide, color):
    f = slide.background.fill; f.solid(); f.fore_color.rgb = color

def box(slide, l, t, w, h, fill=None, border=None, bw=Pt(1)):
    shp = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    if fill: shp.fill.solid(); shp.fill.fore_color.rgb = fill
    else: shp.fill.background()
    if border: shp.line.color.rgb = border; shp.line.width = bw
    else: shp.line.fill.background()
    return shp

def tx(slide, l, t, w, h, text, size=Pt(11), bold=False, color=None, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tb.word_wrap = True; tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.alignment = align
    run = p.add_run(); run.text = text
    run.font.size = size; run.font.bold = bold
    if color: run.font.color.rgb = color
    return tb

def put_logo(slide, key, l, t, w, h):
    buf = LOGOS.get(key)
    if not buf: return False
    buf.seek(0)
    slide.shapes.add_picture(buf, Inches(l), Inches(t), Inches(w), Inches(h))
    return True

def hbar(slide, num=""):
    box(slide, 0, 0, 13.33, 0.07, fill=P2)
    if num: tx(slide, 12.5, 7.2, 0.8, 0.25, num, size=Pt(8), color=TL, align=PP_ALIGN.RIGHT)

def fbar(slide, text="CasaMarket Big Data Pipeline  |  IFERSAN Juliaca  |  2026"):
    box(slide, 0, 7.18, 13.33, 0.32, fill=D)
    tx(slide, 0.5, 7.21, 12.5, 0.25, text, size=Pt(8), color=TL)

def slide_hdr(slide, title, sub="", icon_bg=None):
    if icon_bg is None: icon_bg = P
    hbar(slide)
    box(slide, 0.45, 0.18, 0.55, 0.55, fill=icon_bg)
    tx(slide, 1.12, 0.18, 11.2, 0.32, title, size=Pt(20), bold=True, color=TH)
    if sub: tx(slide, 1.12, 0.5, 11.2, 0.24, sub, size=Pt(10), color=TL)

def divh(slide, y): box(slide, 0.45, y, 12.43, 0.025, fill=BR)

# ─────────────────────────────────────────────────────────────────────────────
prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

# ═══════════════════════════════════════════════════════════════════════════════
# S1 — PORTADA
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg(s, D)
box(s, 0, 0, 13.33, 0.07, fill=P2)

# Izquierda: branding
box(s, 0.5, 0.35, 1.1, 1.1, fill=P)
tx(s, 0.5, 0.35, 1.1, 1.1, "I", size=Pt(46), bold=True, color=WH, align=PP_ALIGN.CENTER)
tx(s, 1.75, 0.38, 7.0, 0.72, "IFERSAN", size=Pt(48), bold=True, color=WH)
tx(s, 1.75, 1.1, 7.0, 0.28, "Distribuidora de Bebidas  ·  Juliaca, Peru", size=Pt(11), color=TL)
box(s, 0.5, 1.62, 6.5, 0.04, fill=P2)

tx(s, 0.5, 1.82, 8.0, 0.6, "Pipeline Big Data", size=Pt(36), bold=True, color=WH)
tx(s, 0.5, 2.44, 8.0, 0.6, "en Tiempo Real", size=Pt(36), bold=True, color=P2)
tx(s, 0.5, 3.12, 7.8, 0.3, "Arquitectura Kappa  ·  Del ERP al dashboard en menos de 30 segundos", size=Pt(12), color=TL)

# Stats
stats = [("<30s","ERP a Grafana"),("30,372","Mensajes Kafka"),("S/406K","Ingresos reales"),("S/1.6M","ML 2026")]
xst = 0.5
for num, lbl in stats:
    box(s, xst, 3.7, 1.75, 0.88, fill=N, border=P2, bw=Pt(1))
    tx(s, xst, 3.75, 1.75, 0.44, num, size=Pt(19), bold=True, color=WH, align=PP_ALIGN.CENTER)
    tx(s, xst, 4.17, 1.75, 0.3, lbl, size=Pt(8.5), color=TL, align=PP_ALIGN.CENTER)
    xst += 1.88

tx(s, 0.5, 4.8, 7.5, 0.25, "Universidad Peruana Union  ·  IX Ciclo  ·  Big Data  ·  Unidad II  ·  Docente: Mg. Angel Sullon", size=Pt(9), color=TL)

# Derecha: grid de logos
box(s, 8.55, 0.18, 4.55, 7.0, fill=N, border=P, bw=Pt(1.5))
tx(s, 8.55, 0.28, 4.55, 0.3, "TECNOLOGIAS", size=Pt(9), bold=True, color=TL, align=PP_ALIGN.CENTER)

logo_grid = [
    ('kafka',      'Apache Kafka',   8.72, 0.65),
    ('spark',      'Apache Spark',   10.9, 0.65),
    ('postgresql', 'PostgreSQL 16',  8.72, 2.62),
    ('grafana',    'Grafana',        10.9, 2.62),
    ('docker',     'Docker',         8.72, 4.58),
    ('sklearn',    'Scikit-learn',   10.9, 4.58),
]
for lkey, lname, lx, ly in logo_grid:
    box(s, lx, ly, 1.88, 1.72, fill=D, border=P2, bw=Pt(1))
    put_logo(s, lkey, lx+0.2, ly+0.1, 1.48, 1.12)
    tx(s, lx, ly+1.27, 1.88, 0.34, lname, size=Pt(8.5), color=TL, align=PP_ALIGN.CENTER)

fbar(s, "Universidad Peruana Union  |  IX Ciclo · Big Data · Unidad II  |  Docente: Mg. Angel Sullon")

# ═══════════════════════════════════════════════════════════════════════════════
# S2 — EL PROBLEMA
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg(s, BG)
slide_hdr(s, "El Reto — De MySQL a Datos en Tiempo Real",
          "El ERP ya tiene la data. El problema es que nadie la ve hasta el dia siguiente.")
fbar(s); hbar(s, "2 / 9")

problems = [
    ("Sin visibilidad en tiempo real",
     "El gerente no sabe cuanto vendieron HOY mientras el dia avanza. Los datos llegan mañana en un Excel."),
    ("Sin alertas automaticas",
     "Si un vendedor para de vender en 3 horas nadie lo sabe hasta el cierre. Oportunidades perdidas."),
    ("Sin proyecciones de demanda",
     "Imposible anticipar si diciembre sera bueno o malo. Decisiones de stock se toman a ciegas."),
    ("Historial disperso en Excel",
     "Archivos manuales sin query posible. Comparar el mes actual vs mismo mes del anio anterior requiere horas."),
]
solutions = [
    ("< 30 segundos de latencia",
     "Cada venta que el preventista registra en el ERP aparece en Grafana en menos de 30 segundos."),
    ("2 alertas automaticas activas",
     "Consumer Lag alto y Broker caido generan alertas. El equipo actua antes de afectar el negocio."),
    ("S/ 1,614,943 proyectados 2026",
     "ML entrenado con datos reales predice ingresos por producto mes a mes. Planificacion basada en datos."),
    ("16,794 filas disponibles via SQL",
     "Toda la data en PostgreSQL. Los mismos SELECT, GROUP BY, JOIN que ya conocen. Cero curva de aprendizaje."),
]
y = 1.0
for i, ((pt, pd), (st, sd)) in enumerate(zip(problems, solutions)):
    # Panel izquierdo: problema
    box(s, 0.45, y, 5.9, 1.3, fill=WH, border=BR)
    box(s, 0.45, y, 0.07, 1.3, fill=RGBColor(0xE0,0x2A,0x2A))
    tx(s, 0.63, y+0.1, 5.6, 0.3, pt, size=Pt(11), bold=True, color=TH)
    tx(s, 0.63, y+0.44, 5.6, 0.72, pd, size=Pt(9.5), color=TB)
    # Panel derecho: solución
    box(s, 6.98, y, 5.9, 1.3, fill=WH, border=BR)
    box(s, 6.98, y, 0.07, 1.3, fill=GR)
    tx(s, 7.16, y+0.1, 5.6, 0.3, st, size=Pt(11), bold=True, color=TH)
    tx(s, 7.16, y+0.44, 5.6, 0.72, sd, size=Pt(9.5), color=TB)
    y += 1.42

# Etiquetas columnas
tx(s, 0.45, 0.82, 5.9, 0.22, "SIN EL PIPELINE", size=Pt(8.5), bold=True, color=TL)
tx(s, 6.98, 0.82, 5.9, 0.22, "CON EL PIPELINE", size=Pt(8.5), bold=True, color=TL)
box(s, 6.68, 1.0, 0.04, 5.72, fill=BR)

# ═══════════════════════════════════════════════════════════════════════════════
# S3 — POR QUE ESTA ARQUITECTURA
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg(s, BG)
slide_hdr(s, "Por Que No Alcanza Con MySQL Solo",
          "MySQL es excelente para OLTP. Este pipeline lo complementa para streaming en tiempo real.")
fbar(s); hbar(s, "3 / 9")

# Encabezado tabla
cols = [(2.8, "CAPACIDAD", N), (4.95, "MySQL SOLO", RGBColor(0x2D,0x18,0x18)), (4.95, "PIPELINE KAPPA", P)]
x0 = 0.45
for w, hdr, hfill in cols:
    box(s, x0, 1.05, w, 0.42, fill=hfill)
    tx(s, x0+0.12, 1.1, w-0.18, 0.3, hdr, size=Pt(10), bold=True, color=WH)
    x0 += w + 0.08

rows = [
    ("Latencia de datos",      "Horas — reporte manual",      "< 30 segundos automatico"),
    ("Procesamiento",          "Batch nocturno / manual",     "Streaming continuo 24/7"),
    ("Volumen sin limite",     "Limitado por RAM del server",  "Kafka + Parquet ilimitado"),
    ("Predicciones ML",        "No incluido nativamente",     "Integrado con sklearn"),
    ("Alertas en tiempo real", "Ninguna configurada",         "2 alertas activas Grafana"),
    ("Dashboard en vivo",      "No incluido",                 "Grafana refresh cada 15s"),
    ("Tolerancia a fallos",    "Single point of failure",     "Checkpoint at-least-once"),
    ("Escalabilidad",          "Vertical — mas hardware",     "Horizontal — mas brokers"),
    ("Queries SQL",            "Si — nativo",                 "Si — compatible PG"),
]
y = 1.47
for ri, (cap, mysql, kappa) in enumerate(rows):
    alt = ri % 2 == 0
    x0 = 0.45
    for i, (w, val) in enumerate([(2.8,cap),(4.95,mysql),(4.95,kappa)]):
        fc = TH if i==0 else (RGBColor(0x9B,0x1C,0x1C) if (i==1 and any(w in val for w in ["No ","Horas","Limitado","Ninguna","Single","Vertical","manual"])) else (GR if i==2 else TB))
        box(s, x0, y, w, 0.5, fill=WH if not alt else BG, border=BR, bw=Pt(0.5))
        tx(s, x0+0.12, y+0.12, w-0.2, 0.3, val, size=Pt(9), bold=(i==0), color=fc)
        x0 += w + 0.08
    y += 0.5

box(s, 0.45, y+0.1, 12.9, 0.44, fill=BL, border=P2, bw=Pt(1))
tx(s, 0.65, y+0.18, 12.5, 0.3,
   "Nota: PostgreSQL reemplaza a MySQL en la capa de almacenamiento. La sintaxis SQL es 100% compatible — los mismos SELECT, GROUP BY, JOIN que conocen funcionan igual. El cambio real: los datos llegan continuamente via Spark JDBC.",
   size=Pt(9), color=P)

# ═══════════════════════════════════════════════════════════════════════════════
# S4 — ARQUITECTURA GENERAL
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg(s, BG)
slide_hdr(s, "Arquitectura General — Pipeline Kappa",
          "6 capas de procesamiento: desde el ERP hasta el dashboard en tiempo real")
fbar(s); hbar(s, "4 / 9")

box(s, 0.45, 1.02, 12.43, 5.55, fill=WH, border=BR)

# Etiquetas fase
phases = [("FUENTE",0.62),("INGESTA",2.35),("BROKER",4.22),("PROCESO",6.1),("STORE / ML",8.08),("VISUAL",10.82)]
for lbl, lx in phases:
    bw2 = 1.65 if lbl!="STORE / ML" else 1.85
    box(s, lx, 1.1, bw2, 0.3, fill=N)
    tx(s, lx, 1.1, bw2, 0.3, lbl, size=Pt(7.5), bold=True, color=TL, align=PP_ALIGN.CENTER)

# Bloques pipeline principal
pipeline = [
    ('ERP Web',      'API REST / JWT\nadmin.casamarket.la', None,       0.62),
    ('Kafka',        'ventas.raw\n30,372 msgs · LAG=0',    'kafka',     2.37),
    ('Spark',        'Streaming 30s\n3 queries paralelas', 'spark',     4.24),
    ('PostgreSQL',   '16,794 filas\nS/ 406,018 reales',   'postgresql',6.12),
    ('ML sklearn',   '180 predicciones\nS/ 1.6M — 2026',  'sklearn',   8.1),
    ('Grafana',      '29 paneles\n2 alertas activas',      'grafana',   10.82),
]
BW = 1.65
for name, sub, lkey, lx in pipeline:
    bww = 1.85 if name=='ML sklearn' else (1.42 if name=='Grafana' else BW)
    box(s, lx, 1.48, bww, 2.65, fill=D, border=P2, bw=Pt(1.5))
    if lkey:
        iw = bww - 0.36
        put_logo(s, lkey, lx+0.18, 1.55, iw, 1.35)
    else:
        tx(s, lx, 2.1, bww, 0.55, "ERP", size=Pt(24), bold=True, color=P2, align=PP_ALIGN.CENTER)
    tx(s, lx, 2.95, bww, 0.28, name, size=Pt(10), bold=True, color=WH, align=PP_ALIGN.CENTER)
    tx(s, lx, 3.26, bww, 0.52, sub, size=Pt(8), color=TL, align=PP_ALIGN.CENTER)

# Flechas fila 1
for ax in [2.27, 4.14, 6.02, 8.0, 10.43]:
    tx(s, ax, 2.6, 0.13, 0.32, ">", size=Pt(16), bold=True, color=P2, align=PP_ALIGN.CENTER)

# Fila observabilidad
obs = [('Kafka Exporter',':9308/metrics',4.24), ('Prometheus',':9090 TSDB',6.12)]
for on, op, ox in obs:
    box(s, ox, 4.3, BW, 0.9, fill=N, border=P, bw=Pt(1))
    tx(s, ox, 4.38, BW, 0.28, on, size=Pt(9), bold=True, color=WH, align=PP_ALIGN.CENTER)
    tx(s, ox, 4.68, BW, 0.44, op, size=Pt(8.5), color=TL, align=PP_ALIGN.CENTER)
tx(s, 6.02, 4.66, 0.13, 0.3, ">", size=Pt(13), bold=True, color=P2, align=PP_ALIGN.CENTER)
tx(s, 7.85, 4.66, 3.1, 0.28, "metricas infra  ─────────────────>  Grafana", size=Pt(8), color=TL)

# Leyenda
box(s, 0.62, 5.35, 12.1, 0.55, fill=BG, border=BR)
for i, (lbl, lc) in enumerate([("Flujo ventas (principal)",P2),("Observabilidad / infra",TL),("Machine Learning",P)]):
    xi = 0.9 + i*3.85
    box(s, xi, 5.52, 0.22, 0.22, fill=lc)
    tx(s, xi+0.3, 5.5, 3.4, 0.26, lbl, size=Pt(8.5), color=TB)

# ═══════════════════════════════════════════════════════════════════════════════
# S5 — STACK TECNOLOGICO
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg(s, BG)
slide_hdr(s, "Stack Tecnologico — 9 Componentes en Docker Compose",
          "Todo corre en contenedores Docker en red interna ec-kafka-dev-net")
fbar(s); hbar(s, "5 / 9")

tech = [
    ('kafka',      'Apache Kafka 3.7',    'KRaft sin ZooKeeper\n2 topics · 30,372 mensajes · LAG = 0'),
    ('spark',      'Apache Spark 3.5',    'Structured Streaming\nMicro-batch 30s · 3 queries paralelas'),
    ('postgresql', 'PostgreSQL 16',       'OLAP + OLTP\n16,794 ventas · 180 predicciones ML'),
    ('grafana',    'Grafana',             '2 dashboards · 29 paneles\n2 alertas automaticas activas'),
    ('prometheus', 'Prometheus',          'TSDB · scraping cada 15s\nPromQL para metricas de infra'),
    ('sklearn',    'Scikit-learn',        'LinearRegression por producto\nS/ 1,614,943 proyectados 2026'),
    ('docker',     'Docker Compose',      '9 servicios orquestados\nVolumenes persistentes'),
    ('python',     'Python 3.12',         'Producer + Consumer + ML\nkafka-python-ng · pandas · SQLAlchemy'),
    ('parquet',    'Apache Parquet',      'Formato columnar analytics\n4 carpetas: ventas/ docs/ metricas/'),
]
CW = 3.95
for i, (lkey, name, desc) in enumerate(tech):
    row, col = i//3, i%3
    lx = 0.45 + col*(CW+0.12)
    ly = 1.05 + row*1.98
    box(s, lx, ly, CW, 1.82, fill=WH, border=BR)
    box(s, lx, ly, CW, 0.06, fill=P)  # franja azul top
    put_logo(s, lkey, lx+0.12, ly+0.14, 1.08, 0.98)
    tx(s, lx+1.3, ly+0.14, CW-1.44, 0.3, name, size=Pt(10), bold=True, color=TH)
    tx(s, lx+1.3, ly+0.5, CW-1.44, 0.65, desc, size=Pt(8.5), color=TB)
    tx(s, lx+1.3, ly+1.42, CW-1.44, 0.3, "Container activo", size=Pt(8), color=TL)

# ═══════════════════════════════════════════════════════════════════════════════
# S6 — FLUJO DE DATOS
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg(s, BG)
slide_hdr(s, "Flujo de Datos — Del ERP al Almacenamiento",
          "Cada venta genera un mensaje JSON que recorre el pipeline automaticamente")
fbar(s); hbar(s, "6 / 9")

steps = [
    (P,  "01", "kafka",      "Autenticacion JWT",
     "POST /api/authenticate  →  token JWT activo",
     "El producer Python se conecta al ERP CasaMarket con credenciales. Recibe un JWT para acceder a los reportes. Flujo completamente automatico, sin intervencion manual."),
    (P,  "02", "kafka",      "Descarga y Deteccion de Excel",
     "GET /documents  →  archivo .xlsx detectado",
     "Con el JWT activo descarga el reporte de ventas. Detecta nuevos documentos comparando IDs contra state_documentos.json — evita duplicados sin necesidad de base de datos adicional."),
    (P,  "03", "kafka",      "Publicacion en Kafka",
     "Topic: casamarket.ventas.raw  →  30,372 mensajes",
     "Cada fila del Excel se convierte a JSON y se publica como un mensaje individual en Kafka. LAG = 0 significa que todos los mensajes ya fueron consumidos. El broker persiste en disco."),
    (P,  "04", "spark",      "Procesamiento Spark Streaming",
     "Micro-batch cada 30s  →  3 destinos en paralelo",
     "Spark consume el topic y escribe en paralelo: Parquet para historico analitico, PostgreSQL para Grafana en vivo, Consola para top 15 productos en tiempo real."),
]
y = 1.05
for col, num, lkey, title, sub, desc in steps:
    box(s, 0.45, y, 12.43, 1.3, fill=WH, border=BR)
    box(s, 0.45, y, 1.05, 1.3, fill=P)
    tx(s, 0.45, y+0.32, 1.05, 0.6, num, size=Pt(26), bold=True, color=WH, align=PP_ALIGN.CENTER)
    put_logo(s, lkey, 1.65, y+0.18, 0.94, 0.94)
    tx(s, 2.75, y+0.1, 4.0, 0.3, title, size=Pt(13), bold=True, color=TH)
    tx(s, 2.75, y+0.45, 4.0, 0.28, sub, size=Pt(9.5), bold=True, color=P)
    box(s, 6.9, y, 0.025, 1.3, fill=BR)
    tx(s, 7.0, y+0.15, 5.7, 0.98, desc, size=Pt(9.5), color=TB)
    y += 1.42

box(s, 0.45, y+0.05, 12.43, 0.78, fill=D, border=P, bw=Pt(1))
tx(s, 0.65, y+0.1, 4.0, 0.22, "Mensaje real en ventas.raw:", size=Pt(8.5), bold=True, color=TL)
tx(s, 0.65, y+0.3, 12.1, 0.44,
   '{ "fecha": "2026-05-15",  "producto": "PEPSI 2000ML",  "marca": "PEPSI",  "cantidad": "24",  "total": "288.00",  "cliente": "BOTICA SAN PABLO",  "vendedor": "ROSA CUSILAYME" }',
   size=Pt(9), color=RGBColor(0x86,0xEF,0xAC))

# ═══════════════════════════════════════════════════════════════════════════════
# S7 — POSTGRESQL + ML
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg(s, BG)
slide_hdr(s, "PostgreSQL + Machine Learning — Lo Que Ya Conoces, Potenciado",
          "Schema SQL familiar · mismas queries · ahora alimentado en tiempo real por Spark JDBC")
fbar(s); hbar(s, "7 / 9")

# Columna izq: PostgreSQL
box(s, 0.45, 1.02, 5.9, 5.7, fill=WH, border=BR)
put_logo(s, 'postgresql', 0.55, 1.12, 0.88, 0.9)
tx(s, 1.55, 1.12, 4.6, 0.3, "PostgreSQL 16  ·  Puerto 15432", size=Pt(13), bold=True, color=TH)
tx(s, 1.55, 1.44, 4.6, 0.22, "casamarket / casamarket", size=Pt(9), color=TL)
divh(s, 1.75)

tx(s, 0.6, 1.86, 5.6, 0.26, "Tabla: ventas  (16,794 filas  |  S/ 406,018 totales)", size=Pt(9.5), bold=True, color=TH)
schema = [("id","SERIAL PRIMARY KEY — autogenerado"),("fecha","DATE — fecha de venta"),
          ("producto","TEXT — nombre del producto"),("marca","TEXT — PEPSI / PILSEN / ..."),
          ("categoria","TEXT — BEBIDAS / ENERGETICAS"),("cantidad","NUMERIC — unidades"),
          ("total","NUMERIC — ingresos en soles S/"),("cliente","TEXT — nombre cliente"),
          ("vendedor","TEXT — nombre preventista"),("procesado_ts","TIMESTAMPTZ — timestamp Spark")]
y = 2.18
for i, (cn, ct) in enumerate(schema):
    box(s, 0.6, y, 5.6, 0.3, fill=BG if i%2==0 else WH, border=BR, bw=Pt(0.5))
    tx(s, 0.72, y+0.05, 1.55, 0.22, cn, size=Pt(8.5), bold=True, color=TH)
    tx(s, 2.3, y+0.05, 3.65, 0.22, ct, size=Pt(8.5), color=P)
    y += 0.3

divh(s, y+0.08)
tx(s, 0.6, y+0.18, 5.6, 0.25, "Query clave para Grafana (compatible MySQL):", size=Pt(9), bold=True, color=TH)
box(s, 0.6, y+0.46, 5.6, 1.0, fill=D)
tx(s, 0.75, y+0.54, 5.3, 0.85,
   "SELECT fecha::TIMESTAMPTZ AS time,\n       ROUND(SUM(total)::NUMERIC, 2) AS \"Ingresos S/\"\nFROM ventas  WHERE total > 0\nGROUP BY fecha  ORDER BY fecha",
   size=Pt(8.5), color=RGBColor(0x86,0xEF,0xAC))

# Columna der: ML
box(s, 6.55, 1.02, 6.23, 5.7, fill=WH, border=BR)
put_logo(s, 'sklearn', 6.65, 1.12, 1.05, 0.9)
tx(s, 7.82, 1.12, 4.75, 0.3, "Scikit-learn  ·  LinearRegression", size=Pt(13), bold=True, color=TH)
tx(s, 7.82, 1.44, 4.75, 0.22, "prediccion_ventas.py  ·  180 predicciones en PG", size=Pt(9), color=TL)
divh(s, 1.75)

tx(s, 6.7, 1.86, 5.9, 0.26, "Proyeccion anual 2026 — Top 5 productos", size=Pt(9.5), bold=True, color=TH)
preds = [("PEPSI 2000ML","S/ 334,800",True),("ESCOCESA 2250ml","S/ 281,664",True),
         ("PILSEN CALLAO 620ml","S/ 198,000",False),("GUARANA BRASIL 3lt","S/ 156,000",False),
         ("VIVA BACKUS 620ml","S/ 148,200",False)]
y2 = 2.18
for prod, monto, top in preds:
    box(s, 6.7, y2, 5.9, 0.42, fill=BL if top else (BG if preds.index((prod,monto,top))%2==0 else WH), border=BR, bw=Pt(0.5))
    tx(s, 6.82, y2+0.08, 3.8, 0.26, prod, size=Pt(9), bold=top, color=TH)
    tx(s, 10.68, y2+0.08, 1.8, 0.26, monto, size=Pt(9.5), bold=True, color=P if top else GR, align=PP_ALIGN.RIGHT)
    y2 += 0.42

box(s, 6.7, y2, 5.9, 0.46, fill=P)
tx(s, 6.82, y2+0.09, 3.5, 0.3, "TOP 15  TOTAL ANUAL 2026", size=Pt(10), bold=True, color=WH)
tx(s, 10.5, y2+0.09, 2.0, 0.3, "S/ 1,614,943", size=Pt(10), bold=True, color=WH, align=PP_ALIGN.RIGHT)
y2 += 0.62

divh(s, y2+0.08)
ml_steps = ["1  Lee ventas de PG agrupadas por mes y producto",
            "2  Selecciona Top 15 productos por ingreso historico",
            "3  Entrena LinearRegression por producto  ( y = B0 + B1 * mes )",
            "4  Proyecta enero — diciembre 2026 (12 meses x 15 productos)",
            "5  Escribe 180 filas en tabla predicciones_2026",
            "6  Grafana muestra real vs prediccion en overlay"]
y2 += 0.2
for step in ml_steps:
    tx(s, 6.75, y2, 5.85, 0.3, step, size=Pt(8.5), color=TB)
    y2 += 0.3

# ═══════════════════════════════════════════════════════════════════════════════
# S8 — RESULTADOS (slide oscura)
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg(s, D)
hbar(s, "8 / 9"); fbar(s)

tx(s, 0.6, 0.2, 12.0, 0.42, "RESULTADOS DEL SISTEMA", size=Pt(11), bold=True, color=TL, align=PP_ALIGN.CENTER)
tx(s, 0.6, 0.6, 12.0, 0.55, "Datos reales de IFERSAN procesados por el pipeline", size=Pt(28), bold=True, color=WH, align=PP_ALIGN.CENTER)

big_stats = [("30,372","Mensajes en Kafka",P2),("16,794","Filas en PostgreSQL",P2),
             ("S/ 406K","Ingresos procesados",RGBColor(0x34,0xD3,0x99)),("S/ 1.6M","ML 2026",RGBColor(0xC4,0xB5,0xFD))]
xs = 0.5
for num, lbl, nc in big_stats:
    box(s, xs, 1.32, 3.02, 1.52, fill=N, border=P, bw=Pt(1.5))
    tx(s, xs, 1.42, 3.02, 0.72, num, size=Pt(28), bold=True, color=nc, align=PP_ALIGN.CENTER)
    tx(s, xs, 2.14, 3.02, 0.55, lbl, size=Pt(9), color=TL, align=PP_ALIGN.CENTER)
    xs += 3.15

# Top 10 tabla (izq)
box(s, 0.5, 2.98, 6.1, 3.82, fill=N, border=P, bw=Pt(1))
tx(s, 0.65, 3.08, 5.8, 0.28, "TOP 10 PRODUCTOS POR INGRESO REAL", size=Pt(9), bold=True, color=TL)
top10 = [("1","PEPSI 2000ML","S/ 71,448"),("2","ESCOCESA 2250ml","S/ 56,520"),
         ("3","PILSEN CALLAO 620ml","S/ 44,232"),("4","GUARANA BRASIL 3lt","S/ 35,916"),
         ("5","VIVA BACKUS 620ml","S/ 31,716"),("6","TRIPLE KOLA 3lt","S/ 29,400"),
         ("7","PEPSI 500ML","S/ 26,880"),("8","BACKUS ICE 620ml","S/ 24,192"),
         ("9","CONCORDIA 3lt","S/ 22,344"),("10","SPRITE 1.5lt","S/ 19,800")]
y = 3.4
for rank, prod, total in top10:
    is_top3 = int(rank) <= 3
    box(s, 0.6, y, 5.85, 0.34, fill=P if is_top3 else (RGBColor(0x1A,0x2F,0x5C) if int(rank)%2==0 else N))
    tx(s, 0.65, y+0.05, 0.42, 0.24, rank, size=Pt(8.5), bold=True, color=WH, align=PP_ALIGN.CENTER)
    tx(s, 1.12, y+0.05, 3.5, 0.24, prod, size=Pt(8.5), bold=is_top3, color=WH)
    tx(s, 4.72, y+0.05, 1.62, 0.24, total, size=Pt(8.5), bold=True, color=RGBColor(0x34,0xD3,0x99), align=PP_ALIGN.RIGHT)
    y += 0.34

# Metricas (der)
box(s, 6.83, 2.98, 6.0, 3.82, fill=N, border=P, bw=Pt(1))
tx(s, 6.98, 3.08, 5.7, 0.28, "METRICAS DEL SISTEMA EN PRODUCCION", size=Pt(9), bold=True, color=TL)
sysm = [("Latencia ERP a Grafana","< 30 segundos",RGBColor(0x34,0xD3,0x99)),
        ("Consumer LAG Kafka","0  (sin mensajes pendientes)",RGBColor(0x34,0xD3,0x99)),
        ("Uptime Docker Compose","11 contenedores activos",P2),
        ("Clientes unicos","1,106 clientes",WH),("Productos catalogados","62 SKUs activos",WH),
        ("Vendedores activos","6 preventistas",WH),("Docs descargados","173 archivos Excel",WH),
        ("Meses de historico","Enero — Junio 2026",WH),
        ("Predicciones ML","180 filas (15 prod x 12 mes)",RGBColor(0xC4,0xB5,0xFD)),
        ("R2 Score promedio","0.82  (buena correlacion)",RGBColor(0xC4,0xB5,0xFD)),
        ("Alertas configuradas","2  activas en Grafana",P2)]
y = 3.4
for lbl, val, vc in sysm:
    box(s, 6.93, y, 5.75, 0.34, fill=RGBColor(0x1A,0x2F,0x5C) if sysm.index((lbl,val,vc))%2==0 else N)
    tx(s, 7.0, y+0.06, 3.2, 0.22, lbl, size=Pt(8.5), color=TL)
    tx(s, 10.25, y+0.06, 2.38, 0.22, val, size=Pt(8.5), bold=True, color=vc, align=PP_ALIGN.RIGHT)
    y += 0.34

# ═══════════════════════════════════════════════════════════════════════════════
# S9 — ROADMAP + CIERRE
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg(s, BG)
slide_hdr(s, "Fase Final — De Prototipo a Produccion Real",
          "Lo que ya funciona hoy y los pasos para el despliegue en produccion")
fbar(s); hbar(s, "9 / 9")

# Columna izq: Hecho
box(s, 0.45, 1.02, 5.9, 5.7, fill=WH, border=BR)
box(s, 0.45, 1.02, 5.9, 0.38, fill=GR)
tx(s, 0.62, 1.08, 5.6, 0.27, "COMPLETADO — Sistema funcionando con datos reales", size=Pt(9.5), bold=True, color=WH)

done = ["Autenticacion JWT automatica contra API CasaMarket",
        "Producer Python: detecta Excel, publica en Kafka",
        "Apache Kafka 3.7 KRaft con 2 topics activos",
        "Spark job_ventas: 3 queries paralelas (Parquet + PG + consola)",
        "Spark job_documentos: 4 queries, ventanas 5 min",
        "PostgreSQL 16: ventas (16k filas) + predicciones_2026",
        "Machine Learning: 180 predicciones 2026 en PostgreSQL",
        "Grafana: 2 dashboards, 29 paneles, 2 alertas",
        "Prometheus + kafka-exporter: observabilidad de infra",
        "Docker Compose: 11 servicios orquestados",
        "Kafka UI: monitoreo visual de topics en tiempo real",
        "Datos reales de IFERSAN validados end-to-end"]
y = 1.5
for item in done:
    box(s, 0.55, y, 5.7, 0.37, fill=GL, border=RGBColor(0xBC,0xF0,0xDA), bw=Pt(0.75))
    tx(s, 0.64, y+0.07, 0.3, 0.24, "V", size=Pt(9), bold=True, color=GR, align=PP_ALIGN.CENTER)
    tx(s, 1.0, y+0.08, 5.1, 0.22, item, size=Pt(8.5), color=TB)
    y += 0.41

# Columna der: proximos pasos
box(s, 6.55, 1.02, 6.23, 5.7, fill=WH, border=BR)
box(s, 6.55, 1.02, 6.23, 0.38, fill=P)
tx(s, 6.72, 1.08, 5.9, 0.27, "PROXIMOS PASOS — Para ir a produccion real", size=Pt(9.5), bold=True, color=WH)

next_steps = [
    ("Migrar a servidor cloud",
     "AWS EC2 o servidor propio. Kafka en VM dedicada, PG en RDS, Grafana en ECS."),
    ("Credenciales de produccion",
     "Actualizar .env con cuenta real del ERP. Ajustar frecuencia de descarga segun volumen real."),
    ("Escalar particionamiento Kafka",
     "Subir a 3 particiones por topic. Replication-factor=2 para tolerancia a fallos."),
    ("Reentrenamiento ML mensual",
     "Cron job mensual para prediccion_ventas.py. Agregar variables: precio, temporada, zona."),
    ("Alertas de negocio",
     "Alertas de ventas bajas por vendedor. Integracion con email o WhatsApp Business API."),
    ("Documentacion y capacitacion",
     "Manual operativo para IFERSAN. Playbook de incidentes y backup semanal automatico."),
]
y2 = 1.5
for i, (title, desc) in enumerate(next_steps):
    box(s, 6.65, y2, 6.03, 0.88, fill=BG, border=P2, bw=Pt(1.5))
    box(s, 6.65, y2, 0.38, 0.88, fill=P)
    tx(s, 6.65, y2+0.23, 0.38, 0.4, str(i+1), size=Pt(16), bold=True, color=WH, align=PP_ALIGN.CENTER)
    tx(s, 7.1, y2+0.07, 5.44, 0.28, title, size=Pt(10), bold=True, color=TH)
    tx(s, 7.1, y2+0.38, 5.44, 0.44, desc, size=Pt(8.5), color=TB)
    y2 += 0.96

# ═══════════════════════════════════════════════════════════════════════════════
# S10 — CIERRE (slide oscura)
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg(s, D)
box(s, 0, 0, 13.33, 0.07, fill=P2)

tx(s, 0.7, 0.28, 12.0, 0.38, "RESUMEN EJECUTIVO", size=Pt(11), bold=True, color=TL, align=PP_ALIGN.CENTER)
tx(s, 0.7, 0.66, 12.0, 0.6, "Una arquitectura que parte de lo que ya conoces", size=Pt(30), bold=True, color=WH, align=PP_ALIGN.CENTER)
tx(s, 0.7, 1.3, 12.0, 0.3, "SQL familiar  +  Streaming en tiempo real  +  Machine Learning  +  Dashboards en vivo", size=Pt(12), color=P2, align=PP_ALIGN.CENTER)
box(s, 0.7, 1.78, 11.93, 0.025, fill=N)

# 5 pilares con logos
pillars = [('kafka','Kafka','El bus de datos.\nDesacopla y persiste\ntodos los eventos.'),
           ('spark','Spark','El motor.\nTransforma en tiempo\nreal cada 30 segundos.'),
           ('postgresql','PostgreSQL','Tu base de datos.\nSQL que ya conoces,\nalimentada en vivo.'),
           ('sklearn','ML','El cerebro.\nS/ 1.6M proyectados\npara 2026.'),
           ('grafana','Grafana','Los ojos.\n29 paneles y alertas\nautomaticas activas.')]
xp = 0.7
PW = 2.32
for lkey, pname, pdesc in pillars:
    box(s, xp, 1.92, PW, 2.85, fill=N, border=P, bw=Pt(1.5))
    put_logo(s, lkey, xp+0.3, 2.02, PW-0.6, 1.15)
    tx(s, xp, 3.24, PW, 0.28, pname, size=Pt(11), bold=True, color=WH, align=PP_ALIGN.CENTER)
    tx(s, xp+0.1, 3.56, PW-0.2, 0.88, pdesc, size=Pt(9), color=TL, align=PP_ALIGN.CENTER)
    xp += PW + 0.1

box(s, 0.7, 4.95, 11.93, 0.025, fill=N)

# Stats finales
fin = [("<30s","Latencia"),("30,372","Mensajes"),("16,794","Filas SQL"),("S/406K","Ingresos"),("S/1.6M","ML 2026"),("11","Containers")]
xf = 0.7
for num, lbl in fin:
    BFW = 1.92
    box(s, xf, 5.05, BFW, 0.82, fill=N, border=P2, bw=Pt(1))
    tx(s, xf, 5.1, BFW, 0.44, num, size=Pt(18), bold=True, color=WH, align=PP_ALIGN.CENTER)
    tx(s, xf, 5.53, BFW, 0.28, lbl, size=Pt(8.5), color=TL, align=PP_ALIGN.CENTER)
    xf += BFW + 0.07

box(s, 0.7, 6.08, 11.93, 0.025, fill=N)
tx(s, 0.7, 6.18, 12.0, 0.27, "Universidad Peruana Union  ·  IX Ciclo  ·  Big Data  ·  Unidad II  ·  Docente: Mg. Angel Sullon", size=Pt(9), color=TL, align=PP_ALIGN.CENTER)
tx(s, 0.7, 6.48, 12.0, 0.27, "Sistema en produccion con datos reales de IFERSAN Juliaca, Peru  ·  Junio 2026", size=Pt(9), color=TL, align=PP_ALIGN.CENTER)

# ── GUARDAR ───────────────────────────────────────────────────────────────────
OUT = r"Z:\Universidad\IXCICLO\BigData\UnidadII\pptx\CasaMarket_BigData_v2.pptx"
prs.save(OUT)
print(f"\nGuardado: {OUT}")
print(f"Slides: {len(prs.slides)}  |  Logos: {sum(1 for v in LOGOS.values() if v)}/{len(LOGOS)}")

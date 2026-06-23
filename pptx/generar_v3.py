"""
CasaMarket Pipeline Big Data
"Lleva tu Negocio a la Nube"
Fondos degradados + glow PIL | Logos reales | 16:9 | Paleta navy/blue
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import io, os, requests, math

# ─── Dimensiones fondo 16:9 a 96dpi ──────────────────────────────────────────
BW, BH = 1280, 720

# ─── PALETA UNICA: Navy → Blue ───────────────────────────────────────────────
C = {
    'dark':   (4,   11,  24 ),
    'navy':   (10,  25,  55 ),
    'mid':    (16,  42,  90 ),
    'blue':   (26,  86,  219),
    'blue2':  (63,  131, 248),
    'cyan':   (14,  165, 233),
    'light':  (240, 244, 249),
    'white':  (255, 255, 255),
    'green':  (5,   122, 85 ),
    'green_l':(222, 247, 236),
}

# ─── PIL: GENERADORES DE FONDO ────────────────────────────────────────────────

def grad(c1, c2, w=BW, h=BH):
    img = Image.new('RGB', (w, h))
    dr = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        color = tuple(int(c1[i]*(1-t) + c2[i]*t) for i in range(3))
        dr.line([(0,y),(w,y)], fill=color)
    return img

def glow(img, cx, cy, r, color, blur=90, alpha=170):
    layer = Image.new('RGBA', img.size, (0,0,0,0))
    dr = ImageDraw.Draw(layer)
    dr.ellipse([(cx-r, cy-r), (cx+r, cy+r)], fill=(color[0], color[1], color[2], alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=blur))
    return Image.alpha_composite(img.convert('RGBA'), layer).convert('RGB')

def arc_deco(img, cx, cy, radii, color=(63,131,248), start=150, end=280, w=1):
    dr = ImageDraw.Draw(img)
    for r in radii:
        dr.arc([(cx-r, cy-r), (cx+r, cy+r)], start=start, end=end, fill=color, width=w)
    return img

def dot_grid(img, spacing=60, color=(255,255,255), alpha=18):
    layer = Image.new('RGBA', img.size, (0,0,0,0))
    dr = ImageDraw.Draw(layer)
    for x in range(0, BW, spacing):
        for y in range(0, BH, spacing):
            dr.ellipse([(x-2, y-2), (x+2, y+2)], fill=(color[0], color[1], color[2], alpha))
    return Image.alpha_composite(img.convert('RGBA'), layer).convert('RGB')

def diag_lines(img, spacing=110, color=(255,255,255), alpha=12):
    layer = Image.new('RGBA', img.size, (0,0,0,0))
    dr = ImageDraw.Draw(layer)
    for x in range(-BH, BW+BH, spacing):
        dr.line([(x, 0), (x+BH, BH)], fill=(color[0], color[1], color[2], alpha), width=1)
    return Image.alpha_composite(img.convert('RGBA'), layer).convert('RGB')

def to_buf(img):
    b = io.BytesIO(); img.save(b, format='PNG'); b.seek(0); return b

# Backgrounds
def mk_hero():
    img = grad(C['dark'], (12, 30, 65))
    img = glow(img, BW-100, 80,  420, C['blue'],  blur=110, alpha=160)
    img = glow(img, 60,  BH-60, 280, C['cyan'],  blur=80,  alpha=100)
    img = glow(img, BW//2, BH,  350, C['blue'],  blur=100, alpha=60)
    img = arc_deco(img, BW+50, -50, [380, 470, 560], (80,150,255), 160, 280, w=1)
    img = arc_deco(img, BW+50, -50, [390, 480, 570], (80,150,255), 160, 280, w=1)
    img = dot_grid(img, 65, alpha=14)
    return to_buf(img)

def mk_dark():
    img = grad((6,14,32), (14,34,70))
    img = glow(img, int(BW*0.8), int(BH*0.15), 380, C['blue'], blur=100, alpha=130)
    img = dot_grid(img, 70, alpha=10)
    return to_buf(img)

def mk_medium():
    img = grad((8,20,46), (18,44,90))
    img = glow(img, BW//2, -50, 420, C['blue2'], blur=100, alpha=120)
    img = diag_lines(img, 100, alpha=10)
    return to_buf(img)

def mk_split():
    """Izquierda oscura, derecha muy oscura"""
    img = grad((6,15,34), (10,25,54))
    img = glow(img, 0, BH//2, 380, C['blue'], blur=90, alpha=90)
    img = dot_grid(img, 60, alpha=8)
    return to_buf(img)

def mk_light():
    """Para slides con contenido técnico"""
    img = grad((242,246,252), (255,255,255))
    dr = ImageDraw.Draw(img)
    dr.rectangle([(0,0),(BW-1,6)], fill=C['blue'])
    return to_buf(img)

print("Generando fondos PIL...")
BGHERO   = mk_hero()
BGDARK   = mk_dark()
BGMED    = mk_medium()
BGSPLIT  = mk_split()
BGLIGHT  = mk_light()
print("  Fondos OK")

# ─── LOGOS ────────────────────────────────────────────────────────────────────
LOGO_DIR = os.path.join(os.path.dirname(__file__), 'logos')

def make_badge(abbr, full, bg, size=300):
    r0, g0, b0 = int(bg[0]), int(bg[1]), int(bg[2])
    img = Image.new('RGBA', (size, size), (0,0,0,0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle([0, 0, size-1, size-1], radius=36, fill=(r0, g0, b0, 255))
    dr.rectangle([0, size-56, size-1, size-1],
                 fill=(max(0,r0-25), max(0,g0-25), max(0,b0-25), 255))
    fs = size // (3 if len(abbr) <= 2 else 4)
    try:
        font_b = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", fs)
        font_s = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size//11)
    except:
        font_b = ImageFont.load_default(size=fs)
        font_s = ImageFont.load_default(size=size//12)
    bb = dr.textbbox((0,0), abbr, font=font_b)
    dr.text(((size-(bb[2]-bb[0]))//2, size//2 - fs//2 - 20), abbr,
            fill=(255,255,255,255), font=font_b)
    bb2 = dr.textbbox((0,0), full, font=font_s)
    dr.text(((size-(bb2[2]-bb2[0]))//2, size-44), full,
            fill=(200,220,255,255), font=font_s)
    buf = io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0)
    return buf

def load_logo(key):
    for p in [os.path.join(LOGO_DIR, f'{key}_raw.png'), os.path.join(LOGO_DIR, f'{key}.png')]:
        if os.path.exists(p):
            try:
                Image.open(p)
                buf = io.BytesIO(open(p,'rb').read())
                return buf
            except: pass
    badges = {
        'kafka':      ((227, 76, 38),   'K',  'Kafka'),
        'spark':      ((226, 90, 28),   'S',  'Spark'),
        'postgresql': ((51, 103, 145),  'PG', 'PostgreSQL'),
        'grafana':    ((244,104,  0),   'G',  'Grafana'),
        'prometheus': ((230, 82, 44),   'P',  'Prometheus'),
        'docker':     ((29,  99, 237),  'D',  'Docker'),
        'python':     ((55, 118, 171),  'Py', 'Python'),
        'sklearn':    ((247,147, 30),   'ML', 'sklearn'),
        'parquet':    ((80, 171, 241),  'PQ', 'Parquet'),
    }
    if key in badges:
        bg, abbr, name = badges[key]
        return make_badge(abbr, name, bg)
    return None

print("Cargando logos...")
LOGOS = {k: load_logo(k) for k in ['kafka','spark','postgresql','grafana','prometheus','docker','python','sklearn','parquet']}
print(f"  {sum(1 for v in LOGOS.values() if v)}/9 logos OK")

# ─── HELPERS PPTX ─────────────────────────────────────────────────────────────
def R(*rgb): return RGBColor(*rgb)

RW = R(*C['white']); RB = R(*C['blue']); RB2 = R(*C['blue2'])
RN = R(*C['navy']); RD = R(*C['dark']); RT = R(60,75,100); RTL = R(140,165,200)
RGR = R(*C['green']); RGL = R(*C['green_l']); RBR = R(209,217,232)
RLIGHT = R(*C['light'])

def set_bg(slide, color): f=slide.background.fill; f.solid(); f.fore_color.rgb=R(*color)

def set_bg_img(slide, buf):
    buf.seek(0)
    slide.shapes.add_picture(buf, Inches(0), Inches(0), prs.slide_width, prs.slide_height)

def B(slide, l, t, w, h, fill=None, border=None, bw=Pt(1)):
    shp = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    if fill: shp.fill.solid(); shp.fill.fore_color.rgb = fill
    else: shp.fill.background()
    if border: shp.line.color.rgb = border; shp.line.width = bw
    else: shp.line.fill.background()
    return shp

def T(slide, l, t, w, h, text, size=Pt(11), bold=False, color=None, align=PP_ALIGN.LEFT, italic=False):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tb.word_wrap = True; tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.alignment = align
    run = p.add_run(); run.text = text
    run.font.size = size; run.font.bold = bold; run.font.italic = italic
    if color: run.font.color.rgb = color
    return tb

def LOGO(slide, key, l, t, w, h):
    buf = LOGOS.get(key)
    if not buf: return False
    buf.seek(0); slide.shapes.add_picture(buf, Inches(l), Inches(t), Inches(w), Inches(h))
    return True

def divider(slide, y, dark=False):
    B(slide, 0.5, y, 12.33, 0.025, fill=RN if dark else RBR)

def hbar_top(slide, color_rgb=None):
    if color_rgb is None: color_rgb = C['blue']
    B(slide, 0, 0, 13.33, 0.07, fill=R(*color_rgb))

def footer_dark(slide, txt="CasaMarket Big Data  |  IFERSAN Juliaca  |  2026"):
    B(slide, 0, 7.18, 13.33, 0.32, fill=R(*C['dark']))
    T(slide, 0.5, 7.21, 12.5, 0.25, txt, size=Pt(8), color=RTL)

def footer_light(slide, txt="CasaMarket Big Data  |  IFERSAN Juliaca  |  2026"):
    B(slide, 0, 7.18, 13.33, 0.32, fill=RLIGHT, border=RBR)
    T(slide, 0.5, 7.21, 12.5, 0.25, txt, size=Pt(8), color=RTL)

def slide_num(slide, n, total=9, dark=True):
    c = RTL
    T(slide, 12.4, 7.21, 0.85, 0.25, f"{n}/{total}", size=Pt(8), color=c, align=PP_ALIGN.RIGHT)

# ─────────────────────────────────────────────────────────────────────────────
prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

# ═══════════════════════════════════════════════════════════════════════════════
# S1 — PORTADA HERO
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg_img(s, BGHERO)
hbar_top(s, C['blue2'])

# Tag empresa superior izq
B(s, 0.5, 0.25, 2.2, 0.38, fill=R(16,42,90), border=R(63,131,248), bw=Pt(1))
T(s, 0.5, 0.25, 2.2, 0.38, "  IFERSAN · Juliaca, Peru", size=Pt(9), bold=True, color=RB2)

# Tag superior der
B(s, 10.62, 0.25, 2.2, 0.38, fill=R(16,42,90), border=R(63,131,248), bw=Pt(1))
T(s, 10.62, 0.25, 2.2, 0.38, "Big Data · Unidad II", size=Pt(9), bold=True, color=RB2, align=PP_ALIGN.CENTER)

# Título principal centrado
T(s, 0.6, 1.05, 12.1, 1.1,
  "Lleva tu Negocio\na la Nube",
  size=Pt(54), bold=True, color=RW, align=PP_ALIGN.CENTER)

# Subtítulo
T(s, 0.6, 3.1, 12.1, 0.5,
  "Pipeline Big Data en Tiempo Real para IFERSAN",
  size=Pt(20), bold=False, color=RB2, align=PP_ALIGN.CENTER)

T(s, 0.6, 3.62, 12.1, 0.35,
  "Del ERP al dashboard en menos de 30 segundos · Kafka · Spark · PostgreSQL · ML · Grafana",
  size=Pt(11), color=RTL, align=PP_ALIGN.CENTER)

# Linea decorativa
B(s, 3.5, 4.12, 6.33, 0.04, fill=RB2)

# Stats row
stats = [("<30s","Del ERP al\nDashboard"),("30,372","Mensajes\nprocesados"),
         ("S/ 406K","Ingresos\nvalidados"),("S/ 1.6M","Proyeccion\nML 2026")]
xs = 1.8
for num, lbl in stats:
    B(s, xs, 4.3, 2.2, 1.1, fill=R(16,42,90), border=RB2, bw=Pt(1))
    B(s, xs, 4.3, 2.2, 0.06, fill=RB2)
    T(s, xs, 4.38, 2.2, 0.52, num, size=Pt(22), bold=True, color=RW, align=PP_ALIGN.CENTER)
    T(s, xs, 4.9, 2.2, 0.44, lbl, size=Pt(8), color=RTL, align=PP_ALIGN.CENTER)
    xs += 2.35

T(s, 0.5, 5.58, 12.3, 0.28,
  "Universidad Peruana Union  ·  IX Ciclo  ·  Big Data  ·  Unidad II  ·  Docente: Mg. Angel Sullon",
  size=Pt(9), color=RTL, align=PP_ALIGN.CENTER)

# Logo strip en footer
logos_portada = ['kafka','spark','postgresql','grafana','docker','sklearn']
xl = 1.5
for lkey in logos_portada:
    B(s, xl, 5.98, 1.72, 1.02, fill=R(10,25,55), border=RB, bw=Pt(1))
    LOGO(s, lkey, xl+0.25, 6.04, 1.22, 0.72)
    xl += 1.85

footer_dark(s)

# ═══════════════════════════════════════════════════════════════════════════════
# S2 — EL RETO
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg_img(s, BGSPLIT)
hbar_top(s)

T(s, 0.5, 0.15, 12.3, 0.5, "EL PROBLEMA QUE RESOLVEMOS",
  size=Pt(10), bold=True, color=RTL, align=PP_ALIGN.CENTER)

# Cuatro cards de problema
problems = [
    ("Sin visibilidad en tiempo real",
     "El gerente no sabe cuanto vendieron HOY mientras el dia avanza. Los datos llegan mañana en un Excel. Cada hora sin datos es una hora de decision ciega."),
    ("Sin alertas automaticas",
     "Si un vendedor deja de vender 3 horas, nadie se entera hasta el cierre de caja. Sin alertas automaticas, los problemas se detectan demasiado tarde."),
    ("Sin proyecciones de demanda",
     "No hay forma de anticipar si diciembre sera bueno o malo. Las decisiones de stock y personal se toman a ciegas, arriesgando perdidas innecesarias."),
    ("Historial disperso en archivos",
     "Reportes manuales en Excel sin consolidar. Comparar el mes actual vs el mismo mes del anio anterior demora horas de trabajo manual cada semana."),
]
y = 0.72
for i, (title, desc) in enumerate(problems):
    box_h = 1.5
    B(s, 0.45, y, 6.1, box_h, fill=R(10,22,48), border=R(26,86,219), bw=Pt(1.5))
    B(s, 0.45, y, 0.08, box_h, fill=R(220,50,50))
    # Numero grande de fondo
    T(s, 5.5, y+0.1, 0.9, 1.2, str(i+1), size=Pt(56), bold=True, color=R(20,40,85), align=PP_ALIGN.RIGHT)
    T(s, 0.65, y+0.12, 5.5, 0.34, title, size=Pt(13), bold=True, color=RW)
    T(s, 0.65, y+0.5, 5.5, 0.9, desc, size=Pt(9), color=RTL)
    y += box_h + 0.18

# Soluciones (columna der)
solutions = [
    ("Visibilidad total en < 30 segundos",
     "Con el pipeline, cada venta aparece en Grafana en menos de 30 segundos de ser registrada en el ERP. Decision en tiempo real, siempre."),
    ("2 alertas automaticas 24/7",
     "Consumer Lag alto y Broker caido generan alertas inmediatas. El equipo de TI actua antes de que el negocio se vea afectado por algun problema."),
    ("S/ 1.6M proyectados con ML 2026",
     "Machine Learning entrenado con datos reales de IFERSAN. Proyeccion mensual por producto para todo 2026. Planificacion de stock basada en datos."),
    ("16,794 filas listas via SQL",
     "Toda la data en PostgreSQL. Los mismos SELECT, GROUP BY, JOIN que ya conocen. Sin curva de aprendizaje, solo mas poder y velocidad."),
]
y = 0.72
for title, desc in solutions:
    box_h = 1.5
    B(s, 6.78, y, 6.1, box_h, fill=R(8,32,22), border=R(5,122,85), bw=Pt(1.5))
    B(s, 6.78, y, 0.08, box_h, fill=RGR)
    T(s, 6.98, y+0.12, 5.7, 0.34, title, size=Pt(13), bold=True, color=RW)
    T(s, 6.98, y+0.5, 5.7, 0.9, desc, size=Pt(9), color=RTL)
    y += box_h + 0.18

# Divisor central y etiquetas
B(s, 6.53, 0.65, 0.04, 6.4, fill=R(16,42,90))
T(s, 0.45, 0.68, 6.1, 0.26, "SIN EL PIPELINE", size=Pt(8.5), bold=True, color=R(220,80,80))
T(s, 6.78, 0.68, 6.1, 0.26, "CON EL PIPELINE", size=Pt(8.5), bold=True, color=RGR)

footer_dark(s); slide_num(s, 2)

# ═══════════════════════════════════════════════════════════════════════════════
# S3 — ARQUITECTURA GENERAL
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg_img(s, BGMED)
hbar_top(s)

T(s, 0.5, 0.15, 12.3, 0.5, "COMO FUNCIONA", size=Pt(10), bold=True, color=RTL, align=PP_ALIGN.CENTER)
T(s, 0.5, 0.55, 12.3, 0.6, "6 Capas, 1 Objetivo — Del ERP al Dashboard",
  size=Pt(30), bold=True, color=RW, align=PP_ALIGN.CENTER)

# Panel fondo del pipeline
B(s, 0.4, 1.32, 12.53, 4.5, fill=R(8,20,45), border=R(26,86,219), bw=Pt(1))

# Etiquetas de fase
phases = ["FUENTE","INGESTA","BROKER","PROCESO","STORE / ML","VISUAL"]
px = [0.55, 2.6, 4.65, 6.7, 8.75, 11.08]
pw = [1.9,  1.9, 1.9,  1.9, 2.15, 1.72]
for lbl, lx, lw in zip(phases, px, pw):
    B(s, lx, 1.4, lw, 0.3, fill=R(16,42,90))
    T(s, lx, 1.4, lw, 0.3, lbl, size=Pt(8), bold=True, color=RTL, align=PP_ALIGN.CENTER)

# Bloques con logo + nombre + descripción
pipeline = [
    (None,      'ERP Web',    'API REST · JWT\nadmin.casamarket.la', 0.55, 1.9),
    ('kafka',   'Kafka 3.7',  'ventas.raw\n30,372 msgs · LAG=0',    2.6,  1.9),
    ('spark',   'Spark 3.5',  'Streaming 30s\n3 queries paralelas', 4.65, 1.9),
    ('postgresql','PostgreSQL','16,794 filas\nS/ 406,018 reales',   6.7,  1.9),
    ('sklearn', 'ML sklearn', '180 predicciones\nS/ 1.6M — 2026',  8.75, 2.15),
    ('grafana', 'Grafana',    '29 paneles\n2 alertas activas',      11.08,1.72),
]
for lkey, name, sub, lx, lw in pipeline:
    B(s, lx, 1.78, lw, 2.8, fill=R(12,28,60), border=R(63,131,248), bw=Pt(1.5))
    if lkey:
        iw = lw - 0.4
        LOGO(s, lkey, lx+0.2, 1.85, iw, 1.3)
    else:
        T(s, lx, 2.3, lw, 0.65, "ERP", size=Pt(26), bold=True, color=RB2, align=PP_ALIGN.CENTER)
    T(s, lx, 3.22, lw, 0.3, name, size=Pt(10), bold=True, color=RW, align=PP_ALIGN.CENTER)
    T(s, lx, 3.54, lw, 0.6, sub, size=Pt(8), color=RTL, align=PP_ALIGN.CENTER)

# Flechas
for ax in [2.5, 4.55, 6.6, 8.65, 10.93]:
    T(s, ax, 2.6, 0.13, 0.35, ">", size=Pt(18), bold=True, color=RB2, align=PP_ALIGN.CENTER)

# Fila observabilidad
obs = [('Kafka Exporter',':9308',4.65), ('Prometheus',':9090',6.7)]
for on, op, ox in obs:
    B(s, ox, 4.72, 1.9, 0.85, fill=R(10,24,52), border=R(40,80,160), bw=Pt(1))
    T(s, ox, 4.79, 1.9, 0.28, on, size=Pt(9), bold=True, color=RW, align=PP_ALIGN.CENTER)
    T(s, ox, 5.1, 1.9, 0.4, op, size=Pt(8.5), color=RTL, align=PP_ALIGN.CENTER)
T(s, 6.6, 4.95, 0.13, 0.3, ">", size=Pt(13), bold=True, color=RTL, align=PP_ALIGN.CENTER)
T(s, 8.7, 4.95, 2.55, 0.28, "metricas infra ──────────> Grafana", size=Pt(8), color=RTL)

# Leyenda
B(s, 0.4, 5.72, 12.53, 0.42, fill=R(8,20,45), border=R(20,45,95), bw=Pt(0.5))
for i, (lbl, rc) in enumerate([("Datos de negocio",RB2),("Observabilidad",RTL),("Machine Learning",R(147,112,219))]):
    xi = 1.2 + i*3.8
    B(s, xi, 5.85, 0.2, 0.2, fill=rc)
    T(s, xi+0.26, 5.83, 3.3, 0.24, lbl, size=Pt(8.5), color=RW)

footer_dark(s); slide_num(s, 3)

# ═══════════════════════════════════════════════════════════════════════════════
# S4 — STACK TECNOLOGICO (9 logos)
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg_img(s, BGDARK)
hbar_top(s)

T(s, 0.5, 0.15, 12.3, 0.38, "LAS TECNOLOGIAS", size=Pt(10), bold=True, color=RTL, align=PP_ALIGN.CENTER)
T(s, 0.5, 0.52, 12.3, 0.55, "9 Tecnologias de Clase Mundial",
  size=Pt(28), bold=True, color=RW, align=PP_ALIGN.CENTER)
T(s, 0.5, 1.08, 12.3, 0.3,
  "Todas en contenedores Docker · Red interna ec-kafka-dev-net · Produccion lista",
  size=Pt(11), color=RTL, align=PP_ALIGN.CENTER)

tech = [
    ('kafka',      'Apache Kafka 3.7',   'KRaft sin ZooKeeper\n2 topics activos · LAG = 0'),
    ('spark',      'Apache Spark 3.5',   'Structured Streaming\nMicro-batch cada 30 segundos'),
    ('postgresql', 'PostgreSQL 16',      '16,794 ventas · 180 predicciones\nSQL compatible con MySQL'),
    ('grafana',    'Grafana',            '2 dashboards · 29 paneles\n2 alertas automaticas activas'),
    ('prometheus', 'Prometheus',         'TSDB · scraping cada 15s\nPromQL para metricas de infra'),
    ('sklearn',    'Scikit-learn',       'LinearRegression por producto\nS/ 1,614,943 proyectados 2026'),
    ('docker',     'Docker Compose',     '9 servicios orquestados\nVolumenes y redes persistentes'),
    ('python',     'Python 3.12',        'Producer + Consumer + ML\nkafka-python-ng · pandas · SQLAlchemy'),
    ('parquet',    'Apache Parquet',     'Formato columnar para analytics\n4 carpetas de datos historicos'),
]
CW = 3.97
for i, (lkey, name, desc) in enumerate(tech):
    row, col = i // 3, i % 3
    lx = 0.42 + col * (CW + 0.14)
    ly = 1.55 + row * 1.88
    B(s, lx, ly, CW, 1.72, fill=R(12,28,62), border=R(63,131,248), bw=Pt(1))
    B(s, lx, ly, CW, 0.06, fill=RB2)
    LOGO(s, lkey, lx+0.12, ly+0.15, 1.05, 0.9)
    T(s, lx+1.26, ly+0.15, CW-1.38, 0.32, name, size=Pt(10.5), bold=True, color=RW)
    T(s, lx+1.26, ly+0.52, CW-1.38, 0.64, desc, size=Pt(9), color=RTL)
    T(s, lx+1.26, ly+1.35, CW-1.38, 0.28, "Container activo en Docker", size=Pt(8), color=R(40,80,160))

footer_dark(s); slide_num(s, 4)

# ═══════════════════════════════════════════════════════════════════════════════
# S5 — PARA EL EQUIPO TECNICO (PostgreSQL + ML)
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg_img(s, BGLIGHT)
hbar_top(s)

T(s, 0.5, 0.15, 12.3, 0.38, "PARA EL EQUIPO TECNICO", size=Pt(10), bold=True, color=RTL)
T(s, 0.5, 0.5, 12.3, 0.45, "El mismo SQL que ya conoces — ahora alimentado en tiempo real",
  size=Pt(20), bold=True, color=R(*C['dark']))

# Columna izq: PostgreSQL
B(s, 0.42, 1.12, 6.0, 5.88, fill=RW, border=RBR)
B(s, 0.42, 1.12, 6.0, 0.07, fill=RB)

LOGO(s, 'postgresql', 0.52, 1.22, 0.95, 0.95)
T(s, 1.58, 1.22, 4.6, 0.34, "PostgreSQL 16  ·  Puerto 15432", size=Pt(13), bold=True, color=R(*C['dark']))
T(s, 1.58, 1.58, 4.6, 0.22, "base: casamarket  ·  user: casamarket", size=Pt(9), color=RTL)
divider(s, 1.88)

T(s, 0.55, 1.98, 5.7, 0.28, "Tabla ventas  (16,794 filas  |  S/ 406,018 totales)",
  size=Pt(10), bold=True, color=R(*C['dark']))

schema = [("id","SERIAL PRIMARY KEY — autogenerado"),
          ("fecha","DATE — fecha de la venta"),
          ("producto","TEXT — nombre del producto"),
          ("marca","TEXT — PEPSI / PILSEN / ESCOCESA"),
          ("categoria","TEXT — BEBIDAS / ENERGETICAS"),
          ("cantidad","NUMERIC — unidades vendidas"),
          ("total","NUMERIC — ingresos en soles S/"),
          ("cliente","TEXT — nombre del cliente"),
          ("vendedor","TEXT — nombre del preventista"),
          ("procesado_ts","TIMESTAMPTZ — timestamp Spark")]
y = 2.3
for i, (cn, ct) in enumerate(schema):
    B(s, 0.52, y, 5.7, 0.3, fill=RLIGHT if i%2==0 else RW, border=RBR, bw=Pt(0.5))
    T(s, 0.64, y+0.05, 1.55, 0.22, cn, size=Pt(8.5), bold=True, color=R(*C['dark']))
    T(s, 2.22, y+0.05, 3.85, 0.22, ct, size=Pt(8.5), color=RB)
    y += 0.3

divider(s, y+0.08)
T(s, 0.55, y+0.18, 5.5, 0.24, "Query para Grafana (funciona igual que MySQL):",
  size=Pt(9), bold=True, color=R(*C['dark']))
B(s, 0.52, y+0.46, 5.7, 1.05, fill=R(*C['dark']))
T(s, 0.65, y+0.54, 5.42, 0.92,
  "SELECT fecha::TIMESTAMPTZ AS time,\n       ROUND(SUM(total)::NUMERIC, 2) AS \"Ingresos S/\"\nFROM ventas  WHERE total > 0\nGROUP BY fecha  ORDER BY fecha",
  size=Pt(9), color=R(134,239,172))

# Columna der: ML
B(s, 6.65, 1.12, 6.25, 5.88, fill=RW, border=RBR)
B(s, 6.65, 1.12, 6.25, 0.07, fill=RB)

LOGO(s, 'sklearn', 6.75, 1.22, 1.05, 0.95)
T(s, 7.92, 1.22, 4.8, 0.34, "Scikit-learn  ·  LinearRegression", size=Pt(13), bold=True, color=R(*C['dark']))
T(s, 7.92, 1.58, 4.8, 0.22, "prediccion_ventas.py  ·  tabla predicciones_2026", size=Pt(9), color=RTL)
divider(s, 1.88)

T(s, 6.78, 1.98, 5.9, 0.28, "Proyeccion anual 2026 — Top 5 productos",
  size=Pt(10), bold=True, color=R(*C['dark']))

preds = [("PEPSI 2000ML","S/ 334,800",True),("ESCOCESA 2250ml","S/ 281,664",True),
         ("PILSEN CALLAO 620ml","S/ 198,000",False),("GUARANA BRASIL 3lt","S/ 156,000",False),
         ("VIVA BACKUS 620ml","S/ 148,200",False)]
y2 = 2.3
for prod, monto, top in preds:
    B(s, 6.75, y2, 5.9, 0.44, fill=R(232,240,254) if top else (RLIGHT if preds.index((prod,monto,top))%2==0 else RW), border=RBR, bw=Pt(0.5))
    T(s, 6.87, y2+0.09, 3.85, 0.26, prod, size=Pt(9.5), bold=top, color=R(*C['dark']))
    T(s, 10.75, y2+0.09, 1.8, 0.26, monto, size=Pt(9.5), bold=True, color=RB if top else R(*C['green']), align=PP_ALIGN.RIGHT)
    y2 += 0.44

B(s, 6.75, y2, 5.9, 0.5, fill=RB)
T(s, 6.87, y2+0.1, 3.5, 0.3, "TOP 15  TOTAL ANUAL 2026", size=Pt(10), bold=True, color=RW)
T(s, 10.55, y2+0.1, 2.0, 0.3, "S/ 1,614,943", size=Pt(10), bold=True, color=RW, align=PP_ALIGN.RIGHT)
y2 += 0.65

divider(s, y2+0.1)
ml_info = ["Modelo:  LinearRegression por producto  (y = B0 + B1 × mes)",
           "Top 15 productos por ingreso historico  ·  12 meses × 15 productos = 180 predicciones",
           "R2 Score promedio: 0.82  ·  Los resultados estan en tabla predicciones_2026 en PostgreSQL"]
y2 += 0.25
for info in ml_info:
    T(s, 6.78, y2, 5.9, 0.28, info, size=Pt(8.5), color=RTL)
    y2 += 0.3

footer_light(s); slide_num(s, 5)

# ═══════════════════════════════════════════════════════════════════════════════
# S6 — RESULTADOS REALES (impacto maximo)
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg_img(s, BGDARK)
hbar_top(s)

T(s, 0.5, 0.15, 12.3, 0.4, "RESULTADOS DEL SISTEMA", size=Pt(10), bold=True, color=RTL, align=PP_ALIGN.CENTER)
T(s, 0.5, 0.55, 12.3, 0.58, "Ya Funciona — Datos Reales de IFERSAN",
  size=Pt(30), bold=True, color=RW, align=PP_ALIGN.CENTER)

# 4 stat boxes grandes
bigs = [("30,372","Mensajes procesados\nen Apache Kafka",   RB2),
        ("16,794","Filas de ventas\nen PostgreSQL",          RB2),
        ("S/ 406K","Ingresos reales\nvalidados en el pipeline",  R(52,211,153)),
        ("S/ 1.6M","Proyeccion ML\npara 2026",              R(196,181,253))]
xs = 0.45
for num, lbl, nc in bigs:
    B(s, xs, 1.28, 3.08, 1.55, fill=R(12,28,62), border=R(26,86,219), bw=Pt(1.5))
    B(s, xs, 1.28, 3.08, 0.07, fill=nc)
    T(s, xs, 1.38, 3.08, 0.7, num, size=Pt(30), bold=True, color=nc, align=PP_ALIGN.CENTER)
    T(s, xs, 2.1, 3.08, 0.62, lbl, size=Pt(9), color=RTL, align=PP_ALIGN.CENTER)
    xs += 3.22

# Dos tablas: Top 10 y metricas sistema
B(s, 0.45, 3.0, 6.15, 3.82, fill=R(10,24,52), border=R(26,86,219), bw=Pt(1))
T(s, 0.6, 3.1, 5.85, 0.3, "TOP 10 PRODUCTOS POR INGRESO REAL", size=Pt(9), bold=True, color=RTL)
top10 = [("1","PEPSI 2000ML","S/ 71,448"),("2","ESCOCESA 2250ml","S/ 56,520"),
         ("3","PILSEN CALLAO 620ml","S/ 44,232"),("4","GUARANA BRASIL 3lt","S/ 35,916"),
         ("5","VIVA BACKUS 620ml","S/ 31,716"),("6","TRIPLE KOLA 3lt","S/ 29,400"),
         ("7","PEPSI 500ML","S/ 26,880"),("8","BACKUS ICE 620ml","S/ 24,192"),
         ("9","CONCORDIA 3lt","S/ 22,344"),("10","SPRITE 1.5lt","S/ 19,800")]
y = 3.44
for rank, prod, total in top10:
    top3 = int(rank) <= 3
    B(s, 0.55, y, 5.9, 0.33, fill=RB if top3 else (R(16,38,80) if int(rank)%2==0 else R(12,28,62)))
    T(s, 0.6, y+0.05, 0.44, 0.23, rank, size=Pt(8.5), bold=True, color=RW, align=PP_ALIGN.CENTER)
    T(s, 1.1, y+0.05, 3.5, 0.23, prod, size=Pt(8.5), bold=top3, color=RW)
    T(s, 4.7, y+0.05, 1.65, 0.23, total, size=Pt(8.5), bold=True, color=R(52,211,153), align=PP_ALIGN.RIGHT)
    y += 0.33

B(s, 6.83, 3.0, 6.05, 3.82, fill=R(10,24,52), border=R(26,86,219), bw=Pt(1))
T(s, 6.98, 3.1, 5.7, 0.3, "METRICAS DEL SISTEMA EN PRODUCCION", size=Pt(9), bold=True, color=RTL)
sysm = [("Latencia ERP a Grafana","< 30 segundos",R(52,211,153)),
        ("Consumer LAG Kafka","0  — sin mensajes pendientes",R(52,211,153)),
        ("Uptime Docker Compose","11 contenedores activos",RB2),
        ("Clientes unicos","1,106 clientes en base",RW),
        ("Productos catalogados","62 SKUs activos",RW),
        ("Vendedores activos","6 preventistas",RW),
        ("Documentos descargados","173 archivos Excel",RW),
        ("Meses de historico","Enero — Junio 2026",RW),
        ("Predicciones ML","180 filas (15 prod × 12 meses)",R(196,181,253)),
        ("R2 Score promedio","0.82  (buena correlacion)",R(196,181,253)),
        ("Alertas configuradas","2 activas en Grafana",RB2)]
y = 3.44
for lbl, val, vc in sysm:
    B(s, 6.93, y, 5.8, 0.33, fill=R(16,38,80) if sysm.index((lbl,val,vc))%2==0 else R(12,28,62))
    T(s, 7.0, y+0.06, 3.2, 0.22, lbl, size=Pt(8.5), color=RTL)
    T(s, 10.25, y+0.06, 2.42, 0.22, val, size=Pt(8.5), bold=True, color=vc, align=PP_ALIGN.RIGHT)
    y += 0.33

footer_dark(s); slide_num(s, 6)

# ═══════════════════════════════════════════════════════════════════════════════
# S7 — ROADMAP / FASE FINAL
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg_img(s, BGLIGHT)
hbar_top(s)

T(s, 0.5, 0.15, 12.3, 0.38, "PLAN DE IMPLEMENTACION", size=Pt(10), bold=True, color=RTL)
T(s, 0.5, 0.5, 12.3, 0.45, "De Prototipo a Produccion Real en la Nube",
  size=Pt(22), bold=True, color=R(*C['dark']))

B(s, 0.42, 1.1, 5.98, 5.82, fill=RW, border=RBR)
B(s, 0.42, 1.1, 5.98, 0.42, fill=R(*C['green']))
T(s, 0.56, 1.16, 5.7, 0.3, "COMPLETADO — Sistema funcionando con datos reales", size=Pt(10), bold=True, color=RW)

done = ["Autenticacion JWT automatica contra API CasaMarket",
        "Producer Python: detecta Excel, publica en Kafka",
        "Apache Kafka 3.7 KRaft con 2 topics activos (ventas + docs)",
        "Spark job_ventas: 3 queries paralelas (Parquet + PG + consola)",
        "Spark job_documentos: 4 queries, ventanas 5 minutos",
        "PostgreSQL 16: ventas (16k filas) + predicciones_2026",
        "Machine Learning: 180 predicciones 2026 en PostgreSQL",
        "Grafana: 2 dashboards completos, 29 paneles, 2 alertas",
        "Prometheus + kafka-exporter: observabilidad de infra",
        "Docker Compose: 11 servicios orquestados y configurados",
        "Kafka UI: monitoreo visual de topics en tiempo real",
        "Datos reales de IFERSAN validados end-to-end en produccion"]
y = 1.62
for item in done:
    B(s, 0.52, y, 5.72, 0.37, fill=R(*C['green_l']), border=R(187,240,215), bw=Pt(0.75))
    T(s, 0.6, y+0.07, 0.32, 0.24, "V", size=Pt(9), bold=True, color=RGR, align=PP_ALIGN.CENTER)
    T(s, 0.98, y+0.08, 5.1, 0.22, item, size=Pt(8.5), color=R(*C['dark']))
    y += 0.41

B(s, 6.6, 1.1, 6.3, 5.82, fill=RW, border=RBR)
B(s, 6.6, 1.1, 6.3, 0.42, fill=RB)
T(s, 6.74, 1.16, 6.02, 0.3, "PROXIMOS PASOS — Para ir a produccion real", size=Pt(10), bold=True, color=RW)

next_steps = [
    ("Migrar a servidor cloud",
     "AWS EC2 / GCP / Azure o servidor propio. Kafka en VM dedicada, PostgreSQL en RDS, Grafana en ECS o VPS con SSL."),
    ("Credenciales de produccion",
     "Actualizar .env con cuenta real del ERP de produccion. Ajustar frecuencia de descarga segun volumen diario real."),
    ("Escalar particionamiento Kafka",
     "Subir de 1 a 3 particiones por topic. Configurar replication-factor=2 minimo para tolerancia a fallos reales."),
    ("Reentrenamiento ML mensual",
     "Cron job mensual para prediccion_ventas.py. Agregar variables: precio unitario, temporada, zona geografica."),
    ("Alertas de negocio personalizadas",
     "Alertas de ventas bajas por vendedor con umbral configurable. Integracion con WhatsApp Business API o email."),
    ("Documentacion y capacitacion",
     "Manual operativo para el equipo de IFERSAN. Playbook de incidentes, backup semanal y monitoreo continuo."),
]
y2 = 1.62
for i, (title, desc) in enumerate(next_steps):
    B(s, 6.7, y2, 6.1, 0.9, fill=RLIGHT, border=R(209,225,248), bw=Pt(1.5))
    B(s, 6.7, y2, 0.42, 0.9, fill=RB)
    T(s, 6.7, y2+0.24, 0.42, 0.4, str(i+1), size=Pt(18), bold=True, color=RW, align=PP_ALIGN.CENTER)
    T(s, 7.2, y2+0.07, 5.48, 0.3, title, size=Pt(10.5), bold=True, color=R(*C['dark']))
    T(s, 7.2, y2+0.4, 5.48, 0.46, desc, size=Pt(8.5), color=RTL)
    y2 += 0.97

footer_light(s); slide_num(s, 7)

# ═══════════════════════════════════════════════════════════════════════════════
# S8 — POR QUE NO SOLO MySQL (comparativo)
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg_img(s, BGMED)
hbar_top(s)

T(s, 0.5, 0.15, 12.3, 0.38, "LA DECISION CORRECTA", size=Pt(10), bold=True, color=RTL, align=PP_ALIGN.CENTER)
T(s, 0.5, 0.52, 12.3, 0.55, "Por Que Esta Arquitectura y No Solo MySQL",
  size=Pt(28), bold=True, color=RW, align=PP_ALIGN.CENTER)

# Tabla
cols = [(2.85,"CAPACIDAD",R(12,28,62)), (4.97,"MySQL SOLO",R(42,14,14)), (4.97,"PIPELINE KAPPA",RB)]
x0 = 0.42
for w, hdr, hf in cols:
    B(s, x0, 1.2, w, 0.42, fill=hf)
    T(s, x0+0.12, 1.25, w-0.18, 0.3, hdr, size=Pt(10), bold=True, color=RW)
    x0 += w + 0.09

rows = [
    ("Latencia de datos",      "Horas — reporte manual",       "< 30 segundos automatico"),
    ("Procesamiento",          "Batch nocturno o manual",      "Streaming continuo 24/7"),
    ("Escalar volumen",        "Limitado por RAM del server",  "Kafka + Parquet: ilimitado"),
    ("Predicciones ML",        "No incluido nativamente",      "Integrado con sklearn"),
    ("Alertas tiempo real",    "Ninguna configurada",          "2 alertas activas Grafana"),
    ("Dashboard en vivo",      "No incluido",                  "Grafana, refresh 15s"),
    ("Tolerancia a fallos",    "Single point of failure",      "Checkpoint at-least-once"),
    ("Escalabilidad",          "Vertical — mas hardware",      "Horizontal — mas brokers"),
    ("Queries SQL",            "Si — nativo MySQL",            "Si — compatible PostgreSQL"),
    ("Historial de datos",     "En disco, sin streaming",      "Parquet columnar analytics"),
]
y = 1.62
for ri, (cap, mysql, kappa) in enumerate(rows):
    x0 = 0.42
    alt = ri%2==0
    for i, (w, val) in enumerate([(2.85,cap),(4.97,mysql),(4.97,kappa)]):
        B(s, x0, y, w, 0.46, fill=R(12,28,62) if not alt else R(16,36,74), border=R(20,45,95), bw=Pt(0.5))
        bad = i==1 and any(kw in val for kw in ["No ","Horas","Limitado","Ninguna","Single","Vertical","manual"])
        fc = RW if i==0 else (R(255,100,100) if bad else (R(52,211,153) if i==2 else RTL))
        T(s, x0+0.12, y+0.12, w-0.2, 0.28, val, size=Pt(9), bold=(i==0), color=fc)
        x0 += w + 0.09
    y += 0.46

B(s, 0.42, y+0.1, 12.48, 0.45, fill=R(10,35,90), border=R(63,131,248), bw=Pt(1))
T(s, 0.62, y+0.18, 12.1, 0.3,
  "Nota: PostgreSQL reemplaza a MySQL en la capa de almacenamiento. La sintaxis SQL es 100% compatible — SELECT, GROUP BY, JOIN, SUM funcionan igual. El cambio real es que los datos ahora llegan continuamente via Spark JDBC en lugar de carga manual.",
  size=Pt(8.5), color=RB2)

footer_dark(s); slide_num(s, 8)

# ═══════════════════════════════════════════════════════════════════════════════
# S9 — CIERRE / CALL TO ACTION
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
set_bg_img(s, BGHERO)
hbar_top(s, C['blue2'])

T(s, 0.5, 0.18, 12.3, 0.38, "EL SIGUIENTE PASO", size=Pt(10), bold=True, color=RTL, align=PP_ALIGN.CENTER)

T(s, 0.5, 0.62, 12.3, 1.2,
  "Transformemos IFERSAN\nJuntos",
  size=Pt(46), bold=True, color=RW, align=PP_ALIGN.CENTER)

T(s, 0.5, 2.0, 12.3, 0.42,
  "La arquitectura ya esta lista y funcionando con datos reales.\nEl siguiente paso es llevarlo a la nube para que IFERSAN opere al 100% en tiempo real.",
  size=Pt(13), color=RB2, align=PP_ALIGN.CENTER)

B(s, 4.0, 2.62, 5.33, 0.04, fill=RB2)

# 5 pilares con logos + nombre
pillars = [('kafka','Kafka'),('spark','Spark'),('postgresql','PostgreSQL'),('sklearn','ML'),('grafana','Grafana')]
xp = 1.15
PW = 2.2
for lkey, pname in pillars:
    B(s, xp, 2.82, PW, 1.85, fill=R(10,25,55), border=R(63,131,248), bw=Pt(1.5))
    LOGO(s, lkey, xp+0.27, 2.9, PW-0.54, 1.18)
    T(s, xp, 4.12, PW, 0.42, pname, size=Pt(11), bold=True, color=RW, align=PP_ALIGN.CENTER)
    xp += PW + 0.12

# 6 stats grandes
fin = [("<30s","Latencia"),("30,372","Mensajes"),("16,794","Filas SQL"),("S/406K","Ingresos"),("S/1.6M","ML 2026"),("9","Servicios")]
xf = 0.5
for num, lbl in fin:
    BFW = 2.04
    B(s, xf, 4.72, BFW, 0.88, fill=R(12,28,62), border=R(63,131,248), bw=Pt(1))
    T(s, xf, 4.78, BFW, 0.46, num, size=Pt(20), bold=True, color=RW, align=PP_ALIGN.CENTER)
    T(s, xf, 5.24, BFW, 0.3, lbl, size=Pt(8.5), color=RTL, align=PP_ALIGN.CENTER)
    xf += BFW + 0.08

B(s, 0.5, 5.78, 12.33, 0.04, fill=R(16,42,90))

T(s, 0.5, 5.9, 12.3, 0.3,
  "Universidad Peruana Union  ·  IX Ciclo  ·  Big Data  ·  Unidad II  ·  Docente: Mg. Angel Sullon",
  size=Pt(9.5), color=RTL, align=PP_ALIGN.CENTER)
T(s, 0.5, 6.22, 12.3, 0.28,
  "Pipeline Big Data en Tiempo Real  ·  IFERSAN Distribuidora de Bebidas  ·  Juliaca, Peru  ·  Junio 2026",
  size=Pt(9.5), color=RTL, align=PP_ALIGN.CENTER)
T(s, 0.5, 6.62, 12.3, 0.38,
  "Sistema en produccion con datos reales  ·  30,372 mensajes procesados  ·  S/ 406,018 validados",
  size=Pt(10), bold=True, color=RB2, align=PP_ALIGN.CENTER)

footer_dark(s)

# ── GUARDAR ───────────────────────────────────────────────────────────────────
OUT = r"Z:\Universidad\IXCICLO\BigData\UnidadII\pptx\CasaMarket_LlevaLaNube.pptx"
prs.save(OUT)
f = __import__('os').path.getsize(OUT)
print(f"\nGuardado: {OUT}")
print(f"Tamano: {f//1024} KB  |  Slides: {len(prs.slides)}")

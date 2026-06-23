"""
Genera presentacion profesional PPTX — CasaMarket Big Data Pipeline
Audiencia: tecnico con conocimiento MySQL, para validar arquitectura fase final
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from pptx.enum.dml import MSO_THEME_COLOR
import copy

# ── Paleta de colores ──────────────────────────────────────────────────────────
C_NAVY      = RGBColor(0x0F, 0x23, 0x4A)   # fondo portada
C_BLUE      = RGBColor(0x25, 0x63, 0xEB)   # azul principal
C_BLUE_LT   = RGBColor(0xEF, 0xF6, 0xFF)   # azul muy claro (bg cards)
C_BLUE_MID  = RGBColor(0xBF, 0xDB, 0xFE)   # azul borde
C_GREEN     = RGBColor(0x16, 0xA3, 0x4A)   # verde ok
C_GREEN_LT  = RGBColor(0xF0, 0xFD, 0xF4)
C_KAFKA     = RGBColor(0xE3, 0x4C, 0x26)   # rojo-naranja Kafka
C_KAFKA_LT  = RGBColor(0xFE, 0xF3, 0xEA)
C_SPARK     = RGBColor(0xE2, 0x5A, 0x1C)   # naranja Spark
C_SPARK_LT  = RGBColor(0xFF, 0xF7, 0xED)
C_PG        = RGBColor(0x33, 0x67, 0x91)   # azul PostgreSQL
C_PG_LT     = RGBColor(0xEA, 0xF2, 0xFB)
C_ML        = RGBColor(0x7C, 0x3A, 0xED)   # violeta ML
C_ML_LT     = RGBColor(0xFA, 0xF5, 0xFF)
C_GRF       = RGBColor(0xF4, 0x68, 0x00)   # Grafana naranja
C_GRF_LT    = RGBColor(0xFF, 0xF4, 0xEC)
C_TEAL      = RGBColor(0x08, 0x91, 0xB2)   # docker/teal
C_WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
C_TEXT      = RGBColor(0x0F, 0x17, 0x2A)
C_TEXT2     = RGBColor(0x64, 0x74, 0x8B)
C_BORDER    = RGBColor(0xE2, 0xE8, 0xF0)
C_BG        = RGBColor(0xF8, 0xFA, 0xFC)
C_RED       = RGBColor(0xEF, 0x44, 0x44)
C_RED_LT    = RGBColor(0xFE, 0xF2, 0xF2)

# ── Helpers ───────────────────────────────────────────────────────────────────

def add_rect(slide, l, t, w, h, fill=None, border=None, border_w=Pt(1), radius=None):
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(l), Inches(t), Inches(w), Inches(h)
    )
    shape.line.width = border_w
    if fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    else:
        shape.fill.background()
    if border:
        shape.line.color.rgb = border
    else:
        shape.line.fill.background()
    return shape

def add_textbox(slide, l, t, w, h, text, size=Pt(11), bold=False, color=None, align=PP_ALIGN.LEFT, wrap=True):
    txb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    txb.word_wrap = wrap
    tf = txb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = size
    run.font.bold = bold
    if color:
        run.font.color.rgb = color
    return txb

def add_label(slide, l, t, w, h, text, size=Pt(10), bold=False, color=None, align=PP_ALIGN.LEFT):
    return add_textbox(slide, l, t, w, h, text, size, bold, color, align)

def set_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_line(slide, x1, y1, x2, y2, color=None, w=Pt(1.5)):
    connector = slide.shapes.add_connector(
        1,  # STRAIGHT
        Inches(x1), Inches(y1), Inches(x2), Inches(y2)
    )
    connector.line.width = w
    if color:
        connector.line.color.rgb = color
    return connector

def tag_box(slide, l, t, text, bg, border, text_color, size=Pt(8.5)):
    """Small rounded tag-like box"""
    r = add_rect(slide, l, t, 1.25, 0.26, fill=bg, border=border, border_w=Pt(1))
    add_textbox(slide, l+0.05, t+0.03, 1.15, 0.22, text, size=size, bold=True, color=text_color, align=PP_ALIGN.CENTER)
    return r

def pipeline_block(slide, l, t, label, sublabel, bg, border, text_color):
    """One stage block in the pipeline"""
    add_rect(slide, l, t, 1.45, 0.75, fill=bg, border=border, border_w=Pt(1.5))
    add_textbox(slide, l+0.05, t+0.1, 1.35, 0.3, label, size=Pt(9), bold=True, color=text_color, align=PP_ALIGN.CENTER)
    add_textbox(slide, l+0.05, t+0.38, 1.35, 0.28, sublabel, size=Pt(7.5), bold=False, color=C_TEXT2, align=PP_ALIGN.CENTER)

def section_header(slide, icon_char, title, subtitle, icon_bg=None):
    """Top header bar with icon + title"""
    if icon_bg is None:
        icon_bg = C_BLUE
    add_rect(slide, 0.4, 0.25, 0.45, 0.45, fill=icon_bg, border=None)
    add_textbox(slide, 0.4, 0.27, 0.45, 0.4, icon_char, size=Pt(16), bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_textbox(slide, 0.95, 0.25, 8.5, 0.28, title, size=Pt(16), bold=True, color=C_TEXT)
    add_textbox(slide, 0.95, 0.52, 8.5, 0.22, subtitle, size=Pt(9), bold=False, color=C_TEXT2)

def card(slide, l, t, w, h, title, body_lines, title_color=None, icon=None, icon_bg=None):
    """Card with title + body text"""
    add_rect(slide, l, t, w, h, fill=C_WHITE, border=C_BORDER, border_w=Pt(1))
    y = t + 0.14
    if icon and icon_bg:
        add_rect(slide, l+0.14, t+0.14, 0.3, 0.3, fill=icon_bg, border=None)
        add_textbox(slide, l+0.14, t+0.14, 0.3, 0.3, icon, size=Pt(11), bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
        tx = l + 0.52
        tw = w - 0.6
        add_textbox(slide, tx, t+0.14, tw, 0.28, title, size=Pt(10), bold=True, color=title_color or C_TEXT)
        y = t + 0.5
    else:
        add_textbox(slide, l+0.16, t+0.14, w-0.3, 0.28, title, size=Pt(10), bold=True, color=title_color or C_TEXT)
        y = t + 0.44
    for line in body_lines:
        add_textbox(slide, l+0.16, y, w-0.3, 0.22, line, size=Pt(8.5), bold=False, color=C_TEXT2)
        y += 0.22

def kv_row(slide, l, t, w, key, val, key_color=None, val_color=None):
    half = (w - 0.05) / 2
    add_rect(slide, l, t, half, 0.28, fill=C_BG, border=C_BORDER, border_w=Pt(0.75))
    add_textbox(slide, l+0.08, t+0.04, half-0.1, 0.22, key, size=Pt(8.5), bold=True, color=key_color or C_TEXT)
    add_rect(slide, l+half+0.05, t, half, 0.28, fill=C_WHITE, border=C_BORDER, border_w=Pt(0.75))
    add_textbox(slide, l+half+0.13, t+0.04, half-0.1, 0.22, val, size=Pt(8.5), bold=False, color=val_color or C_TEXT2)

def stat_box(slide, l, t, number, label, num_color=None):
    add_rect(slide, l, t, 1.5, 0.9, fill=C_WHITE, border=C_BORDER, border_w=Pt(1))
    add_textbox(slide, l, t+0.1, 1.5, 0.45, number, size=Pt(22), bold=True, color=num_color or C_BLUE, align=PP_ALIGN.CENTER)
    add_textbox(slide, l, t+0.55, 1.5, 0.3, label, size=Pt(8), bold=False, color=C_TEXT2, align=PP_ALIGN.CENTER)

# ── Presentacion ──────────────────────────────────────────────────────────────

prs = Presentation()
prs.slide_width  = Inches(10)
prs.slide_height = Inches(7.5)

blank_layout = prs.slide_layouts[6]  # blank

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — PORTADA
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s, C_NAVY)

# Franja decorativa superior
add_rect(s, 0, 0, 10, 0.06, fill=C_BLUE, border=None)

# Franja lateral izquierda
add_rect(s, 0, 0.06, 0.06, 7.44, fill=C_BLUE, border=None)

# Logo / icon empresa
add_rect(s, 0.55, 0.7, 1.0, 1.0, fill=C_BLUE, border=None)
add_textbox(s, 0.55, 0.7, 1.0, 1.0, "I", size=Pt(36), bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)

# Nombre empresa
add_textbox(s, 1.7, 0.72, 7.5, 0.65, "IFERSAN", size=Pt(42), bold=True, color=C_WHITE)
add_textbox(s, 1.7, 1.35, 7.5, 0.3, "Distribuidora de Bebidas  |  Juliaca, Peru", size=Pt(11), bold=False, color=RGBColor(0x94, 0xA3, 0xB8))

# Linea divisora
add_rect(s, 0.55, 2.0, 9.1, 0.03, fill=RGBColor(0x1E, 0x40, 0xAF), border=None)

# Titulo principal
add_textbox(s, 0.55, 2.15, 9.1, 0.7, "Pipeline Big Data en Tiempo Real", size=Pt(28), bold=True, color=C_WHITE)
add_textbox(s, 0.55, 2.85, 9.1, 0.4, "Arquitectura Kappa  |  Del ERP al Dashboard en menos de 30 segundos", size=Pt(13), bold=False, color=RGBColor(0xBF, 0xDB, 0xFE))

# Tags tecnologias
tags = [
    ("Kafka 3.7",     C_KAFKA,  C_KAFKA_LT),
    ("Spark 3.5",     C_SPARK,  C_SPARK_LT),
    ("PostgreSQL 16", C_PG,     C_PG_LT),
    ("Scikit-learn",  C_ML,     C_ML_LT),
    ("Grafana",       C_GRF,    C_GRF_LT),
    ("Docker",        C_TEAL,   RGBColor(0xE0, 0xF7, 0xFA)),
]
x_tag = 0.55
for label, tc, bg in tags:
    w_tag = len(label) * 0.085 + 0.35
    add_rect(s, x_tag, 3.45, w_tag, 0.32, fill=RGBColor(0x1E, 0x3A, 0x8A), border=RGBColor(0x3B, 0x82, 0xF6), border_w=Pt(1))
    add_textbox(s, x_tag+0.05, 3.48, w_tag-0.1, 0.26, label, size=Pt(9), bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    x_tag += w_tag + 0.15

# Mini pipeline visual
stages = [
    ("ERP Web",       "API REST",       RGBColor(0x1E, 0x40, 0xAF)),
    ("Kafka",         "Broker",         C_KAFKA),
    ("Spark",         "Streaming",      C_SPARK),
    ("PostgreSQL",    "Storage",        C_PG),
    ("ML",            "Prediccion",     C_ML),
    ("Grafana",       "Dashboard",      C_GRF),
]
add_rect(s, 0.55, 3.95, 9.1, 1.15, fill=RGBColor(0x0A, 0x14, 0x2E), border=RGBColor(0x1E, 0x40, 0xAF), border_w=Pt(1))
xb = 0.75
for i, (name, sub, col) in enumerate(stages):
    bw = 1.2
    add_rect(s, xb, 4.1, bw, 0.82, fill=col, border=None)
    add_textbox(s, xb, 4.15, bw, 0.38, name, size=Pt(10), bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_textbox(s, xb, 4.5, bw, 0.3, sub, size=Pt(8), bold=False, color=RGBColor(0xFF, 0xFF, 0xFF), align=PP_ALIGN.CENTER)
    if i < len(stages) - 1:
        add_textbox(s, xb + bw + 0.02, 4.35, 0.2, 0.3, ">", size=Pt(12), bold=True, color=RGBColor(0x94, 0xA3, 0xB8), align=PP_ALIGN.CENTER)
    xb += bw + 0.25

# Stats fila
stats = [("11", "Servicios Docker"), ("30,372", "Mensajes Kafka"), ("S/ 406K", "Ingresos reales"), ("S/ 1.6M", "Proyeccion 2026")]
xs = 0.55
for num, lbl in stats:
    bw = 2.1
    add_rect(s, xs, 5.3, bw, 0.72, fill=RGBColor(0x1E, 0x3A, 0x8A), border=RGBColor(0x3B, 0x82, 0xF6), border_w=Pt(1))
    add_textbox(s, xs, 5.32, bw, 0.38, num, size=Pt(18), bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_textbox(s, xs, 5.68, bw, 0.28, lbl, size=Pt(8.5), bold=False, color=RGBColor(0x93, 0xC5, 0xFD), align=PP_ALIGN.CENTER)
    xs += bw + 0.12

# Footer
add_textbox(s, 0.55, 6.18, 9.1, 0.25, "Universidad Peruana Union  |  IX Ciclo - Big Data - Unidad II  |  Docente: Mg. Angel Sullon", size=Pt(8), bold=False, color=RGBColor(0x64, 0x74, 0x8B), align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — EL CONTEXTO: DE MYSQL A TIEMPO REAL
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s, C_BG)
add_rect(s, 0, 0, 10, 0.06, fill=C_BLUE, border=None)
section_header(s, "C", "El Contexto: Partimos de una Base de Datos Relacional", "La empresa ya tiene MySQL — el reto es ir mas alla sin reemplazarlo todo", icon_bg=C_TEAL)

# Columna izq: situacion actual
add_rect(s, 0.35, 0.85, 4.35, 5.8, fill=C_WHITE, border=C_BORDER)
add_textbox(s, 0.55, 0.95, 3.95, 0.3, "Situacion Actual (lo que conocen)", size=Pt(11), bold=True, color=C_TEXT)

items_actual = [
    ("Base de Datos ERP", "MySQL / MariaDB detras del sistema CasaMarket.\nEstructura relacional: ventas, clientes, productos."),
    ("Acceso a datos", "Reportes exportados como .xlsx desde el ERP web.\nDescarga manual o programada por el equipo."),
    ("Consultas conocidas", "SELECT, JOIN, GROUP BY — logica SQL clasica.\nAgregados por fecha, producto, vendedor."),
    ("Herramienta actual", "Excel + tablas dinamicas para analizar.\nNo hay dashboard en tiempo real."),
]
y = 1.38
for title, desc in items_actual:
    add_rect(s, 0.45, y, 4.1, 0.75, fill=C_BG, border=C_BORDER, border_w=Pt(0.75))
    add_textbox(s, 0.6, y+0.05, 3.8, 0.25, title, size=Pt(9.5), bold=True, color=C_TEXT)
    add_textbox(s, 0.6, y+0.3, 3.8, 0.38, desc, size=Pt(8), bold=False, color=C_TEXT2)
    y += 0.88

# Columna der: lo que se necesita ahora
add_rect(s, 4.9, 0.85, 4.75, 5.8, fill=C_WHITE, border=C_BORDER)
add_textbox(s, 5.1, 0.95, 4.4, 0.3, "Que Necesita el Negocio Ahora", size=Pt(11), bold=True, color=C_TEXT)

items_need = [
    (C_RED,   "X", "Sin visibilidad en tiempo real", "Un gerente no puede ver cuanto vendieron HOY mientras el dia avanza."),
    (C_RED,   "X", "Sin alertas automaticas",        "Si un vendedor no vende en 3 horas, nadie lo sabe hasta el cierre."),
    (C_RED,   "X", "Sin proyecciones futuras",       "No hay forma de saber si diciembre sera bueno o malo con anticipacion."),
    (C_GREEN, "V", "Pipeline en tiempo real",         "Cada venta aparece en el dashboard en menos de 30 segundos."),
    (C_GREEN, "V", "Predicciones ML para 2026",      "Proyeccion de S/ 1,614,943 basada en datos reales del ERP."),
]
y = 1.38
for col, sym, title, desc in items_need:
    bg = C_GREEN_LT if sym == "V" else C_RED_LT
    br = C_GREEN if sym == "V" else C_RED
    add_rect(s, 5.0, y, 4.5, 0.9, fill=bg, border=br, border_w=Pt(1))
    add_rect(s, 5.08, y+0.28, 0.28, 0.28, fill=col, border=None)
    add_textbox(s, 5.08, y+0.28, 0.28, 0.28, sym, size=Pt(10), bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_textbox(s, 5.44, y+0.07, 3.9, 0.25, title, size=Pt(9.5), bold=True, color=C_TEXT)
    add_textbox(s, 5.44, y+0.33, 3.9, 0.45, desc, size=Pt(8), bold=False, color=C_TEXT2)
    y += 1.02

add_rect(s, 0, 7.22, 10, 0.28, fill=C_NAVY, border=None)
add_textbox(s, 0, 7.24, 10, 0.22, "  CasaMarket Big Data Pipeline  |  IFERSAN Juliaca", size=Pt(8), bold=False, color=RGBColor(0x94, 0xA3, 0xB8))

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — POR QUE ESTA ARQUITECTURA Y NO SOLO MySQL
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s, C_BG)
add_rect(s, 0, 0, 10, 0.06, fill=C_BLUE, border=None)
section_header(s, "?", "Por Que Esta Arquitectura — y No Solo MySQL/SQL", "MySQL sigue presente. Esta arquitectura lo complementa para procesar datos en tiempo real", icon_bg=C_BLUE)

# Tabla comparativa
col_w = [2.5, 3.2, 3.2]
headers = ["Capacidad", "MySQL solo", "Pipeline Kappa (esta solucion)"]
rows = [
    ("Latencia de datos",    "Horas (reporte manual)",    "< 30 segundos (automatico)"),
    ("Volumen por dia",      "Limitado por disco/RAM",    "Ilimitado via Kafka + Parquet"),
    ("Procesamiento",        "Batch nocturno / manual",   "Streaming continuo 24/7"),
    ("Predicciones ML",      "No nativo",                 "Integrado — 180 predicciones"),
    ("Alertas en tiempo real","Ninguna",                   "2 alertas automaticas activas"),
    ("Dashboard en vivo",    "No incluido",               "Grafana con refresh cada 15s"),
    ("Tolerancia a fallos",  "Single point of failure",   "Checkpoint Kafka — at-least-once"),
    ("Escalabilidad",        "Vertical (mas hardware)",   "Horizontal (mas brokers/workers)"),
]
x0 = 0.35
y0 = 0.92
# header
for i, (h, w) in enumerate(zip(headers, col_w)):
    bg = C_NAVY if i == 0 else (C_RED_LT if i == 1 else C_BLUE_LT)
    fc = C_WHITE if i == 0 else (C_RED if i == 1 else C_BLUE)
    add_rect(s, x0 + sum(col_w[:i]) + i*0.04, y0, w, 0.35, fill=bg, border=C_BORDER)
    add_textbox(s, x0 + sum(col_w[:i]) + i*0.04 + 0.1, y0+0.06, w-0.15, 0.24, h, size=Pt(9.5), bold=True, color=fc)

y0 += 0.35
for ri, row in enumerate(rows):
    bg_row = C_BG if ri % 2 == 0 else C_WHITE
    for ci, (cell, w) in enumerate(zip(row, col_w)):
        bg = bg_row
        fc = C_TEXT
        if ci == 1 and ("No " in cell or "manual" in cell or "Ninguna" in cell or "Single" in cell or "Vertical" in cell or "Limitado" in cell or "Horas" in cell):
            fc = C_RED
        if ci == 2:
            fc = C_GREEN
        add_rect(s, x0 + sum(col_w[:ci]) + ci*0.04, y0, w, 0.52, fill=bg, border=C_BORDER, border_w=Pt(0.5))
        add_textbox(s, x0 + sum(col_w[:ci]) + ci*0.04 + 0.1, y0+0.1, w-0.18, 0.35, cell, size=Pt(8.5), bold=(ci==0), color=fc)
    y0 += 0.52

# Nota al pie
add_rect(s, 0.35, y0+0.1, 9.2, 0.42, fill=C_BLUE_LT, border=C_BLUE_MID)
add_textbox(s, 0.55, y0+0.16, 8.8, 0.32, "Nota tecnica: PostgreSQL reemplaza a MySQL en la capa de almacenamiento. La sintaxis SQL es compatible — GROUP BY, JOIN, SUM funcionan igual. El cambio real es que ahora los datos llegan continuamente via Spark JDBC.", size=Pt(8.5), bold=False, color=C_BLUE)

add_rect(s, 0, 7.22, 10, 0.28, fill=C_NAVY, border=None)
add_textbox(s, 0, 7.24, 10, 0.22, "  CasaMarket Big Data Pipeline  |  IFERSAN Juliaca", size=Pt(8), bold=False, color=RGBColor(0x94, 0xA3, 0xB8))

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — ARQUITECTURA GENERAL (DIAGRAMA)
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s, C_BG)
add_rect(s, 0, 0, 10, 0.06, fill=C_BLUE, border=None)
section_header(s, "D", "Arquitectura General — Pipeline Kappa", "6 capas de procesamiento: desde el ERP hasta el dashboard en vivo", icon_bg=C_ML)

# Caja de fondo del pipeline
add_rect(s, 0.3, 0.88, 9.4, 5.0, fill=C_WHITE, border=C_BORDER)

# Etiquetas de capas
layer_labels = ["FUENTE", "INGESTA", "BROKER", "PROCESO", "STORAGE + ML", "VISUAL"]
layer_x      = [0.42, 1.97, 3.52, 5.07, 6.62, 8.45]
layer_w      = [1.4,  1.4,  1.4,  1.4,  1.65, 1.2 ]
for lbl, lx, lw in zip(layer_labels, layer_x, layer_w):
    add_rect(s, lx, 0.95, lw, 0.28, fill=C_NAVY, border=None)
    add_textbox(s, lx, 0.95, lw, 0.28, lbl, size=Pt(7.5), bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)

# ── Fila 1: Flujo principal ──
blocks_row1 = [
    (0.42, "ERP Web",        "admin.casamarket.la\nAPI REST + JWT",    C_BLUE_LT,  C_BLUE_MID, C_BLUE),
    (1.97, "Producer.py",    "Detecta Excel\npublish a Kafka",         C_SPARK_LT, C_KAFKA_LT, C_SPARK),
    (3.52, "Apache Kafka",   "Topic: ventas.raw\n30,372 mensajes",     C_KAFKA_LT, RGBColor(0xFB,0xD4,0xBE), C_KAFKA),
    (5.07, "Spark Streaming","Micro-batch 30s\n3 queries paralelas",   C_SPARK_LT, RGBColor(0xFE,0xD7,0xAA), C_SPARK),
    (6.62, "PostgreSQL 16",  "Tabla ventas\n16,794 filas",             C_PG_LT,    RGBColor(0xBD,0xD7,0xF5), C_PG),
    (8.45, "Grafana",        "Dashboard ventas\n29 paneles",           C_GRF_LT,   RGBColor(0xFD,0xD9,0xBC), C_GRF),
]
for lx, name, desc, bg, br, tc in blocks_row1:
    add_rect(s, lx, 1.35, 1.4 if lx < 8 else 1.2, 1.05, fill=bg, border=br, border_w=Pt(1.5))
    add_textbox(s, lx+0.06, 1.38, 1.28, 0.32, name, size=Pt(9.5), bold=True, color=tc, align=PP_ALIGN.CENTER)
    add_textbox(s, lx+0.06, 1.7,  1.28, 0.62, desc, size=Pt(7.5), bold=False, color=C_TEXT2, align=PP_ALIGN.CENTER)

# Flechas fila 1
arrow_positions = [(1.82, 2.2, 0.15), (3.37, 2.2, 0.15), (4.92, 2.2, 0.15), (6.47, 2.2, 0.15), (8.02, 2.2, 0.43)]
for ax, ay, aw in arrow_positions:
    add_textbox(s, ax, ay-0.12, aw, 0.28, ">", size=Pt(13), bold=True, color=C_TEXT2, align=PP_ALIGN.CENTER)

# ── Fila 2: Flujo documentos ──
add_rect(s, 1.97, 2.6, 1.4, 0.95, fill=C_SPARK_LT, border=RGBColor(0xFE,0xD7,0xAA), border_w=Pt(1.5))
add_textbox(s, 2.03, 2.63, 1.28, 0.3, "Excel Parser", size=Pt(9.5), bold=True, color=C_SPARK, align=PP_ALIGN.CENTER)
add_textbox(s, 2.03, 2.93, 1.28, 0.55, "Lee filas .xlsx\nconvierte a JSON", size=Pt(7.5), bold=False, color=C_TEXT2, align=PP_ALIGN.CENTER)

add_rect(s, 3.52, 2.6, 1.4, 0.95, fill=C_KAFKA_LT, border=RGBColor(0xFB,0xD4,0xBE), border_w=Pt(1.5))
add_textbox(s, 3.58, 2.63, 1.28, 0.3, "Kafka Topic #2", size=Pt(9.5), bold=True, color=C_KAFKA, align=PP_ALIGN.CENTER)
add_textbox(s, 3.58, 2.93, 1.28, 0.55, "documento.detectado\n173 mensajes", size=Pt(7.5), bold=False, color=C_TEXT2, align=PP_ALIGN.CENTER)

add_rect(s, 5.07, 2.6, 1.4, 0.95, fill=C_SPARK_LT, border=RGBColor(0xFE,0xD7,0xAA), border_w=Pt(1.5))
add_textbox(s, 5.13, 2.63, 1.28, 0.3, "Spark job_docs", size=Pt(9.5), bold=True, color=C_SPARK, align=PP_ALIGN.CENTER)
add_textbox(s, 5.13, 2.93, 1.28, 0.55, "Ventanas 5min\nParquet metricas", size=Pt(7.5), bold=False, color=C_TEXT2, align=PP_ALIGN.CENTER)

# Flechas fila 2
for ax in [3.37, 4.92]:
    add_textbox(s, ax, 2.93, 0.15, 0.28, ">", size=Pt(13), bold=True, color=C_TEXT2, align=PP_ALIGN.CENTER)

# ── Fila 3: ML y Observabilidad ──
add_rect(s, 6.62, 2.6, 1.65, 0.95, fill=C_ML_LT, border=RGBColor(0xDD,0xD6,0xFE), border_w=Pt(1.5))
add_textbox(s, 6.68, 2.63, 1.53, 0.3, "ML — sklearn", size=Pt(9.5), bold=True, color=C_ML, align=PP_ALIGN.CENTER)
add_textbox(s, 6.68, 2.93, 1.53, 0.55, "LinearRegression\nS/ 1.6M proyectados", size=Pt(7.5), bold=False, color=C_TEXT2, align=PP_ALIGN.CENTER)

# Flecha PG -> ML
add_textbox(s, 7.08, 2.45, 0.55, 0.22, "V", size=Pt(11), bold=True, color=C_ML, align=PP_ALIGN.CENTER)

# ── Fila 4: Observabilidad ──
add_rect(s, 3.52, 3.72, 1.4, 0.85, fill=C_RED_LT, border=RGBColor(0xFE,0xCA,0xCA), border_w=Pt(1.5))
add_textbox(s, 3.58, 3.75, 1.28, 0.3, "Kafka Exporter", size=Pt(9), bold=True, color=C_RED, align=PP_ALIGN.CENTER)
add_textbox(s, 3.58, 4.03, 1.28, 0.45, ":9308/metrics\nscraping 15s", size=Pt(7.5), bold=False, color=C_TEXT2, align=PP_ALIGN.CENTER)

add_rect(s, 5.07, 3.72, 1.4, 0.85, fill=C_RED_LT, border=RGBColor(0xFE,0xCA,0xCA), border_w=Pt(1.5))
add_textbox(s, 5.13, 3.75, 1.28, 0.3, "Prometheus", size=Pt(9), bold=True, color=C_RED, align=PP_ALIGN.CENTER)
add_textbox(s, 5.13, 4.03, 1.28, 0.45, "TSDB :9090\nPromQL", size=Pt(7.5), bold=False, color=C_TEXT2, align=PP_ALIGN.CENTER)

add_textbox(s, 3.37, 4.08, 0.15, 0.28, ">", size=Pt(11), bold=True, color=C_TEXT2, align=PP_ALIGN.CENTER)
add_textbox(s, 4.92, 4.08, 0.15, 0.28, ">", size=Pt(11), bold=True, color=C_TEXT2, align=PP_ALIGN.CENTER)

# Etiqueta Grafana tambien recibe Prometheus
add_textbox(s, 8.0, 3.75, 1.65, 0.28, "< metricas infra", size=Pt(7.5), bold=False, color=C_TEXT2)

# Leyenda
add_rect(s, 0.35, 5.05, 9.2, 0.65, fill=C_BG, border=C_BORDER)
legend_items = [
    (C_BLUE,  "Datos de negocio (ventas)"),
    (C_KAFKA, "Mensajeria / broker"),
    (C_ML,    "Machine learning"),
    (C_RED,   "Observabilidad / infra"),
]
xl = 0.55
for col, lbl in legend_items:
    add_rect(s, xl, 5.2, 0.18, 0.18, fill=col, border=None)
    add_textbox(s, xl+0.23, 5.18, 1.8, 0.22, lbl, size=Pt(8), bold=False, color=C_TEXT2)
    xl += 2.25

add_rect(s, 0, 7.22, 10, 0.28, fill=C_NAVY, border=None)
add_textbox(s, 0, 7.24, 10, 0.22, "  CasaMarket Big Data Pipeline  |  IFERSAN Juliaca", size=Pt(8), bold=False, color=RGBColor(0x94, 0xA3, 0xB8))

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — INGESTA: ERP → KAFKA
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s, C_BG)
add_rect(s, 0, 0, 10, 0.06, fill=C_BLUE, border=None)
section_header(s, "1", "Capa 1: Ingesta de Datos — Del ERP a Kafka", "Producer Python detecta nuevos Excel cada 60s y los publica como mensajes JSON", icon_bg=C_KAFKA)

# Paso a paso
steps = [
    (C_BLUE,  "1", "Autenticacion JWT contra el ERP",
     "POST https://acl.casamarketapp.com/api/authenticate\nBody: {\"email\": \"...\", \"password\": \"...\", \"codeApp\": \"quipuadmin\"}\nResponse: token JWT con duracion de sesion"),
    (C_TEAL,  "2", "Descarga de reportes Excel (.xlsx)",
     "GET https://n5.report.casamarketapp.com/documents\nParams: startDate, endDate, limit, page\nHeader: Authorization: Bearer <token>"),
    (C_SPARK, "3", "Parsing del archivo Excel",
     "consumer_excel_parser.py lee cada fila del .xlsx\nConvierte a JSON: fecha, producto, marca, cantidad, total, cliente, vendedor\nPublica al topic casamarket.ventas.raw"),
    (C_KAFKA, "4", "Kafka recibe el mensaje",
     "Topic: casamarket.ventas.raw\nBroker: localhost:19092 (KRaft, sin ZooKeeper)\nEstado actual: 30,372 mensajes, LAG = 0"),
]
y = 0.92
for col, num, title, desc in steps:
    add_rect(s, 0.35, y, 9.2, 1.2, fill=C_WHITE, border=C_BORDER)
    add_rect(s, 0.35, y, 0.42, 1.2, fill=col, border=None)
    add_textbox(s, 0.35, y+0.4, 0.42, 0.4, num, size=Pt(18), bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_textbox(s, 0.88, y+0.08, 8.5, 0.3, title, size=Pt(11), bold=True, color=C_TEXT)
    add_textbox(s, 0.88, y+0.4, 8.5, 0.72, desc, size=Pt(8.5), bold=False, color=C_TEXT2)
    y += 1.3

# JSON sample
add_rect(s, 0.35, y+0.05, 9.2, 0.98, fill=RGBColor(0x1E, 0x29, 0x3B), border=C_BORDER)
add_textbox(s, 0.55, y+0.08, 9.0, 0.22, "Mensaje real publicado en ventas.raw:", size=Pt(8.5), bold=True, color=RGBColor(0x94,0xA3,0xB8))
add_textbox(s, 0.55, y+0.28, 9.0, 0.65,
    '{  "fecha": "2026-05-15",  "producto": "PEPSI 2000ML",  "cantidad": "24",  "total": "288.00",  "cliente": "BOTICA SAN PABLO",  "vendedor": "ROSA CUSILAYME"  }',
    size=Pt(8.5), bold=False, color=RGBColor(0x86, 0xEF, 0xAC))

add_rect(s, 0, 7.22, 10, 0.28, fill=C_NAVY, border=None)
add_textbox(s, 0, 7.24, 10, 0.22, "  CasaMarket Big Data Pipeline  |  IFERSAN Juliaca", size=Pt(8), bold=False, color=RGBColor(0x94, 0xA3, 0xB8))

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — KAFKA + SPARK
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s, C_BG)
add_rect(s, 0, 0, 10, 0.06, fill=C_BLUE, border=None)
section_header(s, "2", "Capas 2 y 3: Kafka como Bus de Datos + Spark Streaming", "Kafka desacopla produccion y consumo. Spark procesa en micro-batches de 30 segundos.", icon_bg=C_KAFKA)

# Columna Kafka
add_rect(s, 0.35, 0.88, 4.5, 5.9, fill=C_WHITE, border=C_BORDER)
add_rect(s, 0.35, 0.88, 4.5, 0.38, fill=C_KAFKA, border=None)
add_textbox(s, 0.45, 0.9, 4.3, 0.32, "Apache Kafka 3.7 — KRaft", size=Pt(11), bold=True, color=C_WHITE)

kafka_items = [
    ("Que es Kafka para un DBA",  "Una cola de mensajes persistente. Como una tabla de log que nunca borra sus filas y que multiples consumidores pueden leer de forma independiente."),
    ("Por que no INSERT directo", "MySQL/PostgreSQL con INSERTs directos desde el ERP crea acoplamiento. Si la DB cae, se pierden datos. Kafka actua como buffer: guarda hasta que Spark esta listo."),
    ("Topics activos",            "casamarket.ventas.raw   ->  30,372 msgs  LAG 0\ncasamarket.documento.detectado  ->  173 msgs  LAG 0"),
    ("Modo KRaft",                "Kafka 3.7 sin ZooKeeper. El cluster maneja su propio consenso. Menos componentes = menos puntos de fallo."),
    ("Acceso visual",             "Kafka UI: http://localhost:18085\nPuerto broker: 19092 (externo)"),
]
y = 1.38
for title, desc in kafka_items:
    add_rect(s, 0.45, y, 4.25, 0.88, fill=C_BG, border=C_KAFKA_LT, border_w=Pt(0.75))
    add_textbox(s, 0.58, y+0.06, 3.98, 0.26, title, size=Pt(9), bold=True, color=C_TEXT)
    add_textbox(s, 0.58, y+0.32, 3.98, 0.5, desc, size=Pt(7.8), bold=False, color=C_TEXT2)
    y += 0.98

# Columna Spark
add_rect(s, 5.05, 0.88, 4.6, 5.9, fill=C_WHITE, border=C_BORDER)
add_rect(s, 5.05, 0.88, 4.6, 0.38, fill=C_SPARK, border=None)
add_textbox(s, 5.15, 0.9, 4.4, 0.32, "Apache Spark 3.5 — Structured Streaming", size=Pt(11), bold=True, color=C_WHITE)

# Query table Spark
queries = [
    ("Q1 — Parquet",     "Escribe ventas/ en formato columnar (analisis futuro)", C_GREEN),
    ("Q2 — PostgreSQL",  "INSERT via JDBC a tabla ventas (Grafana la lee en vivo)", C_PG),
    ("Q3 — Consola",     "Top 15 productos por ingreso (monitoreo operativo)", C_TEXT2),
]
y = 1.38
for qname, qdesc, qc in queries:
    add_rect(s, 5.15, y, 4.35, 0.58, fill=C_BG, border=C_BORDER, border_w=Pt(0.75))
    add_textbox(s, 5.25, y+0.06, 4.1, 0.25, qname, size=Pt(9), bold=True, color=qc)
    add_textbox(s, 5.25, y+0.3, 4.1, 0.22, qdesc, size=Pt(8), bold=False, color=C_TEXT2)
    y += 0.66

# Parametros
spark_params = [
    ("Trigger",      "30 segundos",  "Latencia baja sin saturar la DB"),
    ("Watermark",    "10 minutos",   "Tolera mensajes que llegan tarde"),
    ("Ventanas",     "5 minutos",    "Agrupacion temporal para metricas"),
    ("Checkpoint",   "Disco local",  "At-least-once: si cae, retoma"),
    ("Particiones",  "2",            "Optimo para modo local de desarrollo"),
]
add_textbox(s, 5.15, y+0.1, 4.3, 0.25, "Parametros de configuracion:", size=Pt(9), bold=True, color=C_TEXT)
y += 0.38
for param, val, reason in spark_params:
    add_rect(s, 5.15, y, 4.35, 0.42, fill=C_WHITE, border=C_BORDER, border_w=Pt(0.5))
    add_textbox(s, 5.22, y+0.06, 1.1, 0.3, param, size=Pt(8), bold=True, color=C_TEXT)
    add_textbox(s, 6.38, y+0.06, 0.8, 0.3, val, size=Pt(8), bold=True, color=C_BLUE)
    add_textbox(s, 7.22, y+0.06, 2.2, 0.3, reason, size=Pt(7.5), bold=False, color=C_TEXT2)
    y += 0.46

add_rect(s, 0, 7.22, 10, 0.28, fill=C_NAVY, border=None)
add_textbox(s, 0, 7.24, 10, 0.22, "  CasaMarket Big Data Pipeline  |  IFERSAN Juliaca", size=Pt(8), bold=False, color=RGBColor(0x94, 0xA3, 0xB8))

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — POSTGRESQL + ML
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s, C_BG)
add_rect(s, 0, 0, 10, 0.06, fill=C_BLUE, border=None)
section_header(s, "4", "Capas 4 y 5: PostgreSQL + Machine Learning", "PostgreSQL es la fuente de verdad. ML proyecta ventas 2026 usando datos reales.", icon_bg=C_PG)

# Columna PG
add_rect(s, 0.35, 0.88, 4.5, 5.9, fill=C_WHITE, border=C_BORDER)
add_rect(s, 0.35, 0.88, 4.5, 0.38, fill=C_PG, border=None)
add_textbox(s, 0.45, 0.9, 4.3, 0.32, "PostgreSQL 16  |  Puerto 15432", size=Pt(11), bold=True, color=C_WHITE)

# Schema tabla ventas
add_textbox(s, 0.45, 1.38, 4.3, 0.25, "Tabla: ventas  (16,794 filas  |  S/ 406,018)", size=Pt(9.5), bold=True, color=C_PG)
schema_ventas = [
    ("id",            "SERIAL PK",   "Identificador unico"),
    ("fecha",         "DATE",        "Fecha de la venta"),
    ("producto",      "TEXT",        "Nombre del producto"),
    ("marca",         "TEXT",        "Marca (PEPSI, PILSEN...)"),
    ("categoria",     "TEXT",        "Categoria de producto"),
    ("cantidad",      "NUMERIC",     "Unidades vendidas"),
    ("total",         "NUMERIC",     "Ingreso en soles S/"),
    ("cliente",       "TEXT",        "Nombre del cliente"),
    ("vendedor",      "TEXT",        "Nombre del vendedor"),
    ("procesado_ts",  "TIMESTAMPTZ", "Timestamp Spark"),
]
y = 1.68
for col_name, tipo, desc in schema_ventas:
    add_rect(s, 0.45, y, 4.25, 0.3, fill=C_BG if schema_ventas.index((col_name, tipo, desc)) % 2 == 0 else C_WHITE, border=C_BORDER, border_w=Pt(0.5))
    add_textbox(s, 0.55, y+0.04, 1.1, 0.22, col_name, size=Pt(8), bold=True, color=C_TEXT)
    add_textbox(s, 1.7,  y+0.04, 0.9, 0.22, tipo, size=Pt(7.8), bold=False, color=C_BLUE)
    add_textbox(s, 2.65, y+0.04, 1.95, 0.22, desc, size=Pt(7.5), bold=False, color=C_TEXT2)
    y += 0.3

# Query Grafana
add_rect(s, 0.45, y+0.08, 4.25, 0.88, fill=RGBColor(0x1E, 0x29, 0x3B), border=C_BORDER)
add_textbox(s, 0.55, y+0.1, 4.1, 0.22, "Query para Grafana (compatible MySQL):", size=Pt(8), bold=True, color=RGBColor(0x94,0xA3,0xB8))
add_textbox(s, 0.55, y+0.3, 4.1, 0.6,
    "SELECT fecha::TIMESTAMPTZ AS time,\n       ROUND(SUM(total)::NUMERIC,2) AS \"Ingresos S/\"\nFROM ventas  WHERE total > 0\nGROUP BY fecha  ORDER BY fecha",
    size=Pt(7.8), bold=False, color=RGBColor(0x86, 0xEF, 0xAC))

# Columna ML
add_rect(s, 5.05, 0.88, 4.6, 5.9, fill=C_WHITE, border=C_BORDER)
add_rect(s, 5.05, 0.88, 4.6, 0.38, fill=C_ML, border=None)
add_textbox(s, 5.15, 0.9, 4.4, 0.32, "Machine Learning — Scikit-learn", size=Pt(11), bold=True, color=C_WHITE)

add_textbox(s, 5.15, 1.38, 4.4, 0.25, "Modelo: LinearRegression por producto", size=Pt(9.5), bold=True, color=C_ML)
add_textbox(s, 5.15, 1.65, 4.4, 0.22, "y = B0 + B1 * mes_ordinal  (trend mensual)", size=Pt(8.5), bold=False, color=C_TEXT2)

# Tabla Top 5
predictions = [
    ("PEPSI 2000ML",         "S/ 334,800"),
    ("ESCOCESA 2250ml",      "S/ 281,664"),
    ("PILSEN CALLAO 620ml",  "S/ 198,000"),
    ("GUARANA BRASIL 3lt",   "S/ 156,000"),
    ("VIVA BACKUS 620ml",    "S/ 148,200"),
    ("TOP 15 TOTAL",         "S/ 1,614,943"),
]
add_textbox(s, 5.15, 1.95, 4.4, 0.25, "Proyeccion anual 2026 — Top 5 productos:", size=Pt(9), bold=True, color=C_TEXT)
y = 2.25
for prod, monto in predictions:
    is_total = "TOTAL" in prod
    bg = C_BLUE_LT if is_total else (C_BG if predictions.index((prod, monto)) % 2 == 0 else C_WHITE)
    fc_val = C_BLUE if is_total else C_GREEN
    fw_val = True
    add_rect(s, 5.15, y, 4.35, 0.36, fill=bg, border=C_BORDER, border_w=Pt(0.5 if not is_total else 1.0))
    add_textbox(s, 5.24, y+0.06, 2.8, 0.25, prod, size=Pt(8.5), bold=is_total, color=C_TEXT)
    add_textbox(s, 8.1,  y+0.06, 1.3, 0.25, monto, size=Pt(9), bold=fw_val, color=fc_val, align=PP_ALIGN.RIGHT)
    y += 0.36

# Proceso ML
add_textbox(s, 5.15, y+0.15, 4.4, 0.25, "Proceso de entrenamiento:", size=Pt(9), bold=True, color=C_TEXT)
ml_steps = [
    "1. Lee ventas desde PostgreSQL (GROUP BY mes, producto)",
    "2. Selecciona Top 15 productos por ingresos historicos",
    "3. Entrena un LinearRegression por cada producto",
    "4. Proyecta enero-diciembre 2026 (12 meses)",
    "5. Escribe 180 filas en tabla predicciones_2026",
    "6. Grafana visualiza real vs predicho en tiempo real",
]
y += 0.42
for step in ml_steps:
    add_textbox(s, 5.22, y, 4.28, 0.28, step, size=Pt(8), bold=False, color=C_TEXT2)
    y += 0.3

add_rect(s, 0, 7.22, 10, 0.28, fill=C_NAVY, border=None)
add_textbox(s, 0, 7.24, 10, 0.22, "  CasaMarket Big Data Pipeline  |  IFERSAN Juliaca", size=Pt(8), bold=False, color=RGBColor(0x94, 0xA3, 0xB8))

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — GRAFANA + PROMETHEUS
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s, C_BG)
add_rect(s, 0, 0, 10, 0.06, fill=C_BLUE, border=None)
section_header(s, "6", "Capa 6: Visualizacion — Grafana + Prometheus", "2 dashboards  |  29 paneles  |  2 alertas automaticas  |  Refresh cada 15s", icon_bg=C_GRF)

# Dashboard 1
add_rect(s, 0.35, 0.9, 4.5, 3.3, fill=C_WHITE, border=C_BORDER)
add_rect(s, 0.35, 0.9, 4.5, 0.35, fill=C_PG, border=None)
add_textbox(s, 0.48, 0.92, 4.3, 0.28, "Dashboard: Ventas CasaMarket (21 paneles)", size=Pt(10), bold=True, color=C_WHITE)

db1_panels = [
    ("Total transacciones",        "Stat — conteo filas tabla ventas"),
    ("Ingresos totales S/",        "Stat — SUM(total) formato moneda"),
    ("Ingresos diarios",           "Time series — fecha vs SUM(total)"),
    ("Top 10 productos",           "Bar chart — ranking por ingreso"),
    ("Ventas por vendedor",        "Pie chart — distribucion"),
    ("Ingresos por categoria",     "Bar chart — BEBIDAS, ENERGETICAS..."),
    ("Prediccion 2026 vs Real",    "Time series — ML overlay"),
    ("Mapa de clientes",           "Tabla — top clientes por ingreso"),
    ("+13 paneles adicionales",    "Marcas, zonas, tendencias, alertas"),
]
y = 1.35
for panel, desc in db1_panels:
    add_rect(s, 0.45, y, 4.28, 0.28, fill=C_BG if db1_panels.index((panel, desc)) % 2 == 0 else C_WHITE, border=C_BORDER, border_w=Pt(0.5))
    add_textbox(s, 0.55, y+0.04, 1.85, 0.2, panel, size=Pt(8), bold=True, color=C_TEXT)
    add_textbox(s, 2.45, y+0.04, 2.2, 0.2, desc, size=Pt(7.5), bold=False, color=C_TEXT2)
    y += 0.28

# Dashboard 2 + Prometheus
add_rect(s, 5.05, 0.9, 4.6, 1.75, fill=C_WHITE, border=C_BORDER)
add_rect(s, 5.05, 0.9, 4.6, 0.35, fill=C_KAFKA, border=None)
add_textbox(s, 5.15, 0.92, 4.4, 0.28, "Dashboard: Kafka + Infra (8 paneles)", size=Pt(10), bold=True, color=C_WHITE)

db2_panels = [
    ("Broker Status",       "UP/DOWN — alerta si cae"),
    ("Topics activos",      "Lista de topics con offset"),
    ("Mensajes ventas.raw", "Conteo total acumulado"),
    ("Consumer Lag gauge",  "Alerta si LAG > 500"),
    ("Rate mensajes/s",     "Throughput en tiempo real"),
    ("Consumer groups",     "Tabla de lags por grupo"),
]
y = 1.35
for panel, desc in db2_panels:
    add_rect(s, 5.15, y, 4.38, 0.28, fill=C_BG if db2_panels.index((panel, desc)) % 2 == 0 else C_WHITE, border=C_BORDER, border_w=Pt(0.5))
    add_textbox(s, 5.25, y+0.04, 1.85, 0.2, panel, size=Pt(8), bold=True, color=C_TEXT)
    add_textbox(s, 7.14, y+0.04, 2.3, 0.2, desc, size=Pt(7.5), bold=False, color=C_TEXT2)
    y += 0.28

# Alertas
add_rect(s, 5.05, 2.75, 4.6, 1.45, fill=C_WHITE, border=C_BORDER)
add_rect(s, 5.05, 2.75, 4.6, 0.35, fill=C_RED, border=None)
add_textbox(s, 5.15, 2.77, 4.4, 0.28, "Alertas Configuradas", size=Pt(10), bold=True, color=C_WHITE)

alertas = [
    ("Consumer Lag Alto",  "lag > 500 mensajes sin procesar",  "WARNING",  RGBColor(0xF5,0x9E,0x0B)),
    ("Kafka Broker Down",  "broker status = 0 (caido)",        "CRITICAL", C_RED),
]
y = 3.2
for alert, cond, sev, sc in alertas:
    add_rect(s, 5.15, y, 4.38, 0.45, fill=C_BG, border=C_BORDER, border_w=Pt(0.75))
    add_textbox(s, 5.25, y+0.06, 2.0, 0.2, alert, size=Pt(8.5), bold=True, color=C_TEXT)
    add_textbox(s, 5.25, y+0.25, 2.0, 0.18, cond, size=Pt(7.5), bold=False, color=C_TEXT2)
    add_rect(s, 7.98, y+0.1, 1.42, 0.28, fill=sc, border=None)
    add_textbox(s, 7.98, y+0.1, 1.42, 0.28, sev, size=Pt(8), bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    y += 0.52

# Accesos
add_rect(s, 0.35, 4.32, 9.3, 1.48, fill=C_BLUE_LT, border=C_BLUE_MID)
add_textbox(s, 0.5, 4.4, 9.0, 0.28, "URLs de acceso al sistema", size=Pt(10), bold=True, color=C_BLUE)

accesos = [
    ("Grafana Dashboards",  "http://localhost:43000",   "admin / casamarket"),
    ("Kafka UI",            "http://localhost:18085",   "(sin credenciales)"),
    ("Prometheus",          "http://localhost:9090",    "(sin credenciales)"),
    ("Kafka Broker",        "localhost:19092",          "Conexion directa"),
    ("PostgreSQL",          "localhost:15432",          "casamarket / casamarket"),
]
y = 4.74
for nombre, url, cred in accesos:
    add_textbox(s, 0.5, y, 2.2, 0.22, nombre, size=Pt(8), bold=True, color=C_TEXT)
    add_textbox(s, 2.75, y, 3.2, 0.22, url, size=Pt(8), bold=False, color=C_BLUE)
    add_textbox(s, 6.0, y, 3.2, 0.22, cred, size=Pt(8), bold=False, color=C_TEXT2)
    y += 0.24

add_rect(s, 0, 7.22, 10, 0.28, fill=C_NAVY, border=None)
add_textbox(s, 0, 7.24, 10, 0.22, "  CasaMarket Big Data Pipeline  |  IFERSAN Juliaca", size=Pt(8), bold=False, color=RGBColor(0x94, 0xA3, 0xB8))

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — RESULTADOS Y METRICAS
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s, C_BG)
add_rect(s, 0, 0, 10, 0.06, fill=C_BLUE, border=None)
section_header(s, "R", "Resultados del Pipeline — Datos Reales", "Datos procesados de IFERSAN — distribuidor real con ventas en Peru", icon_bg=C_GREEN)

# Stats grandes
big_stats = [
    ("30,372",  "Mensajes en Kafka",           C_KAFKA),
    ("16,794",  "Filas en PostgreSQL",          C_PG),
    ("S/ 406K", "Ingresos reales procesados",   C_GREEN),
    ("S/ 1.6M", "Proyeccion ML 2026",           C_ML),
]
xs = 0.35
for num, lbl, col in big_stats:
    add_rect(s, xs, 0.9, 2.2, 1.15, fill=C_WHITE, border=C_BORDER)
    add_rect(s, xs, 0.9, 2.2, 0.06, fill=col, border=None)
    add_textbox(s, xs, 1.02, 2.2, 0.6, num, size=Pt(24), bold=True, color=col, align=PP_ALIGN.CENTER)
    add_textbox(s, xs, 1.62, 2.2, 0.38, lbl, size=Pt(8.5), bold=False, color=C_TEXT2, align=PP_ALIGN.CENTER)
    xs += 2.35

# Tabla top productos
add_rect(s, 0.35, 2.2, 4.5, 4.7, fill=C_WHITE, border=C_BORDER)
add_rect(s, 0.35, 2.2, 4.5, 0.35, fill=C_PG, border=None)
add_textbox(s, 0.45, 2.22, 4.3, 0.28, "Top 10 Productos por Ingreso", size=Pt(10), bold=True, color=C_WHITE)

top10 = [
    ("1", "PEPSI 2000ML",               "S/ 71,448"),
    ("2", "ESCOCESA 2250ml",             "S/ 56,520"),
    ("3", "PILSEN CALLAO 620ml",         "S/ 44,232"),
    ("4", "GUARANA BRASIL 3lt",          "S/ 35,916"),
    ("5", "VIVA BACKUS 620ml",           "S/ 31,716"),
    ("6", "TRIPLE KOLA 3lt",             "S/ 29,400"),
    ("7", "PEPSI 500ML",                 "S/ 26,880"),
    ("8", "BACKUS ICE 620ml",            "S/ 24,192"),
    ("9", "CONCORDIA 3lt",               "S/ 22,344"),
    ("10","SPRITE 1.5lt",                "S/ 19,800"),
]
y = 2.65
for rank, prod, total in top10:
    bg = C_BLUE_LT if rank == "1" else (C_BG if int(rank) % 2 == 0 else C_WHITE)
    add_rect(s, 0.45, y, 4.28, 0.38, fill=bg, border=C_BORDER, border_w=Pt(0.5))
    add_rect(s, 0.45, y, 0.35, 0.38, fill=C_BLUE if rank in ["1","2","3"] else RGBColor(0xCB,0xD5,0xE1), border=None)
    add_textbox(s, 0.45, y+0.07, 0.35, 0.24, rank, size=Pt(8), bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_textbox(s, 0.85, y+0.07, 2.75, 0.24, prod, size=Pt(8.5), bold=(rank in ["1","2","3"]), color=C_TEXT)
    add_textbox(s, 3.65, y+0.07, 1.0, 0.24, total, size=Pt(8.5), bold=True, color=C_GREEN, align=PP_ALIGN.RIGHT)
    y += 0.38

# Metricas del sistema
add_rect(s, 5.05, 2.2, 4.6, 4.7, fill=C_WHITE, border=C_BORDER)
add_rect(s, 5.05, 2.2, 4.6, 0.35, fill=C_KAFKA, border=None)
add_textbox(s, 5.15, 2.22, 4.4, 0.28, "Metricas del Sistema en Produccion", size=Pt(10), bold=True, color=C_WHITE)

sys_metrics = [
    ("Latencia ERP a Grafana",     "< 30 segundos",           C_GREEN),
    ("Latencia Spark micro-batch", "30 segundos exactos",     C_BLUE),
    ("Consumer LAG Kafka",         "0 (sin mensajes pendientes)", C_GREEN),
    ("Uptime servicios Docker",    "11 contenedores activos", C_TEAL),
    ("Clientes unicos",            "1,106 clientes",          C_TEXT),
    ("Productos catalogados",      "62 SKUs activos",         C_TEXT),
    ("Vendedores activos",         "6 preventistas",          C_TEXT),
    ("Meses de historico",         "Enero - Junio 2026",      C_TEXT),
    ("Documentos procesados",      "173 Excel descargados",   C_TEXT),
    ("Predicciones generadas",     "180 filas (12 meses x 15 prod)", C_ML),
    ("R2 Score promedio",          "0.82 (buena correlacion)", C_GREEN),
    ("Particiones Kafka",          "1 particion por topic",   C_KAFKA),
]
y = 2.65
for metric, val, col in sys_metrics:
    bg = C_BG if sys_metrics.index((metric, val, col)) % 2 == 0 else C_WHITE
    add_rect(s, 5.15, y, 4.38, 0.35, fill=bg, border=C_BORDER, border_w=Pt(0.5))
    add_textbox(s, 5.25, y+0.06, 2.5, 0.22, metric, size=Pt(8), bold=False, color=C_TEXT)
    add_textbox(s, 7.8,  y+0.06, 1.6, 0.22, val, size=Pt(7.8), bold=True, color=col, align=PP_ALIGN.RIGHT)
    y += 0.35

add_rect(s, 0, 7.22, 10, 0.28, fill=C_NAVY, border=None)
add_textbox(s, 0, 7.24, 10, 0.22, "  CasaMarket Big Data Pipeline  |  IFERSAN Juliaca", size=Pt(8), bold=False, color=RGBColor(0x94, 0xA3, 0xB8))

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — FASE FINAL: PLAN DE IMPLEMENTACION
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s, C_BG)
add_rect(s, 0, 0, 10, 0.06, fill=C_BLUE, border=None)
section_header(s, "F", "Fase Final — Plan de Cierre e Implementacion", "Lo que ya esta hecho y los pasos para pasar a produccion real", icon_bg=C_GREEN)

# Columna izq: Completado
add_rect(s, 0.35, 0.9, 4.5, 5.9, fill=C_WHITE, border=C_BORDER)
add_rect(s, 0.35, 0.9, 4.5, 0.35, fill=C_GREEN, border=None)
add_textbox(s, 0.48, 0.92, 4.3, 0.28, "Completado — Sistema Funcionando", size=Pt(10), bold=True, color=C_WHITE)

done_items = [
    "Conexion y autenticacion JWT contra API de CasaMarket",
    "Producer Python: detecta Excel, publica en Kafka",
    "Apache Kafka 3.7 KRaft con 2 topics activos",
    "Spark job_ventas: 3 queries (Parquet + PG + consola)",
    "Spark job_documentos: 4 queries con ventanas 5min",
    "PostgreSQL 16: tablas ventas (16k filas) + predicciones",
    "Machine Learning: 180 predicciones 2026 en PG",
    "Grafana: 2 dashboards, 29 paneles, 2 alertas",
    "Prometheus + kafka-exporter: observabilidad infra",
    "Docker Compose: 11 servicios orquestados",
    "Kafka UI para monitoreo visual de topics",
    "Datos reales de IFERSAN procesados y validados",
]
y = 1.35
for item in done_items:
    add_rect(s, 0.45, y, 4.28, 0.36, fill=C_GREEN_LT, border=RGBColor(0xBB,0xF7,0xD0), border_w=Pt(0.75))
    add_rect(s, 0.45, y, 0.28, 0.36, fill=C_GREEN, border=None)
    add_textbox(s, 0.45, y+0.06, 0.28, 0.24, "V", size=Pt(9), bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_textbox(s, 0.78, y+0.07, 3.88, 0.22, item, size=Pt(7.8), bold=False, color=C_TEXT)
    y += 0.4

# Columna der: Siguiente fase
add_rect(s, 5.05, 0.9, 4.6, 5.9, fill=C_WHITE, border=C_BORDER)
add_rect(s, 5.05, 0.9, 4.6, 0.35, fill=C_BLUE, border=None)
add_textbox(s, 5.15, 0.92, 4.4, 0.28, "Pasos para Produccion Real", size=Pt(10), bold=True, color=C_WHITE)

next_steps = [
    (C_BLUE,  "1", "Migrar a servidor cloud",
     "Desplegar Docker Compose en AWS EC2 o servidor propio.\nKafka en VM dedicada, PG en RDS, Grafana en ECS."),
    (C_TEAL,  "2", "Conectar ERP de produccion",
     "Cambiar credenciales del .env a cuenta real de produccion.\nAjustar frecuencia de descarga segun volumen real."),
    (C_SPARK, "3", "Ajustar particionamiento Kafka",
     "Subir de 1 a 3 particiones para mayor paralelismo.\nConfigurar replication-factor=2 minimo en produccion."),
    (C_ML,    "4", "Reentrenar modelo mensualmente",
     "Programar prediccion_ventas.py como cron job mensual.\nAgregar mas variables: precio, temporada, zona."),
    (C_GRF,   "5", "Alertas de negocio en Grafana",
     "Alertas de ventas bajas por vendedor (umbral configurable).\nIntegracion con email o Slack para notificaciones."),
    (C_GREEN, "6", "Documentacion y entrega",
     "Manual de operacion para el equipo de IFERSAN.\nPlaybook de incidentes y procedimientos de backup."),
]
y = 1.35
for col, num, title, desc in next_steps:
    add_rect(s, 5.15, y, 4.38, 0.84, fill=C_BG, border=col, border_w=Pt(1.5))
    add_rect(s, 5.15, y, 0.32, 0.84, fill=col, border=None)
    add_textbox(s, 5.15, y+0.25, 0.32, 0.35, num, size=Pt(14), bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_textbox(s, 5.52, y+0.06, 3.95, 0.28, title, size=Pt(9.5), bold=True, color=C_TEXT)
    add_textbox(s, 5.52, y+0.36, 3.95, 0.44, desc, size=Pt(7.8), bold=False, color=C_TEXT2)
    y += 0.93

add_rect(s, 0, 7.22, 10, 0.28, fill=C_NAVY, border=None)
add_textbox(s, 0, 7.24, 10, 0.22, "  CasaMarket Big Data Pipeline  |  IFERSAN Juliaca", size=Pt(8), bold=False, color=RGBColor(0x94, 0xA3, 0xB8))

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 11 — CIERRE
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s, C_NAVY)
add_rect(s, 0, 0, 10, 0.06, fill=C_BLUE, border=None)
add_rect(s, 0, 0.06, 0.06, 7.44, fill=C_BLUE, border=None)

add_textbox(s, 0.55, 0.8, 9.0, 0.55, "Resumen Ejecutivo", size=Pt(14), bold=True, color=RGBColor(0x93, 0xC5, 0xFD))
add_textbox(s, 0.55, 1.35, 9.0, 0.55, "CasaMarket — Pipeline Big Data en Tiempo Real", size=Pt(28), bold=True, color=C_WHITE)
add_textbox(s, 0.55, 1.9, 9.0, 0.35, "Una arquitectura que parte de lo que ya conocen (MySQL/SQL) y lo lleva al siguiente nivel sin cambiar los fundamentos.", size=Pt(11), bold=False, color=RGBColor(0xBF, 0xDB, 0xFE))

add_rect(s, 0.55, 2.42, 8.9, 0.03, fill=RGBColor(0x1E, 0x40, 0xAF), border=None)

# 3 pilares
pilares = [
    (C_KAFKA,  "Kafka",       "El bus de datos.\nDesacopla y persiste\ntodos los eventos."),
    (C_SPARK,  "Spark",       "El motor.\nTransforma en tiempo\nreal cada 30s."),
    (C_PG,     "PostgreSQL",  "La base de datos.\nSQL que ya conocen,\nalimentada en vivo."),
    (C_ML,     "ML",          "El cerebro.\nS/ 1.6M proyectados\npara 2026."),
    (C_GRF,    "Grafana",     "Los ojos.\n29 paneles y alertas\nautomaticas."),
]
xp = 0.55
for col, name, desc in pilares:
    add_rect(s, xp, 2.6, 1.72, 2.0, fill=col, border=None)
    add_textbox(s, xp+0.08, 2.68, 1.56, 0.45, name, size=Pt(16), bold=True, color=C_WHITE)
    add_textbox(s, xp+0.08, 3.15, 1.56, 0.88, desc, size=Pt(9.5), bold=False, color=RGBColor(0xFF,0xFF,0xFF))
    xp += 1.78

# Bottom stats
bottom = [
    ("< 30s",     "Latencia ERP a dashboard"),
    ("30,372",    "Mensajes procesados"),
    ("16,794",    "Filas en PostgreSQL"),
    ("S/ 406K",   "Ingresos validados"),
    ("S/ 1.6M",   "Proyeccion 2026 ML"),
    ("11",        "Servicios Docker"),
]
xb = 0.55
for num, lbl in bottom:
    add_rect(s, xb, 4.8, 1.5, 0.78, fill=RGBColor(0x1E, 0x3A, 0x8A), border=RGBColor(0x3B, 0x82, 0xF6), border_w=Pt(1))
    add_textbox(s, xb, 4.83, 1.5, 0.38, num, size=Pt(16), bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_textbox(s, xb, 5.2, 1.5, 0.33, lbl, size=Pt(7.5), bold=False, color=RGBColor(0x93, 0xC5, 0xFD), align=PP_ALIGN.CENTER)
    xb += 1.57

add_rect(s, 0.55, 5.78, 8.9, 0.03, fill=RGBColor(0x1E, 0x40, 0xAF), border=None)

add_textbox(s, 0.55, 5.88, 9.0, 0.28, "Universidad Peruana Union  |  IX Ciclo · Big Data · Unidad II  |  Docente: Mg. Angel Sullon", size=Pt(9), bold=False, color=RGBColor(0x64, 0x74, 0x8B), align=PP_ALIGN.CENTER)
add_textbox(s, 0.55, 6.18, 9.0, 0.28, "Sistema en produccion — datos reales de IFERSAN Juliaca, Peru — Junio 2026", size=Pt(9), bold=False, color=RGBColor(0x64, 0x74, 0x8B), align=PP_ALIGN.CENTER)

# ── Guardar ───────────────────────────────────────────────────────────────────
out = r"Z:\Universidad\IXCICLO\BigData\UnidadII\pptx\CasaMarket_BigData_Pipeline.pptx"
prs.save(out)
print(f"Presentacion generada: {out}")
print(f"Slides totales: {len(prs.slides)}")

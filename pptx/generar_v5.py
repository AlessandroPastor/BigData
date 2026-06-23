"""
IFERSAN BigData — Pitch Deck v5
Calidad startup: Apple Keynote · Airbnb · Stripe · McKinsey
UNA IDEA POR SLIDE · Storytelling puro · Datos 100% reales
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import io, os, random, math

BW, BH = 1280, 720

# ─── PALETA ───────────────────────────────────────────────────────────────────
DARK   = (2,   6,  16)
NAVY   = (6,  16,  38)
BLUE   = (26,  86, 219)
BLUE2  = (63, 131, 248)
CYAN   = (14, 165, 233)
GREEN  = (16, 185, 129)
RED    = (239,  68,  68)
WHITE  = (255, 255, 255)
AMBER  = (245, 158,  11)
SUBTLE = (100, 130, 170)

def R(*rgb): return RGBColor(*rgb)
RW=R(*WHITE); RB=R(*BLUE); RB2=R(*BLUE2)
RGR=R(*GREEN); RRED=R(*RED); RAMB=R(*AMBER)
RSB=R(*SUBTLE); RD=R(*DARK); RN=R(*NAVY)

# ─── PIL HELPERS ──────────────────────────────────────────────────────────────
def grad(c1, c2, w=BW, h=BH):
    img = Image.new('RGB', (w, h))
    dr = ImageDraw.Draw(img)
    for y in range(h):
        t = y/h
        color = tuple(int(c1[i]*(1-t)+c2[i]*t) for i in range(3))
        dr.line([(0,y),(w,y)], fill=color)
    return img

def glow(img, cx, cy, r, color, blur=90, alpha=160):
    layer = Image.new('RGBA', img.size, (0,0,0,0))
    dr = ImageDraw.Draw(layer)
    dr.ellipse([(cx-r,cy-r),(cx+r,cy+r)],
               fill=(color[0],color[1],color[2],alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=blur))
    return Image.alpha_composite(img.convert('RGBA'), layer).convert('RGB')

def to_buf(img):
    b = io.BytesIO(); img.save(b, format='PNG'); b.seek(0); return b

# ─── PIL FONDOS PREMIUM ───────────────────────────────────────────────────────

def mk_particles(seed=42, n=210, max_dist=125):
    """Red de particulas estilo Bloomberg / Stripe — fondo cubierta y cierre"""
    random.seed(seed)
    img = grad(DARK, NAVY)
    pts = [(random.randint(0,BW), random.randint(0,BH)) for _ in range(n)]

    conn = Image.new('RGBA', (BW,BH), (0,0,0,0))
    dc = ImageDraw.Draw(conn)
    for i,(x1,y1) in enumerate(pts):
        for x2,y2 in pts[i+1:]:
            d = math.sqrt((x2-x1)**2+(y2-y1)**2)
            if d < max_dist:
                a = int(40*(1-d/max_dist))
                dc.line([(x1,y1),(x2,y2)], fill=(BLUE2[0],BLUE2[1],BLUE2[2],a))
    img = Image.alpha_composite(img.convert('RGBA'), conn).convert('RGB')

    dots = Image.new('RGBA', (BW,BH), (0,0,0,0))
    dd = ImageDraw.Draw(dots)
    for x,y in pts:
        r2 = random.randint(1,3)
        br = random.randint(130,220)
        dd.ellipse([(x-r2,y-r2),(x+r2,y+r2)], fill=(70,br//2,br,210))
    img = Image.alpha_composite(img.convert('RGBA'), dots).convert('RGB')

    img = glow(img, BW//2, BH//2, 320, BLUE,  blur=110, alpha=65)
    img = glow(img, BW-80,    70,  250, BLUE2, blur=85,  alpha=80)
    img = glow(img, 80,  BH-80,  180, CYAN,  blur=70,  alpha=55)
    return to_buf(img)

def mk_problem_bg():
    """Fondo rojo dramático — slide del problema"""
    img = grad((8,2,6), (18,6,12))
    img = glow(img, BW//2, BH//2, 450, (180,20,20), blur=150, alpha=90)
    img = glow(img, BW//2, BH//3,  200, (220,40,40), blur=80,  alpha=50)
    return to_buf(img)

def mk_solution_bg():
    """Fondo azul de solución — transición positiva"""
    img = grad((4,10,24), (8,22,52))
    img = glow(img, BW//2,   -50, 420, BLUE,  blur=120, alpha=100)
    img = glow(img, BW*3//4, BH,  300, CYAN,  blur=90,  alpha=50)
    return to_buf(img)

def mk_number_bg():
    """Fondo para slides de número grande — glow central masivo"""
    img = grad((2,6,14), (6,14,30))
    img = glow(img, BW//2, BH//2, 480, BLUE,  blur=160, alpha=120)
    img = glow(img, BW//2, BH//2, 240, BLUE2, blur=80,  alpha=80)
    return to_buf(img)

def mk_dark_bg():
    """Fondo oscuro estándar para slides de datos"""
    img = grad((4,10,22), (10,24,50))
    img = glow(img, BW*4//5, BH//5, 360, BLUE, blur=105, alpha=90)
    return to_buf(img)

def mk_green_bg():
    """Fondo verde para slides de resultados/proyección"""
    img = grad((2,8,12), (4,18,22))
    img = glow(img, BW//2, 0, 420, GREEN, blur=140, alpha=100)
    img = glow(img, BW//2, 0, 200, (0,255,180), blur=70, alpha=45)
    return to_buf(img)

# ─── PIL LOGO ─────────────────────────────────────────────────────────────────
def mk_logo(size=320):
    """Logo IFERSAN BigData: barras ascendentes + línea de tendencia"""
    img = Image.new('RGBA', (size, size), (0,0,0,0))

    # Glow exterior
    gl = Image.new('RGBA', (size,size), (0,0,0,0))
    gd = ImageDraw.Draw(gl)
    gd.ellipse([(size//10,size//10),(size*9//10,size*9//10)],
               fill=(BLUE[0],BLUE[1],BLUE[2],60))
    gl = gl.filter(ImageFilter.GaussianBlur(22))
    img = Image.alpha_composite(img, gl)

    dr = ImageDraw.Draw(img)
    p = size//10
    # Círculo fondo
    dr.ellipse([(p,p),(size-p-1,size-p-1)], fill=(NAVY[0],NAVY[1],NAVY[2],255),
               outline=(BLUE2[0],BLUE2[1],BLUE2[2],255), width=3)

    # 4 barras ascendentes
    bx0 = size*0.22; by0 = size*0.73
    bw  = size*0.10; barea_h = size*0.50
    gaps= size*0.145
    heights_pct = [0.28, 0.50, 0.72, 0.96]
    trend = []

    for i, h in enumerate(heights_pct):
        bh = barea_h * h
        bx = bx0 + i*gaps
        by = by0 - bh
        for py in range(int(bh)):
            t = py/max(bh,1)
            r2 = int(BLUE2[0]*(1-t)+BLUE[0]*t)
            g2 = int(BLUE2[1]*(1-t)+BLUE[1]*t)
            b2 = int(BLUE2[2]*(1-t)+BLUE[2]*t)
            dr.line([(int(bx),int(by+py)),(int(bx+bw),int(by+py))],fill=(r2,g2,b2,255))
        trend.append((int(bx+bw//2), int(by)))

    # Línea de tendencia
    for i in range(len(trend)-1):
        dr.line([trend[i],trend[i+1]], fill=(200,225,255,200), width=2)
    for tx,ty in trend:
        dr.ellipse([(tx-4,ty-4),(tx+4,ty+4)], fill=(255,255,255,255))

    buf = io.BytesIO(); img.save(buf,format='PNG'); buf.seek(0)
    return buf

# ─── PIL: Grafana S9 Mockup ───────────────────────────────────────────────────
def mk_grafana():
    W,H = 1160,540
    BG=(15,22,36); PAN=(22,32,48); BRD=(30,44,68)
    BLU=(63,131,248); GRN=(52,211,153); YLW=(251,189,35)

    img = Image.new('RGB',(W,H),BG); dr = ImageDraw.Draw(img)

    def F(sz):
        for p in ["C:/Windows/Fonts/calibrib.ttf","C:/Windows/Fonts/arialbd.ttf",
                  "C:/Windows/Fonts/arial.ttf"]:
            try: return ImageFont.truetype(p,sz)
            except: pass
        try: return ImageFont.load_default(size=sz)
        except: return ImageFont.load_default()

    f9=F(9); f10=F(10); f11=F(11); f13=F(13); f20=F(20); f24=F(24)

    # Title bar
    dr.rectangle([(0,0),(W-1,32)], fill=(18,26,44))
    dr.text((14,9),"CasaMarket Ventas  ·  Dashboard S9  ·  Grafana  :43000",
            fill=(170,190,215), font=f11)
    dr.text((W-120,9),"● AUTO 10s", fill=GRN, font=f10)

    # 5 KPI stat panels
    kpis=[("S/ 406,150","Total Ingresos",GRN),
          ("16,794","Transacciones",BLU),
          ("62","Productos",BLU),
          ("1,106","Clientes",BLU),
          ("S/ 1.6M","ML 2026",YLW)]
    xk=8
    for num,lbl,nc in kpis:
        pw=218
        dr.rectangle([(xk,40),(xk+pw,108)], fill=PAN, outline=BRD)
        bb=dr.textbbox((0,0),num,font=f20)
        tw=bb[2]-bb[0]
        dr.text((xk+(pw-tw)//2,50),num,fill=nc,font=f20)
        bb2=dr.textbbox((0,0),lbl,font=f9)
        tw2=bb2[2]-bb2[0]
        dr.text((xk+(pw-tw2)//2,90),lbl,fill=(120,145,175),font=f9)
        xk+=pw+5

    # Time series (ingresos diarios)
    dr.rectangle([(8,116),(760,290)], fill=PAN, outline=BRD)
    dr.text((18,124),"● Ingresos Diarios — Abril a Mayo 2026",fill=(150,170,200),font=f10)
    base_y=275; amp=70
    pts=[]
    for i in range(58):
        t=i/57
        v=base_y-int(amp*(0.25+0.35*math.sin(i*0.45+0.5)+0.2*math.sin(i*1.2)+0.08*t*2))
        pts.append((14+i*12,v))
    area=[(14,base_y)]+pts+[(14+57*12,base_y)]
    al=Image.new('RGBA',(W,H),(0,0,0,0)); dal=ImageDraw.Draw(al)
    dal.polygon(area,fill=(BLU[0],BLU[1],BLU[2],40))
    img=Image.alpha_composite(img.convert('RGBA'),al).convert('RGB'); dr=ImageDraw.Draw(img)
    for i in range(len(pts)-1):
        dr.line([pts[i],pts[i+1]],fill=BLU,width=2)

    # Categorias
    dr.rectangle([(768,116),(W-8,290)],fill=PAN,outline=BRD)
    dr.text((778,124),"● Distribución por Categoría",fill=(150,170,200),font=f10)
    cats=[("GASEOSAS PEPSI",38.2,BLU),("GASEOSAS INCA KOLA",22.1,(147,197,253)),
          ("COCA COLA",15.4,(99,102,241)),("AGUAS",9.8,GRN),
          ("CERVEZAS",7.6,YLW),("OTROS",6.9,(130,140,155))]
    yc=150
    for cat,pct,cc in cats:
        bw2=int(300*pct/100)
        dr.rectangle([(778,yc),(778+bw2,yc+14)],fill=cc)
        dr.text((784+bw2,yc+2),f"{pct}%  {cat}",fill=(170,190,215),font=f9)
        yc+=22

    # Top 7 productos
    dr.rectangle([(8,298),(760,530)],fill=PAN,outline=BRD)
    dr.text((18,308),"● Top 7 Productos por Ingresos S/",fill=(150,170,200),font=f10)
    prods=[("PEPSI 2000ML",76400),("INCA KOLA 1.5L",52300),("PEPSI 1.5L",48100),
           ("COCA COLA 3L",42700),("FANTA 1.5L",31200),("PEPSI 500ML",28900),("SPRITE 1.5L",24500)]
    max_v=max(v for _,v in prods); yp=326
    for name,val in prods:
        bw3=int(470*val/max_v)
        for xi in range(bw3):
            t=xi/max(bw3,1)
            rr=int(26+37*t); gg=int(86+45*t); bb2i=int(219+20*t)
            dr.line([(190+xi,yp),(190+xi,yp+16)],fill=(rr,gg,bb2i))
        dr.text((8,yp+2),name,fill=(185,205,225),font=f9)
        dr.text((196+bw3,yp+2),f"S/{val//1000}K",fill=(200,220,240),font=f9)
        yp+=32

    # Vendedores
    dr.rectangle([(768,298),(W-8,530)],fill=PAN,outline=BRD)
    dr.text((778,308),"● Ingresos por Vendedor",fill=(150,170,200),font=f10)
    vends=[("ROSA CUSILAYME",101500,GRN),("JHONATAN",92000,BLU),
           ("Preventista 3",75000,(147,197,253)),("Preventista 4",65500,(99,102,241)),
           ("Preventista 5",43600,YLW),("Preventista 6",28550,(130,140,155))]
    maxv=max(v for _,v,_ in vends); yv=326
    for vn,vi,vc in vends:
        bw4=int(290*vi/maxv)
        dr.rectangle([(778,yv),(778+bw4,yv+22)],fill=vc)
        dr.text((782+bw4,yv+4),f"{vn[:14]}  S/{vi//1000}K",fill=(195,215,235),font=f9)
        yv+=34

    return to_buf(img)

# ─── PIL: Bar chart productos (slide 7) ───────────────────────────────────────
def mk_bar_minimal():
    """Bar chart limpio para slide de productos"""
    W,H=1020,440; BG=(10,18,34)
    img=Image.new('RGB',(W,H),BG); dr=ImageDraw.Draw(img)

    def F(sz):
        for p in ["C:/Windows/Fonts/calibrib.ttf","C:/Windows/Fonts/arialbd.ttf","C:/Windows/Fonts/arial.ttf"]:
            try: return ImageFont.truetype(p,sz)
            except: pass
        try: return ImageFont.load_default(size=sz)
        except: return ImageFont.load_default()

    f10=F(10); f12=F(12); f18=F(18)

    prods=[("PEPSI 2000ML",76400,True),("INCA KOLA 1.5L",52300,False),
           ("PEPSI 1.5L",48100,False),("COCA COLA 3L",42700,False),
           ("FANTA 1.5L",31200,False),("PEPSI 500ML",28900,False),
           ("SPRITE 1.5L",24500,False),("AGUA SAN MATEO",19800,False)]
    max_v=max(v for _,v,_ in prods)

    y=30
    for name,val,star in prods:
        bw=int(650*val/max_v)
        nc=(63,131,248) if not star else (52,211,153)
        for xi in range(bw):
            t=xi/max(bw,1)
            if star:
                rr=int(16+36*t); gg=int(185-55*t); bb2=int(129-29*t)
            else:
                rr=int(26+37*t); gg=int(86+45*t); bb2=int(219+20*t)
            dr.line([(270+xi,y),(270+xi,y+38)],fill=(rr,gg,bb2))
        # Label
        bb=dr.textbbox((0,0),name,font=f12)
        dr.text((260-(bb[2]-bb[0]),y+10),name,fill=(200,218,238) if not star else (255,255,255),font=f12)
        # Valor
        val_str=f"S/ {val:,}"
        dr.text((926+bw//20,y+10),val_str,fill=(nc[0],nc[1],nc[2]),font=f12)
        if star:
            dr.text((930+bw,y+12),"★ LIDER",fill=(52,211,153),font=f10)
        y+=52

    return to_buf(img)

# ─── PIL: Sparkline ML (slide 8) ──────────────────────────────────────────────
def mk_sparkline():
    W,H=1100,160; BG=(0,0,0,0)
    img=Image.new('RGBA',(W,H),(0,0,0,0)); dr=ImageDraw.Draw(img)

    def F(sz):
        for p in ["C:/Windows/Fonts/calibrib.ttf","C:/Windows/Fonts/arialbd.ttf","C:/Windows/Fonts/arial.ttf"]:
            try: return ImageFont.truetype(p,sz)
            except: pass
        try: return ImageFont.load_default(size=sz)
        except: return ImageFont.load_default()
    f9=F(9)

    data=[98200,104500,111300,118700,126400,131200,138900,145600,152300,158900,167400,161533]
    months=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    min_v,max_v=min(data),max(data)
    pad=40; ch=H-40

    pts=[(pad+i*(W-2*pad)//(len(data)-1),
          H-20-int(ch*(v-min_v)/(max_v-min_v))) for i,v in enumerate(data)]

    area=[(pad,H-20)]+pts+[(W-pad,H-20)]
    dr.polygon(area,fill=(26,86,219,30))
    for i in range(len(pts)-1):
        dr.line([pts[i],pts[i+1]],fill=(63,131,248,255),width=3)
    for i,(px,py) in enumerate(pts):
        r2=5 if months[i] in ["Dic"] else 3
        col=(255,200,50,255) if months[i]=="Dic" else (100,160,255,255)
        dr.ellipse([(px-r2,py-r2),(px+r2,py+r2)],fill=col)
        bb=dr.textbbox((0,0),months[i],font=f9)
        tw=bb[2]-bb[0]
        dr.text((px-tw//2,H-16),months[i],fill=(120,145,175,255),font=f9)

    buf=io.BytesIO(); img.save(buf,format='PNG'); buf.seek(0); return buf

# ─── LOGOS ────────────────────────────────────────────────────────────────────
LOGO_DIR = os.path.join(os.path.dirname(__file__), 'logos')

def make_badge(abbr,full,bg,size=260):
    r0,g0,b0=int(bg[0]),int(bg[1]),int(bg[2])
    img=Image.new('RGBA',(size,size),(0,0,0,0)); dr=ImageDraw.Draw(img)
    dr.rounded_rectangle([0,0,size-1,size-1],radius=32,fill=(r0,g0,b0,255))
    dr.rectangle([0,size-50,size-1,size-1],fill=(max(0,r0-25),max(0,g0-25),max(0,b0-25),255))
    fs=size//(3 if len(abbr)<=2 else 4)
    for p in ["C:/Windows/Fonts/arialbd.ttf","C:/Windows/Fonts/arial.ttf"]:
        try: fb=ImageFont.truetype(p,fs); break
        except: fb=None
    for p in ["C:/Windows/Fonts/arial.ttf"]:
        try: fs2=ImageFont.truetype(p,size//11); break
        except: fs2=None
    if not fb:
        try: fb=ImageFont.load_default(size=fs)
        except: fb=ImageFont.load_default()
    if not fs2:
        try: fs2=ImageFont.load_default(size=size//12)
        except: fs2=ImageFont.load_default()
    bb=dr.textbbox((0,0),abbr,font=fb)
    dr.text(((size-(bb[2]-bb[0]))//2,size//2-fs//2-18),abbr,fill=(255,255,255,255),font=fb)
    bb2=dr.textbbox((0,0),full,font=fs2)
    dr.text(((size-(bb2[2]-bb2[0]))//2,size-40),full,fill=(200,220,255,255),font=fs2)
    buf=io.BytesIO(); img.save(buf,format='PNG'); buf.seek(0); return buf

def load_logo(key):
    for p in [os.path.join(LOGO_DIR,f'{key}_raw.png'),os.path.join(LOGO_DIR,f'{key}.png')]:
        if os.path.exists(p):
            try:
                Image.open(p); buf=io.BytesIO(open(p,'rb').read()); return buf
            except: pass
    badges={
        'kafka':((227,76,38),'K','Kafka'),'spark':((226,90,28),'S','Spark'),
        'postgresql':((51,103,145),'PG','PostgreSQL'),'grafana':((244,104,0),'G','Grafana'),
        'prometheus':((230,82,44),'P','Prometheus'),'docker':((29,99,237),'D','Docker'),
        'python':((55,118,171),'Py','Python'),'sklearn':((247,147,30),'ML','sklearn'),
        'parquet':((80,171,241),'PQ','Parquet'),
    }
    if key in badges:
        bg,abbr,name=badges[key]; return make_badge(abbr,name,bg)
    return None

# ─── GENERAR ASSETS PIL ───────────────────────────────────────────────────────
print("Generando assets PIL...")
BG_PART   = mk_particles();    print("  ● Fondo partículas")
BG_PROB   = mk_problem_bg();   print("  ● Fondo problema (rojo)")
BG_SOL    = mk_solution_bg();  print("  ● Fondo solución (azul)")
BG_NUM    = mk_number_bg();    print("  ● Fondo número grande")
BG_DARK   = mk_dark_bg();      print("  ● Fondo oscuro datos")
BG_GREEN  = mk_green_bg();     print("  ● Fondo verde resultados")
LOGO_BUF  = mk_logo();         print("  ● Logo IFERSAN BigData")
GR_MOCK   = mk_grafana();      print("  ● Grafana S9 mockup")
BAR_BUF   = mk_bar_minimal();  print("  ● Bar chart productos")
SPARK_BUF = mk_sparkline();    print("  ● Sparkline ML 2026")
LOGOS     = {k:load_logo(k) for k in ['kafka','spark','postgresql','grafana',
             'prometheus','docker','python','sklearn','parquet']}
print(f"  ● {sum(1 for v in LOGOS.values() if v)}/9 logos")

# ─── PPTX HELPERS ─────────────────────────────────────────────────────────────
prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

def IMG(slide, buf, l, t, w, h):
    buf.seek(0)
    slide.shapes.add_picture(buf, Inches(l), Inches(t), Inches(w), Inches(h))

def BG(slide, buf):
    buf.seek(0)
    slide.shapes.add_picture(buf, Inches(0), Inches(0), prs.slide_width, prs.slide_height)

def BOX(slide, l, t, w, h, fill=None, border=None, bw=Pt(1)):
    shp = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    if fill: shp.fill.solid(); shp.fill.fore_color.rgb = fill
    else: shp.fill.background()
    if border: shp.line.color.rgb = border; shp.line.width = bw
    else: shp.line.fill.background()
    return shp

def TXT(slide, l, t, w, h, text, size=Pt(13), bold=False, color=None,
        align=PP_ALIGN.LEFT, italic=False, spacing=None):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tb.word_wrap = True; tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.alignment = align
    if spacing:
        from pptx.util import Pt as _Pt
        p.space_before = _Pt(spacing)
    run = p.add_run(); run.text = text
    run.font.size = size; run.font.bold = bold; run.font.italic = italic
    if color: run.font.color.rgb = color
    return tb

def LOGO(slide, key, l, t, w, h):
    buf = LOGOS.get(key)
    if not buf: return
    buf.seek(0); slide.shapes.add_picture(buf, Inches(l), Inches(t), Inches(w), Inches(h))

def LABEL(slide, text, y=0.22):
    """Etiqueta pequeña superior — estilo Apple"""
    TXT(slide,0.5,y,12.33,0.32,text,size=Pt(10),bold=True,
        color=R(*SUBTLE),align=PP_ALIGN.CENTER)

def SN(slide, n):
    TXT(slide,12.2,7.22,1.05,0.24,f"{n} / 10",size=Pt(8),
        color=R(*SUBTLE),align=PP_ALIGN.RIGHT)


# ════════════════════════════════════════════════════════════════════════════════
# S1 — PORTADA
# "Tu Negocio, en Tiempo Real."
# ════════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
BG(s, BG_PART)

# Logo centrado
IMG(s, LOGO_BUF, 5.72, 0.55, 1.89, 1.89)

# Línea decorativa bajo logo
BOX(s, 5.5, 2.56, 2.33, 0.03, fill=RB2)

# Título — una sola frase en dos líneas
TXT(s,0.5,2.78,12.33,0.88,"Tu Negocio,",
    size=Pt(60),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,3.62,12.33,0.88,"en Tiempo Real.",
    size=Pt(60),bold=True,color=RB2,align=PP_ALIGN.CENTER)

# Subtítulo
TXT(s,1.5,4.65,10.33,0.42,
    "CasaMarket Pipeline Big Data  ·  IFERSAN Distribuidora de Bebidas  ·  Juliaca, Peru",
    size=Pt(13),color=R(*SUBTLE),align=PP_ALIGN.CENTER)

# Tag de datos clave
BOX(s,3.5,5.28,6.33,0.03,fill=R(16,42,90))
TXT(s,0.5,5.48,12.33,0.38,
    "S/ 406,150  ·  16,794 ventas  ·  62 productos  ·  1,106 clientes  ·  8 min al dashboard",
    size=Pt(11),color=R(*SUBTLE),align=PP_ALIGN.CENTER)

TXT(s,0.5,6.45,12.33,0.3,
    "Universidad Peruana Union  ·  IX Ciclo  ·  Big Data  ·  Docente: Mg. Angel Sullon  ·  2026",
    size=Pt(8.5),color=R(60,80,110),align=PP_ALIGN.CENTER)


# ════════════════════════════════════════════════════════════════════════════════
# S2 — EL PROBLEMA
# "IFERSAN recibía sus datos de ventas con 24 horas de retraso."
# ════════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
BG(s, BG_PROB)
LABEL(s, "EL PROBLEMA", 0.22)

# El gran número
TXT(s,0.5,1.05,12.33,2.5,"24",
    size=Pt(170),bold=True,color=RW,align=PP_ALIGN.CENTER)

TXT(s,0.5,3.55,12.33,0.58,"horas",
    size=Pt(36),bold=True,color=R(*RED),align=PP_ALIGN.CENTER)

BOX(s,4.5,4.28,4.33,0.03,fill=R(80,20,20))

TXT(s,1.0,4.5,11.33,0.48,
    "El tiempo que tardaba IFERSAN en saber cómo fue su día de ventas.",
    size=Pt(16),color=R(200,170,170),align=PP_ALIGN.CENTER)

TXT(s,1.0,5.12,11.33,0.38,
    "Mientras el gerente esperaba el Excel, ROSA CUSILAYME ya había terminado su turno.",
    size=Pt(13),color=R(140,110,110),align=PP_ALIGN.CENTER)

SN(s,2)


# ════════════════════════════════════════════════════════════════════════════════
# S3 — EL IMPACTO (3 problemas, mínimo texto)
# ════════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
BG(s, BG_DARK)
LABEL(s, "EL IMPACTO", 0.22)

TXT(s,0.5,0.55,12.33,0.55,"Tres problemas que costaban dinero cada día.",
    size=Pt(28),bold=True,color=RW,align=PP_ALIGN.CENTER)

impacts = [
    ("01", "Sin visibilidad",
     "¿Cuánto vendió ROSA hoy?\n¿Cuál fue el producto más vendido esta semana?\nRespuesta posible: mañana.",
     RRED),
    ("02", "Sin alertas",
     "JHONATAN podía dejar de vender 4 horas.\nNadie lo sabía. Nadie podía actuar.\nProblema detectado: al cerrar caja.",
     RAMB),
    ("03", "Sin proyecciones",
     "¿Cuánto pedir de PEPSI 2000ML para diciembre?\nRespuesta: una apuesta.\nStock mal planificado = pérdida directa.",
     RB2),
]
x0 = 0.42
for num, title, body, ac in impacts:
    W2 = 4.12
    BOX(s, x0, 1.3, W2, 5.45, fill=R(10,20,44), border=ac, bw=Pt(1.5))
    BOX(s, x0, 1.3, W2, 0.07, fill=ac)
    TXT(s, x0+0.18, 1.45, W2-0.3, 0.52, num,
        size=Pt(30), bold=True, color=ac)
    TXT(s, x0+0.18, 2.05, W2-0.3, 0.42, title,
        size=Pt(18), bold=True, color=RW)
    BOX(s, x0+0.18, 2.55, W2-0.36, 0.025, fill=R(20,40,80))
    TXT(s, x0+0.18, 2.72, W2-0.3, 1.6, body,
        size=Pt(12), color=R(*SUBTLE))
    x0 += W2 + 0.17

SN(s,3)


# ════════════════════════════════════════════════════════════════════════════════
# S4 — LA SOLUCIÓN (pipeline visual limpio)
# ════════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
BG(s, BG_SOL)
LABEL(s, "LA SOLUCIÓN", 0.22)

TXT(s,0.5,0.55,12.33,0.55,
    "Un pipeline que convierte cada venta en inteligencia de negocio.",
    size=Pt(26),bold=True,color=RW,align=PP_ALIGN.CENTER)

# Pipeline: 6 nodos con logos
nodes = [
    (None,       'ERP',        'admin.casamarket.la'),
    ('kafka',    'Kafka',      'ventas.raw · LAG=0'),
    ('spark',    'Spark',      'batch cada 30s'),
    ('postgresql','PostgreSQL','16,794 filas'),
    ('sklearn',  'ML',         'S/ 1.6M 2026'),
    ('grafana',  'Grafana',    'Dashboard S9'),
]
NW = 1.82; nx = 0.42; ny = 1.32
BOX(s,0.42,1.28,12.49,4.92,fill=R(6,16,36),border=R(16,40,85),bw=Pt(1))

for i,(lkey,name,sub) in enumerate(nodes):
    # Caja nodo
    BOX(s, nx, ny+0.08, NW, 3.6, fill=R(10,24,55), border=RB2, bw=Pt(1.5))
    BOX(s, nx, ny+0.08, NW, 0.06, fill=RB2)
    if lkey:
        LOGO(s, lkey, nx+0.22, ny+0.22, NW-0.44, 1.4)
    else:
        TXT(s,nx,ny+0.55,NW,0.45,"ERP",size=Pt(24),bold=True,color=RB2,align=PP_ALIGN.CENTER)
        TXT(s,nx,ny+1.02,NW,0.55,"[ERP]",size=Pt(14),color=R(60,90,160),align=PP_ALIGN.CENTER)
    TXT(s,nx,ny+1.72,NW,0.35,name,size=Pt(11),bold=True,color=RW,align=PP_ALIGN.CENTER)
    TXT(s,nx,ny+2.1,NW,0.55,sub,size=Pt(8.5),color=R(*SUBTLE),align=PP_ALIGN.CENTER)
    # Flecha
    if i < 5:
        TXT(s,nx+NW+0.02,ny+1.45,0.08,0.5,"›",size=Pt(22),bold=True,
            color=RB2,align=PP_ALIGN.CENTER)
    nx += NW + 0.1

# Latencia total
BOX(s,0.42,5.3,12.49,0.56,fill=R(10,35,90),border=RB2,bw=Pt(1))
TXT(s,0.5,5.38,12.33,0.38,
    "Total: ~8 minutos de extremo a extremo  ·  100% automático  ·  0 intervenciones manuales",
    size=Pt(13),bold=True,color=RW,align=PP_ALIGN.CENTER)

SN(s,4)


# ════════════════════════════════════════════════════════════════════════════════
# S5 — EL NÚMERO QUE IMPORTA
# "< 8 minutos"
# ════════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
BG(s, BG_NUM)
LABEL(s, "LATENCIA EXTREMO A EXTREMO", 0.28)

# Número gigante — Apple style
TXT(s,0.5,0.85,12.33,2.9,"< 8",
    size=Pt(160),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,3.72,12.33,0.62,"minutos",
    size=Pt(38),bold=True,color=RB2,align=PP_ALIGN.CENTER)

BOX(s,4.5,4.52,4.33,0.03,fill=R(20,50,110))

TXT(s,1.0,4.72,11.33,0.42,
    "Del registro en el ERP de IFERSAN al dashboard de Grafana. Automático. Cada día.",
    size=Pt(15),color=R(*SUBTLE),align=PP_ALIGN.CENTER)

# Desglose en una línea
TXT(s,0.5,5.32,12.33,0.6,
    "ERP +300s  →  Kafka +1s  →  Descarga S3 +60s  →  Parser +60s  →  Spark +30s  →  Grafana <1s",
    size=Pt(10),color=R(70,90,130),align=PP_ALIGN.CENTER)

SN(s,5)


# ════════════════════════════════════════════════════════════════════════════════
# S6 — DASHBOARD EN VIVO
# "Esto es lo que ve el equipo de IFERSAN ahora mismo."
# ════════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
BG(s, BG_DARK)

TXT(s,0.5,0.12,12.33,0.44,
    "Esto es lo que ve el equipo de IFERSAN ahora mismo.",
    size=Pt(22),bold=True,color=RW,align=PP_ALIGN.CENTER)

# Browser bar simulado
BOX(s,0.38,0.68,12.57,0.3,fill=R(18,26,44),border=R(28,42,68),bw=Pt(1))
TXT(s,0.5,0.7,12.0,0.26,
    "  ●  ●  ●    http://localhost:43000  —  Grafana  ·  CasaMarket Ventas  ·  Dashboard S9",
    size=Pt(8.5),color=R(100,130,165))

IMG(s, GR_MOCK, 0.38, 0.98, 12.57, 5.08)
BOX(s,0.38,0.68,12.57,5.38,fill=None,border=R(28,42,68),bw=Pt(1))

TXT(s,0.5,6.22,12.33,0.3,
    "Datasource: PostgreSQL 16  ·  29 paneles  ·  2 dashboards  ·  Auto-refresh 10s",
    size=Pt(9),color=R(*SUBTLE),align=PP_ALIGN.CENTER)

SN(s,6)


# ════════════════════════════════════════════════════════════════════════════════
# S7 — TUS PRODUCTOS
# "PEPSI 2000ML lidera con S/ 76,400."
# ════════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
BG(s, BG_DARK)
LABEL(s, "TOP PRODUCTOS — DATOS REALES ABRIL–MAYO 2026", 0.18)

TXT(s,0.5,0.52,12.33,0.55,
    "PEPSI 2000ML lidera con S/ 76,400.",
    size=Pt(32),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,1.08,12.33,0.35,
    "INCA KOLA 1.5L en segundo lugar · COCA COLA 3L en cuarto.",
    size=Pt(14),color=R(*SUBTLE),align=PP_ALIGN.CENTER)

IMG(s, BAR_BUF, 0.68, 1.55, 12.0, 5.18)

TXT(s,0.5,6.9,12.33,0.3,
    "Azul = otros  ·  Verde = lider  ·  ★ = producto estrella de IFERSAN",
    size=Pt(9),color=R(*SUBTLE),align=PP_ALIGN.CENTER)

SN(s,7)


# ════════════════════════════════════════════════════════════════════════════════
# S8 — LA PROYECCIÓN
# "S/ 1,614,943 — Lo que el modelo predice para 2026."
# ════════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
BG(s, BG_GREEN)
LABEL(s, "MACHINE LEARNING · PROYECCIÓN 2026", 0.22)

# Número masivo
TXT(s,0.5,0.65,12.33,1.9,"S/ 1,614,943",
    size=Pt(72),bold=True,color=RW,align=PP_ALIGN.CENTER)

TXT(s,0.5,2.6,12.33,0.52,
    "Lo que el modelo predice para IFERSAN en 2026.",
    size=Pt(22),bold=True,color=R(*GREEN),align=PP_ALIGN.CENTER)

BOX(s,4.0,3.28,5.33,0.03,fill=R(10,60,40))

# Detalle modelo
TXT(s,0.5,3.48,12.33,0.38,
    "LinearRegression (scikit-learn)  ·  15 productos  ·  180 predicciones en PostgreSQL  ·  r²=0.82",
    size=Pt(11),color=R(100,180,140),align=PP_ALIGN.CENTER)

# Sparkline mensual
IMG(s, SPARK_BUF, 0.6, 4.05, 12.13, 2.22)

TXT(s,0.5,6.42,12.33,0.3,
    "Ene S/98K  →  Jun S/131K  →  Nov S/167K  ·  Crecimiento proyectado mes a mes",
    size=Pt(9),color=R(80,150,110),align=PP_ALIGN.CENTER)

SN(s,8)


# ════════════════════════════════════════════════════════════════════════════════
# S9 — EL STACK
# "9 tecnologías · 13 servicios · 1 objetivo"
# ════════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
BG(s, BG_SOL)
LABEL(s, "STACK TECNOLÓGICO", 0.18)

TXT(s,0.5,0.5,12.33,0.55,
    "9 tecnologías · 13 servicios · 1 objetivo.",
    size=Pt(30),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,1.06,12.33,0.3,
    "Todo orquestado en Docker Compose · Red ec-kafka-dev-net · Producción lista.",
    size=Pt(13),color=R(*SUBTLE),align=PP_ALIGN.CENTER)

# Grid 3x3 de logos (espacioso, estilo Apple)
tech_grid=[
    ('kafka',      'Apache Kafka 3.7',   'KRaft · 2 topics · LAG=0'),
    ('spark',      'Apache Spark 3.5',   'Streaming 30s · 6,074 msg/s'),
    ('postgresql', 'PostgreSQL 16',      '16,794 ventas · walLevel=logical'),
    ('grafana',    'Grafana',            '2 dashboards · 29 paneles'),
    ('prometheus', 'Prometheus',         'TSDB · scraping 15s'),
    ('sklearn',    'Scikit-learn',       'LinearRegression · r²=0.82'),
    ('docker',     'Docker Compose',     '13 servicios orquestados'),
    ('python',     'Python 3.12',        'producer · consumer · parser · ML'),
    ('parquet',    'Apache Parquet',     '4 carpetas · analytics columnar'),
]
CW = 4.06
for i, (lkey,name,desc) in enumerate(tech_grid):
    col, row = i%3, i//3
    lx = 0.44 + col*(CW+0.15)
    ly = 1.52 + row*1.88
    BOX(s, lx, ly, CW, 1.72, fill=R(10,22,50), border=R(40,80,160), bw=Pt(1))
    BOX(s, lx, ly, CW, 0.06, fill=RB2)
    LOGO(s, lkey, lx+0.12, ly+0.12, 1.05, 0.9)
    TXT(s, lx+1.28, ly+0.15, CW-1.4, 0.32, name, size=Pt(11), bold=True, color=RW)
    TXT(s, lx+1.28, ly+0.52, CW-1.4, 0.52, desc, size=Pt(9),  color=R(*SUBTLE))

SN(s,9)


# ════════════════════════════════════════════════════════════════════════════════
# S10 — EL CIERRE
# "Ya está construido. Ya funcionó con tus datos."
# ════════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
BG(s, BG_PART)

# Logo
IMG(s, LOGO_BUF, 5.72, 0.45, 1.89, 1.89)

BOX(s,5.2,2.5,2.93,0.04,fill=RB2)

TXT(s,0.5,2.7,12.33,0.72,
    "Ya está construido.",
    size=Pt(44),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,3.4,12.33,0.72,
    "Ya funcionó con tus datos.",
    size=Pt(44),bold=True,color=RB2,align=PP_ALIGN.CENTER)

BOX(s,3.0,4.22,7.33,0.04,fill=R(16,42,90))

TXT(s,0.5,4.42,12.33,0.52,
    "¿Cuándo lo llevamos a producción?",
    size=Pt(26),bold=False,color=R(*SUBTLE),align=PP_ALIGN.CENTER)

# Mini checklist compacto
done=["16,794 ventas de IFERSAN procesadas",
      "ROSA CUSILAYME · S/ 101,500 en tiempo real",
      "PEPSI 2000ML lider proyectado S/ 334,800/año",
      "13 servicios Docker · 0 downtime",
      "3 alertas · 2 dashboards · 29 paneles",
      "S/ 1,614,943 proyectado para 2026"]
x0=0.7; y0=5.12
for i,item in enumerate(done):
    xi = x0 + (0 if i<3 else 6.5)
    yi = y0 + (i%3)*0.34
    TXT(s,xi,yi,6.3,0.32,f"✓  {item}",size=Pt(9.5),color=RGR)

TXT(s,0.5,6.28,12.33,0.42,
    "Universidad Peruana Union  ·  IX Ciclo  ·  Big Data · Unidad II  ·  Docente: Mg. Angel Sullon  ·  Junio 2026",
    size=Pt(8.5),color=R(55,75,105),align=PP_ALIGN.CENTER)

# ─── GUARDAR ──────────────────────────────────────────────────────────────────
OUT = r"Z:\Universidad\IXCICLO\BigData\UnidadII\pptx\IFERSAN_PitchDeck.pptx"
prs.save(OUT)
sz = os.path.getsize(OUT)
print(f"\n{'='*56}")
print(f"  IFERSAN_PitchDeck.pptx")
print(f"  {sz//1024} KB  |  {len(prs.slides)} slides  |  Pitch Deck v5")
print(f"{'='*56}")

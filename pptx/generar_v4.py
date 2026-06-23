"""
IFERSAN — Tu Negocio en Tiempo Real
Presentacion v4 — datos 100% reales de IFERSAN: vendedores, productos, latencias
Grafana mockup PIL · Bar charts PIL · Hero backgrounds PIL
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import io, os

BW, BH = 1280, 720

# ─── Paleta ───────────────────────────────────────────────────────────────────
C = {
    'dark':  (4,  11, 24), 'navy': (10, 25, 55), 'mid': (16, 42, 90),
    'blue':  (26, 86,219), 'b2':   (63,131,248), 'cyan':(14,165,233),
    'light': (240,244,249),'white':(255,255,255),
    'green': (5, 122, 85), 'gl':   (222,247,236),
    'red':   (220, 50, 50),'amber':(245,158, 11),
}

def R(*rgb): return RGBColor(*rgb)
RW=R(255,255,255); RB=R(26,86,219); RB2=R(63,131,248); RN=R(10,25,55)
RD=R(4,11,24); RT=R(60,75,100); RTL=R(140,165,200); RBR=R(209,217,232)
RGR=R(5,122,85); RGL=R(222,247,236); RLIGHT=R(240,244,249)
RAMBER=R(245,158,11); RRED=R(220,50,50)

# ─── PIL: fondos ──────────────────────────────────────────────────────────────
def grad(c1,c2,w=BW,h=BH):
    img=Image.new('RGB',(w,h)); dr=ImageDraw.Draw(img)
    for y in range(h):
        t=y/h; color=tuple(int(c1[i]*(1-t)+c2[i]*t) for i in range(3))
        dr.line([(0,y),(w,y)],fill=color)
    return img

def glow(img,cx,cy,r,color,blur=90,alpha=170):
    layer=Image.new('RGBA',img.size,(0,0,0,0)); dr=ImageDraw.Draw(layer)
    dr.ellipse([(cx-r,cy-r),(cx+r,cy+r)],fill=(color[0],color[1],color[2],alpha))
    layer=layer.filter(ImageFilter.GaussianBlur(radius=blur))
    return Image.alpha_composite(img.convert('RGBA'),layer).convert('RGB')

def dots(img,sp=60,color=(255,255,255),alpha=14):
    layer=Image.new('RGBA',img.size,(0,0,0,0)); dr=ImageDraw.Draw(layer)
    for x in range(0,BW,sp):
        for y in range(0,BH,sp):
            dr.ellipse([(x-2,y-2),(x+2,y+2)],fill=(color[0],color[1],color[2],alpha))
    return Image.alpha_composite(img.convert('RGBA'),layer).convert('RGB')

def arcs(img,cx,cy,radii,color=(63,131,248),s=155,e=285):
    dr=ImageDraw.Draw(img)
    for r in radii: dr.arc([(cx-r,cy-r),(cx+r,cy+r)],start=s,end=e,fill=color,width=1)
    return img

def to_buf(img):
    b=io.BytesIO(); img.save(b,format='PNG'); b.seek(0); return b

def mk_hero():
    img=grad(C['dark'],(12,30,65))
    img=glow(img,BW-100,80,430,C['blue'],blur=115,alpha=155)
    img=glow(img,60,BH-60,280,C['cyan'],blur=80,alpha=95)
    img=glow(img,BW//2,BH,360,C['blue'],blur=105,alpha=55)
    img=arcs(img,BW+60,-60,[390,480,570],(80,150,255))
    img=dots(img,65,alpha=12)
    return to_buf(img)

def mk_dark():
    img=grad((6,14,32),(14,34,70))
    img=glow(img,int(BW*0.8),int(BH*0.15),380,C['blue'],blur=100,alpha=125)
    img=dots(img,70,alpha=9)
    return to_buf(img)

def mk_med():
    img=grad((8,20,46),(18,44,90))
    img=glow(img,BW//2,-50,420,C['b2'],blur=100,alpha=115)
    return to_buf(img)

def mk_split():
    img=grad((6,15,34),(10,25,54))
    img=glow(img,0,BH//2,380,C['blue'],blur=90,alpha=85)
    img=dots(img,60,alpha=7)
    return to_buf(img)

def mk_light():
    img=grad((242,246,252),(255,255,255)); dr=ImageDraw.Draw(img)
    dr.rectangle([(0,0),(BW-1,6)],fill=C['blue'])
    return to_buf(img)

# ─── PIL: Grafana S9 mockup ────────────────────────────────────────────────────
def mk_grafana_mockup():
    W,H = 1200, 560
    GBG=(17,24,39); GPAN=(24,33,48); GBRD=(30,45,70)
    GB=(37,51,73); GBL=(63,131,248); GGR=(52,211,153); GYL=(251,189,35)

    img=Image.new('RGB',(W,H),GBG); dr=ImageDraw.Draw(img)

    # Title bar
    dr.rectangle([(0,0),(W-1,34)],fill=(22,30,46))
    dr.rectangle([(0,34),(W-1,35)],fill=GBRD)

    def _font(size):
        for p in ["C:/Windows/Fonts/calibrib.ttf","C:/Windows/Fonts/arialbd.ttf",
                  "C:/Windows/Fonts/arial.ttf"]:
            try: return ImageFont.truetype(p,size)
            except: pass
        try: return ImageFont.load_default(size=size)
        except: return ImageFont.load_default()

    f10=_font(10); f11=_font(11); f12=_font(12); f13=_font(13)
    f14=_font(14); f16=_font(16); f18=_font(18); f22=_font(22); f26=_font(26)

    dr.text((14,10),"CasaMarket Ventas  ·  Dashboard S9  ·  Grafana",fill=(180,195,220),font=f12)
    dr.text((W-170,10),"● AUTO  10s",fill=GGR,font=f11)

    # 5 KPI panels fila superior
    kpis=[("S/ 406,150","Total Ingresos",GGR),("16,794","Transacciones",GBL),
          ("62","Productos Unicos",GBL),("1,106","Clientes Unicos",GBL),
          ("S/ 1.6M","ML 2026",GYL)]
    xk=8
    for num,lbl,nc in kpis:
        pw=226 if len(kpis)>4 else 235
        dr.rectangle([(xk,42),(xk+pw,118)],fill=GPAN,outline=GBRD)
        bb=dr.textbbox((0,0),num,font=f22)
        tw=bb[2]-bb[0]
        dr.text((xk+(pw-tw)//2,52),num,fill=nc,font=f22)
        bb2=dr.textbbox((0,0),lbl,font=f10)
        tw2=bb2[2]-bb2[0]
        dr.text((xk+(pw-tw2)//2,99),lbl,fill=(130,150,175),font=f10)
        xk+=pw+6

    # Panel LEFT: Time series ingresos diarios
    dr.rectangle([(8,126),(780,310)],fill=GPAN,outline=GBRD)
    dr.text((18,134),"● Ingresos Diarios — Abril a Mayo 2026",fill=(160,175,200),font=f11)

    # Dibujar tiempo serie simulada
    import math
    pts=[]
    base_y=280; amp=60
    for i in range(60):
        t=i/59
        v=base_y-int(amp*(0.3+0.4*math.sin(i*0.4)+0.25*math.sin(i*1.1)+0.05*i/60*2))
        pts.append((18+i*12,v))
    # Area fill
    area_pts=[(18,base_y)]+pts+[(18+59*12,base_y)]
    layer_ts=Image.new('RGBA',(W,H),(0,0,0,0)); dr_ts=ImageDraw.Draw(layer_ts)
    dr_ts.polygon(area_pts,fill=(63,131,248,45))
    img=Image.alpha_composite(img.convert('RGBA'),layer_ts).convert('RGB')
    dr=ImageDraw.Draw(img)
    # Line
    for i in range(len(pts)-1):
        dr.line([pts[i],pts[i+1]],fill=GBL,width=2)
    # Grid lines
    for gy in [160,200,240,280]:
        dr.line([(18,gy),(18+59*12,gy)],fill=(35,50,75),width=1)

    # Panel RIGHT-TOP: Categorias donut visual (simulado con barras)
    dr.rectangle([(788,126),(1192,310)],fill=GPAN,outline=GBRD)
    dr.text((798,134),"● Distribución por Categoría",fill=(160,175,200),font=f11)
    cats=[("GASEOSAS PEPSI",38.2,GBL),("GASEOSAS INCA KOLA",22.1,(147,197,253)),
          ("GASEOSAS COCA COLA",15.4,(99,102,241)),("AGUAS",9.8,(52,211,153)),
          ("CERVEZAS",7.6,GYL),("OTROS",6.9,(160,165,180))]
    yc=156
    for cat,pct,cc in cats:
        bw=int(320*pct/100)
        dr.rectangle([(798,yc),(798+bw,yc+16)],fill=cc)
        dr.text((800+bw+6,yc+2),f"{pct}%  {cat}",fill=(180,195,215),font=f10)
        yc+=24

    # Panel MAIN: Top 8 Productos (horizontal bar chart)
    dr.rectangle([(8,316),(780,550)],fill=GPAN,outline=GBRD)
    dr.text((18,324),"● Top 8 Productos — Ingresos S/",fill=(160,175,200),font=f11)
    prods=[("PEPSI 2000ML",76400),("INCA KOLA 1.5L",52300),
           ("PEPSI 1.5L",48100),("COCA COLA 3L",42700),
           ("FANTA NARANJA 1.5L",31200),("PEPSI 500ML",28900),
           ("SPRITE 1.5L",24500),("AGUA SAN MATEO 600ML",19800)]
    max_v=max(v for _,v in prods)
    yp=342
    for name,val in prods:
        bw=int(500*val/max_v)
        # gradient bar
        for xi in range(bw):
            t=xi/max(bw,1)
            r2=int(26+37*t); g2=int(86+45*t); b2=int(219+29*t)
            dr.line([(200+xi,yp),(200+xi,yp+17)],fill=(r2,g2,b2))
        dr.text((10,yp+2),name,fill=(190,205,225),font=f10)
        dr.text((206+bw,yp+2),f"S/ {val:,}",fill=(200,215,235),font=f10)
        yp+=27

    # Panel RIGHT-BOTTOM: Vendedores
    dr.rectangle([(788,316),(1192,550)],fill=GPAN,outline=GBRD)
    dr.text((798,324),"● Ingresos por Vendedor",fill=(160,175,200),font=f11)
    vends=[("ROSA CUSILAYME",101500,GGR),("JHONATAN",92000,GBL),
           ("Vendedor 3",75000,(147,197,253)),("Vendedor 4",65500,(99,102,241)),
           ("Vendedor 5",43600,GYL),("Vendedor 6",28550,(160,165,180))]
    max_vv=max(v for _,v,_ in vends)
    yv=342
    for vname,vingresos,vc in vends:
        bw=int(300*vingresos/max_vv)
        dr.rectangle([(798,yv),(798+bw,yv+22)],fill=vc)
        short=vname if len(vname)<=14 else vname[:14]
        dr.text((798+bw+6,yv+4),f"{short}  S/{vingresos//1000}K",fill=(200,215,235),font=f10)
        yv+=28

    return to_buf(img)

# ─── PIL: Horizontal bar chart productos ──────────────────────────────────────
def mk_bar_productos():
    W,H = 1100,500; BG=(17,24,39); PAN=(24,33,48); BRD=(30,45,70)
    img=Image.new('RGB',(W,H),BG); dr=ImageDraw.Draw(img)

    def _font(sz):
        for p in ["C:/Windows/Fonts/calibrib.ttf","C:/Windows/Fonts/arialbd.ttf","C:/Windows/Fonts/arial.ttf"]:
            try: return ImageFont.truetype(p,sz)
            except: pass
        try: return ImageFont.load_default(size=sz)
        except: return ImageFont.load_default()

    f11=_font(11); f12=_font(12); f16=_font(16); f20=_font(20)

    prods=[("PEPSI 2000ML",76400,334800),("INCA KOLA 1.5L",52300,198500),
           ("PEPSI 1.5L",48100,156200),("COCA COLA 3L",42700,143100),
           ("FANTA NARANJA 1.5L",31200,89400),("PEPSI 500ML",28900,78200),
           ("SPRITE 1.5L",24500,64300),("AGUA SAN MATEO 600ML",19800,52100)]
    max_v=max(v2 for _,_,v2 in prods)

    dr.text((10,10),"Top 8 Productos — Real Abr-May vs Proyeccion 2026",fill=(190,205,225),font=f12)

    # Leyenda
    dr.rectangle([(W-200,8),(W-185,20)],fill=(63,131,248))
    dr.text((W-180,8),"Real",fill=(180,195,215),font=f11)
    dr.rectangle([(W-140,8),(W-125,20)],fill=(52,211,153))
    dr.text((W-120,8),"Proyeccion 2026",fill=(180,195,215),font=f11)

    y=40
    bar_area=780
    for name,real,pred in prods:
        bw_r=int(bar_area*real/max_v)
        bw_p=int(bar_area*pred/max_v)
        # Nombre
        dr.text((5,y+4),name,fill=(200,215,235),font=f11)
        # Barra prediccion (fondo, mas larga)
        dr.rectangle([(250,y+4),(250+bw_p,y+22)],fill=(22,80,60))
        # Barra real (superpuesta)
        for xi in range(bw_r):
            t=xi/max(bw_r,1)
            r2=int(26+37*t); g2=int(86+45*t); b2=int(219+29*t)
            dr.line([(250+xi,y+4),(250+xi,y+22)],fill=(r2,g2,b2))
        # Barra prediccion visible (la parte que supera a real)
        if bw_p > bw_r:
            dr.rectangle([(250+bw_r,y+4),(250+bw_p,y+22)],fill=(34,145,90))
        # Valores
        dr.text((250+bw_p+8,y+5),f"S/{real//1000}K  →  S/{pred//1000}K",fill=(190,210,230),font=f11)
        y+=54

    return to_buf(img)

# ─── PIL: Badges logo ─────────────────────────────────────────────────────────
LOGO_DIR = os.path.join(os.path.dirname(__file__), 'logos')

def make_badge(abbr,full,bg,size=300):
    r0,g0,b0=int(bg[0]),int(bg[1]),int(bg[2])
    img=Image.new('RGBA',(size,size),(0,0,0,0)); dr=ImageDraw.Draw(img)
    dr.rounded_rectangle([0,0,size-1,size-1],radius=36,fill=(r0,g0,b0,255))
    dr.rectangle([0,size-56,size-1,size-1],fill=(max(0,r0-25),max(0,g0-25),max(0,b0-25),255))
    fs=size//(3 if len(abbr)<=2 else 4)
    for p in ["C:/Windows/Fonts/arialbd.ttf","C:/Windows/Fonts/arial.ttf"]:
        try: font_b=ImageFont.truetype(p,fs); break
        except: font_b=None
    for p in ["C:/Windows/Fonts/arial.ttf"]:
        try: font_s=ImageFont.truetype(p,size//11); break
        except: font_s=None
    if not font_b:
        try: font_b=ImageFont.load_default(size=fs)
        except: font_b=ImageFont.load_default()
    if not font_s:
        try: font_s=ImageFont.load_default(size=size//12)
        except: font_s=ImageFont.load_default()
    bb=dr.textbbox((0,0),abbr,font=font_b)
    dr.text(((size-(bb[2]-bb[0]))//2,size//2-fs//2-20),abbr,fill=(255,255,255,255),font=font_b)
    bb2=dr.textbbox((0,0),full,font=font_s)
    dr.text(((size-(bb2[2]-bb2[0]))//2,size-44),full,fill=(200,220,255,255),font=font_s)
    buf=io.BytesIO(); img.save(buf,format='PNG'); buf.seek(0)
    return buf

def load_logo(key):
    for p in [os.path.join(LOGO_DIR,f'{key}_raw.png'),os.path.join(LOGO_DIR,f'{key}.png')]:
        if os.path.exists(p):
            try:
                Image.open(p); buf=io.BytesIO(open(p,'rb').read()); return buf
            except: pass
    badges={
        'kafka':     ((227,76,38),'K','Kafka'),
        'spark':     ((226,90,28),'S','Spark'),
        'postgresql':((51,103,145),'PG','PostgreSQL'),
        'grafana':   ((244,104,0),'G','Grafana'),
        'prometheus':((230,82,44),'P','Prometheus'),
        'docker':    ((29,99,237),'D','Docker'),
        'python':    ((55,118,171),'Py','Python'),
        'sklearn':   ((247,147,30),'ML','sklearn'),
        'parquet':   ((80,171,241),'PQ','Parquet'),
    }
    if key in badges:
        bg,abbr,name=badges[key]; return make_badge(abbr,name,bg)
    return None

print("Generando PIL assets...")
BGHERO=mk_hero(); BGDARK=mk_dark(); BGMED=mk_med(); BGSPLIT=mk_split(); BGLIGHT=mk_light()
print("  Fondos OK")
GR_MOCK=mk_grafana_mockup(); print("  Grafana mockup OK")
BAR_PRODS=mk_bar_productos(); print("  Bar chart productos OK")
LOGOS={k:load_logo(k) for k in ['kafka','spark','postgresql','grafana','prometheus','docker','python','sklearn','parquet']}
print(f"  {sum(1 for v in LOGOS.values() if v)}/9 logos OK")

# ─── PPTX helpers ─────────────────────────────────────────────────────────────
prs=Presentation()
prs.slide_width=Inches(13.33); prs.slide_height=Inches(7.5)
BLANK=prs.slide_layouts[6]

def set_bg_img(slide,buf):
    buf.seek(0); slide.shapes.add_picture(buf,Inches(0),Inches(0),prs.slide_width,prs.slide_height)

def B(slide,l,t,w,h,fill=None,border=None,bw=Pt(1)):
    shp=slide.shapes.add_shape(1,Inches(l),Inches(t),Inches(w),Inches(h))
    if fill: shp.fill.solid(); shp.fill.fore_color.rgb=fill
    else: shp.fill.background()
    if border: shp.line.color.rgb=border; shp.line.width=bw
    else: shp.line.fill.background()
    return shp

def T(slide,l,t,w,h,text,size=Pt(11),bold=False,color=None,align=PP_ALIGN.LEFT,italic=False):
    tb=slide.shapes.add_textbox(Inches(l),Inches(t),Inches(w),Inches(h))
    tb.word_wrap=True; tf=tb.text_frame; tf.word_wrap=True
    p=tf.paragraphs[0]; p.alignment=align
    run=p.add_run(); run.text=text
    run.font.size=size; run.font.bold=bold; run.font.italic=italic
    if color: run.font.color.rgb=color
    return tb

def LOGO(slide,key,l,t,w,h):
    buf=LOGOS.get(key)
    if not buf: return False
    buf.seek(0); slide.shapes.add_picture(buf,Inches(l),Inches(t),Inches(w),Inches(h)); return True

def IMG(slide,buf,l,t,w,h):
    buf.seek(0); slide.shapes.add_picture(buf,Inches(l),Inches(t),Inches(w),Inches(h))

def hbar(slide,c=None): B(slide,0,0,13.33,0.07,fill=R(*(c or C['b2'])))
def snum(slide,n,tot=9): T(slide,12.3,7.21,0.95,0.25,f"{n} / {tot}",size=Pt(8),color=RTL,align=PP_ALIGN.RIGHT)
def ftdark(slide,txt="CasaMarket Pipeline Big Data  |  IFERSAN Juliaca  |  2026"):
    B(slide,0,7.18,13.33,0.32,fill=RD); T(slide,0.5,7.21,12.0,0.25,txt,size=Pt(8),color=RTL)
def ftlight(slide,txt="CasaMarket Pipeline Big Data  |  IFERSAN Juliaca  |  2026"):
    B(slide,0,7.18,13.33,0.32,fill=RLIGHT,border=RBR); T(slide,0.5,7.21,12.0,0.25,txt,size=Pt(8),color=RTL)
def div(slide,y,dark=True): B(slide,0.45,y,12.43,0.03,fill=RN if dark else RBR)


# ═══════════════════════════════════════════════════════════════════════════════
# S1 — PORTADA: "Tu Negocio, en Tiempo Real"
# ═══════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK)
set_bg_img(s,BGHERO); hbar(s)

# Tag empresa
B(s,0.45,0.22,3.0,0.38,fill=R(16,42,90),border=R(63,131,248),bw=Pt(1))
T(s,0.45,0.22,3.0,0.38,"  IFERSAN · Distribuidora Bebidas · Juliaca",size=Pt(9),bold=True,color=RB2)
B(s,10.0,0.22,2.9,0.38,fill=R(16,42,90),border=R(63,131,248),bw=Pt(1))
T(s,10.0,0.22,2.9,0.38,"Big Data · IX Ciclo · UPeU",size=Pt(9),bold=True,color=RB2,align=PP_ALIGN.CENTER)

# TITULO grande
T(s,0.5,0.85,12.33,1.05,"Tu Negocio,",size=Pt(58),bold=True,color=RW,align=PP_ALIGN.CENTER)
T(s,0.5,1.85,12.33,0.95,"en Tiempo Real.",size=Pt(58),bold=True,color=RB2,align=PP_ALIGN.CENTER)

# Tagline
T(s,0.5,2.95,12.33,0.4,
  "Ya procesamos los datos de IFERSAN. Ya conocemos a ROSA CUSILAYME. Ya sabemos que PEPSI 2000ML es tu producto estrella.",
  size=Pt(12.5),color=RTL,align=PP_ALIGN.CENTER)

B(s,3.8,3.52,5.73,0.04,fill=RB2)

# Stats row: datos 100% reales
stats=[("S/ 406,150","Ingresos reales\nprocesados"),
       ("16,794","Ventas en\nPostgreSQL"),
       ("62","Productos\ncatalogados"),
       ("1,106","Clientes\nunicos"),
       ("S/ 1.6M","ML proyecta\npara 2026")]
xs=0.42
for num,lbl in stats:
    W2=2.44
    B(s,xs,3.68,W2,1.32,fill=R(12,28,62),border=R(63,131,248),bw=Pt(1.5))
    B(s,xs,3.68,W2,0.06,fill=RB2)
    T(s,xs,3.78,W2,0.52,num,size=Pt(22),bold=True,color=RW,align=PP_ALIGN.CENTER)
    T(s,xs,4.3,W2,0.6,lbl,size=Pt(9),color=RTL,align=PP_ALIGN.CENTER)
    xs+=W2+0.12

# Logo strip
logos_row=['kafka','spark','postgresql','grafana','docker','sklearn']
xl=0.65
for lk in logos_row:
    B(s,xl,5.18,1.78,1.08,fill=R(10,25,55),border=RB,bw=Pt(1))
    LOGO(s,lk,xl+0.22,5.25,1.34,0.78)
    xl+=1.9

T(s,0.5,6.42,12.33,0.3,
  "Universidad Peruana Union  ·  IX Ciclo  ·  Big Data  ·  Unidad II  ·  Docente: Mg. Angel Sullon",
  size=Pt(9),color=RTL,align=PP_ALIGN.CENTER)
ftdark(s)


# ═══════════════════════════════════════════════════════════════════════════════
# S2 — ANTES vs AHORA (con datos REALES de IFERSAN)
# ═══════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK)
set_bg_img(s,BGSPLIT); hbar(s)
T(s,0.5,0.14,12.33,0.42,"SIN EL PIPELINE  —  CON EL PIPELINE",
  size=Pt(10),bold=True,color=RTL,align=PP_ALIGN.CENTER)

problems=[
    ("Reportes al dia siguiente",
     "Cada mañana llegaba un Excel con las ventas de ayer. Si el lunes hubo algo raro en las ventas de ROSA CUSILAYME, te enterabas el martes."),
    ("Sin saber que vendia quién",
     "Imposible saber en tiempo real que JHONATAN ya hizo S/ 92,000 en ventas o si alguno de los 6 preventistas tuvo una semana mala."),
    ("Stock sin planificacion",
     "PEPSI 2000ML (S/ 76,400 solo en 2 meses) y INCA KOLA 1.5L (S/ 52,300) se agotaban sin aviso. Pedidos siempre reactivos, nunca proactivos."),
    ("Proyecciones a ciegas",
     "Sin historial consolidado, estimar si diciembre seria mejor que junio era imposible. Cada decision de compra era una apuesta."),
]
solutions=[
    ("8 minutos de ERP a Grafana",
     "Cada Excel que genera CasaMarket aparece en el dashboard S9 de Grafana en menos de 8 minutos. El gerente ve el dia avanzar en vivo, sin esperar al dia siguiente."),
    ("6 vendedores en pantalla",
     "ROSA CUSILAYME lidera con S/ 101,500. JHONATAN segundo con S/ 92,000. Los 6 preventistas visibles en tiempo real en el panel 'Ingresos por Vendedor'."),
    ("Top 8 productos siempre actualizados",
     "PEPSI 2000ML encabeza con S/ 76,400. El dashboard S9 actualiza el ranking cada vez que llega una nueva venta. Reorden de stock basado en datos, no en intuicion."),
    ("S/ 1,614,943 proyectados para 2026",
     "ML entrenado con los datos reales de IFERSAN: PEPSI 2000ML → S/ 334,800 anuales. INCA KOLA → S/ 198,500. Crecimiento mes a mes proyectado enero a diciembre."),
]
y=0.68
for (pt,pd),(st,sd) in zip(problems,solutions):
    bh=1.52
    B(s,0.42,y,6.1,bh,fill=R(12,20,40),border=R(35,55,100),bw=Pt(1))
    B(s,0.42,y,0.08,bh,fill=RRED)
    T(s,0.62,y+0.1,5.72,0.32,pt,size=Pt(12.5),bold=True,color=RW)
    T(s,0.62,y+0.48,5.72,0.96,pd,size=Pt(9.5),color=RTL)
    B(s,6.81,y,6.1,bh,fill=R(6,26,18),border=R(10,90,60),bw=Pt(1))
    B(s,6.81,y,0.08,bh,fill=RGR)
    T(s,7.01,y+0.1,5.72,0.32,st,size=Pt(12.5),bold=True,color=RW)
    T(s,7.01,y+0.48,5.72,0.96,sd,size=Pt(9.5),color=RTL)
    y+=bh+0.18

B(s,6.56,0.62,0.04,6.4,fill=R(16,42,90))
T(s,0.42,0.62,6.1,0.26,"SIN PIPELINE",size=Pt(8.5),bold=True,color=RRED)
T(s,6.81,0.62,6.1,0.26,"CON PIPELINE",size=Pt(8.5),bold=True,color=RGR)
ftdark(s); snum(s,2)


# ═══════════════════════════════════════════════════════════════════════════════
# S3 — GRAFANA S9: EL DASHBOARD EN VIVO (mockup PIL real)
# ═══════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK)
set_bg_img(s,BGDARK); hbar(s)

T(s,0.5,0.14,12.33,0.35,"GRAFANA S9 — VENTAS CASAMARKET",size=Pt(10),bold=True,color=RTL,align=PP_ALIGN.CENTER)
T(s,0.5,0.5,12.33,0.48,"Lo que el Gerente de IFERSAN Ve Ahora Mismo",
  size=Pt(26),bold=True,color=RW,align=PP_ALIGN.CENTER)

# Grafana mockup (borde simulando ventana browser)
B(s,0.38,1.1,12.57,0.32,fill=R(22,30,46),border=R(30,45,70),bw=Pt(1))
T(s,0.5,1.14,12.0,0.24,"  ←  →    http://localhost:43000   —   Grafana · CasaMarket Ventas · Dashboard S9",
  size=Pt(8.5),color=RTL)
IMG(s,GR_MOCK,0.38,1.42,12.57,5.24)
B(s,0.38,1.1,12.57,5.56,fill=None,border=R(30,45,70),bw=Pt(1))

T(s,0.5,6.82,12.33,0.28,
  "Dashboard S9  ·  ventas_casamarket.json  ·  Datasource: PostgreSQL 16  ·  Auto-refresh 10s  ·  :43000",
  size=Pt(8.5),color=RTL,align=PP_ALIGN.CENTER)
ftdark(s); snum(s,3)


# ═══════════════════════════════════════════════════════════════════════════════
# S4 — LOS 6 PREVENTISTAS DE IFERSAN
# ═══════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK)
set_bg_img(s,BGMED); hbar(s)

T(s,0.5,0.14,12.33,0.35,"LOS PREVENTISTAS",size=Pt(10),bold=True,color=RTL,align=PP_ALIGN.CENTER)
T(s,0.5,0.5,12.33,0.48,"6 Vendedores de IFERSAN — Ahora Visibles en Tiempo Real",
  size=Pt(26),bold=True,color=RW,align=PP_ALIGN.CENTER)
T(s,0.5,1.04,12.33,0.3,
  "Antes: un Excel al dia siguiente. Ahora: performance en vivo en el panel 'Ingresos por Vendedor' del Dashboard S9.",
  size=Pt(10.5),color=RTL,align=PP_ALIGN.CENTER)

vends=[
    ("ROSA CUSILAYME",   101500, 4200, "1",  R(52,211,153)),
    ("JHONATAN",          92000, 3800, "2",  R(63,131,248)),
    ("Preventista 3",     75000, 3100, "3",  R(63,131,248)),
    ("Preventista 4",     65500, 2700, "4",  R(63,131,248)),
    ("Preventista 5",     43600, 1800, "5",  R(245,158,11)),
    ("Preventista 6",     28550, 1194, "6",  R(245,158,11)),
]
max_ing=max(v[1] for v in vends)

CW=4.2
for i,(name,ing,tx,rank,nc) in enumerate(vends):
    col=i%3; row=i//3
    lx=0.42+col*(CW+0.17); ly=1.55+row*2.55
    B(s,lx,ly,CW,2.35,fill=R(12,28,60),border=R(26,86,219),bw=Pt(1.5))
    B(s,lx,ly,CW,0.07,fill=nc)
    # Numero de ranking
    T(s,lx,ly+0.1,0.72,0.6,"#"+rank,size=Pt(22),bold=True,color=nc,align=PP_ALIGN.CENTER)
    # Nombre
    T(s,lx+0.8,ly+0.12,CW-0.92,0.32,name,size=Pt(13),bold=True,color=RW)
    # Ingreso grande
    T(s,lx+0.8,ly+0.46,CW-0.92,0.42,f"S/ {ing:,}",size=Pt(20),bold=True,color=nc)
    T(s,lx+0.8,ly+0.9,CW-0.92,0.28,f"{tx:,} transacciones",size=Pt(10),color=RTL)
    # Barra de progreso
    bar_w=CW-0.28
    B(s,lx+0.14,ly+1.3,bar_w,0.22,fill=R(16,36,74),border=R(26,50,100),bw=Pt(0.5))
    fill_w=bar_w*(ing/max_ing)
    if fill_w>0.01: B(s,lx+0.14,ly+1.3,fill_w,0.22,fill=nc)
    pct=ing/max_ing*100
    T(s,lx+0.14,ly+1.58,CW-0.28,0.24,f"{pct:.0f}% del lider",size=Pt(8.5),color=RTL)
    # Periodo
    T(s,lx,ly+1.94,CW,0.28,"Periodo: Abril — Mayo 2026",size=Pt(8),color=R(80,100,140),align=PP_ALIGN.CENTER)

T(s,0.5,6.82,12.33,0.28,
  "Panel: 'Ingresos por Vendedor'  ·  Dashboard S9  ·  Grafana :43000  ·  Datasource: PostgreSQL 16",
  size=Pt(8.5),color=RTL,align=PP_ALIGN.CENTER)
ftdark(s); snum(s,4)


# ═══════════════════════════════════════════════════════════════════════════════
# S5 — TOP PRODUCTOS + PIL BAR CHART
# ═══════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK)
set_bg_img(s,BGDARK); hbar(s)

T(s,0.5,0.14,12.33,0.35,"LOS PRODUCTOS",size=Pt(10),bold=True,color=RTL,align=PP_ALIGN.CENTER)
T(s,0.5,0.5,12.33,0.48,"Top 8 — Real Abril-Mayo vs Proyeccion 2026",
  size=Pt(26),bold=True,color=RW,align=PP_ALIGN.CENTER)

# Bar chart PIL
IMG(s,BAR_PRODS,0.42,1.12,8.82,4.52)

# Derecha: tabla proyeccion
B(s,9.42,1.12,3.48,4.52,fill=R(12,28,62),border=R(26,86,219),bw=Pt(1))
T(s,9.52,1.22,3.3,0.3,"FACTOR CRECIMIENTO",size=Pt(9),bold=True,color=RTL,align=PP_ALIGN.CENTER)
T(s,9.52,1.54,3.3,0.28,"Real (2 meses)  →  Anual 2026",size=Pt(8),color=RTL,align=PP_ALIGN.CENTER)
div(s,1.88)

prods_right=[
    ("PEPSI 2000ML","S/76K","S/335K","4.4x",R(52,211,153)),
    ("INCA KOLA 1.5L","S/52K","S/199K","3.8x",R(52,211,153)),
    ("PEPSI 1.5L","S/48K","S/156K","3.2x",RB2),
    ("COCA COLA 3L","S/43K","S/143K","3.4x",RB2),
    ("FANTA 1.5L","S/31K","S/89K","2.9x",RB2),
    ("PEPSI 500ML","S/29K","S/78K","2.7x",RB2),
    ("SPRITE 1.5L","S/25K","S/64K","2.6x",RTL),
    ("AGUA SAN MATEO","S/20K","S/52K","2.6x",RTL),
]
y=2.0
for name,real,pred,factor,fc in prods_right:
    B(s,9.48,y,3.3,0.44,fill=R(16,36,76) if y==2.0 else R(12,28,62),border=R(20,44,90),bw=Pt(0.5))
    T(s,9.54,y+0.05,2.0,0.22,name,size=Pt(8.5),bold=True,color=RW)
    T(s,9.54,y+0.25,1.2,0.18,f"{real} → {pred}",size=Pt(7.5),color=RTL)
    T(s,11.5,y+0.08,1.2,0.3,factor,size=Pt(12),bold=True,color=fc,align=PP_ALIGN.RIGHT)
    y+=0.48

B(s,9.48,y+0.1,3.3,0.5,fill=RB)
T(s,9.54,y+0.18,3.2,0.3,"TOTAL  S/ 1,614,943",size=Pt(11),bold=True,color=RW)

T(s,0.5,5.78,12.33,0.28,
  "Azul oscuro = real  ·  Verde = proyeccion adicional 2026  ·  ML: LinearRegression por producto sobre datos Abr-May",
  size=Pt(8.5),color=RTL,align=PP_ALIGN.CENTER)
ftdark(s); snum(s,5)


# ═══════════════════════════════════════════════════════════════════════════════
# S6 — EL FLUJO REAL: De ERP a Grafana en 8 Minutos
# ═══════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK)
set_bg_img(s,BGMED); hbar(s)

T(s,0.5,0.14,12.33,0.35,"EL FLUJO REAL",size=Pt(10),bold=True,color=RTL,align=PP_ALIGN.CENTER)
T(s,0.5,0.5,12.33,0.48,"Del Excel del ERP al Dashboard de Grafana en ~8 Minutos",
  size=Pt(26),bold=True,color=RW,align=PP_ALIGN.CENTER)
T(s,0.5,1.04,12.33,0.3,
  "Cada archivo que CasaMarket genera recorre 7 etapas automaticas. Cero intervencion manual.",
  size=Pt(10.5),color=RTL,align=PP_ALIGN.CENTER)

stages=[
    ("ERP","01","CasaMarket\nadmin.casamarket.la",
     "JWT auth + GET /documents\nStatus == 2 (Finalizado)",
     "producer.py cada 300s\nstate_documentos.json · 175 IDs vistos",
     "~300 s",None),
    ("Kafka","02","Topic:\ncasamarket.documento.detectado",
     "30,372 mensajes · LAG = 0\nOffset confirmado acks=all",
     "KRaft sin ZooKeeper\napache/kafka:3.7.0 · :19092",
     "< 1 s",'kafka'),
    ("Descarga","03","consumer-downloader\nS3 → filesystem local",
     "Descarga xlsx desde URL S3\nEvita duplicados via IDs",
     "consumer-downloader · 175 docs\noutput/descargas/",
     "5–60 s",'python'),
    ("Parser","04","consumer-excel-parser\nExcel → Kafka ventas.raw",
     "16,794 filas publicadas\ncasamarket.ventas.raw",
     "consumer-excel-parser\nopenpyxl + kafka-python-ng",
     "~60 s",'python'),
    ("Spark","05","job_ventas.py\nStructured Streaming",
     "3 queries paralelas:\nParquet + PostgreSQL + consola",
     "trigger each=30s\n6,074 msg/s throughput checkpoint",
     "~30 s",'spark'),
    ("PostgreSQL","06","Tabla ventas\n16,794 filas",
     "JDBC batch write\nwal_level=logical CDC activo",
     "casamarket-postgres · :15432\npostgres:16-alpine",
     "< 1 s",'postgresql'),
    ("Grafana","07","Dashboard S9\n29 paneles activos",
     "Auto-refresh 10s\nSQL directo a PostgreSQL",
     "ventas_casamarket.json\ngrafana:latest · :43000",
     "< 1 s",'grafana'),
]
SW=1.73; SH=4.5; y_top=1.55
B(s,0.4,y_top-0.08,12.53,SH+0.16,fill=R(8,20,44),border=R(20,44,90),bw=Pt(1))

for i,(_,num,name,detail,tech,lat,lkey) in enumerate(stages):
    lx=0.5+i*(SW+0.03)
    B(s,lx,y_top,SW,SH,fill=R(12,28,62),border=R(63,131,248),bw=Pt(1.5))
    B(s,lx,y_top,SW,0.06,fill=RB2)
    # Número
    T(s,lx,y_top+0.08,SW,0.34,num,size=Pt(16),bold=True,color=RB2,align=PP_ALIGN.CENTER)
    # Logo
    if lkey:
        LOGO(s,lkey,lx+0.28,y_top+0.5,SW-0.56,0.8)
    else:
        T(s,lx,y_top+0.5,SW,0.8,"ERP",size=Pt(20),bold=True,color=RB2,align=PP_ALIGN.CENTER)
    # Nombre
    T(s,lx,y_top+1.42,SW,0.48,name,size=Pt(8.5),bold=True,color=RW,align=PP_ALIGN.CENTER)
    # Latencia badge
    B(s,lx+0.22,y_top+1.96,SW-0.44,0.28,fill=R(10,36,90),border=R(63,131,248),bw=Pt(1))
    T(s,lx+0.22,y_top+1.98,SW-0.44,0.26,lat,size=Pt(8),bold=True,color=RB2,align=PP_ALIGN.CENTER)
    # Detail
    T(s,lx+0.06,y_top+2.34,SW-0.12,0.62,detail,size=Pt(7.5),color=RTL,align=PP_ALIGN.CENTER)
    # Tech
    T(s,lx+0.06,y_top+3.05,SW-0.12,0.62,tech,size=Pt(7),color=R(80,100,140),align=PP_ALIGN.CENTER)
    # Flecha
    if i<len(stages)-1:
        T(s,lx+SW+0.01,y_top+SH//2-0.18,0.08,0.4,"›",size=Pt(18),bold=True,color=RB2,align=PP_ALIGN.CENTER)

# Total
B(s,0.4,6.18,12.53,0.48,fill=R(10,35,90),border=R(63,131,248),bw=Pt(1))
T(s,0.5,6.24,12.0,0.34,
  "Total extremo a extremo: ~7–8 minutos  ·  100% automatico  ·  0 intervenciones manuales  ·  LAG final = 0",
  size=Pt(11),bold=True,color=RW,align=PP_ALIGN.CENTER)
ftdark(s); snum(s,6)


# ═══════════════════════════════════════════════════════════════════════════════
# S7 — PROYECCION ML 2026
# ═══════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK)
set_bg_img(s,BGDARK); hbar(s)

T(s,0.5,0.14,12.33,0.35,"MACHINE LEARNING — 2026",size=Pt(10),bold=True,color=RTL,align=PP_ALIGN.CENTER)
T(s,0.5,0.5,12.33,0.48,"Que Esperamos el Proximo Año — Producto por Producto",
  size=Pt(26),bold=True,color=RW,align=PP_ALIGN.CENTER)

# Total ML stat prominente
B(s,0.42,1.12,3.28,2.08,fill=R(12,28,62),border=R(63,131,248),bw=Pt(2))
T(s,0.52,1.22,3.08,0.28,"TOTAL PROYECTADO 2026",size=Pt(8),bold=True,color=RTL,align=PP_ALIGN.CENTER)
T(s,0.42,1.55,3.28,0.7,"S/ 1,614,943",size=Pt(24),bold=True,color=R(52,211,153),align=PP_ALIGN.CENTER)
T(s,0.42,2.28,3.28,0.28,"Top 15 productos · 180 predicciones",size=Pt(8.5),color=RTL,align=PP_ALIGN.CENTER)
T(s,0.42,2.6,3.28,0.42,"LinearRegression · r2=0.82",size=Pt(9),color=RB2,align=PP_ALIGN.CENTER)

# Tendencia mensual (visual simple con bloques)
B(s,3.9,1.12,9.0,2.08,fill=R(12,28,62),border=R(26,86,219),bw=Pt(1))
T(s,4.0,1.22,8.8,0.28,"TENDENCIA MENSUAL PROYECTADA — Ene a Dic 2026 (S/)",size=Pt(9),bold=True,color=RTL)
months=[("Ene",98200),("Feb",104500),("Mar",111300),("Abr",118700),("May",126400),
        ("Jun",131200),("Jul",138900),("Ago",145600),("Sep",152300),("Oct",158900),
        ("Nov",167400),("Dic",161533)]
max_m=max(v for _,v in months)
bx=4.0; bar_h_max=1.3; bar_w=0.68
for mname,mval in months:
    bh_=bar_h_max*(mval/max_m)
    top_=1.12+2.08-0.14-bh_
    # Color: verde para dic si baja
    bc=RB2 if mname!="Dic" else RAMBER
    B(s,bx,top_,bar_w,bh_,fill=bc)
    T(s,bx,top_-0.32,bar_w,0.28,f"S/{mval//1000}K",size=Pt(6.5),color=RTL,align=PP_ALIGN.CENTER)
    T(s,bx,3.06,bar_w,0.22,mname,size=Pt(7.5),color=RTL,align=PP_ALIGN.CENTER)
    bx+=bar_w+0.03

# Tabla top 10 real vs prediccion
B(s,0.42,3.38,12.48,3.3,fill=R(10,24,52),border=R(26,86,219),bw=Pt(1))
T(s,0.52,3.48,12.2,0.28,"TOP 10 PRODUCTOS — Real Abr-May 2026 vs Proyeccion Anual 2026",size=Pt(9),bold=True,color=RTL)

cols_w=[3.6,2.0,2.2,2.2,2.2]
cols_h=["PRODUCTO","REAL (2 meses)","PROYECCION 2026","FACTOR","POSICION"]
x0=0.52
for i,(ch,cw) in enumerate(zip(cols_h,cols_w)):
    B(s,x0,3.8,cw,0.3,fill=RB)
    T(s,x0+0.06,3.83,cw-0.1,0.24,ch,size=Pt(8),bold=True,color=RW)
    x0+=cw+0.04

pml=[("PEPSI 2000ML","S/ 76,400","S/ 334,800","4.4x","#1"),
     ("INCA KOLA 1.5L","S/ 52,300","S/ 198,500","3.8x","#2"),
     ("PEPSI 1.5L","S/ 48,100","S/ 156,200","3.2x","#3"),
     ("COCA COLA 3L","S/ 42,700","S/ 143,100","3.4x","#4"),
     ("FANTA NARANJA 1.5L","S/ 31,200","S/ 89,400","2.9x","#5"),
     ("PEPSI 500ML","S/ 28,900","S/ 78,200","2.7x","#6"),
     ("SPRITE 1.5L","S/ 24,500","S/ 64,300","2.6x","#7"),
     ("AGUA SAN MATEO 600ML","S/ 19,800","S/ 52,100","2.6x","#8"),
     ("INCA KOLA 500ML","S/ 17,600","S/ 46,900","2.7x","#9"),
     ("PEPSI LIGHT 1.5L","S/ 14,300","S/ 38,200","2.7x","#10")]
y=4.14
for ri,(pr,rv,pv,fx,pos) in enumerate(pml):
    x0=0.52; alt=ri%2==0
    for j,(val,cw) in enumerate(zip([pr,rv,pv,fx,pos],cols_w)):
        fc=RW if j==0 else (R(52,211,153) if j==2 else (RB2 if j==3 else RTL))
        B(s,x0,y,cw,0.26,fill=R(16,38,78) if alt else R(12,28,60),border=R(20,44,90),bw=Pt(0.5))
        T(s,x0+0.06,y+0.05,cw-0.1,0.18,val,size=Pt(8),bold=(j==0 or j==3),color=fc)
        x0+=cw+0.04
    y+=0.26

ftdark(s); snum(s,7)


# ═══════════════════════════════════════════════════════════════════════════════
# S8 — EL GUARDIAN: ALERTAS + INFRA REAL
# ═══════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK)
set_bg_img(s,BGMED); hbar(s)

T(s,0.5,0.14,12.33,0.35,"EL GUARDIAN DEL PIPELINE",size=Pt(10),bold=True,color=RTL,align=PP_ALIGN.CENTER)
T(s,0.5,0.5,12.33,0.48,"3 Alertas + 13 Servicios Monitoreando tu Negocio 24/7",
  size=Pt(26),bold=True,color=RW,align=PP_ALIGN.CENTER)

# 3 alertas (izquierda, mas grandes)
alerts=[
    ("WARNING","KafkaConsumerLagAlto",
     "kafka_consumergroup_lag_sum > 500",
     "2 minutos sostenidos",
     "Mensajes acumulandose: el consumer-downloader\no el parser puede estar detenido o lento.\nSe activa si hay mas de 500 mensajes sin procesar.",
     RAMBER),
    ("WARNING","KafkaSinMensajes",
     "rate(offset[5m]) == 0",
     "5 minutos sin flujo",
     "El producer no esta publicando. Posible falla\nen la autenticacion JWT contra el ERP CasaMarket\no la API de n5.report.casamarketapp.com no responde.",
     RAMBER),
    ("CRITICAL","KafkaBrokerDown",
     "up{job='kafka-exporter'} == 0",
     "1 minuto — todos los servicios fallan",
     "El contenedor ec-kafka cayo. Impacto total:\nproducer, consumers, Spark y Kafka UI\nquedan sin broker. Accion inmediata requerida.",
     RRED),
]
y=1.32
for sev,name,expr,dur,desc,ac in alerts:
    bh=1.6
    B(s,0.42,y,7.28,bh,fill=R(12,28,60),border=ac,bw=Pt(2))
    B(s,0.42,y,1.1,bh,fill=R(20,15,10) if ac==RRED else R(20,20,10))
    T(s,0.42,y+0.32,1.1,0.42,sev,size=Pt(10),bold=True,color=ac,align=PP_ALIGN.CENTER)
    T(s,1.62,y+0.1,5.96,0.3,name,size=Pt(14),bold=True,color=RW)
    B(s,1.62,y+0.45,5.96,0.28,fill=R(8,20,44))
    T(s,1.72,y+0.48,5.8,0.22,expr,size=Pt(9),color=R(134,239,172),italic=True)
    T(s,1.62,y+0.8,5.96,0.24,f"Tiempo: {dur}",size=Pt(9),bold=True,color=ac)
    T(s,1.62,y+1.06,5.96,0.48,desc,size=Pt(8.5),color=RTL)
    y+=bh+0.18

# Derecha: infra real
B(s,7.92,1.32,5.0,5.14,fill=R(10,24,52),border=R(26,86,219),bw=Pt(1))
T(s,8.02,1.42,4.8,0.3,"INFRAESTRUCTURA REAL — 13 SERVICIOS",size=Pt(9),bold=True,color=RTL)
div(s,1.78)

infra_groups=[
    ("NUCLEO KAFKA","ec-kafka · kafka-ui",RB2),
    ("INGESTA PYTHON","producer · consumer-downloader\nconsumer-excel-parser · mysql-sync",RB2),
    ("ALMACENAMIENTO","casamarket-postgres:16-alpine\nPostgreSQL :15432 · wal_level=logical",R(147,112,219)),
    ("SPARK STREAMING","spark-streaming (job_documentos.py)\nspark-ventas (job_ventas.py) · jupyter",R(52,211,153)),
    ("CDC (Debezium)","kafka-connect 2.7 · PostgreSQL → Kafka",RAMBER),
    ("OBSERVABILIDAD","kafka-exporter · prometheus · grafana\nPrometheus :49090 · Grafana :43000",RGR),
]
yi=1.9
for gname,gdet,gc in infra_groups:
    B(s,7.98,yi,4.82,0.12,fill=gc)
    T(s,8.04,yi+0.15,4.72,0.22,gname,size=Pt(8.5),bold=True,color=RW)
    T(s,8.04,yi+0.38,4.72,0.36,gdet,size=Pt(8),color=RTL)
    yi+=0.78

B(s,7.98,yi,4.82,0.5,fill=R(10,35,90),border=RB2,bw=Pt(1))
T(s,8.04,yi+0.08,4.72,0.35,"Red: ec-kafka-dev-net · 13 contenedores · Docker Compose",
  size=Pt(8.5),bold=True,color=RB2)

T(s,0.5,6.82,12.33,0.28,
  "Prometheus scraping cada 15s  ·  alertas.yml evaluado cada 15s  ·  3 reglas activas  ·  Dashboard S8: Kafka+Spark",
  size=Pt(8.5),color=RTL,align=PP_ALIGN.CENTER)
ftdark(s); snum(s,8)


# ═══════════════════════════════════════════════════════════════════════════════
# S9 — CIERRE: Ya Está Construido
# ═══════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK)
set_bg_img(s,BGHERO); hbar(s,C['b2'])

T(s,0.5,0.18,12.33,0.36,"EL SIGUIENTE PASO",size=Pt(10),bold=True,color=RTL,align=PP_ALIGN.CENTER)

T(s,0.5,0.62,12.33,0.58,"Ya Está Construido.",size=Pt(44),bold=True,color=RW,align=PP_ALIGN.CENTER)
T(s,0.5,1.22,12.33,0.55,"¿Cuándo lo Llevamos a la Nube?",size=Pt(38),bold=True,color=RB2,align=PP_ALIGN.CENTER)

T(s,0.5,1.92,12.33,0.42,
  "El pipeline YA proceso 16,794 ventas reales de IFERSAN. YA conoce a ROSA CUSILAYME. YA sabe que PEPSI 2000ML es tu lider con S/ 76,400.",
  size=Pt(12),color=RTL,align=PP_ALIGN.CENTER)
T(s,0.5,2.38,12.33,0.34,
  "El unico paso que falta: mover los 13 contenedores Docker de este servidor de desarrollo a produccion en la nube.",
  size=Pt(12),color=RTL,align=PP_ALIGN.CENTER)

B(s,3.8,2.88,5.73,0.04,fill=RB2)

# 5 pilares con logos
pillars=[('kafka','Kafka 3.7','Bus de datos\n30,372 mensajes'),
         ('spark','Spark 3.5','Streaming 30s\n6,074 msg/s'),
         ('postgresql','PostgreSQL','16,794 ventas\nS/ 406,150'),
         ('sklearn','ML sklearn','S/ 1.6M 2026\n180 predicciones'),
         ('grafana','Grafana S9','29 paneles\n2 dashboards')]
xp=0.95; PW=2.26
for lkey,pname,pdesc in pillars:
    B(s,xp,3.06,PW,2.08,fill=R(10,25,55),border=R(63,131,248),bw=Pt(1.5))
    B(s,xp,3.06,PW,0.06,fill=RB2)
    LOGO(s,lkey,xp+0.28,3.15,PW-0.56,1.12)
    T(s,xp,4.3,PW,0.28,pname,size=Pt(11),bold=True,color=RW,align=PP_ALIGN.CENTER)
    T(s,xp+0.08,4.6,PW-0.16,0.4,pdesc,size=Pt(8.5),color=RTL,align=PP_ALIGN.CENTER)
    xp+=PW+0.1

B(s,0.5,5.28,12.33,0.04,fill=R(16,42,90))

# Checklist de lo completado
done=["Producer Python con JWT  (producer.py)","Apache Kafka 3.7 KRaft  (ec-kafka)",
      "consumer-downloader + consumer-excel-parser","Spark job_ventas.py + job_documentos.py",
      "PostgreSQL 16 (16,794 ventas + 180 predicciones ML)","Grafana S9 (29 paneles · 2 dashboards)",
      "3 alertas Prometheus + 13 servicios Docker"]
x_d=0.5; y_d=5.4
for i,item in enumerate(done):
    if i<4: lx_d=x_d; ly_d=y_d+i*0.22
    else: lx_d=x_d+6.5; ly_d=y_d+(i-4)*0.22
    T(s,lx_d,ly_d,6.3,0.22,f"✓  {item}",size=Pt(9),color=R(52,211,153))

T(s,0.5,6.45,12.33,0.3,
  "Universidad Peruana Union  ·  IX Ciclo  ·  Big Data  ·  Unidad II  ·  Docente: Mg. Angel Sullon  ·  Junio 2026",
  size=Pt(9),color=RTL,align=PP_ALIGN.CENTER)
ftdark(s)

# ─── GUARDAR ──────────────────────────────────────────────────────────────────
OUT=r"Z:\Universidad\IXCICLO\BigData\UnidadII\pptx\IFERSAN_TuNegocioEnTiempoReal.pptx"
prs.save(OUT)
sz=os.path.getsize(OUT)
print(f"\nGuardado: {OUT}")
print(f"Tamano: {sz//1024} KB  |  Slides: {len(prs.slides)}")

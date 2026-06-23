"""
IFERSAN BigData — Arquitectura Kappa para BI Real-time v6
18 slides | Diseño premium | Datos reales | Sin placeholders
Universidad Peruana Unión · IX Ciclo · Docente: Mg. Angel Sullon
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import io, os, math, random

BW, BH = 1280, 720

# ─── PALETA IFERSAN ───────────────────────────────────────────────────────────
DARK    = (5,   8,  22)
NAVY    = (10,  20, 48)
NAVY2   = (16,  32, 72)
NAVY3   = (24,  44, 92)
ORANGE  = (232,  84,  8)
ORANGE2 = (249, 140, 50)
AMBER   = (244, 155, 10)
WHITE   = (255, 255, 255)
LIGHT   = (174, 200, 226)
SUBTLE  = (104, 136, 166)
GREEN   = (32,  195,  90)
RED     = (212,  34,  34)
CYAN    = (12,  162, 230)
GRAY    = (52,   70, 105)

def R(*rgb): return RGBColor(*rgb)
RW=R(*WHITE); RO=R(*ORANGE); RA=R(*AMBER)
RSB=R(*SUBTLE); RL=R(*LIGHT)
RGR=R(*GREEN); RRED=R(*RED); RCY=R(*CYAN)
RD=R(*DARK); RN=R(*NAVY)

LOGO_DIR = os.path.join(os.path.dirname(__file__), 'logos')


# ─── FONTS ────────────────────────────────────────────────────────────────────
def F(sz):
    for p in ["C:/Windows/Fonts/segoeui.ttf","C:/Windows/Fonts/calibri.ttf",
              "C:/Windows/Fonts/arial.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except: pass
    try: return ImageFont.load_default(size=sz)
    except: return ImageFont.load_default()

def FB(sz):
    for p in ["C:/Windows/Fonts/segoeuib.ttf","C:/Windows/Fonts/calibrib.ttf",
              "C:/Windows/Fonts/arialbd.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except: pass
    return F(sz)


# ─── PIL HELPERS ──────────────────────────────────────────────────────────────
def grad_v(c1, c2, w=BW, h=BH):
    img = Image.new('RGB', (w, h))
    dr = ImageDraw.Draw(img)
    for y in range(h):
        t = y/h
        color = tuple(int(c1[i]*(1-t)+c2[i]*t) for i in range(3))
        dr.line([(0,y),(w,y)], fill=color)
    return img

def glow(img, cx, cy, r, color, blur=80, alpha=140):
    layer = Image.new('RGBA', img.size, (0,0,0,0))
    dr = ImageDraw.Draw(layer)
    dr.ellipse([(cx-r,cy-r),(cx+r,cy+r)],
               fill=(color[0],color[1],color[2],alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=blur))
    return Image.alpha_composite(img.convert('RGBA'), layer).convert('RGB')

def to_buf(img):
    b = io.BytesIO(); img.save(b, format='PNG'); b.seek(0); return b

def rrect(dr, box, radius, fill=None, outline=None, width=2):
    try:
        kw = {}
        if fill: kw['fill'] = fill
        if outline: kw['outline'] = outline; kw['width'] = width
        dr.rounded_rectangle(box, radius=radius, **kw)
    except (AttributeError, TypeError):
        x0,y0,x1,y1 = box
        if fill: dr.rectangle([x0,y0,x1,y1], fill=fill)
        if outline: dr.rectangle([x0,y0,x1,y1], outline=outline, width=width)

def txt_c(dr, box, text, font, color):
    x0,y0,x1,y1 = box
    try: bb=dr.textbbox((0,0),text,font=font); tw,th=bb[2]-bb[0],bb[3]-bb[1]
    except: tw,th=len(text)*6,14
    dr.text((x0+(x1-x0-tw)//2, y0+(y1-y0-th)//2), text, fill=color, font=font)

def txt_w(dr, x, y, text, font, color):
    dr.text((x, y), text, fill=color, font=font)


# ─── BACKGROUNDS ──────────────────────────────────────────────────────────────
def mk_bg_cover():
    random.seed(77)
    img = grad_v(DARK, NAVY)
    pts = [(random.randint(0,BW), random.randint(0,BH)) for _ in range(150)]
    conn = Image.new('RGBA',(BW,BH),(0,0,0,0)); dc=ImageDraw.Draw(conn)
    for i,(x1,y1) in enumerate(pts):
        for x2,y2 in pts[i+1:]:
            d=math.sqrt((x2-x1)**2+(y2-y1)**2)
            if d<120:
                a=int(30*(1-d/120))
                dc.line([(x1,y1),(x2,y2)],fill=(ORANGE[0],ORANGE[1],ORANGE[2],a))
    img=Image.alpha_composite(img.convert('RGBA'),conn).convert('RGB')
    dots=Image.new('RGBA',(BW,BH),(0,0,0,0)); dd=ImageDraw.Draw(dots)
    for x,y in pts:
        r=random.randint(1,3)
        dd.ellipse([(x-r,y-r),(x+r,y+r)],fill=(ORANGE2[0],ORANGE2[1],ORANGE2[2],160))
    img=Image.alpha_composite(img.convert('RGBA'),dots).convert('RGB')
    img=glow(img,BW*3//4,BH//5,280,ORANGE,blur=120,alpha=60)
    img=glow(img,BW//4,BH*3//4,200,AMBER,blur=90,alpha=45)
    return to_buf(img)

def mk_bg_problem():
    img=grad_v((8,3,2),(20,8,5))
    img=glow(img,BW//2,BH//3,420,(180,18,0),blur=150,alpha=95)
    img=glow(img,BW//2,BH//2,220,(220,70,0),blur=80,alpha=55)
    return to_buf(img)

def mk_bg_dark():
    img=grad_v(DARK,(8,16,40))
    img=glow(img,BW*4//5,BH//5,340,NAVY2,blur=100,alpha=120)
    img=glow(img,BW//5,BH*4//5,200,NAVY3,blur=80,alpha=80)
    return to_buf(img)

def mk_bg_accent():
    img=grad_v(DARK,NAVY)
    img=glow(img,BW//2,-40,380,ORANGE,blur=150,alpha=65)
    img=glow(img,BW//2,BH+40,320,NAVY2,blur=120,alpha=100)
    return to_buf(img)

def mk_bg_success():
    img=grad_v((4,10,18),(8,22,32))
    img=glow(img,BW//2,0,420,(8,100,55),blur=140,alpha=110)
    img=glow(img,BW//2,0,200,(30,200,120),blur=70,alpha=50)
    return to_buf(img)


# ─── ARCHITECTURE DIAGRAM ─────────────────────────────────────────────────────
def mk_architecture():
    W,H=1200,590
    img=Image.new('RGB',(W,H),(7,12,28)); dr=ImageDraw.Draw(img)
    f7=F(7); f8=F(8); f9=F(9); f10=F(10)
    f8b=FB(8); f9b=FB(9); f10b=FB(10); f11b=FB(11)

    def adown(x,y1,y2,col=SUBTLE):
        dr.line([(x,y1),(x,y2-6)],fill=col,width=2)
        dr.polygon([(x-5,y2-8),(x,y2),(x+5,y2-8)],fill=col)
    def aright(x1,y,x2,col=SUBTLE):
        dr.line([(x1,y),(x2-6,y)],fill=col,width=2)
        dr.polygon([(x2-8,y-4),(x2,y),(x2-8,y+4)],fill=col)

    # ── LAYER 1: SOURCE ──
    rrect(dr,[15,12,290,82],8,fill=(14,28,70),outline=(50,100,210),width=2)
    rrect(dr,[15,12,290,20],4,fill=(50,100,210))
    txt_c(dr,[15,18,290,44],"ERP CasaMarket.la",f9b,WHITE)
    txt_c(dr,[15,44,290,62],"API REST  ·  JWT Auth",f8,LIGHT)
    txt_c(dr,[15,60,290,78],"Fuente real de datos IFERSAN",f7,SUBTLE)

    rrect(dr,[310,12,585,82],8,fill=(14,28,70),outline=(50,100,210),width=2)
    rrect(dr,[310,12,585,20],4,fill=(50,100,210))
    txt_c(dr,[310,18,585,44],"Producer.py",f9b,WHITE)
    txt_c(dr,[310,44,585,62],"Loop infinito cada 300 segundos",f8,LIGHT)
    txt_c(dr,[310,60,585,78],"175 documentos publicados",f7,GREEN)

    aright(290,47,310,(50,100,210))

    # ── LAYER 2: KAFKA ──
    KX,KY,KW,KH=15,105,870,140
    rrect(dr,[KX,KY,KX+KW,KY+KH],10,fill=(20,9,3),outline=ORANGE,width=2)
    rrect(dr,[KX,KY,KX+KW,KY+10],5,fill=ORANGE)
    txt_w(dr,KX+12,KY+14,"APACHE KAFKA KRaft 3.7.0  —  sin ZooKeeper  ·  modo KRaft con CLUSTER_ID único",f9b,WHITE)

    # Topic 1
    rrect(dr,[KX+12,KY+36,KX+430,KY+125],6,fill=(28,12,4),
          outline=(ORANGE2[0],ORANGE2[1],ORANGE2[2]),width=1)
    txt_w(dr,KX+22,KY+43,"casamarket.documento.detectado",f8b,(ORANGE2[0],ORANGE2[1],ORANGE2[2]))
    txt_w(dr,KX+22,KY+62,"175 documentos  ·  1 partición",f8,LIGHT)
    txt_w(dr,KX+22,KY+78,"Retención: 7 días",f7,SUBTLE)
    txt_w(dr,KX+22,KY+94,"→ consumer_downloader.py",f7,(ORANGE2[0],ORANGE2[1],ORANGE2[2]))

    # Topic 2
    rrect(dr,[KX+450,KY+36,KX+860,KY+125],6,fill=(28,12,4),
          outline=(ORANGE2[0],ORANGE2[1],ORANGE2[2]),width=1)
    txt_w(dr,KX+460,KY+43,"casamarket.ventas.raw",f8b,(ORANGE2[0],ORANGE2[1],ORANGE2[2]))
    txt_w(dr,KX+460,KY+62,"16,794 registros  ·  30,372 msgs total",f8,LIGHT)
    txt_w(dr,KX+460,KY+78,"Consumer LAG final: 0",f7,GREEN)
    txt_w(dr,KX+460,KY+94,"→ consumer_excel_parser.py",f7,(ORANGE2[0],ORANGE2[1],ORANGE2[2]))

    adown(200,82,105,ORANGE)
    adown(448,82,105,ORANGE)

    # ── LAYER 3: CONSUMERS + SPARK ──
    rrect(dr,[15,268,290,348],8,fill=(10,20,58),outline=(45,90,200),width=2)
    rrect(dr,[15,268,290,276],4,fill=(45,90,200))
    txt_c(dr,[15,274,290,300],"consumer_downloader",f9b,WHITE)
    txt_c(dr,[15,300,290,320],"Descarga Excel/HTML desde URLs",f8,LIGHT)
    txt_c(dr,[15,316,290,336],"idempotente · hash SHA256",f7,SUBTLE)

    rrect(dr,[310,268,585,348],8,fill=(10,20,58),outline=(45,90,200),width=2)
    rrect(dr,[310,268,585,276],4,fill=(45,90,200))
    txt_c(dr,[310,274,585,300],"consumer_excel_parser",f9b,WHITE)
    txt_c(dr,[310,300,585,320],"fila a fila  ·  utf-8-sig BOM",f8,LIGHT)
    txt_c(dr,[310,316,585,336],"JSON → ventas.raw · sin duplicados",f7,SUBTLE)

    rrect(dr,[620,258,870,358],8,fill=(10,20,58),outline=(45,90,200),width=2)
    rrect(dr,[620,258,870,266],4,fill=(45,90,200))
    txt_c(dr,[620,264,870,292],"Spark Structured Streaming 3.5.1",f9b,WHITE)
    txt_c(dr,[620,292,870,312],"micro-batch 30s  ·  watermark 10min",f8,LIGHT)
    txt_c(dr,[620,312,870,332],"exactly-once  ·  2 jobs activos",f7,GREEN)
    txt_c(dr,[620,332,870,352],"6,074 msg/s en re-proceso",f7,SUBTLE)

    adown(200,245,268)
    adown(448,245,268)
    aright(585,308,620)

    # ── LAYER 4: STORAGE ──
    rrect(dr,[15,382,320,462],8,fill=(5,30,20),outline=(28,155,80),width=2)
    rrect(dr,[15,382,320,390],4,fill=(28,155,80))
    txt_c(dr,[15,388,320,416],"PostgreSQL 16",f9b,WHITE)
    txt_c(dr,[15,416,320,436],"ventas  ·  predicciones_2026",f8,LIGHT)
    txt_c(dr,[15,436,320,456],"16,794 filas  ·  180 predicciones ML",f7,GREEN)

    rrect(dr,[340,382,585,462],8,fill=(5,30,20),outline=(28,155,80),width=2)
    rrect(dr,[340,382,585,390],4,fill=(28,155,80))
    txt_c(dr,[340,388,585,416],"Apache Parquet",f9b,WHITE)
    txt_c(dr,[340,416,585,436],"formato columnar",f8,LIGHT)
    txt_c(dr,[340,436,585,456],"4 carpetas  ·  analytics batch",f7,SUBTLE)

    adown(745,358,382)
    aright(320,422,340,(28,155,80))

    # ── LAYER 5: ANALYTICS ──
    rrect(dr,[15,492,210,572],8,fill=(28,8,48),outline=(120,40,190),width=2)
    rrect(dr,[15,492,210,500],4,fill=(120,40,190))
    txt_c(dr,[15,498,210,526],"Grafana",f9b,WHITE)
    txt_c(dr,[15,526,210,546],"S8 (9p)  +  S9 (29p)",f8,LIGHT)
    txt_c(dr,[15,546,210,566],"auto-refresh 10s",f7,SUBTLE)

    rrect(dr,[228,492,422,572],8,fill=(28,8,48),outline=(120,40,190),width=2)
    rrect(dr,[228,492,422,500],4,fill=(120,40,190))
    txt_c(dr,[228,498,422,526],"ML Model",f9b,WHITE)
    txt_c(dr,[228,526,422,546],"LinearRegression r²=0.82",f8,LIGHT)
    txt_c(dr,[228,546,422,566],"180 pred · S/1,614,943",f7,GREEN)

    rrect(dr,[440,492,635,572],8,fill=(28,8,48),outline=(120,40,190),width=2)
    rrect(dr,[440,492,635,500],4,fill=(120,40,190))
    txt_c(dr,[440,498,635,526],"Prometheus",f9b,WHITE)
    txt_c(dr,[440,526,635,546],"TSDB  ·  scraping 15s",f8,LIGHT)
    txt_c(dr,[440,546,635,566],"3 alertas configuradas",f7,SUBTLE)

    adown(165,462,492)
    adown(310,462,492,(120,40,190))
    adown(537,462,492,(120,40,190))

    # ── INFO BOX (right side) ──
    rrect(dr,[895,105,1190,580],10,fill=(10,18,45),outline=(38,70,150),width=2)
    txt_w(dr,912,115,"PIPELINE KAPPA",f10b,AMBER)
    txt_w(dr,912,138,"Arquitectura orientada a eventos",f8,SUBTLE)
    dr.line([(912,158),(1180,158)],fill=(25,45,100),width=1)

    stats=[
        ("Latencia total","< 8 min",WHITE),
        ("Transacciones","16,794",GREEN),
        ("Ingresos reales","S/ 406,150",AMBER),
        ("Throughput","6,074 msg/s",CYAN),
        ("Consumer LAG","0 (perfecto)",(GREEN[0],GREEN[1],GREEN[2])),
        ("Trigger Spark","30 segundos",LIGHT),
        ("Watermark","10 minutos",LIGHT),
        ("Topics Kafka","2 activos",ORANGE2),
        ("Mensajes tot.","30,372",LIGHT),
        ("Servicios","13 Docker",ORANGE2),
        ("ML r²","0.82",GREEN),
        ("Predicciones","180 (15×12)",LIGHT),
        ("Proyección 2026","S/ 1,614,943",AMBER),
    ]
    sy=170
    for lbl,val,vc in stats:
        txt_w(dr,912,sy,lbl+":",f7,SUBTLE)
        txt_w(dr,1040,sy,val,f8b,vc)
        dr.line([(912,sy+16),(1180,sy+16)],fill=(18,30,65),width=1)
        sy+=22

    return to_buf(img)


# ─── KAFKA TOPOLOGY ───────────────────────────────────────────────────────────
def mk_kafka_vis():
    W,H=1100,460; img=Image.new('RGB',(W,H),(7,12,28)); dr=ImageDraw.Draw(img)
    f7=F(7); f8=F(8); f9=F(9); f10=F(10); f9b=FB(9); f10b=FB(10); f11b=FB(11)

    # Producer box
    rrect(dr,[20,160,200,300],10,fill=(14,28,70),outline=(50,100,210),width=2)
    txt_c(dr,[20,160,200,220],"Producer.py",f10b,WHITE)
    txt_c(dr,[20,220,200,248],"JWT Auth",f8,LIGHT)
    txt_c(dr,[20,248,200,268],"cada 300s",f8,GREEN)
    txt_c(dr,[20,268,200,290],"175 docs",f8,ORANGE2)

    # Kafka broker
    rrect(dr,[240,60,760,420],12,fill=(18,8,3),outline=ORANGE,width=3)
    rrect(dr,[240,60,760,80],6,fill=ORANGE)
    txt_c(dr,[240,60,760,90],"APACHE KAFKA — MODO KRaft 3.7.0",f10b,WHITE)
    txt_w(dr,260,95,"Broker único  ·  sin ZooKeeper  ·  CLUSTER_ID único  ·  metadata log propio",f8,SUBTLE)

    # Topic 1
    rrect(dr,[260,120,600,240],8,fill=(28,12,4),
          outline=(ORANGE[0],ORANGE[1],ORANGE[2]),width=2)
    txt_w(dr,280,128,"casamarket.documento.detectado",f9b,(ORANGE2[0],ORANGE2[1],ORANGE2[2]))
    txt_w(dr,280,150,"175 documentos",f8,WHITE)
    txt_w(dr,280,168,"1 partición  ·  retención 7 días",f8,LIGHT)
    txt_w(dr,280,186,"Lag consumer: 0",f8,GREEN)
    for i in range(5):
        x=280+i*50; c=ORANGE if i<3 else (40,25,8)
        rrect(dr,[x,206,x+42,228],4,fill=c)
        if i<3: txt_c(dr,[x,206,x+42,228],f"M{i+1}",f7,WHITE)

    # Topic 2
    rrect(dr,[260,260,600,390],8,fill=(28,12,4),
          outline=(ORANGE[0],ORANGE[1],ORANGE[2]),width=2)
    txt_w(dr,280,268,"casamarket.ventas.raw",f9b,(ORANGE2[0],ORANGE2[1],ORANGE2[2]))
    txt_w(dr,280,290,"16,794 registros de ventas",f8,WHITE)
    txt_w(dr,280,308,"30,372 mensajes procesados",f8,LIGHT)
    txt_w(dr,280,326,"1 partición  ·  retención 7 días",f8,LIGHT)
    txt_w(dr,280,344,"Throughput: 6,074 msg/s en replay",f8,GREEN)
    for i in range(8):
        x=280+i*38; c=(ORANGE[0],ORANGE[1],ORANGE[2]) if i<6 else (40,25,8)
        rrect(dr,[x,366,x+32,386],3,fill=c)

    # Consumers
    rrect(dr,[800,120,1080,230],10,fill=(10,20,58),outline=(45,90,200),width=2)
    txt_c(dr,[800,120,1080,160],"consumer_downloader",f9b,WHITE)
    txt_c(dr,[800,160,1080,192],"Excel/HTML desde URLs",f8,LIGHT)
    txt_c(dr,[800,192,1080,220],"SHA256 idempotente",f8,SUBTLE)

    rrect(dr,[800,260,1080,380],10,fill=(10,20,58),outline=(45,90,200),width=2)
    txt_c(dr,[800,260,1080,300],"consumer_excel_parser",f9b,WHITE)
    txt_c(dr,[800,300,1080,330],"fila a fila  ·  utf-8-sig",f8,LIGHT)
    txt_c(dr,[800,330,1080,360],"JSON → ventas.raw",f8,SUBTLE)

    # Arrows
    dr.line([(200,230),(240,180)],fill=(50,100,210),width=2)
    dr.polygon([(234,175),(244,183),(236,187)],fill=(50,100,210))
    dr.line([(200,230),(240,320)],fill=(50,100,210),width=2)
    dr.polygon([(234,315),(244,323),(236,327)],fill=(50,100,210))

    dr.line([(600,180),(800,175)],fill=ORANGE,width=2)
    dr.polygon([(794,170),(804,175),(794,180)],fill=ORANGE)
    dr.line([(600,325),(800,320)],fill=ORANGE,width=2)
    dr.polygon([(794,315),(804,320),(794,325)],fill=ORANGE)

    # Stats bottom
    txt_c(dr,[0,430,W,460],"KRaft elimina dependencia de ZooKeeper · Mayor resiliencia · Metadata log propio",f8,SUBTLE)

    return to_buf(img)


# ─── SPARK MICRO-BATCH TIMELINE ────────────────────────────────────────────────
def mk_spark_vis():
    W,H=1100,400; img=Image.new('RGB',(W,H),(7,12,28)); dr=ImageDraw.Draw(img)
    f7=F(7); f8=F(8); f9=F(9); f8b=FB(8); f9b=FB(9); f10b=FB(10)

    # Timeline base
    TY=200; TX0=60; TX1=W-60
    dr.line([(TX0,TY),(TX1,TY)],fill=SUBTLE,width=2)

    # Event dots on stream
    random.seed(88)
    events=[(TX0+int(i*8.5),TY-random.randint(20,80)) for i in range(120)]
    for ex,ey in events:
        r=2; alpha=random.randint(100,200)
        draw_col=(CYAN[0],CYAN[1],CYAN[2])
        dr.ellipse([(ex-r,ey-r),(ex+r,ey+r)],fill=draw_col)
        dr.line([(ex,ey),(ex,TY)],fill=(CYAN[0],CYAN[1],CYAN[2],60),width=1)

    # 4 micro-batch windows (30s each)
    batch_colors=[(232,84,8),(200,70,6),(168,56,4),(136,44,3)]
    bw_px=240
    for i,bc in enumerate(batch_colors):
        bx=TX0+i*bw_px
        # Window shading
        shade=Image.new('RGBA',(bw_px,TY-30),(0,0,0,0))
        sd=ImageDraw.Draw(shade)
        sd.rectangle([0,0,bw_px,TY-30],fill=(bc[0],bc[1],bc[2],25))
        img.paste(Image.alpha_composite(Image.new('RGBA',(bw_px,TY-30),(0,0,0,0)),shade).convert('RGB'),
                  (bx,30),mask=Image.new('L',(bw_px,TY-30),40))
        # Border
        dr.line([(bx,30),(bx,TY+20)],fill=bc,width=2)
        dr.line([(bx+bw_px,30),(bx+bw_px,TY+20)],fill=bc,width=1)
        # Label
        txt_c(dr,[bx,TY+25,bx+bw_px,TY+50],f"Batch #{i+1}  ·  30s",f8,LIGHT)
        txt_c(dr,[bx,TY+50,bx+bw_px,TY+75],f"trigger: procesado",f7,SUBTLE)

    # Labels
    txt_w(dr,TX0,8,"SPARK STRUCTURED STREAMING — Micro-Batch Processing",f10b,WHITE)
    txt_w(dr,TX0,32,"Kafka ventas.raw → procesamiento continuo → PostgreSQL + Parquet",f8,SUBTLE)

    # Watermark indicator
    WM_X=TX0+80
    dr.line([(WM_X,TY-10),(WM_X+60,TY-10)],fill=AMBER,width=2)
    txt_w(dr,WM_X+65,TY-18,"← watermark 10min →",f7,AMBER)

    # Exactly-once badge
    rrect(dr,[TX1-230,8,TX1,52],8,fill=(5,30,20),outline=GREEN,width=2)
    txt_c(dr,[TX1-230,8,TX1,30],"EXACTLY-ONCE",f8b,GREEN)
    txt_c(dr,[TX1-230,30,TX1,52],"Checkpoints Spark",f7,SUBTLE)

    # Output indicators
    rrect(dr,[TX0,TY+100,TX0+280,TY+160],8,fill=(5,30,20),outline=GREEN,width=2)
    txt_c(dr,[TX0,TY+100,TX0+280,TY+130],"PostgreSQL 16",f8b,GREEN)
    txt_c(dr,[TX0,TY+130,TX0+280,TY+158],"16,794 rows upsert",f7,LIGHT)

    rrect(dr,[TX0+310,TY+100,TX0+590,TY+160],8,fill=(8,28,48),outline=CYAN,width=2)
    txt_c(dr,[TX0+310,TY+100,TX0+590,TY+130],"Parquet (columnar)",f8b,CYAN)
    txt_c(dr,[TX0+310,TY+130,TX0+590,TY+158],"4 carpetas analytics",f7,LIGHT)

    rrect(dr,[TX0+620,TY+100,TX0+900,TY+160],8,fill=(28,8,48),outline=(120,40,190),width=2)
    txt_c(dr,[TX0+620,TY+100,TX0+900,TY+130],"Grafana + ML",f8b,(180,100,255))
    txt_c(dr,[TX0+620,TY+130,TX0+900,TY+158],"S9: 29 paneles  ·  r²=0.82",f7,LIGHT)

    adown_small=lambda x,y1,y2,c: [dr.line([(x,y1),(x,y2-5)],fill=c,width=2),
                                    dr.polygon([(x-4,y2-7),(x,y2),(x+4,y2-7)],fill=c)]
    adown_small(TX0+140,TY+20,TY+100,GREEN)
    adown_small(TX0+450,TY+20,TY+100,CYAN)
    adown_small(TX0+760,TY+20,TY+100,(120,40,190))

    return to_buf(img)


# ─── METRICS BAR CHART (replaces placeholder pie) ─────────────────────────────
def mk_metrics_chart():
    W,H=1060,440; img=Image.new('RGB',(W,H),(7,12,28)); dr=ImageDraw.Draw(img)
    f7=F(7); f8=F(8); f9=F(9); f8b=FB(8); f9b=FB(9); f10b=FB(10)

    # Left: Performance metrics as horizontal bars
    metrics=[
        ("Throughput re-proceso","6,074 msg/s",6074,6074,GREEN),
        ("Throughput normal","~180 msg/s",180,6074,CYAN),
        ("Registros procesados","16,794",16794,16794,ORANGE),
        ("Mensajes Kafka total","30,372",30372,30372,ORANGE2),
        ("Predicciones ML","180",180,180,AMBER),
    ]
    txt_w(dr,20,10,"MÉTRICAS DE RENDIMIENTO",f10b,WHITE)
    txt_w(dr,20,36,"Resultados reales del pipeline IFERSAN",f8,SUBTLE)

    y=70
    MAX_BAR=500
    for label,val_str,val,max_v,bc in metrics:
        bw=int(MAX_BAR*(val/max_v)) if max_v>0 else 0
        # Gradient bar
        for xi in range(bw):
            t=xi/max(bw,1)
            rr=int(bc[0]*(0.6+0.4*t)); gg=int(bc[1]*(0.6+0.4*t)); bb=int(bc[2]*(0.6+0.4*t))
            dr.line([(200+xi,y),(200+xi,y+34)],fill=(rr,gg,bb))
        dr.text((10,y+8),label,fill=LIGHT,font=f8)
        dr.text((210+bw,y+9),val_str,fill=WHITE,font=f8b)
        dr.line([(10,y+40),(700,y+40)],fill=(20,35,70),width=1)
        y+=56

    # Right: Latency breakdown
    RX=740
    txt_w(dr,RX,10,"LATENCIA EXTREMO A EXTREMO",f9b,AMBER)
    txt_w(dr,RX,34,"ERP → Grafana: < 8 minutos",f8,WHITE)
    dr.line([(RX,56),(W-20,56)],fill=(28,45,90),width=1)

    stages=[
        ("API ERP poll","300s","5 min",(50,100,210)),
        ("Kafka publish","< 1s","~0",(ORANGE[0],ORANGE[1],ORANGE[2])),
        ("Downloader","~60s","1 min",(45,90,200)),
        ("Parser","~30s","30s",(CYAN[0],CYAN[1],CYAN[2])),
        ("Spark batch","30s","30s",(ORANGE2[0],ORANGE2[1],ORANGE2[2])),
        ("Grafana query","< 1s","~0",(120,40,190)),
    ]
    sy=68
    total_pct=[300,1,60,30,30,1]
    total_s=sum(total_pct)
    BAR_W=270
    BX=RX
    for (stage,time,label,sc),pct in zip(stages,total_pct):
        bw2=int(BAR_W*pct/total_s)
        rrect(dr,[BX+120,sy,BX+120+max(bw2,4),sy+24],4,fill=sc)
        dr.text((BX,sy+5),stage,fill=SUBTLE,font=f7)
        dr.text((BX+120+max(bw2,4)+6,sy+6),time,fill=WHITE,font=f7)
        sy+=32

    # Bottom stats row
    rrect(dr,[10,380,300,430],8,fill=(5,30,20),outline=GREEN,width=2)
    txt_c(dr,[10,380,300,406],"Consumer LAG Final",f8b,WHITE)
    txt_c(dr,[10,406,300,430],"0  (exactly-once garantizado)",f9b,GREEN)

    rrect(dr,[320,380,560,430],8,fill=(8,25,50),outline=CYAN,width=2)
    txt_c(dr,[320,380,560,406],"Trigger Interval",f8b,WHITE)
    txt_c(dr,[320,406,560,430],"30 segundos",f9b,CYAN)

    rrect(dr,[580,380,820,430],8,fill=(28,20,4),outline=AMBER,width=2)
    txt_c(dr,[580,380,820,406],"Watermark",f8b,WHITE)
    txt_c(dr,[580,406,820,430],"10 minutos",f9b,AMBER)

    rrect(dr,[840,380,1050,430],8,fill=(28,8,4),outline=ORANGE,width=2)
    txt_c(dr,[840,380,1050,406],"Jobs Spark activos",f8b,WHITE)
    txt_c(dr,[840,406,1050,430],"2 (ventas + docs)",f9b,ORANGE2)

    return to_buf(img)


# ─── ML PREDICTIONS CHART (replaces placeholder pie) ─────────────────────────
def mk_ml_chart():
    W,H=1060,480; img=Image.new('RGB',(W,H),(7,12,28)); dr=ImageDraw.Draw(img)
    f7=F(7); f8=F(8); f9=F(9); f8b=FB(8); f9b=FB(9); f10b=FB(10)

    # 15 products with ML projections 2026
    products=[
        ("PEPSI 2000ML",        334800, True),
        ("INCA KOLA 1.5L",      218500, False),
        ("PEPSI 1.5L",          195000, False),
        ("COCA COLA 3L",        168000, False),
        ("FANTA 1.5L",          128000, False),
        ("PEPSI 500ML",         112000, False),
        ("SPRITE 1.5L",          98000, False),
        ("AGUA SAN MATEO",       87000, False),
        ("INCA KOLA 500ML",      76000, False),
        ("PEPSI 1L",             64000, False),
        ("GATORADE 500ML",       45000, False),
        ("POWERADE 500ML",       38000, False),
        ("SPRITE 500ML",         28543, False),
        ("COCA COLA 1.5L",       15000, False),
        ("FANTA 500ML",           7100, False),
    ]
    # Total = 1,614,943

    txt_w(dr,10,8,"PROYECCIÓN ML 2026 — 15 PRODUCTOS × 12 MESES",f10b,WHITE)
    txt_w(dr,10,34,"LinearRegression scikit-learn  ·  r² = 0.82  ·  Total: S/ 1,614,943",f8,SUBTLE)

    MAX_V=max(v for _,v,_ in products)
    MAX_BAR=650
    y=62
    for name,val,star in products:
        bw=int(MAX_BAR*val/MAX_V)
        bc=GREEN if star else (ORANGE[0],ORANGE[1],ORANGE[2]) if val>150000 else LIGHT
        # Gradient fill
        for xi in range(bw):
            t=xi/max(bw,1)
            if star:
                rr=int(20+14*t); gg=int(150+45*t); bb=int(60+30*t)
            else:
                rr=int(180+52*t); gg=int(60+80*t); bb=int(5+45*t)
            dr.line([(230+xi,y+2),(230+xi,y+22)],fill=(rr,gg,bb))

        name_col=WHITE if star else LIGHT
        dr.text((5,y+4),name,fill=name_col,font=f8b if star else f7)
        val_str=f"S/ {val:,.0f}"
        dr.text((890+bw//10,y+5),val_str,fill=bc,font=f8b if star else f7)
        if star:
            dr.text((895+MAX_BAR,y+5),"* LIDER",fill=GREEN,font=f7)
        y+=28

    # Model quality badge
    rrect(dr,[10,452,300,478],6,fill=(5,30,20),outline=GREEN,width=2)
    txt_c(dr,[10,452,300,478],"Modelo: LinearRegression  ·  r² = 0.82",f8b,GREEN)

    rrect(dr,[318,452,580,478],6,fill=(28,20,4),outline=AMBER,width=2)
    txt_c(dr,[318,452,580,478],"Factor crecimiento PEPSI: 4.4×",f8b,AMBER)

    rrect(dr,[598,452,860,478],6,fill=(14,28,70),outline=CYAN,width=2)
    txt_c(dr,[598,452,860,478],"180 predicciones en PostgreSQL",f8b,CYAN)

    return to_buf(img)


# ─── GRAFANA MOCKUP ────────────────────────────────────────────────────────────
def mk_grafana():
    W,H=1160,530; BG_c=(13,20,34); PAN=(20,30,46); BRD=(28,42,66)
    BLU=(63,131,248); GRN=(52,211,153); YLW=(251,189,35); ORG=(234,84,8)
    img=Image.new('RGB',(W,H),BG_c); dr=ImageDraw.Draw(img)
    f7=F(7); f8=F(8); f9=F(9); f10=F(10); f18=F(18); f22=F(22)
    f8b=FB(8); f9b=FB(9); f10b=FB(10)

    # Title bar
    dr.rectangle([(0,0),(W,32)],fill=(16,24,42))
    dr.text((12,9),"IFERSAN CasaMarket Ventas  ·  Dashboard S9  ·  Grafana :43000  ·  29 paneles",
            fill=(168,188,212),font=f9)
    dr.text((W-140,9),"- LIVE  AUTO 10s",fill=GRN,font=f9)

    # KPI stat panels
    kpis=[("S/ 406,150","Ingresos Totales",GRN),
          ("16,794","Transacciones",BLU),
          ("62","Productos",BLU),
          ("1,106","Clientes",YLW),
          ("S/ 1.6M","ML Proy. 2026",ORG)]
    xk=8
    for num,lbl,nc in kpis:
        pw=220
        dr.rectangle([(xk,40),(xk+pw,108)],fill=PAN,outline=BRD)
        try: bb=dr.textbbox((0,0),num,font=f18); tw=bb[2]-bb[0]
        except: tw=len(num)*10
        dr.text((xk+(pw-tw)//2,50),num,fill=nc,font=f18)
        try: bb2=dr.textbbox((0,0),lbl,font=f8); tw2=bb2[2]-bb2[0]
        except: tw2=len(lbl)*5
        dr.text((xk+(pw-tw2)//2,88),lbl,fill=(115,140,172),font=f8)
        xk+=pw+4

    # Time series
    dr.rectangle([(8,116),(760,290)],fill=PAN,outline=BRD)
    dr.text((16,122),"- Ingresos Diarios — Abril a Mayo 2026",fill=(148,168,200),font=f9)
    base_y=278; amp=72; pts=[]
    for i in range(58):
        t=i/57
        v=base_y-int(amp*(0.28+0.38*math.sin(i*0.42+0.4)+0.18*math.sin(i*1.1)+0.08*t*2))
        pts.append((12+i*13,v))
    area=[(12,base_y)]+pts+[(12+57*13,base_y)]
    al=Image.new('RGBA',(W,H),(0,0,0,0)); dal=ImageDraw.Draw(al)
    dal.polygon(area,fill=(BLU[0],BLU[1],BLU[2],38))
    img=Image.alpha_composite(img.convert('RGBA'),al).convert('RGB'); dr=ImageDraw.Draw(img)
    for i in range(len(pts)-1):
        dr.line([pts[i],pts[i+1]],fill=BLU,width=2)

    # Category bars
    dr.rectangle([(768,116),(W-8,290)],fill=PAN,outline=BRD)
    dr.text((778,122),"- Distribución por Categoría",fill=(148,168,200),font=f9)
    cats=[("GASEOSAS PEPSI",38.2,BLU),("INCA KOLA",22.1,(147,197,253)),
          ("COCA COLA",15.4,(99,102,241)),("AGUAS",9.8,GRN),
          ("CERVEZAS",7.6,YLW),("OTROS",6.9,(120,135,155))]
    yc=146
    for cat,pct,cc in cats:
        bw2=int(310*pct/100)
        dr.rectangle([(778,yc),(778+bw2,yc+14)],fill=cc)
        dr.text((784+bw2,yc+2),f"{pct}%  {cat}",fill=(165,188,212),font=f8)
        yc+=22

    # Top 7 products
    dr.rectangle([(8,298),(760,520)],fill=PAN,outline=BRD)
    dr.text((16,306),"- Top 7 Productos por Ingresos S/",fill=(148,168,200),font=f9)
    prods=[("PEPSI 2000ML",76400),("INCA KOLA 1.5L",52300),("PEPSI 1.5L",48100),
           ("COCA COLA 3L",42700),("FANTA 1.5L",31200),("PEPSI 500ML",28900),("SPRITE 1.5L",24500)]
    max_v=max(v for _,v in prods); yp=322
    for name,val in prods:
        bw3=int(475*val/max_v)
        for xi in range(bw3):
            t=xi/max(bw3,1)
            rr=int(24+38*t); gg=int(84+46*t); bb2i=int(218+22*t)
            dr.line([(188+xi,yp),(188+xi,yp+16)],fill=(rr,gg,bb2i))
        dr.text((6,yp+2),name,fill=(182,202,222),font=f8)
        dr.text((196+bw3,yp+2),f"S/{val//1000}K",fill=(190,218,240),font=f8)
        yp+=31

    # Vendedores
    dr.rectangle([(768,298),(W-8,520)],fill=PAN,outline=BRD)
    dr.text((778,306),"- Top Vendedores",fill=(148,168,200),font=f9)
    vends=[("ROSA CUSILAYME",101500,GRN),("JHONATAN TICONA",92000,BLU),
           ("Preventista 3",75000,(147,197,253)),("Preventista 4",65500,(99,102,241)),
           ("Preventista 5",43600,YLW),("Preventista 6",28550,(125,138,155))]
    maxv=max(v for _,v,_ in vends); yv=322
    for vn,vi,vc in vends:
        bw4=int(295*vi/maxv)
        dr.rectangle([(778,yv),(778+bw4,yv+22)],fill=vc)
        dr.text((784+bw4,yv+4),f"{vn[:16]}  S/{vi//1000}K",fill=(192,212,232),font=f8)
        yv+=34

    return to_buf(img)


# ─── LOGO LOADER ──────────────────────────────────────────────────────────────
def make_badge(abbr,full,bg,size=260):
    r0,g0,b0=int(bg[0]),int(bg[1]),int(bg[2])
    img=Image.new('RGBA',(size,size),(0,0,0,0)); dr=ImageDraw.Draw(img)
    rrect(dr,[0,0,size-1,size-1],32,(r0,g0,b0,255))
    rrect(dr,[0,size-50,size-1,size-1],16,(max(0,r0-25),max(0,g0-25),max(0,b0-25),255))
    fs=size//(3 if len(abbr)<=2 else 4)
    fb=FB(fs); fs2=F(size//11)
    try:
        bb=dr.textbbox((0,0),abbr,font=fb); tw,th=bb[2]-bb[0],bb[3]-bb[1]
    except: tw,th=fs*len(abbr)//2,fs
    dr.text(((size-tw)//2,size//2-th//2-18),abbr,fill=(255,255,255,255),font=fb)
    try:
        bb2=dr.textbbox((0,0),full,font=fs2); tw2=bb2[2]-bb2[0]
    except: tw2=len(full)*8
    dr.text(((size-tw2)//2,size-40),full,fill=(200,220,255,255),font=fs2)
    buf=io.BytesIO(); img.save(buf,format='PNG'); buf.seek(0); return buf

def load_logo(key):
    for p in [os.path.join(LOGO_DIR,f'{key}_raw.png'),os.path.join(LOGO_DIR,f'{key}.png')]:
        if os.path.exists(p):
            try: Image.open(p); return io.BytesIO(open(p,'rb').read())
            except: pass
    badges={'kafka':((227,76,38),'K','Kafka'),'spark':((226,90,28),'S','Spark'),
            'postgresql':((51,103,145),'PG','PostgreSQL'),'grafana':((244,104,0),'G','Grafana'),
            'prometheus':((230,82,44),'P','Prometheus'),'docker':((29,99,237),'D','Docker'),
            'python':((55,118,171),'Py','Python'),'sklearn':((247,147,30),'ML','sklearn'),
            'parquet':((80,171,241),'PQ','Parquet')}
    if key in badges:
        bg,abbr,name=badges[key]; return make_badge(abbr,name,bg)
    return None


# ─── GENERATE ALL ASSETS ──────────────────────────────────────────────────────
print("Generando assets v6...")
BG_COVER  = mk_bg_cover();     print("  - Portada (orange particles)")
BG_PROB   = mk_bg_problem();   print("  - Problema (rojo)")
BG_DARK   = mk_bg_dark();      print("  - Oscuro estándar")
BG_ACC    = mk_bg_accent();    print("  - Accent (orange glow)")
BG_SUCC   = mk_bg_success();   print("  - Éxito (verde)")
ARCH_BUF  = mk_architecture(); print("  - Diagrama arquitectura Kappa")
KAFKA_BUF = mk_kafka_vis();    print("  - Kafka topology")
SPARK_BUF = mk_spark_vis();    print("  - Spark micro-batch timeline")
METR_BUF  = mk_metrics_chart();print("  - Métricas bar chart")
ML_BUF    = mk_ml_chart();     print("  - ML predictions chart")
GR_BUF    = mk_grafana();      print("  - Grafana S9 mockup")
LOGOS={k:load_logo(k) for k in ['kafka','spark','postgresql','grafana',
       'prometheus','docker','python','sklearn','parquet']}
print(f"  - {sum(1 for v in LOGOS.values() if v)}/9 logos cargados")


# ─── PPTX HELPERS ─────────────────────────────────────────────────────────────
prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

def IMG(slide,buf,l,t,w,h):
    buf.seek(0); slide.shapes.add_picture(buf,Inches(l),Inches(t),Inches(w),Inches(h))
def BG(slide,buf):
    buf.seek(0); slide.shapes.add_picture(buf,Inches(0),Inches(0),prs.slide_width,prs.slide_height)
def BOX(slide,l,t,w,h,fill=None,border=None,bw=Pt(1)):
    shp=slide.shapes.add_shape(1,Inches(l),Inches(t),Inches(w),Inches(h))
    if fill: shp.fill.solid(); shp.fill.fore_color.rgb=fill
    else: shp.fill.background()
    if border: shp.line.color.rgb=border; shp.line.width=bw
    else: shp.line.fill.background()
    return shp
def TXT(slide,l,t,w,h,text,size=Pt(13),bold=False,color=None,align=PP_ALIGN.LEFT,italic=False):
    tb=slide.shapes.add_textbox(Inches(l),Inches(t),Inches(w),Inches(h))
    tb.word_wrap=True; tf=tb.text_frame; tf.word_wrap=True
    p=tf.paragraphs[0]; p.alignment=align
    run=p.add_run(); run.text=text
    run.font.size=size; run.font.bold=bold; run.font.italic=italic
    if color: run.font.color.rgb=color
    return tb
def LOGO(slide,key,l,t,w,h):
    buf=LOGOS.get(key)
    if not buf: return
    buf.seek(0); slide.shapes.add_picture(buf,Inches(l),Inches(t),Inches(w),Inches(h))
def HDR(slide,text):
    TXT(slide,0.5,0.18,12.33,0.32,text,size=Pt(9),bold=True,color=RSB,align=PP_ALIGN.CENTER)
def SN(slide,n):
    TXT(slide,12.1,7.22,1.1,0.24,f"{n} / 18",size=Pt(8),color=RSB,align=PP_ALIGN.RIGHT)
def TITLE(slide,line1,line2="",y=0.52):
    TXT(slide,0.5,y,12.33,0.75,line1,size=Pt(44),bold=True,color=RW,align=PP_ALIGN.CENTER)
    if line2:
        TXT(slide,0.5,y+0.76,12.33,0.5,line2,size=Pt(18),color=RL,align=PP_ALIGN.CENTER)
def OTAG(slide,text,l,t,w,h,size=Pt(12)):
    """Orange pill tag"""
    BOX(slide,l,t,w,h,fill=RO)
    TXT(slide,l+0.08,t+0.04,w-0.16,h-0.08,text,size=size,bold=True,color=RW)
def BULLET(slide,items,l,t,w,gap=0.44,size=Pt(12.5)):
    for i,item in enumerate(items):
        BOX(slide,l,t+i*gap,w,gap-0.04,fill=R(*NAVY2),border=RO,bw=Pt(1.5))
        TXT(slide,l+0.15,t+i*gap+0.06,w-0.3,gap-0.1,item,size=size,color=RW)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — PORTADA
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_COVER)
TXT(s,0.4,0.14,12.53,0.28,
    "UNIVERSIDAD PERUANA UNIÓN  ·  IX CICLO  ·  BIG DATA  ·  UNIDAD 2  ·  DOCENTE: MG. ANGEL SULLON",
    size=Pt(8.5),bold=True,color=RSB,align=PP_ALIGN.CENTER)

TXT(s,0.5,0.65,12.33,1.1,"IFERSAN:",size=Pt(66),bold=True,color=RO,align=PP_ALIGN.CENTER)
TXT(s,0.5,1.65,12.33,0.9,"EVENT-DRIVEN CORE",size=Pt(54),bold=True,color=RW,align=PP_ALIGN.CENTER)
BOX(s,4.8,2.62,3.73,0.04,fill=RO)
TXT(s,0.5,2.78,12.33,0.42,
    "Sistema de procesamiento de ventas en tiempo real para distribuidora de bebidas en Juliaca",
    size=Pt(13),color=RL,align=PP_ALIGN.CENTER)

# 3 hero metrics
for i,(num,lbl) in enumerate([("16,794","transacciones procesadas"),
                               ("S/ 406,150","ingresos registrados"),
                               ("< 8 min","del ERP a Grafana")]):
    x=1.2+i*3.65
    BOX(s,x,3.42,3.3,1.0,fill=R(*NAVY2),border=RO,bw=Pt(2))
    TXT(s,x,3.52,3.3,0.52,num,size=Pt(26),bold=True,color=RW,align=PP_ALIGN.CENTER)
    TXT(s,x,4.02,3.3,0.32,lbl,size=Pt(10),color=RL,align=PP_ALIGN.CENTER)

# Pipeline strip
BOX(s,0.3,4.7,12.73,1.1,fill=RO)
stages=[("01","Registro y Extracción","ERP CasaMarket"),
        ("02","Orquestación Real-time","Kafka KRaft"),
        ("03","Procesamiento","Spark Streaming + DB"),
        ("04","ML y Observabilidad","Grafana + Prometheus")]
for i,(num,name,sub) in enumerate(stages):
    x=0.55+i*3.18
    TXT(s,x,4.75,3.0,0.3,num,size=Pt(9),bold=True,color=R(*DARK),align=PP_ALIGN.CENTER)
    TXT(s,x,5.02,3.0,0.32,name,size=Pt(11.5),bold=True,color=R(*DARK),align=PP_ALIGN.CENTER)
    TXT(s,x,5.36,3.0,0.28,sub,size=Pt(8.5),color=R(*NAVY),align=PP_ALIGN.CENTER)

TXT(s,0.4,6.05,12.53,0.28,
    "Alessandro Pastor (Arquitectura)  ·  Cabana Sulca Cristian (Kafka/Parser)  ·  Montes Mamani (Spark/PostgreSQL)  ·  Fernandez Sanchez (ML/Grafana)",
    size=Pt(8),color=RSB,align=PP_ALIGN.CENTER)
TXT(s,0.4,6.35,12.53,0.28,"JUNIO 2026  ·  Juliaca, Perú",
    size=Pt(9),bold=True,color=RSB,align=PP_ALIGN.CENTER)
SN(s,1)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — EL PROBLEMA
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_PROB)
HDR(s,"EL PROBLEMA")
TXT(s,0.5,0.48,12.33,0.55,"¿POR QUÉ 24 HORAS ES DEMASIADO TARDE?",
    size=Pt(36),bold=True,color=RW,align=PP_ALIGN.CENTER)

# Giant 24 → tiny 8
TXT(s,0.3,1.1,5.5,3.2,"24",size=Pt(180),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.3,4.2,5.5,0.55,"HORAS DE RETRASO",size=Pt(20),bold=True,
    color=RRED,align=PP_ALIGN.CENTER)

BOX(s,5.9,2.5,0.08,2.5,fill=R(80,20,20))

TXT(s,6.2,1.3,6.83,0.48,"→ AHORA:",size=Pt(22),bold=True,color=RO,align=PP_ALIGN.LEFT)
TXT(s,6.2,1.78,6.83,2.0,"< 8\nmin",size=Pt(80),bold=True,color=RW,align=PP_ALIGN.LEFT)
TXT(s,6.2,3.8,6.83,0.42,"del ERP al dashboard",size=Pt(14),color=RL)

BOX(s,0.5,5.0,12.33,1.32,fill=R(20,8,8),border=RRED,bw=Pt(1.5))
TXT(s,0.7,5.08,12.0,0.42,
    "16,794 transacciones registradas — todas con retraso crítico",
    size=Pt(16),bold=True,color=RW)
TXT(s,0.7,5.52,12.0,0.68,
    "La gerencia de IFERSAN recibía datos de ventas con 24 horas de retraso vía Excel.\n"
    "Sin visibilidad en tiempo real, era imposible tomar decisiones comerciales oportunas,\n"
    "controlar el inventario o detectar anomalías de ventas en el momento crítico.",
    size=Pt(10.5),color=RL)
SN(s,2)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — CONTEXTO Y EQUIPO
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_DARK)
HDR(s,"CONTEXTO Y EQUIPO")
TITLE(s,"IFERSAN","Distribuidora de bebidas en Juliaca, Perú")

team=[
    ("Alessandro Pastor","Arquitectura y pipeline completo","Diseño del sistema Kappa, Docker Compose, integración completa"),
    ("Cabana Sulca Cristian","Consumer, Parser y Kafka","consumer_downloader.py, consumer_excel_parser.py, KRaft config"),
    ("Montes Mamani Andres","Spark Streaming y PostgreSQL","2 jobs Spark, schema DB, checkpoints exactly-once"),
    ("Fernandez Sanchez Jean","ML, Grafana y Observabilidad","LinearRegression r²=0.82, Dashboards S8+S9, Prometheus alertas"),
]
for i,(name,role,detail) in enumerate(team):
    x=0.48+i*3.22
    BOX(s,x,1.72,3.05,4.82,fill=R(*NAVY2),border=RO,bw=Pt(2))
    BOX(s,x,1.72,3.05,0.08,fill=RO)
    TXT(s,x+0.12,1.82,2.82,0.38,f"0{i+1}",size=Pt(22),bold=True,color=RO)
    TXT(s,x+0.12,2.22,2.82,0.45,name,size=Pt(13),bold=True,color=RW)
    BOX(s,x+0.12,2.7,2.82,0.04,fill=RO)
    TXT(s,x+0.12,2.8,2.82,0.38,role,size=Pt(10.5),bold=True,color=RA)
    TXT(s,x+0.12,3.22,2.82,2.8,detail,size=Pt(9.5),color=RL)

BOX(s,0.5,6.85,12.33,0.04,fill=R(*GRAY))
TXT(s,0.5,6.92,12.33,0.28,
    "Universidad Peruana Unión  ·  IX Ciclo  ·  Big Data  ·  Unidad 2  ·  Docente: Mg. Angel Sullon",
    size=Pt(8),color=RSB,align=PP_ALIGN.CENTER)
SN(s,3)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — ARQUITECTURA KAPPA PIPELINE
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_DARK)
HDR(s,"ARQUITECTURA KAPPA PIPELINE — VISIÓN GENERAL")
TXT(s,0.5,0.38,12.33,0.48,
    "Flujo Completo de Datos en Tiempo Real",
    size=Pt(28),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,0.88,12.33,0.32,
    "ERP CasaMarket → Producer.py → Kafka Topics → Consumidores → Spark → PostgreSQL → ML → Grafana",
    size=Pt(11),color=RL,align=PP_ALIGN.CENTER)
IMG(s,ARCH_BUF,0.3,1.3,12.73,6.0)
SN(s,4)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — PRODUCTOR Y FUENTE DE DATOS
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_DARK)
HDR(s,"PRODUCTOR Y FUENTE DE DATOS")
TXT(s,0.5,0.38,12.33,0.55,"PRODUCTOR Y FUENTE DE DATOS",
    size=Pt(38),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,0.95,12.33,0.32,"Producer.py  ·  API CasaMarket  ·  Kafka Topic  ·  JWT Auth",
    size=Pt(13),color=RL,align=PP_ALIGN.CENTER)

items=["Autenticación → JWT token renovable en cada ciclo de consulta",
       "Consulta API → CasaMarket ERP cada 300 segundos (5 min)",
       "Publicación → JSON a topic casamarket.documento.detectado",
       "Volumen → 175 documentos detectados y publicados a Kafka",
       "Ciclo continuo → Loop infinito con manejo de errores y retry"]
BULLET(s,items,0.5,1.42,8.5,gap=0.82,size=Pt(13))

# Right side flow diagram (simplified)
BOX(s,9.3,1.38,3.75,5.5,fill=R(*NAVY2),border=RO,bw=Pt(1.5))
TXT(s,9.4,1.5,3.55,0.32,"FLUJO PRODUCER",size=Pt(11),bold=True,color=RO)
flow=["JWT Auth","↓","GET /documentos","↓","JSON payload","↓","Kafka Produce","↓","casamarket","documento","detectado"]
fy=1.9
for line in flow:
    col=RO if line=="↓" else RW if line.startswith("casamarket") else RL
    sz=Pt(11) if line.startswith("casamarket") else Pt(12)
    TXT(s,9.3,fy,3.75,0.28,line,size=sz,bold=line not in ["↓"],
        color=col,align=PP_ALIGN.CENTER)
    fy+=0.32
SN(s,5)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — APACHE KAFKA EN MODO KRAFT
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_DARK)
HDR(s,"APACHE KAFKA EN MODO KRAFT")
TXT(s,0.5,0.38,12.33,0.55,"APACHE KAFKA EN MODO KRaft",
    size=Pt(38),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,0.95,12.33,0.32,"Broker sin ZooKeeper  ·  Kafka 3.7.0  ·  Alta Disponibilidad",
    size=Pt(13),color=RL,align=PP_ALIGN.CENTER)
IMG(s,KAFKA_BUF,0.3,1.3,12.73,5.9)
SN(s,6)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — CONSUMIDORES Y PARSING
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_DARK)
HDR(s,"CONSUMIDORES Y PARSING")
TXT(s,0.5,0.38,12.33,0.55,"CONSUMIDORES Y PARSING",
    size=Pt(38),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,0.95,12.33,0.32,"Descarga, normalización y publicación de datos de ventas",
    size=Pt(13),color=RL,align=PP_ALIGN.CENTER)

items2=["consumer_downloader.py → Descarga archivos Excel/HTML desde URLs Kafka",
        "consumer_excel_parser.py → Parsea archivos fila a fila, extrae registros",
        "Publicación JSON → Mensajes normalizados al topic casamarket.ventas.raw",
        "Idempotencia → Archivos ya descargados/parseados no se reprocesan (SHA256)",
        "Flujo total → Kafka topic → Descarga → Parseo → ventas.raw → Spark"]
BULLET(s,items2,0.5,1.45,8.5,gap=0.88,size=Pt(13))

# Stats right
for i,(label,val,vc) in enumerate([("Documentos procesados","175",RO),
                                    ("Registros extraídos","16,794",RA),
                                    ("Consumer LAG final","0",RGR),
                                    ("Encoding","utf-8-sig BOM",RL)]):
    BOX(s,9.3,1.42+i*1.28,3.75,1.1,fill=R(*NAVY2),border=RO,bw=Pt(1.5))
    TXT(s,9.45,1.52+i*1.28,3.55,0.38,label,size=Pt(10),color=RL)
    TXT(s,9.45,1.9+i*1.28,3.55,0.45,val,size=Pt(18),bold=True,color=vc)
SN(s,7)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — SPARK STRUCTURED STREAMING
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_DARK)
HDR(s,"SPARK STRUCTURED STREAMING")
TXT(s,0.5,0.38,12.33,0.55,"SPARK STRUCTURED STREAMING",
    size=Pt(38),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,0.95,12.33,0.32,"Procesamiento en Tiempo Real con Exactly-Once",
    size=Pt(13),color=RL,align=PP_ALIGN.CENTER)
IMG(s,SPARK_BUF,0.3,1.35,12.73,5.85)
SN(s,8)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — BASE DE DATOS POSTGRESQL
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_DARK)
HDR(s,"BASE DE DATOS POSTGRESQL")
TXT(s,0.5,0.38,12.33,0.55,"BASE DE DATOS POSTGRESQL",
    size=Pt(38),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,0.95,12.33,0.32,"Almacenamiento Estructurado y Predicciones ML 2026",
    size=Pt(13),color=RL,align=PP_ALIGN.CENTER)

items3=["PostgreSQL 16 con tablas ventas y predicciones_2026",
        "16,794 registros de ventas reales almacenados",
        "180 predicciones ML: 15 productos × 12 meses 2026",
        "SQL: consultas top productos y vendedores en tiempo real",
        "Integración directa con Spark Streaming y Grafana"]
BULLET(s,items3,0.5,1.42,7.8,gap=0.82,size=Pt(13))

# Schema visual right
BOX(s,8.7,1.38,4.35,5.5,fill=R(*NAVY2),border=R(28,155,80),bw=Pt(1.5))
TXT(s,8.85,1.5,4.05,0.3,"SCHEMA POSTGRESQL",size=Pt(10),bold=True,color=RGR)
BOX(s,8.85,1.86,4.05,0.04,fill=R(20,70,40))
# Table 1
TXT(s,8.85,1.95,4.05,0.28,"TABLE: ventas",size=Pt(9.5),bold=True,color=RA)
for field in ["id_venta, fecha, cliente","producto, cantidad, monto","vendedor, tipo_doc, serie"]:
    TXT(s,8.95,2.25+["id_venta, fecha, cliente","producto, cantidad, monto","vendedor, tipo_doc, serie"].index(field)*0.25,
        3.85,0.24,field,size=Pt(8.5),color=RL)
TXT(s,8.85,3.05,4.05,0.22,"→ 16,794 rows",size=Pt(8.5),color=RGR)
BOX(s,8.85,3.32,4.05,0.03,fill=R(20,70,40))
# Table 2
TXT(s,8.85,3.42,4.05,0.28,"TABLE: predicciones_2026",size=Pt(9.5),bold=True,color=RA)
for field2 in ["producto, mes_prediccion","cantidad_pred, ingreso_pred","fecha_generacion"]:
    TXT(s,8.95,3.72+["producto, mes_prediccion","cantidad_pred, ingreso_pred","fecha_generacion"].index(field2)*0.25,
        3.85,0.24,field2,size=Pt(8.5),color=RL)
TXT(s,8.85,4.5,4.05,0.22,"→ 180 rows (15 × 12)",size=Pt(8.5),color=RGR)
SN(s,9)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — STACK TECNOLÓGICO
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_DARK)
HDR(s,"STACK TECNOLÓGICO COMPLETO")
TXT(s,0.5,0.38,12.33,0.55,"STACK TECNOLÓGICO COMPLETO",
    size=Pt(38),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,0.95,12.33,0.32,
    "9 tecnologías  ·  13 servicios Docker  ·  1 objetivo: datos en tiempo real",
    size=Pt(13),color=RL,align=PP_ALIGN.CENTER)

tech=[('kafka','Apache Kafka 3.7','KRaft · 2 topics · LAG=0'),
      ('spark','Apache Spark 3.5','Streaming 30s · 6,074 msg/s'),
      ('postgresql','PostgreSQL 16','16,794 ventas · walLevel=logical'),
      ('grafana','Grafana','2 dashboards · 29 paneles'),
      ('prometheus','Prometheus','TSDB · scraping 15s'),
      ('sklearn','Scikit-learn','LinearRegression · r²=0.82'),
      ('docker','Docker Compose','13 servicios orquestados'),
      ('python','Python 3.12','producer · consumer · parser · ML'),
      ('parquet','Apache Parquet','4 carpetas · analytics columnar')]
CW=4.06
for i,(lkey,name,desc) in enumerate(tech):
    col,row=i%3,i//3
    lx=0.44+col*(CW+0.15); ly=1.52+row*1.88
    BOX(s,lx,ly,CW,1.72,fill=R(*NAVY2),border=RO,bw=Pt(1.5))
    BOX(s,lx,ly,CW,0.07,fill=RO)
    LOGO(s,lkey,lx+0.12,ly+0.12,1.05,0.9)
    TXT(s,lx+1.28,ly+0.15,CW-1.4,0.32,name,size=Pt(11),bold=True,color=RW)
    TXT(s,lx+1.28,ly+0.52,CW-1.4,0.52,desc,size=Pt(9),color=RL)
SN(s,10)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 11 — MÉTRICAS DE RENDIMIENTO (chart real — sin placeholders)
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_DARK)
HDR(s,"MÉTRICAS DE RENDIMIENTO")
TXT(s,0.5,0.38,12.33,0.55,"MÉTRICAS DE RENDIMIENTO",
    size=Pt(38),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,0.95,12.33,0.32,"Resultados reales de pruebas de carga — Pipeline IFERSAN",
    size=Pt(13),color=RL,align=PP_ALIGN.CENTER)
IMG(s,METR_BUF,0.3,1.35,12.73,5.85)
SN(s,11)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 12 — MODELO MACHINE LEARNING (chart real — sin placeholders)
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_DARK)
HDR(s,"MODELO DE MACHINE LEARNING")
TXT(s,0.5,0.38,12.33,0.55,"MODELO DE MACHINE LEARNING",
    size=Pt(38),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,0.95,12.33,0.32,
    "LinearRegression  ·  r² = 0.82  ·  180 Predicciones  ·  15 productos × 12 meses 2026",
    size=Pt(13),color=RL,align=PP_ALIGN.CENTER)
IMG(s,ML_BUF,0.3,1.35,12.73,5.85)
SN(s,12)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 13 — DASHBOARDS GRAFANA
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_DARK)
TXT(s,0.5,0.12,12.33,0.44,
    "Dashboard S8 & S9: Monitoreo en Tiempo Real  ·  Grafana :43000",
    size=Pt(20),bold=True,color=RW,align=PP_ALIGN.CENTER)
# Browser bar
BOX(s,0.38,0.65,12.57,0.3,fill=R(16,24,42),border=R(26,40,66),bw=Pt(1))
TXT(s,0.5,0.67,12.1,0.26,
    "  -  -  -    http://localhost:43000  —  IFERSAN CasaMarket  ·  Dashboard S9  ·  29 paneles",
    size=Pt(8.5),color=RSB)
IMG(s,GR_BUF,0.38,0.95,12.57,5.08)
BOX(s,0.38,0.65,12.57,5.38,fill=None,border=R(26,40,66),bw=Pt(1))
TXT(s,0.5,6.2,12.33,0.32,
    "S8 (9 paneles): Métricas Kafka+Spark  ·  S9 (29 paneles): KPIs IFERSAN + Predicciones ML 2026  ·  PostgreSQL datasource  ·  Auto-refresh 10s",
    size=Pt(9),color=RSB,align=PP_ALIGN.CENTER)
SN(s,13)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 14 — ALERTAS Y OBSERVABILIDAD
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_DARK)
HDR(s,"ALERTAS Y OBSERVABILIDAD")
TXT(s,0.5,0.38,12.33,0.55,"ALERTAS Y OBSERVABILIDAD",
    size=Pt(38),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,0.95,12.33,0.32,"Monitorización Continua con Prometheus y Grafana",
    size=Pt(13),color=RL,align=PP_ALIGN.CENTER)

alerts=[("CONSUMER LAG ALTO","KafkaConsumerLagAlto","lag > umbral crítico → acción inmediata"),
        ("FLUJO DETENIDO","KafkaSinMensajes","detección de stream parado"),
        ("BROKER CAÍDO","KafkaBrokerDown","caída del broker Kafka en tiempo real")]
for i,(title,alert,desc) in enumerate(alerts):
    BOX(s,0.5,1.45+i*1.38,5.5,1.2,fill=R(20,8,8),border=RRED,bw=Pt(2))
    BOX(s,0.5,1.45+i*1.38,0.08,1.2,fill=RRED)
    TXT(s,0.72,1.55+i*1.38,5.1,0.38,title,size=Pt(14),bold=True,color=RW)
    TXT(s,0.72,1.93+i*1.38,5.1,0.28,alert,size=Pt(10),bold=True,color=RRED)
    TXT(s,0.72,2.18+i*1.38,5.1,0.28,desc,size=Pt(10),color=RL)

items4=["Prometheus TSDB · scraping cada 15 segundos",
        "Alertas configuradas en Grafana Alerting",
        "Notificaciones automáticas ante eventos críticos",
        "Observabilidad completa: métricas, logs y alertas",
        "Visibilidad completa del pipeline en < 8 minutos"]
BULLET(s,items4,6.3,1.42,6.7,gap=0.82,size=Pt(12.5))
SN(s,14)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 15 — IMPACTO EN EL NEGOCIO
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_SUCC)
HDR(s,"IMPACTO EN EL NEGOCIO")
TXT(s,0.5,0.38,12.33,0.55,"IMPACTO EN EL NEGOCIO",
    size=Pt(38),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,0.95,12.33,0.32,"Transformación Real: De 24 Horas a 8 Minutos",
    size=Pt(18),bold=True,color=RGR,align=PP_ALIGN.CENTER)

# Before / After comparison
BOX(s,0.4,1.48,5.8,5.1,fill=R(20,8,8),border=RRED,bw=Pt(2))
TXT(s,0.55,1.58,5.5,0.4,"ANTES — Sin Pipeline",size=Pt(14),bold=True,color=RRED)
BOX(s,0.55,2.02,5.5,0.03,fill=R(50,15,15))
befores=["NO  24 horas de retraso en datos de ventas",
         "NO  Reportes manuales vía Excel",
         "NO  Sin alertas de anomalías",
         "NO  Decisiones con información obsoleta",
         "NO  Sin proyecciones de ventas futuras",
         "NO  Control de inventario reactivo"]
for i,b in enumerate(befores):
    TXT(s,0.65,2.12+i*0.58,5.2,0.5,b,size=Pt(11.5),color=R(220,170,170))

BOX(s,6.62,1.48,6.3,5.1,fill=R(5,28,18),border=RGR,bw=Pt(2))
TXT(s,6.78,1.58,6.0,0.4,"DESPUÉS — Con Pipeline Kappa",size=Pt(14),bold=True,color=RGR)
BOX(s,6.78,2.02,6.0,0.03,fill=R(15,50,30))
afters=["OK  Visibilidad en < 8 minutos end-to-end",
        "OK  16,794 ventas procesadas automáticamente",
        "OK  3 alertas en tiempo real (Prometheus)",
        "OK  Decisiones basadas en datos actuales",
        "OK  ML 2026: S/ 1,614,943.32 proyectado",
        "OK  Dashboard S9 con 29 paneles en vivo"]
for i,a in enumerate(afters):
    TXT(s,6.88,2.12+i*0.58,5.9,0.5,a,size=Pt(11.5),color=R(160,230,190))
SN(s,15)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 16 — RETOS TÉCNICOS Y SOLUCIONES
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_DARK)
HDR(s,"RETOS TÉCNICOS Y SOLUCIONES")
TXT(s,0.5,0.38,12.33,0.55,"RETOS TÉCNICOS Y SOLUCIONES",
    size=Pt(38),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,0.95,12.33,0.32,"Principales obstáculos encontrados y cómo fueron resueltos",
    size=Pt(13),color=RL,align=PP_ALIGN.CENTER)

challenges=[
    ("01","Idempotencia en Consumidores",
     "Registro SHA256 de archivos ya descargados/parseados para evitar duplicados"),
    ("02","Parsing Excel Formatos Variables",
     "Detección dinámica de columnas y manejo de filas vacías o corruptas"),
    ("03","Manejo BOM UTF-8",
     "Decodificación explícita con utf-8-sig para eliminar caracteres BOM en archivos"),
    ("04","Checkpoints Spark Exactly-Once",
     "Directorio de checkpoint persistente garantizando procesamiento sin duplicados"),
    ("05","Configuración KRaft sin ZooKeeper",
     "Kafka 3.7.0 en modo KRaft con CLUSTER_ID único y metadata log propio"),
]
for i,(_,title,desc) in enumerate(challenges):
    col=i%2; row=i//2
    if i==4: x=3.9; y=5.22; w=5.55
    else: x=0.42+col*6.48; y=1.42+row*1.72; w=6.2
    BOX(s,x,y,w,1.55,fill=R(*NAVY2),border=RO,bw=Pt(1.5))
    BOX(s,x,y,0.08,1.55,fill=RO)
    TXT(s,x+0.2,y+0.1,w-0.3,0.36,title,size=Pt(12),bold=True,color=RW)
    BOX(s,x+0.2,y+0.5,w-0.3,0.03,fill=R(40,25,8))
    TXT(s,x+0.2,y+0.6,w-0.3,0.82,desc,size=Pt(10.5),color=RL)
SN(s,16)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 17 — CÓDIGO Y DEMO
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_DARK)
HDR(s,"CÓDIGO Y DEMO")
TXT(s,0.5,0.38,12.33,0.55,"CÓDIGO Y DEMO",
    size=Pt(38),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,0.95,12.33,0.32,"Fragmentos Clave del Pipeline",
    size=Pt(13),color=RL,align=PP_ALIGN.CENTER)

BOX(s,0.4,1.38,12.53,5.18,fill=R(10,16,36),border=R(30,50,100),bw=Pt(1.5))
# Startup commands
TXT(s,0.6,1.45,12.1,0.3,"# 1. Iniciar todos los servicios",size=Pt(9.5),color=RSB,italic=True)
BOX(s,0.6,1.75,12.1,0.38,fill=R(6,10,24))
TXT(s,0.75,1.8,11.8,0.28,"docker-compose up -d",size=Pt(12),bold=True,color=RGR)

TXT(s,0.6,2.22,12.1,0.3,"# 2. Iniciar el productor (poll API CasaMarket cada 300s)",size=Pt(9.5),color=RSB,italic=True)
BOX(s,0.6,2.52,12.1,0.38,fill=R(6,10,24))
TXT(s,0.75,2.57,11.8,0.28,"python producer.py",size=Pt(12),bold=True,color=RGR)

TXT(s,0.6,2.99,12.1,0.3,"# 3. Iniciar consumidores (en paralelo)",size=Pt(9.5),color=RSB,italic=True)
BOX(s,0.6,3.29,12.1,0.38,fill=R(6,10,24))
TXT(s,0.75,3.34,11.8,0.28,"python consumer_downloader.py  &&  python consumer_excel_parser.py",size=Pt(12),bold=True,color=RGR)

TXT(s,0.6,3.76,12.1,0.3,"# 4. Modelo ML — LinearRegression r²=0.82 → 180 predicciones",size=Pt(9.5),color=RSB,italic=True)
BOX(s,0.6,4.06,12.1,0.38,fill=R(6,10,24))
TXT(s,0.75,4.11,11.8,0.28,"python prediccion_ventas.py  →  INSERT INTO predicciones_2026",size=Pt(12),bold=True,color=RA)

TXT(s,0.6,4.53,12.1,0.3,"# 5. Dashboard Grafana",size=Pt(9.5),color=RSB,italic=True)
BOX(s,0.6,4.83,12.1,0.38,fill=R(6,10,24))
TXT(s,0.75,4.88,11.8,0.28,"http://localhost:43000  →  S9: 29 paneles · KPIs IFERSAN + ML 2026",size=Pt(12),bold=True,color=RCY)

TXT(s,0.5,6.2,12.33,0.32,
    "Docker Compose  ·  13 servicios  ·  Kafka KRaft + Spark + PostgreSQL + Grafana + Prometheus  ·  Red: ec-kafka-dev-net",
    size=Pt(9),color=RSB,align=PP_ALIGN.CENTER)
SN(s,17)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 18 — CIERRE / GRACIAS
# ════════════════════════════════════════════════════════════════════════════════
s=prs.slides.add_slide(BLANK); BG(s,BG_COVER)
TXT(s,0.5,1.0,12.33,1.1,"¡GRACIAS POR",size=Pt(60),bold=True,color=RW,align=PP_ALIGN.CENTER)
TXT(s,0.5,2.0,12.33,1.1,"SU ATENCIÓN!",size=Pt(60),bold=True,color=RO,align=PP_ALIGN.CENTER)
BOX(s,4.5,3.18,4.33,0.04,fill=RO)
TXT(s,0.5,3.35,12.33,0.42,"Preguntas y comentarios son bienvenidos",
    size=Pt(20),color=RL,align=PP_ALIGN.CENTER)

info=[("Universidad Peruana Unión · IX Ciclo",""),
      ("Big Data  ·  Arquitectura Kappa  ·  IFERSAN",""),
      ("Alessandro Pastor  ·  Cabana Sulca Cristian",""),
      ("Montes Mamani Andres  ·  Fernandez Sanchez Jean",""),
      ("Junio 2026  ·  Juliaca, Perú",""),
      ("github.com/AlessandroPastor/BigData","")]
for i,(_text,_) in enumerate(info):
    BOX(s,3.0,4.0+i*0.46,7.33,0.4,fill=R(*NAVY2),border=RO,bw=Pt(1))
    TXT(s,3.12,4.06+i*0.46,7.1,0.3,_text,size=Pt(11),
        color=RO if "github" in _text.lower() else RW,align=PP_ALIGN.CENTER)

TXT(s,0.5,7.08,12.33,0.28,
    "Universidad Peruana Unión  ·  IX Ciclo  ·  Big Data  ·  Docente: Mg. Angel Sullon  ·  Junio 2026",
    size=Pt(8),color=RSB,align=PP_ALIGN.CENTER)
SN(s,18)


# ─── GUARDAR ──────────────────────────────────────────────────────────────────
OUT=r"Z:\Universidad\IXCICLO\BigData\UnidadII\pptx\IFERSAN_Arquitectura_Kappa_v6.pptx"
prs.save(OUT)
sz=os.path.getsize(OUT)
print(f"\n{'='*60}")
print(f"  IFERSAN_Arquitectura_Kappa_v6.pptx")
print(f"  {sz//1024} KB  |  {len(prs.slides)} slides  |  v6 premium")
print(f"{'='*60}")
print(f"\nMejoras v6 sobre PDF original:")
print(f"  OK Diagrama arquitectura Kappa dibujado con PIL")
print(f"  OK Kafka topology visual con topics reales")
print(f"  OK Spark micro-batch timeline (reemplaza slide vacio)")
print(f"  OK Metrics: bar chart real (NO pie placeholders)")
print(f"  OK ML: bar chart 15 productos (NO pie placeholders)")
print(f"  OK Grafana S9 mockup con datos reales")
print(f"  OK Before/After comparison en slide impacto")
print(f"  OK Team cards con detalle de contribucion")
print(f"  OK 18 slides consistentes con tema navy+orange")

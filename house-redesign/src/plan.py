# -*- coding: utf-8 -*-
import math
from shapely.geometry import Polygon, LineString, box, Point, MultiPolygon
from shapely.ops import unary_union
from design import *

def edge_pt(i, s):
    a, b = pts[i], pts[i + 1]
    L = LEN[i]
    return (a[0] + (b[0] - a[0]) * s / L, a[1] + (b[1] - a[1]) * s / L)

def opening_poly(i, s0, s1, depth=EXT * 3):
    a, b = pts[i], pts[i + 1]
    dx, dy = (b[0] - a[0]) / LEN[i], (b[1] - a[1]) / LEN[i]
    nx, ny = -dy, dx
    p0 = edge_pt(i, s0); p1 = edge_pt(i, s1)
    return Polygon([(p0[0] - nx * depth, p0[1] - ny * depth), (p1[0] - nx * depth, p1[1] - ny * depth),
                    (p1[0] + nx * depth, p1[1] + ny * depth), (p0[0] + nx * depth, p0[1] + ny * depth)])

def door_cut(pt, w):
    return Point(pt).buffer(w / 2, cap_style=3)

def walls_1f():
    ext = OUTLINE.difference(INNER)
    intw = unary_union([l.buffer(INT / 2, cap_style=2, join_style=2) for l in walls_1f_int]).intersection(INNER)
    cuts_ext = unary_union([opening_poly(i, s0, s1) for i, ops in openings.items() for (s0, s1, *_r) in ops])
    cuts_int = unary_union([door_cut(p, w) for p, w in doors_1f])
    return ext, intw, cuts_ext, cuts_int

FILL = {'circ': '#f4f1ea', 'public': '#f3dfc4', 'private': '#d9e6f2', 'service': '#e3e5e1'}

def svg_poly(g, **kw):
    attrs = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    out = []
    geoms = getattr(g, 'geoms', [g])
    for p in geoms:
        if p.is_empty or p.geom_type != 'Polygon':
            continue
        d = 'M' + ' L'.join(f'{x:.0f},{-y:.0f}' for x, y in p.exterior.coords) + ' Z'
        for r in p.interiors:
            d += ' M' + ' L'.join(f'{x:.0f},{-y:.0f}' for x, y in r.coords) + ' Z'
        out.append(f'<path d="{d}" fill-rule="evenodd" {attrs}/>')
    return '\n'.join(out)

def label(p, name, area=True, dx=0, dy=0, size=380):
    c = p.representative_point() if name not in ('다이닝·주방',) else p.centroid
    x, y = c.x + dx, c.y + dy
    s = f'<text x="{x:.0f}" y="{-y:.0f}" font-size="{size}" text-anchor="middle" font-weight="600" fill="#2b2b2b">{name}</text>'
    if area:
        s += f'<text x="{x:.0f}" y="{-y + size * 1.15:.0f}" font-size="{size * 0.72:.0f}" text-anchor="middle" fill="#666">{p.area / 1e6:.1f}㎡ ({p.area / 1e6 / 3.3058:.1f}평)</text>'
    return s

def stairs_svg(x0, x1, y0, y1, n, up_label, direction):
    """direction: +1 오르는 방향 x증가"""
    s = []
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        s.append(f'<line x1="{x:.0f}" y1="{-y0:.0f}" x2="{x:.0f}" y2="{-y1:.0f}" stroke="#777" stroke-width="20"/>')
    ym = (y0 + y1) / 2
    xa, xb = (x0 + 200, x1 - 200) if direction > 0 else (x1 - 200, x0 + 200)
    s.append(f'<line x1="{xa:.0f}" y1="{-ym:.0f}" x2="{xb:.0f}" y2="{-ym:.0f}" stroke="#333" stroke-width="30" marker-end="url(#arr)"/>')
    s.append(f'<text x="{(x0 + x1) / 2:.0f}" y="{-ym - 120:.0f}" font-size="260" text-anchor="middle" fill="#333">{up_label}</text>')
    return '\n'.join(s)

# ---------------------------------------------------------------- 대지 (기존 도면에서 추정한 좌표)
PX = lambda px, py: ((px - 395) * 31.51, (932 - py) * 31.47)
BOUNDARY_W = [PX(1790, 168), PX(1275, 285), PX(715, 352), PX(625, 330), PX(610, 425), PX(420, 575), PX(195, 710), PX(5, 1045)]
BOUNDARY_S = [PX(0, 1250), PX(400, 1278), PX(620, 1305), PX(745, 1162), PX(640, 1085), PX(915, 940), PX(988, 975),
              PX(1270, 1048), PX(1590, 1093), PX(1740, 1095), PX(1790, 1130)]
ROAD = [PX(560, 40), PX(640, 40), PX(640, 240), PX(610, 425), PX(420, 575), PX(195, 710), PX(40, 1010),
        PX(35, 1010), PX(190, 715), PX(395, 530), PX(558, 365)]
WALL_L1 = [PX(625, 330), PX(715, 352), PX(1275, 285), PX(1815, 155)]
WALL_L2 = [PX(620, 388), PX(710, 415), PX(1280, 345), PX(1830, 218)]
WALL_LOW = [PX(360, 680), PX(990, 680), PX(1400, 683), PX(1790, 633)]
FILL_W = [(0, 0), PX(230, 800), PX(360, 680)]
FILL_E = [(7549, 0), PX(990, 680)]
# 평탄화: 남측 마당 성토 후 새 옹벽선 (남측 경계에서 약 2m 안쪽)
NEWS = [(7549, 0), (10500, -1300), (16385, 1800), (18686, 700), (27571, -1600), (37654, -3000), (43900, -3100)]
DECK = Polygon([W(-1000, 8000), W(6500, 8000), W(6500, 11000), W(-1000, 11000)])
DECK = DECK.intersection(Polygon([(7549, 0), (10500, -1300), (16385, 1800), (18686, 700), (27571, -1600), (37654, -3000), (43900, -3100), (43900, 30000), (7549, 30000)]).buffer(-400))

def site_svg():
    s = [svg_poly(Polygon(ROAD), fill='#cfcfcf', stroke='none')]
    lawn = Polygon(NEWS + [(43900, 30000), (7549, 30000)]).buffer(0).intersection(Polygon([(-20000, -20000)] + [(-20000, WALL_L2[0][1])] + WALL_L2 + [(45217, -20000)]).buffer(0)).difference(Polygon(ROAD).buffer(300))
    s.append(svg_poly(lawn, fill='#e4eed8', stroke='none'))
    s.append(f'<text x="28000" y="-3500" font-size="420" text-anchor="middle" fill="#5d7a45">잔디마당 (성토·평탄화, FL-150)</text>')
    for wl, w in [(WALL_L1, 600), (WALL_L2, 600), (NEWS, 350)]:
        s.append(svg_poly(LineString(wl).buffer(w / 2, cap_style=2), fill='#d8cbb5', stroke='#9a8b70', stroke_width=25))
    for f in (FILL_W,):
        s.append(f'<polyline points="{" ".join(f"{x:.0f},{-y:.0f}" for x, y in f)}" fill="none" stroke="#9a8b70" stroke-width="250"/>')
    for b in (BOUNDARY_W, BOUNDARY_S):
        s.append(f'<polyline points="{" ".join(f"{x:.0f},{-y:.0f}" for x, y in b)}" fill="none" stroke="#e02020" stroke-width="70" stroke-dasharray="500,180,90,180"/>')
    return '\n'.join(s)

def dim(p0, p1, off, text=None, size=300):
    (x0, y0), (x1, y1) = p0, p1
    L = math.dist(p0, p1)
    dx, dy = (x1 - x0) / L, (y1 - y0) / L
    nx, ny = -dy, dx
    a = (x0 + nx * off, y0 + ny * off); b = (x1 + nx * off, y1 + ny * off)
    t = text or f'{L:,.0f}'
    ang = -math.degrees(math.atan2(dy, dx))
    if ang < -90 or ang > 90:
        ang += 180
    mx, my = (a[0] + b[0]) / 2 + nx * 180, (a[1] + b[1]) / 2 + ny * 180
    return (f'<line x1="{a[0]:.0f}" y1="{-a[1]:.0f}" x2="{b[0]:.0f}" y2="{-b[1]:.0f}" stroke="#444" stroke-width="18"/>'
            + ''.join(f'<line x1="{p[0] - (dx + dy) * 120:.0f}" y1="{-(p[1] + (dx - dy) * 120):.0f}" x2="{p[0] + (dx + dy) * 120:.0f}" y2="{-(p[1] - (dx - dy) * 120):.0f}" stroke="#444" stroke-width="22"/>' for p in (a, b))
            + f'<text x="{mx:.0f}" y="{-my:.0f}" font-size="{size}" text-anchor="middle" fill="#333" transform="rotate({ang:.1f} {mx:.0f} {-my:.0f})">{t}</text>')

def furniture_1f():
    f = []
    st = dict(fill='none', stroke='#8a8a8a', stroke_width=20)
    f.append(svg_poly(box(3000, 1500, 5600, 2400), **st))           # 소파
    f.append(svg_poly(box(3300, 3000, 5300, 3500), **st))           # TV장
    isl = Polygon([W(4300, 4900), W(6900, 4900), W(6900, 5800), W(4300, 5800)])
    f.append(svg_poly(isl, **st))                                    # 아일랜드
    cnt = Polygon([W(3400, 2900), W(8300, 2900), W(8300, 3550), W(3400, 3550)])
    f.append(svg_poly(cnt, **st))                                    # 주방 카운터
    tab = Polygon([W(300, 4800), W(2400, 4800), W(2400, 5900), W(300, 5900)])
    f.append(svg_poly(Polygon([W(7300, 6200), W(8500, 6200), W(8500, 7200), W(7300, 7200)]), **st))
    f.append(svg_poly(tab, **st))                                    # 식탁
    f.append(svg_poly(box(23400, 9900, 25500, 12000), **st))         # 안방 침대
    f.append(svg_poly(box(19000, 9900, 20500, 11900), **st))         # 침실2 침대
    f.append(svg_poly(box(27000, 9750, 28700, 10550), **st))         # 욕조
    f.append(svg_poly(box(28800, 9700, 30000, 11300), fill='none', stroke='#3a8fd6', stroke_width=20, stroke_dasharray='120,80'))  # 무턱 샤워
    f.append(svg_poly(box(26700, 13300, 29900, 13848), **st))        # 세면대 2
    f.append(svg_poly(box(30300, 13300, 32250, 13848), **st))        # 드레스 수납
    f.append(svg_poly(box(30300, 9648, 32250, 10200), **st))
    for c in [(1100, 4150), (24300, 13000), (28400, 12300), (10900, 9700), (7000, 8000)]:
        f.append(svg_poly(Point(c).buffer(750), fill='none', stroke='#2e9e6a', stroke_width=18, stroke_dasharray='60,60'))  # 휠체어 회전원 1.5m
    return '\n'.join(f)

def render(level):
    if level == '1F':
        rooms = rooms_1f
        ext, intw, ce, ci = walls_1f()
        walls = unary_union([ext.difference(ce), intw.difference(ci)])
        glass = [LineString([edge_pt(i, s0), edge_pt(i, s1)]).parallel_offset(-EXT / 2) for i, ops in openings.items() for (s0, s1, *_r) in ops]
        title = '1층 평면도'
    elif level == 'B1':
        rooms = rooms_b1
        ext = B1_BOX.difference(B1_BOX.buffer(-EXT, join_style=2)).difference(box(250, -100, 7299, 260))
        intw = unary_union([LineString([(250, 5250), (1980, 5250)]).buffer(60, cap_style=2),
                            LineString([(1980, 5250), (1980, 7050)]).buffer(60, cap_style=2),
                            LineString([(2700, 5925), (7299, 5925)]).buffer(60, cap_style=2)])
        intw = intw.difference(door_cut((1100, 5250), 1000))
        walls = unary_union([ext, intw])
        glass = []
        title = '지하 1층 (주차) 평면도'
    else:
        rooms = {}
        walls = Polygon()
        glass = []
        title = '지붕 평면도 (박공지붕)'
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-13500 -27000 61000 38500" width="2440" height="1540" font-family="WenQuanYi Zen Hei, sans-serif">',
         '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#333"/></marker></defs>',
         '<rect x="-13500" y="-27000" width="61000" height="38500" fill="#ffffff"/>',
         site_svg()]
    if level != 'B1':
        s.append(svg_poly(OUTLINE if level == '1F' else LEFT, fill='#ffffff', stroke='none'))
    if level == '1F':
        s.append(svg_poly(DECK, fill='#efe6d6', stroke='#a08c6a', stroke_width=30))
        s.append(label(DECK, '남측 테라스', area=False, size=340))
    if level == 'AT':
        RX = 7549 / 2; RWY = (9348 + 14148) / 2
        lb = box(-500, -500, 8049, 7800)
        bfp = OUTLINE.difference(LEFT).difference(WING).buffer(600, join_style=2).difference(LEFT).difference(box(XJ, -1e6, 1e6, 1e6))
        bfp = bfp.intersection(band_poly(-3000, 20000, -600, 8600))
        ws = unary_union([box(XJ, 8748, 32950, RWY), box(XJ - 2500, 9348, XJ, RWY)])
        wn = unary_union([box(XJ, RWY, 32950, 15248), box(XJ - 2500, RWY, XJ, 14148)])
        for fp, col in [(ws, '#6c7076'), (wn, '#5d6166'), (bfp.intersection(band_poly(-1e5, 1e5, -1e5, 4000)), '#5d6166'),
                        (bfp.intersection(band_poly(-1e5, 1e5, 4000, 1e5)), '#6c7076'),
                        (lb.intersection(box(-1e6, -1e6, RX, 1e6)), '#5d6166'), (lb.intersection(box(RX, -1e6, 1e6, 1e6)), '#6c7076')]:
            s.append(svg_poly(fp, fill=col, stroke='#2b2b2b', stroke_width=30))
        ridges = [LineString([(RX, -500), (RX, 7800)]), LineString([(XJ - 2500, RWY), (32950, RWY)]),
                  LineString([W(-3000, 4000), W(20000, 4000)]).intersection(bfp)]
        for r in ridges:
            for seg in getattr(r, 'geoms', [r]):
                s.append(f'<polyline points="{" ".join(f"{x:.0f},{-y:.0f}" for x, y in seg.coords)}" fill="none" stroke="#f2c14e" stroke-width="80"/>')
        s.append('<text x="3775" y="-3300" font-size="300" text-anchor="middle" fill="#fff">거실동 30°</text>')
        s.append(f'<text x="25000" y="{-RWY - 700:.0f}" font-size="300" text-anchor="middle" fill="#fff">날개 6/12 (26.6°)</text>')
        c = W(7000, 2000)
        s.append(f'<text x="{c[0]:.0f}" y="{-c[1]:.0f}" font-size="300" text-anchor="middle" fill="#fff">사선부 6/12</text>')
        s.append('<text x="-12500" y="-22900" font-size="300" fill="#555">노란 선 = 용마루 · 짙은 회색 강판(또는 기와) · 처마 600 (북측 툇마루 쪽 1,100)</text>')
    for name, p in rooms.items():
        z = ZONE.get(name, 'circ')
        s.append(svg_poly(p, fill=FILL[z], stroke='none'))
    if level == '1F':
        s.append(furniture_1f())
        s.append(stairs_svg(2100, 6260, 5975, 7000, 16, 'DN (지하)', -1))
        s.append(svg_poly(box(2100, 5265, 6260, 5865), fill='none', stroke='#8a8a8a', stroke_width=20))
        s.append('<text x="4180" y="-5480" font-size="240" text-anchor="middle" fill="#666">붙박이 수납장</text>')
    if level == 'B1':
        for x0, w0 in ((300, 3300), (4300, 2500)):
            s.append(svg_poly(box(x0, 250, x0 + w0, 5250), fill='none', stroke='#888', stroke_width=25, stroke_dasharray='200,120'))
        s.append(stairs_svg(2100, 6260, 5975, 7000, 16, 'UP (1층)', 1))
        s.append('<text x="3775" y="-900" font-size="300" text-anchor="middle" fill="#555">장애인 주차 3.3m + 일반 2.5m (EV 충전·자율주행 차량 대응)</text>')
    s.append(svg_poly(walls, fill='#222', stroke='none'))
    for g in glass:
        if not g.is_empty:
            s.append(f'<polyline points="{" ".join(f"{x:.0f},{-y:.0f}" for x, y in g.coords)}" fill="none" stroke="#3a8fd6" stroke-width="60"/>')
    for name, p in rooms.items():
        if name in ('EV',):
            s.append(label(p, 'EV', area=False, size=300))
        elif name in ('계단실', '계단·홀'):
            continue
        elif p.area > 2.5e6:
            s.append(label(p, name, size=330 if p.area < 9e6 else 380))
    # 치수
    if level != 'AT':
        s.append(dim((0, 0), (7549, 0), -1500))
    if level == '1F':
        s.append(dim((0, 0), (32550, 0), -2600, '32,550'))
        s.append(dim(SE_END, (32550, 9348), -1300))
        s.append(dim((32550, 9348), (32550, 14148), -1200))
        s.append(dim((0, 7300), (0, 0), -1200))
        s.append(dim((7549, 0), SE_END, -1200))
        s.append(f'<text x="-12500" y="-24800" font-size="700" font-weight="700" fill="#111">{title}</text>')
    elif level == 'B1':
        s.append(dim((0, 7300), (0, 0), -1200))
        s.append(f'<text x="-12500" y="-24800" font-size="700" font-weight="700" fill="#111">{title}</text>')
    else:
        s.append(f'<text x="-12500" y="-24800" font-size="700" font-weight="700" fill="#111">{title}</text>')
    s.append('<text x="-12500" y="-23900" font-size="320" fill="#555">B안 재설계 · 1:150 상당 · 대지·옹벽 좌표는 기존 도면에서 추정</text>')
    s.append('</svg>')
    return '\n'.join(s)

if __name__ == '__main__':
    import sys
    for lv in ('1F', 'B1', 'AT'):
        open(f'plan_{lv}.svg', 'w').write(render(lv))
    print('ok')

# -*- coding: utf-8 -*-
import math
from shapely.geometry import Polygon, LineString, box, Point
from shapely.ops import unary_union
import geom2 as G
from design2 import *

def sp(g, **kw):
    attrs = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    out = []
    for p in getattr(g, 'geoms', [g]):
        if p.is_empty or p.geom_type != 'Polygon': continue
        d = 'M' + ' L'.join(f'{x:.0f},{-y:.0f}' for x, y in p.exterior.coords) + ' Z'
        for r in p.interiors:
            d += ' M' + ' L'.join(f'{x:.0f},{-y:.0f}' for x, y in r.coords) + ' Z'
        out.append(f'<path d="{d}" fill-rule="evenodd" {attrs}/>')
    return '\n'.join(out)
def pl(pts, **kw):
    attrs = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f'<polyline points="{" ".join(f"{x:.0f},{-y:.0f}" for x, y in pts)}" fill="none" {attrs}/>'
def tx(x, y, s, size=330, anchor='middle', fill='#222', weight=400, rot=None):
    r = f' transform="rotate({rot} {x:.0f} {-y:.0f})"' if rot is not None else ''
    return f'<text x="{x:.0f}" y="{-y:.0f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}"{r}>{s}</text>'
def dim(p0, p1, off, text=None, size=300):
    (x0, y0), (x1, y1) = p0, p1
    Lg = math.dist(p0, p1); dx, dy = (x1 - x0) / Lg, (y1 - y0) / Lg; nx, ny = -dy, dx
    a = (x0 + nx * off, y0 + ny * off); b = (x1 + nx * off, y1 + ny * off)
    ang = -math.degrees(math.atan2(dy, dx))
    if ang < -90 or ang > 90: ang += 180
    m = ((a[0] + b[0]) / 2 + nx * 190 * (1 if off > 0 else -1) * 0 + nx * 170, (a[1] + b[1]) / 2 + ny * 170)
    s = pl([a, b], stroke='#444', stroke_width=18)
    for p, q in ((p0, a), (p1, b)):
        s += pl([p, (q[0] + nx * 120 * (1 if off > 0 else -1), q[1] + ny * 120 * (1 if off > 0 else -1))], stroke='#888', stroke_width=10)
        s += pl([(q[0] - (dx + nx) * 110, q[1] - (dy + ny) * 110), (q[0] + (dx + nx) * 110, q[1] + (dy + ny) * 110)], stroke='#444', stroke_width=22)
    return s + tx(m[0], m[1], text or f'{Lg:,.0f}', size, rot=round(ang, 1))

FILL = {'garage': '#e3e3df', 'service': '#e4e7e1', 'circ': '#f3eee3', 'public': '#f1dcc0', 'private': '#d8e5f1'}

def plan():
    X0, X1, Y0, Y1 = -24500, 40500, -24500, 8500     # 로컬 y (북+)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{X0} {-Y1} {X1 - X0} {Y1 - Y0}" width="{(X1 - X0) * 0.03:.0f}" height="{(Y1 - Y0) * 0.03:.0f}" font-family="WenQuanYi Zen Hei, sans-serif">',
         f'<rect x="{X0}" y="{-Y1}" width="{X1 - X0}" height="{Y1 - Y0}" fill="#e9ecdf"/>']
    s.append(sp(T2, fill='#dfe8d2')); s.append(sp(T1, fill='#d6e2c6'))
    s.append(sp(PADP, fill='#e3eed6', stroke='none'))
    s.append(sp(ROAD, fill='#c9c9c7'))
    for w in (WALL_L1, WALL_L2): s.append(sp(w, fill='#cdbfa5', stroke='#93856a', stroke_width=20))
    s.append(sp(RWALL, fill='#b9ad98', stroke='#857a66', stroke_width=20))
    s.append(sp(G.COURT, fill='#dedad0')); s.append(sp(G.REAR.difference(G.SERV), fill='#ece8dc')); s.append(sp(G.SERV, fill='#d9d5ca', stroke='#aaa', stroke_width=15))
    s.append(sp(B(-8500, 6000, -7000, 12800), fill='#d4d0c5'))
    s.append(sp(G.WALK, fill='#e7e1d2', stroke='#b3a98f', stroke_width=20)); s.append(sp(B(-9300, 13400, -7300, 14800), fill='#e7e1d2', stroke='#b3a98f', stroke_width=20))
    for d in (B(7500, 14600, 15300, 16800), B(15300, 12600, 26500, 14600)): s.append(sp(d, fill='#e6d2b4', stroke='#b59a6f', stroke_width=20))
    s.append(sp(B(15300, 15200, 17100, 16600), fill='#e7e1d2', stroke='#b3a98f', stroke_width=20))
    s.append(sp(G.POOL, fill='#bcd9e6', stroke='#5f6b70', stroke_width=60))
    for p in G.P:
        if p['n'].startswith('Bed_'): s.append(sp(Polygon(p['p']), fill='#c9c2e6' if 'Lav' in p['n'] or 'Hyd' in p['n'] else '#b9d3a0', stroke='none'))
        if p['n'].startswith('VegBed') and 'Green' not in p['n']: s.append(sp(Polygon(p['p']), fill='#b7cf96', stroke='#8a6a45', stroke_width=30))
        if p['n'].startswith('StepStone') or p['n'].startswith('Jangdok'): s.append(sp(Polygon(p['p']), fill='#b5b2aa', stroke='none'))
    for (u, d, r, h, kind) in G.TREES:
        s.append(f'<circle cx="{u}" cy="{d}" r="{r}" fill="{"#e0a58a" if kind == "maple" else "#a9cc8c"}" fill-opacity="0.75" stroke="#6f8f55" stroke-width="20"/>')
    s.append(pl(G.FENCE[0]['p'], stroke='#fff', stroke_width=60)); s.append(pl(G.FENCE[0]['p'], stroke='#8a8a80', stroke_width=14, stroke_dasharray='200,120'))
    for b in (BOUND_W, BOUND_S): s.append(pl(b, stroke='#e02020', stroke_width=70, stroke_dasharray='500,180,90,180'))
    # 건물
    for k, v in ROOMS.items(): s.append(sp(room_poly(k), fill=FILL[v[4]]))
    for poly, dw, nm in PORCH: s.append(sp(poly, fill='none', stroke='#7a6a50', stroke_width=22, stroke_dasharray='160,110'))
    for (u, d) in POSTS: s.append(sp(B(u - 90, d - 90, u + 90, d + 90), fill='#8a5f35'))
    cuts = unary_union([G.band(i, s0, s1, -400, 400) for i, ops in G.EDGE_OPS.items() for (s0, s1, *_r) in ops])
    walls = unary_union([OUTLINE.difference(INNER).difference(cuts), G.allw.difference(G.dc)])
    for p in G.P:
        if p['g'] == 'Furniture' and not p['n'].endswith('_Top') and 'Leg' not in p['n'] and not p['n'].startswith('Attic'): s.append(sp(Polygon(p['p']), fill='none', stroke='#8b8b8b', stroke_width=18))
        if 'Car' in p['n'] and 'Body' in p['n']: s.append(sp(Polygon(p['p']).buffer(-60).buffer(60), fill='#cfd3d6' if 'Guest' in p['n'] else '#bfc4c8', stroke='#777', stroke_width=18))
        if p['n'] == 'Outdoor_Table': s.append(sp(Polygon(p['p']), fill='#e8d3ae', stroke='#8b8b8b', stroke_width=18))
        if p['n'] == 'Dining_Table': s.append(sp(Polygon(p['p']), fill='#e8d3ae', stroke='#6b5a3a', stroke_width=25))
    for c in G.CH: s.append(f'<rect x="{c[0] - 210:.0f}" y="{-c[1] - 210:.0f}" width="420" height="420" rx="90" fill="#fff" stroke="#8b6b45" stroke-width="18"/>')
    s.append(sp(B(-1125, 8700, -125, 12700), fill='#f3eee3', stroke='#777', stroke_width=14))
    for k in range(16): s.append(pl([(-1125, -(12700 - 250 * k)), (-125, -(12700 - 250 * k))], stroke='#999', stroke_width=8))
    s.append(tx(-625, -8450, '다락 계단', 170, fill='#555'))
    s.append(sp(walls, fill='#1f1f1f'))
    s.append(sp(B(17650, 5100, 18550, 5600), fill='#7d7466'))
    for i, ops in G.EDGE_OPS.items():
        for (s0, s1, sill, head, kind) in ops:
            a, (ex, ey), Lg = G.edge_frame(i); nx, ny = -ey, ex
            col = {'gdoor': '#a8763f', 'wdoor': '#7e5230', 'sdoor': '#666'}.get(kind, '#2f8fd8')
            s.append(pl([(a[0] + ex * s0 + nx * 125, a[1] + ey * s0 + ny * 125), (a[0] + ex * s1 + nx * 125, a[1] + ey * s1 + ny * 125)], stroke=col, stroke_width=70 if kind != 'gdoor' else 110))
    for (u, d) in [(1900, 10700), (1500, 7400), (5900, 11450), (10800, 9900), (25480, 8550), (29900, 9700), (27400, 14800), (-700, 9400), (5000, 7400)]:
        s.append(f'<circle cx="{u}" cy="{d}" r="750" fill="none" stroke="#2e9e6a" stroke-width="16" stroke-dasharray="70,70"/>')
    for k, v in ROOMS.items():
        p = room_poly(k); c = p.centroid; a = p.area / 1e6; small = a < 8
        dy = {'주방': 1300, '다이닝 (14인)': -1500, '거실': -1700, '침실2 (게스트·서재)': 900, '안방': -1400, '차고 (2대)': 600}.get(k, 0)
        s.append(tx(c.x, c.y + dy + 60, k, 250 if small else 330, weight=700))
        s.append(tx(c.x, c.y + dy - (300 if small else 380), f'{a:.1f}㎡ · {a / 3.3058:.1f}평', 200 if small else 240, fill='#555'))
    s.append(tx(-12300, -9000, '진입 마당', 380, fill='#666', weight=700)); s.append(tx(-12300, -9550, '도로와 같은 높이 · 손님 주차 2~4대', 230, fill='#777'))
    s.append(tx(-3500, -14150, '처마 밑 보행로 (경사로 1:15)', 220, fill='#665')); s.append(tx(11400, -16000, '포치 · 야외 12인 식탁', 230, fill='#654'))
    s.append(tx(20500, -13700, '툇마루', 240, fill='#654')); s.append(tx(20500, -16300, '중정 수반', 230, fill='#456'))
    s.append(tx(20500, -18800, '남쪽 잔디마당 (성토·평탄화)', 330, fill='#5d7a45')); s.append(tx(11500, -3200, '뒤뜰 (자갈·디딤돌)', 280, fill='#776'))
    s.append(tx(5200, -4300, '서비스 마당', 220, fill='#665')); s.append(tx(6300, -1000, '장독대', 200, fill='#665'))
    s.append(tx(29500, -19250, '텃밭', 220, fill='#575')); s.append(tx(22500, 8300 - 600, '뒷집 대지 (윗단)', 300, fill='#787'))
    s.append(tx(-9500, 3000, '도로 (오르막 ↗)', 260, fill='#666', rot=-28))
    s.append(dim((-7000, -5600), (32000, -5600), 4300, '39,000 (차고 7,000 + 본채 32,000)')); s.append(dim((32000, -12600), (32000, -5600), -1100, '7,000'))
    s.append(dim((32000, -17100), (32000, -12600), -1100, '4,500')); s.append(dim((7500, -14600), (15300, -14600), -3300, '7,800'))
    s.append(dim((24000, -5600), (24000, -600), 500, '5,000', 260)); s.append(dim((-7000, -13200), (-7000, -5600), 900, '7,600'))
    s.append(dim((26500, -17100), (32000, -17100), -900, '5,500'))
    nx_, ny_ = UX[1], NY[1]
    ox, oy = 37500, 5200
    s.append(f'<circle cx="{ox}" cy="{-oy}" r="900" fill="#fff" stroke="#333" stroke-width="30"/>')
    s.append(pl([(ox - nx_ * 800, oy - ny_ * 800), (ox + nx_ * 1300, oy + ny_ * 1300)], stroke='#222', stroke_width=50)); s.append(tx(ox + nx_ * 1750, oy + ny_ * 1650, 'N', 420, weight=700))
    s.append(tx(X0 + 700, Y1 - 1100, 'C안 · 1층 평면도 + 차고 위 다락 (엘리베이터 없음)', 620, 'start', '#111', 700))
    s.append(tx(X0 + 700, Y1 - 1800, f'난방면적 {HEATED.area / 1e6:.0f}㎡({HEATED.area / 1e6 / 3.3058:.0f}평) + 차고 {GAR.area / 1e6:.0f}㎡({GAR.area / 1e6 / 3.3058:.0f}평) · 초록 점선 원 = 휠체어 회전 지름 1.5m · 대지·석축·도로 좌표는 기존 도면에서 추정', 260, 'start', '#555'))
    # ---- 다락 평면 인셋 (차고 위)
    ox, oy = -23300, -24000            # 인셋 원점 (좌하단)
    def R(u0, d0, u1, d1, **kw):       # 차고 좌표(u -7000..0, d 5600..13200) -> 인셋
        return sp(box(ox + (u0 + 7000), oy + (13200 - max(d0, d1)), ox + (u1 + 7000), oy + (13200 - min(d0, d1))), **kw)
    s.append(sp(box(ox - 500, oy - 500, ox + 7500, oy + 9300), fill='#ffffff', stroke='#999', stroke_width=20))
    s.append(R(-7000, 5600, 0, 13200, fill='#1f1f1f'))
    s.append(R(-6750, 5850, -125, 12950, fill='#d8e5f1'))
    s.append(R(-6750, 7980, -125, 10820, fill='#c4d9ec', stroke='#2e6fa8', stroke_width=14, stroke_dasharray='90,70'))
    s.append(R(-1125, 8700, -125, 12700, fill='#f3eee3', stroke='#777', stroke_width=14))
    for k in range(16): s.append(R(-1125, 12700 - 250 * k - 250, -125, 12700 - 250 * k, fill='none', stroke='#999', stroke_width=8))
    s.append(R(-7000, 9150, -6750, 9650, fill='#c8642a'))
    s.append(tx(ox + 1250, oy + 3730, '원형 창 Ø500', 170, fill='#a04a18'))
    for u0 in (-5600, -3200): s.append(R(u0, 10700, u0 + 900, 12100, fill='#bfe0f5', stroke='#2f8fd8', stroke_width=20))
    for (a, b_, c, d_) in [(-6700, 8600, -6000, 10200), (-4600, 8000, -2400, 8900), (-6600, 6300, -1500, 6700), (-6600, 12300, -1500, 12700)]:
        s.append(R(a, b_, c, d_, fill='none', stroke='#8b8b8b', stroke_width=14))
    s.append(tx(ox + 3500, oy + 8650, '다락 평면 (차고 위, 개인 공간)', 300, weight=700))
    s.append(tx(ox + 2900, oy + 4000, '서서 쓰는 구간', 210, fill='#2e6fa8')); s.append(tx(ox + 2900, oy + 3650, '(천장 2.0m 이상, 폭 2.8m)', 180, fill='#2e6fa8'))
    s.append(tx(ox + 6400, oy + 2500, '계단', 190, fill='#555')); s.append(tx(ox + 1850, oy + 1800, '천창', 170, fill='#2f6fa0')); s.append(tx(ox + 4250, oy + 1800, '천창', 170, fill='#2f6fa0'))
    s.append(tx(ox + 3500, oy - 250, '바닥 43㎡ · 천장 평균 약 1.6m (다락 기준 1.8m 이하)', 190, fill='#555'))
    s.append('</svg>')
    return '\n'.join(s)

def section():
    k = 0.045
    X = lambda d: (d + 14000) * k
    Y = lambda z: (12700 - z) * k
    Wd, Hd = X(27000), Y(-2600)
    def poly(pts, **kw):
        attrs = ' '.join(f'{a.replace("_", "-")}="{v}"' for a, v in kw.items())
        return f'<polygon points="{" ".join(f"{X(d):.1f},{Y(z):.1f}" for d, z in pts)}" {attrs}/>'
    def line(pts, **kw):
        attrs = ' '.join(f'{a.replace("_", "-")}="{v}"' for a, v in kw.items())
        return f'<polyline points="{" ".join(f"{X(d):.1f},{Y(z):.1f}" for d, z in pts)}" fill="none" {attrs}/>'
    def t(d, z, s, size=14, anchor='middle', fill='#222', w=400):
        return f'<text x="{X(d):.1f}" y="{Y(z):.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{w}">{s}</text>'
    nat = lambda d: 4470 - 0.18 * d
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wd:.0f} {Hd:.0f}" width="{Wd:.0f}" height="{Hd:.0f}" font-family="WenQuanYi Zen Hei, sans-serif"><rect width="100%" height="100%" fill="#f7f8f4"/>']
    ground = [(-14000, 6450), (-1895, 6450), (-1895, 4650), (0, 4650), (0, 2850), (20200, 2850), (20200, 2970), (20550, 2970), (20550, nat(20550)), (27000, nat(27000)), (27000, -2600), (-14000, -2600)]
    s.append(poly(ground, fill='#d9d2c2', stroke='#6b6252', stroke_width=1.5))
    s.append(poly([(9000, 2850), (20200, 2850), (20200, nat(20200))], fill='#e9c9a8', stroke='none'))           # 성토
    s.append(poly([(600, 2850), (9000, 2850), (600, nat(600))], fill='#ffffff', fill_opacity=0.55, stroke='none'))
    s.append(line([(-14000, nat(-14000)), (27000, nat(27000))], stroke='#9a6b3a', stroke_width=1.3, stroke_dasharray='7,5'))
    for d0, d1, z1 in [(-1895, -1295, 6450), (0, 600, 4650), (20200, 20550, 2970)]:
        s.append(poly([(d0, -1500 if d0 < 20000 else 300), (d1, -1500 if d0 < 20000 else 300), (d1, z1), (d0, z1)], fill='#a99c84', stroke='#5f5646', stroke_width=1))
    # 뒷집
    s.append(poly([(-11200, 6450), (-5200, 6450), (-5200, 9300), (-11200, 9300)], fill='#ecebe6', stroke='#777', stroke_width=1.2))
    s.append(poly([(-11600, 9120), (-8200, 10650), (-4800, 9120), (-4800, 9320), (-8200, 10850), (-11600, 9320)], fill='#8b9094', stroke='#555', stroke_width=1))
    # 본채 단면 (거실 위치)
    s.append(poly([(5600, 2850), (12600, 2850), (12600, 3000), (5600, 3000)], fill='#8f8a82'))
    for d0, d1 in [(5600, 5850), (12350, 12600)]:
        s.append(poly([(d0, 3000), (d1, 3000), (d1, 5700), (d0, 5700)], fill='#efe9dd', stroke='#444', stroke_width=1.2))
    roof = [(5300, 5550), (9100, 7450), (12900, 5550), (12900, 5796), (9100, 7696), (5300, 5796)]
    s.append(poly(roof, fill='#565b61', stroke='#333', stroke_width=1))
    s.append(poly([(5850, 3000), (12350, 3000), (12350, 3015), (5850, 3015)], fill='#c9a678'))
    s.append(poly([(12600, 5450), (14650, 5327), (14650, 5447), (12600, 5570)], fill='#565b61')); s.append(poly([(14460, 2985), (14600, 2985), (14600, 5130), (14460, 5130)], fill='#a67c52'))
    s.append(poly([(12600, 2850), (14600, 2850), (14600, 2985), (12600, 2985)], fill='#b08a62'))
    s.append(poly([(5100, 2850), (5600, 2850), (5600, 7780), (5100, 7780)], fill='#9a8f7d', stroke='#555', stroke_width=0.8))
    s.append(line([(5350, 7896), (14850, 7896)], stroke='#565b61', stroke_width=2, stroke_dasharray='8,4'))
    s.append(t(14900, 8420, '홀 용마루 (뒤쪽, 점선) +5.05m', 12, 'start', '#444'))
    # 조망선
    eye = (-5300, 8100)
    s.append(f'<circle cx="{X(eye[0]):.1f}" cy="{Y(eye[1]):.1f}" r="4" fill="#1b6fc2"/>')
    for (d1, z1) in [(9100, 7696), (5350, 7896)]:
        sl = (z1 - eye[1]) / (d1 - eye[0])
        s.append(line([eye, (27000, eye[1] + sl * (27000 - eye[0]))], stroke='#1b6fc2', stroke_width=1.6, stroke_dasharray='9,5'))
    s.append(line([eye, (27000, eye[1])], stroke='#1b6fc2', stroke_width=0.8, stroke_dasharray='2,5'))
    s.append(t(17500, 8330, '뒷집 눈높이 수평선', 12, 'start', '#1b6fc2')); s.append(t(17500, 6800, '지붕을 스치는 조망선 (수평에서 약 1.1~1.6° 아래)', 12, 'start', '#1b6fc2'))
    s.append(t(-8200, 7700, '뒷집 (위치·높이 추정)', 13)); s.append(t(-5100, 8500, '눈높이 +8.1m', 12, 'start', '#1b6fc2'))
    s.append(t(9100, 4500, '본채 (거실)', 14, w=700)); s.append(t(9100, 8420, '본채 용마루 +4.85m', 12))
    s.append(t(3100, 3250, '뒤뜰 5.0m', 13)); s.append(t(13650, 4200, '툇마루', 12)); s.append(t(17400, 3150, '잔디마당', 13))
    s.append(t(15500, 1500, '성토 (추정)', 12, fill='#8a5a2a')); s.append(t(3600, 3900, '절토', 12, fill='#777'))
    s.append(t(21000, 3400, '새 옹벽 + 울타리', 12, 'start')); s.append(t(-900, 5600, '석축', 12)); s.append(t(22500, 900, '기존 지반 (추정 경사)', 12, 'start', '#9a6b3a'))
    s.append(line([(600, 3550), (5600, 3550)], stroke='#444', stroke_width=1))
    s.append(t(-13700, 12150, '남북 단면 (거실 위치) — 뒷집 조망 검토', 18, 'start', '#111', 700))
    s.append(t(-13700, 11550, '지반고·뒷집 위치는 도면과 모델에서 추정한 값입니다. 현황측량 후 다시 확인해야 합니다.', 12, 'start', '#666'))
    s.append('</svg>')
    return '\n'.join(s)

if __name__ == '__main__':
    open('plan_C.svg', 'w').write(plan()); open('section_C.svg', 'w').write(section()); print('ok')

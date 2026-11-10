# -*- coding: utf-8 -*-
"""C안 3D 데이터: 프리즘(평면 다각형 + 밑·윗면 평면) 목록과 디테일 스펙을 만든다."""
import json, math
from shapely.geometry import Polygon, LineString, box, Point
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from design2 import *
import detail

P = []
def C(z): return [0.0, 0.0, float(z)]
def sh(pl, d): return [pl[0], pl[1], pl[2] + d]
def zat(pl, x, y): return pl[0] * x + pl[1] * y + pl[2]

def nohole_parts(g):
    out = []
    for p in getattr(g, 'geoms', [g]):
        if p.is_empty or p.geom_type != 'Polygon' or p.area < 1.0:
            continue
        if not p.interiors:
            out.append(p); continue
        xs = sorted(set([Polygon(r).centroid.x for r in p.interiors]))
        minx, miny, maxx, maxy = p.bounds
        cuts = [minx - 1] + xs + [maxx + 1]
        for a, b in zip(cuts[:-1], cuts[1:]):
            out += nohole_parts(p.intersection(box(a, miny - 1, b, maxy + 1)))
    return out

def add(name, group, mat, geom, zb, zt, minarea=1500):
    if isinstance(zb, (int, float)): zb = C(zb)
    if isinstance(zt, (int, float)): zt = C(zt)
    if geom.is_empty: return
    parts = nohole_parts(geom.buffer(0))
    for k, p in enumerate(parts):
        p = orient(p.simplify(0.5), 1.0)
        if p.area < minarea: continue
        P.append({'n': name if len(parts) == 1 else f'{name}_{k + 1}', 'g': group, 'm': mat,
                  'p': [[round(x, 1), round(y, 1)] for x, y in list(p.exterior.coords)[:-1]],
                  'zb': [round(v, 6) for v in zb], 'zt': [round(v, 6) for v in zt]})

def halfplane(a, b, c, Lg=1e6):
    n = math.hypot(a, b)
    if n < 1e-12:
        return box(-Lg, -Lg, Lg, Lg) if c > 0 else Polygon()
    ax, ay = a / n, b / n
    px, py = -c / n * ax, -c / n * ay
    tx, ty = -ay, ax
    return Polygon([(px - Lg * tx, py - Lg * ty), (px + Lg * tx, py + Lg * ty),
                    (px + Lg * tx + Lg * ax, py + Lg * ty + Lg * ay), (px - Lg * tx + Lg * ax, py - Lg * ty + Lg * ay)])

# ================================================================= 지붕 (박공 4동의 상부 포락면)
OVE, OVG = 300, 250
PLN = []
def vol(name, fp, axis):
    x0, y0, x1, y1 = fp.bounds
    if axis == 'u':
        yr = (y0 + y1) / 2
        PLN.append((box(x0 - OVG, yr, x1 + OVG, y1 + OVE), [0.0, -TAN, EAVE + TAN * y1], name))
        PLN.append((box(x0 - OVG, y0 - OVE, x1 + OVG, yr), [0.0, TAN, EAVE - TAN * y0], name))
    else:
        xr = (x0 + x1) / 2
        PLN.append((box(x0 - OVE, y0 - OVG, xr, y1 + OVG), [TAN, 0.0, EAVE - TAN * x0], name))
        PLN.append((box(xr, y0 - OVG, x1 + OVE, y1 + OVG), [-TAN, 0.0, EAVE + TAN * x1], name))
vol('bar', BAR, 'u'); vol('hall', HALL, 'd'); vol('mast', MAST, 'd'); vol('gar', GAR, 'u')
REG = []
for i, (fp, pl, nm) in enumerate(PLN):
    vis = fp
    for j, (fq, pq, nq) in enumerate(PLN):
        if nq == nm: continue
        hp = halfplane(pq[0] - pl[0], pq[1] - pl[1], pq[2] - pl[2] - 0.5)
        vis = vis.difference(fq.intersection(hp))
    vis = vis.buffer(-2, join_style=2).buffer(2, join_style=2)
    for part in nohole_parts(vis):
        if part.area > 20000:
            REG.append((orient(part.simplify(1), 1.0), pl, nm))

def tops(geom, off=0.0):
    out = []
    for poly, pl, nm in REG:
        pc = geom.intersection(poly)
        for q in getattr(pc, 'geoms', [pc]):
            if q.geom_type == 'Polygon' and q.area > 1500:
                out.append((q, sh(pl, off)))
    return out
def hi_of(poly, pl):
    return max(zat(pl, x, y) for x, y in poly.exterior.coords)

ROOFSPEC = []
for k, (poly, pl, nm) in enumerate(REG):
    add(f'Roof_{nm}_{k + 1}', 'Roof', 'aluzinc', poly, pl, sh(pl, RT))
    ROOFSPEC.append({'p': [[round(x), round(y)] for x, y in list(poly.exterior.coords)[:-1]], 'pl': [round(v, 5) for v in pl], 'g': 'Roof', 'th': RT, 'sp': 450})
# 포치 덧지붕
for poly, dw, nm in PORCH:
    pl = porch_plane(dw)
    add(f'Porch_Roof_{nm}', 'Roof', 'aluzinc', poly, pl, sh(pl, 120))
    for part in nohole_parts(poly):
        ROOFSPEC.append({'p': [[round(x), round(y)] for x, y in list(orient(part, 1.0).exterior.coords)[:-1]], 'pl': [round(v, 5) for v in pl], 'g': 'Roof', 'th': 120, 'sp': 450})
# 포치 기둥·도리
for (u, d) in POSTS:
    dw = 14600 if d > 16000 else 12600
    pl = porch_plane(dw)
    add('Porch_Post', '1F', 'timber', B(u - 70, d - 70, u + 70, d + 70), FL - 15, zat(pl, u, -d) - 200)
for (u0, u1, d, dw) in [(-7300, 7500, 14930, 12600), (7400, 15400, 16730, 14600), (15300, 26500, 14530, 12600)]:
    z = zat(porch_plane(dw), 0, -d)
    add('Porch_Beam', '1F', 'timber', B(u0, d - 70, u1, d + 70), z - 200, z)

# ================================================================= 외벽
opts = list(OUTLINE.exterior.coords)[:-1]
n = len(opts)
def inner_pt(k):
    p0, p1, p2 = opts[k - 1], opts[k], opts[(k + 1) % n]
    def off(a, b):
        Lg = math.dist(a, b); dx, dy = (b[0] - a[0]) / Lg, (b[1] - a[1]) / Lg
        return (a[0] - dy * EXT, a[1] + dx * EXT), (dx, dy)
    (a1, d1), (a2, d2) = off(p0, p1), off(p1, p2)
    den = d1[0] * d2[1] - d1[1] * d2[0]
    t = ((a2[0] - a1[0]) * d2[1] - (a2[1] - a1[1]) * d2[0]) / den
    return (a1[0] + d1[0] * t, a1[1] + d1[1] * t)
inn = [inner_pt(k) for k in range(n)]
def edge_frame(i):
    a, b = opts[i], opts[(i + 1) % n]
    Lg = math.dist(a, b)
    return a, ((b[0] - a[0]) / Lg, (b[1] - a[1]) / Lg), Lg
def band(i, s0, s1, a0=-5000, a1=5000):
    a, (ex, ey), Lg = edge_frame(i)
    nx, ny = -ey, ex
    return Polygon([(a[0] + ex * s0 + nx * a0, a[1] + ey * s0 + ny * a0), (a[0] + ex * s1 + nx * a0, a[1] + ey * s1 + ny * a0),
                    (a[0] + ex * s1 + nx * a1, a[1] + ey * s1 + ny * a1), (a[0] + ex * s0 + nx * a1, a[1] + ey * s0 + ny * a1)])
EDGE_OPS = {i: [] for i in range(n)}
for (u0, d0, u1, d1, sill, head, kind) in OPENINGS:
    p0, p1 = (u0, -d0), (u1, -d1)
    hit = None
    for i in range(n):
        a, (ex, ey), Lg = edge_frame(i)
        ok = True; ss = []
        for p in (p0, p1):
            s = (p[0] - a[0]) * ex + (p[1] - a[1]) * ey
            off = abs(-(p[0] - a[0]) * ey + (p[1] - a[1]) * ex)
            if off > 2 or s < -1 or s > Lg + 1: ok = False
            ss.append(s)
        if ok: hit = (i, min(ss), max(ss)); break
    assert hit, ('opening not on outline', u0, d0, u1, d1)
    EDGE_OPS[hit[0]].append((hit[1], hit[2], sill, head, kind))

ACCENT = B(0, 12500, 7500, 12700)      # 현관 포치 안쪽 벽: 목재 톤
FRAMES = []
wk = [0]
def wall_solid(name, poly, zb, mat):
    if poly.is_empty or poly.area < 1500: return
    if zb < EAVE - 1:
        add(name, '1F', mat, poly, zb, EAVE)
    for sub, top in tops(poly):
        if hi_of(sub, top) > EAVE + 320:
            up = sub.intersection(halfplane(top[0], top[1], top[2] - EAVE - 25))
            add(name + '_Peak', 'Roof', 'siding_wood', up, max(zb, EAVE), top)

for i in range(n):
    a, (ex, ey), Lg = edge_frame(i)
    nx, ny = -ey, ex
    quad = Polygon([opts[i], opts[(i + 1) % n], inn[(i + 1) % n], inn[i]])
    mid = ((opts[i][0] + opts[(i + 1) % n][0]) / 2, (opts[i][1] + opts[(i + 1) % n][1]) / 2)
    mat = 'siding_wood' if ACCENT.contains(Point(mid)) else 'siding'
    s = -1000
    for (s0, s1, sill, head, kind) in sorted(EDGE_OPS[i]):
        wk[0] += 1
        nm = f'Wall_E{i}_{wk[0]}'
        wall_solid(nm, quad.intersection(band(i, s, s0)), PAD, mat)
        piece = quad.intersection(band(i, s0, s1))
        if sill > 0:
            add(nm + '_Sill', '1F', mat, piece, PAD, FL + sill)
        if kind == 'gable':
            TR = FL + 2600
            add(nm + '_Glass', '1F', 'glass', band(i, s0, s1, 110, 150), FL + sill, FL + head)
            add(nm + '_Transom', '1F', 'siding_wood', piece, FL + head, TR)
            nmull = 5
            FRAMES.append([a[0] + ex * s0, a[1] + ey * s0, a[0] + ex * s1, a[1] + ey * s1, nx, ny, FL + sill, FL + head, nmull, 0])
            for sub, top in tops(piece):
                clear = sub.intersection(halfplane(top[0], top[1], top[2] - 250 - TR - 60))
                add(nm + '_Rake', 'Roof', 'siding_wood', clear, sh(top, -250), top)
                add(nm + '_GlassUp', 'Roof', 'glass', clear.intersection(band(i, s0, s1, 110, 150)), TR, sh(top, -250))
                rest = sub.difference(clear.buffer(1))
                add(nm + '_PeakSolid', 'Roof', 'siding_wood', rest, TR, top)
                for m in range(nmull + 2):
                    c = s0 + (s1 - s0) * m / (nmull + 1)
                    add(nm + '_MullUp', 'Roof', 'frame', clear.intersection(band(i, c - 30, c + 30, 80, 180)), TR, sh(top, -250), minarea=300)
        else:
            wall_solid(nm + '_Head', piece, FL + head, mat)
            if kind in ('win', 'door'):
                add(nm + '_Glass', '1F', 'glass', band(i, s0, s1, 110, 150), FL + sill, FL + head)
                w = s1 - s0
                nmull = max(0, int(round(w / 1150.0)) - 1)
                FRAMES.append([a[0] + ex * s0, a[1] + ey * s0, a[0] + ex * s1, a[1] + ey * s1, nx, ny, FL + sill, FL + head, nmull, 1 if sill > 0 else 0])
            elif kind == 'wdoor':
                add(nm + '_Door', '1F', 'door_wood', band(i, s0 + 50, s1 - 50, 90, 150), FL, FL + head - 50)
                FRAMES.append([a[0] + ex * s0, a[1] + ey * s0, a[0] + ex * s1, a[1] + ey * s1, nx, ny, FL, FL + head, 0, 0])
            elif kind == 'sdoor':
                add(nm + '_Door', '1F', 'door_gray', band(i, s0 + 50, s1 - 50, 90, 150), FL, FL + head - 50)
                FRAMES.append([a[0] + ex * s0, a[1] + ey * s0, a[0] + ex * s1, a[1] + ey * s1, nx, ny, FL, FL + head, 0, 0])
            elif kind == 'gdoor':
                add(nm + '_GarageDoor', '1F', 'gdoor', band(i, s0, s1, 60, 120), FL - 20, FL + head)
                for h in range(1, 5):
                    add(nm + '_GDoorTrim', '1F', 'frame', band(i, s0, s1, 50, 62), FL - 20 + h * 450, FL - 20 + h * 450 + 18, minarea=300)
        s = s1
    wk[0] += 1
    wall_solid(f'Wall_E{i}_{wk[0]}', quad.intersection(band(i, s, Lg + 1000)), PAD, mat)

# ================================================================= 내벽·바닥·천장
def wall_poly(w):
    u0, d0, u1, d1, th = w
    return LineString([(u0, -d0), (u1, -d1)]).buffer(th / 2, cap_style=2, join_style=2).intersection(INNER)
IW = [wall_poly(w) for w in WALLS_INT]
allw = unary_union(IW)
dc = unary_union([Point(u, -d).buffer(w / 2, cap_style=3) for (u, d, w) in DOORS_INT])
add('IntWall', '1F', 'partition', allw.difference(dc), FL, EAVE)
add('IntWall_Lintel', '1F', 'partition', allw.intersection(dc), FL + 2150, EAVE)
for k in VAULT_WALLS:
    for sub, top in tops(IW[k]):
        if hi_of(sub, top) > EAVE + 60:
            add('IntWall_Upper', 'Roof', 'partition', sub.intersection(halfplane(top[0], top[1], top[2] - EAVE - 20)), EAVE, top)
add('Slab_House', '1F', 'stone_plinth', HEATED, PAD - 300, FL)
add('Slab_Garage', '1F', 'stone_plinth', GAR.difference(BAR), PAD - 300, FL - 20)
FMAT = {'garage': 'fl_garage', 'service': 'fl_service', 'circ': 'fl_public', 'public': 'fl_public', 'private': 'fl_private'}
for k, v in ROOMS.items():
    z0 = FL - 20 if v[4] == 'garage' else FL
    add('Floor_' + k, '1F', FMAT[v[4]], room_poly(k), z0, z0 + 15)
VAULT = unary_union([B(7500, 5600, 20800, 12600), HALL])
add('Ceiling', 'Roof', 'ceiling', HEATED.buffer(-EXT + 20, join_style=2).difference(VAULT), EAVE, EAVE + 30)
# 홀 목재 트러스 (노출)
for d in (7300, 9500, 11700, 13700):
    add('Truss_Tie', 'Roof', 'timber', B(7560, d - 70, 15240, d + 70), EAVE, EAVE + 200)
    for sub, top in tops(B(11330, d - 70, 11470, d + 70)):
        add('Truss_Post', 'Roof', 'timber', sub, EAVE + 200, top)
# 굴뚝 (거실 벽난로)
add('Chimney', '1F', 'stone_wall', B(17650, 5100, 18550, 5600), PAD, 7780)
add('Chimney_Cap', '1F', 'frame', B(17580, 5030, 18620, 5670), 7780, 7850)

# ================================================================= 대지
add('Hillside', 'Site', 'hill', HILL, -14000, NAT)
add('Pad_Lawn', 'Site', 'grass', PADP, -3000, PAD)
add('Terrace_Upper1', 'Site', 'grass', T1, -1000, 4650)
add('Terrace_Upper2', 'Site', 'grass', T2, -1000, 6450)
add('Road', 'Site', 'road', ROAD.intersection(BOX), sh(ROAD_PLANE, -2500), ROAD_PLANE)
add('StoneWall_Upper', 'Site', 'stone_wall', WALL_L1, -1000, 6450)
add('StoneWall_Lower', 'Site', 'stone_wall', WALL_L2, -1000, 4650)
add('RetainingWall_New', 'Site', 'stone_wall', RWALL.intersection(BOX), -3000, PAD + 120)
T = 30
COURT = PADP.intersection(B(-17500, -5000, -7000, 15300))
add('Court_Paving', 'Site', 'court', COURT, PAD, PAD + T)
add('Garage_Apron', 'Site', 'court', B(-8500, 6000, -7000, 12800), PAD, [0.0667, 0.0, FL - 20 + 0.0667 * 7000])
REAR = PADP.intersection(B(-7000, 0, XE, 5600)).difference(OUTLINE)
SERV = B(2800, 2600, 7600, 5600)
add('Rear_Gravel', 'Site', 'gravel', REAR.difference(SERV), PAD, PAD + T)
add('Service_Yard', 'Site', 'paving_stone', SERV, PAD, PAD + T + 5)
add('Jangdokdae', 'Site', 'stone_wall', B(5200, 1200, 7400, 2500), PAD, PAD + 250)
for k, (u, d) in enumerate([(5550, 1550), (6150, 1550), (6750, 1550), (5700, 2150), (6350, 2150), (6950, 2150)]):
    add(f'Jar_{k + 1}', 'Site', 'pot', Point(u, -d).buffer(230 if k % 2 else 190, resolution=3), PAD + 250, PAD + 250 + (560 if k % 2 else 420))
add('HeatPump', 'Site', 'metal', B(-3600, 4750, -2400, 5350), PAD + T, PAD + 950)
WALK = unary_union([B(-7300, 13200, 0, 15000), B(0, 12600, 7500, 15000)]).difference(OUTLINE)
add('Entry_Walk', 'Site', 'paving_stone', WALK, PAD, FL - 15)
add('Entry_Ramp', 'Site', 'paving_stone', B(-9300, 13400, -7300, 14800), PAD - 100, [0.0675, 0.0, PAD + 0.0675 * 9300])
add('Hall_Porch_Deck', 'Site', 'deck_wood', B(7500, 14600, 15300, 16800), PAD, FL - 15)
add('Court_Veranda_Deck', 'Site', 'deck_wood', B(15300, 12600, 26500, 14600), PAD, FL - 15)
add('Lawn_Ramp', 'Site', 'paving_stone', B(15300, 15200, 17100, 16600), PAD - 100, [-0.075, 0.0, FL - 15 + 0.075 * 15300])
POOL = B(18200, 15400, 22800, 17000)
add('Pool_Coping', 'Site', 'stone_dark', POOL.buffer(180, join_style=2).difference(POOL), PAD, PAD + 60)
add('Pool_Water', 'Site', 'water', POOL, PAD - 250, PAD + 20)
for nm, g, m, h in [('Bed_Lavender_Entry', B(-6500, 15060, 4000, 15650), 'lavender', 420), ('Bed_Lavender_Court', B(23100, 14700, 26300, 15500), 'lavender', 420),
                    ('Bed_Hydrangea', B(26800, 17250, 31800, 18000), 'hydrangea', 650), ('Bed_Rear', B(15500, 720, 26000, 1900), 'fern', 380),
                    ('Bed_Boxwood_Hall', B(7600, 16900, 15200, 17250), 'hedge', 450)]:
    add(nm, 'Site', m, g.intersection(PADP), PAD + T, PAD + T + h)
for k in range(3):
    add(f'VegBed_{k + 1}', 'Site', 'timber', B(27300 + k * 1700, 18500, 28500 + k * 1700, 19900), PAD + T, PAD + 300)
    add(f'VegBed_{k + 1}_Green', 'Site', 'veg', B(27380 + k * 1700, 18580, 28420 + k * 1700, 19820), PAD + 300, PAD + 520)
for k in range(13):
    add(f'StepStone_{k + 1}', 'Site', 'stone_dark', B(8200 + k * 1450, 3900, 8800 + k * 1450, 4400), PAD + T, PAD + T + 40)
add('Tsukubai', 'Site', 'stone_wall', Point(21200, -3300).buffer(330, resolution=3), PAD + T, PAD + 480)
for k, u in enumerate((18100, 23700, 3750)):      # 빗물받이 사슬 + 자갈 받침
    d = 14700 if k < 2 else 15100
    add(f'RainChain_{k + 1}_Basin', 'Site', 'stone_dark', B(u - 350, d - 350, u + 350, d + 350), PAD + T, PAD + 110)
    z = 5080.0
    j = 0
    while z - 160 > PAD + 250:
        j += 1
        add(f'RainChain_{k + 1}_Cup{j}', 'Site', 'copper', Point(u, -d).buffer(38, resolution=2), z - 110, z, minarea=100)
        z -= 300
TREES = [(-15900, 15900, 1700, 5600, 'zelkova'), (-5600, 3300, 1500, 5200, 'pine'), (24300, 18400, 1300, 4300, 'maple'), (33300, 15500, 2000, 6200, 'zelkova'),
         (5700, 16600, 1000, 3400, 'maple'), (-3000, 16100, 1100, 3600, 'zelkova'), (36500, 6500, 1800, 5600, 'zelkova'), (12000, 2600, 1300, 4300, 'maple')]
for k, (u, d, r, h, kind) in enumerate(TREES):
    add(f'Tree_{k + 1}_Trunk', 'Site', 'trunk', Point(u, -d).buffer(110 + r * 0.03, resolution=2), PAD, PAD + h * 0.45)
    add(f'Tree_{k + 1}_Crown_{kind}', 'Site', 'crown_' + kind, Point(u, -d).buffer(r, resolution=3), PAD + h * 0.38, PAD + h)
for k, u in enumerate((16200, 19000, 22000, 25200)):
    for j in range(6):
        aa = 2 * math.pi * j / 6
        add(f'Bamboo_{k + 1}_{j + 1}', 'Site', 'bamboo', Point(u + 300 * math.cos(aa), -1250 + 220 * math.sin(aa)).buffer(26, resolution=2), PAD + T, PAD + 2900 + 200 * (j % 3), minarea=100)
    add(f'Bamboo_{k + 1}_Crown_bamboo', 'Site', 'crown_bamboo', Point(u, -1250).buffer(750, resolution=3), PAD + 1900, PAD + 3600)
# 뒷집 (위치·높이 추정)
NB = box(17500, 5200, 27500, 11200)
add('Neighbor_Walls', 'Site', 'neighbor', NB, 6450, 9300)
add('Neighbor_Roof_N', 'Site', 'neighbor_roof', box(17100, 8200, 27900, 11600), [0, -0.45, 9300 + 0.45 * 11200], [0, -0.45, 9500 + 0.45 * 11200])
add('Neighbor_Roof_S', 'Site', 'neighbor_roof', box(17100, 4800, 27900, 8200), [0, 0.45, 9300 - 0.45 * 5200], [0, 0.45, 9500 - 0.45 * 5200])
for nm, g in [('Neighbor_Gable_W', box(17500, 5200, 17700, 11200)), ('Neighbor_Gable_E', box(27300, 5200, 27500, 11200))]:
    add(nm + '_N', 'Site', 'neighbor', g.intersection(box(0, 8200, 1e5, 1e5)), 9300, [0, -0.45, 9300 + 0.45 * 11200])
    add(nm + '_S', 'Site', 'neighbor', g.intersection(box(0, 0, 1e5, 8200)), 9300, [0, 0.45, 9300 - 0.45 * 5200])

# ================================================================= 가구·설비
def fur(name, g, z0, z1, mat='furniture', grp='Furniture'):
    add(name, grp, mat, g, z0, z1)
F = FL + 15
fur('Kitchen_Counter_N', B(7700, 5850, 12300, 6480), F, FL + 900, 'cabinet'); fur('Kitchen_Counter_N_Top', B(7700, 5850, 12300, 6500), FL + 900, FL + 940, 'counter')
fur('Kitchen_Tall', B(7560, 6500, 8180, 7350), F, FL + 2250, 'cabinet_wood')
fur('Kitchen_Island', B(9200, 7600, 12600, 8750), F, FL + 900, 'cabinet_wood'); fur('Kitchen_Island_Top', B(9150, 7550, 12650, 8800), FL + 900, FL + 940, 'counter')
fur('Scullery_Counter_N', B(4600, 5850, 7380, 6450), F, FL + 900, 'cabinet'); fur('Scullery_Counter_N_Top', B(4600, 5850, 7380, 6470), FL + 900, FL + 940, 'counter')
fur('Scullery_Counter_S', B(4300, 8360, 7380, 8960), F, FL + 900, 'cabinet'); fur('Scullery_Counter_S_Top', B(4300, 8340, 7380, 8960), FL + 900, FL + 940, 'counter')
fur('Scullery_Fridges', B(3060, 8300, 4300, 8960), F, FL + 2000, 'metal')
fur('Laundry', B(300, 5850, 1750, 6450), F, FL + 900, 'porcelain')
fur('Shoe_Cabinet', B(125, 9080, 560, 12350), F, FL + 2250, 'cabinet_wood')
fur('Foyer_Bench', B(3350, 11850, 4290, 12350), F, FL + 450, 'timber')
fur('Powder_WC', B(6850, 10900, 7440, 11350), F, FL + 430, 'porcelain'); fur('Powder_Sink', B(4500, 11800, 5400, 12350), FL + 700, FL + 850, 'porcelain')
fur('Dining_Table', B(9200, 11425, 13600, 12575), FL + 700, FL + 760, 'timber')
for (u, d) in [(9500, 11600), (13300, 11600), (9500, 12400), (13300, 12400)]:
    fur('Dining_Table_Leg', B(u - 50, d - 50, u + 50, d + 50), F, FL + 700, 'timber')
fur('Sofa', B(16300, 9300, 19300, 10250), F, FL + 430, 'sofa'); fur('Sofa_Back', B(16300, 10050, 19300, 10250), FL + 430, FL + 850, 'sofa')
fur('Sofa_Side', B(19300, 7500, 20200, 10250), F, FL + 430, 'sofa'); fur('Sofa_Side_Back', B(20000, 7500, 20200, 10250), FL + 430, FL + 850, 'sofa')
fur('Coffee_Table', B(17000, 7800, 18400, 8600), FL + 300, FL + 380, 'timber')
fur('Fireplace', B(17500, 5850, 18700, 6300), F, FL + 2700, 'stone_wall'); fur('Fireplace_Glass', B(17750, 6290, 18450, 6320), FL + 350, FL + 1050, 'frame')
fur('Bed2', B(21100, 9700, 22700, 11800), F, FL + 500, 'bed'); fur('Desk2', B(23400, 7400, 24300, 8900), FL + 700, FL + 740, 'timber')
fur('Vanity2', B(24520, 7270, 25300, 7830), F, FL + 850, 'cabinet'); fur('WC2', B(25850, 9250, 26440, 9700), F, FL + 430, 'porcelain')
fur('Closet_Dress', B(28400, 7400, 31750, 7940), F, FL + 2250, 'cabinet_wood'); fur('Closet_Pass', B(26560, 8060, 27160, 11540), F, FL + 2250, 'cabinet_wood')
fur('MBath_Vanity', B(28900, 8060, 30700, 8620), F, FL + 850, 'cabinet'); fur('MBath_Tub', B(30950, 8300, 31750, 10000), F, FL + 560, 'porcelain')
fur('MBath_WC', B(31150, 10850, 31750, 11400), F, FL + 430, 'porcelain'); fur('MBath_ShowerGlass', B(28800, 10200, 30300, 10240), F, FL + 2100, 'glass')
fur('Bed_Master', B(28150, 11700, 30250, 13900), F, FL + 520, 'bed'); fur('Bed_Master_Head', B(28150, 11660, 30250, 11760), FL + 520, FL + 1150, 'timber')
for k, d0 in enumerate((6350, 10500)):
    fur(f'Car_{k + 1}_Body', B(-6300, d0, -1500, d0 + 1900), FL + 250, FL + 950, 'car', '1F'); fur(f'Car_{k + 1}_Cabin', B(-5300, d0 + 90, -2500, d0 + 1810), FL + 950, FL + 1600, 'car_glass', '1F')
for k, d0 in enumerate((10400, 12900)):
    fur(f'GuestCar_{k + 1}_Body', B(-17200, d0, -12400, d0 + 1900), PAD + 280, PAD + 980, 'car2' if k else 'car', 'Site'); fur(f'GuestCar_{k + 1}_Cabin', B(-16200, d0 + 90, -13400, d0 + 1810), PAD + 980, PAD + 1630, 'car_glass', 'Site')
fur('Outdoor_Table', B(9600, 15200, 13200, 16300), FL + 690, FL + 750, 'timber', 'Site')
CH = []
for i in range(6):
    x = 9200 + 4400 / 6 * (i + 0.5)
    CH += [[x, -11095, 0, FL + 15, 'Furniture'], [x, -12905, 180, FL + 15, 'Furniture']]
CH += [[8870, -12000, 90, FL + 15, 'Furniture'], [13930, -12000, 270, FL + 15, 'Furniture']]
for i in range(5):
    x = 9600 + 3600 / 5 * (i + 0.5)
    CH += [[x, -14870, 0, FL - 15, 'Site'], [x, -16630, 180, FL - 15, 'Site']]
for k in range(4):
    CH.append([9700 + k * 800, -9150, 0, FL + 15, 'Furniture'])   # 아일랜드 스툴

FENCE = [{'p': [(-17350, -8200), (-17350, -16650), (2450, -16650), (4680, -15740), (7000, -17140), (14450, -20050), (34350, -20050), (34350, -11400)], 'z': PAD + 120}]
SPEC = {'roofs': ROOFSPEC, 'frames': [[round(v, 1) for v in f] for f in FRAMES], 'fences': FENCE, 'chairs': CH}
LABELS = [{'t': k, 'x': round(room_poly(k).centroid.x), 'y': round(room_poly(k).centroid.y), 'z': FL + 100} for k in ROOMS]

if __name__ == '__main__':
    core = len(P)
    rows = detail.gen_details(SPEC)
    allp = list(P)
    for r in rows:
        f = r[3]
        allp.append({'n': r[0], 'g': r[1], 'm': r[2], 'p': [[round(f[2 * i], 1), round(f[2 * i + 1], 1)] for i in range(len(f) // 2)],
                     'zb': r[4] if isinstance(r[4], list) else [0, 0, r[4]], 'zt': r[5] if isinstance(r[5], list) else [0, 0, r[5]]})
    json.dump({'prisms': allp, 'labels': LABELS}, open('prisms.json', 'w'), ensure_ascii=False)
    json.dump({'core': P, 'spec': SPEC, 'labels': LABELS}, open('core.json', 'w'), ensure_ascii=False)
    from collections import Counter
    print('core', core, 'detail', len(rows), Counter(p['g'] for p in allp))
    print('roof regions', len(REG), 'frames', len(FRAMES), 'mats', sorted(set(p['m'] for p in allp)))

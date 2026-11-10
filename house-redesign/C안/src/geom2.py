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
EAVE_G, TAN_G = EAVE + 250, 0.839        # 차고(다락) 지붕: 다락 바닥에서 바로 올라가는 10/12 물매
VOLP = {}
def vol(name, fp, axis, eave=EAVE, tan=TAN):
    x0, y0, x1, y1 = fp.bounds
    VOLP[name] = (axis, x0, y0, x1, y1, eave, tan)
    if axis == 'u':
        yr = (y0 + y1) / 2
        PLN.append((box(x0 - OVG, yr, x1 + OVG, y1 + OVE), [0.0, -tan, eave + tan * y1], name))
        PLN.append((box(x0 - OVG, y0 - OVE, x1 + OVG, yr), [0.0, tan, eave - tan * y0], name))
    else:
        xr = (x0 + x1) / 2
        PLN.append((box(x0 - OVE, y0 - OVG, xr, y1 + OVG), [tan, 0.0, eave - tan * x0], name))
        PLN.append((box(xr, y0 - OVG, x1 + OVE, y1 + OVG), [-tan, 0.0, eave + tan * x1], name))
vol('bar', BAR, 'u'); vol('hall', HALL, 'd'); vol('mast', MAST, 'd'); vol('gar', GAR, 'u', EAVE_G, TAN_G)
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
DSP = []
for k, (poly, pl, nm) in enumerate(REG):
    axis, x0, y0, x1, y1, ev, tn = VOLP[nm]
    cs = list(poly.exterior.coords)
    for i in range(len(cs) - 1):
        (ax, ay), (bx, by) = cs[i], cs[i + 1]
        Lg = math.dist((ax, ay), (bx, by))
        if Lg < 400: continue
        ex, ey = (bx - ax) / Lg, (by - ay) / Lg
        ox, oy = ey, -ex                                     # CCW 다각형의 바깥쪽
        def strip(a0, a1, s0=0.0, s1=None):
            s1 = Lg if s1 is None else s1
            return Polygon([(ax + ex * s0 + ox * a0, ay + ey * s0 + oy * a0), (ax + ex * s1 + ox * a0, ay + ey * s1 + oy * a0),
                            (ax + ex * s1 + ox * a1, ay + ey * s1 + oy * a1), (ax + ex * s0 + ox * a1, ay + ey * s0 + oy * a1)])
        if axis == 'u':
            is_eave = abs(ay - by) < 1 and (abs(ay - (y1 + OVE)) < 2 or abs(ay - (y0 - OVE)) < 2)
            is_ridge = abs(ay - by) < 1 and abs(ay - (y0 + y1) / 2) < 2
        else:
            is_eave = abs(ax - bx) < 1 and (abs(ax - (x0 - OVE)) < 2 or abs(ax - (x1 + OVE)) < 2)
            is_ridge = abs(ax - bx) < 1 and abs(ax - (x0 + x1) / 2) < 2
        if is_eave:
            zg = zat(pl, ax, ay)
            add('Gutter', 'Roof', 'gutter', strip(0, 125), zg - 15, zg + 95)
            north = axis == 'u' and oy > 0.5
            if north and Lg > 2500:
                for s in ([450, Lg - 450] if Lg > 6000 else [Lg / 2]):
                    px, py = ax + ex * s, ay + ey * s
                    add('Downspout_Arm', 'Roof', 'gutter', Polygon([(px - 40, py - OVE + 20), (px + 40, py - OVE + 20), (px + 40, py + 60), (px - 40, py + 60)]), zg - 100, zg - 20)
                    add('Downspout', 'Roof', 'gutter', Polygon([(px - 40, py - OVE + 20), (px + 40, py - OVE + 20), (px + 40, py - OVE + 100), (px - 40, py - OVE + 100)]), PAD + 60, zg - 20)
        if is_ridge:
            add('RidgeCap', 'Roof', 'gutter', strip(-130, 0).intersection(poly), sh(pl, RT), sh(pl, RT + 48), minarea=300)
    over = poly.difference(OUTLINE.buffer(-5))
    add(f'Soffit_{k}', 'Roof', 'soffit', over, sh(pl, -20), pl)
VAULT_IN = unary_union([B(7560, 5850, 20740, 12350), B(7560, 12350, 15240, 14350), B(-6750, 5850, -125, 12950)])
for k, (poly, pl, nm) in enumerate(REG):
    add(f'CeilWood_{k}', 'Roof', 'ceil_wood', poly.intersection(VAULT_IN), sh(pl, -20), pl)
# 포치 덧지붕
for poly, dw, nm in PORCH:
    pl = porch_plane(dw)
    add(f'Porch_Roof_{nm}', 'Roof', 'aluzinc', poly, pl, sh(pl, 120))
    add(f'Porch_Soffit_{nm}', 'Roof', 'soffit', poly, sh(pl, -20), pl)
    xa, ya, xb, yb = poly.bounds
    add(f'Porch_Gutter_{nm}', 'Roof', 'gutter', box(xa, ya - 120, xb, ya), zat(pl, 0, ya) - 15, zat(pl, 0, ya) + 95)
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
                for q in range(4):
                    c0 = s0 + 250 + q * (s1 - s0 - 500) / 4 + 60
                    add(nm + '_GDoorLite', '1F', 'glass', band(i, c0, c0 + (s1 - s0 - 500) / 4 - 120, 40, 58), FL + 1760, FL + 2120, minarea=300)
                for h in range(1, 4):
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
add('Open_Beam_HallLiving', 'Roof', 'timber', B(15220, 5850, 15380, 12350), EAVE - 80, EAVE + 220)
# 굴뚝 (거실 벽난로)
add('Chimney', '1F', 'stone_wall', B(17650, 5100, 18550, 5600), PAD, 7780)
add('Chimney_Cap', '1F', 'frame', B(17580, 5030, 18620, 5670), 7780, 7850)

# ================================================================= 차고 위 다락 (개인 공간)
AT_FL = EAVE + 250
for sub, top in tops(B(-250, 5600, 0, 13200)):                       # 본채 지붕 위로 드러나는 차고 동측 박공벽
    add('Attic_Gable_E', 'Roof', 'siding_wood', sub.intersection(halfplane(top[0], top[1], top[2] - EAVE - 25)), EAVE, top)
WELL = B(-1125, 8700, -125, 12700)
add('Attic_Slab', '1F', 'concrete', B(-6750, 5850, -125, 12950).difference(WELL), EAVE, AT_FL)
add('Attic_Floor', '1F', 'fl_private', B(-6750, 5850, -125, 12950).difference(WELL), AT_FL, AT_FL + 15)
for k in range(16):
    d1 = 12700 - 250 * k
    add(f'Attic_Stair_{k + 1}', '1F', 'timber', B(-1125, d1 - 250, -175, d1), FL - 20, FL - 20 + (AT_FL - FL + 20) / 17 * (k + 1))
for d_ in range(8700, 12701, 800):                                    # 계단 난간: 기둥 + 손잡이 + 중간대
    add('Attic_Rail_Post', '1F', 'frame', B(-1165, d_ - 20, -1125, d_ + 20), AT_FL, AT_FL + 1000, minarea=100)
for u_ in (-765, -365):
    add('Attic_Rail_Post', '1F', 'frame', B(u_ - 20, 12700, u_ + 20, 12740), AT_FL, AT_FL + 1000, minarea=100)
for (z0_, z1_) in [(960, 1010), (480, 510)]:
    add('Attic_Rail_Bar', '1F', 'frame' if z0_ < 900 else 'timber', B(-1170, 8680, -1120, 12740), AT_FL + z0_, AT_FL + z1_, minarea=100)
    add('Attic_Rail_Bar', '1F', 'frame' if z0_ < 900 else 'timber', B(-1170, 12695, -125, 12745), AT_FL + z0_, AT_FL + z1_, minarea=100)
GPN = [0.0, -TAN_G, EAVE_G + TAN_G * (-5600)]; GPS = [0.0, TAN_G, EAVE_G + TAN_G * 13200]
for k, u0 in enumerate((-5600, -3200)):                                # 남측 지붕 천창 2개
    add(f'Skylight_{k + 1}_Frame', 'Roof', 'frame', B(u0, 10700, u0 + 900, 12100), sh(GPS, RT), sh(GPS, RT + 70))
    add(f'Skylight_{k + 1}_Glass', 'Roof', 'glass', B(u0 + 70, 10770, u0 + 830, 12030), sh(GPS, RT + 70), sh(GPS, RT + 90))
AF = AT_FL + 15
add('Attic_Desk_Top', 'Furniture', 'timber', B(-6450, 8250, -5700, 10550), AF + 720, AF + 760)
for (u_, d_) in [(-6400, 8300), (-5800, 8300), (-6400, 10450), (-5800, 10450)]:
    add('Attic_Desk_Leg', 'Furniture', 'frame', B(u_, d_, u_ + 50, d_ + 50), AF, AF + 720, minarea=100)
add('Attic_Desk_Lamp', 'Furniture', 'lamp', B(-6350, 8400, -6230, 8520), AF + 760, AF + 1100, minarea=100)
add('Attic_Desk_Books', 'Furniture', 'cabinet_wood', B(-6400, 10000, -6150, 10450), AF + 760, AF + 960, minarea=100)
add('Attic_Shelf_N', 'Furniture', 'cabinet_wood', B(-5400, 6250, -1500, 6650), AF, AF + 620)
add('Attic_Shelf_S', 'Furniture', 'cabinet_wood', B(-5400, 12150, -1500, 12550), AF, AF + 620)
for k_, d_ in enumerate((7150, 11330)):
    add(f'Attic_Speaker_{k_}', 'Furniture', 'frame', B(-6500, d_, -6150, d_ + 320), AF, AF + 1000)
add('Attic_AudioRack', 'Furniture', 'cabinet_wood', B(-3300, 6750, -1900, 7250), AF, AF + 560)
add('Attic_Turntable', 'Furniture', 'frame', B(-2900, 6820, -2400, 7180), AF + 560, AF + 650)
add('Attic_Amp', 'Furniture', 'metal', B(-3250, 6830, -2950, 7170), AF + 560, AF + 700)
add('Attic_Lounge_Seat', 'Furniture', 'sofa', B(-3300, 8950, -2500, 9850), AF, AF + 400)
add('Attic_Lounge_Back', 'Furniture', 'sofa', B(-2650, 8950, -2500, 9850), AF + 400, AF + 900)
add('Attic_Ottoman', 'Furniture', 'sofa', B(-4250, 9150, -3750, 9650), AF, AF + 360)
add('Attic_Rug', 'Furniture', 'bed', B(-5300, 8300, -2000, 10500), AF, AF + 12)
# 외부 벽등
for (u, d, ox, oy) in [(-7000, 9400, -1, 0), (-7000, 5900, -1, 0), (-7000, 12900, -1, 0), (1150, 12600, 0, -1), (3450, 12600, 0, -1), (-1000 + 700, 13200, 0, -1),
                       (7900, 14600, 0, -1), (14900, 14600, 0, -1), (15650, 12600, 0, -1), (20650, 12600, 0, -1), (3850, 5600, 0, 1)]:
    x, y = u + ox * 45, -d + oy * 45
    add('WallLamp', '1F', 'lamp', box(x - 60, y - 60, x + 60, y + 60) if True else None, FL + 2000, FL + 2220, minarea=300)

# 다락 서측 박공벽: 지붕선을 따르는 큰 창(창대 450, 가운데 높이 2000) + 꼭대기 원형 스테인드글라스(지름 500)
RW_C, RW_Z, RW_R = 9400, AT_FL + 2500, 250
GW0, GW1, GW_S, GW_H, GW_RK = 6600, 12200, AT_FL + 450, AT_FL + 2000, 300
GA, GB = 5600 + (GW_H - AT_FL + GW_RK) / TAN_G, 13200 - (GW_H - AT_FL + GW_RK) / TAN_G
_old = list(P); P[:] = []
for p in _old:
    xs_ = [q[0] for q in p['p']]
    if not (p['g'] == 'Roof' and p['m'] == 'siding_wood' and min(xs_) >= -7001 and max(xs_) <= -6749):
        P.append(p); continue
    poly = Polygon(p['p']); pl = p['zt']
    add(p['n'], p['g'], p['m'], poly.difference(B(-7100, GW0, -6700, GW1)), p['zb'], pl)
    win = poly.intersection(B(-7100, GW0, -6700, GW1))
    add(p['n'] + '_Sill', p['g'], p['m'], win, p['zb'], GW_S)
    for (d0, d1) in ((GW0, GA), (GB, GW1)):
        add(p['n'] + '_Rake', p['g'], p['m'], win.intersection(B(-7100, d0, -6700, d1)), sh(pl, -GW_RK), pl)
    mid = win.intersection(B(-7100, GA, -6700, GB))
    add(p['n'] + '_Transom', p['g'], p['m'], mid.difference(B(-7100, RW_C - RW_R, -6700, RW_C + RW_R)), GW_H, pl)
    for k in range(10):
        d0 = RW_C - RW_R + 50 * k; half = math.sqrt(max(RW_R ** 2 - (d0 + 25 - RW_C) ** 2, 0)); cut = mid.intersection(B(-7100, d0, -6700, d0 + 50))
        add(p['n'] + f'_Under{k}', p['g'], p['m'], cut, GW_H, RW_Z - half, minarea=300)
        add(p['n'] + f'_Over{k}', p['g'], p['m'], cut, RW_Z + half, pl, minarea=300)
for (d0, d1, zt_) in ((GW0, GA, sh(GPN, -GW_RK)), (GA, 9400, GW_H), (9400, GB, GW_H), (GB, GW1, sh(GPS, -GW_RK))):
    add('Attic_BigWindow_Glass', 'Roof', 'glass', B(-6900, d0, -6860, d1), GW_S, zt_)
add('Attic_BigWindow_SillBar', 'Roof', 'frame', B(-6960, GW0, -6800, GW1), GW_S - 50, GW_S + 20, minarea=300)
add('Attic_BigWindow_HeadBar', 'Roof', 'frame', B(-6960, GA, -6800, GB), GW_H - 20, GW_H + 50, minarea=300)
for k in range(7):
    dm = GW0 + (GW1 - GW0) * k / 6
    ztm = GW_H if GA <= dm <= GB else sh(GPN if dm < 9400 else GPS, -GW_RK)
    add(f'Attic_BigWindow_Mullion{k}', 'Roof', 'frame', B(-6950, max(dm - 30, GW0), -6810, min(dm + 30, GW1)), GW_S, ztm, minarea=300)

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
# 다용도실: 타워형 세탁기·건조기, 개수대, 키 큰 수납장, 벤치
fur('Util_Tower_Washer', B(200, 5870, 820, 6520), F, FL + 870, 'porcelain'); fur('Util_Tower_Band', B(200, 5870, 820, 6525), FL + 870, FL + 1010, 'metal')
fur('Util_Tower_Dryer', B(200, 5870, 820, 6520), FL + 1010, FL + 1890, 'porcelain')
fur('Util_Sink_Cabinet', B(900, 5850, 2250, 6450), F, FL + 860, 'cabinet'); fur('Util_Sink_Top', B(900, 5850, 2250, 6470), FL + 860, FL + 900, 'counter')
fur('Util_Sink_Basin', B(1150, 5950, 1750, 6350), FL + 900, FL + 915, 'metal')
fur('Util_Tall_Storage', B(2330, 5850, 2900, 6420), F, FL + 2150, 'cabinet_wood')
fur('Util_Bench', B(200, 8450, 1150, 8900), F, FL + 450, 'timber'); fur('Util_Hooks_Rail', B(200, 8880, 1150, 8950), FL + 1600, FL + 1680, 'timber')
# 보조주방: 개수대, 쿡탑, 상부장, 선반
fur('Scullery_Sink_Basin', B(5100, 5950, 5900, 6350), FL + 940, FL + 955, 'metal'); fur('Scullery_Cooktop', B(6300, 5950, 7000, 6380), FL + 940, FL + 955, 'frame')
fur('Scullery_Upper_S', B(4300, 8610, 7380, 8960), FL + 1500, FL + 2250, 'cabinet'); fur('Scullery_Hood', B(6250, 5850, 7050, 6250), FL + 1650, FL + 1800, 'metal')
fur('Scullery_Shelf_W', B(3060, 5900, 3300, 6700), FL + 1300, FL + 1340, 'timber'); fur('Scullery_Shelf_W2', B(3060, 5900, 3300, 6700), FL + 1650, FL + 1690, 'timber')
fur('Shoe_Cabinet', B(125, 9080, 560, 12350), F, FL + 2250, 'cabinet_wood')
fur('Foyer_Bench', B(3350, 11850, 4290, 12350), F, FL + 450, 'timber')
fur('Powder_WC', B(6850, 10900, 7440, 11350), F, FL + 430, 'porcelain'); fur('Powder_Sink', B(4500, 11800, 5400, 12350), FL + 700, FL + 850, 'porcelain')
fur('Dining_Table', B(8950, 11425, 12650, 12575), FL + 700, FL + 760, 'timber')          # 12인: 긴 변 5석씩 + 양 끝
for (u, d) in [(9250, 11600), (12350, 11600), (9250, 12400), (12350, 12400)]:
    fur('Dining_Table_Leg', B(u - 50, d - 50, u + 50, d + 50), F, FL + 700, 'timber')
fur('Sofa', B(16300, 9300, 19300, 10250), F, FL + 430, 'sofa'); fur('Sofa_Back', B(16300, 10050, 19300, 10250), FL + 430, FL + 850, 'sofa')
fur('Sofa_Side', B(19300, 7500, 20200, 10250), F, FL + 430, 'sofa'); fur('Sofa_Side_Back', B(20000, 7500, 20200, 10250), FL + 430, FL + 850, 'sofa')
fur('Coffee_Table', B(17000, 7800, 18400, 8600), FL + 300, FL + 380, 'timber')
fur('Living_Rug', B(14900, 7100, 20300, 10400), F, F + 12, 'bed')
for k_, d_ in enumerate((7350, 8950)):                                     # 넓어진 서쪽에 안락의자 한 쌍
    fur(f'Living_Armchair_{k_}_Seat', B(14950, d_, 15800, d_ + 850), F, FL + 420, 'sofa'); fur(f'Living_Armchair_{k_}_Back', B(14950, d_, 15130, d_ + 850), FL + 420, FL + 860, 'sofa')
fur('Living_SideTable', B(15150, 8320, 15550, 8830), FL + 480, FL + 520, 'timber')
fur('Fireplace', B(17500, 5850, 18700, 6300), F, FL + 2700, 'stone_wall'); fur('Fireplace_Glass', B(17750, 6290, 18450, 6320), FL + 350, FL + 1050, 'frame')
# 침실2: 창밖을 향한 붙박이 책상 + 서쪽 벽의 벽장침대(펼친 모습)
fur('Bed2_Desk_Top', B(21250, 11780, 24050, 12350), FL + 720, FL + 760, 'timber')
for u_ in (21250, 22630, 24010):
    fur('Bed2_Desk_Panel', B(u_, 11800, u_ + 40, 12350), F, FL + 720, 'cabinet_wood')
fur('Bed2_Desk_Drawers', B(23400, 11820, 24010, 12350), FL + 250, FL + 720, 'cabinet_wood')
fur('Bed2_Desk_Lamp', B(21400, 12150, 21500, 12250), FL + 760, FL + 1100, 'lamp')
fur('Bed2_Wallbed_Cabinet_Side1', B(20860, 8250, 21320, 8300), F, FL + 2250, 'cabinet_wood'); fur('Bed2_Wallbed_Cabinet_Side2', B(20860, 9900, 21320, 9950), F, FL + 2250, 'cabinet_wood')
fur('Bed2_Wallbed_Cabinet_Top', B(20860, 8250, 21320, 9950), FL + 2200, FL + 2250, 'cabinet_wood'); fur('Bed2_Wallbed_Cabinet_Back', B(20860, 8300, 20900, 9900), F, FL + 2200, 'cabinet')
fur('Bed2_Wallbed_Platform', B(20950, 8320, 23050, 9880), FL + 280, FL + 330, 'cabinet_wood'); fur('Bed2_Wallbed_Mattress', B(21000, 8350, 23000, 9850), FL + 330, FL + 530, 'bed')
fur('Bed2_Wallbed_Pillow', B(21050, 8500, 21450, 9700), FL + 530, FL + 640, 'porcelain'); fur('Bed2_Wallbed_Throw', B(22300, 8340, 22800, 9860), FL + 530, FL + 545, 'furniture')
for d_ in (8340, 9810):
    fur('Bed2_Wallbed_Leg', B(22980, d_, 23040, d_ + 50), F, FL + 280, 'frame')
fur('Bed2_Shelf_N', B(20860, 7330, 21200, 8250), F, FL + 2250, 'cabinet_wood'); fur('Bed2_Shelf_S', B(20860, 9950, 21200, 11200), F, FL + 2250, 'cabinet_wood')
fur('Vanity2', B(24520, 7270, 25300, 7830), F, FL + 850, 'cabinet'); fur('WC2', B(25850, 9250, 26440, 9700), F, FL + 430, 'porcelain')
fur('Closet_Dress', B(28400, 7400, 31750, 7940), F, FL + 2250, 'cabinet_wood'); fur('Closet_Pass', B(26560, 8060, 27160, 11540), F, FL + 2250, 'cabinet_wood')
fur('MBath_Vanity', B(28900, 8060, 30700, 8620), F, FL + 850, 'cabinet'); fur('MBath_Tub', B(30950, 8300, 31750, 10000), F, FL + 560, 'porcelain')
fur('MBath_WC', B(31150, 10850, 31750, 11400), F, FL + 430, 'porcelain'); fur('MBath_ShowerGlass', B(28800, 10200, 30300, 10240), F, FL + 2100, 'glass')
fur('Master_Headwall', B(27950, 11660, 30950, 11720), F, FL + 1150, 'cabinet')
for k_, (u0_, rise_) in enumerate(((28300, 380), (29420, 140))):            # 모션베드 2개를 붙여서 (머리판 각도는 따로)
    u1_ = u0_ + 1100
    fur(f'MotionBed_{k_}_Base', B(u0_, 11760, u1_, 13810), F, FL + 300, 'cabinet')
    fur(f'MotionBed_{k_}_MattFoot', B(u0_ + 30, 12650, u1_ - 30, 13790), FL + 300, FL + 550, 'bed')
    sl_ = rise_ / 870.0                                                      # 머리 쪽(북)으로 갈수록 올라감: z = sl*(d0 - d) = sl*y + sl*d0
    pb_ = [0.0, sl_, FL + 300 + sl_ * 12650]; pt_ = [0.0, sl_, FL + 550 + sl_ * 12650]
    add(f'MotionBed_{k_}_MattHead', 'Furniture', 'bed', B(u0_ + 30, 11780, u1_ - 30, 12650), pb_, pt_)
    add(f'MotionBed_{k_}_Wedge', 'Furniture', 'cabinet', B(u0_ + 60, 11780, u1_ - 60, 12650), FL + 300, pb_)
    add(f'MotionBed_{k_}_Pillow', 'Furniture', 'porcelain', B(u0_ + 220, 11850, u1_ - 220, 12250), pt_, [0.0, sl_, pt_[2] + 120])
    add(f'MotionBed_{k_}_Cushion', 'Furniture', 'fern', B(u0_ + 300, 12280, u1_ - 300, 12560), pt_, [0.0, sl_, pt_[2] + 110])
    fur(f'MotionBed_{k_}_Throw', B(u0_ + 20, 13150, u1_ - 20, 13600), FL + 550, FL + 565, 'furniture')
    add(f'Master_Sconce_{k_}', 'Furniture', 'lamp', B(u0_ + 500, 11720, u0_ + 600, 11790), FL + 1250, FL + 1450, minarea=100)
fur('Master_Nightstand_W', B(27950, 11720, 28280, 12200), F, FL + 480, 'cabinet'); fur('Master_Nightstand_E', B(30540, 11720, 30990, 12200), F, FL + 480, 'cabinet')
for k_, u0_ in enumerate((27750, 30000)):                                  # 남쪽 창가 리클라이너 2개 (창을 향함)
    fur(f'Recliner_{k_}_Seat', B(u0_, 15250, u0_ + 800, 16050), F, FL + 430, 'sofa')
    add(f'Recliner_{k_}_Back', 'Furniture', 'sofa', B(u0_ + 60, 14850, u0_ + 740, 15300), FL + 250, [0.0, 1.45, FL + 430 + 1.45 * 15300])
    fur(f'Recliner_{k_}_ArmL', B(u0_, 15150, u0_ + 110, 16050), FL + 430, FL + 600, 'sofa'); fur(f'Recliner_{k_}_ArmR', B(u0_ + 690, 15150, u0_ + 800, 16050), FL + 430, FL + 600, 'sofa')
    fur(f'Recliner_{k_}_Foot', B(u0_ + 80, 16080, u0_ + 720, 16520), FL + 240, FL + 400, 'sofa')
fur('TeaTable_Top', Point(29275, -15700).buffer(300, resolution=4), FL + 500, FL + 530, 'timber'); fur('TeaTable_Leg', Point(29275, -15700).buffer(45, resolution=3), F, FL + 500, 'frame')
fur('Master_Rug', B(27600, 14700, 31000, 16600), F, F + 12, 'bed')
for k, d0 in enumerate((6350, 10500)):
    fur(f'Car_{k + 1}_Body', B(-6300, d0, -1500, d0 + 1900), FL + 250, FL + 950, 'car', '1F'); fur(f'Car_{k + 1}_Cabin', B(-5300, d0 + 90, -2500, d0 + 1810), FL + 950, FL + 1600, 'car_glass', '1F')
for k, d0 in enumerate((10400, 12900)):
    fur(f'GuestCar_{k + 1}_Body', B(-17200, d0, -12400, d0 + 1900), PAD + 280, PAD + 980, 'car2' if k else 'car', 'Site'); fur(f'GuestCar_{k + 1}_Cabin', B(-16200, d0 + 90, -13400, d0 + 1810), PAD + 980, PAD + 1630, 'car_glass', 'Site')
fur('Outdoor_Table', B(9600, 15200, 13200, 16300), FL + 690, FL + 750, 'timber', 'Site')
# ------------------------------------------------------------------ 천장 설비 (시스템 에어컨 · 전열교환기)
def cassette(nm, u, d):                                                     # 평천장: 4방향 카세트 840각
    fur(nm + '_Panel', B(u - 420, d - 420, u + 420, d + 420), EAVE - 32, EAVE, 'porcelain')
    fur(nm + '_Grille', B(u - 250, d - 250, u + 250, d + 250), EAVE - 37, EAVE - 32, 'metal')
    for (a0, b0, a1, b1) in [(-330, -390, 330, -330), (-330, 330, 330, 390), (-390, -330, -330, 330), (330, -330, 390, 330)]:
        fur(nm + '_Slot', B(u + a0, d + b0, u + a1, d + b1), EAVE - 37, EAVE - 32, 'frame')
def erv_flat(nm, u, d):                                                     # 평천장: 전열교환기 급·배기구 (지름 220)
    fur(nm + '_Ring', Point(u, -d).buffer(110, resolution=4), EAVE - 22, EAVE, 'porcelain'); fur(nm + '_Core', Point(u, -d).buffer(60, resolution=4), EAVE - 30, EAVE - 22, 'metal')
def erv_slope(nm, u, d):                                                    # 박공 천장: 경사면을 따라 붙는 급·배기구
    for sub, top in tops(Point(u, -d).buffer(115, resolution=4)):
        add(nm + '_Ring', 'Roof', 'porcelain', sub, sh(top, -45), sh(top, -20), minarea=100)
def slot(nm, geom, z0, z1, grp='Furniture'):                                # 벽 상부 선형 디퓨저 (덕트형 에어컨 토출구)
    add(nm + '_Frame', grp, 'porcelain', geom, z0 - 25, z1 + 25, minarea=100); add(nm + '_Slot', grp, 'frame', geom.buffer(8, join_style=2), z0, z1, minarea=100)
def duct_flat(nm, u, d, along='u', L=1300):                                # 평천장: 덕트형 에어컨의 선형 토출구 + 흡입 그릴
    hx, hy = (L / 2, 55) if along == 'u' else (55, L / 2)
    fur(nm + '_SupplyFrame', B(u - hx - 25, d - hy - 25, u + hx + 25, d + hy + 25), EAVE - 14, EAVE, 'porcelain')
    fur(nm + '_SupplySlot', B(u - hx, d - hy, u + hx, d + hy), EAVE - 18, EAVE - 14, 'frame')
    ox, oy = (0, 520) if along == 'u' else (520, 0)                          # 흡입 그릴은 토출구 옆에
    rx, ry = (350, 175) if along == 'u' else (175, 350)
    fur(nm + '_ReturnFrame', B(u + ox - rx - 25, d + oy - ry - 25, u + ox + rx + 25, d + oy + ry + 25), EAVE - 14, EAVE, 'porcelain')
    for k_ in range(7):
        t_ = -ry + 2 * ry * (k_ + 0.5) / 7 if along == 'u' else -rx + 2 * rx * (k_ + 0.5) / 7
        fur(nm + '_ReturnLouver', B(u + ox - rx, d + oy + t_ - 14, u + ox + rx, d + oy + t_ + 14) if along == 'u' else B(u + ox + t_ - 14, d + oy - ry, u + ox + t_ + 14, d + oy + ry), EAVE - 19, EAVE - 14, 'metal')
for nm, u, d, al in [('AC_Master', 29150, 14700, 'u'), ('AC_Bed2', 22630, 9000, 'u'), ('AC_Foyer', 2200, 10500, 'u'), ('AC_Scullery', 5200, 7200, 'u'), ('AC_Util', 1500, 6900, 'u')]: duct_flat(nm, u, d, al)
for nm, u, d in [('ERV_Master_S', 27500, 13000), ('ERV_Master_R', 31000, 16200), ('ERV_Bed2', 21500, 11500), ('ERV_Dress', 29000, 6900), ('ERV_MBath', 30200, 9800), ('ERV_Bath2', 25480, 8500),
                 ('ERV_Corridor', 23600, 6500), ('ERV_Gallery', 5900, 9770), ('ERV_Util', 2300, 7200), ('ERV_Scullery', 3700, 7000), ('ERV_Powder', 5900, 11500), ('ERV_DressPass', 27600, 9800)]: erv_flat(nm, u, d)
fur('ERV_Unit_Hatch', B(1100, 7700, 1700, 8300), EAVE - 12, EAVE, 'porcelain'); fur('ERV_Unit_Hatch_Frame', B(1080, 7680, 1720, 8320).difference(B(1100, 7700, 1700, 8300)), EAVE - 16, EAVE, 'metal')
for nm, u, d in [('ERV_Hall_1', 9300, 10800), ('ERV_Hall_2', 13000, 7900), ('ERV_Hall_3', 12800, 13400), ('ERV_Living_1', 16500, 7600), ('ERV_Living_2', 19200, 11200), ('ERV_Attic', -3600, 8300)]: erv_slope(nm, u, d)
def grille_wall(nm, geom, z0, z1, horiz=True):                             # 벽 흡입 그릴 (루버)
    add(nm + '_Frame', 'Furniture', 'porcelain', geom, z0 - 25, z1 + 25, minarea=100)
    n_ = 6
    for k_ in range(n_):
        za = z0 + (z1 - z0) * k_ / n_
        add(nm + '_Louver', 'Furniture', 'metal', geom.buffer(8, join_style=2), za + 6, za + (z1 - z0) / n_ - 6, minarea=100)
slot('AC_Hall_W', B(7560, 10650, 7585, 12250), FL + 2440, FL + 2570); grille_wall('ACR_Hall_W', B(7560, 10900, 7580, 11800), FL + 1950, FL + 2250)
slot('AC_Hall_N1', B(8700, 5850, 10300, 5875), FL + 2440, FL + 2570); slot('AC_Hall_N2', B(11300, 5850, 12900, 5875), FL + 2440, FL + 2570)
slot('AC_Living_E1', B(20715, 7600, 20740, 9200), FL + 2440, FL + 2570); slot('AC_Living_E2', B(20715, 10000, 20740, 11600), FL + 2440, FL + 2570)
grille_wall('ACR_Living_E', B(20720, 9350, 20740, 9850), FL + 2150, FL + 2550)
slot('AC_Attic_E', B(-275, 6300, -250, 7900), AT_FL + 1240, AT_FL + 1370)
CH = []
for i in range(5):
    x = 8950 + 3700 / 5 * (i + 0.5)
    CH += [[x, -11095, 0, FL + 15, 'Furniture'], [x, -12905, 180, FL + 15, 'Furniture']]
CH += [[8620, -12000, 90, FL + 15, 'Furniture'], [12980, -12000, 270, FL + 15, 'Furniture']]
for i in range(5):
    x = 9600 + 3600 / 5 * (i + 0.5)
    CH += [[x, -14870, 0, FL - 15, 'Site'], [x, -16630, 180, FL - 15, 'Site']]
for k in range(4):
    CH.append([9700 + k * 800, -9150, 0, FL + 15, 'Furniture'])   # 아일랜드 스툴

FENCE = [{'p': [(-17350, -8200), (-17350, -16650), (2450, -16650), (4680, -15740), (7000, -17140), (14450, -20050), (34350, -20050), (34350, -11400)], 'z': PAD + 120}]
SPEC = {'roofs': ROOFSPEC, 'frames': [[round(v, 1) for v in f] for f in FRAMES], 'fences': FENCE, 'chairs': CH}
CH.append([-5250, -9400, 270, AT_FL + 15, 'Furniture'])
CH.append([22630, -11300, 0, FL + 15, 'Furniture'])
LABELS = [{'t': '다락 (서재·음악감상실)', 'x': -3600, 'y': -9400, 'z': AT_FL + 100, 'attic': 1}] + [{'t': k, 'x': round(room_poly(k).centroid.x), 'y': round(room_poly(k).centroid.y), 'z': FL + 100} for k in ROOMS]

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

# -*- coding: utf-8 -*-
"""설계 데이터 -> SketchUp용 프리즘 목록(JSON). 프리즘 = 평면 다각형 + 바닥/윗면 평면 z=a*x+b*y+c (mm)."""
import json, math
from shapely.geometry import Polygon, LineString, box, Point
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from design import *
from plan import (ROAD, WALL_L1, WALL_L2, WALL_LOW, FILL_W, FILL_E, NEWS, DECK, door_cut, PX)

P = []   # prisms

def C(z):
    return [0.0, 0.0, float(z)]

def nohole_parts(g):
    """구멍 있는 폴리곤을 구멍 없는 조각들로 분할"""
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

def add(name, group, mat, geom, zb, zt):
    if isinstance(zb, (int, float)): zb = C(zb)
    if isinstance(zt, (int, float)): zt = C(zt)
    parts = nohole_parts(geom.buffer(0) if geom.geom_type != 'GeometryCollection' else unary_union([g for g in geom.geoms if g.geom_type in ('Polygon', 'MultiPolygon')]))
    for k, p in enumerate(parts):
        p = orient(p.simplify(0.5), 1.0)
        if p.area < 2000:  # 2000mm2 미만 파편 무시
            continue
        P.append({'n': name if len(parts) == 1 else f'{name}_{k + 1:02d}', 'g': group, 'm': mat,
                  'p': [[round(x, 1), round(y, 1)] for x, y in list(p.exterior.coords)[:-1]],
                  'zb': [round(v, 6) for v in zb], 'zt': [round(v, 6) for v in zt]})

# ------------------------------------------------------------------ 평면 정의
WING_PLANE = [0.0, -1000 / 4800, 5700 + 14148 * 1000 / 4800]   # 날개 지붕 밑면 (남측으로 높아짐)
LB_PLANE = [1800 / 7549, 0.0, 6900.0]                          # 좌측 블록 지붕 밑면 (동측으로 높아짐)
def shift(pl, d):
    return [pl[0], pl[1], pl[2] + d]
ROAD_PLANE = [0.0, 0.2115, 519.0]

# ------------------------------------------------------------------ 대지
def single(line_pts, w, side):
    return LineString(line_pts).buffer(w * side, single_sided=True, cap_style=2, join_style=2)

road = Polygon(ROAD).buffer(0)
wall_L1 = single(WALL_L1, 600, -1)
wall_L2 = single(WALL_L2, 600, -1)
wall_low = single(NEWS, 350, -1)
wall_fw = single(FILL_W[:2], 350, +1)

XMIN, XMAX, YMIN, YMAX = -14000, 47000, -14000, 30000
def ext_line(pts, x0, x1):
    (ax, ay), (bx, by) = pts[0], pts[1]
    (cx, cy), (dx, dy) = pts[-2], pts[-1]
    first = (x0, ay + (by - ay) * (x0 - ax) / (bx - ax))
    last = (x1, cy + (dy - cy) * (x1 - cx) / (dx - cx))
    return [first] + list(pts) + [last]

L2e = ext_line(WALL_L2, 6000, XMAX)
L1e = ext_line(WALL_L1, 6000, XMAX)
LOWe = ext_line(WALL_LOW, WALL_LOW[0][0], XMAX)
mid_region = Polygon([(XMIN, YMIN)] + [(XMIN, L2e[0][1])] + L2e + [(XMAX, YMIN)])  # L2 남쪽 전체
up1_region = Polygon(L2e + list(reversed(L1e)))
up2_region = Polygon(L1e + [(XMAX, YMAX), (6000, YMAX)])
low_cut = Polygon([(XMIN, YMIN), (XMAX, YMIN), (XMAX, NEWS[-1][1])] + list(reversed(NEWS[:-1])) + [(0, 0), FILL_W[1], (XMIN, FILL_W[1][1])])
west_of_road = Polygon([(XMIN, YMIN), (XMIN, YMAX), (5136, YMAX)] + [PX(558, 365), PX(395, 530), PX(190, 715), PX(35, 1010)] + [(-13000, YMIN)])

terr_mid = mid_region.difference(low_cut).difference(road).difference(west_of_road).difference(LEFT)
terr_mid = terr_mid.difference(unary_union([wall_L2, wall_low, wall_fw]))
terr_up1 = up1_region.difference(road).difference(west_of_road).difference(wall_L1)
terr_up2 = up2_region.difference(road).difference(west_of_road)
ground = box(XMIN, YMIN, XMAX, YMAX).difference(road).difference(LEFT)

add('Ground_Lower', 'Site', 'grass_low', ground, -300, 0)
add('Terrace_Mid', 'Site', 'grass', terr_mid, 0, 2850)
add('Terrace_Upper1', 'Site', 'grass', terr_up1, 0, 4650)
add('Terrace_Upper2', 'Site', 'grass', terr_up2, 0, 6450)
add('Road', 'Site', 'road', road, shift(ROAD_PLANE, -300), ROAD_PLANE)
add('StoneWall_Upper', 'Site', 'stone', wall_L1.difference(road), 0, 6450)
add('StoneWall_Lower', 'Site', 'stone', wall_L2.difference(road), 0, 4650)
add('Retaining_South_New', 'Site', 'block', wall_low.difference(road), 0, 2850)
add('Retaining_South_Railing', 'Site', 'steel', LineString(NEWS).buffer(-40, single_sided=True, cap_style=2).difference(road), 2850, 3850)
add('Retaining_FillW', 'Site', 'block', wall_fw.difference(LEFT), 0, 2850)

NST = 17
# 남측 테라스 (성토 마당 위, 석재 포장)
terrace = DECK.intersection(terr_mid).difference(OUTLINE)
add('South_Terrace', 'Site', 'paving', terrace, 2850, 2950)

# ------------------------------------------------------------------ 지하 (B1)
add('B1_Floor', 'B1', 'concrete', box(0, 0, 7549, 7300), -300, 0)
add('B1_Wall_W', 'B1', 'concrete', box(0, 0, 250, 7300), 0, 2700)
add('B1_Wall_E', 'B1', 'concrete', box(7299, 0, 7549, 7300), 0, 2700)
add('B1_Wall_N', 'B1', 'concrete', box(250, 7050, 7299, 7300), 0, 2700)
add('B1_Transfer_Beam', 'B1', 'concrete', box(250, 0, 7299, 250), 2000, 2700)
evw = unary_union([LineString([(250, 5350), (1950, 5350)]).buffer(60, cap_style=2),
                   LineString([(1950, 5290), (1950, 7050)]).buffer(60, cap_style=2)]).difference(door_cut((1100, 5350), 900))
add('B1_EV_Shaft', 'B1', 'concrete', evw, 0, 2700)
add('B1_EV_Lintel', 'B1', 'concrete', door_cut((1100, 5350), 900).intersection(box(0, 5290, 3000, 5410)), 2100, 2700)
add('B1_Stair_Wall', 'B1', 'concrete', box(2700, 5865, 7299, 5985), 0, 2700)
for k in range(NST - 1):
    x0 = 2100 + 260 * k
    add(f'B1_Stair_{k + 1:02d}', 'B1', 'concrete', box(x0, 5985, x0 + 260, 7050), 0, 3000 / NST * (k + 1))
add('B1_Floor_Finish', 'B1', 'fl_service', rooms_b1['주차장'], 0, 15)

# ------------------------------------------------------------------ 1층
add('1F_Slab_OverGarage', '1F', 'concrete', LEFT.difference(box(2100, 5985, 6260, 7050)).difference(box(250, 5350, 1950, 7050)), 2700, 3000)
add('1F_Slab_OnGrade', '1F', 'concrete', OUTLINE.difference(LEFT), 2850, 3000)
# 바닥 마감 (실별 색)
FMAT = {'circ': 'fl_circ', 'public': 'fl_public', 'private': 'fl_private', 'service': 'fl_service'}
for name, p in rooms_1f.items():
    if name == 'EV':
        continue
    g = p
    if name == '계단실':
        g = p.difference(box(2100, 5985, 6260, 7050))
    add('1F_Floor_' + name, '1F', FMAT[ZONE[name]], g, 3000, 3015)

# 외벽: 외곽선 각 변을 마이터 사변형으로
opts = list(OUTLINE.exterior.coords)[:-1]
n = len(opts)
def inner_pt(k):
    p0, p1, p2 = opts[k - 1], opts[k], opts[(k + 1) % n]
    def off(a, b):
        L = math.dist(a, b); dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = -dy, dx
        return (a[0] + nx * EXT, a[1] + ny * EXT), (dx, dy)
    (a1, d1), (a2, d2) = off(p0, p1), off(p1, p2)
    den = d1[0] * d2[1] - d1[1] * d2[0]
    t = ((a2[0] - a1[0]) * d2[1] - (a2[1] - a1[1]) * d2[0]) / den
    return (a1[0] + d1[0] * t, a1[1] + d1[1] * t)
inn = [inner_pt(k) for k in range(n)]

def strip(i, s0, s1):
    a, b = opts[i], opts[(i + 1) % n]
    L = math.dist(a, b); dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -dy, dx
    big = 5000
    p0 = (a[0] + dx * s0, a[1] + dy * s0); p1 = (a[0] + dx * s1, a[1] + dy * s1)
    return Polygon([(p0[0] - nx * big, p0[1] - ny * big), (p1[0] - nx * big, p1[1] - ny * big),
                    (p1[0] + nx * big, p1[1] + ny * big), (p0[0] + nx * big, p0[1] + ny * big)])

def zone_top(geom):
    c = geom.centroid
    if c.x >= XJ - 1 and c.y > 9348 - 1:
        return WING_PLANE
    if LEFT.buffer(1).contains(c):
        return C(5750)
    return C(5700)

def wall_pieces(tag, i, quad, ops, z0, mat_wall):
    L = math.dist(opts[i], opts[(i + 1) % n])
    cuts = sorted(ops)
    s = -1000
    pieces = []
    for (s0, s1, sill, head, kind) in cuts:
        pieces.append(('solid', quad.intersection(strip(i, s, s0)), None))
        pieces.append((kind, quad.intersection(strip(i, s0, s1)), (sill, head)))
        s = s1
    pieces.append(('solid', quad.intersection(strip(i, s, L + 1000)), None))
    k = 0
    for kind, g, sh in pieces:
        if g.is_empty or g.area < 2000:
            continue
        # 날개/사선부 경계(XJ)에서 높이가 바뀌므로 분할
        for sub in (g.intersection(box(-1e5, -1e5, XJ, 1e5)), g.intersection(box(XJ, -1e5, 1e5, 1e5))):
            if sub.is_empty or sub.area < 2000:
                continue
            k += 1
            top = zone_top(sub)
            nm = f'{tag}_E{i}_{k:02d}'
            if kind == 'solid':
                add(nm, '1F', mat_wall, sub, z0, top)
            else:
                sill, head = sh
                if sill > 0:
                    add(nm + '_Sill', '1F', mat_wall, sub, z0, z0 + sill)
                add(nm + '_Head', '1F', mat_wall, sub, z0 + head, top)
                a, b = opts[i], opts[(i + 1) % n]
                Lr = math.dist(a, b); dx, dy = (b[0] - a[0]) / Lr, (b[1] - a[1]) / Lr
                nx, ny = -dy, dx
                gl = sub.intersection(Polygon([(a[0] - dx * 1e5 + nx * 100, a[1] - dy * 1e5 + ny * 100),
                                               (a[0] + dx * 1e5 + nx * 100, a[1] + dy * 1e5 + ny * 100),
                                               (a[0] + dx * 1e5 + nx * 140, a[1] + dy * 1e5 + ny * 140),
                                               (a[0] - dx * 1e5 + nx * 140, a[1] - dy * 1e5 + ny * 140)]))
                mat = 'glass'
                if i == 5 and 8000 < (cuts and [c for c in cuts if c[2] == sill and c[3] == head][0][0]) < 9000:
                    mat = 'wood_door'
                if i == 5 and kind == 'door' and head == 2200:
                    mat = 'door_gray'
                add(nm + ('_Door' if mat != 'glass' else '_Glass'), '1F', mat, gl, z0 + sill, z0 + head)

for i in range(n):
    quad = Polygon([opts[i], opts[(i + 1) % n], inn[(i + 1) % n], inn[i]])
    wall_pieces('1F_ExtWall', i, quad, openings.get(i, []), 3000, 'stucco')

# 날개 서측 박공벽 (사선부 지붕 위로 드러나는 부분 포함)
xj_wall = box(XJ, 9348 + EXT, XJ + EXT, 14148 - EXT)
add('1F_Wall_WingWest', '1F', 'stucco', xj_wall.difference(box(0, 12900, 1e6, 13900)), 3000, WING_PLANE)
add('1F_Wall_WingWest_Lintel', '1F', 'stucco', xj_wall.intersection(box(0, 12900, 1e6, 13900)), 5100, WING_PLANE)

# 내벽
int_lines = [l for l in walls_1f_int if not (abs(l.coords[0][0] - XJ) < 1 and abs(l.coords[-1][0] - XJ) < 1)]
iw = unary_union([l.buffer(INT / 2, cap_style=2, join_style=2) for l in int_lines]).intersection(INNER)
iw = iw.difference(xj_wall)
dc = unary_union([door_cut(p, w) for p, w in doors_1f])
solid_iw = iw.difference(dc)
for k, part in enumerate(nohole_parts(solid_iw)):
    add(f'1F_IntWall_{k + 1:02d}', '1F', 'partition', part, 3015, zone_top(part))
for k, part in enumerate(nohole_parts(iw.intersection(dc))):
    add(f'1F_IntWall_Lintel_{k + 1:02d}', '1F', 'partition', part, 5115, zone_top(part))
# EV 샤프트 (1층)
add('1F_EV_Door', '1F', 'steel', door_cut((1100, 5350), 900).intersection(box(0, 5330, 3000, 5370)), 3015, 5115)
# 다락 계단 (1층 -> 다락, 동쪽으로 오름)
for k in range(NST - 1):
    x0 = 2040 + 260 * k
    add(f'1F_Stair_Up_{k + 1:02d}', '1F', 'wood', box(x0, 4800, x0 + 260, 5865), 3000, 3000 + 3000 / NST * (k + 1))

# ------------------------------------------------------------------ 다락
add('AT_Slab', 'Attic', 'concrete', LEFT.difference(box(2040, 4800, 6200, 5865)), 5750, 6000)
add('AT_Floor_Study', 'Attic', 'fl_public', rooms_at['다락(서재)'], 6000, 6015)
add('AT_Floor_Store', 'Attic', 'fl_service', rooms_at['다락 수납'], 6000, 6015)
ainn = LEFT.buffer(-EXT, join_style=2)
aring = LEFT.difference(ainn)
at_open = [  # (영역, 하단, 상단, 종류)
    (box(7299, 1400, 7549, 3400), 6000, 6000 + 2200, 'door'),          # 옥상 데크로 나가는 문
    (box(2600, 0, 7299, 250), 6450, None, 'win'),                        # 남측 경사 고창
    (box(0, 2000, 250, 3200), 6450, None, 'win'),                        # 서측 작은 창
]
solid = aring
for g, zb, zt, kind in at_open:
    solid = solid.difference(g)
    top = [LB_PLANE[0], LB_PLANE[1], LB_PLANE[2] - 200] if zt is None else C(zt)
    add('AT_Wall_Below_' + kind, 'Attic', 'metal_dark', g.intersection(aring), 6000, zb) if zb > 6000 else None
    add('AT_Wall_Above_' + kind, 'Attic', 'metal_dark', g.intersection(aring), top, LB_PLANE)
    # 유리
    if g.bounds[2] - g.bounds[0] > g.bounds[3] - g.bounds[1]:
        gl = g.intersection(box(-1e5, g.bounds[1] + 100, 1e5, g.bounds[1] + 140))
    else:
        gl = g.intersection(box(g.bounds[0] + 100, -1e5, g.bounds[0] + 140, 1e5))
    add('AT_Glass_' + kind, 'Attic', 'glass', gl, zb, top)
add('AT_Wall', 'Attic', 'metal_dark', solid, 6000, LB_PLANE)
add('AT_Wall_Stair', 'Attic', 'partition', box(2040, 5865, 7299, 5985), 6015, shift(LB_PLANE, -1))

# ------------------------------------------------------------------ 지붕
add('Roof_LeftBlock', 'Roof', 'metal_dark', box(-400, -400, 7949, 7700), LB_PLANE, shift(LB_PLANE, 250))
band = OUTLINE.difference(LEFT).difference(WING)
add('Roof_Band_Slab', 'Roof', 'concrete', band, 5700, 6000)
deck_r = band.intersection(Polygon([W(-3000, 2900), W(6000, 2900), W(6000, 8000), W(-3000, 8000)])).buffer(-EXT, join_style=2)
green = band.buffer(-EXT, join_style=2).difference(deck_r.buffer(150, join_style=2))
add('Roof_Deck_Wood', 'Roof', 'wood', deck_r, 6000, 6060)
add('Roof_Green', 'Roof', 'green_roof', green, 6000, 6100)
par = band.difference(band.buffer(-EXT, join_style=2)).difference(LEFT.buffer(1)).difference(box(XJ - 1, 0, 1e6, 1e6))
add('Roof_Parapet', 'Roof', 'stucco', par, 6000, 6350)
deck_edge = par.intersection(deck_r.buffer(EXT + 10, join_style=2))
add('Roof_Deck_Railing_Glass', 'Roof', 'glass', deck_edge.buffer(-110, join_style=2) if not deck_edge.buffer(-110).is_empty else deck_edge, 6350, 7200)
add('Roof_Wing', 'Roof', 'metal_dark', box(XJ, 9348 - 600, 32550 + 400, 14148 + 400), WING_PLANE, shift(WING_PLANE, 250))

# ------------------------------------------------------------------ 가구/차량 (스케일용 매스)
F = []
def fur(name, poly, zb, zt, group='Furniture', mat='furniture'):
    add(name, group, mat, poly, zb, zt)
fur('Sofa', box(3000, 1500, 5600, 2400), 3015, 3415)
fur('Sofa_Back', box(3000, 1500, 5600, 1700), 3415, 3815)
fur('TV_Unit', box(3300, 3000, 5300, 3450), 3015, 3515)
fur('Kitchen_Island', Polygon([W(4300, 4300), W(6900, 4300), W(6900, 5200), W(4300, 5200)]), 3015, 3915)
fur('Kitchen_Counter', Polygon([W(3400, 2900 + 60), W(8300, 2900 + 60), W(8300, 3550), W(3400, 3550)]), 3015, 3915)
fur('Dining_Table', Polygon([W(300, 4800), W(2400, 4800), W(2400, 5900), W(300, 5900)]), 3700, 3765)
fur('Bed_Master', box(23400, 9900, 25500, 12000), 3015, 3515)
fur('Bed_2', box(19000, 9900, 20500, 11900), 3015, 3515)
fur('Desk_Attic', box(3200, 600, 6200, 1300), 6700, 6750)
for k, x0 in enumerate((1425, 4225)):
    fur(f'Car_{k + 1}_Body', box(x0, 400, x0 + 1900, 5200), 300, 1000, group='B1', mat='car')
    fur(f'Car_{k + 1}_Cabin', box(x0 + 100, 1400, x0 + 1800, 4300), 1000, 1700, group='B1', mat='car_glass')

# 실명 라벨 위치
LABELS = []
for name, p in rooms_1f.items():
    if name in ('EV',):
        continue
    c = p.representative_point()
    LABELS.append({'t': name, 'x': round(c.x), 'y': round(c.y), 'z': 3100, 'l': 'Labels_1F'})
for name, p in rooms_b1.items():
    c = p.representative_point(); LABELS.append({'t': name, 'x': round(c.x), 'y': round(c.y), 'z': 100, 'l': 'Labels_B1'})
for name, p in rooms_at.items():
    c = p.representative_point(); LABELS.append({'t': name, 'x': round(c.x), 'y': round(c.y), 'z': 6100, 'l': 'Labels_AT'})
LABELS.append({'t': '남측 테라스', 'x': round(DECK.centroid.x), 'y': round(DECK.centroid.y), 'z': 3050, 'l': 'Labels_1F'})
LABELS.append({'t': '옥상 데크', 'x': round(deck_r.centroid.x), 'y': round(deck_r.centroid.y), 'z': 6150, 'l': 'Labels_AT'})

if __name__ == '__main__':
    json.dump({'prisms': P, 'labels': LABELS}, open('prisms.json', 'w'), ensure_ascii=False)
    from collections import Counter
    print(len(P), Counter(p['g'] for p in P))
    print('size', len(json.dumps(P)))

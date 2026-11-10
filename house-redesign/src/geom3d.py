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
POOL_S = Polygon([W(600, 9000), W(4600, 9000), W(4600, 10300), W(600, 10300)]).intersection(terrace.buffer(-300))
add('South_Deck_Wood', 'Site', 'wood', terrace.difference(POOL_S), 2850, 2985)
add('LS_SouthPool_Base', 'Site', 'pebble_dark', POOL_S, 2450, 2550)
add('LS_SouthPool_Water', 'Site', 'water', POOL_S, 2550, 2880)

# ------------------------------------------------------------------ 지하 (B1)
add('B1_Floor', 'B1', 'concrete', box(0, 0, 7549, 7300), -300, 0)
add('B1_Wall_W', 'B1', 'concrete', box(0, 0, 250, 7300), 0, 2700)
add('B1_Wall_E', 'B1', 'concrete', box(7299, 0, 7549, 7300), 0, 2700)
add('B1_Wall_N', 'B1', 'concrete', box(250, 7050, 7299, 7300), 0, 2700)
add('B1_Transfer_Beam', 'B1', 'concrete', box(250, 0, 7299, 250), 2000, 2700)
evw = unary_union([LineString([(250, 5250), (1980, 5250)]).buffer(60, cap_style=2),
                   LineString([(1980, 5190), (1980, 7050)]).buffer(60, cap_style=2)]).difference(door_cut((1100, 5250), 1000))
add('B1_EV_Shaft', 'B1', 'concrete', evw, 0, 2700)
add('B1_EV_Lintel', 'B1', 'concrete', door_cut((1100, 5250), 1000).intersection(box(0, 5190, 3000, 5310)), 2100, 2700)
add('B1_Stair_Wall', 'B1', 'concrete', box(2700, 5865, 7299, 5985), 0, 2700)
for k in range(NST - 1):
    x0 = 2100 + 260 * k
    add(f'B1_Stair_{k + 1:02d}', 'B1', 'concrete', box(x0, 5985, x0 + 260, 7050), 0, 3000 / NST * (k + 1))
add('B1_Floor_Finish', 'B1', 'fl_service', rooms_b1['주차장'], 0, 15)

# ------------------------------------------------------------------ 1층
add('1F_Slab_OverGarage', '1F', 'concrete', LEFT.difference(box(2100, 5985, 6260, 7050)).difference(box(250, 5250, 1980, 7050)), 2700, 3000)
add('1F_Slab_OnGrade', '1F', 'concrete', OUTLINE.difference(LEFT), 2850, 3000)
# 바닥 마감 (실별 색)
FMAT = {'circ': 'fl_circ', 'public': 'fl_public', 'private': 'fl_private', 'service': 'fl_service'}
for name, p in rooms_1f.items():
    if name == 'EV':
        continue
    g = p
    if name == '계단·홀':
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

# ---- 박공지붕 평면 (밑면, 외벽 외곽선 기준)  z = a*x + b*y + c
PITCH_B = 0.5          # 사선부·날개 6/12 (26.6도)
PITCH_L = 0.5774       # 좌측 블록(거실) 30도
EAVE = 5750
RIDGE_LX = 7549 / 2
_pv = P3[0] * V[0] + P3[1] * V[1]
PL = {
    'L_W': [PITCH_L, 0.0, EAVE],                                  # 거실동 서측 경사
    'L_E': [-PITCH_L, 0.0, EAVE + PITCH_L * 7549],                # 거실동 동측 경사
    'B_NW': [PITCH_B * V[0], PITCH_B * V[1], EAVE - PITCH_B * _pv],              # 사선부 북서 경사 (v<4000)
    'B_SE': [-PITCH_B * V[0], -PITCH_B * V[1], EAVE + PITCH_B * (8000 + _pv)],   # 사선부 남동 경사
    'W_S': [0.0, PITCH_B, EAVE - PITCH_B * 9348],                 # 날개 남측 경사 (y<11748)
    'W_N': [0.0, -PITCH_B, EAVE + PITCH_B * 14148],               # 날개 북측 경사
}
RIDGE_WY = (9348 + 14148) / 2
LEFT_Z = box(-1e5, -1e5, 7549, 7300)
WING_Z = box(XJ, 9348 - 1, 1e6, 1e6)
BAND_Z = box(-1e6, -1e6, 1e6, 1e6).difference(LEFT_Z).difference(WING_Z)
def band_side(nw):
    return band_poly(-1e5, 1e5, -1e5, 4000) if nw else band_poly(-1e5, 1e5, 4000, 1e5)
ZONES = [
    (LEFT_Z.intersection(box(-1e6, -1e6, RIDGE_LX, 1e6)), 'L_W'),
    (LEFT_Z.intersection(box(RIDGE_LX, -1e6, 1e6, 1e6)), 'L_E'),
    (WING_Z.intersection(box(-1e6, -1e6, 1e6, RIDGE_WY)), 'W_S'),
    (WING_Z.intersection(box(-1e6, RIDGE_WY, 1e6, 1e6)), 'W_N'),
    (BAND_Z.intersection(band_side(True)), 'B_NW'),
    (BAND_Z.intersection(band_side(False)), 'B_SE'),
]
def tops(geom, off=0.0):
    out = []
    for zpoly, key in ZONES:
        pc = geom.intersection(zpoly)
        if pc.is_empty or pc.area < 1500:
            continue
        pl = PL[key]
        out.append((pc, [pl[0], pl[1], pl[2] + off]))
    return out

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
    a, b = opts[i], opts[(i + 1) % n]
    Lr = math.dist(a, b); dx, dy = (b[0] - a[0]) / Lr, (b[1] - a[1]) / Lr
    nx, ny = -dy, dx
    gstrip = Polygon([(a[0] - dx * 1e5 + nx * 100, a[1] - dy * 1e5 + ny * 100), (a[0] + dx * 1e5 + nx * 100, a[1] + dy * 1e5 + ny * 100),
                      (a[0] + dx * 1e5 + nx * 140, a[1] + dy * 1e5 + ny * 140), (a[0] - dx * 1e5 + nx * 140, a[1] - dy * 1e5 + ny * 140)])
    for kind, g0, sh in pieces:
        if g0.is_empty or g0.area < 2000:
            continue
        for sub, top in tops(g0):
            k += 1
            mw = 'wood_dark' if (i == 5 and Point(4828, 8212).distance(sub.centroid) < 2700) else mat_wall
            nm = f'{tag}_E{i}_{k:02d}'
            if kind == 'solid':
                add(nm, '1F', mw, sub, z0, top)
            else:
                sill, head = sh
                if sill > 0:
                    add(nm + '_Sill', '1F', mw, sub, z0, z0 + sill)
                add(nm + '_Head', '1F', mw, sub, z0 + head, top)
                mat = 'glass'
                if i == 5 and kind == 'door' and head == 2400:
                    mat = 'bronze'
                if i == 5 and kind == 'door' and head == 2200:
                    mat = 'door_gray'
                add(nm + ('_Door' if mat != 'glass' else '_Glass'), '1F', mat, sub.intersection(gstrip), z0 + sill, z0 + head)

for i in range(n):
    quad = Polygon([opts[i], opts[(i + 1) % n], inn[(i + 1) % n], inn[i]])
    wall_pieces('1F_ExtWall', i, quad, openings.get(i, []), 3000, 'stucco')

# 날개 서측 박공벽
xj_wall = box(XJ, 9348 + EXT, XJ + EXT, 14148 - EXT)
for k, (pc, top) in enumerate(tops(xj_wall.difference(box(0, 12650, 1e6, 13850)))):
    add(f'1F_Wall_WingWest_{k + 1}', '1F', 'stucco', pc, 3000, top)
for k, (pc, top) in enumerate(tops(xj_wall.intersection(box(0, 12650, 1e6, 13850)))):
    add(f'1F_Wall_WingWest_Lintel_{k + 1}', '1F', 'stucco', pc, 5100, top)

# 내벽 (지붕 밑까지: 박공 천장)
int_lines = [l for l in walls_1f_int if not (abs(l.coords[0][0] - XJ) < 1 and abs(l.coords[-1][0] - XJ) < 1)]
iw = unary_union([l.buffer(INT / 2, cap_style=2, join_style=2) for l in int_lines]).intersection(INNER)
iw = iw.difference(xj_wall)
dc = unary_union([door_cut(p, w) for p, w in doors_1f])
k = 0
for part in nohole_parts(iw.difference(dc)):
    for pc, top in tops(part):
        k += 1
        add(f'1F_IntWall_{k:02d}', '1F', 'partition', pc, 3015, top)
k = 0
for part in nohole_parts(iw.intersection(dc)):
    for pc, top in tops(part):
        k += 1
        add(f'1F_IntWall_Lintel_{k:02d}', '1F', 'partition', pc, 5115, top)
add('1F_EV_Door', '1F', 'steel', door_cut((1100, 5250), 1000).intersection(box(0, 5230, 3000, 5270)), 3015, 5115)
# 다락 계단 자리 -> 붙박이 수납장 (청소·관리 편의)
add('1F_Builtin_Storage', 'Furniture', 'furniture', box(2100, 5265, 6260, 5865), 3015, 5415)

# ------------------------------------------------------------------ 박공지붕 (평면 경사판 조합)
RT = 250
ov = 600
lb_fp = box(-500, -500, 7549 + 500, 7300 + 500)
add('Roof_Living_W', 'Roof', 'metal_dark', lb_fp.intersection(box(-1e6, -1e6, RIDGE_LX, 1e6)), PL['L_W'], shift(PL['L_W'], RT))
add('Roof_Living_E', 'Roof', 'metal_dark', lb_fp.intersection(box(RIDGE_LX, -1e6, 1e6, 1e6)), PL['L_E'], shift(PL['L_E'], RT))
band_fp = OUTLINE.difference(LEFT).difference(WING).buffer(ov, join_style=2).difference(LEFT).difference(box(XJ, -1e6, 1e6, 1e6))
band_fp = band_fp.intersection(band_poly(-3000, 20000, -ov, 8000 + ov))
add('Roof_Band_NW', 'Roof', 'metal_dark', band_fp.intersection(band_side(True)), PL['B_NW'], shift(PL['B_NW'], RT))
add('Roof_Band_SE', 'Roof', 'metal_dark', band_fp.intersection(band_side(False)), PL['B_SE'], shift(PL['B_SE'], RT))
wing_s = unary_union([box(XJ, 9348 - ov, 32550 + 400, RIDGE_WY), box(XJ - 2500, 9348, XJ, RIDGE_WY)])
wing_n = unary_union([box(XJ, RIDGE_WY, 32550 + 400, 14148 + 1100), box(XJ - 2500, RIDGE_WY, XJ, 14148)])
add('Roof_Wing_S', 'Roof', 'metal_dark', wing_s, PL['W_S'], shift(PL['W_S'], RT))
add('Roof_Wing_N', 'Roof', 'metal_dark', wing_n, PL['W_N'], shift(PL['W_N'], RT))
deck_r = band_fp  # (라벨 호환용)

# ------------------------------------------------------------------ 가구/차량 (스케일용 매스)
F = []
def fur(name, poly, zb, zt, group='Furniture', mat='furniture'):
    add(name, group, mat, poly, zb, zt)
fur('Sofa', box(3000, 1500, 5600, 2400), 3015, 3415)
fur('Sofa_Back', box(3000, 1500, 5600, 1700), 3415, 3815)
fur('TV_Unit', box(3300, 3000, 5300, 3450), 3015, 3515)
fur('Kitchen_Island', Polygon([W(4300, 4900), W(6900, 4900), W(6900, 5800), W(4300, 5800)]), 3015, 3865)
fur('Kitchen_Counter', Polygon([W(3400, 2900 + 60), W(8300, 2900 + 60), W(8300, 3550), W(3400, 3550)]), 3015, 3915)
fur('Dining_Table', Polygon([W(300, 4800), W(2400, 4800), W(2400, 5900), W(300, 5900)]), 3700, 3765)
fur('Bed_Master', box(23400, 9900, 25500, 12000), 3015, 3515)
fur('Bed_2', box(19000, 9900, 20500, 11900), 3015, 3515)
fur('Breakfast_Table', Polygon([W(7300, 6200), W(8500, 6200), W(8500, 7200), W(7300, 7200)]), 3700, 3765)
fur('Bath_Tub', box(27000, 9750, 28700, 10550), 3015, 3565, mat='porcelain')
fur('Bath_Shower_Glass', box(28800, 9700, 28840, 11000), 3015, 5115, mat='glass')
fur('Bath_Vanity_1', box(26700, 13300, 28200, 13848), 3015, 3865)
fur('Bath_Vanity_2', box(28400, 13300, 29900, 13848), 3015, 3865)
fur('Closet_Shelves_N', box(30300, 13300, 32250, 13848), 3015, 5015)
fur('Closet_Shelves_S', box(30300, 9648, 32250, 10200), 3015, 5015)
for k, x0 in enumerate((1600, 4600)):
    fur(f'Car_{k + 1}_Body', box(x0, 400, x0 + 1900, 5200), 300, 1000, group='B1', mat='car')
    fur(f'Car_{k + 1}_Cabin', box(x0 + 100, 1400, x0 + 1800, 4300), 1000, 1700, group='B1', mat='car_glass')


# ------------------------------------------------------------------ 조경 (레퍼런스 반영)
def oct_(cx, cy, r, n=8):
    return Polygon([(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)])
LSG = 'Site'
site_ok = terr_mid.buffer(-50)
# (1) 현관 수공간 중정 : 문 중심 D, 외측 법선 N, 입면 방향 T
D = (4828.0, 8212.0); N = (-0.6523, 0.758); T = (0.758, 0.6523)
def L(n_, t_):
    return (D[0] + n_ * N[0] + t_ * T[0], D[1] + n_ * N[1] + t_ * T[1])
def LR(n0, n1, t0, t1):
    return Polygon([L(n0, t0), L(n1, t0), L(n1, t1), L(n0, t1)])
court = LR(0, 5600, -3600, 4200).intersection(site_ok).difference(OUTLINE.buffer(30))
water = unary_union([LR(700, 1500, -2500, 2400), LR(1500, 5000, 1100, 2400)]).intersection(court)
coping = water.buffer(160, join_style=2).intersection(court).difference(water)
path = LR(0, 5600, -800, 800).intersection(court)
bridge = LR(600, 1600, -900, 900).intersection(court)
beds = unary_union([LR(600, 5200, 2700, 4000), LR(2000, 5200, -3400, -1200)]).intersection(court).difference(coping)
gravel = court.difference(unary_union([water.buffer(160), path, beds]))
add('LS_Entry_Gravel', LSG, 'pebble_dark', gravel, 2850, 2880)
add('LS_Entry_Path_Travertine', LSG, 'travertine', path.difference(water.buffer(160)), 2850, 2990)
water = water.difference(bridge)
add('LS_Entry_Pool_Base', LSG, 'pebble_dark', water, 2500, 2600)
add('LS_Entry_Pool_Water', LSG, 'water', water, 2600, 2900)
add('LS_Entry_Pool_Coping', LSG, 'stone_dark', coping.difference(bridge), 2850, 2980)
add('LS_Entry_Bridge_Slab', LSG, 'stone_dark', bridge, 2600, 2990)
add('LS_Entry_Planting', LSG, 'fern', beds, 2850, 3250)
add('LS_Entry_Bench', LSG, 'wood', LR(3600, 4050, -3000, -1600).intersection(court), 3250, 3300)
for k, (nn, tt) in enumerate([(4200, 3300), (3200, -2600)]):
    c = L(nn, tt)
    if site_ok.contains(Point(c)):
        add(f'LS_Maple_{k + 1}_Trunk', LSG, 'trunk', oct_(c[0], c[1], 90), 2850, 4600)
        add(f'LS_Maple_{k + 1}_Crown', LSG, 'maple', oct_(c[0], c[1], 1500, 10), 4600, 6400)
# 현관 캐노피 (깊은 평지붕 처마)
canopy = LR(0, 2300, -1900, 2600).difference(OUTLINE)
add('LS_Entry_Canopy', '1F', 'metal_dark', canopy, 5800, 6000)

# (2) 북측 정원: 툇마루 + 빗물체인 + 자갈·이끼·대나무
north_zone = terr_mid.intersection(box(11900, 14148, 33500, 30000)).difference(OUTLINE.buffer(10))
engawa = north_zone.intersection(box(13000, 14148, 22000, 15050))
channel = north_zone.intersection(box(22000, 14148, 33200, 15900))
gravel_w = north_zone.difference(engawa).difference(channel).intersection(box(11900, 14148, 33200, 30000))
add('LS_Engawa_Deck', LSG, 'wood', engawa, 2850, 2980)
add('LS_RainChain_Pebbles', LSG, 'pebble_dark', channel, 2850, 2880)
add('LS_Gravel_Garden', LSG, 'gravel_white', gravel_w, 2850, 2880)
for k, x in enumerate([23600, 27000, 30600]):
    y = 15150
    zr = PL['W_N'][1] * y + PL['W_N'][2]
    add(f'LS_RainChain_{k + 1}_Slab', LSG, 'stone_dark', box(x - 450, y - 450, x + 450, y + 450), 2880, 2980)
    z = zr - 60
    j = 0
    while z - 170 > 3050:
        j += 1
        add(f'LS_RainChain_{k + 1}_Cup{j:02d}', LSG, 'copper', oct_(x, y, 60), z - 150, z)
        z -= 340
add('LS_Tsukubai_Basin', LSG, 'stone', oct_(27900, 15500, 330, 10), 2880, 3330)
for k, (x, y, r) in enumerate([(24800, 16200, 900), (28600, 16700, 700), (19500, 15900, 650)]):
    m = oct_(x, y, r, 10).intersection(gravel_w)
    add(f'LS_Moss_{k + 1}', LSG, 'moss', m, 2880, 2960)
wall_face = LineString(WALL_L2).parallel_offset(700, 'right')
for k, x in enumerate([15000, 20000, 24500, 29000, 32300]):
    base = wall_face.interpolate(wall_face.project(Point(x, 17000)))
    if not north_zone.contains(base):
        continue
    for j in range(7):
        a_ = 2 * math.pi * j / 7
        sx, sy = base.x + 260 * math.cos(a_) * (j % 3 + 1) / 2, base.y + 200 * math.sin(a_)
        add(f'LS_Bamboo_{k + 1}_{j + 1}', LSG, 'bamboo', oct_(sx, sy, 28, 6), 2880, 7200 + 300 * (j % 3))
    add(f'LS_Bamboo_{k + 1}_Leaves', LSG, 'bamboo_leaf', oct_(base.x, base.y, 900, 10), 5600, 7900)

# (3) 남측: 목재 루버 담장 + 사각 화분 회양목 + 낮은 생울타리
for j in range(12):
    z0 = 3050 + j * 150
    add(f'LS_Slat_Screen_{j + 1:02d}', LSG, 'wood', Polygon([W(-850, 8150), W(-810, 8150), W(-810, 10600), W(-850, 10600)]).intersection(site_ok.buffer(300)), z0, z0 + 90)
add('LS_Slat_Screen_Post_1', LSG, 'steel', Polygon([W(-880, 8150), W(-780, 8150), W(-780, 8250), W(-880, 8250)]), 2950, 4900)
add('LS_Slat_Screen_Post_2', LSG, 'steel', Polygon([W(-880, 10500), W(-780, 10500), W(-780, 10600), W(-880, 10600)]), 2950, 4900)
for k, u in enumerate([-100, 5300]):
    pl = Polygon([W(u, 9350), W(u + 600, 9350), W(u + 600, 9950), W(u, 9950)])
    if terrace.contains(pl.centroid):
        c = pl.centroid
        add(f'LS_Planter_{k + 1}', LSG, 'planter', pl, 2950, 3650)
        for t_, (r_, z0_, z1_) in enumerate([(300, 3650, 3800), (380, 3800, 4150), (300, 4150, 4300)]):
            add(f'LS_Boxwood_{k + 1}_{t_ + 1}', LSG, 'hedge', oct_(c.x, c.y, r_, 10), z0_, z1_)
hedge = Polygon([W(0, 10650), W(6300, 10650), W(6300, 11000), W(0, 11000)]).intersection(terrace)
add('LS_Hedge_South', LSG, 'hedge', hedge, 2950, 3550)

# 실명 라벨 위치
LABELS = []
for name, p in rooms_1f.items():
    if name in ('EV',):
        continue
    c = p.representative_point()
    LABELS.append({'t': name, 'x': round(c.x), 'y': round(c.y), 'z': 3100, 'l': 'Labels_1F'})
for name, p in rooms_b1.items():
    c = p.representative_point(); LABELS.append({'t': name, 'x': round(c.x), 'y': round(c.y), 'z': 100, 'l': 'Labels_B1'})
LABELS.append({'t': '연못 데크', 'x': round(DECK.centroid.x), 'y': round(DECK.centroid.y), 'z': 3050, 'l': 'Labels_1F'})

if __name__ == '__main__':
    json.dump({'prisms': P, 'labels': LABELS}, open('prisms.json', 'w'), ensure_ascii=False)
    from collections import Counter
    print(len(P), Counter(p['g'] for p in P))
    print('size', len(json.dumps(P)))

# -*- coding: utf-8 -*-
"""C안: 단층·무(無)엘리베이터 모던 팜하우스. 로컬 좌표계(mm): x=u(뒤 석축과 나란한 동쪽), y=북(석축 쪽, 석축선=0), d=-y(석축에서 남쪽 거리)."""
import math
from shapely.geometry import Polygon, LineString, box, Point
from shapely.ops import unary_union
from shapely.geometry.polygon import orient

EXT, INT = 250, 120
PAD, FL = 2850, 3000
EAVE = FL + 2700
RT = 220            # 지붕 두께
TAN = 0.5           # 6/12 (26.6도)
NAT = [0.0, 0.18, 4470.0]   # 원지반(추정) 평면 z = 4470 + 0.18*y

# ---- 도면(월드) -> 로컬
O = (9926.0, 16270.0)
_a = math.atan2(2203, 17960)
UX = (math.cos(_a), math.sin(_a)); NY = (-math.sin(_a), math.cos(_a))
def L(p):
    dx, dy = p[0] - O[0], p[1] - O[1]
    return (dx * UX[0] + dy * UX[1], dx * NY[0] + dy * NY[1])
def LP(px, py):
    return L(((px - 395) * 31.51, (932 - py) * 31.47))
def B(u0, d0, u1, d1):
    return box(min(u0, u1), -max(d0, d1), max(u0, u1), -min(d0, d1))

# ---- 건물 매스
D0 = 5600                                   # 북측 외벽 (석축 남면 d=600 에서 5.0m)
GAR = B(-7000, D0, 0, D0 + 7600)            # 차고
BAR = B(0, D0, 32000, D0 + 7000)            # 본채 (동서로 긴 채)
HALL = B(7500, D0, 15300, D0 + 9000)        # 주방·다이닝 홀 (남쪽 박공)
MAST = B(26500, D0, 32000, D0 + 11500)      # 안방 날개
OUTLINE = orient(unary_union([GAR, BAR, HALL, MAST]).simplify(1), 1.0)
HEATED = unary_union([BAR, HALL, MAST])
INNER = OUTLINE.buffer(-EXT, join_style=2)

# ---- 실 (내치수 사각형)  name: (u0,d0,u1,d1, zone)
ROOMS = {
    '차고 (2대)':            (-6750, 5850, -125, 12950, 'garage'),
    '다용도실':              (125, 5850, 2940, 8960, 'service'),
    '보조주방':              (3060, 5850, 7440, 8960, 'service'),
    '현관':                  (125, 9080, 4350, 12350, 'circ'),
    '갤러리':                (4350, 9080, 7440, 10460, 'circ'),
    '손님 화장실':           (4470, 10580, 7440, 12350, 'service'),
    '주방':                  (7560, 5850, 15240, 9700, 'public'),
    '다이닝 (14인)':         (7560, 9700, 15240, 14350, 'public'),
    '거실':                  (15360, 5850, 20740, 12350, 'public'),
    '복도':                  (20860, 5850, 26440, 7150, 'circ'),
    '침실2 (게스트·서재)':   (20860, 7270, 24400, 12350, 'private'),
    '욕실2':                 (24520, 7270, 26440, 9840, 'service'),
    '붙박이 수납':           (24520, 9960, 26440, 12350, 'private'),
    '드레스룸':              (26560, 5850, 31750, 7940, 'private'),
    '드레스 통로':           (26560, 8060, 28680, 11540, 'private'),
    '부부욕실':              (28800, 8060, 31750, 11540, 'service'),
    '안방':                  (26560, 11660, 31750, 16850, 'private'),
}
def room_poly(k):
    u0, d0, u1, d1, _ = ROOMS[k]
    return B(u0, d0, u1, d1)

# ---- 내벽 (u0,d0,u1,d1,두께)  /  문 (u,d,폭)
WALLS_INT = [
    (0, 5600, 0, 12600, 250),          # W1 차고|다용도·현관
    (3000, 5600, 3000, 9020, INT),     # W2 다용도|보조주방
    (0, 9020, 7500, 9020, INT),        # W3
    (7500, 5600, 7500, 12600, INT),    # W4 링크|홀
    (4410, 10520, 7500, 10520, INT),   # W5 화장실 북벽
    (4410, 10520, 4410, 12600, INT),   # W6 화장실 서벽
    (15300, 5600, 15300, 12600, INT),  # W7 홀|거실
    (20800, 5600, 20800, 12600, INT),  # W8 거실|침실동
    (20800, 7210, 26500, 7210, INT),   # W9 복도 남벽
    (24460, 7210, 24460, 12600, INT),  # W10
    (24460, 9900, 26500, 9900, INT),   # W11
    (26500, 5600, 26500, 12600, INT),  # W12 본채|안방 날개
    (26500, 8000, 32000, 8000, INT),   # W13
    (28740, 8000, 28740, 11600, INT),  # W14
    (26500, 11600, 32000, 11600, INT), # W15
]
VAULT_WALLS = [3, 6, 7]                # 박공 천장 공간(홀·거실)을 나누는 벽
DOORS_INT = [
    (0, 7200, 1000),       # 차고 -> 다용도실
    (3000, 7300, 1000),    # 다용도실 -> 보조주방
    (1800, 9020, 1000),    # 다용도실 -> 현관
    (7500, 7900, 1000),    # 보조주방 -> 주방
    (7500, 9770, 1380),    # 갤러리 -> 홀 (개방)
    (6200, 10520, 1000),   # 손님 화장실
    (15300, 9450, 4300),   # 홀 <-> 거실 (넓은 개구부)
    (20800, 6500, 1100),   # 거실 -> 복도
    (23100, 7210, 1000),   # 침실2
    (25480, 7210, 1000),   # 욕실2
    (24460, 11150, 1500),  # 침실2 -> 붙박이 수납
    (26500, 6500, 1100),   # 복도 -> 안방 드레스룸
    (27500, 8000, 1600),   # 드레스룸 -> 통로
    (28740, 9800, 1000),   # 부부욕실
    (27350, 11600, 1100),  # 통로 -> 안방
]

# ---- 외벽 개구부: (u0,d0,u1,d1, 창대, 상단, 종류)  높이는 FL 기준
def od(d, u0, u1, sill, head, kind='win'):
    return (u0, d, u1, d, sill, head, kind)
def ou(u, d0, d1, sill, head, kind='win'):
    return (u, d0, u, d1, sill, head, kind)
N_, S_, SH, SM = D0, D0 + 7000, D0 + 9000, D0 + 11500
OPENINGS = [
    # 북면 (뒤뜰)
    od(N_, -5200, -3800, 1500, 2300), od(N_, 800, 2000, 1500, 2300),
    od(N_, 3400, 4300, 0, 2200, 'sdoor'), od(N_, 4800, 6700, 1100, 2300),
    od(N_, 8300, 12000, 1100, 2300), od(N_, 12900, 14600, 900, 2300),
    od(N_, 15900, 17300, 900, 2300), od(N_, 18900, 20300, 900, 2300),
    od(N_, 21400, 23500, 1000, 2300), od(N_, 24200, 25900, 1000, 2300),
    od(N_, 27500, 29800, 1500, 2300),
    # 동면
    ou(32000, 6300, 7400, 1500, 2300), ou(32000, 8600, 10400, 1400, 2300), ou(32000, 12800, 15800, 700, 2300),
    # 안방 남면·서면
    od(SM, 27400, 31100, 0, 2300, 'door'),
    ou(26500, 12900, 14300, 0, 2300, 'door'), ou(26500, 15000, 16600, 700, 2300),
    # 본채 남면 (중정 쪽)
    od(S_, 16000, 20300, 0, 2300, 'door'), od(S_, 21500, 23900, 600, 2300), od(S_, 24900, 26000, 1200, 2300),
    # 현관 포치
    od(S_, 1500, 2600, 0, 2300, 'wdoor'), od(S_, 2750, 3250, 0, 2300), od(S_, 5400, 6500, 1600, 2250),
    # 홀 남면 박공 유리 / 돌출부 옆면
    od(SH, 8300, 14500, 0, 2300, 'gable'),
    ou(7500, 13000, 14200, 700, 2300), ou(15300, 13000, 14200, 700, 2300),
    # 차고
    od(D0 + 7600, -1500, -500, 0, 2200, 'sdoor'), od(D0 + 7600, -5600, -3400, 1100, 2100),
    ou(-7000, 6200, 8900, 0, 2250, 'gdoor'), ou(-7000, 9900, 12600, 0, 2250, 'gdoor'),
]

# ---- 포치(처마 아래 덧지붕) : (다각형, 벽선 d, 이름)
PORCH = [
    (unary_union([B(-7300, 13200, 0, 15050), B(0, 12600, 7500, 15050)]), 12600, 'Entry'),
    (B(7400, 14600, 15400, 16850), 14600, 'Hall'),
    (B(15300, 12600, 26500, 14650), 12600, 'Court'),
]
def porch_plane(dw):
    return [0.0, 0.06, 5450 + 0.06 * dw]       # 밑면: z = 5450 - 0.06*(d-dw)
POSTS = [(u, 14930) for u in (-7200, -4800, -2400, 0, 2500, 5000, 7300)] + \
        [(u, 16730) for u in (7570, 10150, 12650, 15230)] + \
        [(u, 14530) for u in (18100, 20900, 23700, 26430)]

# ---- 대지 (기존 도면 좌표를 로컬로 변환)
BOUND_W = [LP(1790, 168), LP(1275, 285), LP(715, 352), LP(625, 330), LP(610, 425), LP(420, 575), LP(195, 710), LP(5, 1045)]
BOUND_S = [LP(0, 1250), LP(400, 1278), LP(620, 1305), LP(745, 1162), LP(640, 1085), LP(915, 940), LP(988, 975),
           LP(1270, 1048), LP(1590, 1093), LP(1740, 1095), LP(1790, 1130)]
ROAD = Polygon([LP(560, -300), LP(640, -300), LP(640, 240), LP(610, 425), LP(420, 575), LP(195, 710), LP(5, 1045), LP(-185, 1380),
                LP(-215, 1380), LP(35, 1010), LP(190, 715), LP(395, 530), LP(558, 365)]).buffer(0)
ROAD_PLANE = [0.2115 * UX[1], 0.2115 * NY[1], 0.2115 * O[1] + 519.0]
XE, XW, YS, YN = 46000, -42000, -48000, 42000
BOX = box(XW, YS, XE, YN)
def ext_e(pts):
    (ax, ay), (bx, by) = pts[-2], pts[-1]
    return list(pts) + [(XE + 2000, by + (by - ay) * (XE + 2000 - bx) / (bx - ax))]
L1 = ext_e([LP(625, 330), LP(715, 352), LP(1275, 285), LP(1815, 155)])
L2 = ext_e([LP(620, 388), LP(710, 415), LP(1280, 345), LP(1830, 218)])
WALL_L1 = LineString(L1).buffer(-600, single_sided=True, cap_style=2, join_style=2).intersection(BOX).difference(ROAD)
WALL_L2 = LineString(L2).buffer(-600, single_sided=True, cap_style=2, join_style=2).intersection(BOX).difference(ROAD)
_R = [LP(625, 330), LP(610, 425), LP(420, 575), LP(195, 710), LP(5, 1045), LP(-185, 1380)]
ROADSIDE = Polygon(_R + [(-90000, _R[-1][1]), (-90000, 90000), (_R[0][0], 90000)]).buffer(0)
SOUTH_L2 = Polygon([(-90000, -90000), (-90000, L2[0][1])] + L2 + [(XE + 2000, -90000)]).buffer(0)
# 새 옹벽선 (대지경계 안쪽 1.1~2m) — 서측·남측·동측
RW = [(-17500, -7700), (-17500, -16800), (2500, -16800), (4700, -15900), (7000, -17300), (14500, -20200), (34500, -20200), (34500, -11300)]
PADRAW = Polygon(RW + [(XE, -11800), (XE, 6000), (-17500, 6000)])
PADP = PADRAW.intersection(SOUTH_L2).difference(ROADSIDE).difference(ROAD).difference(WALL_L2).intersection(BOX).buffer(0)
RWALL = LineString(RW).buffer(-350, single_sided=True, cap_style=2, join_style=2).difference(ROADSIDE).difference(ROAD)
T1 = Polygon(L2 + list(reversed(L1))).buffer(0).difference(ROADSIDE).difference(ROAD).difference(WALL_L1).intersection(BOX)
T2 = Polygon(L1 + [(XE + 2000, 12000), LP(640, 40), LP(640, 240)]).buffer(0).difference(ROAD).intersection(BOX)
HILL = BOX.difference(unary_union([PADP, T1, T2, ROAD, WALL_L1, WALL_L2, RWALL]).buffer(1))

if __name__ == '__main__':
    tot = 0
    for k in ROOMS:
        a = room_poly(k).area / 1e6
        print(f'{k:16s} {a:6.1f} m2 ({a / 3.3058:4.1f}평)')
    print('난방면적(외곽)', round(HEATED.area / 1e6, 1), '차고', round(GAR.area / 1e6, 1), '합계', round(OUTLINE.area / 1e6, 1), '=', round(OUTLINE.area / 1e6 / 3.3058, 1), '평')
    print('PAD', round(PADP.area / 1e6), PADP.geom_type, 'T1', T1.geom_type, 'T2', T2.geom_type, 'HILL', HILL.geom_type, HILL.is_valid)
    print('outline', [(round(x), round(-y)) for x, y in OUTLINE.exterior.coords])

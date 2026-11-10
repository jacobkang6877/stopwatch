# -*- coding: utf-8 -*-
"""B안 재설계 — 설계 데이터 (mm). 원점: 좌측 블록(차고 위) 남서 외곽 모서리. x=동, y=북(도면 위쪽), z=지하 주차장 바닥."""
import json, math
from shapely.geometry import Polygon, LineString, box, Point
from shapely.ops import split, unary_union
from shapely import affinity

# ---------------------------------------------------------------- 기준
EXT = 250      # 외벽 두께
INT = 120      # 내벽 두께
Z_B1 = 0
Z_1F = 3000
Z_AT = 6000
H_1F = 2750    # 1층 벽 높이(슬래브 하부까지)

# 사선부(힌지) 좌표계: P3 기준, U = 북서면 방향, V = 실내(남동) 방향
P3 = (3768.0, 7300.0)
_th = math.atan2(6848, 7958)
U = (math.cos(_th), math.sin(_th))
V = (math.sin(_th), -math.cos(_th))

def W(u, v):
    return (P3[0] + u * U[0] + v * V[0], P3[1] + u * U[1] + v * V[1])

# 외곽선 (기존 1층 외곽을 유지, 남동면만 북서면과 평행하게 정리)
SE_END = (7549 + (9348 / U[1]) * U[0], 9348.0)          # (18412, 9348)
XJ = SE_END[0]
OUTLINE = Polygon([(0, 0), (7549, 0), SE_END, (32550, 9348), (32550, 14148),
                   (11726, 14148), P3, (0, 7300)])
INNER = OUTLINE.buffer(-EXT, join_style=2)
LEFT = box(0, 0, 7549, 7300)
WING = box(XJ, 9348, 32550, 14148)

def band_poly(u0, u1, v0, v1):
    return Polygon([W(u0, v0), W(u1, v0), W(u1, v1), W(u0, v1)])

def clip(p):
    return p.intersection(INNER)

# ---------------------------------------------------------------- 1층 실 구성
rooms_1f = {}
# 좌측 블록 (차고 위)
stair_zone = box(2040, 4800, 6260, 7050)
ev = box(250, 5250, 1980, 7050)
rooms_1f['EV'] = clip(ev)
# 현관: 사선부 남서 끝 (기존 주출입구 위치)
genkan = band_poly(0, 3300, 0, 2900).intersection(INNER)
genkan = genkan.difference(box(-1e5, -1e5, 6260, 7050))
rooms_1f['현관'] = genkan
landing = box(6260, 4800, 7549, 7300).intersection(INNER).difference(genkan)
# 북측 서비스 띠 (v 0~2900)
north = lambda u0, u1: clip(band_poly(u0, u1, 0, 2900))
rooms_1f['팬트리·세탁'] = north(3300, 6000)
rooms_1f['공용욕실'] = north(6000, 8400)
# 수납 (복도 꺾이는 곳의 삼각형 자투리)
CORR_Y = 12600
store = clip(band_poly(9800, 20000, 0, 2900)).intersection(box(-1e5, -1e5, 1e5, CORR_Y))
rooms_1f['수납'] = store
# 복도: 홀(u 8400~9800) + 날개로 이어지는 북측 갤러리 복도
hall = clip(band_poly(8400, 9800, 0, 2900))
gallery = clip(box(0, CORR_Y, 22200, 14148)).difference(box(-1e5, -1e5, XJ, 9348))
gallery = gallery.intersection(OUTLINE.buffer(-EXT, join_style=2))
gallery = gallery.difference(band_poly(-1e4, 9800, -1e4, 1e4))
rooms_1f['복도'] = unary_union([hall.buffer(2), gallery.buffer(2)]).buffer(-2)
# 남측 생활 띠 (LDK + 가족실)
ldk_region = unary_union([clip(box(250, 250, 7549, 4800)), landing,
                          clip(band_poly(-3000, 9800, 2900, 8000)),
                          clip(band_poly(-3000, 3300, 0, 2900))])
ldk_region = ldk_region.difference(box(-1e5, 4800, 6260, 1e5)).difference(genkan)
fam = clip(band_poly(9800, 20000, 2900, 8000)).intersection(box(-1e5, -1e5, XJ, CORR_Y))
liv = ldk_region.intersection(box(-1e5, -1e5, 7549, 1e5))
dk = ldk_region.difference(box(-1e5, -1e5, 7549, 1e5))
rooms_1f['계단·홀'] = clip(box(250, 4800, 6260, 7050)).difference(ev)
rooms_1f['거실'] = liv
DIN_U = 3300
dining = dk.intersection(band_poly(-6000, DIN_U, -1e4, 1e4))
rooms_1f['다이닝룸'] = dining
rooms_1f['주방·조식'] = dk.difference(dining)
rooms_1f['가족실·서재'] = fam
# 우측 날개
rooms_1f['침실2'] = box(XJ + INT / 2, 9348 + EXT, 22200, CORR_Y - INT / 2)
rooms_1f['안방'] = box(22200 + INT / 2, 9348 + EXT, 26500, 14148 - EXT)
rooms_1f['부부욕실'] = box(26500 + INT / 2, 9348 + EXT, 30100, 14148 - EXT)
rooms_1f['드레스룸'] = box(30100 + INT / 2, 9348 + EXT, 32550 - EXT, 14148 - EXT)

ZONE = {'현관': 'circ', '계단실': 'circ', '계단·홀': 'circ', '복도': 'circ', 'EV': 'circ',
        '거실': 'public', '다이닝룸': 'public', '주방·조식': 'public', '가족실·서재': 'public',
        '팬트리·세탁': 'service', '공용욕실': 'service', '부부욕실': 'service', '드레스룸': 'private',
        '침실2': 'private', '안방': 'private',
        '주차장': 'service', '창고': 'service', '다락(서재)': 'public', '다락 수납': 'service', '수납': 'service'}

# ---------------------------------------------------------------- 내벽 (중심선, 1층)
def bl(u, v):
    return W(u, v)

DIN_U = 3300

def _vline_u(u, y):
    # u=const 선이 y와 만나는 v
    return (y - P3[1] - u * U[1]) / V[1]

def _yline_v(v, y):
    # v=const 선이 y와 만나는 u
    return (y - P3[1] - v * V[1]) / U[1]

walls_1f_int = [
    LineString([bl(3300, 2900), bl(8400, 2900)]),   # 서비스 띠 | 주방
    LineString([bl(3300, 0), bl(3300, 2900)]),      # 현관 | 팬트리
    LineString([bl(6000, 0), bl(6000, 2900)]),      # 팬트리 | 욕실
    LineString([bl(8400, 0), bl(8400, 2900)]),      # 욕실 | 홀
    LineString([bl(9800, 2900), bl(9800, 8000)]),   # 다이닝 | 가족실 (미닫이)
    LineString([bl(9800, _vline_u(9800, CORR_Y)), bl(9800, 2900)]),  # 홀 | 수납
    LineString([bl(9800, 2900), bl(_yline_v(2900, CORR_Y), 2900)]),      # 가족실·수납 북측
    LineString([(W(9800, _vline_u(9800, CORR_Y))[0], CORR_Y), (22200, CORR_Y)]),  # 갤러리 복도 남측
    LineString([(XJ, 9348), (XJ, CORR_Y)]),
    LineString([(22200, 9348), (22200, 14148)]),
    LineString([(26500, 9348), (26500, 14148)]),
    LineString([(30100, 9348), (30100, 14148)]),
    LineString([(7549, 250), (7549, 4800)]),         # 거실 | 다이닝룸 (넓은 개구부)
    LineString([bl(DIN_U, 2900), bl(DIN_U, 8000)]),  # 다이닝룸 | 주방 (아치형 개구부)
    LineString([(250, 5250), (1980, 5250)]),        # EV (휠체어 대응 샤프트)
    LineString([(1980, 5250), (1980, 7050)]),
    LineString([(2040, 5925), (6260, 5925)]),       # 계단 사이 벽
]
# 가족실 북측 경계(v=2900)가 복도와 겹치는 부분 정리용으로 그대로 사용

# 문 (벽 위 위치: 점, 폭) — 내벽에서 개구부로 잘라냄
doors_1f = [
    (bl(4650, 2900), 1000),   # 팬트리 (주방에서)
    (bl(8400, 1600), 1000),   # 공용욕실 (홀에서)
    (bl(9800, 4700), 2000),  # 가족실 미닫이
    (bl(9800, 2400), 800),   # 수납
    ((20200, CORR_Y), 1000),  # 침실2
    ((22200, 13250), 1100),   # 안방
    ((26500, 13100), 1100),   # 안방 -> 부부욕실
    ((30100, 12900), 1000),   # 부부욕실 -> 드레스룸
    ((7549, 2600), 2800),    # 거실-다이닝 개구부
    (bl(DIN_U, 5200), 2000), # 다이닝-주방 개구부
    ((1100, 5250), 1000),    # EV
]

# ---------------------------------------------------------------- 외벽 개구부 (외곽선 변 번호별)
# 외곽 변: 0 남(좌측블록) 1 남동 사선 2 날개 남 3 날개 동 4 날개 북 5 북서 사선 6 좌측블록 북 7 좌측블록 서
# (s0, s1, sill, head, kind) — s는 변 시작점부터 거리
LEN = []
pts = list(OUTLINE.exterior.coords)
for i in range(len(pts) - 1):
    LEN.append(math.dist(pts[i], pts[i + 1]))

openings = {
    0: [(600, 3300, 450, 2600, 'win'), (3700, 6900, 450, 2600, 'win')],      # 거실 남측 전망창 + 상부 고창
    1: [(1200, 4400, 0, 2400, 'door'), (5200, 8800, 0, 2400, 'door'), (9800, 13400, 0, 2400, 'door')],
    2: [(700, 3100, 900, 2400, 'win'), (5000, 7800, 300, 2400, 'win'), (8900, 11300, 900, 2400, 'win'),
        (12200, 13300, 1500, 2300, 'win')],
    3: [(1800, 3000, 1500, 2300, 'win')],
    4: [(900, 1700, 1700, 2300, 'win'), (3000, 4500, 1700, 2300, 'win'), (6600, 8800, 900, 2400, 'win'),
        (10600, 13000, 300, 2400, 'win'), (15200, 18800, 300, 2400, 'win')],
    5: [(800, 1800, 1500, 2200, 'win'), (2900, 3900, 1500, 2200, 'win'), (5700, 6600, 0, 2200, 'door'),
        (7700, 8400, 0, 2400, 'win'), (8500, 9700, 0, 2400, 'door')],
    6: [(300, 1500, 1200, 2400, 'win')],
    7: [(3600, 6300, 900, 2400, 'win')],
}

# ---------------------------------------------------------------- 지하 / 다락
B1_BOX = box(0, 0, 7549, 7300)
rooms_b1 = {
    '주차장': box(250, 250, 7299, 5925).difference(box(0, 5250, 1980, 8000)),
    'EV': box(250, 5250, 1980, 7050),
    '계단실': box(1950, 5925, 7299, 7050),
}
rooms_at = {
    '다락(서재)': box(250, 250, 7299, 4800),
    '계단실': box(2040, 4800, 7299, 5925),
    '다락 수납': box(250, 4800, 2040, 7050).union(box(2040, 5925, 7299, 7050)),
}

def ring(poly):
    return [[round(x, 1), round(y, 1)] for x, y in list(poly.exterior.coords)[:-1]]

if __name__ == '__main__':
    tot = 0
    for k, p in rooms_1f.items():
        print(f'{k:10s} {p.area/1e6:6.1f} m2  {p.geom_type}')
        tot += p.area
    print('1F gross', OUTLINE.area / 1e6, 'net rooms', tot / 1e6)
    print('B1 gross', B1_BOX.area / 1e6, ' attic gross', LEFT.area / 1e6)
    print('SE_END', SE_END, 'edge lengths', [round(l) for l in LEN])

# -*- coding: utf-8 -*-
"""C안 실사 렌더 (Blender Cycles). 사용: python3 scene.py <prisms.json> <views.json> <outdir> [view names...]"""
import bpy, bmesh, json, math, sys, random, os, time
T0 = time.time()
def tick(m): print('TICK', m, round(time.time() - T0, 1), flush=True)
from mathutils import Vector

PRISMS, VIEWS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
ONLY = sys.argv[4:]
SAMPLES = int(os.environ.get('SAMPLES', '72'))
RES = (int(os.environ.get('RX', '1600')), int(os.environ.get('RY', '1000')))
S = 0.001
random.seed(11)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
D = json.load(open(PRISMS))

# ------------------------------------------------------------------ 재질
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    return m, nt, b
def N(nt, t, **kw):
    n = nt.nodes.new(t)
    for k, v in kw.items(): setattr(n, k, v)
    return n
def math_(nt, op, a, b=None, clamp=False):
    n = N(nt, 'ShaderNodeMath', operation=op, use_clamp=clamp)
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[0]
def pos_xyz(nt):
    g = N(nt, 'ShaderNodeNewGeometry'); s = N(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(g.outputs['Position'], s.inputs[0])
    return s.outputs[0], s.outputs[1], s.outputs[2], g
def along_wall(nt):
    """벽면을 따라가는 수평 좌표 t = x*|ny| + y*|nx|"""
    x, y, z, g = pos_xyz(nt)
    sn = N(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(g.outputs['Normal'], sn.inputs[0])
    ax = math_(nt, 'ABSOLUTE', sn.outputs[0]); ay = math_(nt, 'ABSOLUTE', sn.outputs[1])
    return math_(nt, 'ADD', math_(nt, 'MULTIPLY', x, ay), math_(nt, 'MULTIPLY', y, ax)), z
def rgb(nt, c):
    n = N(nt, 'ShaderNodeRGB'); n.outputs[0].default_value = (c[0], c[1], c[2], 1); return n.outputs[0]
def mixc(nt, fac, a, b):
    n = N(nt, 'ShaderNodeMix', data_type='RGBA')
    if isinstance(fac, (int, float)): n.inputs[0].default_value = fac
    else: nt.links.new(fac, n.inputs[0])
    for i, v in ((6, a), (7, b)):
        if isinstance(v, tuple): n.inputs[i].default_value = (v[0], v[1], v[2], 1)
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[2]
def bump(nt, bsdf, height, strength=0.5, dist=0.01):
    b = N(nt, 'ShaderNodeBump'); b.inputs['Strength'].default_value = strength; b.inputs['Distance'].default_value = dist
    nt.links.new(height, b.inputs['Height']); nt.links.new(b.outputs[0], bsdf.inputs['Normal'])
def noise(nt, scale, detail=4.0, vec=None, rough=0.55):
    n = N(nt, 'ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough
    if vec is not None: nt.links.new(vec, n.inputs['Vector'])
    else:
        g = N(nt, 'ShaderNodeNewGeometry'); nt.links.new(g.outputs['Position'], n.inputs['Vector'])
    return n.outputs[0]
def srgb(h):
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (f((h >> 16) & 255), f((h >> 8) & 255), f(h & 255))

MATS = {}
def simple(name, col, rough=0.8, metal=0.0, **kw):
    m, nt, b = new_mat(name); b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    MATS[name] = m; return m, nt, b

def m_siding():
    m, nt, b = new_mat('siding'); t, z = along_wall(nt)
    row = math_(nt, 'DIVIDE', z, 0.455)
    fr = math_(nt, 'FRACT', row)
    groove = math_(nt, 'LESS_THAN', fr, 0.045)
    off = math_(nt, 'MULTIPLY', math_(nt, 'FLOOR', row), 1.37)
    jt = math_(nt, 'LESS_THAN', math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'ADD', t, off), 3.03)), 0.0035)
    g = math_(nt, 'MAXIMUM', groove, jt)
    shade = math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, fr), 0.10)                     # 판마다 아래쪽이 살짝 어두움
    base = mixc(nt, noise(nt, 6.0, 3.0), srgb(0xefe9dd), srgb(0xe6dfd0))
    c = mixc(nt, g, mixc(nt, shade, base, srgb(0xbdb5a4)), srgb(0x8a8273))
    nt.links.new(c, b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.72
    bump(nt, b, math_(nt, 'SUBTRACT', 1.0, g), 0.9, 0.012); MATS['siding'] = m
def m_boards(name, mode, w=0.14, c1=0xa97c52, c2=0x8b6238, rough=0.6):
    """mode: 'wall'(세로널), 'x'(x 방향으로 줄), 'y'"""
    m, nt, b = new_mat(name)
    if mode == 'wall': t, z = along_wall(nt)
    else:
        x, y, z, g = pos_xyz(nt); t = x if mode == 'x' else y
    u = math_(nt, 'DIVIDE', t, w); fr = math_(nt, 'FRACT', u); bid = math_(nt, 'FLOOR', u)
    wn = N(nt, 'ShaderNodeTexWhiteNoise', noise_dimensions='1D'); nt.links.new(bid, wn.inputs['W'])
    gv = N(nt, 'ShaderNodeNewGeometry'); mp = N(nt, 'ShaderNodeMapping'); nt.links.new(gv.outputs['Position'], mp.inputs['Vector'])
    mp.inputs['Scale'].default_value = (38, 38, 2.2) if mode == 'wall' else ((2.2, 38, 38) if mode == 'y' else (38, 2.2, 38))
    grain = noise(nt, 1.0, 6.0, mp.outputs[0])
    col = mixc(nt, wn.outputs['Value'], srgb(c1), srgb(c2)); col = mixc(nt, math_(nt, 'MULTIPLY', grain, 0.45), col, srgb(0x4d3018))
    gr = math_(nt, 'LESS_THAN', fr, 0.05)
    nt.links.new(mixc(nt, gr, col, srgb(0x2a1a0e)), b.inputs['Base Color']); b.inputs['Roughness'].default_value = rough
    bump(nt, b, math_(nt, 'SUBTRACT', 1.0, gr), 0.7, 0.008); MATS[name] = m
def m_brick(name, mode, bw, rh, c1, c2, mortar, msize=0.012, rough=0.85, bstr=0.8):
    m, nt, b = new_mat(name)
    if mode == 'wall':
        t, z = along_wall(nt); cmb = N(nt, 'ShaderNodeCombineXYZ'); nt.links.new(t, cmb.inputs[0]); nt.links.new(z, cmb.inputs[1])
    else:
        x, y, z, g = pos_xyz(nt); cmb = N(nt, 'ShaderNodeCombineXYZ'); nt.links.new(x, cmb.inputs[0]); nt.links.new(y, cmb.inputs[1])
    br = N(nt, 'ShaderNodeTexBrick'); nt.links.new(cmb.outputs[0], br.inputs['Vector'])
    br.inputs['Scale'].default_value = 1.0; br.inputs['Brick Width'].default_value = bw; br.inputs['Row Height'].default_value = rh
    br.inputs['Mortar Size'].default_value = msize; br.inputs['Color1'].default_value = (*srgb(c1), 1); br.inputs['Color2'].default_value = (*srgb(c2), 1)
    br.inputs['Mortar'].default_value = (*srgb(mortar), 1); br.offset = 0.5 if mode == 'wall' else 0.0
    col = mixc(nt, math_(nt, 'MULTIPLY', noise(nt, 9.0, 5.0), 0.35), br.outputs['Color'], srgb(mortar))
    nt.links.new(col, b.inputs['Base Color']); b.inputs['Roughness'].default_value = rough
    bump(nt, b, math_(nt, 'SUBTRACT', 1.0, br.outputs['Fac']), bstr, 0.015); MATS[name] = m
def m_noise(name, c1, c2, scale, rough=0.95, bstr=0.3, big=None):
    m, nt, b = new_mat(name); n1 = noise(nt, scale, 8.0)
    col = mixc(nt, n1, srgb(c1), srgb(c2))
    if big: col = mixc(nt, math_(nt, 'MULTIPLY', noise(nt, big[0], 2.0), big[2]), col, srgb(big[1]))
    nt.links.new(col, b.inputs['Base Color']); b.inputs['Roughness'].default_value = rough
    if bstr: bump(nt, b, n1, bstr, 0.02)
    MATS[name] = m; return m, nt, b

m_siding()
m_boards('siding_wood', 'wall'); m_boards('gdoor', 'wall', 0.11, 0x9a6a40, 0x80552f); m_boards('soffit', 'x', 0.12, 0xb98d5e, 0xa0764a, 0.55)
m_boards('ceil_wood', 'x', 0.14, 0xc49a6a, 0xae8452, 0.5); m_boards('deck_wood', 'y', 0.14, 0xa98562, 0x8e6c4c, 0.7)
m_boards('fl_public', 'y', 0.19, 0xc9a678, 0xb48f62, 0.35); m_boards('fl_private', 'y', 0.19, 0xd6bc94, 0xc4a87e, 0.4)
m_boards('timber', 'x', 0.6, 0xa67c52, 0x94693f, 0.6); m_boards('door_wood', 'wall', 0.16, 0x7e5230, 0x6b4426, 0.5)
m_boards('fence', 'x', 3.0, 0xf2efe8, 0xe9e5db, 0.6); m_boards('cabinet_wood', 'wall', 0.45, 0xb08a62, 0xa07a54, 0.45); m_boards('chair', 'x', 0.5, 0x9a7650, 0x8a6844, 0.5)
m_brick('stone_wall', 'wall', 0.46, 0.2, 0x9a8f7c, 0x7f7667, 0x4b463d, 0.02, 0.9, 1.0)
m_brick('paving_stone', 'xy', 0.6, 0.6, 0xcfc8ba, 0xc4bcad, 0x8d877b, 0.008, 0.75, 0.3)
m_brick('court', 'xy', 1.2, 1.2, 0xc9c2b4, 0xc2bbad, 0x8f897d, 0.01, 0.8, 0.3)
m_brick('fl_service', 'xy', 0.6, 0.6, 0xd9d8d2, 0xd3d2cc, 0x9a9a95, 0.004, 0.35, 0.1)
m_noise('grass', 0x4f7a2c, 0x6f9440, 3.0, 0.95, 0.5, (0.12, 0x86984a, 0.45))
m_noise('gravel', 0xd9d4c8, 0x9c968a, 120.0, 0.9, 0.9)
m_noise('road', 0x8a8a88, 0x6e6e6c, 40.0, 0.85, 0.3)
m_noise('lavender', 0x7a69c2, 0x6f8f5a, 60.0, 1.0, 0.8); m_noise('hydrangea', 0x9fb6e8, 0x5f8a4a, 14.0, 1.0, 0.8)
m_noise('veg', 0x5fa244, 0x5a4332, 18.0, 1.0, 0.8); m_noise('fern', 0x6d9a4a, 0x49722f, 25.0, 1.0, 0.8); m_noise('hedge', 0x4a7435, 0x3c6229, 30.0, 1.0, 0.9)
m_noise('stone_plinth', 0x8f8a82, 0x7d7870, 25.0, 0.85, 0.4); m_noise('stone_dark', 0x55585a, 0x47494b, 30.0, 0.7, 0.3); m_noise('concrete', 0xbdbdb8, 0xb0b0aa, 12.0, 0.8, 0.2)
# 지형: 낮은 계곡 바닥은 논밭 색
m, nt, b = m_noise('hill', 0x3a5c22, 0x5f7f36, 0.5, 1.0, 0.0, (0.05, 0x7f8f48, 0.55))
m, nt, b = simple('aluzinc', srgb(0x565b61), 0.36, 0.95); MATS['seam'] = m; MATS['gutter'] = m
m, nt, b = new_mat('glass'); MATS['glass'] = m
tr = N(nt, 'ShaderNodeBsdfTransparent'); tr.inputs[0].default_value = (0.86, 0.93, 0.95, 1)
gl = N(nt, 'ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.02
fres = N(nt, 'ShaderNodeFresnel'); fres.inputs['IOR'].default_value = 1.5
mx = N(nt, 'ShaderNodeMixShader'); nt.links.new(math_(nt, 'ADD', math_(nt, 'MULTIPLY', fres.outputs[0], 1.6), 0.06, True), mx.inputs[0])
nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
m, nt, b = simple('water', srgb(0x2a4a58), 0.03); b.inputs['Transmission Weight'].default_value = 0.6; bump(nt, b, noise(nt, 6.0, 2.0), 0.08, 0.02)
m, nt, b = simple('lamp', (1.0, 0.75, 0.45), 0.4); b.inputs['Emission Color'].default_value = (1.0, 0.72, 0.42, 1); b.inputs['Emission Strength'].default_value = 3.0
for k, (c, r, mt) in {'frame': (0x1d1e20, 0.4, 0.6), 'door_gray': (0x4a4d50, 0.5, 0.3), 'partition': (0xf5f3ee, 0.9, 0), 'ceiling': (0xfaf8f4, 0.9, 0), 'fl_garage': (0xb9b7b0, 0.6, 0),
                      'cabinet': (0xf1efe9, 0.5, 0), 'counter': (0x3d4043, 0.25, 0), 'furniture': (0xbdb5a6, 0.8, 0), 'sofa': (0x8c9a8e, 0.95, 0), 'bed': (0xe9e4da, 0.95, 0),
                      'porcelain': (0xf8f8f6, 0.15, 0), 'car': (0x596069, 0.3, 0.7), 'car2': (0xb9bcc0, 0.3, 0.7), 'car_glass': (0x1a2028, 0.05, 0.2), 'metal': (0xb5b8ba, 0.4, 0.8),
                      'trunk': (0x5a4533, 0.9, 0), 'bamboo': (0x93a860, 0.6, 0), 'copper': (0x9c5f3a, 0.35, 0.9), 'pot': (0x4e3528, 0.35, 0), 'neighbor': (0xd9d6cd, 0.85, 0),
                      'neighbor_roof': (0x6d7175, 0.6, 0.3)}.items():
    simple(k, srgb(c), r, mt)
# 잎: 꼭짓점 색 사용
m, nt, b = new_mat('foliage'); at = N(nt, 'ShaderNodeAttribute', attribute_name='Col')
nt.links.new(mixc(nt, math_(nt, 'MULTIPLY', noise(nt, 2.5, 3.0), 0.35), at.outputs['Color'], (0.02, 0.05, 0.01)), b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.9
b.inputs['Subsurface Weight'].default_value = 0.0; MATS['foliage'] = m

# ------------------------------------------------------------------ 프리즘 -> 메시
zp = lambda pl, x, y: pl[0] * x + pl[1] * y + pl[2]
buckets = {}
crowns = []
for p in D['prisms']:
    if p['m'].startswith('crown_'): crowns.append(p); continue
    if p['n'].startswith('GuestCar'): continue
    key = (p['g'], p['m'])
    vs, fs = buckets.setdefault(key, ([], []))
    n = len(p['p']); o = len(vs)
    for x, y in p['p']: vs.append((x * S, y * S, zp(p['zb'], x, y) * S))
    for x, y in p['p']: vs.append((x * S, y * S, zp(p['zt'], x, y) * S))
    fs.append([o + i for i in range(n - 1, -1, -1)]); fs.append([o + n + i for i in range(n)])
    for i in range(n):
        j = (i + 1) % n; fs.append([o + i, o + j, o + n + j, o + n + i])
GROUP_OBJS = {}
for (g, mname), (vs, fs) in buckets.items():
    me = bpy.data.meshes.new(f'{g}_{mname}'); me.from_pydata(vs, [], fs); me.update()
    ob = bpy.data.objects.new(me.name, me); sc.collection.objects.link(ob)
    ob.data.materials.append(MATS.get(mname) or simple(mname, (0.7, 0.7, 0.7))[0])
    GROUP_OBJS.setdefault(g, []).append(ob)

tick('prisms')
# ------------------------------------------------------------------ 나무 수관 (불규칙한 덩어리)
import numpy as np
_TPL = {}
def _tpl(subdiv):
    if subdiv not in _TPL:
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0); bm.verts.ensure_lookup_table()
        _TPL[subdiv] = (np.array([v.co[:] for v in bm.verts], dtype=np.float32), np.array([[v.index for v in f.verts] for f in bm.faces], dtype=np.int32)); bm.free()
    return _TPL[subdiv]
def add_blobs(name, blobs, subdiv=2, jitter=0.16):
    tv, tf = _tpl(subdiv); nv, nf = len(tv), len(tf); nb = len(blobs)
    rng = np.random.default_rng(5)
    B_ = np.array([b[:6] for b in blobs], dtype=np.float32); C_ = np.array([b[6] for b in blobs], dtype=np.float32)
    k = 1.0 + (rng.random((nb, nv, 1), dtype=np.float32) - 0.5) * 2 * jitter
    V = B_[:, None, 0:3] + tv[None, :, :] * B_[:, None, 3:6] * k
    F = tf[None, :, :] + (np.arange(nb, dtype=np.int32) * nv)[:, None, None]
    me = bpy.data.meshes.new(name)
    me.vertices.add(nb * nv); me.vertices.foreach_set('co', V.reshape(-1))
    me.loops.add(nb * nf * 3); me.loops.foreach_set('vertex_index', F.reshape(-1))
    me.polygons.add(nb * nf); me.polygons.foreach_set('loop_start', np.arange(0, nb * nf * 3, 3, dtype=np.int32)); me.polygons.foreach_set('loop_total', np.full(nb * nf, 3, dtype=np.int32))
    me.polygons.foreach_set('use_smooth', np.ones(nb * nf, dtype=bool)); me.update(calc_edges=True)
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    shade = 0.8 + rng.random((nb, nv, 1), dtype=np.float32) * 0.4
    col = np.concatenate([C_[:, None, :] * shade, np.ones((nb, nv, 1), dtype=np.float32)], axis=2)
    ca.data.foreach_set('color', col.reshape(-1))
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); ob.data.materials.append(MATS['foliage']); return ob
CK = {'zelkova': [(0.20, 0.38, 0.09), (0.26, 0.45, 0.12), (0.16, 0.32, 0.08)], 'maple': [(0.55, 0.10, 0.04), (0.65, 0.18, 0.05), (0.42, 0.07, 0.03)],
      'pine': [(0.05, 0.16, 0.07), (0.07, 0.20, 0.08)], 'bamboo': [(0.30, 0.45, 0.12), (0.36, 0.52, 0.16)]}
blobs = []
for p in crowns:
    kind = p['m'][6:]; xs = [q[0] for q in p['p']]; ys = [q[1] for q in p['p']]
    cx, cy, r = (min(xs) + max(xs)) / 2 * S, (min(ys) + max(ys)) / 2 * S, (max(xs) - min(xs)) / 2 * S
    zb, zt = p['zb'][2] * S, p['zt'][2] * S; cols = CK.get(kind, CK['zelkova'])
    if kind == 'pine':
        for i in range(6):
            f = i / 5.0; blobs.append((cx, cy, zb + (zt - zb) * (0.1 + 0.85 * f), r * (1.05 - 0.8 * f), r * (1.05 - 0.8 * f), r * 0.42, cols[i % 2]))
    else:
        nb = 7 if kind == 'bamboo' else 16
        for i in range(nb):
            a = random.random() * 6.283; rr = (0.62 * r * math.sqrt(random.random())) if i else 0
            sr = r * (0.42 + 0.28 * random.random())
            blobs.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr, zb + (zt - zb) * (0.3 + 0.55 * random.random()), sr, sr, sr * (1.25 if kind == 'bamboo' else 0.78), cols[i % len(cols)]))
GROUP_OBJS.setdefault('Site', []).append(add_blobs('TreeCrowns', blobs))
# 관목 (포치·보행로 주변)
sh = []
for (u, d, r) in [(-6900, 15500, 380), (4300, 15500, 380), (7400, 17050, 420), (15400, 17050, 420), (15150, 14950, 350), (26650, 17300, 400), (31900, 17300, 400),
                  (-7150, 13000, 420), (-7150, 6000, 420), (2600, 5300, 380), (8000, 5250, 360), (15500, 5250, 360), (20600, 5250, 360), (26800, 5250, 360), (32350, 9000, 420), (32350, 12300, 420)]:
    sh.append((u * S, -d * S, 2.88 + r * S * 0.75, r * S, r * S, r * S * 0.8, (0.14, 0.30, 0.08)))
GROUP_OBJS['Site'].append(add_blobs('Shrubs', sh, 2, 0.12))

# ------------------------------------------------------------------ 주변 지형 + 숲 (가상)
BX0, BY0, BX1, BY1 = -42.0, -48.0, 46.0, 42.0
def sm(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)
def terr(x, y):
    dout = max(BX0 - x, x - BX1, BY0 - y, y - BY1, 0.0); w = sm(0, 140, dout)
    if y > -114: h = 4.47 + 0.18 * y
    elif y > -300: h = -16.05
    else: h = -16.05 + 0.55 * (-300 - y)
    if y > 60: h += 0.0032 * (y - 60) ** 2
    sx = max(0.0, abs(x - 2) - 95); h += min(0.0034 * sx * sx, 190)
    h += w * (math.sin(x * 0.021 + 1.3) * math.cos(y * 0.019) * 9 + math.sin(x * 0.008 + y * 0.011) * 18 + math.sin(x * 0.05) * math.sin(y * 0.045) * 3)
    return min(h, 330.0)
def lin(a, b, n): return [a + (b - a) * i / n for i in range(n + 1)]
xs = lin(-1500, BX0, 80)[:-1] + lin(BX0, BX1, 10)[:-1] + lin(BX1, 1500, 80)
ys = lin(-1500, BY0, 80)[:-1] + lin(BY0, BY1, 10)[:-1] + lin(BY1, 1500, 80)
vs = [(x, y, terr(x, y)) for x in xs for y in ys]; ny = len(ys); fs = []
for i in range(len(xs) - 1):
    for j in range(ny - 1):
        if xs[i] >= BX0 - 1e-6 and xs[i + 1] <= BX1 + 1e-6 and ys[j] >= BY0 - 1e-6 and ys[j + 1] <= BY1 + 1e-6: continue
        fs.append([i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1])
me = bpy.data.meshes.new('Terrain'); me.from_pydata(vs, [], fs); me.update()
for poly in me.polygons: poly.use_smooth = True
tob = bpy.data.objects.new('Terrain', me); sc.collection.objects.link(tob)
m, nt, b = new_mat('terrain'); x, y, z, g = pos_xyz(nt)
fld = math_(nt, 'LESS_THAN', z, -15.9)
gcol = mixc(nt, noise(nt, 0.5, 6.0), srgb(0x34561f), srgb(0x55783a)); fcol = mixc(nt, noise(nt, 0.02, 1.0), srgb(0xa9b860), srgb(0x7fa04c))
nt.links.new(mixc(nt, fld, gcol, fcol), b.inputs['Base Color']); b.inputs['Roughness'].default_value = 1.0; tob.data.materials.append(m)
ROAD = [(p[0] * S, p[1] * S) for p in D['road']]
def dseg(x, y, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]; t = max(0, min(1, ((x - a[0]) * vx + (y - a[1]) * vy) / (vx * vx + vy * vy))); return math.hypot(x - a[0] - t * vx, y - a[1] - t * vy)
def near_road(x, y):
    for i in range(5):
        if dseg(x, y, ROAD[i], ROAD[i + 1]) < 7: return True
    return dseg(x, y, ROAD[0], ROAD[6]) < 7 or dseg(x, y, ROAD[6], ROAD[7]) < 7
fb = []
cnt = 0
while cnt < int(os.environ.get('TREES', '22000')):
    R = 40 + (random.random() ** 0.8) * 760; th = random.random() * 6.283; x = 8 + math.cos(th) * R; y = -10 + math.sin(th) * R
    if -24 < x < 50 and -33 < y < 14: continue
    if near_road(x, y): continue
    h = terr(x, y)
    if h < -15.5 and random.random() < 0.94: continue
    if -114 < y < -20 and abs(x - 10) < 45 and random.random() < 0.8: continue
    s = 1.5 + random.random() * 1.9; cnt += 1
    if random.random() < 0.4:
        c = (0.02 + random.random() * 0.015, 0.075 + random.random() * 0.035, 0.03)
        for i in range(3): fb.append((x, y, h + s * (0.9 + 1.0 * i), s * (0.85 - 0.25 * i), s * (0.85 - 0.25 * i), s * 0.75, c))
    else:
        c = (0.05 + random.random() * 0.05, 0.15 + random.random() * 0.08, 0.03 + random.random() * 0.02)
        fb.append((x, y, h + s * 1.0, s * 1.1, s * 1.1, s * 1.2, c))
        fb.append((x + s * 0.5, y + s * 0.3, h + s * 0.7, s * 0.8, s * 0.8, s * 0.85, c))
add_blobs('Forest', fb, 1, 0.3)

tick('forest')
# ------------------------------------------------------------------ 손님 차 (간단한 형태 + 바퀴)
def car(x0, y0, mat):
    def boxo(name, cx, cy, cz, sx, sy, sz, m, bev=0.12):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz)); o = bpy.context.object; o.scale = (sx, sy, sz); o.name = name
        md = o.modifiers.new('b', 'BEVEL'); md.width = bev; md.segments = 3; o.data.materials.append(MATS[m])
        for p_ in o.data.polygons: p_.use_smooth = True
        return o
    boxo('carbody', x0 + 2.4, y0 + 0.95, 2.85 + 0.72, 4.7, 1.86, 0.68, mat)
    boxo('carcabin', x0 + 2.55, y0 + 0.95, 2.85 + 1.28, 2.7, 1.66, 0.62, 'car_glass', 0.2)
    for dx in (0.85, 3.9):
        for dy in (0.12, 1.78):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.34, depth=0.24, location=(x0 + dx, y0 + dy, 2.85 + 0.36), rotation=(math.pi / 2, 0, 0)); bpy.context.object.data.materials.append(MATS['frame'])
car(-17.2, -12.3, 'car'); car(-17.2, -14.8, 'car2')

# ------------------------------------------------------------------ 하늘·해·실내등
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
wnt = w.node_tree; bg = wnt.nodes['Background']; sky = wnt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'MULTIPLE_SCATTERING'
wnt.links.new(sky.outputs[0], bg.inputs[0])
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); sc.collection.objects.link(sun)
sun.data.angle = math.radians(1.2)
def set_sun(az_deg, el_deg, strength, sky_strength, color=(1.0, 0.94, 0.86)):
    el, az = math.radians(el_deg), math.radians(az_deg)
    d = Vector((math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el)))      # 해가 있는 방향 (az: 북=0, 동=90)
    sun.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); sun.data.energy = strength; sun.data.color = color
    sky.sun_elevation = max(el, math.radians(-3)); sky.sun_rotation = az; sky.sun_disc = False; bg.inputs[1].default_value = sky_strength
LIGHTS = []
for (u, d, zz, pw) in [(11400, 12000, 5.9, 1.0), (11400, 8200, 5.9, 0.8), (18000, 9000, 5.9, 1.0), (2200, 10700, 5.4, 0.5), (5300, 7400, 5.4, 0.5), (22600, 9800, 5.4, 0.5),
                       (29100, 14200, 5.4, 0.7), (30200, 9800, 5.4, 0.4), (-3600, 9400, 7.7, 0.45), (-3400, 9400, 5.4, 0.5), (23600, 6500, 5.4, 0.3), (1500, 7400, 5.4, 0.3)]:
    L = bpy.data.objects.new('L', bpy.data.lights.new('L', 'POINT')); sc.collection.objects.link(L); L.location = (u * S, -d * S, zz)
    L.data.color = (1.0, 0.80, 0.58); L.data.shadow_soft_size = 0.12; LIGHTS.append((L, pw))

# ------------------------------------------------------------------ 렌더 설정
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.05; sc.cycles.max_bounces = 4; sc.cycles.glossy_bounces = 2; sc.cycles.diffuse_bounces = 2
sc.cycles.transmission_bounces = 2; sc.cycles.transparent_max_bounces = 8; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
sc.render.resolution_x, sc.render.resolution_y = RES; sc.render.use_persistent_data = True
sc.view_settings.view_transform = 'AgX'
try: sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.clip_start = 0.1; cam.data.clip_end = 6000; cam.data.sensor_fit = 'VERTICAL'
os.makedirs(OUT, exist_ok=True)
import bpy_extras.object_utils as ou
proj = {}
for v in json.load(open(VIEWS)):
    if ONLY and v['file'] not in ONLY: continue
    for g, obs in GROUP_OBJS.items():
        for o in obs: o.hide_render = g in v.get('hide', [])
    e = Vector([c * S for c in v['eye']]); t = Vector([c * S for c in v['target']])
    cam.location = e; cam.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler(); cam.data.angle_y = math.radians(v['fov'])
    mode = v.get('mode', 'day')
    if mode == 'dusk':
        set_sun(262, 2.0, 0.5, 0.16, (1.0, 0.5, 0.25)); lp, ls = 700.0, 40.0
    elif mode == 'interior':
        set_sun(215, 42, 4.5, 0.32); lp, ls = 420.0, 4.0
    else:
        set_sun(v.get('az', 222), v.get('el', 40), 4.2, 0.30); lp, ls = 40.0, 3.0
    for L, pw in LIGHTS: L.data.energy = lp * pw
    MATS['lamp'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = ls
    sc.view_settings.exposure = v.get('exposure', 0.0)
    sc.cycles.samples = int(SAMPLES * v.get('sm', 1.0))
    sc.render.filepath = os.path.join(OUT, v['file'] + '.png')
    bpy.context.view_layer.update()
    tick('render start')
    bpy.ops.render.render(write_still=True)
    if v.get('labels'):
        proj[v['file']] = [[L['t']] + list(ou.world_to_camera_view(sc, cam, Vector((L['x'] * S, L['y'] * S, (L['z'] + 250) * S)))) for L in D['labels']]
    tick('DONE ' + v['file'])
json.dump(proj, open(os.path.join(OUT, 'labels.json'), 'w'), ensure_ascii=False)

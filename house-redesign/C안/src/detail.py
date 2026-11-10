# -*- coding: utf-8 -*-
"""반복 디테일 생성기 (순수 파이썬, 외부 모듈 없음 — SketchUp 샌드박스에서도 같은 코드 사용).
행 형식: [이름, 그룹, 재질, [x0,y0,x1,y1,...], 밑면, 윗면]  (면은 상수 z 또는 [a,b,c] 평면)"""
import math

def gen_details(spec):
    rows = []
    def rect(px, py, ex, ey, nx, ny, s0, s1, a0, a1):
        return [px + ex * s0 + nx * a0, py + ey * s0 + ny * a0, px + ex * s1 + nx * a0, py + ey * s1 + ny * a0,
                px + ex * s1 + nx * a1, py + ey * s1 + ny * a1, px + ex * s0 + nx * a1, py + ey * s0 + ny * a1]
    # 1) 거멀접기 지붕 솔기
    k = 0
    for reg in spec['roofs']:
        pts, pl, grp, th, sp = reg['p'], reg['pl'], reg['g'], reg['th'], reg['sp']
        n = math.hypot(pl[0], pl[1])
        gx, gy = pl[0] / n, pl[1] / n
        qx, qy = -gy, gx
        ss = [x * qx + y * qy for x, y in pts]
        tt = [x * gx + y * gy for x, y in pts]
        s = min(ss) + sp * 0.5
        m = len(pts)
        while s < max(ss):
            cuts = []
            for i in range(m):
                j = (i + 1) % m
                if (ss[i] - s) * (ss[j] - s) < 0:
                    cuts.append(tt[i] + (s - ss[i]) / (ss[j] - ss[i]) * (tt[j] - tt[i]))
            cuts = sorted(cuts)
            for c in range(len(cuts) // 2):
                t0, t1 = cuts[2 * c] + 25, cuts[2 * c + 1] - 25
                if t1 - t0 > 120:
                    k += 1
                    rows.append(['Seam_' + str(k), grp, 'seam', rect(0, 0, gx, gy, qx, qy, t0, t1, s - 14, s + 14),
                                 [pl[0], pl[1], pl[2] + th], [pl[0], pl[1], pl[2] + th + 32]])
            s += sp
    # 2) 창호 프레임·멀리언·창대석
    k = 0
    for o in spec['frames']:
        x0, y0, x1, y1, nx, ny, zs, zh, nm, st = o
        Lo = math.hypot(x1 - x0, y1 - y0)
        ex, ey = (x1 - x0) / Lo, (y1 - y0) / Lo
        k += 1
        nmb = 'Frame_' + str(k)
        for (a, b) in [(0, 60), (Lo - 60, Lo)]:
            rows.append([nmb + '_J', '1F', 'frame', rect(x0, y0, ex, ey, nx, ny, a, b, 75, 185), zs, zh])
        for i in range(nm):
            c = Lo * (i + 1) / (nm + 1)
            rows.append([nmb + '_M', '1F', 'frame', rect(x0, y0, ex, ey, nx, ny, c - 25, c + 25, 85, 175), zs + 60, zh - 60])
        rows.append([nmb + '_B', '1F', 'frame', rect(x0, y0, ex, ey, nx, ny, 60, Lo - 60, 75, 185), zs, zs + 60])
        rows.append([nmb + '_T', '1F', 'frame', rect(x0, y0, ex, ey, nx, ny, 60, Lo - 60, 75, 185), zh - 60, zh])
        if st:
            rows.append([nmb + '_Sill', '1F', 'stone_plinth', rect(x0, y0, ex, ey, nx, ny, -60, Lo + 60, -45, 75), zs - 55, zs])
    # 3) 목장형 울타리
    k = 0
    for f in spec['fences']:
        pts, zb = f['p'], f['z']
        for i in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            Ls = math.hypot(bx - ax, by - ay)
            ex, ey = (bx - ax) / Ls, (by - ay) / Ls
            nseg = max(1, int(round(Ls / 2400.0)))
            for j in range(nseg + (1 if i == len(pts) - 2 else 0)):
                c = Ls * j / nseg
                k += 1
                rows.append(['Fence_Post_' + str(k), 'Site', 'fence', rect(ax, ay, ex, ey, -ey, ex, c - 45, c + 45, -45, 45), zb, zb + 1120])
            for h in (430, 930):
                k += 1
                rows.append(['Fence_Rail_' + str(k), 'Site', 'fence', rect(ax, ay, ex, ey, -ey, ex, 0, Ls, -18, 18), zb + h, zb + h + 85])
    # 4) 의자
    k = 0
    for c in spec['chairs']:
        cx, cy, rot, z0, grp = c
        ex, ey = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        k += 1
        rows.append(['Chair_' + str(k) + '_Seat', grp, 'chair', rect(cx, cy, ex, ey, -ey, ex, -220, 220, -220, 220), z0 + 400, z0 + 450])
        rows.append(['Chair_' + str(k) + '_Back', grp, 'chair', rect(cx, cy, ex, ey, -ey, ex, -220, 220, 180, 220), z0 + 450, z0 + 880])
        for (a, b) in [(-200, -200), (160, -200), (-200, 160), (160, 160)]:
            rows.append(['Chair_' + str(k) + '_Leg', grp, 'chair', rect(cx, cy, ex, ey, -ey, ex, a, a + 40, b, b + 40), z0, z0 + 400])
    return rows

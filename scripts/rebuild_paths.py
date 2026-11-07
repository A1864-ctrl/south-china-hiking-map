# -*- coding: utf-8 -*-
"""重建徒步轨迹 path：从「关键点直连」改为「贴合里程的盘山折线」。

问题：原 path 只把关键点直连，53 条路线里 51 条的折线长度只有标注里程的
0.1~0.8 倍 —— 相当于把盘山路抄成了直线，地图上看就是「轨迹穿山而过」。

做法：
1. 逐段（相邻关键点之间）生成带横向摆动的折线，端点严格落在关键点上；
2. 用二分法调振幅，使折线总长逼近标注里程（真实盘山路的长度特征）；
3. 摆动幅度硬性限制在 700 m 内，且不超过段长 90%，避免线路乱飞；
4. 对每个采样点做「是否落在水面」检查，命中则反相 / 缩幅重试；
5. 沿海路线（东西冲 / 黑排角 / 大鹿港）保留人工描的海岸线，只做轻微加密。

用法：python scripts/rebuild_paths.py [--dry]
"""
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import check_water as cw  # noqa: E402

SRC = os.path.join(ROOT, 'src', 'data', 'routes.js')

# 人工描过真实岸线，保留原折线，只加密不摆动
COAST_KEEP = {'东西冲海岸线', '黑排角海岸线', '大鹿港海岸线'}

STEP_KM = 0.035          # 采样间隔
AMP_CAP_M = 700.0        # 横向摆动上限
AMP_MIN_M = 12.0


def hav_km(a, b):
    R = 6371.0
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    x = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def polyline_km(pts):
    return sum(hav_km(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def meander(a, b, amp_m, waves, sign, n):
    """a→b 之间生成一条正弦摆动折线（单位：度），端点严格落在 a、b。

    在「公里平面」（X=lng·kx, Y=lat·ky）里做法向量偏移，避免经纬度各向异性。
    """
    lat_mid = (a[0] + b[0]) / 2
    kx = 111.32 * math.cos(math.radians(lat_mid))
    ky = 110.57
    ax, ay = a[1] * kx, a[0] * ky
    bx, by = b[1] * kx, b[0] * ky
    dX, dY = bx - ax, by - ay
    L = math.hypot(dX, dY) or 1e-6
    uX, uY = dX / L, dY / L          # 单位切向量
    nX, nY = -uY, uX                 # 单位法向量
    out = []
    for k in range(n + 1):
        s = k / n
        env = math.sin(math.pi * s) ** 0.65      # 端点收口
        off_km = sign * (amp_m / 1000.0) * env * math.sin(2 * math.pi * waves * s)
        X = ax + dX * s + nX * off_km
        Y = ay + dY * s + nY * off_km
        out.append((round(Y / ky, 5), round(X / kx, 5)))
    return out


def build_segment(a, b, target_km, sign=1):
    d = hav_km(a, b)
    if d < 0.02:
        return [a, b], d
    waves = max(2, min(26, round(target_km / max(d, 0.05) * 2.0)))
    # 采样点必须密于摆动的 5 倍，否则正弦会被采样抹平
    n = max(waves * 6, min(360, int(target_km / STEP_KM) + 6))
    lo, hi = 0.0, min(AMP_CAP_M, d * 1000 * 0.9)
    best = meander(a, b, 0.0, waves, sign, n)
    if target_km <= d * 1.015:
        return best, polyline_km(best)
    # 二分振幅
    for _ in range(18):
        mid = (lo + hi) / 2
        cand = meander(a, b, mid, waves, sign, n)
        L = polyline_km(cand)
        if L < target_km:
            lo = mid
        else:
            hi = mid
        best = cand
    # 复算最终长度
    L = polyline_km(best)
    return best, L


def densify(path, step_km=0.02):
    out = []
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        d = hav_km(a, b)
        n = max(2, int(d / step_km) + 1)
        for k in range(n):
            t = k / n
            out.append((round(a[0] + (b[0] - a[0]) * t, 5), round(a[1] + (b[1] - a[1]) * t, 5)))
    out.append(tuple(path[-1]))
    return out


def water_hits(path, every=3):
    bad = 0
    tot = 0
    for i in range(0, len(path), every):
        rgb = cw.sample(path[i][0], path[i][1], z=16, k=2)
        if rgb is None:
            continue
        tot += 1
        if cw.is_water(rgb):
            bad += 1
    return bad, tot


def fmt_path(path):
    parts = ['[%s,%s]' % (('%.4f' % p[0]).rstrip('0').rstrip('.'),
                          ('%.4f' % p[1]).rstrip('0').rstrip('.')) for p in path]
    lines, cur = [], '    path: ['
    for i, p in enumerate(parts):
        piece = p + (',' if i < len(parts) - 1 else '')
        if len(cur) + len(piece) > 104:
            lines.append(cur)
            cur = '      ' + piece
        else:
            cur += piece
    lines.append(cur + ']')
    return '\n'.join(lines)


def main():
    dry = '--dry' in sys.argv
    src = open(SRC, encoding='utf-8').read()
    heads = [(m.start(), m.group(1)) for m in re.finditer(r"\n  \{\n    name: '([^']+)', province:", src)]
    blocks = []
    for i, (st, name) in enumerate(heads):
        en = src.find('\n  },', st)
        blocks.append((st, en + len('\n  },'), name))

    report = []
    out = src
    for st, en, name in reversed(blocks):
        block = out[st:en]
        dm = re.search(r'distance: ([\d.]+)', block)
        target = float(dm.group(1)) if dm else 0
        pts = [(float(x), float(y)) for x, y in re.findall(
            r"name: '[^']+', lat: ([\d.]+), lng: ([\d.]+)", block)]
        pm = re.search(r'path: (\[\[.*?\]\])', block, re.S)
        old = json.loads(pm.group(1)) if pm else []
        if len(pts) < 2:
            continue

        if name in COAST_KEEP:
            new = densify(old or pts)
            note = '保留岸线'
        else:
            straight = sum(hav_km(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) or target
            segs = []
            acc = []
            for i in range(len(pts) - 1):
                d = hav_km(pts[i], pts[i + 1])
                share = max(d, 0.15) / max(straight, 0.15)
                seg_target = max(d * 1.02, target * share)
                seg, L = build_segment(pts[i], pts[i + 1], seg_target, sign=1)
                bad, tot = water_hits(seg)
                if tot and bad / tot > 0.12:
                    seg2, L2 = build_segment(pts[i], pts[i + 1], seg_target, sign=-1)
                    b2, t2 = water_hits(seg2)
                    if t2 and b2 / t2 < bad / tot:
                        seg, L, bad = seg2, L2, b2
                acc.extend(seg[:-1])
                segs.append(L)
            acc.append(pts[-1])
            # 全串水检 → 命中多则整体缩幅重来一次
            new = acc
            note = ''
            bad, tot = water_hits(new, every=2)
            if tot and bad / tot > 0.06:
                new = densify(pts, 0.03)
                note = '缩幅兜底'
        L = polyline_km(new)
        ratio = L / target if target else 0
        report.append({'name': name, 'pts': len(pts), 'target': target,
                       'oldLen': round(polyline_km(old), 1), 'newLen': round(L, 1),
                       'ratio': round(ratio, 2), 'n': len(new), 'note': note})
        if not dry:
            out = out[:st] + block.replace(pm.group(0), fmt_path(new)) + out[en:]

    if not dry:
        open(SRC, 'w', encoding='utf-8').write(out)
    json.dump(report, open(os.path.join(ROOT, 'scripts', 'rebuild_report.json'), 'w',
                           encoding='utf-8'), ensure_ascii=False, indent=1)
    bad = [r for r in report if abs(r['ratio'] - 1) > 0.15]
    for r in sorted(report, key=lambda r: r['ratio']):
        print('%-22s 标注%6.1f 原%6.1f 新%6.1f 比%.2f 点%3d %s'
              % (r['name'], r['target'], r['oldLen'], r['newLen'], r['ratio'], r['n'], r['note']))
    print('总 %d 条，里程比偏差>15%% 的 %d 条%s' % (len(report), len(bad), '（dry run）' if dry else ''))


if __name__ == '__main__':
    main()

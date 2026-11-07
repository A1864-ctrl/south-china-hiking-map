# -*- coding: utf-8 -*-
"""把追踪到的真实路网轨迹写回 routes.js。

以追踪折线为主干：
- 里程已经接近标注值（0.85~1.35）→ 直接用；
- 偏短 → 沿主干加小幅横向摆动（≤180 m）把里程补到标注值，主干走向不变；
- 偏长 → 直接用（说明真实路网绕行更远）；
- 没有追踪结果的路线 → 保留原 path。
"""
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import check_water as cw  # noqa: E402
from rebuild_paths import fmt_path, hav_km, polyline_km, water_hits  # noqa: E402

SRC = os.path.join(ROOT, 'src', 'data', 'routes.js')
COAST_KEEP = {'东西冲海岸线', '黑排角海岸线', '大鹿港海岸线'}
TRACES = os.path.join(ROOT, 'scripts', 'traces')
STEP = 0.02
AMP_CAP = 210.0


def densify(path, step_km=STEP):
    out = []
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        d = hav_km(a, b)
        n = max(1, int(d / step_km))
        for k in range(n):
            t = k / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    out.append(tuple(path[-1]))
    return out


def resample(path, ds_km=0.008):
    """按固定间距重采样，保证能表达高频摆动。"""
    out = [(path[0][0], path[0][1])]
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        d = hav_km(a, b)
        n = max(1, int(d / ds_km))
        for k in range(1, n + 1):
            t = k / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def wiggle(spine, amp_m, wave_km=0.09, sign=1):
    """沿主干叠加正弦横摆：波长 90 m 左右，端点收口。"""
    pts = resample(spine)
    # 累计里程
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + hav_km(pts[i - 1], pts[i]))
    total = cum[-1] or 1e-6
    out = []
    for i, p in enumerate(pts):
        if i == 0 or i == len(pts) - 1:
            out.append(p)
            continue
        a, b = pts[i - 1], pts[i + 1]
        lat_mid = p[0]
        kx = 111.32 * math.cos(math.radians(lat_mid))
        ky = 110.57
        ax, ay = a[1] * kx, a[0] * ky
        bx, by = b[1] * kx, b[0] * ky
        dX, dY = bx - ax, by - ay
        L = math.hypot(dX, dY)
        if L < 1e-9:
            out.append(p)
            continue
        nX, nY = -dY / L, dX / L
        s = cum[i]
        env = min(1.0, s / 0.25, (total - s) / 0.25)     # 首尾 250 m 收口
        off = sign * (amp_m / 1000.0) * env * math.sin(2 * math.pi * s / wave_km)
        X, Y = p[1] * kx + nX * off, p[0] * ky + nY * off
        out.append((Y / ky, X / kx))
    return out


def fit_length(spine, target):
    """先粗定波长，再二分振幅，让里程逼近 target。"""
    base = polyline_km(spine)
    if base >= target:
        return spine
    need = target / max(base, 1e-6)
    # 需要的伸缩比越大，之字形越密（波长越短），但不超过 45 m
    wave = max(0.045, min(0.16, 0.16 / max(1.0, need / 1.6)))
    amp_cap = min(AMP_CAP / 1000.0, wave * 1.15)
    lo, hi = 0.0, amp_cap
    best = spine
    for _ in range(24):
        mid = (lo + hi) / 2
        cand = wiggle(spine, mid * 1000.0, wave)
        L = polyline_km(cand)
        if L < target:
            lo = mid
        else:
            hi = mid
        best = cand
    return best


def main():
    src = open(SRC, encoding='utf-8').read()
    heads = [(m.start(), m.group(1)) for m in re.finditer(r"\n  \{\n    name: '([^']+)', province:", src)]
    blocks = [(st, src.find('\n  },', st) + len('\n  },'), nm) for st, nm in heads]

    report = []
    out = src
    for st, en, name in reversed(blocks):
        block = out[st:en]
        dm = re.search(r'distance: ([\d.]+)', block)
        target = float(dm.group(1)) if dm else 0
        pm = re.search(r'path: (\[\[.*?\]\])', block, re.S)
        if not pm:
            continue
        old = json.loads(pm.group(1))
        fp = os.path.join(TRACES, name.replace('/', '_') + '.json')
        if name in COAST_KEEP or not os.path.exists(fp):
            # 海岸线是照真实岸线人工描的，保留；无追踪结果的也保留
            report.append({'name': name, 'mode': 'keep', 'target': target,
                           'len': round(polyline_km([tuple(p) for p in old]), 1)})
            continue
        tr = json.load(open(fp, encoding='utf-8'))
        spine = [tuple(p) for p in tr['path']]
        L0 = polyline_km(spine)
        mode = 'trace'
        new = spine
        # 只用路网追踪出来的真实走线，不再为了凑里程硬加摆动（会变成假的锯齿）
        if target and L0 < target * 0.6:
            mode = 'trace-偏短'
        elif target and L0 > target * 1.45:
            mode = 'trace-偏长'
        bad, tot = water_hits(new, every=3)
        if tot and bad / tot > 0.45:
            # 落水过多 → 退回原 path（原 path 已做过水体校验）
            new = [tuple(p) for p in old]
            mode = '落水退回'
        new = [(round(float(a), 5), round(float(b), 5)) for a, b in new]
        L = polyline_km(new)
        report.append({'name': name, 'mode': mode, 'target': target,
                       'len': round(L, 1), 'ratio': round(L / target, 2) if target else 0,
                       'n': len(new), 'water': '%d/%d' % (bad, tot)})
        out = out[:st] + block.replace(pm.group(0), fmt_path(new)) + out[en:]

    open(SRC, 'w', encoding='utf-8').write(out)
    json.dump(report, open(os.path.join(ROOT, 'scripts', 'rebuild2_report.json'), 'w',
                           encoding='utf-8'), ensure_ascii=False, indent=1)
    for r in report:
        if r.get('ratio') is not None:
            print('%-22s %-10s 标注%6.1f 写入%6.1f 比%.2f 点%4d 水%s'
                  % (r['name'], r['mode'], r['target'], r['len'], r['ratio'], r.get('n', 0), r.get('water', '-')))
        else:
            print('%-22s %-10s 标注%6.1f 写入%6.1f' % (r['name'], r['mode'], r['target'], r['len']))
    bad = [r for r in report if r.get('ratio') and abs(r['ratio'] - 1) > 0.3]
    print('共 %d 条，里程比偏差>30%% 的 %d 条' % (len(report), len(bad)))


if __name__ == '__main__':
    main()

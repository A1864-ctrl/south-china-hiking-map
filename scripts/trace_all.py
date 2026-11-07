# -*- coding: utf-8 -*-
"""批量追踪全部路线，结果存 scripts/traces/<name>.json，支持断点续跑。

python scripts/trace_all.py            # 全部
python scripts/trace_all.py --force    # 重跑已完成的
"""
import json
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import trace_trail as tt  # noqa: E402

OUT = os.path.join(ROOT, 'scripts', 'traces')
os.makedirs(OUT, exist_ok=True)


def main():
    force = '--force' in sys.argv
    routes = tt.load_routes()
    done = 0
    for i, (name, r) in enumerate(routes.items(), 1):
        fp = os.path.join(OUT, name.replace('/', '_') + '.json')
        if os.path.exists(fp) and not force:
            print('[%2d/%d] 跳过 %s' % (i, len(routes), name), flush=True)
            continue
        try:
            path, zs = tt.trace_route(r['pts'])
            L = tt.plen(path)
            straight = tt.plen(r['pts'])
            stat = {'name': name, 'zoom': zs, 'pts': len(r['pts']), 'nodes': len(path),
                    'straight': round(straight, 2), 'traced': round(L, 2),
                    'stated': r['distance'],
                    'ratio': round(L / r['distance'], 2) if r['distance'] else 0}
            json.dump({'path': [[float(a), float(b)] for a, b in path], 'stat': stat},
                      open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
            done += 1
            print('[%2d/%d] %-22s 直线%6.1f 追踪%6.1f 标注%6.1f 比%.2f'
                  % (i, len(routes), name, straight, L, r['distance'], stat['ratio']), flush=True)
        except Exception:
            print('[%2d/%d] 失败 %s' % (i, len(routes), name), flush=True)
            traceback.print_exc()
    print('完成', done, '条')


if __name__ == '__main__':
    main()

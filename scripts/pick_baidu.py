"""从候选里挑一张：优先标题命中景点名，再比分辨率与构图。"""

import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'scripts', 'baidu_files.json')
OUT = os.path.join(ROOT, 'scripts', 'baidu_pick.json')

# 手工覆盖：自动选的候选不满意时在这里指定下标（从 1 开始）
OVERRIDE = {}


def key_of(name):
    return name.replace('观景台', '').replace('骑行', '').replace('国家森林公园', '')[:2]


def pick(name, items):
    if not items:
        return None
    if name in OVERRIDE:
        i = OVERRIDE[name] - 1
        return items[i] if 0 <= i < len(items) else items[0]
    k = key_of(name)
    hit = [it for it in items if k in it['title'] or name in it['title']]
    pool = hit if hit else items
    best = max(pool, key=lambda it: it['w'] * it['h'])
    return best


def main():
    data = json.load(io.open(SRC, encoding='utf-8'))
    picked = {}
    for name, items in data.items():
        p = pick(name, items)
        if not p:
            print('!! 无候选:', name)
            continue
        picked[name] = p
        print('%-8s %-58s %sx%s' % (name, p['title'][:40], p['w'], p['h']))
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(picked, ensure_ascii=False, indent=1))
    print('picked', len(picked))


if __name__ == '__main__':
    main()

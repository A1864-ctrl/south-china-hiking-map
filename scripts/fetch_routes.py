#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路线配图：按山名抓 Wikipedia 首图（同一座山的多条线共用）。"""
import json, os, importlib.util, urllib.parse, urllib.request, time, re

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('fp2', os.path.join(HERE, 'fetch_photos2.py'))
fp2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fp2)

ROOT = fp2.ROOT
OUT = os.path.join(ROOT, 'public', 'photos')
CAND = os.path.join(ROOT, 'scripts', 'route_candidates.json')
META = os.path.join(ROOT, 'src', 'data', 'routePhotos.js')
UA = fp2.UA


def main():
    routes = json.load(open(os.path.join(ROOT, 'scripts', 'route_list.json'), encoding='utf-8'))
    bases = []
    for r in routes:
        if r['name'] not in bases:
            bases.append(r['name'])
    cache = json.load(open(CAND, encoding='utf-8')) if os.path.exists(CAND) else {}
    for i, base in enumerate(bases):
        if cache.get(base):
            continue
        picks = fp2.pick_spot({'name': base, 'city': ''})[:2]
        cache[base] = picks
        print(i, base, len(picks), [p['title'][:26] for p in picks], flush=True)
        json.dump(cache, open(CAND, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        time.sleep(0.9)

    # 下载并生成清单：文件名用序号，避免中文路径
    idx = {b: i + 1 for i, b in enumerate(bases)}
    ok = 0
    mapping = {}
    for base, picks in cache.items():
        files = []
        for k, p in enumerate(picks[:2]):
            fn = f'route-{idx[base]}-{k + 1}.jpg'
            path = os.path.join(OUT, fn)
            if not (os.path.exists(path) and os.path.getsize(path) > 8000):
                try:
                    req = urllib.request.Request(p['thumb'], headers={'User-Agent': UA})
                    data = urllib.request.urlopen(req, timeout=50).read()
                    if len(data) > 8000:
                        open(path, 'wb').write(data)
                    else:
                        continue
                except Exception as e:
                    print('dl fail', fn, str(e)[:40], flush=True)
                    continue
            ok += 1
            files.append({
                'src': f'/photos/{fn}',
                'credit': f"{p['artist'] or 'Wikimedia'} / {p['license']}",
                'page': p['page'],
                'title': p['title'],
            })
        if files:
            mapping[base] = files
    print('downloaded', ok)
    lines = ['// 自动生成：scripts/fetch_routes.py（来源 Wikipedia / Wikimedia Commons）',
             'export const routePhotos = {']
    for base, files in mapping.items():
        items = ', '.join(
            '{ src: "%s", credit: "%s", page: "%s" }' % (f['src'], f['credit'].replace('"', ''), f['page'])
            for f in files)
        lines.append(f'  "{base}": [{items}],')
    lines.append('}')
    open(META, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', META)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 MediaWiki action API 取条目首图（顺序请求，避免限流）。"""
import json, os, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'public', 'photos')
UA = 'SouthChinaTrails/2.0 (personal hiking project)'
API = 'https://zh.wikipedia.org/w/api.php'


def q(title):
    params = {
        'action': 'query', 'format': 'json', 'titles': title, 'redirects': 1,
        'prop': 'pageimages', 'piprop': 'original|thumbnail|name', 'pithumbsize': 1000,
    }
    url = API + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print('  err', str(e)[:40], title, flush=True)
        return 'ERR'
    pages = (d.get('query', {}) or {}).get('pages', {})
    for pid, p in pages.items():
        if pid == '-1':
            return None
        return {
            'title': p.get('title'),
            'img': (p.get('original') or {}).get('source') or (p.get('thumbnail') or {}).get('source'),
            'page': 'https://zh.wikipedia.org/wiki/' + urllib.parse.quote(p.get('title', '').replace(' ', '_')),
        }
    return None


def norm(name):
    n = name.split('·')[0]
    for suf in ['国家森林公园', '森林公园', '风景区', '景区', '旅游区', '竹筏', '漂流', '骑行', '观景台']:
        n = n.replace(suf, '')
    return n.strip()


def dl(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 8000:
        return True
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        data = urllib.request.urlopen(req, timeout=60).read()
        if len(data) < 8000:
            return False
        open(path, 'wb').write(data)
        return True
    except Exception as e:
        print('  dl!', str(e)[:40], flush=True)
        return False


def run(kind):
    lst = json.load(open(os.path.join(ROOT, 'scripts', f'{kind}_list.json'), encoding='utf-8'))
    if kind == 'route':
        seen, uniq = set(), []
        for r in lst:
            if r['name'] in seen:
                continue
            seen.add(r['name'])
            uniq.append({'id': len(uniq) + 1, 'name': r['name']})
        lst = uniq
    cache_path = os.path.join(ROOT, 'scripts', f'{kind}_wiki.json')
    cache = json.load(open(cache_path, encoding='utf-8')) if os.path.exists(cache_path) else {}

    for s in lst:
        key = str(s['id'])
        if key in cache:
            continue
        res = q(norm(s['name']))
        tries = 0
        while res == 'ERR' and tries < 2:
            time.sleep(8)
            res = q(norm(s['name']))
            tries += 1
        if not res or res == 'ERR':
            res = q(s['name']) if res is not 'ERR' else None
        if res == 'ERR':
            res = None
        cache[key] = {'name': s['name'], **(res or {'img': None})}
        print(key, s['name'], 'OK' if cache[key].get('img') else 'miss', flush=True)
        json.dump(cache, open(cache_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        time.sleep(1.1)

    lines = ['// 自动生成：scripts/fetch_pageimg.py（首图来自中文维基百科条目）',
             f'export const {"spotPhotoFiles" if kind == "spot" else "routePhotoFiles"} = {{']
    ok = 0
    for key, v in cache.items():
        if not v.get('img'):
            continue
        name = v.get('name', '')
        fn = f'{kind}-{key}.jpg'
        if not dl(v['img'], os.path.join(OUT, fn)):
            continue
        ok += 1
        lines.append('  "%s": { src: "/photos/%s", title: "%s", page: "%s" },' % (
            name, fn, (v.get('title') or name).replace('"', ''), (v.get('page') or '').replace('"', '')))
    lines.append('}')
    outfile = 'spotWiki.js' if kind == 'spot' else 'routeWiki.js'
    open(os.path.join(ROOT, 'src', 'data', outfile), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print(f'{kind}: images {ok}')


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else 'spot')

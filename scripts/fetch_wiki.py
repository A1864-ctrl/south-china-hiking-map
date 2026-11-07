#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用中文维基百科 REST 摘要接口取条目首图（地点准确），并生成清单。
只用 1 次 API + 1 次图片下载 / 每个条目。
"""
import json, os, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'public', 'photos')
UA = 'SouthChinaTrails/2.0 (personal hiking project; contact: a1864ctrl@example.com)'
REST = 'https://zh.wikipedia.org/api/rest_v1/page/summary/'


def get_summary(title):
    url = REST + urllib.parse.quote(title.replace(' ', '_'))
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            print('   !', e.code, title, flush=True)
            time.sleep(20 + i * 15)
        except Exception as e:
            print('   !', str(e)[:50], title, flush=True)
            time.sleep(5)
    return None


def norm(name):
    n = name.split('·')[0]
    for suf in ['国家森林公园', '森林公园', '风景区', '景区', '旅游区', '竹筏', '漂流', '骑行', '观景台']:
        n = n.replace(suf, '')
    return n.strip()


def download(url, path):
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
        print('   dl!', str(e)[:50], flush=True)
        return False


def run(kind):
    """kind: spot / route"""
    lst = json.load(open(os.path.join(ROOT, 'scripts', f'{kind}_list.json'), encoding='utf-8'))
    cache_path = os.path.join(ROOT, 'scripts', f'{kind}_wiki.json')
    cache = json.load(open(cache_path, encoding='utf-8')) if os.path.exists(cache_path) else {}

    if kind == 'route':
        seen, uniq = set(), []
        for r in lst:
            if r['name'] in seen:
                continue
            seen.add(r['name'])
            uniq.append({'id': len(uniq) + 1, 'name': r['name'], 'city': r['city']})
        lst = uniq

    for s in lst:
        key = str(s['id'])
        if key in cache:
            continue
        base = norm(s['name'])
        data = get_summary(base) or get_summary(s['name'])
        if not data:
            cache[key] = {'name': s['name'], 'img': None}
        else:
            img = (data.get('originalimage') or {}).get('source') or (data.get('thumbnail') or {}).get('source')
            cache[key] = {
                'name': s['name'],
                'title': data.get('title'),
                'img': img,
                'page': (data.get('content_urls', {}).get('desktop', {}) or {}).get('page'),
                'extract': (data.get('extract') or '')[:120],
            }
        print(key, s['name'], 'OK' if cache[key]['img'] else 'miss', flush=True)
        json.dump(cache, open(cache_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        time.sleep(0.9)

    # 下载 + 清单
    lines = ['// 自动生成：scripts/fetch_wiki.py（首图来自中文维基百科条目，版权见原页面）',
             f'export const {"spotPhotoFiles" if kind == "spot" else "routePhotoFiles"} = {{']
    ok = 0
    for key, v in cache.items():
        if not v.get('img'):
            continue
        fn = f'{kind}-{key}.jpg'
        if not download(v['img'], os.path.join(OUT, fn)):
            continue
        ok += 1
        page = (v.get('page') or '').replace('"', '')
        lines.append(f'  "{key}": {{ src: "/photos/{fn}", title: "{v.get("title", "")}", page: "{page}" }},')
    lines.append('}')
    outfile = 'spotWiki.js' if kind == 'spot' else 'routeWiki.js'
    open(os.path.join(ROOT, 'src', 'data', outfile), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print(f'{kind}: downloaded {ok}, wrote {outfile}')


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else 'spot')

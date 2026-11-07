#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用中文维基条目主图（pageimages）补缺图点位，写入 spotWiki.js 的 x 区块。
只接受条目名与景点名高度相关的命中，宁缺勿错。
"""
import json, os, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(ROOT, 'src', 'data', 'spotWiki.js')
OUT = os.path.join(ROOT, 'public', 'photos')
UA = 'SouthChinaTrails/2.0 (personal hiking project)'
API = 'https://zh.wikipedia.org/w/api.php'

# 景点名 -> 维基条目名（不确定的留空，宁可不查）
TITLES = {
    '相公山观景台': '相公山',
    '猫儿山': '猫儿山 (广西)',
    '十里画廊骑行': '十里画廊 (阳朔)',
    '八角寨': '八角寨',
    '古东瀑布': '古东瀑布',
    '全州天湖': '天湖 (全州)',
    '越秀公园': '越秀公园',
    '从化溪头村': '溪头村 (从化)',
    '石门国家森林公园': '石门国家森林公园',
    '海珠湖': '海珠湖',
    '大鹏所城': '大鹏所城',
    '马峦山': '马峦山',
    '观澜湖': '观澜湖',
    '大围山': '大围山 (浏阳)',
    '石燕湖': '石燕湖',
    '铜官窑古镇': '长沙铜官窑遗址',
    '德夯大峡谷': '德夯',
    '红石林': '红石林',
    '坐龙峡': '坐龙峡',
    '老司城': '老司城遗址',
    '张家界大峡谷': '张家界大峡谷',
    '杨家界': '杨家界',
    '七星山': '七星山 (张家界)',
    '南昆山': '南昆山',
    '惠州西湖': '惠州西湖',
    '象头山': '象头山',
    '黑排角': '黑排角',
    '大亚湾': '大亚湾',
    '东江湖·小东江': '东江湖',
    '高椅岭': '高椅岭',
    '飞天山': '飞天山',
    '仰天湖草原': '仰天湖',
    '板梁古村': '板梁古村',
    '苏仙岭': '苏仙岭',
}

spots = json.load(open(os.path.join(ROOT, 'scripts', 'spot_list.json'), encoding='utf-8'))
spot_id = {s['name']: s['id'] for s in spots}

src = open(WIKI, encoding='utf-8').read()
have = set(re.findall(r'^\s*"([^"]+)"\s*:\s*\{', src, re.M))


def api(params):
    req = urllib.request.Request(API + '?' + urllib.parse.urlencode(params), headers={'User-Agent': UA})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            print('  retry', str(e)[:40], flush=True)
            time.sleep(5 + i * 5)
    return {}


new_lines = []
for name, title in TITLES.items():
    if name in have:
        continue
    if name not in spot_id:
        continue
    d = api({'action': 'query', 'format': 'json', 'titles': title, 'redirects': 1,
             'prop': 'pageimages|images', 'piprop': 'original|name', 'imlimit': 1})
    pages = d.get('query', {}).get('pages', {})
    page = next(iter(pages.values()), {})
    if 'missing' in page:
        print(name, 'no page', flush=True)
        time.sleep(1.5)
        continue
    orig = page.get('original', {})
    url = orig.get('source')
    if not url or not re.search(r'\.(jpg|jpeg|png)$', url, re.I):
        print(name, 'no image', flush=True)
        time.sleep(1.5)
        continue
    fid = spot_id[name]
    fn = 'spot-%d-w.jpg' % fid
    try:
        rq = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(rq, timeout=60) as r:
            data = r.read()
        if len(data) < 20000:
            print(name, 'too small', flush=True)
            continue
        open(os.path.join(OUT, fn), 'wb').write(data)
    except Exception as e:
        print(name, 'dl fail', str(e)[:40], flush=True)
        time.sleep(2)
        continue
    meta = api({'action': 'query', 'format': 'json', 'titles': page['title'],
                'prop': 'pageimages'})
    new_lines.append({'name': name, 'id': fid, 'file': fn, 'src': url,
                      'title': page['title']})
    print(name, '->', page['title'], 'ok', flush=True)
    time.sleep(1.8)

json.dump(new_lines, open(os.path.join(ROOT, 'scripts', 'zhwiki_photos.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('total new', len(new_lines))

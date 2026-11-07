#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重写 spotWiki.js 的 x 区块：路径用 spot-<id>-x.jpg，署名取自缓存或接口。"""
import json, os, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(ROOT, 'src', 'data', 'spotWiki.js')
API = 'https://commons.wikimedia.org/w/api.php'
UA = 'SouthChinaTrails/2.0 (personal hiking project)'

# name -> (id, commons file)
KEEP = {
    '兴坪古镇': (8, 'Li River at Xingping 1.jpg'),
    '橘子洲': (35, 'Orange Isle 2021122625.jpg'),
    '洋湖湿地': (41, 'Yanghu Wetland Park 20210429a.jpg'),
    '黑麋峰': (42, 'Heimifeng Temple, Changsha, Hunan, Picture1.jpg'),
    '芙蓉镇': (44, '1 furong aerial panorama 2017.jpg'),
    '矮寨大桥': (46, 'Aizhai Bridge-1.jpg'),
    '天门山': (53, 'Tianmen Mountain 20180326 094808.jpg'),
    '杨家界': (59, 'Yangjiajie.jpg'),
    '惠州西湖': (65, 'Huizhou Xihu 2013.09.20 09-16-09.jpg'),
    '东江湖·小东江': (69, 'Dongjiang Lake, Chenzhou, Hunan.JPG'),
    '高椅岭': (70, 'Mount Gaoyiling in Chenzhou, Hunan, China2.jpg'),
}

src = open(WIKI, encoding='utf-8').read()
cache = {}
for m in re.finditer(r'title: "([^"]+)", credit: "([^"]*)", license: "([^"]*)"', src):
    cache[m.group(1)] = (m.group(2), m.group(3))


def meta(fname):
    if fname in cache and cache[fname][1] != '见原页面':
        return cache[fname]
    params = {'action': 'query', 'format': 'json', 'titles': 'File:' + fname,
              'prop': 'imageinfo', 'iiprop': 'extmetadata'}
    req = urllib.request.Request(API + '?' + urllib.parse.urlencode(params), headers={'User-Agent': UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode('utf-8'))
            em = next(iter(d['query']['pages'].values()))['imageinfo'][0]['extmetadata']
            artist = re.sub(r'<[^>]+>', '', em.get('Artist', {}).get('value', '')).strip()
            lic = em.get('LicenseShortName', {}).get('value', '').strip()
            return artist or 'Wikimedia Commons', lic or '见原页面'
        except Exception as e:
            print('retry', fname, str(e)[:40], flush=True)
            time.sleep(5 + attempt * 5)
    return cache.get(fname, ('Wikimedia Commons', '见原页面'))


head = src.split('\n\n')[0].rstrip()
lines = [head, '']
for name, (sid, fname) in KEEP.items():
    a, l = meta(fname)
    a = a.replace('"', "'")
    lines.append(
        '  "%s": { src: "/photos/spot-%d-x.jpg", all: ["/photos/spot-%d-x.jpg"], '
        'title: %s, credit: %s, license: %s, page: "https://commons.wikimedia.org/wiki/File:%s" },'
        % (name, sid, sid, json.dumps(fname, ensure_ascii=False), json.dumps(a, ensure_ascii=False),
           json.dumps(l, ensure_ascii=False), urllib.parse.quote(fname.replace(' ', '_')))
    )
lines.append('}')
open(WIKI, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('ok', len(KEEP))

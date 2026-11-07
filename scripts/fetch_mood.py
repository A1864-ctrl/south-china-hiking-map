#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""氛围图 (日落 / 夜景)：按主题抓取 Wikimedia Commons 图片，标注为参考图。"""
import json, os, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('fp', os.path.join(HERE, 'fetch_photos.py'))
fp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fp)

QUERIES = {
    'sea': ('海边 日落', '海滨 夜景'),
    'mountain': ('山顶 日落 云海', '银河 星空 山'),
    'peak': ('张家界 日落', '张家界 云海'),
    'lake': ('湖泊 日落', '湖 夜景 倒影'),
    'river': ('漓江 日落', '凤凰古城 夜景'),
    'town': ('古镇 夕阳', '古镇 夜景'),
    'city': ('城市 日落 天际线', '深圳 夜景'),
    'danxia': ('丹霞 日落', '丹霞 地貌'),
    'forest': ('森林 夕阳', '森林 星空'),
    'terrace': ('梯田 日落', '梯田 村寨'),
    'grass': ('草原 日落', '草原 星空'),
    'cave': ('溶洞 灯光', '溶洞 钟乳石')
}

OUT = os.path.join(fp.ROOT, 'public', 'photos')
META = os.path.join(fp.ROOT, 'src', 'data', 'moodPhotos.js')


def main():
    os.makedirs(OUT, exist_ok=True)
    picks = {}
    for theme, (qs, qn) in QUERIES.items():
        for slot, q in (('sunset', qs), ('night', qn)):
            res = fp.search(q, limit=8) or []
            if not res:
                print('miss', theme, slot, flush=True)
                continue
            p = res[0]
            fn = f'mood-{theme}-{slot}.jpg'
            path = os.path.join(OUT, fn)
            if not (os.path.exists(path) and os.path.getsize(path) > 8000):
                try:
                    import urllib.request
                    req = urllib.request.Request(p['thumb'], headers={'User-Agent': fp.UA})
                    data = urllib.request.urlopen(req, timeout=45).read()
                    open(path, 'wb').write(data)
                except Exception as e:
                    print('dl fail', fn, e, flush=True)
                    continue
            picks[f'{theme}-{slot}'] = {
                'file': fn, 'title': p['title'], 'artist': (p['artist'] or '')[:40],
                'license': p['license'], 'page': p['page']
            }
            print('ok', fn, p['title'][:40], flush=True)

    lines = ['// 自动生成：scripts/fetch_mood.py（日落 / 夜景 参考图，来源 Wikimedia Commons）',
             'export const moodPhotos = {']
    for k, v in picks.items():
        lines.append(
            f'  "{k}": {{ src: "/photos/{v["file"]}", credit: "{v["artist"].replace(chr(34), "")} / {v["license"]}", title: "{v["title"].replace(chr(34), "")[:60]}", page: "{v["page"]}" }},')
    lines.append('}')
    open(META, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', META)


if __name__ == '__main__':
    main()

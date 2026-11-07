# -*- coding: utf-8 -*-
"""对四季图里配错（截图/人物/横幅/外地图/贴纸框/菜品）的条目，按「景点名+季节」换词重抓。"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_seasons as fs

fs.MIN_W = 1000
ROOT = fs.ROOT
OUT2 = os.path.join(ROOT, 'scripts', '_seasonfix')
os.makedirs(OUT2, exist_ok=True)
FIX_JSON = os.path.join(ROOT, 'scripts', 'season_fix.json')
JS = os.path.join(ROOT, 'src', 'data', 'seasonPhoto.js')

JUNK = {
    ('便江', '春'): '永兴 便江 便江风光', ('便江', '夏'): '永兴 便江 便江风光',
    ('便江', '秋'): '永兴 便江 便江风光', ('便江', '冬'): '永兴 便江 便江风光',
    ('太平老街', '春'): '长沙太平老街 街景', ('太平老街', '秋'): '长沙太平老街 街景',
    ('棉花山', '春'): '棉花山 山顶', ('棉花山', '冬'): '棉花山 山顶',
    ('陈家祠', '春'): '广州陈家祠 屋脊 灰塑', ('陈家祠', '夏'): '广州陈家祠 屋脊 灰塑',
    ('陈家祠', '秋'): '广州陈家祠 屋脊 灰塑', ('陈家祠', '冬'): '广州陈家祠 屋脊 灰塑',
    ('飞天山', '春'): '郴州飞天山 丹霞', ('飞天山', '秋'): '郴州飞天山 丹霞',
    ('飞天山', '冬'): '郴州飞天山 丹霞',
    ('大梅沙', '夏'): '大梅沙 海滨公园 沙滩', ('大梅沙', '冬'): '大梅沙 海滨公园 沙滩',
    ('杨梅坑', '夏'): '杨梅坑 海岸线 鹿嘴', ('杨梅坑', '冬'): '杨梅坑 海岸线 鹿嘴',
    ('橘子洲', '夏'): '橘子洲 毛泽东雕像',
    ('观澜湖', '夏'): '观澜湖 生态体育公园',
    ('七娘山', '秋'): '七娘山 大鹏 山顶', ('七娘山', '冬'): '七娘山 大鹏 海岸',
    ('人才公园', '秋'): '深圳人才公园 星光桥',
    ('梧桐山', '秋'): '梧桐山 云海 深圳',
    ('苏仙岭', '秋'): '郴州苏仙岭 山景',
    ('边城茶峒', '秋'): '边城茶峒 古镇 渡口',
    ('黑麋峰', '秋'): '长沙黑麋峰 山顶', ('黑麋峰', '冬'): '长沙黑麋峰 山顶',
    ('海珠湖', '秋'): '广州海珠湖 花海',
    ('南昆山', '冬'): '南昆山 森林 瀑布',
    ('张家界国家森林公园', '冬'): '张家界 国家森林公园 雪',
    ('深圳湾公园', '冬'): '深圳湾公园 骑行 绿道',
    ('湖南博物院', '冬'): '湖南省博物馆 建筑',
    ('白云山', '冬'): '广州白云山 摩星岭',
    ('矮寨大桥', '冬'): '矮寨大桥 悬索桥',
    ('莲花山', '冬'): '番禺莲花山 望海观音',
    ('燕子岩', '冬'): '燕子岩 溶洞 郴州',
    ('马头山', '冬'): '马头山 丹霞 郴州',
    ('黑排角', '冬'): '黑排角 海岸线 礁石',
    ('永庆坊', '夏'): '广州永庆坊 骑楼',
}


def file_of(name, season):
    src = open(JS, encoding='utf-8').read()
    m = re.search(r"'%s': \{ ([^}]*) \}" % re.escape(name), src)
    if not m:
        return None
    mm = re.search(season + r": '([^']+)'", m.group(1))
    return mm.group(1) if mm else None


def work(item):
    (name, season), word = item
    cs = fs.search(word)
    got = []
    for c in cs:
        if len(got) >= 4:
            break
        dst = os.path.join(OUT2, '%s_%s_%d.jpg' % (name, season, len(got)))
        try:
            size = fs.download(c['u'], dst)
        except Exception:
            continue
        if not size:
            continue
        rel = os.path.relpath(dst, ROOT).replace(os.sep, '/')
        got.append({'path': rel, 'w': size[0], 'h': size[1], 'title': c['title'],
                    'file': file_of(name, season), 'src': c['u']})
    print(name, season, word, '->', len(got), flush=True)
    return '%s|%s' % (name, season), {'name': name, 'season': season, 'cands': got}


def main():
    res = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        for k, v in ex.map(work, sorted(JUNK.items())):
            res[k] = v
    json.dump(res, open(FIX_JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('完成', len(res), '空', sum(1 for v in res.values() if not v['cands']))


if __name__ == '__main__':
    main()

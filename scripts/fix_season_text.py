# -*- coding: utf-8 -*-
"""重抓四季里仍带大文字 / 配错的一批，并直接替换。"""
import json
import os
import sys

from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_seasons as fs

fs.MIN_W = 900
ROOT = fs.ROOT
MAN = os.path.join(ROOT, 'scripts', 'season_cand.json')
JS = os.path.join(ROOT, 'src', 'data', 'seasonPhoto.js')
PUB = os.path.join(ROOT, 'public')

BAD = ('方案', '规划', '效果图', '公告', '通知', '招聘', '地图', '门票', '海报',
       '二维码', '截图', '秀', '组图', '合集', '攻略', '推文', '一日游', '两日游', '跟团')

FIX = {
    ('仙湖植物园', '春'): '深圳仙湖植物园 花',
    ('兴坪古镇', '春'): '兴坪 漓江 老寨山',
    ('兴坪古镇', '冬'): '兴坪古镇 漓江',
    ('大亚湾', '春'): '惠州大亚湾 海岛',
    ('大亚湾', '秋'): '大亚湾 海岸',
    ('大亚湾', '冬'): '大亚湾 海岸',
    ('人才公园', '夏'): '深圳人才公园 湖 天际线',
    ('人才公园', '冬'): '深圳人才公园 湖 天际线',
    ('橘子洲', '夏'): '橘子洲 湘江',
    ('湖南博物院', '夏'): '湖南博物院 建筑',
    ('七娘山', '秋'): '七娘山 大鹏 山脊',
    ('七娘山', '冬'): '七娘山 大鹏 海岸',
    ('永庆坊', '秋'): '永庆坊 骑楼 广州',
    ('仰天湖草原', '冬'): '仰天湖草原 郴州',
    ('相公山观景台', '冬'): '相公山 漓江 晨雾',
    ('莲花山', '冬'): '番禺莲花山 古采石场',
    ('马头山', '冬'): '马头山 丹霞',
}


def daylight(path):
    im = Image.open(path).convert('RGB').resize((120, 80), Image.BILINEAR)
    px = list(im.getdata())
    return sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in px) / len(px)


def collage(path):
    im = Image.open(path).convert('RGB').resize((200, 133), Image.BILINEAR)
    px = list(im.getdata())
    return sum(1 for r, g, b in px if min(r, g, b) >= 246) / len(px)


def main():
    man = json.load(open(MAN, encoding='utf-8'))
    js = open(JS, encoding='utf-8').read()
    out = {}

    for (name, season), word in FIX.items():
        key = next((k for k, v in man.items() if v['name'] == name and v['season'] == season), None)
        if not key:
            print('未找到', name, season)
            continue
        got = []
        for c in fs.search(word):
            if len(got) >= 4:
                break
            dst = os.path.join(fs.OUT_DIR, '%03d_%s_x%d.jpg' % (man[key]['idx'], season, len(got)))
            try:
                size = fs.download(c['u'], dst)
            except Exception:
                continue
            if not size:
                continue
            rel = os.path.relpath(dst, ROOT).replace(os.sep, '/')
            got.append({'path': rel, 'w': size[0], 'h': size[1], 'title': c['title'], 'src': c['u']})
        print(name, season, word, '->', len(got), [g['title'][:20] for g in got], flush=True)
        if not got:
            continue
        man[key]['cands'] = got
        man[key]['word'] = word
        out[(name, season)] = got

    # 选：标题含景点名/城市、非拼图、白天的优先
    done = 0
    for (name, season), got in out.items():
        key2 = name.replace('·', ' ').split()[0][:2]
        pick = None
        for c in got:
            fp = os.path.join(ROOT, c['path'])
            if any(b in c['title'] for b in BAD):
                continue
            if not (key2 in c['title']):
                continue
            if daylight(fp) < 70 or collage(fp) > 0.10:
                continue
            pick = c
            break
        if not pick:
            pick = got[0]
        im = Image.open(os.path.join(ROOT, pick['path'])).convert('RGB')
        aw, ah = im.size
        tw, th = aw, aw / 1.5
        if th > ah:
            th = ah
            tw = th * 1.5
        x0, y0 = (aw - tw) / 2, (ah - th) / 2
        im = im.crop((int(x0), int(y0), int(x0 + tw), int(y0 + th)))
        w = min(1050, im.width)
        im = im.resize((w, int(round(w / 1.5))), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=0.7, percent=46, threshold=3))
        # 直接从 seasonPhoto.js 里找该景点该季的文件名
        row = next(p for p in js.split('\n') if "'%s': {" % name in p)
        fname = row.split('%s: ' % season)[1].split("'")[1].replace('photos/season/', '')
        im.save(os.path.join(PUB, 'photos', 'season', fname), 'JPEG', quality=84, optimize=True, progressive=True)
        done += 1
        print('替换', name, season, fname, im.size, pick['title'][:26])

    json.dump(man, open(MAN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('共替换', done)


if __name__ == '__main__':
    main()

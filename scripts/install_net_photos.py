"""把选定的配图规范化后写入站点。

- 自动裁掉上下黑边（视频截图常见）
- 统一裁成 3:2、宽 1200，JPEG q82
- 轻度自动对比 + 微饱和，让不同来源的图观感统一
- 生成 src/data/spotPhotoNet.js 供 spotWiki 合并
"""

import io
import json
import os

from PIL import Image, ImageEnhance, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'scripts', 'p360_final.json')
PHOTOS = os.path.join(ROOT, 'public', 'photos')
OUT_JS = os.path.join(ROOT, 'src', 'data', 'spotPhotoNet.js')

LAST_SWAP = {'湖南博物院': 4, '大围山': 3, '铜官窑古镇': 2}
TARGET_RATIO = 3 / 2
W, H = 1200, 800


def trim_bars(im):
    """裁掉近黑边（视频截图/截图留白）"""
    g = im.convert('L')
    w, h = g.size
    px = g.load()

    def row_dark(y):
        s = 0
        for x in range(0, w, max(1, w // 60)):
            s += px[x, y]
        return s / (w // max(1, w // 60) + 1) < 26

    top, bot = 0, h - 1
    while top < h // 4 and row_dark(top):
        top += 1
    while bot > h * 3 // 4 and row_dark(bot):
        bot -= 1
    if top or bot < h - 1:
        im = im.crop((0, top, w, bot + 1))
    return im


def normalize(path):
    im = Image.open(path).convert('RGB')
    im = trim_bars(im)
    w, h = im.size
    ratio = w / h
    if ratio > TARGET_RATIO:  # 太宽，裁左右
        nw = int(h * TARGET_RATIO)
        left = (w - nw) // 2
        im = im.crop((left, 0, left + nw, h))
    else:  # 太高，裁上下
        nh = int(w / TARGET_RATIO)
        top = int((h - nh) * 0.42)  # 稍微偏上，保住天际线
        im = im.crop((0, top, w, top + nh))
    im = im.resize((W, H), Image.LANCZOS)
    im = ImageOps.autocontrast(im, cutoff=0.4)
    im = ImageEnhance.Color(im).enhance(1.04)
    im = ImageEnhance.Contrast(im).enhance(1.03)
    return im


def main():
    data = json.load(io.open(SRC, encoding='utf-8'))
    # 最后三处换图
    files = json.load(io.open(os.path.join(ROOT, 'scripts', 'p360_files.json'), encoding='utf-8'))
    for name, idx in LAST_SWAP.items():
        items = files.get(name) or []
        if idx - 1 < len(items):
            data[name] = items[idx - 1]

    os.makedirs(PHOTOS, exist_ok=True)
    rows = []
    for i, (name, it) in enumerate(data.items(), start=1):
        fn = 'spot-net-%02d.jpg' % i
        dst = os.path.join(PHOTOS, fn)
        im = normalize(it['file'])
        im.save(dst, 'JPEG', quality=82, optimize=True, progressive=True)
        size = os.path.getsize(dst)
        rows.append((name, 'photos/' + fn, it.get('title', ''), it.get('page', '')))
        print('%-10s %-18s %4d KB  %s' % (name, fn, size // 1024, it.get('title', '')[:36]))

    lines = [
        '// 由 scripts/install_net_photos.py 生成：网络检索到的景点配图',
        '// 图源为公开网页（博主分享为主），仅作毕业设计演示使用，如涉版权请联系删除',
        'export const spotPhotoNet = {',
    ]
    for i, (name, src, title, page) in enumerate(rows, start=1):
        t = (title or '').replace("'", ' ').replace('\n', ' ')[:60]
        pg = (page or '').replace("'", ' ')
        lines.append(
            "  '%s': { src: '%s', all: ['%s'], title: '%s', credit: '网络图源 · 侵删', license: '仅作演示', page: '%s' },"
            % (name, src, src, t, pg)
        )
    lines.append('}')
    lines.append('')
    io.open(OUT_JS, 'w', encoding='utf-8').write('\n'.join(lines))
    print('wrote', OUT_JS)


if __name__ == '__main__':
    main()

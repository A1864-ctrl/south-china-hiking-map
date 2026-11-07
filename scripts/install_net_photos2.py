"""第二轮：把原有但不合格的 13 张封面也换成网络实景图。

输出与第一轮同一份 spotPhotoNet.js（共 45 条），
photos.js 改为网络图优先，这样这 13 个点位会覆盖旧的维基封面。
"""

import io
import json
import os

from PIL import Image, ImageEnhance, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_A = os.path.join(ROOT, 'scripts', 'p360_final.json')
SRC_B = os.path.join(ROOT, 'scripts', 'p360b_files.json')
PHOTOS = os.path.join(ROOT, 'public', 'photos')
OUT_JS = os.path.join(ROOT, 'src', 'data', 'spotPhotoNet.js')

PICKS_B = {
    '白云山': 2,
    '华南植物园': 3,
    '梧桐山': 1,
    '七娘山': 4,
    '西冲海滩': 2,
    '仙湖植物园': 3,
    '莽山': 1,
    '黑麋峰': 3,
    '橘子洲': 2,
    '广州塔': 2,
    '太平老街': 5,
    '洋湖湿地': 2,
    '岳麓山': 4,
}
TARGET_RATIO = 3 / 2
W, H = 1200, 800


def trim_bars(im):
    g = im.convert('L')
    w, h = g.size
    px = g.load()
    step = max(1, w // 60)

    def row_dark(y):
        s = 0
        n = 0
        for x in range(0, w, step):
            s += px[x, y]
            n += 1
        return n and s / n < 26

    top, bot = 0, h - 1
    while top < h // 4 and row_dark(top):
        top += 1
    while bot > h * 3 // 4 and row_dark(bot):
        bot -= 1
    if top or bot < h - 1:
        im = im.crop((0, top, w, bot + 1))
    return im


def normalize(path):
    im = trim_bars(Image.open(path).convert('RGB'))
    w, h = im.size
    if w / h > TARGET_RATIO:
        nw = int(h * TARGET_RATIO)
        left = (w - nw) // 2
        im = im.crop((left, 0, left + nw, h))
    else:
        nh = int(w / TARGET_RATIO)
        top = int((h - nh) * 0.42)
        im = im.crop((0, top, w, top + nh))
    im = im.resize((W, H), Image.LANCZOS)
    im = ImageOps.autocontrast(im, cutoff=0.4)
    im = ImageEnhance.Color(im).enhance(1.04)
    im = ImageEnhance.Contrast(im).enhance(1.03)
    return im


def main():
    first = json.load(io.open(SRC_A, encoding='utf-8'))
    second_files = json.load(io.open(SRC_B, encoding='utf-8'))

    # 第一轮 32 个点位，沿用已有文件，不重跑
    rows = []
    for i, (name, it) in enumerate(first.items(), start=1):
        fn = 'spot-net-%02d.jpg' % i
        if not os.path.exists(os.path.join(PHOTOS, fn)):
            normalize(it['file']).save(os.path.join(PHOTOS, fn), 'JPEG', quality=82)
        rows.append((name, 'photos/' + fn, it.get('title', ''), it.get('page', '')))

    # 第二轮 13 个不合格封面
    idx = len(rows)
    for name, pick in PICKS_B.items():
        items = second_files.get(name) or []
        if pick - 1 >= len(items):
            print('skip', name)
            continue
        it = items[pick - 1]
        idx += 1
        fn = 'spot-net-%02d.jpg' % idx
        normalize(it['file']).save(os.path.join(PHOTOS, fn), 'JPEG', quality=82,
                                    optimize=True, progressive=True)
        rows.append((name, 'photos/' + fn, it.get('title', ''), it.get('page', '')))
        print('%-8s -> %s' % (name, fn))

    lines = [
        '// 由 scripts/install_net_photos2.py 生成：网络检索到的景点配图',
        '// 图源为公开网页（博主分享为主），仅作毕业设计演示使用，如涉版权请联系删除',
        'export const spotPhotoNet = {',
    ]
    for name, src, title, page in rows:
        t = (title or '').replace("'", ' ').replace('\n', ' ')[:60]
        pg = (page or '').replace("'", ' ')
        lines.append(
            "  '%s': { src: '%s', all: ['%s'], title: '%s', credit: '网络图源 · 侵删', license: '仅作演示', page: '%s' },"
            % (name, src, src, t, pg)
        )
    lines.append('}')
    lines.append('')
    io.open(OUT_JS, 'w', encoding='utf-8').write('\n'.join(lines))
    print('total entries', len(rows))


if __name__ == '__main__':
    main()

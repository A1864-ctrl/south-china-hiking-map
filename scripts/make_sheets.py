"""把候选图拼成核对用的对比图，每张图放 3 个点位。"""

import io
import json
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'scripts', 'baidu_files.json')
OUT = os.path.join(ROOT, 'shots', 'sheets')
PER_SHEET = 3
TW, TH = 300, 190


def main():
    data = json.load(io.open(SRC, encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    names = list(data.keys())
    n = 0
    for gi in range(0, len(names), PER_SHEET):
        group = names[gi:gi + PER_SHEET]
        rows = []
        for name in group:
            rows.append((name, data[name]))
        width = TW * 6
        height = sum(TH + 26 for _ in rows)
        sheet = Image.new('RGB', (width, height), '#ffffff')
        d = ImageDraw.Draw(sheet)
        y = 0
        for name, items in rows:
            d.rectangle([0, y, width, y + 22], fill='#1e3d29')
            d.text((8, y + 5), '%s  (%d 张候选)' % (name, len(items)), fill='white')
            for ci, it in enumerate(items[:6]):
                try:
                    im = Image.open(it['file']).convert('RGB')
                except Exception:
                    continue
                im.thumbnail((TW - 6, TH - 6))
                x = ci * TW + 3
                sheet.paste(im, (x, y + 26))
                d.text((x + 4, y + 28), str(ci + 1), fill='#c0392b')
            y += TH + 26
        n += 1
        p = os.path.join(OUT, 'sheet-%02d.png' % n)
        sheet.save(p)
        print(p, [g for g in group])


if __name__ == '__main__':
    main()

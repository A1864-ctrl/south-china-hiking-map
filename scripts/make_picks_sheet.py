"""把挑中的图拼成总表，逐张核对是否对得上景点、画质是否够用。"""

import io
import json
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'scripts', 'baidu_pick.json')
OUT = os.path.join(ROOT, 'shots', 'picks')
PER = 16
TW, TH = 340, 210


def main():
    data = json.load(io.open(SRC, encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    names = list(data.keys())
    cols = 4
    for gi in range(0, len(names), PER):
        group = names[gi:gi + PER]
        rows = (len(group) + cols - 1) // cols
        sheet = Image.new('RGB', (TW * cols, (TH + 20) * rows), '#ffffff')
        d = ImageDraw.Draw(sheet)
        for i, name in enumerate(group):
            it = data[name]
            im = Image.open(it['file']).convert('RGB')
            im.thumbnail((TW - 6, TH - 6))
            x = (i % cols) * TW
            y = (i // cols) * (TH + 20)
            sheet.paste(im, (x + 3, y + 20))
            d.rectangle([x, y, x + TW, y + 19], fill='#1e3d29')
            d.text((x + 5, y + 4), '%d %s' % (gi + i + 1, name), fill='white')
        n = gi // PER + 1
        p = os.path.join(OUT, 'picks-%d.png' % n)
        sheet.save(p)
        print(p)


if __name__ == '__main__':
    main()

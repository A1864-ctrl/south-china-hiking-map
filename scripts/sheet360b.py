"""把补拍候选拼成核对图。"""

import io
import json
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'scripts', 'p360b_files.json')
OUT = os.path.join(ROOT, 'shots', 'fix2')
PER_SHEET = 7
TW, TH = 300, 190


def main():
    data = json.load(io.open(SRC, encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    names = list(data.keys())
    for gi in range(0, len(names), PER_SHEET):
        group = names[gi:gi + PER_SHEET]
        sheet = Image.new('RGB', (TW * 5, (TH + 22) * len(group)), 'white')
        dr = ImageDraw.Draw(sheet)
        for ri, name in enumerate(group):
            y = ri * (TH + 22)
            dr.rectangle([0, y, TW * 5, y + 20], fill='#1e3d29')
            dr.text((8, y + 4), name, fill='white')
            for ci, it in enumerate(data[name][:5]):
                try:
                    im = Image.open(it['file']).convert('RGB')
                except Exception:
                    continue
                im.thumbnail((TW - 6, TH - 6))
                x = ci * TW
                sheet.paste(im, (x + 3, y + 22))
                dr.text((x + 5, y + 24), str(ci + 1), fill='#c0392b')
        p = os.path.join(OUT, 'r%d.png' % (gi // PER_SHEET + 1))
        sheet.save(p)
        print(p, group)


if __name__ == '__main__':
    main()

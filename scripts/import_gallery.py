# -*- coding: utf-8 -*-
"""
从「户外出片图集」导入配图
- 解析图集 HTML 的卡片，得到 景点/路线 -> 图片 的对应关系
- 统一裁成 3:2（裁掉右/下边缘的水印带），最长边不超过 1200，质量 86
- 输出到 public/photos/gal/，并生成 src/data/gallery.js
"""
import os, re, json
from PIL import Image, ImageFilter

SRC = r"C:/Users/Tsy20723/Desktop/户外出片图集"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "public", "photos", "gal")

html = open(os.path.join(SRC, "户外出片图集.html"), encoding="utf-8").read()

# 景点卡片：data-group=城市 data-name=名称 data-sub=区县·类型
spot_cards = re.findall(
    r'<article class="card" data-group="([^"]*)" data-name="([^"]*)" data-sub="([^"]*)">.*?<img src="(assets/[^"]+)"',
    html, re.S)
# 路线卡片：带 data-difficulty
route_cards = re.findall(
    r'<article class="card" data-group="([^"]*)" data-difficulty="([^"]*)" data-name="([^"]*)" data-sub="([^"]*)">.*?<img src="(assets/[^"]+)"',
    html, re.S)

print("景点卡片", len(spot_cards), "路线卡片", len(route_cards))

os.makedirs(OUT, exist_ok=True)


def norm(src_file, dst_file):
    im = Image.open(src_file).convert("RGB")
    W, H = im.size
    portrait = W / H < 1.2
    # 保留原图作者水印（属来源署名，不做涂抹），只做 3:2 统一裁切
    aw, ah = W, H
    tw, th = aw, aw / 1.5
    if th > ah:
        th = ah
        tw = th * 1.5
    x0 = (aw - tw) / 2.0
    # 竖图大半是天空，窗口压下保住地景
    y0 = (ah - th) * (0.92 if portrait else 0.5)
    box = (int(x0), int(y0), int(x0 + tw), int(y0 + th))
    im = im.crop(box)
    w = min(1400, im.width)
    im = im.resize((w, int(round(w / 1.5))), Image.LANCZOS)
    if w < 1000:  # 小图放大一点点，避免浏览器二次插值发虚
        im = im.resize((int(w * 1.25), int(round(w * 1.25 / 1.5))), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=0.7, percent=52, threshold=3))
    im.save(dst_file, "JPEG", quality=90, optimize=True, progressive=True)
    return im.size


MANIFEST = {"spots": {}, "routes": {}, "meta": {}}
seen = {}

for i, (city, name, sub, src) in enumerate(spot_cards, 1):
    fn = "gal-s%02d.jpg" % i
    size = norm(os.path.join(SRC, src), os.path.join(OUT, fn))
    MANIFEST["spots"][name] = fn
    MANIFEST.setdefault("city", {})[name] = city
    MANIFEST.setdefault("district", {})[name] = sub.split(" · ")[0]
    seen.setdefault(os.path.basename(src), []).append(name)
    MANIFEST["meta"][fn] = {"from": os.path.basename(src), "city": city, "size": size}

for i, (city, diff, name, sub, src) in enumerate(route_cards, 1):
    base = os.path.basename(src)
    if base.startswith("h"):
        fn = "gal-r%s.jpg" % base[1:3]
        if not os.path.exists(os.path.join(OUT, fn)):
            norm(os.path.join(SRC, src), os.path.join(OUT, fn))
    else:
        # 路线复用了景点图，直接指向同一张
        idx = int(re.sub(r"\D", "", base))
        fn = "gal-s%02d.jpg" % idx
    MANIFEST["routes"][name] = fn

js = ["// 由 scripts/import_gallery.py 自动生成，请勿手改",
      "// 图源：用户提供的《户外出片图集》（网络博主图，仅用于毕设演示，不作商用）",
      "",
      "export const spotGallery = " + json.dumps(MANIFEST["spots"], ensure_ascii=False, indent=2),
      "",
      "export const routeGallery = " + json.dumps(MANIFEST["routes"], ensure_ascii=False, indent=2),
      "",
      "export const spotCity = " + json.dumps(MANIFEST.get("city", {}), ensure_ascii=False, indent=2),
      "",
      "export const spotDistrict = " + json.dumps(MANIFEST.get("district", {}), ensure_ascii=False, indent=2),
      "",
      "export const galleryCredit = { title: '户外出片图集', license: '网络图源 · 仅毕设演示' }",
      ""]
open(os.path.join(ROOT, "src", "data", "gallery.js"), "w", encoding="utf-8").write("\n".join(js))

files = os.listdir(OUT)
total = sum(os.path.getsize(os.path.join(OUT, f)) for f in files)
print("输出图片", len(files), "总大小 %.1f MB" % (total / 1048576))
print("spot 映射", len(MANIFEST["spots"]), "route 映射", len(MANIFEST["routes"]))

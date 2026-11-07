"""构建后处理：把 dist/index.html 修成可双击打开的离线版本。

1. 去掉 script 上的 type="module" / crossorigin —— file:// 下 ES module 会被 CORS 拦截
2. 内联 CSS（如果 Vite 没有单独产出）
3. 把 favicon 的 emoji 换成自绘的山脊标记
"""

import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'dist')
INDEX = os.path.join(DIST, 'index.html')

FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
    "%3Crect width='64' height='64' rx='14' fill='%231e3d29'/%3E"
    "%3Cpath d='M10 46l14-22 9 14 6-9 15 17z' fill='%23e8dcc0'/%3E%3C/svg%3E"
)


def main():
    html = io.open(INDEX, encoding='utf-8').read()

    # 1) 去掉模块化标记，让 IIFE 以普通脚本执行；但必须保留 defer，
    #    否则脚本在 <head> 里同步执行时 #app 还没解析出来，挂载目标为空
    html = html.replace(' type="module"', ' defer')
    html = re.sub(r'\scrossorigin(?:="[^"]*")?', '', html)

    # 2) 若存在外链 CSS 且未被内联，直接内联进 <style>
    m = re.search(r'<link[^>]+rel="stylesheet"[^>]+href="\./(assets/[^"]+\.css)"[^>]*>', html)
    if m:
        css_path = os.path.join(DIST, m.group(1).replace('/', os.sep))
        if os.path.exists(css_path):
            css = io.open(css_path, encoding='utf-8').read()
            html = html.replace(m.group(0), '<style>\n' + css + '\n</style>')

    # 3) favicon 换成自绘标记
    html = re.sub(r'<link\s+rel="icon"[^>]*>', '<link rel="icon" href="%s">' % FAVICON, html)

    io.open(INDEX, 'w', encoding='utf-8').write(html)

    size = os.path.getsize(INDEX)
    print('postbuild ok: dist/index.html %.1f KB' % (size / 1024))


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""把 routes.js 里 path 字段的写法统一成：

    ],
    path: [[..],[..]],
    access: { ... }

反复插字段容易写坏（多一个逗号就整包编译不过），所以统一在这里重建。
"""
import io, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'data', 'routes.js')
ROUTE_START = re.compile(r"\{\s*\n\s*name: '")
PATH_RE = re.compile(r"path: (\[\[.*?\]\])(?=,|\n)")


def main():
    s = io.open(SRC, encoding='utf-8').read()
    starts = [m.start() for m in ROUTE_START.finditer(s)] + [len(s)]
    out = s[:starts[0]]
    kept = 0
    for i in range(len(starts) - 1):
        blk = s[starts[i]:starts[i + 1]]
        pm = PATH_RE.search(blk)
        k = blk.index('\n    ],')
        acc = blk.index('access:', k)
        head = blk[:k]
        tail = blk[acc:]
        if pm:
            kept += 1
            out += head + '\n    ],\n    path: ' + pm.group(1) + ',\n    ' + tail
        else:
            out += head + '\n    ],\n    ' + tail
    io.open(SRC, 'w', encoding='utf-8').write(out)
    print('规范化完成，保留 path', kept, '条')


if __name__ == '__main__':
    main()

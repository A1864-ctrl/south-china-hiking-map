import io
import re

s = io.open('src/data/spotWiki.js', encoding='utf-8').read()
ents = re.findall(r'^\s*"([^"]+)":\s*\{\s*src:\s*"([^"]+)"', s, re.M)
for i, (n, src) in enumerate(ents, 1):
    print(i, n)

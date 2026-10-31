"""Bundle the review for offline sharing; source assets remain separate."""
import base64
import mimetypes
import re
from pathlib import Path

root = Path(__file__).resolve().parent
html = (root / 'prototype/index.html').read_text()
html = html.replace('<link rel="stylesheet" href="style.css">', '<style>' + (root / 'prototype/style.css').read_text() + '</style>')
html = html.replace('<script src="app.js"></script>', '<script>' + (root / 'prototype/app.js').read_text() + '</script>')

# Both optical-size variants must be literal paths before embedding.
html = html.replace("../assets/rat-head${n===16?'-small':''}-PROPOSED.svg", "${n===16?'../assets/rat-head-small-PROPOSED.svg':'../assets/rat-head-PROPOSED.svg'}")
paths = set(re.findall(r'\.\./(?:assets/[^\s\'"<>`)]+|relicrat-(?:light|dark)-PROPOSED\.json)', html))
for relative in sorted(paths, key=len, reverse=True):
    path = root / relative.removeprefix('../')
    mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    encoded = base64.b64encode(path.read_bytes()).decode()
    html = html.replace(relative, f'data:{mime};base64,{encoded}')
assert '../assets/' not in html, 'Unbundled asset reference'
(root / 'RelicRat Review.html').write_text(html)
print(f'Bundled {len(paths)} local references into RelicRat Review.html')

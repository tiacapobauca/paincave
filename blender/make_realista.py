"""Crea realista.html = index.html + recursos de Blender + realista.js (substitueix part del 3D).
Ús: python3 blender/build.py   (només cal si canvien els models)
    python3 blender/make_realista.py"""
import os, json
D = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(D)
html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
assets = open(os.path.join(D, 'out', 'assets.json'), encoding='utf-8').read()
js = open(os.path.join(D, 'realista.js'), encoding='utf-8').read()
assert '</script' not in assets
html = html.replace('<title>PainCave ERG · Kickr Core</title>', '<title>PainCave ERG · Realista</title>', 1)
i = html.rindex('</body>')
html = html[:i] + '<script id="g3assets" type="application/json">' + assets + '</script>\n<script>\n' + js + '</script>\n' + html[i:]
open(os.path.join(ROOT, 'realista.html'), 'w', encoding='utf-8').write(html)
print('realista.html: %.0f kB' % (len(html.encode()) / 1024))

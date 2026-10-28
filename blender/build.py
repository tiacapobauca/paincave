"""Genera tots els recursos 3D de la versió realista: python3 blender/build.py
Sortida: blender/out/assets.json amb les malles (gzip + base64) i les textures (WebP en base64)."""
import sys, os, json, base64, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from common import *
import bike, rider, veg, textures
from PIL import Image

OUT = veg.OUT
only = sys.argv[1:]
pack = Pack()
bike.build(pack)
rider.build(pack)
reset(); veg.build_sprites()
imp = veg.build(pack, os.path.join(OUT, 'leaves.png'))
tex = textures.build()

def webp(path, q=82, size=None):
    im = Image.open(path)
    if size: im = im.resize(size, Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'WEBP', quality=q, method=6)
    return 'data:image/webp;base64,' + base64.b64encode(b.getvalue()).decode()

data = dict(mesh=b64(pack.blob()), imp=imp,
            tex=dict(leaves=webp(os.path.join(OUT, 'leaves.png'), 85), impostors=webp(os.path.join(OUT, 'impostors.png'), 85),
                     **{k: webp(p, q, (256, 512) if k == 'roadN' else None) for k, (p, q) in tex.items()}))
json.dump(data, open(os.path.join(OUT, 'assets.json'), 'w'))
print('mida total: %.0f kB' % (len(json.dumps(data)) / 1024), {k: len(v) // 1024 for k, v in data['tex'].items()}, 'malles', len(data['mesh']) // 1024)

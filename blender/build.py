"""Genera els recursos 3D de l'app amb Blender (bpy):  python3 blender/build.py [etapes]

Etapes: bike rider body veg tex sky  (sense arguments: totes). Cada etapa desa el resultat a blender/out/,
de manera que se'n pot refer només una. Al final sempre es munta la carpeta assets/ de l'app:
  assets/g3.bin   malles (quantitzades + gzip)      assets/*.webp   textures
  assets/g3.json  índex: versió, textures, siluetes dels arbres, colors del cel i del terreny
"""
import sys, os, json, io, pickle, time
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
import bpy
from common import *
from PIL import Image

OUT = os.path.join(D, 'out'); ASSETS = os.path.join(os.path.dirname(D), 'assets')
os.makedirs(OUT, exist_ok=True); os.makedirs(ASSETS, exist_ok=True)
STAGES = ['bike', 'rider', 'body', 'veg', 'tex', 'sky']
todo = [a for a in sys.argv[1:] if a in STAGES] or STAGES

def stash(name, obj): pickle.dump(obj, open(os.path.join(OUT, name + '.pkl'), 'wb'))
def fetch(name): return pickle.load(open(os.path.join(OUT, name + '.pkl'), 'rb'))

for st in todo:
    t = time.time()
    if st == 'bike':
        import bike; p = Pack(); bike.build(p); stash('bike', p)
    elif st == 'rider':
        import rider; p = Pack(); rider.build(p); stash('rider', p)
    elif st == 'body':
        import body; p = Pack(); body.build(p); stash('body', p)
    elif st == 'veg':
        import veg; p = Pack(); reset(); veg.build_sprites(); imp = veg.build(p, os.path.join(OUT, 'leaves.png')); stash('veg', (p, imp))
    elif st == 'tex':
        import textures; tex = textures.build(); stash('tex', (tex, textures.TERRAIN))
    elif st == 'sky':
        import sky; stash('sky', sky.build())
    print('== %s: %.0f s' % (st, time.time() - t))

# ---------------------------------------------------------------- muntatge
pack = Pack()
pack.merge(fetch('bike')); pack.merge(fetch('rider')); pack.merge(fetch('body'))
vp, imp = fetch('veg'); pack.merge(vp)
tex, terrain = fetch('tex'); skym = fetch('sky')
blob = pack.blob(); open(os.path.join(ASSETS, 'g3.bin'), 'wb').write(blob)
files = dict(leaves=(os.path.join(OUT, 'leaves.png'), 86), impostors=(os.path.join(OUT, 'impostors.png'), 86), sky=(os.path.join(OUT, 'sky.png'), 90), **tex)
SIZE = dict(roadN=(256, 512))
sizes = {'g3.bin': len(blob)}
for k, (path, q) in files.items():
    im = Image.open(path)
    if k in SIZE: im = im.resize(SIZE[k], Image.LANCZOS)
    im.save(os.path.join(ASSETS, k + '.webp'), 'WEBP', quality=q, method=6)
    sizes[k] = os.path.getsize(os.path.join(ASSETS, k + '.webp'))
old = {}
try: old = json.load(open(os.path.join(ASSETS, 'g3.json')))
except Exception: pass
meta = dict(v=int(old.get('v', 0)) + 1, tex=sorted(files), imp=imp, sky=skym, terrain=terrain)
json.dump(meta, open(os.path.join(ASSETS, 'g3.json'), 'w'), separators=(',', ':'))
print('assets/: %.0f kB' % (sum(sizes.values()) / 1024), {k: v // 1024 for k, v in sizes.items()})

"""Vegetació mediterrània i roques.

1. Sprites de fulles (atles 1024×512, cel·les de 256): es modelen branquetes amb fulles reals i es
   renderitzen amb Cycles des de dalt (o de costat, l'herba), amb fons transparent.
2. Arbres: tronc i branques (tubs amb soroll) + targetes de fulles amb l'sprite, amb normals
   esfèriques (il·luminació suau de copa). Dos nivells de detall.
3. Siluetes llunyanes (impostors): cada arbre renderitzat de costat amb Cycles (atles 1024×512).
4. Roques: icosfera desplaçada amb soroll, amb l'oclusió ambiental al color.
Materials: 0 = escorça / roca (color per vèrtex) · 1 = fulles (atles d'sprites × color per vèrtex)
"""
import bpy, math, random, os, bmesh
from mathutils import Vector, Matrix, noise
from common import *

OUT = os.path.join(os.path.dirname(__file__), 'out')
CELL = 256
# cel·les de l'atles de fulles (columna, fila) — fila 0 = a dalt de la imatge
SPR = dict(pine=(0, 0), olive=(1, 0), carob=(2, 0), lentisk=(3, 0), cypress=(0, 1), palm=(1, 1), grass=(2, 1), flowers=(3, 1))

# ------------------------------------------------------------ render d'sprites
def vc_material(name='vc', rough=0.65, sss=False):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    a = nt.nodes.new('ShaderNodeVertexColor'); a.layer_name = 'Col'
    nt.links.new(a.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    return m

def render_setup(size_x, size_y, ortho, loc, rot, samples=48, sun=True, world=0.75):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = size_x, size_y
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'Standard'
    w = sc.world or bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (1, 1, 1, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = world
    cam = bpy.data.objects.get('cam')
    if not cam:
        cam = link(bpy.data.objects.new('cam', bpy.data.cameras.new('cam')))
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
    cam.location = loc; cam.rotation_euler = rot; sc.camera = cam
    if sun and not bpy.data.objects.get('sun'):
        s = link(bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')))
        s.rotation_euler = (0.5, 0.3, 0.6); s.data.energy = 1.4
    return sc

def render_to(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

def leaf_mesh(bm, base, d, side, L, W, color_fn, col_layer, segs=4):
    """Fulla: tira de quads amb forma de llança, lleugerament corbada."""
    pts = []
    for i in range(segs + 1):
        t = i / segs
        w = W * math.sin(math.pi * min(1, t * 1.15)) * (1 - t * 0.2)
        c = base + d * (L * t) + Vector((0, 0, -0.15 * L * t * t))
        pts.append((c - side * w, c + side * w))
    vs = [(bm.verts.new(a), bm.verts.new(b)) for a, b in pts]
    col = color_fn()
    for i in range(segs):
        f = bm.faces.new((vs[i][0], vs[i][1], vs[i + 1][1], vs[i + 1][0]))
        for l in f.loops: l[col_layer] = (*col, 1)

def twig_sprite(kind, rnd):
    """Branqueta amb fulles dins el quadrat [-0,5, 0,5]² (vista de dalt)."""
    bm = bmesh.new(); cl = bm.loops.layers.float_color.new('Col')
    def stem(a, b, r, col):
        rings = tube_bm(bm, [a, b], r, 5, cap=False)
        for ring in rings:
            for v in ring:
                for l in v.link_loops: l[cl] = (*col, 1)
    if kind in ('pine', 'cypress'):
        # pi: borles d'agulles (2 per beina), llargues; xiprer: ramets d'escates curtes i denses
        for k in range(7 if kind == 'pine' else 11):
            a = rnd.uniform(0, 2 * math.pi); r0 = rnd.uniform(0.0, 0.18 if kind == 'pine' else 0.3)
            c = Vector((math.cos(a) * r0, math.sin(a) * r0, rnd.uniform(-0.03, 0.03)))
            n = 70 if kind == 'pine' else 45
            for i in range(n if kind == 'pine' else 60):
                th = rnd.uniform(0, 2 * math.pi); ph = rnd.uniform(0.2, 1.3)
                d = Vector((math.cos(th) * math.sin(ph), math.sin(th) * math.sin(ph), math.cos(ph) * 0.5)).normalized()
                L = rnd.uniform(0.22, 0.34) if kind == 'pine' else rnd.uniform(0.1, 0.2)
                side = d.cross(Vector((0, 0, 1))).normalized()
                g = rnd.uniform(0.8, 1.15)
                colf = (lambda g=g: (0.16 * g, 0.24 * g, 0.075 * g)) if kind == 'pine' else (lambda g=g: (0.045 * g, 0.1 * g, 0.04 * g))
                leaf_mesh(bm, c, d, side, L, 0.006 if kind == 'pine' else 0.022, colf, cl, 2 if kind == 'pine' else 3)
        stem(Vector((0, -0.48, 0)), Vector((0, 0.05, 0)), 0.012, (0.18, 0.12, 0.07))
    elif kind in ('olive', 'carob', 'lentisk'):
        P = dict(olive=(0.17, 0.028, 26, (0.21, 0.25, 0.14), (0.38, 0.42, 0.33)),
                 carob=(0.085, 0.05, 20, (0.045, 0.095, 0.03), (0.09, 0.14, 0.05)),
                 lentisk=(0.06, 0.028, 34, (0.1, 0.16, 0.055), (0.16, 0.2, 0.09)))[kind]
        L0, W0, nper, top, under = P
        stems = []
        for k in range(6):
            a = -0.75 + 1.5 * k / 5 + rnd.uniform(-0.1, 0.1)
            s = Vector((rnd.uniform(-0.04, 0.04), -0.47, 0))
            L = rnd.uniform(0.62, 0.8) * (1 - 0.25 * abs(a))
            e = s + Vector((math.sin(a), math.cos(a), 0)) * L
            stem(s, e, 0.006, (0.2, 0.15, 0.1)); stems.append((s, e))
        for s, e in stems:
            for i in range(nper):
                t = rnd.uniform(0.1, 1.0)
                b = s.lerp(e, t)
                along = (e - s).normalized()
                sd = 1 if i % 2 else -1
                d = (along * 0.5 + along.cross(Vector((0, 0, 1))) * sd).normalized()
                d.z = rnd.uniform(-0.25, 0.35); d.normalize()
                side = d.cross(Vector((0, 0, 1))).normalized()
                L = L0 * rnd.uniform(0.75, 1.2)
                if b.length + L > 0.5: continue
                up = rnd.random() < (0.55 if kind == 'olive' else 0.8)
                g = rnd.uniform(0.85, 1.15)
                col = top if up else under
                leaf_mesh(bm, b, d, side, L, W0 * rnd.uniform(0.8, 1.1), lambda col=col, g=g: (col[0] * g, col[1] * g, col[2] * g), cl, 4)
    elif kind == 'palm':
        # ventall de margalló: segments estrets en semicercle
        n = 22
        for i in range(n):
            a = math.pi * (0.08 + 0.84 * i / (n - 1))
            d = Vector((math.cos(a), math.sin(a) * 0.95, 0)).normalized()
            side = d.cross(Vector((0, 0, 1))).normalized()
            g = rnd.uniform(0.85, 1.1)
            leaf_mesh(bm, Vector((0, -0.42, 0)) + d * 0.04, d, side, rnd.uniform(0.62, 0.78), 0.022, lambda g=g: (0.13 * g, 0.2 * g, 0.08 * g), cl, 5)
        stem(Vector((0, -0.5, 0)), Vector((0, -0.4, 0)), 0.012, (0.25, 0.22, 0.12))
    elif kind in ('grass', 'flowers'):
        # mata d'herba seca vista de costat (pla XZ): fulles corbes que surten de baix
        for i in range(90):
            x0 = rnd.gauss(0, 0.09)
            h = rnd.uniform(0.45, 0.92)
            lean = rnd.gauss(0, 0.25)
            b = Vector((x0, rnd.uniform(-0.05, 0.05), -0.5))
            d = Vector((lean, 0, 1)).normalized()
            side = Vector((1, 0, 0)).cross(d).normalized() if abs(d.x) < 0.9 else Vector((0, 1, 0))
            side = Vector((d.z, 0, -d.x)).normalized()
            dry = rnd.random()
            col = (0.42, 0.36, 0.17) if dry < 0.55 else (0.3, 0.3, 0.12) if dry < 0.8 else (0.18, 0.24, 0.08)
            g = rnd.uniform(0.8, 1.2)
            # tija corbada: dos trams
            m = b + d * h * 0.55
            d2 = (d + Vector((lean * 0.8, 0, -0.1))).normalized()
            leaf_mesh(bm, b, d, side, h * 0.55, 0.012, lambda col=col, g=g: (col[0] * g, col[1] * g, col[2] * g), cl, 2)
            leaf_mesh(bm, m, d2, side, h * 0.45, 0.009, lambda col=col, g=g: (col[0] * g, col[1] * g, col[2] * g), cl, 2)
        if kind == 'flowers':
            for i in range(16):
                c = Vector((rnd.gauss(0, 0.14), -0.08, rnd.uniform(-0.05, 0.36)))
                pal = rnd.choice([(0.85, 0.72, 0.1), (0.9, 0.9, 0.85), (0.6, 0.25, 0.55), (0.85, 0.35, 0.1)])
                fb = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.022, matrix=Matrix.Translation(c))
                for f in {f for v in fb['verts'] for f in v.link_faces}:
                    for l in f.loops: l[cl] = (*pal, 1)
    me = bpy.data.meshes.new(kind); bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new(kind, me))
    me.color_attributes.active_color = me.color_attributes['Col']
    for p in me.polygons: p.use_smooth = False
    ob.data.materials.append(vc_material())
    return ob

def build_sprites():
    from PIL import Image
    tiles = {}
    for kind in SPR:
        reset()
        rnd = random.Random(sum(map(ord, kind)))   # llavor fixa: el resultat és sempre igual
        ob = twig_sprite(kind, rnd)
        side = kind in ('grass', 'flowers')
        if side:
            render_setup(CELL, CELL, 1.0, (0, -5, 0), (math.pi / 2, 0, 0), 64)
        else:
            render_setup(CELL, CELL, 1.0, (0, 0, 5), (0, 0, 0), 64)
        p = os.path.join(OUT, 'spr_%s.png' % kind)
        render_to(p)
        tiles[kind] = Image.open(p).convert('RGBA')
    atlas = Image.new('RGBA', (CELL * 4, CELL * 2), (0, 0, 0, 0))
    for kind, (cx, cy) in SPR.items():
        atlas.paste(tiles[kind], (cx * CELL, cy * CELL))
    atlas = bleed(atlas)
    atlas.save(os.path.join(OUT, 'leaves.png'))
    return atlas

def bleed(img, it=6):
    """Escampa el color dels píxels opacs cap als transparents (evita vores fosques amb mipmaps)."""
    import numpy as np
    a = np.asarray(img).astype(np.float32)
    rgb, al = a[..., :3], a[..., 3] > 8
    for _ in range(it):
        acc = np.zeros_like(rgb); n = np.zeros(al.shape, np.float32)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            m = np.roll(al, (dy, dx), (0, 1)); acc += np.roll(rgb, (dy, dx), (0, 1)) * m[..., None]; n += m
        fill = (~al) & (n > 0)
        rgb[fill] = acc[fill] / n[fill][:, None]; al = al | fill
    a[..., :3] = rgb
    from PIL import Image
    return Image.fromarray(a.clip(0, 255).astype('uint8'), 'RGBA')

# ------------------------------------------------------------------- arbres
def cell_uv(kind):
    cx, cy = SPR[kind]
    # V de Blender/three: 0 a baix de la imatge
    return (cx / 4, 1 - (cy + 1) / 2, (cx + 1) / 4, 1 - cy / 2)

class Tree:
    def __init__(self, seed):
        self.rnd = random.Random(seed)
        self.bm = bmesh.new(); self.cl = self.bm.loops.layers.float_color.new('Col')
        self.cards = bmesh.new(); self.ccl = self.cards.loops.layers.float_color.new('Col'); self.cuv = self.cards.loops.layers.uv.new('UV')
        self.cnorm = []
        self.tips = []

    def limb(self, pts, r0, r1, col, seg=7):
        n = len(pts)
        radii = [r0 + (r1 - r0) * i / (n - 1) for i in range(n)]
        rings = tube_bm(self.bm, pts, radii, seg, cap=True)
        for ring in rings:
            for v in ring:
                # escorça: variació longitudinal (clivelles) amb soroll
                k = 0.75 + 0.35 * noise.noise(v.co * Vector((40, 40, 6)))
                for l in v.link_loops: l[self.cl] = (col[0] * k, col[1] * k, col[2] * k, 1)

    def branch(self, start, d, L, r, depth, P):
        rnd = self.rnd
        pts = [start]; p = start.copy(); dd = d.copy()
        steps = max(2, int(L / 0.35))
        for i in range(steps):
            dd = (dd + Vector((rnd.gauss(0, P['wob']), rnd.gauss(0, P['wob']), rnd.gauss(0, P['wob']) * 0.5 + P['up']))).normalized()
            p = p + dd * (L / steps); pts.append(p.copy())
        self.limb(pts, r, r * P['taper'], P['bark'], 7 if depth == 0 else 5)
        if depth >= P['depth']:
            self.tips.append((p, dd)); return
        nch = P['kids'][depth]
        for k in range(nch):
            t = rnd.uniform(P['from'][depth], 1.0)
            i = min(len(pts) - 1, int(t * (len(pts) - 1)))
            base = pts[i]
            az = rnd.uniform(0, 2 * math.pi) if k else math.atan2(dd.y, dd.x)
            el = rnd.uniform(*P['spread'][depth])
            nd = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))).normalized()
            self.branch(base, (nd + dd * 0.3).normalized(), L * P['lr'][depth] * rnd.uniform(0.75, 1.15), r * P['rr'], depth + 1, P)

    def foliage(self, kind, center, ell, n, size, tint=(1, 1, 1), flat=0.0):
        """n targetes dins un el·lipsoide; normals cap enfora de la copa (center global)."""
        rnd = self.rnd; u0, v0, u1, v1 = cell_uv(kind)
        for i in range(n):
            while True:
                q = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
                if q.length <= 1: break
            c = ell[0] + Vector((q.x * ell[1].x, q.y * ell[1].y, q.z * ell[1].z))
            outw = (c - center); outw.z *= 0.6
            nrm = (outw.normalized() * 0.75 + Vector((0, 0, 0.55))).normalized()
            # orientació de la targeta: aleatòria amb tendència a l'horitzontal (flat)
            a = rnd.uniform(0, 2 * math.pi); tilt = rnd.uniform(-1.2, 1.2) * (1 - flat) + rnd.uniform(-0.25, 0.25) * flat
            fwd = Vector((math.cos(a), math.sin(a), 0))
            up = Vector((0, 0, 1))
            ax1 = fwd; ax2 = (up * math.cos(tilt) + fwd.cross(up) * math.sin(tilt)).normalized()
            if flat > 0.5: ax2 = fwd.cross(up) * math.cos(tilt) + up * math.sin(tilt)
            s = size * rnd.uniform(0.8, 1.2)
            corners = [c - ax1 * s / 2 - ax2 * s / 2, c + ax1 * s / 2 - ax2 * s / 2, c + ax1 * s / 2 + ax2 * s / 2, c - ax1 * s / 2 + ax2 * s / 2]
            vs = [self.cards.verts.new(p) for p in corners]
            f = self.cards.faces.new(vs)
            g = rnd.uniform(0.82, 1.12)
            # més fosc a l'interior de la copa
            depth = max(0.0, 1 - (c - center).length / max(ell[1].length * 0.9, 0.1))
            dk = g * (1 - 0.25 * depth)
            uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            for l, uv in zip(f.loops, uvs):
                l[self.ccl] = (tint[0] * dk, tint[1] * dk, tint[2] * dk, 1)
                l[self.cuv].uv = uv
            self.cnorm.append(nrm)

    def objects(self, name):
        me = bpy.data.meshes.new(name + '_wood'); self.bm.to_mesh(me); self.bm.free()
        wood = link(bpy.data.objects.new(name + '_wood', me)); smooth(wood)
        me.color_attributes.active_color = me.color_attributes['Col']
        set_mat(wood, 0)
        me2 = bpy.data.meshes.new(name + '_leaf'); self.cards.to_mesh(me2); self.cards.free()
        leaf = link(bpy.data.objects.new(name + '_leaf', me2)); set_mat(leaf, 1)
        me2.color_attributes.active_color = me2.color_attributes['Col']
        loops = []
        for p, nrm in zip(me2.polygons, self.cnorm):
            p.use_smooth = True
            for _ in p.loop_indices: loops.append(nrm)
        me2.normals_split_custom_set([tuple(n) for n in loops])
        return wood, leaf

PINE = dict(bark=(0.34, 0.26, 0.2), wob=0.12, up=0.05, taper=0.55, depth=2, kids=[5, 3], frm=None, lr=[0.42, 0.5], rr=0.5,
            spread=[(0.15, 0.7), (0.0, 0.5)], **{'from': [0.55, 0.4]})
OLIVE = dict(bark=(0.42, 0.38, 0.32), wob=0.35, up=0.0, taper=0.6, depth=2, kids=[4, 3], lr=[0.75, 0.55], rr=0.55,
             spread=[(0.35, 0.9), (0.1, 0.7)], **{'from': [0.5, 0.3]})
CAROB = dict(bark=(0.34, 0.27, 0.21), wob=0.2, up=0.02, taper=0.6, depth=2, kids=[5, 3], lr=[0.75, 0.55], rr=0.55,
             spread=[(0.25, 0.8), (0.1, 0.7)], **{'from': [0.5, 0.3]})

def make_pine(seed, lod):
    T = Tree(seed); rnd = T.rnd
    lean = Vector((rnd.uniform(-0.18, 0.18), rnd.uniform(-0.18, 0.18), 1)).normalized()
    if lod == 0:
        T.branch(Vector((0, 0, -0.1)), lean, 5.6, 0.2, 0, PINE)
        top = sum((t[0] for t in T.tips), Vector()) / len(T.tips)
        for p, d in T.tips:   # pinyes de capçada aplanades a les puntes
            T.foliage('pine', top, (p + Vector((0, 0, 0.3)), Vector((1.3, 1.3, 0.7))), 24, 1.35, flat=0.3)
    else:
        trunk = [Vector((0, 0, -0.1)) + lean * 5.5 * i / 3 for i in range(4)]
        T.limb(trunk, 0.2, 0.1, PINE['bark'], 5)
        top = trunk[-1] + Vector((0, 0, 0.6))
        T.foliage('pine', top, (top, Vector((2.4, 2.4, 1.0))), 30, 2.6, flat=0.6)
    return T.objects('pine')

def make_olive(seed, lod):
    T = Tree(seed); rnd = T.rnd
    if lod == 0:
        # tronc nuós, gruixut i retorçat, que es divideix en 3-4 braços
        base = [Vector((0, 0, -0.1)), Vector((0.1, 0.05, 0.4)), Vector((0.05, -0.08, 0.9)), Vector((0.15, 0, 1.25))]
        T.limb(base, 0.32, 0.22, OLIVE['bark'], 9)
        for k in range(4):
            a = k * math.pi / 2 + rnd.uniform(-0.4, 0.4)
            T.branch(base[-1], Vector((math.cos(a) * 0.7, math.sin(a) * 0.7, 1)).normalized(), 1.6, 0.13, 1, OLIVE)
        top = Vector((0, 0, 2.6))
        for p, d in T.tips:
            T.foliage('olive', top, (p + Vector((0, 0, 0.15)), Vector((0.85, 0.85, 0.6))), 15, 1.1, flat=0.3)
    else:
        T.limb([Vector((0, 0, -0.1)), Vector((0.1, 0, 0.8)), Vector((0.1, 0, 1.6))], 0.28, 0.14, OLIVE['bark'], 5)
        T.foliage('olive', Vector((0, 0, 2.5)), (Vector((0, 0, 2.5)), Vector((1.7, 1.7, 1.0))), 20, 1.6, flat=0.3)
    return T.objects('olive')

def make_carob(seed, lod):
    T = Tree(seed); rnd = T.rnd
    if lod == 0:
        base = [Vector((0, 0, -0.1)), Vector((0.05, 0, 0.7)), Vector((0, 0.05, 1.3))]
        T.limb(base, 0.3, 0.22, CAROB['bark'], 8)
        for k in range(5):
            a = k * 2 * math.pi / 5 + rnd.uniform(-0.3, 0.3)
            T.branch(base[-1], Vector((math.cos(a) * 0.8, math.sin(a) * 0.8, 1)).normalized(), 1.7, 0.12, 1, CAROB)
        top = Vector((0, 0, 2.8))
        T.foliage('carob', top, (top, Vector((2.3, 2.3, 1.45))), 190, 1.25, flat=0.2)
    else:
        T.limb([Vector((0, 0, -0.1)), Vector((0, 0, 1.6))], 0.28, 0.16, CAROB['bark'], 5)
        T.foliage('carob', Vector((0, 0, 2.7)), (Vector((0, 0, 2.7)), Vector((2.4, 2.4, 1.5))), 22, 1.9, flat=0.2)
    return T.objects('carob')

def make_cypress(seed, lod):
    T = Tree(seed); rnd = T.rnd
    T.limb([Vector((0, 0, -0.1)), Vector((0, 0, 1.0))], 0.16, 0.12, (0.2, 0.15, 0.11), 6)
    n = 240 if lod == 0 else 40
    for i in range(n):
        h = rnd.uniform(0.5, 8.4) if lod == 0 else 0.5 + 7.8 * (i + 0.5) / n
        w = 0.62 * math.sin(math.pi * min(1, (h + 0.4) / 9.2)) ** 0.8 + 0.05
        c = Vector((0, 0, h))
        T.foliage('cypress', Vector((0, 0, h)), (c, Vector((w * 0.6, w * 0.6, 0.3))), 1, (0.6 if lod == 0 else 1.1) * (0.6 + w * 0.6), flat=0.0)
    return T.objects('cypress')

def make_shrub(seed, lod):
    T = Tree(seed); rnd = T.rnd
    for k in range(5):
        a = rnd.uniform(0, 2 * math.pi)
        T.limb([Vector((0, 0, -0.05)), Vector((math.cos(a) * 0.35, math.sin(a) * 0.35, 0.55))], 0.035, 0.015, (0.2, 0.16, 0.12), 4)
    n = 34 if lod == 0 else 10
    T.foliage('lentisk', Vector((0, 0, 0.1)), (Vector((0, 0, 0.55)), Vector((1.05, 0.95, 0.55))), n, 0.75 if lod == 0 else 1.1, flat=0.3)
    return T.objects('shrub')

def make_palm(seed, lod):
    T = Tree(seed); rnd = T.rnd
    u0, v0, u1, v1 = cell_uv('palm')
    n = 16 if lod == 0 else 7
    for i in range(n):
        a = i * 2 * math.pi / n + rnd.uniform(-0.2, 0.2)
        el = rnd.uniform(0.35, 1.1)
        L = rnd.uniform(0.7, 1.0)
        d = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
        T.limb([Vector((0, 0, 0)), d * L * 0.55], 0.012, 0.008, (0.3, 0.33, 0.15), 4)
        # ventall: targeta perpendicular al pecíol
        c = d * L * 0.55; side = d.cross(Vector((0, 0, 1))).normalized(); up = side.cross(d).normalized()
        fan_up = (d * 0.75 + up * 0.25).normalized()
        s = 0.95
        corners = [c - side * s / 2, c + side * s / 2, c + side * s / 2 + fan_up * s, c - side * s / 2 + fan_up * s]
        vs = [T.cards.verts.new(p) for p in corners]
        f = T.cards.faces.new(vs)
        g = rnd.uniform(0.85, 1.1)
        for l, uv in zip(f.loops, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]):
            l[T.ccl] = (g, g, g, 1); l[T.cuv].uv = uv
        T.cnorm.append((up * 0.4 + Vector((0, 0, 0.8))).normalized())
    return T.objects('palm')

def make_grass(seed, lod):
    T = Tree(seed); rnd = T.rnd
    for k, kind in enumerate(('grass', 'flowers', 'grass')):
        u0, v0, u1, v1 = cell_uv(kind)
        a = k * math.pi / 3
        ax = Vector((math.cos(a), math.sin(a), 0))
        w, h = 1.2, 0.95
        corners = [-ax * w / 2, ax * w / 2, ax * w / 2 + Vector((0, 0, h)), -ax * w / 2 + Vector((0, 0, h))]
        f = T.cards.faces.new([T.cards.verts.new(p) for p in corners])
        for l, uv in zip(f.loops, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]):
            l[T.ccl] = (1, 1, 1, 1); l[T.cuv].uv = uv
        T.cnorm.append(Vector((0, 0, 1)))
    return T.objects('grass')

def rock(seed, lod):
    rnd = random.Random(seed)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4 if lod == 0 else 2, radius=1)
    ob = bpy.context.active_object; ob.name = 'rock'
    off = Vector((seed * 3.1, seed * 1.7, 0))
    for v in ob.data.vertices:
        p = v.co.copy()
        d = noise.fractal(p * 1.3 + off, 0.55, 2.0, 5, noise_basis='PERLIN_ORIGINAL') * 0.32
        # facetes de calcària: es talla amb plans
        ridged = abs(noise.noise(p * 2.2 + off)) * 0.12
        p = p * (1 + d - ridged)
        p.z = p.z * 0.62 if p.z > 0 else p.z * 0.35
        v.co = Vector((p.x * 1.25, p.y, p.z + 0.25))
    smooth(ob)
    def col(p, n):
        k = 0.85 + 0.25 * noise.noise(p * 3 + off)
        base = (0.36 * k, 0.33 * k, 0.29 * k)
        if n.z > 0.75: base = (base[0] * 0.75, base[1] * 0.8, base[2] * 0.62)   # líquens / pols a dalt
        return base
    paint(ob, col)
    return ob

SPECIES = [('pine', make_pine), ('shrub', make_shrub), ('rock', rock), ('olive', make_olive), ('carob', make_carob),
           ('cypress', make_cypress), ('palm', make_palm), ('grass', make_grass)]
IMP = ['pine', 'olive', 'carob', 'cypress']   # espècies amb silueta llunyana (cel·les de 512×512)

def leaf_material(atlas_path):
    m = bpy.data.materials.get('leaf')
    if m: return m
    m = bpy.data.materials.new('leaf'); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(atlas_path); tex.interpolation = 'Linear'
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UV'
    nt.links.new(uv.outputs['UV'], tex.inputs['Vector'])
    vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
    nt.links.new(tex.outputs['Color'], mul.inputs[6]); nt.links.new(vc.outputs['Color'], mul.inputs[7])
    nt.links.new(mul.outputs[2], b.inputs['Base Color'])
    nt.links.new(tex.outputs['Alpha'], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = 0.8
    return m

def build(pack, atlas_path):
    from PIL import Image
    print('vegetació')
    imps = {}
    for sp, fn in SPECIES:
        for lod in (0, 1):
            if sp == 'grass' and lod: continue
            reset()
            res = fn(11 + lod, lod)
            obs = list(res) if isinstance(res, tuple) else [res]
            if sp == 'grass': obs = obs[1:]
            wood = obs[0]
            if sp != 'grass': bake_ao([wood] if sp != 'rock' else obs, strength=0.6 if sp != 'rock' else 0.75, dist=1.0 if sp != 'rock' else 0.6, floor=True)
            pack.add('%s%d' % (sp, lod), obs)
            if lod == 0 and sp in IMP:
                # silueta: render ortogràfic de costat
                lm = leaf_material(atlas_path); wm = vc_material('bark', 0.9)
                for o in obs:
                    o.data.materials.clear(); o.data.materials.append(wm)
                    if o.name.endswith('_leaf'): o.data.materials.clear(); o.data.materials.append(wm); o.data.materials.append(lm); set_mat(o, 1)
                W, H = dict(pine=(7.4, 9.2), olive=(5.6, 4.4), carob=(6.4, 5.2), cypress=(2.6, 9.6))[sp]
                Hc = max(W, H)
                render_setup(CELL * 2, CELL * 2, Hc, (0, -30, Hc / 2 - 0.15), (math.pi / 2, 0, 0), 96, world=1.35)
                p = os.path.join(OUT, 'imp_%s.png' % sp)
                render_to(p)
                imps[sp] = (Image.open(p).convert('RGBA'), W, Hc)
    atlas = Image.new('RGBA', (CELL * 8, CELL * 2), (0, 0, 0, 0))
    meta = {}
    for i, sp in enumerate(IMP):
        img, W, Hc = imps[sp]
        atlas.paste(img, (i * CELL * 2, 0))
        meta[sp] = dict(i=i, w=Hc, h=Hc)   # amplada i alçada reals de la cel·la (m)
    atlas = bleed(atlas, 8)
    atlas.save(os.path.join(OUT, 'impostors.png'))
    return meta

def preview_objs():
    atlas = os.path.join(OUT, 'leaves.png')
    lm = leaf_material(atlas); wm = vc_material('bark', 0.9)
    out = []
    for i, (sp, fn) in enumerate(SPECIES):
        res = fn(11, 0)
        obs = list(res) if isinstance(res, tuple) else [res]
        for o in obs:
            o.location = ((i % 4) * 7 - 10, 0, -(i // 4) * 9)
            o.data.materials.clear(); o.data.materials.append(wm)
            if o.name.endswith('_leaf'): o.data.materials.append(lm); set_mat(o, 1)
            out.append(o)
    return out

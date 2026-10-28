"""Ciclista: peces del cos que l'app col·loca entre articulacions (cinemàtica inversa).

Cada segment (tors, cuixa, bessó, braç, avantbraç) es modela al llarg de Z de -0,5 a 0,5 (Blender),
que l'app escala a la longitud real; les seccions són en metres.
Orientació a l'app (eix local x = X de Blender):
  tors: +X = pit/panxa · cuixa: +X = isquiotibials (sota) · bessó: +X = darrere (bessó)
  braç: +X = tríceps · avantbraç: +X = part de sota.
Materials: 0 = color per vèrtex · 1 = color de l'equip (mallot, × color per vèrtex) · 2 = brillant (ulleres)
"""
import bpy, math, bmesh
from mathutils import Vector
from common import *

SKIN = (0.48, 0.25, 0.15)
BLACK = (0.018, 0.018, 0.02)
WHITE = (0.82, 0.82, 0.83)
JERSEY = (1, 1, 1)   # es tenyeix amb el color de l'equip

def loft(name, secs, seg=16, color=None, mat=None, caps=True, sub=0):
    """secs: [(t, rx_pos, rx_neg, rz, dx)] amb t de 0 a 1 (Z de -0,5 a 0,5). color(t, a) -> rgb; mat(t, a) -> índex."""
    bm = bmesh.new(); rings = []
    def at(t):
        i = 0
        while i < len(secs) - 2 and secs[i + 1][0] < t: i += 1
        a, b = secs[i], secs[i + 1]
        f = (t - a[0]) / max(1e-6, b[0] - a[0]); f = f * f * (3 - 2 * f)
        return [a[k] + (b[k] - a[k]) * f for k in range(1, 5)]
    ts = sorted(set([s[0] for s in secs] + [i / 16 for i in range(17)]))
    for t in ts:
        rp, rn, rz, dx = at(t)
        ring = []
        for s in range(seg):
            a = 2 * math.pi * s / seg
            c, sn = math.cos(a), math.sin(a)
            rx = rp if c > 0 else rn
            ring.append(bm.verts.new((dx + c * rx, sn * rz, t - 0.5)))
        rings.append((t, ring))
    for i in range(len(rings) - 1):
        A, B = rings[i][1], rings[i + 1][1]
        for s in range(seg):
            s1 = (s + 1) % seg
            bm.faces.new((A[s], A[s1], B[s1], B[s]))
    if caps:
        for (t, ring), rev in ((rings[0], True), (rings[-1], False)):
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / seg)
            for s in range(seg):
                s1 = (s + 1) % seg
                bm.faces.new((c, ring[s1], ring[s]) if rev else (c, ring[s], ring[s1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = new_obj(name, bm); smooth(ob)
    if sub: subsurf(ob, sub)
    ensure_col(ob)
    me = ob.data
    col = me.color_attributes['Col']
    for p in me.polygons:
        cz = sum((me.vertices[v].co for v in p.vertices), Vector()) / len(p.vertices)
        t = cz.z + 0.5; a = math.atan2(cz.y, cz.x)
        if mat: p.material_index = mat(t, a)
        if color:
            rgb = color(t, a)
            for li in p.loop_indices: col.data[li].color = (rgb[0], rgb[1], rgb[2], 1)
    return ob

def torso():
    # t: 0 = maluc, 1 = base del coll. Pit (+X) i esquena (-X); amplada (Z de l'app) màxima a les espatlles
    secs = [(0.0, 0.07, 0.08, 0.13, 0.0), (0.12, 0.085, 0.1, 0.14, -0.005), (0.35, 0.09, 0.1, 0.135, -0.01), (0.6, 0.105, 0.105, 0.155, -0.005),
            (0.8, 0.105, 0.1, 0.19, 0.0), (0.9, 0.085, 0.085, 0.185, 0.0), (0.96, 0.055, 0.06, 0.1, 0.01), (1.0, 0.045, 0.045, 0.06, 0.012)]
    def color(t, a):
        if abs(math.sin(a)) > 0.975 and 0.1 < t < 0.68: return BLACK  # panells laterals (estrets)
        if abs(a) < 0.06 and 0.25 < t < 0.95: return (0.6, 0.6, 0.62) # cremallera
        if t < 0.08: return BLACK                                     # culot
        return JERSEY
    def mat(t, a):
        c = color(t, a)
        return 1 if c == JERSEY else 0
    ob = loft('torso', secs, 22, color, mat)
    # butxaques del darrere (bony a l'esquena, a baix)
    for v in ob.data.vertices:
        t = v.co.z + 0.5
        if v.co.x < -0.05 and 0.08 < t < 0.3 and abs(v.co.y) < 0.11:
            v.co.x -= 0.012 * math.sin(math.pi * (t - 0.08) / 0.22)
    return ob

def limb(name, secs, color, mat):
    return loft(name, secs, 14, color, mat)

def thigh():
    # 0 = maluc, 1 = genoll. Quàdriceps a -X (a dalt), isquiotibials a +X
    secs = [(0.0, 0.072, 0.078, 0.078, 0.0), (0.12, 0.078, 0.086, 0.08, 0.0), (0.45, 0.064, 0.074, 0.066, 0.0), (0.75, 0.05, 0.062, 0.054, 0.0),
            (0.9, 0.044, 0.05, 0.048, 0.0), (1.0, 0.043, 0.045, 0.045, 0.0)]
    col = lambda t, a: BLACK if t < 0.8 else (0.05, 0.05, 0.055) if t < 0.84 else SKIN
    return limb('thigh', secs, col, lambda t, a: 0)

def calf():
    # 0 = genoll, 1 = turmell. Bessó a +X (darrere), tíbia a -X
    secs = [(0.0, 0.042, 0.043, 0.045, 0.0), (0.12, 0.055, 0.04, 0.047, 0.004), (0.3, 0.065, 0.038, 0.05, 0.008), (0.55, 0.048, 0.033, 0.04, 0.005),
            (0.8, 0.033, 0.028, 0.031, 0.0), (1.0, 0.03, 0.027, 0.029, 0.0)]
    col = lambda t, a: WHITE if t > 0.8 else (0.12, 0.3, 0.6) if t > 0.78 else SKIN
    return limb('calf', secs, col, lambda t, a: 0)

def uarm():
    # 0 = espatlla, 1 = colze. Màniga del mallot fins a la meitat
    secs = [(0.0, 0.05, 0.05, 0.05, 0.0), (0.15, 0.052, 0.05, 0.048, 0.0), (0.45, 0.047, 0.046, 0.043, 0.0), (0.85, 0.037, 0.036, 0.036, 0.0), (1.0, 0.034, 0.033, 0.033, 0.0)]
    col = lambda t, a: JERSEY if t < 0.5 else BLACK if t < 0.53 else SKIN
    return limb('uarm', secs, col, lambda t, a: 1 if t < 0.5 else 0)

def farm():
    # 0 = colze, 1 = canell (guant a l'últim tros)
    secs = [(0.0, 0.034, 0.034, 0.033, 0.0), (0.15, 0.038, 0.037, 0.036, 0.0), (0.4, 0.037, 0.035, 0.033, 0.0), (0.85, 0.025, 0.024, 0.024, 0.0), (1.0, 0.024, 0.023, 0.025, 0.0)]
    col = lambda t, a: BLACK if t > 0.9 else SKIN
    return limb('farm', secs, col, lambda t, a: 0)

def head():
    """Cap centrat a l'origen, mirant a +X: crani, cara (nas, barbeta), orelles i coll de la samarreta no."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=26, ring_count=16, radius=1)
    ob = bpy.context.active_object; ob.name = 'head'
    for v in ob.data.vertices:
        x, y, z = v.co
        # forma: crani més llarg darrere, cara més estreta, mandíbula
        sx = 0.098 if x < 0 else 0.088
        sy = 0.075 - (0.012 if z < -0.2 else 0) * (1 - x * 0.5)
        sz = 0.105 if z > 0 else 0.1
        p = Vector((x * sx, y * sy, z * sz))
        # barbeta i mandíbula
        if x > 0.3 and z < -0.3: p.x += 0.01 * (x - 0.3) * (-z - 0.3) * 4
        # nas
        dn = math.exp(-((y / 0.18) ** 2) - ((z + 0.1) / 0.22) ** 2) * max(0, x) ** 4
        p.x += 0.022 * dn
        # conques dels ulls
        for ey in (-0.38, 0.38):
            de = math.exp(-(((y - ey) / 0.18) ** 2) - ((z - 0.12) / 0.12) ** 2) * max(0, x) ** 2
            p.x -= 0.008 * de
        v.co = p
    smooth(ob)
    def col(p, n):
        if p.z > 0.02 and p.x < 0.06: return (0.05, 0.035, 0.025)   # cabell (es veu poc sota el casc)
        return SKIN
    paint(ob, col)
    # orelles
    ears = []
    for sd in (1, -1):
        e = prim('uv_sphere', 'ear', loc=(-0.005, sd * 0.074, -0.005), scale=(0.018, 0.008, 0.03), rgb=SKIN, segments=12, ring_count=8)
        ears.append(e)
    return join([ob] + ears, 'head')

def helmet():
    """Casc de carretera amb forats de ventilació (pintats), rivet de color d'equip i corretges. Centrat al cap."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1)
    ob = bpy.context.active_object; ob.name = 'helmet'
    bm = bmesh.new(); bm.from_mesh(ob.data)
    # només la meitat de dalt, allargada enrere i amb punta (cua) aerodinàmica
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.12], context='VERTS')
    for v in bm.verts:
        x, y, z = v.co
        tail = max(0, -x) ** 2 * (1 - z) * 0.28
        v.co = Vector((x * 0.128 - tail * 0.13, y * 0.1, z * 0.098 + 0.004 + (0.012 if x < -0.6 else 0) * (-x - 0.6)))
    bm.to_mesh(ob.data); bm.free()
    sol = ob.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.014; sol.offset = 1
    apply_mods(ob); smooth(ob)
    def col(p, n):
        # ventilació: franges fosques longitudinals a la part de dalt
        ay = abs(p.y)
        if n.z > 0.2 and -0.1 < p.x < 0.085 and p.z > 0.045 and (0.012 < ay < 0.026 or 0.042 < ay < 0.056): return (0.02, 0.02, 0.022)
        if p.z < 0.012 and n.z < 0.2: return (0.05, 0.05, 0.055)       # vora
        return (1, 1, 1)
    paint(ob, col)
    for p in ob.data.polygons:
        c = sum((ob.data.vertices[v].co for v in p.vertices), Vector()) / len(p.vertices)
        p.material_index = 1 if (abs(c.y) > 0.07 and c.z < 0.05 and c.x < 0.06) else 0
    straps = []
    for sd in (1, -1):
        straps.append(tube('strap', [Vector((0.02, sd * 0.098, -0.004)), Vector((0.035, sd * 0.08, -0.09)), Vector((0.06, sd * 0.05, -0.13))], 0.004, 6, BLACK))
        straps.append(tube('strap', [Vector((-0.06, sd * 0.09, -0.004)), Vector((0.035, sd * 0.08, -0.09))], 0.004, 6, BLACK))
    return join([ob] + straps, 'helmet')

def glasses():
    """Ulleres envolvents: lent corbada (material brillant) i patilles."""
    bm = bmesh.new()
    rows = []
    for j in range(5):
        z = -0.018 + 0.036 * j / 4
        row = []
        for i in range(23):
            a = -1.25 + 2.5 * i / 22
            r = 0.094
            row.append(bm.verts.new((r * math.cos(a) * 0.95, r * math.sin(a) * 0.85, z * (1 - 0.25 * abs(a)))))
        rows.append(row)
    for j in range(4):
        for i in range(22):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    lens = new_obj('lens', bm)
    sol = lens.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.003
    apply_mods(lens); smooth(lens); solid(lens, (0.03, 0.04, 0.06), 2)
    arms = [tube('arm', [Vector((0.03, sd * 0.084, 0.012)), Vector((-0.06, sd * 0.08, 0.008))], (0.002, 0.004), 6, BLACK) for sd in (1, -1)]
    return join([lens] + arms, 'glasses')

def shoe():
    """Sabatilla de ciclisme amb cala; llargada al llarg de +X, centrada a l'eix del pedal."""
    secs = []
    bm = bmesh.new(); rings = []
    N = 16
    for i in range(N + 1):
        t = i / N
        x = -0.1 + 0.27 * t
        w = 0.043 * (1 - (abs(t - 0.62) / 0.62) ** 2.5) + 0.012 if t > 0.1 else 0.036 + 0.05 * t
        h_top = 0.075 - 0.045 * max(0, t - 0.35) / 0.65 if t > 0.12 else 0.05 + 0.2 * t
        h_top = max(h_top, 0.025) - (0.012 * (t - 0.9) / 0.1 if t > 0.9 else 0)
        ring = []
        for s in range(16):
            a = 2 * math.pi * s / 16
            c, sn = math.cos(a), math.sin(a)
            z = (sn * 0.5 + 0.5) * h_top - 0.008
            ring.append(bm.verts.new((x, c * w * (0.9 if sn > 0 else 1), z if sn > -0.2 else -0.008)))
        rings.append(ring)
    for i in range(N):
        for s in range(16):
            s1 = (s + 1) % 16
            bm.faces.new((rings[i][s], rings[i][s1], rings[i + 1][s1], rings[i + 1][s]))
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / 16)
        for s in range(16):
            s1 = (s + 1) % 16
            bm.faces.new((c, ring[s1], ring[s]) if rev else (c, ring[s], ring[s1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = new_obj('shoe', bm); smooth(ob)
    paint(ob, lambda p, n: (0.03, 0.03, 0.035) if p.z < 0.0 else (0.75, 0.75, 0.76) if not (0.0 < p.x < 0.06 and n.z > 0.5) else (0.04, 0.04, 0.05))
    dial = prim('cylinder', 'dial', loc=(0.02, 0, 0.066), scale=(0.014, 0.014, 0.006), rgb=BLACK, vertices=14)
    cleat = prim('cube', 'cleat', loc=(0.06, 0, -0.016), scale=(0.035, 0.03, 0.008), rgb=(0.7, 0.2, 0.1))
    return join([ob, dial, cleat], 'shoe')

def glove():
    ob = prim('uv_sphere', 'hand', scale=(0.05, 0.03, 0.04), rgb=BLACK, segments=14, ring_count=8)
    thumb = prim('uv_sphere', 'thumb', loc=(0.02, 0.025, 0.0), scale=(0.025, 0.012, 0.012), rgb=BLACK, segments=10, ring_count=6)
    return join([ob, thumb], 'glove')

def pelvis():
    ob = prim('uv_sphere', 'pelvis', scale=(0.12, 0.135, 0.095), rgb=BLACK, segments=24, ring_count=12)
    # cames del culot: més ample avall, aplanat a la sella
    for v in ob.data.vertices:
        if v.co.z < -0.03: v.co.z = -0.03 - (v.co.z + 0.03) * 0.6
    return ob

PARTS = ['torso', 'thigh', 'calf', 'uarm', 'farm', 'head', 'helmet', 'glasses', 'shoe', 'glove', 'pelvis']

def build(pack):
    print('ciclista')
    for nm in PARTS:
        reset()
        ob = globals()[nm]()
        pack.add('r_' + nm, ob)

def preview_objs():
    out = []
    for i, nm in enumerate(PARTS):
        ob = globals()[nm]()
        ob.location = ((i % 6) * 0.35 - 0.9, 0, 0.6 - (i // 6) * 0.6)
        if nm in ('torso', 'thigh', 'calf', 'uarm', 'farm'):
            ob.scale = (1, 1, {'torso': 0.55, 'thigh': 0.44, 'calf': 0.43, 'uarm': 0.29, 'farm': 0.28}[nm])
        if nm == 'head': ob.scale = (1.6, 1.6, 1.6)
        out.append(ob)
    return out

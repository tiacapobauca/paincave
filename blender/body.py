"""Cos del ciclista d'una sola peça, amb pell («skinning»).

Es modela directament en postura de ciclista (mans a les manetes, bieles horitzontals), que és la postura
de repòs: així les deformacions en pedalar són petites. Les parts (tors, cuixes, cames, braços, coll, mans)
es fonen amb un «remesh» de vòxels, es suavitzen i es redueixen. Cada vèrtex queda lligat als ossos més propers.

Ossos (els mateixos punts que calcula l'app per cinemàtica inversa); eixos de l'app (x endavant, y amunt, z dreta):
  0 tors (maluc → coll) · 1 coll (coll → cap) · 2/3 cuixa E/D · 4/5 cama E/D · 6/7 braç E/D · 8/9 avantbraç E/D
Materials: 0 = color per vèrtex (pell, culot, mitjons, guants) · 1 = mallot (es tenyeix amb el color de l'equip)
"""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector
from common import *

SKIN = (0.48, 0.25, 0.15); BLACK = (0.018, 0.018, 0.02); WHITE = (0.82, 0.82, 0.83); JERSEY = (1, 1, 1); DARK = (0.05, 0.05, 0.055)

def ik2(s, t, a, b, pole):
    """Dos segments de longituds a i b de s a t; retorna l'articulació del mig (colze/genoll) cap a «pole»."""
    s, t, pole = Vector(s), Vector(t), Vector(pole)
    d = t - s; D = d.length or 1e-6; dl = min(a + b - 1e-4, D); d = d / D
    u = pole - d * pole.dot(d); u.normalize()
    ca = max(-1, min(1, (a * a + dl * dl - b * b) / (2 * a * dl))); sa = math.sqrt(1 - ca * ca)
    return s + (d * ca + u * sa) * a

def rest_pose():
    """Articulacions en eixos de l'app (les mateixes fórmules que g3Pose de l'app, amb la biela a 0)."""
    J = {}
    hx, hy = -0.16, 0.95; nx, ny = hx + 0.46, hy + 0.30
    J['hip'] = Vector((hx, hy, 0)); J['neck'] = Vector((nx, ny, 0)); J['head'] = Vector((nx + 0.1, ny + 0.12, 0))
    tx, ty = nx - hx, ny - hy; tl = math.hypot(tx, ty)
    shx, shy = hx + tx * 0.86 - ty / tl * 0.015, hy + ty * 0.86 + tx / tl * 0.015
    for q, sd in ((0, -1), (1, 1)):
        S = 'LR'[q]; ph = 0.0 + (math.pi if q else 0)
        px, py, pz = 0.17 * math.cos(ph), 0.3 + 0.17 * math.sin(ph), sd * 0.112
        fr = 0.18 * math.sin(ph) - 0.06; fc, fs = math.cos(fr), math.sin(fr)
        ox, oy = px - 0.06 * fc - 0.024 * fs, py + 0.012 - 0.06 * fs + 0.024 * fc
        ank = Vector((ox - 0.03 * fc - 0.065 * fs, oy - 0.03 * fs + 0.065 * fc, pz))
        hip = Vector((hx, hy, sd * 0.085))
        J['hip' + S] = hip; J['ank' + S] = ank; J['knee' + S] = ik2(hip, ank, 0.44, 0.43, (1, 0.25, sd * 0.05))
        sh = Vector((shx, shy, sd * 0.175)); hand = Vector((0.57 - 0.02, 0.875, sd * 0.205))
        J['sh' + S] = sh; J['hand' + S] = hand; J['elb' + S] = ik2(sh, hand, 0.29, 0.28, (-0.2, -1, sd * 0.55))
    return J

def bones(J):
    B = [('torso', J['hip'], J['neck'], 0.115), ('neck', J['neck'], J['head'], 0.05)]
    for S in 'LR': B.append(('thigh' + S, J['hip' + S], J['knee' + S], 0.072))
    for S in 'LR': B.append(('calf' + S, J['knee' + S], J['ank' + S], 0.045))
    for S in 'LR': B.append(('uarm' + S, J['sh' + S], J['elb' + S], 0.045))
    for S in 'LR': B.append(('farm' + S, J['elb' + S], J['hand' + S], 0.034))
    return B

def bl(v):  # eixos de l'app → Blender
    return Vector((v[0], -v[2], v[1]))

def loft(bm, A, B, secs, front, seg=20):
    """Tub de A a B (Blender). secs: [(t, r_davant, r_darrere, r_costat, desplaçament cap a davant)]."""
    A, B = Vector(A), Vector(B); ax = (B - A).normalized()
    f = (Vector(front) - ax * Vector(front).dot(ax)).normalized(); sdv = ax.cross(f).normalized()
    def at(t):
        i = 0
        while i < len(secs) - 2 and secs[i + 1][0] < t: i += 1
        a, b = secs[i], secs[i + 1]; k = (t - a[0]) / max(1e-6, b[0] - a[0]); k = k * k * (3 - 2 * k)
        return [a[j] + (b[j] - a[j]) * k for j in range(1, 5)]
    rings = []
    N = 22
    for r in range(N + 1):
        t = secs[0][0] + (secs[-1][0] - secs[0][0]) * r / N
        rf, rb, rs, off = at(t); c0 = A + (B - A) * t + f * off
        rings.append([bm.verts.new(c0 + f * (math.cos(a) * (rf if math.cos(a) > 0 else rb)) + sdv * (math.sin(a) * rs)) for a in (2 * math.pi * s / seg for s in range(seg))])
    for r in range(N):
        for s in range(seg):
            s1 = (s + 1) % seg; bm.faces.new((rings[r][s], rings[r][s1], rings[r + 1][s1], rings[r + 1][s]))
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / seg)
        for s in range(seg):
            s1 = (s + 1) % seg; bm.faces.new((c, ring[s1], ring[s]) if rev else (c, ring[s], ring[s1]))

def blob(bm, c, r, rot=None):
    m = Matrix.Translation(Vector(c)) @ (rot or Matrix.Identity(4)) @ Matrix.Diagonal((r[0], r[1], r[2], 1))
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1, matrix=m)

def build_mesh(voxel=0.007, target=4200):
    J = rest_pose(); bm = bmesh.new()
    hip, neck = bl(J['hip']), bl(J['neck']); ax = (neck - hip).normalized()
    chest = Vector((ax.z, 0, -ax.x))                      # cap endavant i avall (pit i panxa)
    # tors: maluc ample, cintura, pit, espatlles
    loft(bm, hip - ax * 0.07, neck + ax * 0.0, [(0.0, 0.07, 0.09, 0.13, 0.0), (0.12, 0.09, 0.1, 0.15, 0.0), (0.3, 0.095, 0.1, 0.14, -0.005), (0.48, 0.095, 0.097, 0.135, -0.008),
        (0.7, 0.105, 0.1, 0.158, -0.004), (0.85, 0.1, 0.098, 0.178, 0.0), (0.94, 0.078, 0.088, 0.16, 0.0), (1.0, 0.05, 0.06, 0.075, 0.004)], chest, 28)
    # coll (el cap és una peça rígida a part)
    hd = bl(J['head']); nk = (hd - neck).normalized()
    loft(bm, neck - nk * 0.05, hd - nk * 0.02, [(0, 0.052, 0.058, 0.06, 0), (0.5, 0.047, 0.05, 0.05, 0), (1, 0.046, 0.048, 0.048, 0)], chest, 16)
    for S, sd in (('L', 1), ('R', -1)):                   # a Blender l'esquerra és +Y
        h, k, a = bl(J['hip' + S]), bl(J['knee' + S]), bl(J['ank' + S])
        sh, e, hand = bl(J['sh' + S]), bl(J['elb' + S]), bl(J['hand' + S])
        up = Vector((0, 0, 1)); fwd = Vector((1, 0, 0))
        # cuixa: quàdriceps a dalt-davant, isquiotibials a sota
        loft(bm, h, k, [(-0.04, 0.078, 0.08, 0.078, 0), (0.12, 0.088, 0.082, 0.082, 0.004), (0.45, 0.078, 0.066, 0.07, 0.006), (0.8, 0.058, 0.05, 0.054, 0.002), (0.95, 0.05, 0.046, 0.05, 0), (1.03, 0.048, 0.046, 0.048, 0)], up, 20)
        blob(bm, h + Vector((-0.03, sd * 0.01, 0.004)), (0.085, 0.074, 0.08))                         # gluti
        blob(bm, k + Vector((0.006, 0, 0.004)), (0.05, 0.047, 0.05))                               # genoll
        # cama: bessó al darrere
        loft(bm, k, a, [(-0.03, 0.045, 0.046, 0.047, 0), (0.15, 0.043, 0.057, 0.05, 0), (0.33, 0.04, 0.066, 0.052, -0.004), (0.6, 0.035, 0.047, 0.04, -0.002), (0.85, 0.029, 0.033, 0.031, 0), (1.06, 0.029, 0.031, 0.03, 0)], fwd, 18)
        # braç i avantbraç
        blob(bm, sh + Vector((0.0, sd * 0.004, 0.006)), (0.062, 0.058, 0.06))                         # deltoide
        loft(bm, sh, e, [(-0.05, 0.05, 0.05, 0.05, 0), (0.2, 0.05, 0.05, 0.047, 0), (0.55, 0.044, 0.046, 0.042, 0), (0.9, 0.037, 0.038, 0.037, 0), (1.03, 0.036, 0.036, 0.036, 0)], fwd, 16)
        loft(bm, e, hand, [(-0.04, 0.036, 0.036, 0.036, 0), (0.15, 0.04, 0.04, 0.038, 0), (0.45, 0.037, 0.038, 0.034, 0), (0.85, 0.027, 0.028, 0.03, 0), (1.0, 0.027, 0.028, 0.031, 0)], up, 16)
        # mà agafada a la maneta: palmell, dits al voltant i polze per dins
        fa = (hand - e).normalized()
        blob(bm, hand + fa * 0.035 + Vector((0, 0, 0.004)), (0.05, 0.03, 0.034))
        blob(bm, hand + fa * 0.07 + Vector((0.008, 0, -0.018)), (0.03, 0.036, 0.03))
        blob(bm, hand + fa * 0.045 + Vector((0, -sd * 0.03, -0.004)), (0.03, 0.013, 0.015))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = new_obj('body', bm)
    ob.data.remesh_voxel_size = voxel
    select_only(ob); bpy.ops.object.voxel_remesh()
    sm = ob.modifiers.new('sm', 'SMOOTH'); sm.factor = 0.8; sm.iterations = 6; apply_mods(ob)
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    decimate(ob, min(1.0, target / tris))
    smooth(ob)
    return ob, J

def nearest(B, side, p):
    ds = []
    for i, (nm, a, b, r) in enumerate(B):
        ab = b - a; t = (p - a).dot(ab) / ab.length_squared; tc = max(0.0, min(1.0, t))
        d = max(0.0, (p - (a + ab * tc)).length - r)
        if side[i] and p.z * side[i] < -0.004: d += 1.0      # un punt d'un costat no pot seguir una extremitat de l'altre
        ds.append((d, i, t))
    ds.sort(); return ds

# vores de la roba: (os, posició al llarg de l'os). La malla es talla per aquests plans perquè les vores quedin netes.
CUTS = [(0, 0.1), (0, 0.125), (1, 0.12), (2, 0.74), (2, 0.78), (3, 0.74), (3, 0.78), (4, 0.76), (5, 0.76),
        (6, 0.52), (6, 0.57), (7, 0.52), (7, 0.57), (8, 0.93), (9, 0.93)]

def classify(ob, J):
    """Talla la malla per les vores de la roba; color per cara; pesos dels ossos per vèrtex."""
    B = bones(J)
    side = [0, 0, -1, 1, -1, 1, -1, 1, -1, 1]             # costat de cada os a l'app (z): −1 esquerra, +1 dreta
    me = ob.data
    app = lambda co: Vector((co.x, co.z, -co.y))
    bm = bmesh.new(); bm.from_mesh(me)
    for bi, t in CUTS:
        nm, a, b, r = B[bi]; c = a + (b - a) * t; n = (b - a).normalized()
        rad = 0.26 if bi == 0 else 0.11
        fs = [f for f in bm.faces if (app(f.calc_center_median()) - c).length < rad and nearest(B, side, app(f.calc_center_median()))[0][1] in ((0, 2, 3) if bi == 0 else (0, 1) if bi == 1 else (bi,))]
        geom = list({v for f in fs for v in f.verts}) + list({e for f in fs for e in f.edges}) + fs
        bmesh.ops.bisect_plane(bm, geom=geom, dist=0.0015, plane_co=bl(c), plane_no=bl(n))
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free(); me.update()
    hipA, neckA = J['hip'], J['neck']
    def torso(p):
        tt = (p - hipA).dot(neckA - hipA) / (neckA - hipA).length_squared
        return (BLACK, False) if tt < 0.1 else (DARK, False) if tt < 0.125 else (JERSEY, True)
    def colour(p):
        ds = nearest(B, side, p); d0, i0, t0 = ds[0]; nm = B[i0][0]
        tn = (p - neckA).dot(J['head'] - neckA) / (J['head'] - neckA).length_squared
        if i0 < 2: return (SKIN, False) if tn > 0.12 else (JERSEY, True) if i0 == 1 else torso(p)
        dt = [d for d, i, t in ds if i == 0][0]
        if nm.startswith('thigh') and dt < d0 + 0.03 and torso(p)[1]: return (JERSEY, True)
        if nm == 'torso':
            tt = (p - hipA).dot(neckA - hipA) / (neckA - hipA).length_squared
            return (BLACK, False) if tt < 0.1 else (DARK, False) if tt < 0.125 else (JERSEY, True)
        if nm == 'neck': return (JERSEY, True) if t0 < 0.12 else (SKIN, False)
        if nm.startswith('thigh'): return (BLACK, False) if t0 < 0.74 else (DARK, False) if t0 < 0.78 else (SKIN, False)
        if nm.startswith('calf'): return (WHITE, False) if t0 > 0.76 else (SKIN, False)
        if nm.startswith('uarm'): return (JERSEY, True) if t0 < 0.52 else (DARK, False) if t0 < 0.57 else (SKIN, False)
        return (BLACK, False) if t0 > 0.93 else (SKIN, False)
    skin = []
    for v in me.vertices:
        ds = nearest(B, side, app(v.co))
        # pesos: inversament proporcionals a la distància a la superfície de cada os
        w = [(1.0 / (d + 0.012) ** 4, i) for d, i, t in ds[:3]]
        tot = sum(x for x, i in w); w = [(x / tot, i) for x, i in w if x / tot > 0.04]
        tot = sum(x for x, i in w); q = [int(round(x / tot * 255)) for x, i in w]; q[0] += 255 - sum(q)
        idx = [i for x, i in w] + [0] * (4 - len(w)); q = q + [0] * (4 - len(q))
        skin.append((tuple(idx), tuple(q)))
    col = ensure_col(ob)
    for p in me.polygons:
        c, jr = colour(app(p.center))
        p.material_index = 1 if jr else 0
        for li in p.loop_indices: col.data[li].color = (c[0], c[1], c[2], 1)
    smooth(ob)
    extra = dict(bones=[[round(x, 4) for x in a] + [round(x, 4) for x in b] for nm, a, b, r in B])
    return skin, extra

def build(pack):
    print('cos del ciclista')
    for name, target in (('r_body', 4200), ('r_body1', 1300)):
        reset()
        ob, J = build_mesh(target=target)
        skin, extra = classify(ob, J)
        pack.add(name, ob, skin=skin, extra=extra)

def preview_objs():
    ob, J = build_mesh()
    classify(ob, J)
    return [ob]

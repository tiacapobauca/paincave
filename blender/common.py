"""Utilitats compartides per generar els models 3D de PainCave amb Blender (bpy).

Convencions:
- Es modela amb els eixos de Blender (X endavant, Y esquerra, Z amunt).
- En exportar es passa als eixos de l'app (three.js): x = X, y = Z, z = -Y.
- Cada malla s'exporta triangulada, amb normals, color per vèrtex (atribut "Col")
  i UV (si en té), i amb grups de triangles per material (índex de material de Blender).
"""
import bpy, bmesh, math, json, struct, gzip, base64, random
from mathutils import Vector, Matrix, noise

# ---------------------------------------------------------------- escena
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob

def new_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    return link(bpy.data.objects.new(name, me))

def select_only(ob):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob

def apply_mods(ob):
    select_only(ob)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)

def join(obs, name=None):
    obs = [o for o in obs if o]
    select_only(obs[0])
    for o in obs[1:]:
        o.select_set(True)
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    if name: ob.name = name; ob.data.name = name
    return ob

def set_mat(ob, idx):
    for p in ob.data.polygons:
        p.material_index = idx

def smooth(ob, angle=None):
    for p in ob.data.polygons:
        p.use_smooth = True
    if angle is not None:
        select_only(ob)
        try:
            bpy.ops.object.shade_auto_smooth(angle=angle)
            apply_mods(ob)
        except Exception:
            pass

def subsurf(ob, levels=1, apply=True):
    m = ob.modifiers.new('ss', 'SUBSURF'); m.levels = levels; m.render_levels = levels
    if apply: apply_mods(ob)

def decimate(ob, ratio):
    m = ob.modifiers.new('dec', 'DECIMATE'); m.ratio = ratio
    apply_mods(ob)

def ensure_col(ob, rgb=(1, 1, 1)):
    me = ob.data
    if 'Col' not in me.color_attributes:
        me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    a = me.color_attributes['Col']
    if a.domain != 'CORNER' or a.data_type != 'FLOAT_COLOR':
        raise RuntimeError('Col ha de ser FLOAT_COLOR / CORNER')
    for d in a.data:
        d.color = (rgb[0], rgb[1], rgb[2], 1)
    return a

def paint(ob, fn):
    """fn(world_pos, normal) -> (r,g,b): color per vèrtex (per cantonada)."""
    me = ob.data
    a = ensure_col(ob)
    mw = ob.matrix_world
    for p in me.polygons:
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index]
            c = fn(mw @ v.co, (mw.to_3x3() @ v.normal).normalized())
            a.data[li].color = (c[0], c[1], c[2], 1)

def solid(ob, rgb, mat=None):
    ensure_col(ob, rgb)
    if mat is not None: set_mat(ob, mat)
    return ob

# ------------------------------------------------- oclusió ambiental al color
def bake_ao(obs, strength=0.85, samples=24, dist=0.6, floor=False):
    """Calcula l'oclusió ambiental (Cycles) i la multiplica pel color per vèrtex de cada objecte."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples
    sc.world = sc.world or bpy.data.worlds.new('w')
    sc.world.light_settings.distance = dist
    ground = None
    if floor:
        bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.001)); ground = bpy.context.active_object
    for ob in obs:
        me = ob.data
        base = [tuple(d.color) for d in me.color_attributes['Col'].data]
        tmp = me.color_attributes.new('AOtmp', 'FLOAT_COLOR', 'CORNER')
        me.color_attributes.active_color = tmp
        if not me.materials:
            me.materials.append(bpy.data.materials.new('tmp'))
        select_only(ob)
        sc.render.bake.target = 'VERTEX_COLORS'
        sc.cycles.bake_type = 'AO'
        bpy.ops.object.bake(type='AO', target='VERTEX_COLORS')
        col = me.color_attributes['Col']
        for i, d in enumerate(me.color_attributes['AOtmp'].data):
            ao = d.color[0]
            k = 1 - strength + strength * ao
            b = base[i]
            col.data[i].color = (b[0] * k, b[1] * k, b[2] * k, 1)
        me.color_attributes.remove(me.color_attributes['AOtmp'])
        me.color_attributes.active_color = me.color_attributes['Col']
    if ground:
        bpy.data.objects.remove(ground)

# ------------------------------------------------------------- geometria
def tube_bm(bm, pts, radii, seg=8, prof=None, cap=True, twist_up=Vector((0, 0, 1))):
    """Tub al llarg d'una polilínia. radii: radi (o (rx, ry)) per punt. prof(a) -> (cx, cy) per perfils no circulars."""
    rings = []
    n = len(pts)
    prev_side = None
    for i, p in enumerate(pts):
        p = Vector(p)
        t = (Vector(pts[min(i + 1, n - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        up = twist_up if abs(t.dot(twist_up)) < 0.95 else Vector((1, 0, 0))
        side = t.cross(up).normalized()
        if prev_side is not None and side.dot(prev_side) < 0: side = -side
        prev_side = side
        nrm = side.cross(t).normalized()
        r = radii[i] if isinstance(radii, list) else radii
        rx, ry = (r, r) if not isinstance(r, (list, tuple)) else r
        ring = []
        for s in range(seg):
            a = 2 * math.pi * s / seg
            cx, cy = (math.cos(a), math.sin(a)) if prof is None else prof(a)
            ring.append(bm.verts.new(p + side * (cx * rx) + nrm * (cy * ry)))
        rings.append(ring)
    for i in range(n - 1):
        A, B = rings[i], rings[i + 1]
        for s in range(seg):
            s1 = (s + 1) % seg
            bm.faces.new((A[s], A[s1], B[s1], B[s]))
    if cap:
        for ring, rev in ((rings[0], True), (rings[-1], False)):
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / seg)
            for s in range(seg):
                s1 = (s + 1) % seg
                f = (c, ring[s1], ring[s]) if rev else (c, ring[s], ring[s1])
                bm.faces.new(f)
    return rings

def bezier(p0, p1, p2, p3, n):
    out = []
    for i in range(n + 1):
        t = i / n; u = 1 - t
        out.append(tuple(u * u * u * Vector(p0) + 3 * u * u * t * Vector(p1) + 3 * u * t * t * Vector(p2) + t * t * t * Vector(p3)))
    return out

def tube(name, pts, r, seg=8, rgb=(0.1, 0.1, 0.1), mat=0, **kw):
    bm = bmesh.new(); tube_bm(bm, pts, r, seg, **kw)
    ob = new_obj(name, bm)
    bmesh.ops.recalc_face_normals  # (les cares ja van cap enfora)
    smooth(ob); solid(ob, rgb, mat)
    return ob

def prim(kind, name, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), rgb=(0.5, 0.5, 0.5), mat=0, **kw):
    getattr(bpy.ops.mesh, 'primitive_' + kind + '_add')(location=loc, rotation=rot, **kw)
    ob = bpy.context.active_object; ob.name = name
    ob.scale = scale
    select_only(ob); bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    solid(ob, rgb, mat)
    return ob

def displace_noise(ob, amp, freq, seed=0, octaves=3, axis_scale=(1, 1, 1)):
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    for v in ob.data.vertices:
        p = v.co
        q = Vector((p.x * axis_scale[0], p.y * axis_scale[1], p.z * axis_scale[2])) * freq + off
        d = noise.fractal(q, 0.5, 2.0, octaves, noise_basis='PERLIN_ORIGINAL')
        v.co = p + v.normal * d * amp

# ---------------------------------------------------------------- export
def mesh_data(ob):
    """Dades d'una malla en eixos de l'app: llistes de vèrtexs desdoblats per cantonada (amb dedup)."""
    dg = bpy.context.evaluated_depsgraph_get()
    oe = ob.evaluated_get(dg)
    me = oe.to_mesh()
    me.calc_loop_triangles()
    mw = ob.matrix_world; nm = mw.to_3x3().inverted().transposed()
    col = me.color_attributes.get('Col')
    uvl = me.uv_layers.active
    cn = me.corner_normals
    key2i, P, N, C, U = {}, [], [], [], []
    groups = {}
    for tri in me.loop_triangles:
        mi = tri.material_index
        idx = []
        for li in tri.loops:
            v = me.vertices[me.loops[li].vertex_index]
            p = mw @ v.co
            n = (nm @ Vector(cn[li].vector)).normalized()
            c = tuple(col.data[li].color[:3]) if col else (1, 1, 1)
            u = tuple(uvl.data[li].uv) if uvl else (0, 0)
            # eixos de l'app: (X, Z, -Y)
            pa = (round(p.x, 5), round(p.z, 5), round(-p.y, 5))
            na = (round(n.x, 2), round(n.z, 2), round(-n.y, 2))
            ca = tuple(round(x, 3) for x in c)
            ua = (round(u[0], 4), round(u[1], 4))
            k = (pa, na, ca, ua)
            i = key2i.get(k)
            if i is None:
                i = len(P); key2i[k] = i
                P.append(pa); N.append(na); C.append(ca); U.append(ua)
            idx.append(i)
        groups.setdefault(mi, []).extend(idx)
    oe.to_mesh_clear()
    return dict(P=P, N=N, C=C, U=U, groups=groups, has_uv=bool(uvl), has_col=bool(col))

class Pack:
    """Paquet binari de malles: capçalera JSON + blocs (posicions int16, normals int8, colors uint8, uv uint16, índexs)."""
    def __init__(self):
        self.meshes = []; self.buf = bytearray()

    def _put(self, b):
        while len(self.buf) % 4: self.buf.append(0)
        off = len(self.buf); self.buf += b
        return off

    def add(self, name, ob):
        obs = ob if isinstance(ob, (list, tuple)) else [ob]
        d = None
        for o in obs:   # diverses malles en una (p. ex. tronc + fulles amb normals pròpies)
            e = mesh_data(o)
            if d is None: d = e; continue
            off = len(d['P'])
            for k in 'PNCU': d[k] += e[k]
            for mi, g in e['groups'].items(): d['groups'].setdefault(mi, []).extend(i + off for i in g)
            d['has_uv'] |= e['has_uv']; d['has_col'] |= e['has_col']
        P, N, C, U = d['P'], d['N'], d['C'], d['U']
        nv = len(P)
        mn = [min(p[k] for p in P) for k in range(3)]; mx = [max(p[k] for p in P) for k in range(3)]
        q = lambda v, a, b: int(round((v - a) / ((b - a) or 1) * 65535)) - 32768
        pos = struct.pack('<%dh' % (nv * 3), *[q(p[k], mn[k], mx[k]) for p in P for k in range(3)])
        nor = struct.pack('<%db' % (nv * 3), *[max(-127, min(127, int(round(n[k] * 127)))) for n in N for k in range(3)])
        m = dict(n=name, v=nv, b=mn + mx, a={})
        m['a']['p'] = self._put(pos); m['a']['n'] = self._put(nor)
        if d['has_col']:
            m['a']['c'] = self._put(bytes(max(0, min(255, int(round(c[k] ** (1 / 2.2) * 255)))) for c in C for k in range(3)))
        if d['has_uv']:
            u0 = [min(u[k] for u in U) for k in range(2)]; u1 = [max(u[k] for u in U) for k in range(2)]
            m['ub'] = u0 + u1
            m['a']['u'] = self._put(struct.pack('<%dH' % (nv * 2), *[int(round((u[k] - u0[k]) / ((u1[k] - u0[k]) or 1) * 65535)) for u in U for k in range(2)]))
        idx, groups = [], []
        for mi in sorted(d['groups']):
            g = d['groups'][mi]; groups.append([len(idx), len(g), mi]); idx += g
        fmt = 'H' if nv < 65536 else 'I'
        m['i'] = len(idx); m['it'] = 2 if fmt == 'H' else 4; m['g'] = groups
        m['a']['i'] = self._put(struct.pack('<%d%s' % (len(idx), fmt), *idx))
        self.meshes.append(m)
        print('  %-14s %6d vèrtexs %6d triangles' % (name, nv, len(idx) // 3))
        return m

    def blob(self):
        head = json.dumps(dict(m=self.meshes), separators=(',', ':')).encode()
        raw = struct.pack('<I', len(head)) + head
        while len(raw) % 4: raw += b' '
        # els desplaçaments del cos es compten des del final de la capçalera
        return gzip.compress(raw + bytes(self.buf), 9)

def b64(data):
    return base64.b64encode(data).decode()

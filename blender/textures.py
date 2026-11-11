"""Textures de materials fetes amb nodes procedurals de Blender i «bake» de Cycles.

Perquè les textures es repeteixin sense costures, les coordenades UV es converteixen en un tor 4D
(cos u, sin u, cos v, sin v) i s'usen sorolls i Voronoi de 4 dimensions.
Cada textura dona un color i una alçada; el mapa de normals es calcula de l'alçada (numpy).
"""
import bpy, math, os
import numpy as np
from common import *

OUT = os.path.join(os.path.dirname(__file__), 'out')

class Nodes:
    def __init__(self, mat, W, H, tile_v=True):
        self.nt = mat.node_tree; self.nt.nodes.clear()
        n = self.new
        tc = n('ShaderNodeTexCoord'); sep = n('ShaderNodeSeparateXYZ'); self.link(tc.outputs['UV'], sep.inputs[0])
        self.u, self.v = sep.outputs[0], sep.outputs[1]
        Rx, Ry = W / (2 * math.pi), H / (2 * math.pi)
        def trig(src, f, R):
            a = self.math('MULTIPLY', src, 2 * math.pi)
            return self.math('MULTIPLY', self.math(f, a), R)
        comb = n('ShaderNodeCombineXYZ')
        self.link(trig(self.u, 'COSINE', Rx), comb.inputs[0]); self.link(trig(self.u, 'SINE', Rx), comb.inputs[1])
        if tile_v:
            self.link(trig(self.v, 'COSINE', Ry), comb.inputs[2]); self.w = trig(self.v, 'SINE', Ry)
        else:   # només es repeteix en horitzontal (p. ex. un mur): v lineal
            self.link(self.math('MULTIPLY', self.v, H), comb.inputs[2]); self.w = self.math('MULTIPLY', self.v, 0.0)
        self.vec = comb.outputs[0]

    def new(self, t): return self.nt.nodes.new(t)
    def link(self, a, b): self.nt.links.new(a, b)
    def _in(self, node, i, v):
        if isinstance(v, (int, float)): node.inputs[i].default_value = v
        else: self.link(v, node.inputs[i])
    def math(self, op, a, b=None):
        m = self.new('ShaderNodeMath'); m.operation = op
        self._in(m, 0, a)
        if b is not None: self._in(m, 1, b)
        return m.outputs[0]
    def noise(self, scale, detail=4, rough=0.5, offset=0.0, dist=0.0):
        t = self.new('ShaderNodeTexNoise'); t.noise_dimensions = '4D'
        self.link(self.vec, t.inputs['Vector']); self.link(self.math('ADD', self.w, offset), t.inputs['W'])
        t.inputs['Scale'].default_value = scale; t.inputs['Detail'].default_value = detail; t.inputs['Roughness'].default_value = rough
        t.inputs['Distortion'].default_value = dist
        return t.outputs['Fac']
    def voronoi(self, scale, feature='F1', out='Distance', rand=1.0, offset=0.0):
        t = self.new('ShaderNodeTexVoronoi'); t.voronoi_dimensions = '4D'; t.feature = feature
        self.link(self.vec, t.inputs['Vector']); self.link(self.math('ADD', self.w, offset), t.inputs['W'])
        t.inputs['Scale'].default_value = scale; t.inputs['Randomness'].default_value = rand
        return t.outputs[out]
    def ramp(self, fac, stops):
        r = self.new('ShaderNodeValToRGB'); self.link(fac, r.inputs[0])
        el = r.color_ramp.elements
        while len(el) > 2: el.remove(el[-1])
        for i, (p, c) in enumerate(stops):
            e = el[i] if i < 2 else el.new(p)
            e.position = p; e.color = (*c, 1) if len(c) == 3 else c
        return r.outputs[0]
    def mix(self, fac, a, b, mode='MIX'):
        m = self.new('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = mode
        self._in(m, 0, fac)
        self.link(a, m.inputs[6]) if not isinstance(a, tuple) else setattr(m.inputs[6], 'default_value', (*a, 1))
        self.link(b, m.inputs[7]) if not isinstance(b, tuple) else setattr(m.inputs[7], 'default_value', (*b, 1))
        return m.outputs[2]
    def emit(self, col):
        e = self.new('ShaderNodeEmission'); o = self.new('ShaderNodeOutputMaterial')
        self.link(col, e.inputs[0]); self.link(e.outputs[0], o.inputs[0])

def bake(name, w, h, W, H, graph, tile_v=True):
    """graph(N) -> (color, height). Retorna arrays float (h, w, 3) i (h, w)."""
    reset()
    bpy.ops.mesh.primitive_plane_add(size=2)
    ob = bpy.context.active_object
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 1
    mat = bpy.data.materials.new(name); mat.use_nodes = True; ob.data.materials.append(mat)
    out = []
    for k in range(2):
        N = Nodes(mat, W, H, tile_v)
        col, hgt = graph(N)
        N.emit(col if k == 0 else hgt)
        img = bpy.data.images.new('%s_%d' % (name, k), w, h, float_buffer=True)
        tn = mat.node_tree.nodes.new('ShaderNodeTexImage'); tn.image = img
        mat.node_tree.nodes.active = tn
        select_only(ob)
        bpy.ops.object.bake(type='EMIT')
        a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
        out.append(a[..., :3] if k == 0 else a[..., 0])
    return out

def normal_map(H, strength):
    hl, hr = np.roll(H, 1, 1), np.roll(H, -1, 1); hu, hd = np.roll(H, 1, 0), np.roll(H, -1, 0)
    nx = (hl - hr) * strength; ny = (hu - hd) * strength; nz = np.ones_like(H)
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / L * 0.5 + 0.5, ny / L * 0.5 + 0.5, nz / L * 0.5 + 0.5], -1)

def save(arr, path, srgb=True):
    from PIL import Image
    a = np.clip(arr, 0, 1)
    if srgb: a = np.where(a <= 0.0031308, a * 12.92, 1.055 * np.power(a, 1 / 2.4) - 0.055)
    Image.fromarray((a * 255 + 0.5).astype(np.uint8)).save(path)
    return path

# ------------------------------------------------------------------ asfalt
def road_graph(N):
    chipd = N.voronoi(90)                                       # granulat (~1 cm)
    chip_g = N.ramp(N.math('MULTIPLY', N.noise(140, 2), 1.0), [(0.35, (0.03, 0.03, 0.032)), (0.75, (0.11, 0.105, 0.1))])
    grain = N.mix(N.math('GREATER_THAN', N.noise(60, 1, offset=7), 0.66), chip_g, (0.2, 0.19, 0.17))
    blot = N.ramp(N.noise(0.45, 3, 0.6, offset=2), [(0.35, (0.75, 0.75, 0.75)), (0.65, (1.12, 1.1, 1.08))])
    col = N.mix(1.0, grain, blot, 'MULTIPLY')
    # esquerdes fines (vores de Voronoi) i pegats més foscos
    crack = N.math('LESS_THAN', N.voronoi(0.35, 'DISTANCE_TO_EDGE', offset=5), 0.005)
    crack = N.math('MULTIPLY', crack, N.math('GREATER_THAN', N.noise(0.8, 2, offset=9), 0.6))
    col = N.mix(N.math('MULTIPLY', crack, 0.6), col, (0.015, 0.015, 0.016))
    patch = N.math('GREATER_THAN', N.noise(0.25, 2, offset=11), 0.68)
    col = N.mix(N.math('MULTIPLY', patch, 0.6), col, (0.025, 0.025, 0.027))
    hgt = N.math('SUBTRACT', N.math('MULTIPLY', N.math('SUBTRACT', 1.0, N.math('MINIMUM', N.math('MULTIPLY', chipd, 2.2), 1.0)), 0.6), N.math('MULTIPLY', crack, 0.8))
    hgt = N.math('ADD', hgt, N.math('MULTIPLY', N.noise(20, 3), 0.3))
    return col, hgt

def road():
    w, h = 512, 1024
    col, hgt = bake('road', w, h, 6.0, 12.0, road_graph)
    u = (np.arange(w) + 0.5) / w; v = (np.arange(h) + 0.5) / h
    U, V = np.meshgrid(u, v)
    # rodades: l'asfalt polit és una mica més fosc i llis
    wear = np.exp(-((U - 0.3) / 0.07) ** 2) + np.exp(-((U - 0.7) / 0.07) ** 2)
    col *= (1 - 0.18 * wear)[..., None]
    hgt *= (1 - 0.5 * wear)
    # línies: vorals contínues i central discontínua (pintura gastada, amb gruix)
    rng = np.random.default_rng(3)
    lines = ((U > 0.022) & (U < 0.047)) | ((U > 0.953) & (U < 0.978)) | ((U > 0.49) & (U < 0.51) & (V < 1 / 3))
    wearp = np.clip(np.array(hgt) * 0.8 + rng.random(hgt.shape) * 0.5, 0, 1)
    paint = lines & (wearp > 0.18)
    col[paint] = np.array([0.72, 0.71, 0.66]) * (0.8 + 0.2 * wearp[paint])[:, None]
    hgt = hgt + paint * 0.5
    a = save(col, os.path.join(OUT, 'road.png'))
    b = save(normal_map(hgt, 3.0), os.path.join(OUT, 'roadN.png'), False)
    return a, b

# ------------------------------------------------- terreny (detall en gris)
def ground_graph(N):
    clod = N.ramp(N.noise(1.6, 5, 0.6), [(0.3, (0.6, 0.6, 0.6)), (0.7, (1.0, 1.0, 1.0))])
    peb = N.math('LESS_THAN', N.voronoi(9), 0.18)
    peb = N.math('MULTIPLY', peb, N.math('GREATER_THAN', N.noise(3, 2, offset=4), 0.5))
    col = N.mix(N.math('MULTIPLY', peb, 0.8), clod, (1.15, 1.15, 1.15))
    tuft = N.math('GREATER_THAN', N.noise(14, 3, 0.7, offset=8), 0.62)
    col = N.mix(N.math('MULTIPLY', tuft, 0.5), col, (0.55, 0.55, 0.55))
    hgt = N.math('ADD', N.math('MULTIPLY', N.noise(1.6, 5, 0.6), 0.8), N.math('MULTIPLY', peb, 0.6))
    hgt = N.math('ADD', hgt, N.math('MULTIPLY', tuft, 0.35))
    return col, hgt

def ground():
    col, hgt = bake('ground', 512, 512, 14.0, 14.0, ground_graph)
    g = col.mean(-1, keepdims=True); g = g / g.mean() * 0.62
    return save(np.repeat(g, 3, -1), os.path.join(OUT, 'ground.png')), save(normal_map(hgt, 4.0), os.path.join(OUT, 'groundN.png'), False)

# ---------------------------------------------------------- voral de grava
def dirt_graph(N):
    stone = N.voronoi(40, out='Color')
    d = N.voronoi(40)
    base = N.ramp(N.noise(3, 4), [(0.3, (0.32, 0.25, 0.17)), (0.7, (0.45, 0.37, 0.26))])
    pebc = N.mix(0.5, stone, (0.5, 0.46, 0.4))
    col = N.mix(N.math('LESS_THAN', d, 0.35), base, pebc)
    hgt = N.math('SUBTRACT', 1.0, N.math('MINIMUM', N.math('MULTIPLY', d, 2.0), 1.0))
    return col, hgt

def dirt():
    col, hgt = bake('dirt', 256, 256, 4.0, 4.0, dirt_graph)
    return save(col, os.path.join(OUT, 'dirt.png')), save(normal_map(hgt, 3.0), os.path.join(OUT, 'dirtN.png'), False)

# ------------------------------------------------- marge de pedra en sec
def stone_graph(N):
    cells = N.voronoi(3.2, 'F1', 'Color', rand=0.85)
    edge = N.voronoi(3.2, 'DISTANCE_TO_EDGE', rand=0.85)
    rock = N.ramp(N.noise(6, 4, 0.6), [(0.3, (0.38, 0.33, 0.26)), (0.7, (0.6, 0.55, 0.45))])
    tint = N.mix(0.25, rock, cells, 'MULTIPLY')
    tint = N.mix(0.75, tint, rock)
    gap = N.math('LESS_THAN', edge, 0.035)
    col = N.mix(gap, tint, (0.05, 0.045, 0.04))
    lichen = N.math('GREATER_THAN', N.noise(8, 3, offset=3), 0.63)
    col = N.mix(N.math('MULTIPLY', lichen, 0.5), col, (0.55, 0.55, 0.42))
    hgt = N.math('ADD', N.math('MINIMUM', N.math('MULTIPLY', edge, 9), 1.0), N.math('MULTIPLY', N.noise(6, 4), 0.25))
    return col, hgt

def stone():
    col, hgt = bake('stone', 512, 128, 4.0, 1.0, stone_graph, tile_v=False)
    return save(col, os.path.join(OUT, 'stone.png')), save(normal_map(hgt, 4.0), os.path.join(OUT, 'stoneN.png'), False)

# ------------------------------------------------ terreny: herba seca, terra i roca (color, mosaic de 6 m)
def ridge(N, scale, width, detail=3, offset=0.0, dist=0.0):
    """Línies fines i orgàniques (esquerdes): on el soroll passa per 0,5."""
    return N.math('LESS_THAN', N.math('ABSOLUTE', N.math('SUBTRACT', N.noise(scale, detail, 0.5, offset=offset, dist=dist), 0.5)), width)

def tgrass_graph(N):
    base = N.ramp(N.noise(0.45, 4, 0.6), [(0.3, (0.12, 0.17, 0.055)), (0.5, (0.27, 0.27, 0.11)), (0.7, (0.5, 0.42, 0.2))])
    tuft = N.noise(9, 3, 0.75, offset=3)                              # mates d'herba: taques fosques i clares
    col = N.mix(1.0, base, N.ramp(tuft, [(0.3, (0.45, 0.5, 0.4)), (0.5, (0.95, 0.95, 0.9)), (0.72, (1.5, 1.42, 1.2))]), 'MULTIPLY')
    blade = N.ramp(N.noise(45, 2, 0.8, offset=5), [(0.3, (0.5, 0.5, 0.5)), (0.72, (1.4, 1.4, 1.3))])
    col = N.mix(1.0, col, blade, 'MULTIPLY')
    bare = N.math('GREATER_THAN', N.noise(1.3, 4, 0.7, offset=9), 0.63)
    col = N.mix(N.math('MULTIPLY', bare, 0.75), col, N.ramp(N.noise(20, 2, offset=1), [(0.3, (0.2, 0.13, 0.08)), (0.7, (0.36, 0.25, 0.15))]))
    stone = N.math('MULTIPLY', N.math('LESS_THAN', N.voronoi(9, offset=2), 0.2), N.math('GREATER_THAN', N.noise(2.5, 2, offset=6), 0.58))
    col = N.mix(stone, col, (0.52, 0.5, 0.45))
    hgt = N.math('ADD', N.math('ADD', N.math('MULTIPLY', tuft, 0.8), N.math('MULTIPLY', N.noise(45, 2, 0.8, offset=5), 0.5)), N.math('MULTIPLY', stone, 0.4))
    return col, hgt

def tsoil_graph(N):
    base = N.ramp(N.noise(0.8, 5, 0.65), [(0.3, (0.22, 0.11, 0.065)), (0.55, (0.35, 0.19, 0.105)), (0.75, (0.47, 0.3, 0.18))])
    clod = N.ramp(N.noise(7, 4, 0.7, offset=2), [(0.3, (0.6, 0.6, 0.6)), (0.7, (1.25, 1.25, 1.25))])
    col = N.mix(1.0, base, clod, 'MULTIPLY')
    d = N.voronoi(10); pc = N.voronoi(10, out='Color')
    peb = N.math('MULTIPLY', N.math('LESS_THAN', d, 0.24), N.math('GREATER_THAN', N.noise(1.5, 2, offset=3), 0.5))
    col = N.mix(peb, col, N.mix(0.65, pc, (0.5, 0.46, 0.4)))
    crack = N.math('MULTIPLY', ridge(N, 1.1, 0.004, 3, 4.0, 0.6), N.math('GREATER_THAN', N.noise(0.5, 2, offset=12), 0.45))
    col = N.mix(N.math('MULTIPLY', crack, 0.7), col, (0.07, 0.04, 0.03))
    weed = N.math('GREATER_THAN', N.noise(6, 4, 0.75, offset=15), 0.7)
    col = N.mix(N.math('MULTIPLY', weed, 0.6), col, (0.25, 0.26, 0.1))
    grain = N.ramp(N.noise(55, 2, 0.6, offset=8), [(0.3, (0.75, 0.75, 0.75)), (0.7, (1.2, 1.2, 1.2))])
    col = N.mix(1.0, col, grain, 'MULTIPLY')
    hgt = N.math('ADD', N.math('MULTIPLY', peb, 0.6), N.math('SUBTRACT', N.math('MULTIPLY', N.noise(7, 4, 0.7, offset=2), 0.9), crack))
    return col, hgt

def trock_graph(N):
    strata = N.ramp(N.noise(0.45, 7, 0.75, dist=2.0), [(0.25, (0.27, 0.25, 0.22)), (0.5, (0.45, 0.43, 0.39)), (0.75, (0.64, 0.62, 0.57))])
    crack = N.math('MAXIMUM', ridge(N, 0.6, 0.006, 4, 1.0, 1.0), ridge(N, 1.7, 0.004, 3, 6.0, 0.5))
    col = N.mix(N.math('MULTIPLY', crack, 0.85), strata, (0.06, 0.055, 0.05))
    pit = N.math('GREATER_THAN', N.noise(11, 3, 0.7, offset=4), 0.66)                # forats de la calcària (rascler)
    col = N.mix(N.math('MULTIPLY', pit, 0.5), col, (0.16, 0.15, 0.14))
    lichen = N.math('GREATER_THAN', N.noise(3.5, 4, 0.7, offset=7), 0.67)
    col = N.mix(N.math('MULTIPLY', lichen, 0.5), col, (0.45, 0.4, 0.16))
    moss = N.math('GREATER_THAN', N.noise(2.2, 4, 0.7, offset=17), 0.7)
    col = N.mix(N.math('MULTIPLY', moss, 0.6), col, (0.14, 0.17, 0.07))
    hgt = N.math('SUBTRACT', N.math('MULTIPLY', N.noise(0.45, 7, 0.75, dist=2.0), 1.2), N.math('ADD', crack, N.math('MULTIPLY', pit, 0.4)))
    return col, hgt

def terrain_tex(name, graph):
    col, hgt = bake(name, 512, 512, 6.0, 6.0, graph)
    h = (hgt - hgt.min()) / max(1e-6, hgt.max() - hgt.min())
    col = col * (0.7 + 0.45 * h)[..., None]                    # cavitats més fosques (il·luminació de detall dins el color)
    m = col.reshape(-1, 3).mean(0)
    print('   %s color mitjà (lineal)' % name, [round(float(x), 3) for x in m])
    return save(col, os.path.join(OUT, name + '.png')), [float(x) for x in m]

TERRAIN = {}

def build():
    print('textures')
    out = {}
    for nm, fn in (('road', road), ('ground', ground), ('dirt', dirt), ('stone', stone)):
        a, b = fn()
        out[nm] = (a, 82); out[nm + 'N'] = (b, 88)
    for nm, g in (('tgrass', tgrass_graph), ('tsoil', tsoil_graph), ('trock', trock_graph)):
        p, mean = terrain_tex(nm, g)
        out[nm] = (p, 80); TERRAIN[nm] = mean
    return out

"""Bicicleta de carretera (geometria real: tija 73,5°, direcció 73°, vaines de 41 cm, distància entre eixos 99 cm).

Punts de contacte que fa servir l'animació de l'app (eixos de l'app, metres):
  eix del pedalier (0, 0,30, 0) · roda del darrere (-0,405, 0,35) · roda de davant (0,585, 0,35)
  sella (-0,17, 0,86) · mans a les manetes (0,57, 0,87, ±0,205) · biela de 0,17 m
En Blender: X endavant, Y esquerra, Z amunt.
Materials: 0 = color per vèrtex (pintura, plàstic, goma) · 1 = color de l'equip · 2 = metall
"""
import bpy, math, bmesh
from mathutils import Vector
from common import *

CARBON = (0.022, 0.023, 0.026)
BLACK = (0.012, 0.012, 0.013)
TAPE = (0.018, 0.018, 0.02)
GREY = (0.32, 0.33, 0.35)
SILVER = (0.62, 0.63, 0.66)
WHITE = (0.85, 0.86, 0.87)

BB = Vector((0, 0, 0.30))
RA = Vector((-0.405, 0, 0.35))
FA = Vector((0.585, 0, 0.35))

def steer(z):  # eix de direcció: 73°, amb 45 mm d'avanç de forquilla
    return Vector((0.538 - (z - 0.35) * 0.3057, 0, z))

def aero(a):  # perfil de tub aerodinàmic (llàgrima)
    c, s = math.cos(a), math.sin(a)
    return (c * (1.0 if c > 0 else 0.75), s)

def frame():
    parts = []
    HTb, HTt = steer(0.585), steer(0.745)
    ST_top = Vector((-0.133, 0, 0.75))
    # tub de direcció (més gruixut a baix, com els quadres moderns)
    parts.append(tube('ht', [HTb - (HTt - HTb) * 0.06, HTt + (HTt - HTb) * 0.04], [0.026, 0.021], 16, CARBON))
    # tub inferior: aerodinàmic i ample, de color d'equip
    dt = bezier(BB + Vector((0.02, 0, 0.012)), BB + Vector((0.15, 0, 0.12)), HTb + Vector((-0.12, 0, -0.07)), HTb + Vector((-0.012, 0, 0.012)), 10)
    parts.append(tube('dt', dt, [(0.026, 0.024)] * 3 + [(0.024, 0.021)] * 5 + [(0.024, 0.026)] * 3, 14, CARBON, mat=1, twist_up=Vector((0, 1, 0))))
    # tub superior (lleugerament inclinat, compact)
    tt = bezier(ST_top + Vector((0.005, 0, -0.035)), ST_top + Vector((0.18, 0, -0.012)), HTt + Vector((-0.17, 0, -0.01)), HTt + Vector((-0.006, 0, -0.012)), 8)
    parts.append(tube('tt', tt, [(0.017, 0.02)] * 9, 12, CARBON, twist_up=Vector((0, 1, 0))))
    # tub del seient (corbat al voltant de la roda)
    st = [BB + Vector((-0.004, 0, 0.02)), BB + Vector((-0.028, 0, 0.12)), BB + Vector((-0.07, 0, 0.27)), ST_top]
    parts.append(tube('st', st, [0.021, 0.019, 0.017, 0.016], 14, CARBON, prof=aero, twist_up=Vector((0, 1, 0))))
    # caixa del pedalier
    parts.append(tube('bb', [BB + Vector((0, 0.045, 0)), BB + Vector((0, -0.045, 0))], 0.022, 16, CARBON))
    for sd in (1, -1):
        y = sd * 0.064
        # vaines (baixes) i tirants (alts), units a les potes del darrere
        cs = bezier(BB + Vector((-0.02, sd * 0.03, 0.0)), BB + Vector((-0.15, sd * 0.06, 0.02)), RA + Vector((0.14, y, -0.01)), RA + Vector((0.012, y, 0)), 8)
        parts.append(tube('cs', cs, [0.014, 0.013, 0.012, 0.011, 0.01, 0.009, 0.009, 0.008, 0.008], 10, CARBON))
        ss = bezier(ST_top + Vector((0.012, sd * 0.016, -0.08)), ST_top + Vector((-0.07, sd * 0.05, -0.12)), RA + Vector((0.05, y, 0.12)), RA + Vector((0.008, y, 0.01)), 8)
        parts.append(tube('ss', ss, [0.011, 0.01, 0.009, 0.0085, 0.008, 0.0075, 0.0075, 0.007, 0.007], 10, CARBON, mat=1))
        # pota del darrere
        parts.append(prim('cube', 'drop', loc=(RA.x + 0.006, y, RA.z), scale=(0.018, 0.004, 0.018), rgb=BLACK))
        # forquilla: beines corbes cap a l'eix
        crown = steer(0.585) + Vector((0, 0, -0.012))
        fk = bezier(crown + Vector((0.004, sd * 0.032, -0.01)), crown + Vector((0.03, sd * 0.05, -0.1)), FA + Vector((-0.012, sd * 0.055, 0.1)), FA + Vector((0, sd * 0.055, 0.004)), 8)
        parts.append(tube('fk', fk, [(0.02, 0.012), (0.019, 0.012), (0.017, 0.011), (0.016, 0.01), (0.015, 0.0095), (0.013, 0.009), (0.012, 0.008), (0.01, 0.007), (0.009, 0.006)], 12, CARBON, mat=1 if sd > 0 else 0, prof=aero, twist_up=Vector((0, 1, 0))))
    parts.append(prim('uv_sphere', 'crown', loc=tuple(steer(0.575)), scale=(0.03, 0.045, 0.02), rgb=CARBON, segments=16, ring_count=8))
    # direcció, espaiadors i potència
    st_top = steer(0.80)
    parts.append(tube('steerer', [HTt, st_top], 0.0165, 14, BLACK))
    clamp = Vector((0.50, 0, 0.822))
    parts.append(tube('stem', [st_top + Vector((-0.012, 0, -0.012)), clamp + Vector((0.005, 0, 0))], [(0.018, 0.02), (0.017, 0.016)], 12, BLACK, twist_up=Vector((0, 1, 0))))
    parts.append(tube('stemcap', [st_top + Vector((0, 0.022, 0)), st_top + Vector((0, -0.022, 0))], 0.02, 14, BLACK))
    return parts

def handlebar():
    parts = []
    clamp = Vector((0.50, 0, 0.822))
    parts.append(tube('bar_c', [clamp + Vector((0, 0.06, 0)), clamp + Vector((0, -0.06, 0))], 0.0159, 14, BLACK))
    for sd in (1, -1):
        y = sd * 0.205
        pts = [clamp + Vector((0, sd * 0.05, 0)), clamp + Vector((0, sd * 0.12, 0)), clamp + Vector((0.002, sd * 0.175, 0)), Vector((0.512, sd * 0.196, 0.822)),
               Vector((0.54, y, 0.82)), Vector((0.572, y, 0.812))]
        drop = bezier(Vector((0.572, y, 0.812)), Vector((0.62, y, 0.80)), Vector((0.64, y, 0.73)), Vector((0.585, y, 0.715)), 10)[1:]
        tail = [Vector((0.53, y, 0.712)), Vector((0.49, y, 0.712))]
        parts.append(tube('bar', pts + drop + tail, 0.0125, 12, TAPE))
        # maneta del fre/canvi (el cos on es recolzen les mans) i la palanca
        hood = bezier(Vector((0.565, y, 0.818)), Vector((0.585, y, 0.835)), Vector((0.605, y, 0.86)), Vector((0.618, y, 0.872)), 6)
        parts.append(tube('hood', hood, [(0.017, 0.016), (0.02, 0.02), (0.021, 0.022), (0.02, 0.02), (0.017, 0.018), (0.012, 0.012), (0.008, 0.008)], 12, BLACK))
        lever = bezier(Vector((0.618, y, 0.86)), Vector((0.64, y, 0.80)), Vector((0.635, y, 0.75)), Vector((0.615, y, 0.72)), 6)
        parts.append(tube('lever', lever, [0.008, 0.009, 0.009, 0.008, 0.007, 0.006, 0.005], 8, GREY, mat=2))
    return parts

def saddle_post():
    parts = []
    top = Vector((-0.151, 0, 0.83))
    parts.append(tube('post', [Vector((-0.125, 0, 0.73)), top], (0.0145, 0.012), 14, BLACK, prof=aero))
    parts.append(prim('cube', 'clamp', loc=(top.x, 0, top.z + 0.008), scale=(0.022, 0.016, 0.01), rgb=BLACK))
    # sella: loft de seccions (punta estreta, darrere ample, una mica de forma de cadira)
    bm = bmesh.new()
    sec = []  # (x, mitja amplada, alçada del centre)
    for i in range(15):
        t = i / 14
        x = -0.30 + 0.275 * t
        w = 0.072 * (1 - t) ** 0.6 + 0.018 if t < 0.55 else 0.072 * (0.45) ** 0.6 * (1 - (t - 0.55) / 0.45) ** 0.9 + 0.018
        w = 0.07 if t < 0.12 else w
        z = 0.857 - 0.008 * math.sin(math.pi * t) + (0.006 if t < 0.08 else 0) + 0.004 * t
        sec.append((x, w, z))
    rings = []
    for x, w, z in sec:
        ring = []
        for s in range(16):
            a = 2 * math.pi * s / 16
            cy, cz = math.cos(a), math.sin(a)
            hz = 0.012 if cz > 0 else 0.006
            ring.append(bm.verts.new((x, cy * w, z + cz * hz - (abs(cy) ** 3) * 0.008)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for s in range(16):
            s1 = (s + 1) % 16
            bm.faces.new((rings[i][s], rings[i][s1], rings[i + 1][s1], rings[i + 1][s]))
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / 16)
        for s in range(16):
            s1 = (s + 1) % 16
            bm.faces.new((c, ring[s1], ring[s]) if rev else (c, ring[s], ring[s1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    sd = new_obj('saddle', bm); smooth(sd); subsurf(sd, 1)
    paint(sd, lambda p, n: WHITE if (p.x < -0.27 and n.z < 0.6 and abs(p.y) > 0.045) else (0.03, 0.03, 0.032))
    parts.append(sd)
    for sdn in (1, -1):  # carrils
        parts.append(tube('rail', bezier(Vector((-0.27, sdn * 0.035, 0.846)), Vector((-0.2, sdn * 0.022, 0.832)), Vector((-0.1, sdn * 0.02, 0.832)), Vector((-0.04, sdn * 0.006, 0.848)), 6), 0.0035, 6, SILVER, mat=2))
    return parts

def drivetrain():
    """Part fixa de la transmissió: pinyons, cadena, canvi i desviador, pinces de fre, portabidó i bidó."""
    parts = []
    y = -0.045  # costat de la transmissió (dreta = -Y)
    # pinyons (11 discs)
    for i in range(11):
        r = 0.022 + i * 0.0042
        parts.append(tube('cog', [RA + Vector((0, y + 0.018 - i * 0.0038, 0)), RA + Vector((0, y + 0.0165 - i * 0.0038, 0))], r, 24, SILVER, mat=2))
    # cadena: tram de dalt (plat gran → pinyó) i tram de baix (per la politja del canvi)
    ring_r, cog_r = 0.105, 0.032
    cy = -0.042
    upper = [BB + Vector((0.0, cy, ring_r)), RA + Vector((0, cy, cog_r))]
    parts.append(tube('chain_u', upper, (0.0045, 0.004), 6, GREY, mat=2))
    jockey = RA + Vector((0.01, cy, -0.075))
    lower = [RA + Vector((-0.004, cy, -cog_r)), RA + Vector((0.025, cy, -0.04)), jockey + Vector((0.01, 0, 0.012)), jockey + Vector((0.01, 0, -0.015)), BB + Vector((-0.02, cy, -ring_r + 0.002))]
    parts.append(tube('chain_l', lower, (0.0045, 0.004), 6, GREY, mat=2))
    # canvi del darrere
    parts.append(prim('cube', 'rd_body', loc=(RA.x + 0.005, -0.06, RA.z - 0.035), rot=(0, 0.5, 0), scale=(0.012, 0.009, 0.03), rgb=BLACK))
    parts.append(prim('cube', 'rd_cage', loc=(jockey.x - 0.005, -0.052, jockey.z + 0.02), rot=(0, -0.2, 0), scale=(0.02, 0.003, 0.04), rgb=GREY, mat=2))
    for z in (jockey.z + 0.045, jockey.z):
        parts.append(tube('jockey', [Vector((jockey.x, -0.038, z)), Vector((jockey.x, -0.048, z))], 0.0085, 12, BLACK))
    # desviador
    parts.append(prim('cube', 'fd', loc=(-0.05, -0.04, 0.43), rot=(0, 0.3, 0), scale=(0.03, 0.005, 0.012), rgb=BLACK))
    # pinces de fre de disc i discs (el disc va amb la roda)
    parts.append(prim('cube', 'cal_r', loc=(RA.x + 0.06, 0.07, RA.z + 0.045), rot=(0, 0.6, 0), scale=(0.028, 0.012, 0.016), rgb=BLACK))
    parts.append(prim('cube', 'cal_f', loc=(FA.x - 0.055, 0.07, FA.z + 0.055), rot=(0, -0.9, 0), scale=(0.028, 0.012, 0.016), rgb=BLACK))
    # bidó al tub inferior
    dtc = BB + Vector((0.2, 0, 0.165))
    ang = math.atan2(0.23, 0.36)
    ax = Vector((math.cos(ang), 0, math.sin(ang)))
    up = Vector((-math.sin(ang), 0, math.cos(ang)))
    c = dtc + up * 0.06
    bt = [c - ax * 0.1, c - ax * 0.098, c + ax * 0.06, c + ax * 0.085, c + ax * 0.1, c + ax * 0.115]
    parts.append(tube('bottle', bt, [0.033, 0.036, 0.036, 0.033, 0.015, 0.008], 18, WHITE, mat=1))
    parts.append(tube('cage', [c - ax * 0.06 - up * 0.034, c + ax * 0.07 - up * 0.034], (0.006, 0.02), 8, BLACK))
    return parts

def wheel():
    """Roda de carboni de perfil alt (45 mm) amb coberta de 25 mm, 24 radis, botó i disc (centrada a l'origen)."""
    parts = []
    SEG = 64
    # perfil (r, y) de la llanta, tancat, revolucionat al voltant de Y
    prof = [(0.311, 0.0105), (0.3, 0.0135), (0.285, 0.0135), (0.27, 0.0115), (0.262, 0.0065), (0.26, 0.0), (0.262, -0.0065), (0.27, -0.0115), (0.285, -0.0135), (0.3, -0.0135), (0.311, -0.0105)]
    def revolve(name, prof, seg, rgb, mat=0, closed=False):
        bm = bmesh.new(); rings = []
        for s in range(seg):
            a = 2 * math.pi * s / seg
            rings.append([bm.verts.new((r * math.cos(a), y, r * math.sin(a))) for r, y in prof])
        n = len(prof)
        for s in range(seg):
            A, B = rings[s], rings[(s + 1) % seg]
            for i in range(n - 1 if not closed else n):
                i1 = (i + 1) % n
                bm.faces.new((A[i], A[i1], B[i1], B[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        ob = new_obj(name, bm); smooth(ob); solid(ob, rgb, mat)
        return ob
    rim = revolve('rim', prof, SEG, CARBON)
    # rètol de la llanta (franja de color de l'equip i lletres blanques simulades)
    paint(rim, lambda p, n: (0.55, 0.55, 0.56) if (0.282 < p.length < 0.292 and abs(n.y) > 0.6 and (math.atan2(p.z, p.x) % 1.571) < 0.42) else CARBON)
    # coberta: secció circular amb una mica de pla a terra
    tp = []
    for i in range(14):
        a = 2 * math.pi * i / 14
        tp.append((0.3235 + 0.0125 * math.cos(a), 0.0128 * math.sin(a)))
    tyre = revolve('tyre', tp, SEG, (0.035, 0.035, 0.037), closed=True)
    paint(tyre, lambda p, n: (0.4, 0.33, 0.24) if (abs(n.y) > 0.75 and p.length < 0.322) else (0.035, 0.035, 0.037))
    # botó i radis
    parts += [rim, tyre]
    parts.append(tube('hub', [Vector((0, 0.05, 0)), Vector((0, 0.035, 0)), Vector((0, 0.03, 0)), Vector((0, -0.03, 0)), Vector((0, -0.035, 0)), Vector((0, -0.05, 0))], [0.01, 0.028, 0.016, 0.016, 0.028, 0.01], 16, BLACK))
    for i in range(24):
        a = 2 * math.pi * i / 24
        sd = 1 if i % 2 else -1
        h = Vector((0.026 * math.cos(a + 0.12), sd * 0.032, 0.026 * math.sin(a + 0.12)))
        r = Vector((0.262 * math.cos(a), sd * 0.003, 0.262 * math.sin(a)))
        parts.append(tube('spk', [h, r], 0.0012, 4, SILVER, mat=2, cap=False))
    # disc de fre (costat esquerre)
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=36, radius=0.08)
    disc = new_obj('disc', bm); disc.location = (0, 0.058, 0); disc.rotation_euler = (math.pi / 2, 0, 0)
    sol = disc.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.002
    apply_mods(disc); select_only(disc); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    paint(disc, lambda p, n: (0.16, 0.165, 0.175) if Vector((p.x, p.z)).length > 0.06 else (0.03, 0.03, 0.035) if Vector((p.x, p.z)).length > 0.03 else (0.15, 0.15, 0.16))
    set_mat(disc, 2)
    parts.append(disc)
    return parts

def crankset():
    """Bieles, plats i pedals: giren al voltant de l'eix del pedalier (centrat a l'origen)."""
    parts = []
    y = -0.045
    for r, nt, k in ((0.105, 50, 0), (0.074, 34, 1)):
        bm = bmesh.new()
        outer, inner = [], []
        n = nt * 2
        for i in range(n):
            a = 2 * math.pi * i / n
            rr = r + (0.003 if i % 2 == 0 else -0.001)
            outer.append((rr * math.cos(a), rr * math.sin(a)))
            inner.append(((r - 0.012) * math.cos(a), (r - 0.012) * math.sin(a)))
        yy = y - k * 0.006
        V = lambda x, z, dy: bm.verts.new((x, yy + dy, z))
        o1 = [V(x, z, 0.0012) for x, z in outer]; o2 = [V(x, z, -0.0012) for x, z in outer]
        i1 = [V(x, z, 0.0012) for x, z in inner]; i2 = [V(x, z, -0.0012) for x, z in inner]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((o1[i], o1[j], i1[j], i1[i])); bm.faces.new((o2[j], o2[i], i2[i], i2[j]))
            bm.faces.new((o1[j], o1[i], o2[i], o2[j])); bm.faces.new((i1[i], i1[j], i2[j], i2[i]))
        ob = new_obj('ring', bm); solid(ob, GREY if k == 0 else (0.2, 0.2, 0.21), 2); parts.append(ob)
    # aranya
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        parts.append(tube('spider', [Vector((0, y + 0.004, 0)), Vector((0.096 * math.cos(a), y + 0.002, 0.096 * math.sin(a)))], (0.007, 0.004), 8, BLACK))
    parts.append(tube('axle', [Vector((0, 0.08, 0)), Vector((0, -0.08, 0))], 0.012, 12, SILVER, mat=2))
    for sd, dirx in ((1, 1), (-1, -1)):  # esquerra cap endavant, dreta cap enrere (angle 0)
        yy = sd * 0.074
        arm = [Vector((0, yy, 0)), Vector((dirx * 0.085, yy + sd * 0.004, 0)), Vector((dirx * 0.17, yy + sd * 0.006, 0))]
        parts.append(tube('arm', arm, [(0.012, 0.018), (0.008, 0.014), (0.007, 0.011)], 10, BLACK, twist_up=Vector((0, 1, 0))))
        # pedal: cos pla i simètric (al voltant de l'eix del pedal, perquè giri sense que es noti)
        pc = Vector((dirx * 0.17, yy + sd * 0.04, 0))
        parts.append(tube('pedal_ax', [pc - Vector((0, sd * 0.032, 0)), pc + Vector((0, sd * 0.03, 0))], 0.006, 8, SILVER, mat=2))
        parts.append(tube('pedal', [pc - Vector((0.035, 0, 0)), pc + Vector((0.035, 0, 0))], (0.028, 0.009), 10, BLACK))
    return parts

def build(pack):
    print('bicicleta')
    reset()
    fr = join(frame() + handlebar() + saddle_post() + drivetrain(), 'bike')
    bake_ao([fr], strength=0.55, dist=0.15)
    pack.add('bike', fr)
    reset()
    wh = join(wheel(), 'wheel')
    bake_ao([wh], strength=0.4, dist=0.05)
    pack.add('wheel', wh)
    reset()
    ck = join(crankset(), 'crank')
    pack.add('crank', ck)

def preview_objs():
    a = join(frame() + handlebar() + saddle_post() + drivetrain(), 'bike')
    w1 = join(wheel(), 'w1'); w1.location = RA
    w2 = join(wheel(), 'w2'); w2.location = FA
    c = join(crankset(), 'c'); c.location = BB
    return [a, w1, w2, c]

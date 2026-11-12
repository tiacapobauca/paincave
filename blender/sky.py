"""Cel: panorama equirectangular de la meitat superior del cel, amb núvols volumètrics, renderitzat amb Cycles.

El sol és a l'azimut +X de Blender (a l'app es gira la cúpula perquè coincideixi amb el sol de cada ruta)
i a SUN_EL graus d'alçada (ha de coincidir amb G3A_SUN_EL de l'app).
Sortida: out/sky.png (2048×512, de l'horitzó al zenit) i out/sky.json (colors de l'horitzó, zenit i llum ambiental).
"""
import bpy, math, os, json, random
import numpy as np
from mathutils import Vector
from common import *

OUT = os.path.join(os.path.dirname(__file__), 'out')
SUN_EL = 32.0

def build(w=2048, h=512, samples=48, clouds=True):
    print('cel')
    reset()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.volume_bounces = 8; sc.cycles.max_bounces = 12
    try: sc.cycles.volume_step_rate = 1.0; sc.cycles.volume_max_steps = 256
    except Exception: pass
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.view_settings.exposure = -3.1
    # cel físic (dispersió múltiple) amb el sol a l'est (+X)
    wd = bpy.data.worlds.new('sky'); sc.world = wd; wd.use_nodes = True
    nt = wd.node_tree; bg = nt.nodes['Background']
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_elevation = math.radians(SUN_EL); sky.sun_rotation = math.radians(-90)   # el sol cap a +X
    for k, v in (('sun_disc', True), ('sun_size', math.radians(1.2)), ('sun_intensity', 0.6), ('altitude', 100.0),
                 ('air_density', 1.0), ('aerosol_density', 1.6), ('ozone_density', 1.0), ('dust_density', 1.6)):
        try: setattr(sky, k, v)
        except Exception: pass
    nt.links.new(sky.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 1.0
    # càmera panoràmica: només de l'horitzó (una mica per sota) al zenit
    cam = link(bpy.data.objects.new('cam', bpy.data.cameras.new('cam')))
    cam.data.type = 'PANO'; cam.data.panorama_type = 'EQUIRECTANGULAR'
    cam.data.latitude_min = math.radians(-2.0); cam.data.latitude_max = math.radians(90)
    cam.data.longitude_min = -math.pi; cam.data.longitude_max = math.pi
    cam.rotation_euler = (math.pi / 2, 0, -math.pi / 2)        # el sol queda a la vora esquerra/dreta de la imatge (u = 0)
    cam.location = (0, 0, 2); cam.data.clip_end = 200000
    sc.camera = cam
    # terra fosc (evita que la llum de sota il·lumini els núvols de blau)
    bpy.ops.mesh.primitive_plane_add(size=400000, location=(0, 0, -5)); gnd = bpy.context.active_object
    gm = bpy.data.materials.new('gnd'); gm.use_nodes = True; gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.12, 0.13, 0.1, 1)
    gnd.data.materials.append(gm)
    if clouds:
        # capa de cúmuls: una llosa de volum amb densitat = soroll amb llindar × perfil vertical (base plana, cim arrodonit)
        Z0, Z1, R = 1500.0, 2700.0, 42000.0
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, (Z0 + Z1) / 2)); box = bpy.context.active_object
        box.scale = (R * 2, R * 2, Z1 - Z0)
        m = bpy.data.materials.new('cloud'); m.use_nodes = True; n = m.node_tree; n.nodes.clear()
        out = n.nodes.new('ShaderNodeOutputMaterial'); vol = n.nodes.new('ShaderNodeVolumePrincipled')
        vol.inputs['Color'].default_value = (1, 1, 1, 1); vol.inputs['Anisotropy'].default_value = 0.35
        geo = n.nodes.new('ShaderNodeNewGeometry')
        def math_(op, a, b=None, c=None):
            x = n.nodes.new('ShaderNodeMath'); x.operation = op
            for i, v in enumerate((a, b, c)):
                if v is None: continue
                if isinstance(v, (int, float)): x.inputs[i].default_value = v
                else: n.links.new(v, x.inputs[i])
            return x.outputs[0]
        def noise_(scale, detail, rough, off=0.0):
            mp = n.nodes.new('ShaderNodeMapping'); n.links.new(geo.outputs['Position'], mp.inputs['Vector'])
            mp.inputs['Scale'].default_value = (scale, scale, scale * 1.6); mp.inputs['Location'].default_value = (off, off * 0.7, 0)
            t = n.nodes.new('ShaderNodeTexNoise'); t.inputs['Scale'].default_value = 1; t.inputs['Detail'].default_value = detail; t.inputs['Roughness'].default_value = rough
            n.links.new(mp.outputs[0], t.inputs['Vector']); return t.outputs['Fac']
        big = noise_(1 / 4200.0, 2.0, 0.5, 3.0)            # on hi ha núvols (cobertura)
        mid = noise_(1 / 1100.0, 6.0, 0.66, 11.0)          # forma de coliflor
        sep = n.nodes.new('ShaderNodeSeparateXYZ'); n.links.new(geo.outputs['Position'], sep.inputs[0])
        hz = math_('DIVIDE', math_('SUBTRACT', sep.outputs[2], Z0), Z1 - Z0)          # 0 a la base, 1 al cim
        # com més amunt, més soroll cal perquè hi hagi núvol: bases planes i cims arrodonits
        need = math_('ADD', 0.515, math_('MULTIPLY', math_('POWER', hz, 1.4), 0.2))
        shape = math_('ADD', math_('MULTIPLY', big, 0.62), math_('MULTIPLY', mid, 0.38))
        dens = math_('MULTIPLY', math_('MAXIMUM', math_('SUBTRACT', shape, need), 0.0), 0.07)
        dens = math_('MULTIPLY', dens, math_('MINIMUM', math_('MULTIPLY', hz, 14.0), 1.0))
        n.links.new(dens, vol.inputs['Density']); n.links.new(vol.outputs[0], out.inputs['Volume'])
        box.data.materials.append(m)
    sc.render.filepath = os.path.join(OUT, 'sky.png')
    bpy.ops.render.render(write_still=True)
    from PIL import Image
    im = Image.open(sc.render.filepath).convert('RGB'); a = np.asarray(im).astype(np.float32) / 255
    lin = lambda c: np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    hrow = a[int(h * 0.955):int(h * 0.975)].reshape(-1, 3); zen = a[:int(h * 0.12)].reshape(-1, 3)
    # colors (sRGB 0-1): horitzó (per a la boira), zenit, i mitjana ponderada del cel (llum ambiental)
    lat = np.linspace(90, -2, h)[:, None]; wgt = np.cos(np.radians(lat)) * np.ones((1, w))
    amb = (lin(a) * wgt[..., None]).sum((0, 1)) / wgt.sum()
    meta = dict(el=SUN_EL, hz=[float(x) for x in np.median(hrow, 0)], top=[float(x) for x in zen.mean(0)],
                amb=[float(x) for x in amb], lat0=-2.0)
    json.dump(meta, open(os.path.join(OUT, 'sky.json'), 'w'))
    print('  ', meta)
    return meta

if __name__ == '__main__':
    import sys, time
    t = time.time()
    build(*(int(x) for x in sys.argv[1:4])) if len(sys.argv) > 3 else build()
    print('temps', time.time() - t)

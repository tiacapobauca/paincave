"""Previsualització ràpida d'un mòdul amb Cycles: python3 preview.py bike out.png"""
import sys, math, bpy
sys.path.insert(0, __import__('os').path.dirname(__file__))
from common import *
import importlib
mod = importlib.import_module(sys.argv[1])
fn = sys.argv[3] if len(sys.argv) > 3 else 'preview_objs'
reset()
obs = getattr(mod, fn)()
sc = bpy.context.scene
mat = bpy.data.materials.new('vc'); mat.use_nodes = True
nt = mat.node_tree; bsdf = nt.nodes['Principled BSDF']
attr = nt.nodes.new('ShaderNodeVertexColor'); attr.layer_name = 'Col'
nt.links.new(attr.outputs['Color'], bsdf.inputs['Base Color']); bsdf.inputs['Roughness'].default_value = 0.5
for o in obs:
    if not o.data.materials or o.data.materials[0].name == 'tmp':
        o.data.materials.clear(); o.data.materials.append(mat)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
ctr = Vector(eval(sys.argv[4])) if len(sys.argv) > 4 else Vector((0.1, 0, 0.55))
d = float(sys.argv[5]) if len(sys.argv) > 5 else 2.2
for i, (az, el) in enumerate(((-1.25, 0.25), (-2.4, 0.35))):
    cam.location = ctr + Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * d
    cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 32; sc.render.resolution_x = 900; sc.render.resolution_y = 600
    w = sc.world or bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.7, 0.75, 0.8, 1)
    if not any(o.type == 'LIGHT' for o in sc.objects):
        sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun); sun.rotation_euler = (0.6, 0.2, 0.8); sun.data.energy = 3
    sc.render.filepath = sys.argv[2].replace('.png', '_%d.png' % i)
    bpy.ops.render.render(write_still=True)

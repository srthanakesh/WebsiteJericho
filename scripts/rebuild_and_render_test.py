import socket
import json

def execute_blender(code):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(60.0)
    s.connect(('127.0.0.1', 9876))
    cmd = {'type': 'execute_code', 'params': {'code': code}}
    s.sendall(json.dumps(cmd).encode('utf-8'))
    buf = b''
    while True:
        try:
            chunk = s.recv(8192)
            if not chunk:
                break
            buf += chunk
            try:
                res = json.loads(buf.decode('utf-8'))
                s.close()
                return res
            except:
                pass
        except:
            break
    s.close()
    return None

code = r'''
import bpy
import bmesh
import math
import mathutils
import os

tex_dir = r"c:\Users\srtha\Downloads\JerichoWebsite\website\assets\components\realistic"

# Reload all images
for img in bpy.data.images:
    try:
        img.reload()
    except:
        pass

root = bpy.data.objects.get("Jericho_Root")

# Clean up component objects
to_remove = [o for o in bpy.data.objects if o.name.startswith("Jericho_") and o.name != "Jericho_Root"]
for o in to_remove:
    bpy.data.objects.remove(o, do_unlink=True)

to_remove_meshes = [m for m in bpy.data.meshes if m.name.startswith("Jericho_")]
for m in to_remove_meshes:
    bpy.data.meshes.remove(m, do_unlink=True)

# Helper for PBR material
def make_pbr_card_mat(name, diffuse_file, rough_file=None, metal_file=None):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    out = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    
    if os.path.exists(diffuse_file):
        tex = nodes.new(type='ShaderNodeTexImage')
        tex.image = bpy.data.images.load(diffuse_file, check_existing=True)
        tex.image.reload()
        links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
        
    if rough_file and os.path.exists(rough_file):
        tr = nodes.new(type='ShaderNodeTexImage')
        tr.image = bpy.data.images.load(rough_file, check_existing=True)
        tr.image.colorspace_settings.name = 'Non-Color'
        tr.image.reload()
        links.new(tr.outputs['Color'], bsdf.inputs['Roughness'])
    else:
        bsdf.inputs['Roughness'].default_value = 0.32
        
    if metal_file and os.path.exists(metal_file):
        tm = nodes.new(type='ShaderNodeTexImage')
        tm.image = bpy.data.images.load(metal_file, check_existing=True)
        tm.image.colorspace_settings.name = 'Non-Color'
        tm.image.reload()
        links.new(tm.outputs['Color'], bsdf.inputs['Metallic'])
    else:
        bsdf.inputs['Metallic'].default_value = 0.15
        
    if hasattr(mat, 'surface_render_method'):
        mat.surface_render_method = 'BLENDED'
    mat.blend_method = 'BLEND'
    return mat

mat_spk = make_pbr_card_mat("Mat_SpeakerPBR", os.path.join(tex_dir, "tex_speaker_diffuse.png"), os.path.join(tex_dir, "tex_speaker_roughness.png"), os.path.join(tex_dir, "tex_speaker_metallic.png"))
mat_bat = make_pbr_card_mat("Mat_BatteryPBR", os.path.join(tex_dir, "tex_battery_diffuse.png"), os.path.join(tex_dir, "tex_battery_roughness.png"), os.path.join(tex_dir, "tex_battery_metallic.png"))
mat_pcb = make_pbr_card_mat("Mat_PCBPBR", os.path.join(tex_dir, "tex_pcb_diffuse.png"), os.path.join(tex_dir, "tex_pcb_roughness.png"), os.path.join(tex_dir, "tex_pcb_metallic.png"))
mat_cab = make_pbr_card_mat("Mat_CablePBR", os.path.join(tex_dir, "tex_cable_diffuse.png"), os.path.join(tex_dir, "tex_cable_roughness.png"), os.path.join(tex_dir, "tex_cable_metallic.png"))
mat_pill = make_pbr_card_mat("Mat_PillPBR", os.path.join(tex_dir, "tex_sensor_pill_diffuse.png"), os.path.join(tex_dir, "tex_sensor_pill_roughness.png"), os.path.join(tex_dir, "tex_sensor_pill_metallic.png"))

# Dark tinted lens material
mat_lens_dark = bpy.data.materials.get("Mat_ClearLens")
if not mat_lens_dark:
    mat_lens_dark = bpy.data.materials.new("Mat_ClearLens")
mat_lens_dark.use_nodes = True
nodes = mat_lens_dark.node_tree.nodes
nodes.clear()
out = nodes.new(type='ShaderNodeOutputMaterial')
bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
bsdf.inputs['Base Color'].default_value = (0.07, 0.09, 0.11, 1.0)
bsdf.inputs['Metallic'].default_value = 0.05
bsdf.inputs['Roughness'].default_value = 0.04
bsdf.inputs['Alpha'].default_value = 0.35
mat_lens_dark.node_tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
if hasattr(mat_lens_dark, 'surface_render_method'):
    mat_lens_dark.surface_render_method = 'BLENDED'
mat_lens_dark.blend_method = 'BLEND'

for name in ["Lens_Meta_Right", "Lens_Meta_Left"]:
    o = bpy.data.objects.get(name)
    if o and o.data:
        o.data.materials.clear()
        o.data.materials.append(mat_lens_dark)

# Camera Barrel and Optic Materials
mat_cam_anodized = bpy.data.materials.get("Mat_CamAnodized")
if not mat_cam_anodized:
    mat_cam_anodized = bpy.data.materials.new("Mat_CamAnodized")
mat_cam_anodized.use_nodes = True
nodes = mat_cam_anodized.node_tree.nodes
nodes.clear()
out = nodes.new(type='ShaderNodeOutputMaterial')
bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
bsdf.inputs['Base Color'].default_value = (0.020, 0.020, 0.022, 1.0)
bsdf.inputs['Metallic'].default_value = 0.94
bsdf.inputs['Roughness'].default_value = 0.18
mat_cam_anodized.node_tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

mat_cam_optic_glass = bpy.data.materials.get("Mat_CamOpticGlass")
if not mat_cam_optic_glass:
    mat_cam_optic_glass = bpy.data.materials.new("Mat_CamOpticGlass")
mat_cam_optic_glass.use_nodes = True
nodes = mat_cam_optic_glass.node_tree.nodes
nodes.clear()
out = nodes.new(type='ShaderNodeOutputMaterial')
bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
bsdf.inputs['Base Color'].default_value = (0.010, 0.012, 0.022, 1.0)
bsdf.inputs['Metallic'].default_value = 0.15
bsdf.inputs['Roughness'].default_value = 0.012
bsdf.inputs['Alpha'].default_value = 0.96
mat_cam_optic_glass.node_tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

mat_sensor_dot = bpy.data.materials.get("Mat_SensorDot")
if not mat_sensor_dot:
    mat_sensor_dot = bpy.data.materials.new("Mat_SensorDot")
mat_sensor_dot.use_nodes = True
nodes = mat_sensor_dot.node_tree.nodes
nodes.clear()
out = nodes.new(type='ShaderNodeOutputMaterial')
bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
bsdf.inputs['Base Color'].default_value = (0.035, 0.035, 0.038, 1.0)
bsdf.inputs['Metallic'].default_value = 0.4
bsdf.inputs['Roughness'].default_value = 0.3
mat_sensor_dot.node_tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

# Function to build precision double-sided card
def create_pbr_card(name, width, height, material, parent=root):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    hw, hh = width / 2.0, height / 2.0
    
    # Vertices
    v0 = bm.verts.new((-hw, -hh, 0.0001))
    v1 = bm.verts.new(( hw, -hh, 0.0001))
    v2 = bm.verts.new(( hw,  hh, 0.0001))
    v3 = bm.verts.new((-hw,  hh, 0.0001))
    f_front = bm.faces.new((v0, v1, v2, v3))
    
    v4 = bm.verts.new((-hw, -hh, -0.0001))
    v5 = bm.verts.new(( hw, -hh, -0.0001))
    v6 = bm.verts.new(( hw,  hh, -0.0001))
    v7 = bm.verts.new((-hw,  hh, -0.0001))
    f_back = bm.faces.new((v7, v6, v5, v4))
    
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    uv_layer = bm.loops.layers.uv.verify()
    for loop in f_front.loops:
        u = 0.0 if loop.vert.co.x < 0 else 1.0
        v = 0.0 if loop.vert.co.y < 0 else 1.0
        loop[uv_layer].uv = (u, v)
    for loop in f_back.loops:
        u = 1.0 if loop.vert.co.x < 0 else 0.0
        v = 0.0 if loop.vert.co.y < 0 else 1.0
        loop[uv_layer].uv = (u, v)
        
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    if parent:
        obj.parent = parent
    return obj

# 4 Components strictly on Right side
# Speaker: (101 x 98) -> 0.0101 x 0.0098
create_pbr_card("Jericho_SpeakerModule_R", 0.0105, 0.0100, mat_spk)
# Battery: (177 x 85) -> 0.0185 x 0.0088
create_pbr_card("Jericho_BatteryModule_R", 0.0185, 0.0088, mat_bat)
# PCB: (107 x 115) -> 0.0115 x 0.0122
create_pbr_card("Jericho_SoCPCB_R", 0.0118, 0.0125, mat_pcb)
# Cable: (152 x 90) -> 0.0165 x 0.0098
create_pbr_card("Jericho_FPC_Ribbon_R", 0.0165, 0.0098, mat_cab)

# Camera Module strictly on Right side
def make_cam_barrel_mesh(bm):
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.0048, radius2=0.0048, depth=0.0036)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.0040, radius2=0.0040, depth=0.0022, matrix=mathutils.Matrix.Translation((0, 0, 0.0026)))
    bmesh.ops.create_cone(bm, cap_ends=False, segments=32, radius1=0.0036, radius2=0.0033, depth=0.0010, matrix=mathutils.Matrix.Translation((0, 0, 0.0040)))

cam_mesh = bpy.data.meshes.new("Jericho_CameraModule_R")
bm = bmesh.new()
make_cam_barrel_mesh(bm)
bm.to_mesh(cam_mesh)
bm.free()
cam_obj = bpy.data.objects.new("Jericho_CameraModule_R", cam_mesh)
bpy.context.collection.objects.link(cam_obj)
cam_obj.data.materials.append(mat_cam_anodized)
cam_obj.parent = root

optic_mesh = bpy.data.meshes.new("Jericho_CameraOptics_R")
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.0031)
bm.to_mesh(optic_mesh)
bm.free()
optic_obj = bpy.data.objects.new("Jericho_CameraOptics_R", optic_mesh)
bpy.context.collection.objects.link(optic_obj)
optic_obj.data.materials.append(mat_cam_optic_glass)
optic_obj.parent = cam_obj
optic_obj.location = mathutils.Vector((0, 0, 0.0038))
optic_obj.scale = mathutils.Vector((1.0, 1.0, 0.22))

# Sensor pill
create_pbr_card("Jericho_SensorPill_R", 0.0085, 0.0058, mat_pill)

# Sensor dot
dot_mesh = bpy.data.meshes.new("Jericho_SensorDot_R")
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.0018, radius2=0.0018, depth=0.0010)
bm.to_mesh(dot_mesh)
bm.free()
dot_obj = bpy.data.objects.new("Jericho_SensorDot_R", dot_mesh)
bpy.context.collection.objects.link(dot_obj)
dot_obj.data.materials.append(mat_sensor_dot)
dot_obj.parent = root

# Left temple stays assembled
tl = bpy.data.objects.get("Temple_Meta_Left")
if tl and tl.animation_data:
    tl.animation_data_clear()
    tl.location = (0, 0, 0)

print("SUCCESS: Precision PBR components created without borders!")
'''

res = execute_blender(code)
print(res)

import socket
import json
import os

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

# 1. Clean up ALL old/duplicate Jericho objects
to_remove = [o for o in bpy.data.objects if o.name.startswith("Jericho_") and o.name != "Jericho_Root"]
for o in to_remove:
    bpy.data.objects.remove(o, do_unlink=True)

# Also clean up old meshes
to_remove_meshes = [m for m in bpy.data.meshes if m.name.startswith("Jericho_")]
for m in to_remove_meshes:
    bpy.data.meshes.remove(m, do_unlink=True)

root = bpy.data.objects.get("Jericho_Root")
if not root:
    root = bpy.data.objects.new("Jericho_Root", None)
    bpy.context.collection.objects.link(root)

root.rotation_euler = (0, 0, 0)
root.location = (0, 0, 0)
bpy.context.view_layer.update()

# Materials creation
def make_principled_mat(name, base_color=(0.1, 0.1, 0.1, 1.0), metallic=0.0, roughness=0.5, alpha=1.0):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    out = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = base_color
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Alpha'].default_value = alpha
    mat.node_tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    
    if hasattr(mat, 'surface_render_method'):
        mat.surface_render_method = 'BLENDED' if alpha < 1.0 else 'DITHERED'
    if alpha < 1.0:
        mat.blend_method = 'BLEND'
    return mat

def make_textured_mat(name, img_path, rough_path=None, metal_path=None, alpha_blend=False):
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
    
    if os.path.exists(img_path):
        tex = nodes.new(type='ShaderNodeTexImage')
        tex.image = bpy.data.images.load(img_path, check_existing=True)
        links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        if alpha_blend:
            links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
            
    if rough_path and os.path.exists(rough_path):
        tr = nodes.new(type='ShaderNodeTexImage')
        tr.image = bpy.data.images.load(rough_path, check_existing=True)
        tr.image.colorspace_settings.name = 'Non-Color'
        links.new(tr.outputs['Color'], bsdf.inputs['Roughness'])
    else:
        bsdf.inputs['Roughness'].default_value = 0.32
        
    if metal_path and os.path.exists(metal_path):
        tm = nodes.new(type='ShaderNodeTexImage')
        tm.image = bpy.data.images.load(metal_path, check_existing=True)
        tm.image.colorspace_settings.name = 'Non-Color'
        links.new(tm.outputs['Color'], bsdf.inputs['Metallic'])
    else:
        bsdf.inputs['Metallic'].default_value = 0.15
        
    if alpha_blend:
        if hasattr(mat, 'surface_render_method'):
            mat.surface_render_method = 'BLENDED'
        mat.blend_method = 'BLEND'
    else:
        if hasattr(mat, 'surface_render_method'):
            mat.surface_render_method = 'DITHERED'
    return mat

# Base Chassis Materials
mat_chassis_black = make_principled_mat("Mat_ChassisBlack", (0.028, 0.028, 0.030, 1.0), metallic=0.35, roughness=0.32)
mat_battery_body = make_principled_mat("Mat_BatteryBody", (0.025, 0.025, 0.028, 1.0), metallic=0.15, roughness=0.38)
mat_pcb_edge_gold = make_principled_mat("Mat_PCBEdgeGold", (0.86, 0.72, 0.28, 1.0), metallic=0.96, roughness=0.14)
mat_cable_substrate = make_principled_mat("Mat_CableSubstrate", (0.08, 0.07, 0.06, 1.0), metallic=0.2, roughness=0.3)

# PBR Textured Materials
mat_speaker_front = make_textured_mat(
    "Mat_SpeakerFront",
    os.path.join(tex_dir, "tex_speaker_diffuse.png"),
    os.path.join(tex_dir, "tex_speaker_roughness.png"),
    os.path.join(tex_dir, "tex_speaker_metallic.png"),
    alpha_blend=True
)
mat_battery_front = make_textured_mat(
    "Mat_BatteryFront",
    os.path.join(tex_dir, "tex_battery_diffuse.png"),
    os.path.join(tex_dir, "tex_battery_roughness.png"),
    os.path.join(tex_dir, "tex_battery_metallic.png"),
    alpha_blend=True
)
mat_pcb_front = make_textured_mat(
    "Mat_PCBFront",
    os.path.join(tex_dir, "tex_pcb_diffuse.png"),
    os.path.join(tex_dir, "tex_pcb_roughness.png"),
    os.path.join(tex_dir, "tex_pcb_metallic.png"),
    alpha_blend=True
)
mat_cable_front = make_textured_mat(
    "Mat_CableFront",
    os.path.join(tex_dir, "tex_cable_diffuse.png"),
    os.path.join(tex_dir, "tex_cable_roughness.png"),
    os.path.join(tex_dir, "tex_cable_metallic.png"),
    alpha_blend=True
)
mat_pill_front = make_textured_mat(
    "Mat_PillFront",
    os.path.join(tex_dir, "tex_sensor_pill_diffuse.png"),
    os.path.join(tex_dir, "tex_sensor_pill_roughness.png"),
    os.path.join(tex_dir, "tex_sensor_pill_metallic.png"),
    alpha_blend=True
)

# Dark tinted lens material
mat_lens_dark = make_principled_mat("Mat_ClearLens", (0.07, 0.09, 0.11, 1.0), metallic=0.05, roughness=0.04, alpha=0.35)
for name in ["Lens_Meta_Right", "Lens_Meta_Left"]:
    o = bpy.data.objects.get(name)
    if o and o.data:
        o.data.materials.clear()
        o.data.materials.append(mat_lens_dark)

# Camera Barrel and Optic Materials
mat_cam_anodized = make_principled_mat("Mat_CamAnodized", (0.022, 0.022, 0.024, 1.0), metallic=0.92, roughness=0.18)
mat_cam_optic_glass = make_principled_mat("Mat_CamOpticGlass", (0.015, 0.035, 0.095, 0.94), metallic=0.12, roughness=0.015, alpha=0.94)
mat_cam_lens_rim = make_principled_mat("Mat_CamLensRim", (0.06, 0.06, 0.065, 1.0), metallic=0.8, roughness=0.25)
mat_sensor_dot = make_principled_mat("Mat_SensorDot", (0.035, 0.035, 0.038, 1.0), metallic=0.4, roughness=0.3)

# Function to build solid 3D component with front texture face and solid rim/back
def create_solid_component(name, width, height, thickness, mat_front, mat_side, parent=root):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    hw, hh = width / 2.0, height / 2.0
    tz = thickness / 2.0
    
    # Vertices
    v0 = bm.verts.new((-hw, -hh,  tz))
    v1 = bm.verts.new(( hw, -hh,  tz))
    v2 = bm.verts.new(( hw,  hh,  tz))
    v3 = bm.verts.new((-hw,  hh,  tz))
    
    v4 = bm.verts.new((-hw, -hh, -tz))
    v5 = bm.verts.new(( hw, -hh, -tz))
    v6 = bm.verts.new(( hw,  hh, -tz))
    v7 = bm.verts.new((-hw,  hh, -tz))
    
    f_front = bm.faces.new((v0, v1, v2, v3))
    f_back = bm.faces.new((v7, v6, v5, v4))
    
    f_bottom = bm.faces.new((v0, v4, v5, v1))
    f_right = bm.faces.new((v1, v5, v6, v2))
    f_top = bm.faces.new((v2, v6, v7, v3))
    f_left = bm.faces.new((v3, v7, v4, v0))
    
    f_front.material_index = 0
    f_back.material_index = 1
    for f in [f_bottom, f_right, f_top, f_left]:
        f.material_index = 1
        
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    uv_layer = bm.loops.layers.uv.verify()
    for loop in f_front.loops:
        u = 0.0 if loop.vert.co.x < 0 else 1.0
        v = 0.0 if loop.vert.co.y < 0 else 1.0
        loop[uv_layer].uv = (u, v)
        
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat_front)
    obj.data.materials.append(mat_side)
    if parent:
        obj.parent = parent
    return obj

# Build the 4 realistic components on Right side (and Left side for temple)
for side in ["R", "L"]:
    sign = 1.0 if side == "R" else -1.0
    
    # 1. Speaker
    create_solid_component(
        f"Jericho_SpeakerModule_{side}",
        width=0.0108, height=0.0094, thickness=0.0028,
        mat_front=mat_speaker_front, mat_side=mat_chassis_black
    )
    
    # 2. Battery
    create_solid_component(
        f"Jericho_BatteryModule_{side}",
        width=0.0194, height=0.0074, thickness=0.0030,
        mat_front=mat_battery_front, mat_side=mat_battery_body
    )
    
    # 3. Main SoC PCB
    create_solid_component(
        f"Jericho_SoCPCB_{side}",
        width=0.0130, height=0.0115, thickness=0.0012,
        mat_front=mat_pcb_front, mat_side=mat_pcb_edge_gold
    )
    
    # 4. Flex Cable
    create_solid_component(
        f"Jericho_FPC_Ribbon_{side}",
        width=0.0172, height=0.0089, thickness=0.0004,
        mat_front=mat_cable_front, mat_side=mat_cable_substrate
    )

# CAMERA MODULE: ONLY ON RIGHT SIDE
# Precision lathe/cylinder stepped camera barrel
def make_cam_barrel_mesh(bm):
    # Main outer barrel
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.0048, radius2=0.0048, depth=0.0036)
    # Step ring
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.0040, radius2=0.0040, depth=0.0022, matrix=mathutils.Matrix.Translation((0, 0, 0.0026)))
    # Front rim / aperture
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

# Dark AR-coated optical element
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

# Sensor pill on right side
create_solid_component(
    "Jericho_SensorPill_R",
    width=0.0085, height=0.0055, thickness=0.0020,
    mat_front=mat_pill_front, mat_side=mat_chassis_black
)

# Sensor dot on right side
dot_mesh = bpy.data.meshes.new("Jericho_SensorDot_R")
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.0018, radius2=0.0018, depth=0.0010)
bm.to_mesh(dot_mesh)
bm.free()
dot_obj = bpy.data.objects.new("Jericho_SensorDot_R", dot_mesh)
bpy.context.collection.objects.link(dot_obj)
dot_obj.data.materials.append(mat_sensor_dot)
dot_obj.parent = root

print("SUCCESS: Scene rebuilt with photorealistic solid components and camera ONLY on right side!")
'''

res = execute_blender(code)
print(res)

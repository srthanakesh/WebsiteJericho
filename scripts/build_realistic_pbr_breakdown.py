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

blender_code = r'''
import bpy
import bmesh
import math
import mathutils
import os

# Textures directory
tex_dir = r"c:\Users\srtha\Downloads\JerichoWebsite\website\assets\components\realistic"

def get_or_create_pbr_material(name, diffuse_file, roughness_file=None, metallic_file=None, alpha_blend=True):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    node_out = nodes.new(type='ShaderNodeOutputMaterial')
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    links.new(node_bsdf.outputs['BSDF'], node_out.inputs['Surface'])
    
    # Diffuse / Color
    if diffuse_file and os.path.exists(diffuse_file):
        tex_diff = nodes.new(type='ShaderNodeTexImage')
        tex_diff.image = bpy.data.images.load(diffuse_file, check_existing=True)
        links.new(tex_diff.outputs['Color'], node_bsdf.inputs['Base Color'])
        if alpha_blend:
            links.new(tex_diff.outputs['Alpha'], node_bsdf.inputs['Alpha'])
            
    # Roughness
    if roughness_file and os.path.exists(roughness_file):
        tex_rough = nodes.new(type='ShaderNodeTexImage')
        tex_rough.image = bpy.data.images.load(roughness_file, check_existing=True)
        tex_rough.image.colorspace_settings.name = 'Non-Color'
        links.new(tex_rough.outputs['Color'], node_bsdf.inputs['Roughness'])
    else:
        node_bsdf.inputs['Roughness'].default_value = 0.35
        
    # Metallic
    if metallic_file and os.path.exists(metallic_file):
        tex_metal = nodes.new(type='ShaderNodeTexImage')
        tex_metal.image = bpy.data.images.load(metallic_file, check_existing=True)
        tex_metal.image.colorspace_settings.name = 'Non-Color'
        links.new(tex_metal.outputs['Color'], node_bsdf.inputs['Metallic'])
    else:
        node_bsdf.inputs['Metallic'].default_value = 0.1
        
    if alpha_blend:
        if hasattr(mat, 'surface_render_method'):
            mat.surface_render_method = 'BLENDED'
        mat.blend_method = 'BLEND'
    else:
        if hasattr(mat, 'surface_render_method'):
            mat.surface_render_method = 'DITHERED'
            
    return mat

def get_or_create_basic_material(name, base_color=(0.1, 0.1, 0.1, 1.0), metallic=0.0, roughness=0.5, alpha=1.0):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_out = nodes.new(type='ShaderNodeOutputMaterial')
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_bsdf.inputs['Base Color'].default_value = base_color
    node_bsdf.inputs['Metallic'].default_value = metallic
    node_bsdf.inputs['Roughness'].default_value = roughness
    node_bsdf.inputs['Alpha'].default_value = alpha
    mat.node_tree.links.new(node_bsdf.outputs['BSDF'], node_out.inputs['Surface'])
    
    if hasattr(mat, 'surface_render_method'):
        mat.surface_render_method = 'BLENDED' if alpha < 1.0 else 'DITHERED'
    if alpha < 1.0:
        mat.blend_method = 'BLEND'
    return mat

def create_mesh_object(name, mesh_builder, material=None, parent=None):
    old_obj = bpy.data.objects.get(name)
    if old_obj:
        bpy.data.objects.remove(old_obj, do_unlink=True)
    old_mesh = bpy.data.meshes.get(name)
    if old_mesh:
        bpy.data.meshes.remove(old_mesh, do_unlink=True)
        
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    mesh_builder(bm)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if material:
        obj.data.materials.append(material)
    if parent:
        obj.parent = parent
    return obj

# Remove ALL unwanted objects:
# 1. Left side camera, pill, optics, bezel
for name in [
    "Jericho_CameraModule_L", "Jericho_CameraOptics_L", "Jericho_CameraBezel_L", 
    "Jericho_SensorPill_L", "Jericho_LensBevel_L", "Jericho_LensBevel_R",
    "Jericho_LensBevel", "Jericho_CameraModule", "Jericho_CameraOptics", "Jericho_CameraBezel",
    "Jericho_SensorPill", "Jericho_HingeTongue", "Jericho_HingeTongue_L", "Jericho_HingeTongue_R"
]:
    o = bpy.data.objects.get(name)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)

root = bpy.data.objects.get("Jericho_Root")
if not root:
    root = bpy.data.objects.new("Jericho_Root", None)
    bpy.context.collection.objects.link(root)

root.rotation_euler = (0, 0, 0)
root.location = (0, 0, 0)
bpy.context.view_layer.update()

# Materials
mat_speaker = get_or_create_pbr_material(
    "Mat_PBR_Speaker",
    os.path.join(tex_dir, "tex_speaker_diffuse.png"),
    os.path.join(tex_dir, "tex_speaker_roughness.png"),
    os.path.join(tex_dir, "tex_speaker_metallic.png")
)
mat_battery = get_or_create_pbr_material(
    "Mat_PBR_Battery",
    os.path.join(tex_dir, "tex_battery_diffuse.png"),
    os.path.join(tex_dir, "tex_battery_roughness.png"),
    os.path.join(tex_dir, "tex_battery_metallic.png")
)
mat_pcb = get_or_create_pbr_material(
    "Mat_PBR_PCB",
    os.path.join(tex_dir, "tex_pcb_diffuse.png"),
    os.path.join(tex_dir, "tex_pcb_roughness.png"),
    os.path.join(tex_dir, "tex_pcb_metallic.png")
)
mat_cable = get_or_create_pbr_material(
    "Mat_PBR_Cable",
    os.path.join(tex_dir, "tex_cable_diffuse.png"),
    os.path.join(tex_dir, "tex_cable_roughness.png"),
    os.path.join(tex_dir, "tex_cable_metallic.png")
)
mat_cam_tex = get_or_create_pbr_material(
    "Mat_PBR_Camera",
    os.path.join(tex_dir, "tex_camera_diffuse.png"),
    os.path.join(tex_dir, "tex_camera_roughness.png"),
    os.path.join(tex_dir, "tex_camera_metallic.png")
)
mat_pill_tex = get_or_create_pbr_material(
    "Mat_PBR_Pill",
    os.path.join(tex_dir, "tex_sensor_pill_diffuse.png"),
    os.path.join(tex_dir, "tex_sensor_pill_roughness.png"),
    os.path.join(tex_dir, "tex_sensor_pill_metallic.png")
)

# Dark tinted lens material
mat_lens_dark = get_or_create_basic_material("Mat_ClearLens", (0.07, 0.09, 0.11, 1.0), metallic=0.05, roughness=0.04, alpha=0.35)
for name in ["Lens_Meta_Right", "Lens_Meta_Left"]:
    o = bpy.data.objects.get(name)
    if o and o.data:
        o.data.materials.clear()
        o.data.materials.append(mat_lens_dark)

# Camera metal & glass materials
mat_cam_barrel = get_or_create_basic_material("Mat_CamBarrelMetal", (0.025, 0.025, 0.028, 1.0), metallic=0.92, roughness=0.20)
mat_cam_optic = get_or_create_basic_material("Mat_CamGlassOptic", (0.02, 0.06, 0.18, 0.90), metallic=0.1, roughness=0.02, alpha=0.90)
mat_pill_metal = get_or_create_basic_material("Mat_PillMetal", (0.04, 0.04, 0.045, 1.0), metallic=0.3, roughness=0.3)

# Helper function to create UV-mapped beveled solid cards
def build_planar_card(bm, width, height, thickness=0.001):
    hw, hh = width / 2.0, height / 2.0
    # Front face verts (z = +thickness/2)
    v0 = bm.verts.new((-hw, -hh, thickness/2.0))
    v1 = bm.verts.new(( hw, -hh, thickness/2.0))
    v2 = bm.verts.new(( hw,  hh, thickness/2.0))
    v3 = bm.verts.new((-hw,  hh, thickness/2.0))
    f_front = bm.faces.new((v0, v1, v2, v3))
    
    # Back face verts (z = -thickness/2)
    v4 = bm.verts.new((-hw, -hh, -thickness/2.0))
    v5 = bm.verts.new(( hw, -hh, -thickness/2.0))
    v6 = bm.verts.new(( hw,  hh, -thickness/2.0))
    v7 = bm.verts.new((-hw,  hh, -thickness/2.0))
    f_back = bm.faces.new((v7, v6, v5, v4))
    
    # Side faces
    bm.faces.new((v0, v4, v5, v1))
    bm.faces.new((v1, v5, v6, v2))
    bm.faces.new((v2, v6, v7, v3))
    bm.faces.new((v3, v7, v4, v0))
    
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    # UV map front and back
    uv_layer = bm.loops.layers.uv.verify()
    for loop in f_front.loops:
        u = 0.0 if loop.vert.co.x < 0 else 1.0
        v = 0.0 if loop.vert.co.y < 0 else 1.0
        loop[uv_layer].uv = (u, v)
    for loop in f_back.loops:
        u = 1.0 if loop.vert.co.x < 0 else 0.0
        v = 0.0 if loop.vert.co.y < 0 else 1.0
        loop[uv_layer].uv = (u, v)

# Build realistic components for Right and Left temples
for side in ["R", "L"]:
    sign = 1.0 if side == "R" else -1.0
    
    # 1. Speaker
    def make_spk(bm):
        build_planar_card(bm, 0.0108, 0.0094, 0.0022)
    create_mesh_object(f"Jericho_SpeakerModule_{side}", make_spk, mat_speaker, parent=root)
    
    # 2. Battery
    def make_bat(bm):
        build_planar_card(bm, 0.0192, 0.0075, 0.0022)
    create_mesh_object(f"Jericho_BatteryModule_{side}", make_bat, mat_battery, parent=root)
    
    # 3. Main SoC PCB
    def make_pcb(bm):
        build_planar_card(bm, 0.0128, 0.0120, 0.0012)
    create_mesh_object(f"Jericho_SoCPCB_{side}", make_pcb, mat_pcb, parent=root)
    
    # 4. Flex Cable
    def make_cable(bm):
        build_planar_card(bm, 0.0170, 0.0088, 0.0004)
    create_mesh_object(f"Jericho_FPC_Ribbon_{side}", make_cable, mat_cable, parent=root)

# ONLY ON RIGHT SIDE: Camera module & sensor pill
def make_cam_3d(bm):
    # Precision stepped cylinder barrel
    # Base collar
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.0050, radius2=0.0050, depth=0.0035)
    # Step collar
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.0042, radius2=0.0042, depth=0.0025, matrix=mathutils.Matrix.Translation((0, 0, 0.0028)))
    # Front rim
    bmesh.ops.create_cone(bm, cap_ends=False, segments=32, radius1=0.0038, radius2=0.0036, depth=0.0012, matrix=mathutils.Matrix.Translation((0, 0, 0.0044)))
cam_obj = create_mesh_object("Jericho_CameraModule_R", make_cam_3d, mat_cam_barrel, parent=root)
cam_obj.rotation_euler = (math.radians(90), 0, 0)

# Camera glass optic
def make_optic(bm):
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.0034)
optic_obj = create_mesh_object("Jericho_CameraOptics_R", make_optic, mat_cam_optic, parent=cam_obj)
optic_obj.location = mathutils.Vector((0, 0, 0.0044))
optic_obj.scale = mathutils.Vector((1.0, 1.0, 0.28))

# Sensor pill
def make_pill(bm):
    build_planar_card(bm, 0.0085, 0.0055, 0.0018)
pill_obj = create_mesh_object("Jericho_SensorPill_R", make_pill, mat_pill_tex, parent=root)
pill_obj.rotation_euler = (math.radians(90), 0, 0)

# Camera scale tuned for larger figure
cam = bpy.data.objects.get("Camera")
if cam:
    cam.location = mathutils.Vector((0.0, -0.46, 0.028))
    cam.data.lens = 68.0

print("SUCCESS: Realistic PBR components built with camera ONLY on right side!")
'''

res = execute_blender(blender_code)
print(res)

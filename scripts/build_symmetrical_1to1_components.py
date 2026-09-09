import bpy
import bmesh
import math
import mathutils

def get_or_create_material(name, base_color=(0.1, 0.1, 0.1, 1.0), metallic=0.0, roughness=0.5, alpha=1.0, render_method='DITHERED'):
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
    if 'Specular IOR Level' in node_bsdf.inputs:
        node_bsdf.inputs['Specular IOR Level'].default_value = 0.5
    
    mat.node_tree.links.new(node_bsdf.outputs['BSDF'], node_out.inputs['Surface'])
    
    if hasattr(mat, 'surface_render_method'):
        if alpha < 1.0:
            mat.surface_render_method = 'BLENDED'
        else:
            mat.surface_render_method = 'DITHERED'
    if alpha < 1.0:
        mat.blend_method = 'BLEND'
    return mat

def create_mesh_object(name, mesh_data_builder, material=None, parent=None):
    old_obj = bpy.data.objects.get(name)
    if old_obj:
        bpy.data.objects.remove(old_obj, do_unlink=True)
    old_mesh = bpy.data.meshes.get(name)
    if old_mesh:
        bpy.data.meshes.remove(old_mesh, do_unlink=True)
        
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    mesh_data_builder(bm)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if material:
        obj.data.materials.append(material)
    if parent:
        obj.parent = parent
    return obj

def build_all():
    root = bpy.data.objects.get("Jericho_Root")
    if not root:
        root = bpy.data.objects.new("Jericho_Root", None)
        bpy.context.collection.objects.link(root)
        
    root.rotation_euler = (0, 0, 0)
    root.location = (0, 0, 0)
    bpy.context.view_layer.update()

    # Materials
    mat_anodized = get_or_create_material("Mat_AnodizedCamera", (0.025, 0.025, 0.028, 1.0), metallic=0.85, roughness=0.22)
    mat_optics = get_or_create_material("Mat_CameraOptics", (0.04, 0.09, 0.26, 0.82), metallic=0.1, roughness=0.02, alpha=0.82)
    mat_brass = get_or_create_material("Mat_BrassBezel", (0.88, 0.74, 0.32, 1.0), metallic=0.96, roughness=0.16)
    mat_pill = get_or_create_material("Mat_SensorPill", (0.03, 0.03, 0.032, 1.0), metallic=0.15, roughness=0.32)
    mat_steel = get_or_create_material("Mat_SteelHinge", (0.84, 0.86, 0.88, 1.0), metallic=0.96, roughness=0.14)
    mat_speaker_body = get_or_create_material("Mat_SpeakerBody", (0.04, 0.04, 0.045, 1.0), metallic=0.25, roughness=0.28)
    mat_acoustic_grill = get_or_create_material("Mat_AcousticGrill", (0.78, 0.80, 0.83, 1.0), metallic=0.92, roughness=0.18)
    mat_battery = get_or_create_material("Mat_BatteryCell", (0.035, 0.035, 0.038, 1.0), metallic=0.28, roughness=0.36)
    mat_soc_board = get_or_create_material("Mat_SoCBoard", (0.015, 0.022, 0.018, 1.0), metallic=0.12, roughness=0.26)
    mat_soc_die = get_or_create_material("Mat_SoCSilicon", (0.07, 0.07, 0.08, 1.0), metallic=0.7, roughness=0.08)
    mat_gold = get_or_create_material("Mat_GoldPins", (1.0, 0.78, 0.22, 1.0), metallic=0.98, roughness=0.12)
    mat_smd_cap = get_or_create_material("Mat_SMDCap", (0.68, 0.58, 0.44, 1.0), metallic=0.05, roughness=0.32)
    mat_flex = get_or_create_material("Mat_FlexPolyimide", (0.58, 0.32, 0.10, 0.95), metallic=0.2, roughness=0.22, alpha=0.95)
    
    # Darker tinted lens material for high contrast on white background
    mat_lens_dark = get_or_create_material("Mat_ClearLens", (0.08, 0.10, 0.12, 1.0), metallic=0.05, roughness=0.04, alpha=0.35)
    mat_lens_bevel = get_or_create_material("Mat_FrostedLensBevel", (0.75, 0.78, 0.82, 0.55), metallic=0.0, roughness=0.22, alpha=0.55)

    # Assign darker lens material to both lenses
    for name in ["Lens_Meta_Right", "Lens_Meta_Left"]:
        o = bpy.data.objects.get(name)
        if o and o.data:
            o.data.materials.clear()
            o.data.materials.append(mat_lens_dark)

    for side in ["R", "L"]:
        sign = 1.0 if side == "R" else -1.0
        
        # 1. Lens Bevel
        def make_bevel(bm):
            bmesh.ops.create_circle(bm, cap_ends=False, radius=0.021, segments=32)
            r = bmesh.ops.extrude_edge_only(bm, edges=bm.edges)
            verts = [v for v in r['geom'] if isinstance(v, bmesh.types.BMVert)]
            for v in verts:
                v.co.x *= 1.06
                v.co.z *= 1.06
                v.co.y += 0.0008
            bmesh.ops.triangle_fill(bm, use_beauty=True)
        bevel_obj = create_mesh_object(f"Jericho_LensBevel_{side}", make_bevel, mat_lens_bevel, parent=root)

        # 2. Camera Module
        def make_cam(bm):
            bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.0042, radius2=0.0042, depth=0.0055)
            bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.0034, radius2=0.0034, depth=0.0025, matrix=mathutils.Matrix.Translation((0, 0, 0.0035)))
        cam_obj = create_mesh_object(f"Jericho_CameraModule_{side}", make_cam, mat_anodized, parent=root)
        cam_obj.rotation_euler = (math.radians(90), 0, 0)
        
        def make_optics(bm):
            bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=0.0028)
        optics_obj = create_mesh_object(f"Jericho_CameraOptics_{side}", make_optics, mat_optics, parent=cam_obj)
        optics_obj.location = mathutils.Vector((0, 0, 0.0042))
        optics_obj.scale = mathutils.Vector((1.0, 1.0, 0.35))
        
        def make_bezel(bm):
            bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=0.0036, radius2=0.0036, depth=0.0008)
        bezel_obj = create_mesh_object(f"Jericho_CameraBezel_{side}", make_bezel, mat_brass, parent=cam_obj)
        bezel_obj.location = mathutils.Vector((0, 0, 0.0044))

        # 3. Sensor Pill
        def make_pill(bm):
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.008, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0032, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0032, 4, (0,0,1)))
            bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.0006, radius2=0.0006, depth=0.0008, matrix=mathutils.Matrix.Translation((-0.0022, 0, 0.0016)))
            bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.0006, radius2=0.0006, depth=0.0008, matrix=mathutils.Matrix.Translation((0.0022, 0, 0.0016)))
        pill_obj = create_mesh_object(f"Jericho_SensorPill_{side}", make_pill, mat_pill, parent=root)
        pill_obj.rotation_euler = (math.radians(90), 0, 0)

        # 4. Hinge Tongue
        def make_hinge(bm):
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0024, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0075, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0038, 4, (0,0,1)))
            bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.0016, radius2=0.0016, depth=0.0042, matrix=mathutils.Matrix.Translation((0, -0.0028, 0)))
        create_mesh_object(f"Jericho_HingeTongue_{side}", make_hinge, mat_steel, parent=root)

        # 5. Speaker Module
        def make_speaker(bm):
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.010, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.008, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0042, 4, (0,0,1)))
        spk_obj = create_mesh_object(f"Jericho_SpeakerModule_{side}", make_speaker, mat_speaker_body, parent=root)
        
        def make_grill(bm):
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0084, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0064, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0006, 4, (0,0,1)))
        create_mesh_object(f"Jericho_SpeakerGrill_{side}", make_grill, mat_acoustic_grill, parent=spk_obj).location = mathutils.Vector((0, 0, 0.0022))

        # 6. Battery Module
        def make_bat(bm):
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0065, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0220, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0036, 4, (0,0,1)))
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0048, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0025, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0028, 4, (0,0,1)) @ mathutils.Matrix.Translation((0, 0.0120, 0)))
        create_mesh_object(f"Jericho_BatteryModule_{side}", make_bat, mat_battery, parent=root)

        # 7. SoC PCB
        def make_pcb(bm):
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0135, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0135, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0012, 4, (0,0,1)))
        pcb_obj = create_mesh_object(f"Jericho_SoCPCB_{side}", make_pcb, mat_soc_board, parent=root)
        
        def make_die(bm):
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0068, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0068, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0009, 4, (0,0,1)))
        create_mesh_object(f"Jericho_SoCDie_{side}", make_die, mat_soc_die, parent=pcb_obj).location = mathutils.Vector((-0.0015 * sign, 0.0005, 0.0009))

        def make_passives(bm):
            for x, y in [(-0.0048, -0.0042), (-0.0048, -0.0022), (-0.0048, -0.0002), 
                        (0.0042, -0.0042), (0.0042, -0.0022), (0.0042, 0.0002), (0.0042, 0.0022),
                        (-0.0022, -0.0048), (0.0008, -0.0048)]:
                bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0012, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0018, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0007, 4, (0,0,1)) @ mathutils.Matrix.Translation((x * sign, y, 0.0008)))
        create_mesh_object(f"Jericho_SMDPassives_{side}", make_passives, mat_smd_cap, parent=pcb_obj)

        def make_pins(bm):
            for y in [-0.005, -0.003, -0.001, 0.001, 0.003, 0.005]:
                bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0018, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0008, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0003, 4, (0,0,1)) @ mathutils.Matrix.Translation((0.0062 * sign, y, 0.0006)))
        create_mesh_object(f"Jericho_GoldPins_{side}", make_pins, mat_gold, parent=pcb_obj)

        # 8. FPC Ribbon Cable
        def make_cable(bm):
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0065, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0040, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.00025, 4, (0,0,1)) @ mathutils.Matrix.Translation((0.0032 * sign, 0, 0)))
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0040, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0065, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.00025, 4, (0,0,1)) @ mathutils.Matrix.Translation((0.0075 * sign, 0.0035, 0)))
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0075, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0045, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.00025, 4, (0,0,1)) @ mathutils.Matrix.Translation((0.0125 * sign, 0.0065, 0)))
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0022, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0055, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0012, 4, (0,0,1)) @ mathutils.Matrix.Translation((0.0165 * sign, 0.0065, 0.0005)))
        create_mesh_object(f"Jericho_FPC_Ribbon_{side}", make_cable, mat_flex, parent=root)

    # Make overall figure bigger by moving camera slightly closer & adjusting focal length
    cam = bpy.data.objects.get("Camera")
    if cam:
        cam.location = mathutils.Vector((0.0, -0.46, 0.028)) # closer from -0.55m to -0.46m (20% bigger!)
        cam.data.lens = 68.0

    print("Created symmetrical components (L + R) and scaled camera for larger figure successfully!")

build_all()

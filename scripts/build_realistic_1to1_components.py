import bpy
import bmesh
import math
import mathutils

def get_or_create_material(name, base_color=(0.1, 0.1, 0.1, 1.0), metallic=0.0, roughness=0.5, alpha=1.0, render_method='OPAQUE'):
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

def build_components():
    root = bpy.data.objects.get("Jericho_Root")
    if not root:
        root = bpy.data.objects.new("Jericho_Root", None)
        bpy.context.collection.objects.link(root)
        
    # Reset root transforms for accurate positioning
    root.rotation_euler = (0, 0, 0)
    root.location = (0, 0, 0)
    bpy.context.view_layer.update()

    # Materials
    mat_anodized = get_or_create_material("Mat_AnodizedCamera", (0.025, 0.025, 0.028, 1.0), metallic=0.85, roughness=0.22)
    mat_optics = get_or_create_material("Mat_CameraOptics", (0.04, 0.09, 0.26, 0.82), metallic=0.1, roughness=0.02, alpha=0.82, render_method='BLENDED')
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
    mat_flex = get_or_create_material("Mat_FlexPolyimide", (0.58, 0.32, 0.10, 0.95), metallic=0.2, roughness=0.22, alpha=0.95, render_method='BLENDED')
    mat_lens_bevel = get_or_create_material("Mat_FrostedLensBevel", (0.92, 0.94, 0.96, 0.45), metallic=0.0, roughness=0.22, alpha=0.45, render_method='BLENDED')

    # 1. Lens Rim Frosted Bevel (Contours along the right lens)
    def make_lens_bevel(bm):
        # A curved ring matching the eye frame perimeter
        bmesh.ops.create_circle(bm, cap_ends=False, radius=0.021, segments=32)
        # Extrude slightly outward and bevel
        r = bmesh.ops.extrude_edge_only(bm, edges=bm.edges)
        verts = [v for v in r['geom'] if isinstance(v, bmesh.types.BMVert)]
        for v in verts:
            v.co.x *= 1.06
            v.co.z *= 1.06
            v.co.y += 0.0008
        bmesh.ops.triangle_fill(bm, use_beauty=True)
    lens_bevel = create_mesh_object("Jericho_LensBevel", make_lens_bevel, mat_lens_bevel, parent=root)
    lens_bevel.location = mathutils.Vector((0.0315, -0.0485, 0.0008))
    lens_bevel.scale = mathutils.Vector((1.18, 1.0, 0.92))

    # 2. Camera Module (Stepped precision optical barrel with glass lens and brass bezel)
    def make_camera_module(bm):
        # Main barrel
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=24, radius1=0.0042, radius2=0.0042, depth=0.0055)
        # Step ring
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=24, radius1=0.0034, radius2=0.0034, depth=0.0025, matrix=mathutils.Matrix.Translation((0, 0, 0.0035)))
    cam_body = create_mesh_object("Jericho_CameraModule", make_camera_module, mat_anodized, parent=root)
    cam_body.rotation_euler = (math.radians(90), 0, 0)
    
    # Camera front optics
    def make_cam_lens(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=0.0028)
    cam_lens = create_mesh_object("Jericho_CameraOptics", make_cam_lens, mat_optics, parent=cam_body)
    cam_lens.location = mathutils.Vector((0, 0, 0.0042))
    cam_lens.scale = mathutils.Vector((1.0, 1.0, 0.35))
    
    # Camera brass bezel
    def make_cam_bezel(bm):
        bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=0.0036, radius2=0.0036, depth=0.0008)
    cam_bezel = create_mesh_object("Jericho_CameraBezel", make_cam_bezel, mat_brass, parent=cam_body)
    cam_bezel.location = mathutils.Vector((0, 0, 0.0044))

    # 3. Sensor / Microphone Pill (beside camera)
    def make_sensor_pill(bm):
        # Pill capsule
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.008, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0032, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0032, 4, (0,0,1)))
        # Micro mic ports
        bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.0006, radius2=0.0006, depth=0.0008, matrix=mathutils.Matrix.Translation((-0.0022, 0, 0.0016)))
        bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.0006, radius2=0.0006, depth=0.0008, matrix=mathutils.Matrix.Translation((0.0022, 0, 0.0016)))
    sensor_pill = create_mesh_object("Jericho_SensorPill", make_sensor_pill, mat_pill, parent=root)
    sensor_pill.rotation_euler = (math.radians(90), 0, 0)

    # 4. Stainless Steel Hinge Tongue (at the temple joint)
    def make_hinge_tongue(bm):
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0024, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0075, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0038, 4, (0,0,1)))
        # Hinge screw barrel
        bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.0016, radius2=0.0016, depth=0.0042, matrix=mathutils.Matrix.Translation((0, -0.0028, 0)))
    hinge_tongue = create_mesh_object("Jericho_HingeTongue", make_hinge_tongue, mat_steel, parent=root)

    # 5. Acoustic Speaker Module (rounded rectangle with perforated steel grill)
    def make_speaker_body(bm):
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.010, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.008, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0042, 4, (0,0,1)))
    speaker_body = create_mesh_object("Jericho_SpeakerModule", make_speaker_body, mat_speaker_body, parent=root)
    
    def make_speaker_grill(bm):
        # Metallic acoustic front grill
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0084, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0064, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0006, 4, (0,0,1)))
    speaker_grill = create_mesh_object("Jericho_SpeakerGrill", make_speaker_grill, mat_acoustic_grill, parent=speaker_body)
    speaker_grill.location = mathutils.Vector((0, 0, 0.0022))

    # 6. Battery Module (Sleek lithium cell with terminal clip)
    def make_battery(bm):
        # Main pack
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0065, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0220, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0036, 4, (0,0,1)))
        # Connector terminal
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0048, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0025, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0028, 4, (0,0,1)) @ mathutils.Matrix.Translation((0, 0.0120, 0)))
    battery_module = create_mesh_object("Jericho_BatteryModule", make_battery, mat_battery, parent=root)

    # 7. Main SoC PCB (Square BGA processor, SMDs, gold header pins)
    def make_soc_pcb(bm):
        # Board substrate
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0135, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0135, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0012, 4, (0,0,1)))
    soc_pcb = create_mesh_object("Jericho_SoCPCB", make_soc_pcb, mat_soc_board, parent=root)
    
    # Central SoC silicon chip
    def make_soc_die(bm):
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0068, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0068, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0009, 4, (0,0,1)))
    soc_die = create_mesh_object("Jericho_SoCDie", make_soc_die, mat_soc_die, parent=soc_pcb)
    soc_die.location = mathutils.Vector((-0.0015, 0.0005, 0.0009))

    # SMD capacitors & resistors
    def make_smd_passives(bm):
        for x, y in [(-0.0048, -0.0042), (-0.0048, -0.0022), (-0.0048, -0.0002), 
                    (0.0042, -0.0042), (0.0042, -0.0022), (0.0042, 0.0002), (0.0042, 0.0022),
                    (-0.0022, -0.0048), (0.0008, -0.0048)]:
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0012, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0018, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0007, 4, (0,0,1)) @ mathutils.Matrix.Translation((x, y, 0.0008)))
    smd_parts = create_mesh_object("Jericho_SMDPassives", make_smd_passives, mat_smd_cap, parent=soc_pcb)

    # Gold edge connector pins
    def make_gold_pins(bm):
        for y in [-0.005, -0.003, -0.001, 0.001, 0.003, 0.005]:
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0018, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0008, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0003, 4, (0,0,1)) @ mathutils.Matrix.Translation((0.0062, y, 0.0006)))
    gold_pins = create_mesh_object("Jericho_GoldPins", make_gold_pins, mat_gold, parent=soc_pcb)

    # 8. Flexible Printed Circuit (FPC) Ribbon Cable (Stepped polyimide with gold header)
    def make_fpc_cable(bm):
        # Stepped S-curve ribbon
        # Segment 1
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0065, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0040, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.00025, 4, (0,0,1)) @ mathutils.Matrix.Translation((0.0032, 0, 0)))
        # Step curve segment
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0040, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0065, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.00025, 4, (0,0,1)) @ mathutils.Matrix.Translation((0.0075, 0.0035, 0)))
        # Segment 2
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0075, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0045, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.00025, 4, (0,0,1)) @ mathutils.Matrix.Translation((0.0125, 0.0065, 0)))
        # Terminal gold connector header
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Scale(0.0022, 4, (1,0,0)) @ mathutils.Matrix.Scale(0.0055, 4, (0,1,0)) @ mathutils.Matrix.Scale(0.0012, 4, (0,0,1)) @ mathutils.Matrix.Translation((0.0165, 0.0065, 0.0005)))
    fpc_cable = create_mesh_object("Jericho_FPC_Ribbon", make_fpc_cable, mat_flex, parent=root)

    print("All 1-to-1 components created and styled successfully!")

build_components()

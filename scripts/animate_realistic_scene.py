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

anim_code = r'''
import bpy
import math
import mathutils

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 72

root = bpy.data.objects.get("Jericho_Root")

# Clear animation on all objects
for obj in bpy.data.objects:
    if obj.animation_data:
        obj.animation_data_clear()

temple_r = bpy.data.objects.get("Temple_Meta_Right")
temple_l = bpy.data.objects.get("Temple_Meta_Left")
lens_r = bpy.data.objects.get("Lens_Meta_Right")
lens_l = bpy.data.objects.get("Lens_Meta_Left")

def smoothstep(edge0, edge1, x):
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)

for f in range(1, 73):
    scene.frame_set(f)
    t_global = (f - 1) / 71.0

    # Continuous 3D Spatial Rotation across all 72 frames (2x frame rate):
    # Yaw: -48 deg (hero angle) sweeping smoothly to 0.0 deg (symmetrical front view)
    yaw_deg = -48.0 * (1.0 - t_global)
    if f <= 32:
        p_factor = math.sin((f - 1) / 31.0 * (math.pi / 2.0))
        pitch_deg = 12.0 + 3.0 * p_factor
    else:
        p_factor = (f - 32) / 40.0
        pitch_deg = 15.0 * (1.0 - p_factor) + 1.5 * p_factor

    roll_deg = -2.2 * math.cos(t_global * math.pi)
    center_x = -0.005 * math.sin(t_global * math.pi)
    center_y = 0.0
    center_z = -0.002 * math.sin(t_global * math.pi)

    root.rotation_euler = (math.radians(pitch_deg), math.radians(roll_deg), math.radians(yaw_deg))
    root.location = (center_x, center_y, center_z)
    root.keyframe_insert(data_path="rotation_euler", frame=f)
    root.keyframe_insert(data_path="location", frame=f)

    # Ultra-smooth explosion curve across 72 frames
    if f <= 10:
        expl = 0.0
    elif f <= 28:
        expl = smoothstep(10.0, 28.0, float(f))
    elif f <= 33:
        expl = 1.0
    elif f <= 45:
        expl = 1.0 - smoothstep(33.0, 45.0, float(f))
    else:
        expl = 0.0

    comp_scale = smoothstep(0.08, 0.40, expl)

    # Temples: BOTH temples slide back during breakdown!
    if temple_r:
        temple_r.location = mathutils.Vector((0.15 * expl, 0.72 * expl, 0.0))
        temple_r.keyframe_insert(data_path="location", frame=f)
    if temple_l:
        temple_l.location = mathutils.Vector((-1.5 * expl, 0.9 * expl, 0.3 * expl))
        temple_l.keyframe_insert(data_path="location", frame=f)

    # Lenses: Both pop forward, left comes out a bit
    if lens_r:
        lens_r.location = mathutils.Vector((0.0, -0.75 * expl, 0.12 * expl))
        lens_r.keyframe_insert(data_path="location", frame=f)
    if lens_l:
        lens_l.location = mathutils.Vector((0.0, -0.38 * expl, 0.06 * expl))
        lens_l.keyframe_insert(data_path="location", frame=f)

    # CAMERA MODULE: COMES OUT FROM TOP RIGHT CORNER OF GLASSES FRAME
    cam = bpy.data.objects.get("Jericho_CameraModule_R")
    if cam:
        c_docked = mathutils.Vector((0.068, -0.041, 0.016))
        c_expl = mathutils.Vector((0.071, -0.066, 0.017))
        cam.location = c_docked.lerp(c_expl, expl)
        cam.scale = mathutils.Vector((1, 1, 1)) * comp_scale
        cam.rotation_euler = (math.radians(85 - 5 * expl), math.radians(-6 * expl), 0)
        cam.keyframe_insert(data_path="location", frame=f)
        cam.keyframe_insert(data_path="scale", frame=f)
        cam.keyframe_insert(data_path="rotation_euler", frame=f)

    pill = bpy.data.objects.get("Jericho_SensorPill_R")
    if pill:
        p_docked = mathutils.Vector((0.068, -0.041, 0.016))
        p_expl = mathutils.Vector((0.058, -0.058, 0.020))
        pill.location = p_docked.lerp(p_expl, expl)
        pill.scale = mathutils.Vector((1, 1, 1)) * comp_scale
        pill.rotation_euler = (math.radians(85 - 5 * expl), math.radians(-6 * expl), 0)
        pill.keyframe_insert(data_path="location", frame=f)
        pill.keyframe_insert(data_path="scale", frame=f)
        pill.keyframe_insert(data_path="rotation_euler", frame=f)

    dot = bpy.data.objects.get("Jericho_SensorDot_R")
    if dot:
        d_docked = mathutils.Vector((0.068, -0.041, 0.016))
        d_expl = mathutils.Vector((0.074, -0.056, 0.013))
        dot.location = d_docked.lerp(d_expl, expl)
        dot.scale = mathutils.Vector((1, 1, 1)) * comp_scale
        dot.rotation_euler = (math.radians(90), 0, 0)
        dot.keyframe_insert(data_path="location", frame=f)
        dot.keyframe_insert(data_path="scale", frame=f)

    # RIGHT TEMPLE COMPONENTS (Speaker, Battery, PCB, Cable)
    rot_card_r = (math.radians(84 - 8 * expl), math.radians(-14 * expl), math.radians(6 * expl))

    # Right Speaker
    spk_r = bpy.data.objects.get("Jericho_SpeakerModule_R")
    if spk_r:
        s_docked = mathutils.Vector((0.058, -0.012, 0.001))
        s_expl = mathutils.Vector((0.048, -0.015, -0.014))
        spk_r.location = s_docked.lerp(s_expl, expl)
        spk_r.scale = mathutils.Vector((1, 1, 1)) * comp_scale
        spk_r.rotation_euler = rot_card_r
        spk_r.keyframe_insert(data_path="location", frame=f)
        spk_r.keyframe_insert(data_path="scale", frame=f)
        spk_r.keyframe_insert(data_path="rotation_euler", frame=f)

    # Right Battery
    bat_r = bpy.data.objects.get("Jericho_BatteryModule_R")
    if bat_r:
        b_docked = mathutils.Vector((0.064, 0.008, 0.001))
        b_expl = mathutils.Vector((0.066, -0.002, -0.014))
        bat_r.location = b_docked.lerp(b_expl, expl)
        bat_r.scale = mathutils.Vector((1, 1, 1)) * comp_scale
        bat_r.rotation_euler = rot_card_r
        bat_r.keyframe_insert(data_path="location", frame=f)
        bat_r.keyframe_insert(data_path="scale", frame=f)
        bat_r.keyframe_insert(data_path="rotation_euler", frame=f)

    # Right SoC PCB
    pcb_r = bpy.data.objects.get("Jericho_SoCPCB_R")
    if pcb_r:
        p_docked = mathutils.Vector((0.068, 0.026, 0.001))
        p_expl = mathutils.Vector((0.084, 0.010, -0.014))
        pcb_r.location = p_docked.lerp(p_expl, expl)
        pcb_r.scale = mathutils.Vector((1, 1, 1)) * comp_scale
        pcb_r.rotation_euler = rot_card_r
        pcb_r.keyframe_insert(data_path="location", frame=f)
        pcb_r.keyframe_insert(data_path="scale", frame=f)
        pcb_r.keyframe_insert(data_path="rotation_euler", frame=f)

    # Right Flex Cable
    cab_r = bpy.data.objects.get("Jericho_FPC_Ribbon_R")
    if cab_r:
        c_docked = mathutils.Vector((0.070, 0.042, 0.001))
        c_expl = mathutils.Vector((0.102, 0.022, -0.014))
        cab_r.location = c_docked.lerp(c_expl, expl)
        cab_r.scale = mathutils.Vector((1, 1, 1)) * comp_scale
        cab_r.rotation_euler = rot_card_r
        cab_r.keyframe_insert(data_path="location", frame=f)
        cab_r.keyframe_insert(data_path="scale", frame=f)
        cab_r.keyframe_insert(data_path="rotation_euler", frame=f)

    # LEFT TEMPLE COMPONENTS (Battery, PCB, Cable ONLY - NO Speaker, NO Camera!)
    rot_card_l = (math.radians(84 - 8 * expl), math.radians(14 * expl), math.radians(-6 * expl))

    # Left Battery
    bat_l = bpy.data.objects.get("Jericho_BatteryModule_L")
    if bat_l:
        b_docked_l = mathutils.Vector((-0.064, 0.008, 0.001))
        b_expl_l = mathutils.Vector((-0.088, -0.018, -0.008))
        bat_l.location = b_docked_l.lerp(b_expl_l, expl)
        bat_l.scale = mathutils.Vector((1, 1, 1)) * comp_scale
        bat_l.rotation_euler = rot_card_l
        bat_l.keyframe_insert(data_path="location", frame=f)
        bat_l.keyframe_insert(data_path="scale", frame=f)
        bat_l.keyframe_insert(data_path="rotation_euler", frame=f)

    # Left SoC PCB
    pcb_l = bpy.data.objects.get("Jericho_SoCPCB_L")
    if pcb_l:
        p_docked_l = mathutils.Vector((-0.068, 0.026, 0.001))
        p_expl_l = mathutils.Vector((-0.122, -0.008, -0.008))
        pcb_l.location = p_docked_l.lerp(p_expl_l, expl)
        pcb_l.scale = mathutils.Vector((1, 1, 1)) * comp_scale
        pcb_l.rotation_euler = rot_card_l
        pcb_l.keyframe_insert(data_path="location", frame=f)
        pcb_l.keyframe_insert(data_path="scale", frame=f)
        pcb_l.keyframe_insert(data_path="rotation_euler", frame=f)

    # Left Flex Cable
    cab_l = bpy.data.objects.get("Jericho_FPC_Ribbon_L")
    if cab_l:
        c_docked_l = mathutils.Vector((-0.070, 0.042, 0.001))
        c_expl_l = mathutils.Vector((-0.156, 0.002, -0.008))
        cab_l.location = c_docked_l.lerp(c_expl_l, expl)
        cab_l.scale = mathutils.Vector((1, 1, 1)) * comp_scale
        cab_l.rotation_euler = rot_card_l
        cab_l.keyframe_insert(data_path="location", frame=f)
        cab_l.keyframe_insert(data_path="scale", frame=f)
        cab_l.keyframe_insert(data_path="rotation_euler", frame=f)

print("SUCCESS: Animation updated with refined left-side alignment!")

# Reload textures to ensure updated saturation/contrast are rendered
for img in bpy.data.images:
    if "diffuse" in img.name:
        img.reload()

# Ensure Standard view transform for punchy, vibrant color rendering
scene.view_settings.view_transform = "Standard"

# Render test frame 30 (peak breakdown at 72-frame scale)
scene.frame_set(30)
scene.render.filepath = r"c:\Users\srtha\Downloads\JerichoWebsite\website\assets\test_vibrant_f13.png"
bpy.ops.render.render(write_still=True)
print("Rendered test_vibrant_f13.png (at frame 30)")
'''

res = execute_blender(anim_code)
print(res)

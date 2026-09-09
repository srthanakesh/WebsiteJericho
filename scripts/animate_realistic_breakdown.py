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
import os

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 36

root = bpy.data.objects.get("Jericho_Root")
if not root:
    print("Jericho_Root not found!")

# Clear old animation data on all objects
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

for f in range(1, 37):
    scene.frame_set(f)
    t_global = (f - 1) / 35.0

    # 3D Spatial Rotation across 36 frames:
    yaw_deg = -48.0 * (1.0 - t_global)
    if f <= 16:
        p_factor = math.sin((f - 1) / 15.0 * (math.pi / 2.0))
        pitch_deg = 12.5 + 3.3 * p_factor
    else:
        p_factor = (f - 16) / 20.0
        pitch_deg = 15.8 * (1.0 - p_factor) + 1.5 * p_factor

    roll_deg = -2.5 * math.cos(t_global * math.pi)
    center_x = -0.005 * math.sin(t_global * math.pi)
    center_y = 0.0
    center_z = -0.002 * math.sin(t_global * math.pi)

    root.rotation_euler = (math.radians(pitch_deg), math.radians(roll_deg), math.radians(yaw_deg))
    root.location = (center_x, center_y, center_z)
    root.keyframe_insert(data_path="rotation_euler", frame=f)
    root.keyframe_insert(data_path="location", frame=f)

    # Explosion curve
    if f <= 5:
        expl = 0.0
    elif f <= 15:
        expl = smoothstep(5.0, 15.0, float(f))
    elif f <= 18:
        expl = 1.0
    elif f <= 25:
        expl = 1.0 - smoothstep(18.0, 25.0, float(f))
    else:
        expl = 0.0

    comp_scale = smoothstep(0.0, 0.35, expl)

    # Temples: Right slides back, Left slides back symmetrically
    if temple_r:
        temple_r.location = mathutils.Vector((0.32 * expl, 1.25 * expl, 0.0))
        temple_r.keyframe_insert(data_path="location", frame=f)
    if temple_l:
        temple_l.location = mathutils.Vector((-0.32 * expl, 1.25 * expl, 0.0))
        temple_l.keyframe_insert(data_path="location", frame=f)

    # Lenses: float forward gently
    if lens_r:
        lens_r.location = mathutils.Vector((0.0, -1.05 * expl, 0.18 * expl))
        lens_r.keyframe_insert(data_path="location", frame=f)
    if lens_l:
        lens_l.location = mathutils.Vector((0.0, -1.05 * expl, 0.18 * expl))
        lens_l.keyframe_insert(data_path="location", frame=f)

    # CAMERA MODULE: ONLY ON RIGHT SIDE
    cam = bpy.data.objects.get("Jericho_CameraModule_R")
    if cam:
        c_docked = mathutils.Vector((0.052, -0.046, 0.004))
        c_expl = mathutils.Vector((0.022, -0.075, 0.006))
        cam.location = c_docked.lerp(c_expl, expl)
        cam.scale = mathutils.Vector((1, 1, 1)) * comp_scale
        cam.rotation_euler = (math.radians(90 - 10 * expl), math.radians(12 * expl), 0)
        cam.keyframe_insert(data_path="location", frame=f)
        cam.keyframe_insert(data_path="scale", frame=f)
        cam.keyframe_insert(data_path="rotation_euler", frame=f)

    # SENSOR PILL: ONLY ON RIGHT SIDE
    pill = bpy.data.objects.get("Jericho_SensorPill_R")
    if pill:
        p_docked = mathutils.Vector((0.040, -0.046, 0.005))
        p_expl = mathutils.Vector((0.034, -0.072, 0.005))
        pill.location = p_docked.lerp(p_expl, expl)
        pill.scale = mathutils.Vector((1, 1, 1)) * comp_scale
        pill.rotation_euler = (math.radians(90 - 10 * expl), math.radians(10 * expl), 0)
        pill.keyframe_insert(data_path="location", frame=f)
        pill.keyframe_insert(data_path="scale", frame=f)
        pill.keyframe_insert(data_path="rotation_euler", frame=f)

    # Symmetrical Temple Components (Speaker, Battery, SoC PCB, Flex Cable)
    for side in ["R", "L"]:
        sign = 1.0 if side == "R" else -1.0

        # Card tilt: face the viewer/camera with slight angle
        rot_card = (math.radians(82 - 8 * expl), math.radians(-12 * expl * sign), math.radians(8 * expl * sign))

        # 1. Speaker
        spk = bpy.data.objects.get(f"Jericho_SpeakerModule_{side}")
        if spk:
            s_docked = mathutils.Vector((0.056 * sign, -0.012, 0.001))
            s_expl = mathutils.Vector((0.050 * sign, -0.002, -0.016))
            spk.location = s_docked.lerp(s_expl, expl)
            spk.scale = mathutils.Vector((1, 1, 1)) * comp_scale
            spk.rotation_euler = rot_card
            spk.keyframe_insert(data_path="location", frame=f)
            spk.keyframe_insert(data_path="scale", frame=f)
            spk.keyframe_insert(data_path="rotation_euler", frame=f)

        # 2. Battery
        bat = bpy.data.objects.get(f"Jericho_BatteryModule_{side}")
        if bat:
            b_docked = mathutils.Vector((0.062 * sign, 0.012, 0.002))
            b_expl = mathutils.Vector((0.072 * sign, 0.016, -0.016))
            bat.location = b_docked.lerp(b_expl, expl)
            bat.scale = mathutils.Vector((1, 1, 1)) * comp_scale
            bat.rotation_euler = rot_card
            bat.keyframe_insert(data_path="location", frame=f)
            bat.keyframe_insert(data_path="scale", frame=f)
            bat.keyframe_insert(data_path="rotation_euler", frame=f)

        # 3. Main SoC PCB
        pcb = bpy.data.objects.get(f"Jericho_SoCPCB_{side}")
        if pcb:
            p_docked = mathutils.Vector((0.066 * sign, 0.032, 0.002))
            p_expl = mathutils.Vector((0.092 * sign, 0.032, -0.016))
            pcb.location = p_docked.lerp(p_expl, expl)
            pcb.scale = mathutils.Vector((1, 1, 1)) * comp_scale
            pcb.rotation_euler = rot_card
            pcb.keyframe_insert(data_path="location", frame=f)
            pcb.keyframe_insert(data_path="scale", frame=f)
            pcb.keyframe_insert(data_path="rotation_euler", frame=f)

        # 4. Flex Cable
        cab = bpy.data.objects.get(f"Jericho_FPC_Ribbon_{side}")
        if cab:
            c_docked = mathutils.Vector((0.068 * sign, 0.048, 0.002))
            c_expl = mathutils.Vector((0.110 * sign, 0.046, -0.016))
            cab.location = c_docked.lerp(c_expl, expl)
            cab.scale = mathutils.Vector((1, 1, 1)) * comp_scale
            cab.rotation_euler = rot_card
            cab.keyframe_insert(data_path="location", frame=f)
            cab.keyframe_insert(data_path="scale", frame=f)
            cab.keyframe_insert(data_path="rotation_euler", frame=f)

print("SUCCESS: Realistic breakdown animated across all 36 frames!")

# Test render frame 13 to verify
scene.frame_set(13)
scene.render.filepath = r"c:\Users\srtha\Downloads\JerichoWebsite\website\assets\test_realistic_f13.png"
bpy.ops.render.render(write_still=True)
print("Rendered test frame 13 to website/assets/test_realistic_f13.png")
'''

res = execute_blender(anim_code)
print(res)

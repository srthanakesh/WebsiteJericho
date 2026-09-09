import socket
import json
import os
import sys

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
import math
import os

# 1. Clear existing animation data on all objects
for obj in bpy.data.objects:
    if obj.animation_data:
        obj.animation_data_clear()

# 2. Material setup
def get_or_create_mat(name):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    return mat

# Polished acetate material
mat_frame = get_or_create_mat('Mat_GlossyBlackAcetate')
bsdf = mat_frame.node_tree.nodes.get('Principled BSDF')
if bsdf:
    bsdf.inputs['Base Color'].default_value = (0.012, 0.012, 0.015, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.12
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.85
    elif 'Specular' in bsdf.inputs:
        bsdf.inputs['Specular'].default_value = 0.85

# Assign glossy acetate to frame and temple parts
for name in ['Object_26', 'Object_28', 'Object_30', 'Object_32', 'Object_34', 'Object_36', 'Temple_Meta_Right', 'Temple_Meta_Left']:
    o = bpy.data.objects.get(name)
    if o and o.type == 'MESH':
        if not o.data.materials:
            o.data.materials.append(mat_frame)
        else:
            o.data.materials[0] = mat_frame

# Clear optical lenses
mat_lens = get_or_create_mat('Mat_ClearLens')
bsdf_l = mat_lens.node_tree.nodes.get('Principled BSDF')
if bsdf_l:
    bsdf_l.inputs['Base Color'].default_value = (0.95, 0.98, 1.0, 1.0)
    bsdf_l.inputs['Roughness'].default_value = 0.02
    if 'Transmission Weight' in bsdf_l.inputs:
        bsdf_l.inputs['Transmission Weight'].default_value = 0.95
    elif 'Transmission' in bsdf_l.inputs:
        bsdf_l.inputs['Transmission'].default_value = 0.95
    bsdf_l.inputs['Alpha'].default_value = 0.18

for name in ['Lens_Meta_Left', 'Lens_Meta_Right']:
    o = bpy.data.objects.get(name)
    if o and o.type == 'MESH':
        if not o.data.materials:
            o.data.materials.append(mat_lens)
        else:
            o.data.materials[0] = mat_lens

# Optical Waveguide Combiner
mat_wg = get_or_create_mat('Mat_Waveguide')
bsdf_w = mat_wg.node_tree.nodes.get('Principled BSDF')
if bsdf_w:
    bsdf_w.inputs['Base Color'].default_value = (0.15, 0.85, 0.95, 1.0)
    bsdf_w.inputs['Roughness'].default_value = 0.02
    if 'Transmission Weight' in bsdf_w.inputs:
        bsdf_w.inputs['Transmission Weight'].default_value = 0.92
    elif 'Transmission' in bsdf_w.inputs:
        bsdf_w.inputs['Transmission'].default_value = 0.92
    bsdf_w.inputs['Alpha'].default_value = 0.28
    bsdf_w.inputs['Emission Color'].default_value = (0.0, 0.8, 1.0, 1.0)
    bsdf_w.inputs['Emission Strength'].default_value = 0.35

wg = bpy.data.objects.get('Waveguide_Display')
if wg:
    if not wg.data.materials:
        wg.data.materials.append(mat_wg)
    else:
        wg.data.materials[0] = mat_wg

# Hide duplicate/unneeded objects
for name in ['Object_24', 'Front_Frame', 'Temple_Left', 'Temple_Right', 'Lens_Left', 'Lens_Right']:
    o = bpy.data.objects.get(name)
    if o:
        o.hide_render = True

# 3. Setup Objects and Parenting
root = bpy.data.objects.get('Jericho_Root')
cam = bpy.data.objects.get('Camera')
cam.location = (0.0, -0.55, 0.035)
cam.rotation_euler = (math.radians(86), 0.0, 0.0)

# Lights
key = bpy.data.objects.get('Key_Light')
if key:
    key.location = (-0.30, -0.45, 0.40)
    key.data.energy = 48.0
rim = bpy.data.objects.get('Rim_Light')
if rim:
    rim.location = (0.35, 0.25, 0.30)
    rim.data.energy = 36.0
fill = bpy.data.objects.get('Fill_Light')
if fill:
    fill.location = (0.15, -0.50, -0.15)
    fill.data.energy = 16.0

# 4. Trajectory Coordinates:
trajectories = {
    'Model_Camera': {
        'rest_pos': (0.055, -0.055, 0.012),
        'exp_pos': (0.055, -0.092, 0.018),
        'scale': (0.016, 0.016, 0.016),
        'rot': (math.radians(90), 0.0, math.radians(180)),
        'hide_rest': True
    },
    'Waveguide_Display': {
        'rest_pos': (0.024, -0.055, 0.006),
        'exp_pos': (0.026, -0.088, 0.006),
        'scale': (0.026, 0.0012, 0.020),
        'rot': (math.radians(12), 0.0, math.radians(-10)),
        'hide_rest': True
    },
    'Real_Speaker_Right': {
        'rest_pos': (0.063, -0.005, 0.006),
        'exp_pos': (0.066, -0.012, -0.015),
        'scale': (2.2, 2.2, 2.2),
        'rot': (math.radians(12), 0.0, math.radians(-15)),
        'hide_rest': True
    },
    'Real_Battery_Right': {
        'rest_pos': (0.063, 0.022, 0.006),
        'exp_pos': (0.073, 0.024, -0.015),
        'scale': (2.0, 2.0, 2.0),
        'rot': (math.radians(12), 0.0, math.radians(-15)),
        'hide_rest': True
    },
    'Model_PCB': {
        'rest_pos': (0.063, 0.055, 0.006),
        'exp_pos': (0.080, 0.062, -0.015),
        'scale': (0.009, 0.009, 0.009),
        'rot': (math.radians(102), 0.0, math.radians(165)),
        'hide_rest': True
    },
    'Temple_Meta_Right': {
        'rest_pos': (0.0, 0.0, 0.0),
        'exp_pos': (0.008, 0.018, 0.002),
        'scale': (1.0, 1.0, 1.0),
        'rot': (0.0, 0.0, 0.0),
        'hide_rest': False
    },
    'Temple_Meta_Left': {
        'rest_pos': (0.0, 0.0, 0.0),
        'exp_pos': (-0.008, 0.018, 0.002),
        'scale': (1.0, 1.0, 1.0),
        'rot': (0.0, 0.0, 0.0),
        'hide_rest': False
    },
    'Real_Speaker_Left': {
        'rest_pos': (-0.063, -0.005, 0.006),
        'exp_pos': (-0.066, -0.012, -0.015),
        'scale': (2.2, 2.2, 2.2),
        'rot': (math.radians(12), 0.0, math.radians(15)),
        'hide_rest': True
    },
    'Real_Battery_Left': {
        'rest_pos': (-0.063, 0.022, 0.006),
        'exp_pos': (-0.073, 0.024, -0.015),
        'scale': (2.0, 2.0, 2.0),
        'rot': (math.radians(12), 0.0, math.radians(15)),
        'hide_rest': True
    }
}

def lerp(a, b, t):
    return a + (b - a) * t

def ease_io(t):
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2

for f in range(1, 37):
    # Root rotation
    if f <= 26:
        yaw = -46.0
        pitch = 12.0
    else:
        prog = ease_io((f - 26) / 10.0)
        yaw = lerp(-46.0, 0.0, prog)
        pitch = lerp(12.0, 0.0, prog)
    
    root.rotation_euler = (math.radians(pitch), 0.0, math.radians(yaw))
    root.keyframe_insert(data_path='rotation_euler', frame=f)

    # Component breakdown explosion & reassembly progress:
    if f <= 6:
        t_exp = 0.0
    elif f <= 13:
        t_exp = ease_io((f - 6) / 7.0)
    elif f <= 18:
        t_exp = 1.0
    elif f <= 25:
        t_exp = 1.0 - ease_io((f - 18) / 7.0)
    else:
        t_exp = 0.0

    # Apply to all components
    for name, data in trajectories.items():
        o = bpy.data.objects.get(name)
        if not o:
            continue
        
        rx, ry, rz = data['rest_pos']
        ex, ey, ez = data['exp_pos']
        cur_pos = (lerp(rx, ex, t_exp), lerp(ry, ey, t_exp), lerp(rz, ez, t_exp))
        
        o.location = cur_pos
        o.scale = data['scale']
        o.rotation_euler = data['rot']
        
        # Hide internal components when fully docked (t_exp == 0) if hide_rest is True
        if data.get('hide_rest', False):
            is_hidden = (t_exp <= 0.001)
            o.hide_render = is_hidden
            o.keyframe_insert(data_path='hide_render', frame=f)
            for c in o.children:
                c.hide_render = is_hidden
                c.keyframe_insert(data_path='hide_render', frame=f)
        else:
            o.hide_render = False
            o.keyframe_insert(data_path='hide_render', frame=f)

        o.keyframe_insert(data_path='location', frame=f)
        o.keyframe_insert(data_path='scale', frame=f)
        o.keyframe_insert(data_path='rotation_euler', frame=f)

print('Keyframes successfully inserted for all 36 frames!')
'''

print('Sending setup to Blender...')
res = execute_blender(blender_code)
print('Blender response:', res)

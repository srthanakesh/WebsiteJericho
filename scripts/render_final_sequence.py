import socket
import json
import os
import sys

def execute_blender(code):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(120.0)
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

render_code = r'''
import bpy
import math
import os

out_dir = r"c:\Users\srtha\Downloads\JerichoWebsite\website\assets\render3d"
os.makedirs(out_dir, exist_ok=True)

scene = bpy.context.scene
scene.render.resolution_x = 960
scene.render.resolution_y = 640
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.eevee.use_raytracing = False
scene.eevee.taa_render_samples = 64

print("Rendering complete 72-frame sequence (2x frame rate)...")
for f in range(1, 73):
    scene.frame_set(f)
    frame_path = os.path.join(out_dir, f"frame_{f:02d}.png")
    scene.render.filepath = frame_path
    bpy.ops.render.render(write_still=True)
    if f % 8 == 0 or f == 1:
        print(f"Rendered frame {f:02d}/72 -> {frame_path}")

print("SUCCESS: All 72 frames rendered successfully!")
'''

print("Starting render across all 36 frames...")
res = execute_blender(render_code)
print("Render response:", res)

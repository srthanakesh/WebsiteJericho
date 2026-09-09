import bpy
import math
import mathutils

def run():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 36

    root = bpy.data.objects.get("Jericho_Root")
    if not root:
        print("Jericho_Root not found!")
        return

    # Clear old animation data on all objects
    for obj in bpy.data.objects:
        if obj.animation_data:
            obj.animation_data_clear()

    # Objects to animate
    temple_r = bpy.data.objects.get("Temple_Meta_Right")
    temple_l = bpy.data.objects.get("Temple_Meta_Left")
    lens_r = bpy.data.objects.get("Lens_Meta_Right")
    lens_l = bpy.data.objects.get("Lens_Meta_Left")

    # Helper ease function (smooth hermite)
    def smoothstep(edge0, edge1, x):
        t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
        return t * t * (3.0 - 2.0 * t)

    for f in range(1, 37):
        scene.frame_set(f)
        t_global = (f - 1) / 35.0  # 0.0 to 1.0

        # Continuous 3D Spatial Rotation across ALL 36 frames:
        # Yaw smoothly sweeps from -48.0 deg to 0.0 deg
        yaw_deg = -48.0 * (1.0 - t_global)
        
        # Pitch: starts at 12.5 deg, rises to 15.8 deg during breakdown, settles to 1.5 deg
        if f <= 16:
            p_factor = math.sin((f - 1) / 15.0 * (math.pi / 2.0))
            pitch_deg = 12.5 + 3.3 * p_factor
        else:
            p_factor = (f - 16) / 20.0
            pitch_deg = 15.8 * (1.0 - p_factor) + 1.5 * p_factor

        # Roll: subtle dynamic tilt (-2.5 deg to +0.8 deg to 0.0 deg)
        roll_deg = -2.5 * math.cos(t_global * math.pi)

        # Center translation: slight compensation
        center_x = -0.005 * math.sin(t_global * math.pi)
        center_y = 0.0
        center_z = -0.002 * math.sin(t_global * math.pi)

        root.rotation_euler = (math.radians(pitch_deg), math.radians(roll_deg), math.radians(yaw_deg))
        root.location = (center_x, center_y, center_z)
        root.keyframe_insert(data_path="rotation_euler", frame=f)
        root.keyframe_insert(data_path="location", frame=f)

        # Explosion factor E (0.0 = assembled, 1.0 = peak breakdown)
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

        # Temples: Right slides along +X, Left slides symmetrically along -X
        if temple_r:
            temple_r.location = mathutils.Vector((0.32 * expl, 1.25 * expl, 0.0))
            temple_r.keyframe_insert(data_path="location", frame=f)
        if temple_l:
            temple_l.location = mathutils.Vector((-0.32 * expl, 1.25 * expl, 0.0))
            temple_l.keyframe_insert(data_path="location", frame=f)

        # Lenses: both float forward out of frame rim
        if lens_r:
            lens_r.location = mathutils.Vector((0.0, -1.1 * expl, 0.22 * expl))
            lens_r.keyframe_insert(data_path="location", frame=f)
        if lens_l:
            lens_l.location = mathutils.Vector((0.0, -1.1 * expl, 0.22 * expl))
            lens_l.keyframe_insert(data_path="location", frame=f)

        # Animate Symmetrical Components for both sides
        for side in ["R", "L"]:
            sign = 1.0 if side == "R" else -1.0

            # Lens Bevel
            bevel = bpy.data.objects.get(f"Jericho_LensBevel_{side}")
            if bevel:
                b_docked = mathutils.Vector((0.0315 * sign, -0.0485, 0.0008))
                b_expl = mathutils.Vector((0.0315 * sign, -0.0935, 0.0128))
                bevel.location = b_docked.lerp(b_expl, expl)
                bevel.scale = mathutils.Vector((1.18, 1.0, 0.92)) * comp_scale
                bevel.keyframe_insert(data_path="location", frame=f)
                bevel.keyframe_insert(data_path="scale", frame=f)

            # Camera Module
            cam = bpy.data.objects.get(f"Jericho_CameraModule_{side}")
            if cam:
                c_docked = mathutils.Vector((0.052 * sign, -0.046, 0.004))
                c_expl = mathutils.Vector((0.018 * sign, -0.075, 0.006))
                cam.location = c_docked.lerp(c_expl, expl)
                cam.scale = mathutils.Vector((1, 1, 1)) * comp_scale
                cam.rotation_euler = (math.radians(90 - 15 * expl), math.radians(20 * expl * sign), 0)
                cam.keyframe_insert(data_path="location", frame=f)
                cam.keyframe_insert(data_path="scale", frame=f)
                cam.keyframe_insert(data_path="rotation_euler", frame=f)

            # Sensor Pill
            pill = bpy.data.objects.get(f"Jericho_SensorPill_{side}")
            if pill:
                p_docked = mathutils.Vector((0.038 * sign, -0.046, 0.005))
                p_expl = mathutils.Vector((0.032 * sign, -0.070, 0.004))
                pill.location = p_docked.lerp(p_expl, expl)
                pill.scale = mathutils.Vector((1, 1, 1)) * comp_scale
                pill.rotation_euler = (math.radians(90 - 10 * expl), math.radians(15 * expl * sign), 0)
                pill.keyframe_insert(data_path="location", frame=f)
                pill.keyframe_insert(data_path="scale", frame=f)
                pill.keyframe_insert(data_path="rotation_euler", frame=f)

            # Hinge Tongue
            hinge = bpy.data.objects.get(f"Jericho_HingeTongue_{side}")
            if hinge:
                h_docked = mathutils.Vector((0.058 * sign, -0.035, 0.002))
                h_expl = h_docked + mathutils.Vector((0.010 * sign, 0.035, 0.002))
                hinge.location = h_docked.lerp(h_expl, expl)
                hinge.scale = mathutils.Vector((1, 1, 1)) * comp_scale
                hinge.keyframe_insert(data_path="location", frame=f)
                hinge.keyframe_insert(data_path="scale", frame=f)

            # Speaker Module
            speaker = bpy.data.objects.get(f"Jericho_SpeakerModule_{side}")
            if speaker:
                s_docked = mathutils.Vector((0.056 * sign, -0.010, 0.001))
                s_expl = mathutils.Vector((0.046 * sign, -0.006, -0.018))
                speaker.location = s_docked.lerp(s_expl, expl)
                speaker.scale = mathutils.Vector((1, 1, 1)) * comp_scale
                speaker.rotation_euler = (math.radians(25 * expl), math.radians(-10 * expl * sign), math.radians(15 * expl * sign))
                speaker.keyframe_insert(data_path="location", frame=f)
                speaker.keyframe_insert(data_path="scale", frame=f)
                speaker.keyframe_insert(data_path="rotation_euler", frame=f)

            # Battery Module
            bat = bpy.data.objects.get(f"Jericho_BatteryModule_{side}")
            if bat:
                b_docked = mathutils.Vector((0.058 * sign, 0.015, 0.001))
                b_expl = mathutils.Vector((0.058 * sign, 0.020, -0.018))
                bat.location = b_docked.lerp(b_expl, expl)
                bat.scale = mathutils.Vector((1, 1, 1)) * comp_scale
                bat.rotation_euler = (math.radians(10 * expl), 0, math.radians(-8 * expl * sign))
                bat.keyframe_insert(data_path="location", frame=f)
                bat.keyframe_insert(data_path="scale", frame=f)
                bat.keyframe_insert(data_path="rotation_euler", frame=f)

            # SoC PCB
            pcb = bpy.data.objects.get(f"Jericho_SoCPCB_{side}")
            if pcb:
                pcb_docked = mathutils.Vector((0.060 * sign, 0.038, 0.001))
                pcb_expl = mathutils.Vector((0.072 * sign, 0.046, -0.015))
                pcb.location = pcb_docked.lerp(pcb_expl, expl)
                pcb.scale = mathutils.Vector((1, 1, 1)) * comp_scale
                pcb.rotation_euler = (math.radians(28 * expl), math.radians(-18 * expl * sign), math.radians(12 * expl * sign))
                pcb.keyframe_insert(data_path="location", frame=f)
                pcb.keyframe_insert(data_path="scale", frame=f)
                pcb.keyframe_insert(data_path="rotation_euler", frame=f)

            # FPC Ribbon Cable
            fpc = bpy.data.objects.get(f"Jericho_FPC_Ribbon_{side}")
            if fpc:
                f_docked = mathutils.Vector((0.062 * sign, 0.052, 0.001))
                f_expl = mathutils.Vector((0.086 * sign, 0.064, -0.012))
                fpc.location = f_docked.lerp(f_expl, expl)
                fpc.scale = mathutils.Vector((1, 1, 1)) * comp_scale
                fpc.rotation_euler = (math.radians(24 * expl), math.radians(-15 * expl * sign), math.radians(10 * expl * sign))
                fpc.keyframe_insert(data_path="location", frame=f)
                fpc.keyframe_insert(data_path="scale", frame=f)
                fpc.keyframe_insert(data_path="rotation_euler", frame=f)

    print("Successfully animated symmetrical 3D sequence across 36 frames!")

run()

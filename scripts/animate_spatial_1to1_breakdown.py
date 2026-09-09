import bpy
import math
import mathutils

def setup_animation():
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 36
    
    root = bpy.data.objects.get("Jericho_Root")
    if not root:
        print("Jericho_Root not found!")
        return

    # Clear all animations on all objects
    for obj in bpy.data.objects:
        if obj.animation_data:
            obj.animation_data_clear()

    # Base resting coordinates in local space of Jericho_Root
    # When assembled (docked flush):
    # Temple right
    temple_r = bpy.data.objects.get("Temple_Meta_Right")
    # Lens right
    lens_r = bpy.data.objects.get("Lens_Meta_Right")
    lens_bevel = bpy.data.objects.get("Jericho_LensBevel")
    
    # 1-to-1 breakdown components
    cam_body = bpy.data.objects.get("Jericho_CameraModule")
    sensor_pill = bpy.data.objects.get("Jericho_SensorPill")
    hinge_tongue = bpy.data.objects.get("Jericho_HingeTongue")
    speaker = bpy.data.objects.get("Jericho_SpeakerModule")
    battery = bpy.data.objects.get("Jericho_BatteryModule")
    soc_pcb = bpy.data.objects.get("Jericho_SoCPCB")
    fpc_cable = bpy.data.objects.get("Jericho_FPC_Ribbon")

    # Store initial docked locations
    t_r_base = temple_r.location.copy() if temple_r else mathutils.Vector((0,0,0))
    l_r_base = lens_r.location.copy() if lens_r else mathutils.Vector((0,0,0))

    # Docked positions for internal components
    cam_docked = mathutils.Vector((0.052, -0.046, 0.004))
    pill_docked = mathutils.Vector((0.038, -0.046, 0.005))
    hinge_docked = mathutils.Vector((0.058, -0.035, 0.002))
    speaker_docked = mathutils.Vector((0.056, -0.010, 0.001))
    battery_docked = mathutils.Vector((0.058, 0.015, 0.001))
    soc_docked = mathutils.Vector((0.060, 0.038, 0.001))
    fpc_docked = mathutils.Vector((0.062, 0.052, 0.001))

    # Peak exploded positions (Frame 14 - 18)
    cam_exploded = mathutils.Vector((0.018, -0.075, 0.006))
    pill_exploded = mathutils.Vector((0.032, -0.070, 0.004))
    lens_exploded = l_r_base + mathutils.Vector((0.004, -0.045, 0.012))
    lens_bevel_exploded = mathutils.Vector((0.0315, -0.0935, 0.0128))
    lens_bevel_docked = mathutils.Vector((0.0315, -0.0485, 0.0008))

    temple_r_exploded = t_r_base + mathutils.Vector((0.032, 0.055, 0.006))
    hinge_exploded = hinge_docked + mathutils.Vector((0.032, 0.055, 0.006))

    speaker_exploded = mathutils.Vector((0.046, -0.006, -0.018))
    battery_exploded = mathutils.Vector((0.058, 0.020, -0.018))
    soc_exploded = mathutils.Vector((0.072, 0.046, -0.015))
    fpc_exploded = mathutils.Vector((0.086, 0.064, -0.012))

    # Helper ease function (smooth hermite)
    def smoothstep(edge0, edge1, x):
        t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
        return t * t * (3.0 - 2.0 * t)

    for f in range(1, 37):
        scene.frame_set(f)
        
        # 1. Continuous 3D Spatial Rotation across ALL 36 frames
        # Frame 1: -48 deg yaw, +13 deg pitch, -2 deg roll
        # Frame 18: -30 deg yaw, +16 deg pitch, +0.5 deg roll (elevated to show PCB & battery depth!)
        # Frame 25: -20 deg yaw, +10 deg pitch, 0 deg roll (docking)
        # Frame 36: 0 deg yaw, +1.5 deg pitch, 0 deg roll (straight-on symmetrical front view)
        t_global = (f - 1) / 35.0  # 0.0 to 1.0
        
        # Yaw smoothly rotates from -48 to 0 degrees
        yaw_deg = -48.0 * (1.0 - t_global)
        
        # Pitch: starts at 13 deg, rises slightly to 16 deg during breakdown (around f=15), then settles to 1.5 deg
        if f <= 16:
            p_factor = math.sin((f - 1) / 15.0 * (math.pi / 2.0))
            pitch_deg = 13.0 + 3.2 * p_factor
        else:
            p_factor = (f - 16) / 20.0
            pitch_deg = 16.2 * (1.0 - p_factor) + 1.5 * p_factor
            
        roll_deg = -2.0 * math.cos(t_global * math.pi)

        # Centering translation: glasses shift slightly left as components explode right, keeping viewport perfectly balanced
        center_x = -0.008 * math.sin(t_global * math.pi)
        center_y = 0.0
        center_z = -0.003 * math.sin(t_global * math.pi)

        root.rotation_euler = (math.radians(pitch_deg), math.radians(roll_deg), math.radians(yaw_deg))
        root.location = (center_x, center_y, center_z)
        root.keyframe_insert(data_path="rotation_euler", frame=f)
        root.keyframe_insert(data_path="location", frame=f)

        # 2. Explosion factor (0.0 = fully docked, 1.0 = peak breakdown)
        # Frames 1-5: Assembled (expl = 0.0)
        # Frames 6-15: Exploding outward (expl ramps 0.0 -> 1.0)
        # Frames 16-18: Hold peak exploded view (expl = 1.0)
        # Frames 19-25: Reassembly flush docking (expl ramps 1.0 -> 0.0)
        # Frames 26-36: Fully joined, rotating into front view (expl = 0.0)
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

        # Component scaling factor: when docked, internal components scale down into cavity
        # When exploding, scale quickly ramps to 1.0 so they appear naturally emerging from the housing!
        comp_scale = smoothstep(0.0, 0.35, expl)

        # Apply transforms to Temple Right
        if temple_r:
            temple_r.location = t_r_base.lerp(temple_r_exploded, expl)
            temple_r.keyframe_insert(data_path="location", frame=f)

        # Lens Right
        if lens_r:
            lens_r.location = l_r_base.lerp(lens_exploded, expl)
            lens_r.keyframe_insert(data_path="location", frame=f)

        # Lens Bevel
        if lens_bevel:
            lens_bevel.location = lens_bevel_docked.lerp(lens_bevel_exploded, expl)
            lens_bevel.scale = mathutils.Vector((1.18, 1.0, 0.92)) * comp_scale
            lens_bevel.keyframe_insert(data_path="location", frame=f)
            lens_bevel.keyframe_insert(data_path="scale", frame=f)

        # Camera Module
        if cam_body:
            cam_body.location = cam_docked.lerp(cam_exploded, expl)
            cam_body.scale = mathutils.Vector((1, 1, 1)) * comp_scale
            # subtle tilt to catch light
            cam_body.rotation_euler = (math.radians(90 - 15 * expl), math.radians(20 * expl), 0)
            cam_body.keyframe_insert(data_path="location", frame=f)
            cam_body.keyframe_insert(data_path="scale", frame=f)
            cam_body.keyframe_insert(data_path="rotation_euler", frame=f)

        # Sensor Pill
        if sensor_pill:
            sensor_pill.location = pill_docked.lerp(pill_exploded, expl)
            sensor_pill.scale = mathutils.Vector((1, 1, 1)) * comp_scale
            sensor_pill.rotation_euler = (math.radians(90 - 10 * expl), math.radians(15 * expl), 0)
            sensor_pill.keyframe_insert(data_path="location", frame=f)
            sensor_pill.keyframe_insert(data_path="scale", frame=f)
            sensor_pill.keyframe_insert(data_path="rotation_euler", frame=f)

        # Hinge Tongue
        if hinge_tongue:
            hinge_tongue.location = hinge_docked.lerp(hinge_exploded, expl)
            hinge_tongue.scale = mathutils.Vector((1, 1, 1)) * comp_scale
            hinge_tongue.keyframe_insert(data_path="location", frame=f)
            hinge_tongue.keyframe_insert(data_path="scale", frame=f)

        # Speaker Module
        if speaker:
            speaker.location = speaker_docked.lerp(speaker_exploded, expl)
            speaker.scale = mathutils.Vector((1, 1, 1)) * comp_scale
            # Tilt forward to display the metallic grill
            speaker.rotation_euler = (math.radians(25 * expl), math.radians(-10 * expl), math.radians(15 * expl))
            speaker.keyframe_insert(data_path="location", frame=f)
            speaker.keyframe_insert(data_path="scale", frame=f)
            speaker.keyframe_insert(data_path="rotation_euler", frame=f)

        # Battery Module
        if battery:
            battery.location = battery_docked.lerp(battery_exploded, expl)
            battery.scale = mathutils.Vector((1, 1, 1)) * comp_scale
            battery.rotation_euler = (math.radians(10 * expl), 0, math.radians(-8 * expl))
            battery.keyframe_insert(data_path="location", frame=f)
            battery.keyframe_insert(data_path="scale", frame=f)
            battery.keyframe_insert(data_path="rotation_euler", frame=f)

        # Main SoC PCB
        if soc_pcb:
            soc_pcb.location = soc_docked.lerp(soc_exploded, expl)
            soc_pcb.scale = mathutils.Vector((1, 1, 1)) * comp_scale
            # Tilt to present processor die and gold pins to camera
            soc_pcb.rotation_euler = (math.radians(28 * expl), math.radians(-18 * expl), math.radians(12 * expl))
            soc_pcb.keyframe_insert(data_path="location", frame=f)
            soc_pcb.keyframe_insert(data_path="scale", frame=f)
            soc_pcb.keyframe_insert(data_path="rotation_euler", frame=f)

        # FPC Ribbon Cable
        if fpc_cable:
            fpc_cable.location = fpc_docked.lerp(fpc_exploded, expl)
            fpc_cable.scale = mathutils.Vector((1, 1, 1)) * comp_scale
            fpc_cable.rotation_euler = (math.radians(24 * expl), math.radians(-15 * expl), math.radians(10 * expl))
            fpc_cable.keyframe_insert(data_path="location", frame=f)
            fpc_cable.keyframe_insert(data_path="scale", frame=f)
            fpc_cable.keyframe_insert(data_path="rotation_euler", frame=f)

    # Set interpolation to smooth bezier for all animation curves
    for obj in [root, temple_r, lens_r, lens_bevel, cam_body, sensor_pill, hinge_tongue, speaker, battery, soc_pcb, fpc_cable]:
        if obj and obj.animation_data and obj.animation_data.action:
            try:
                for fcurve in obj.animation_data.action.fcurves:
                    for kf in fcurve.keyframe_points:
                        kf.interpolation = 'BEZIER'
            except Exception:
                pass

    print("Setup 1-to-1 spatial animation with continuous rotation successfully across 36 frames!")

setup_animation()

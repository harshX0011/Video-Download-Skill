"""Animated product camera moves, rendered to a PNG frame sequence (encode with encode_video.py).

  blender -b scene.blend --python camera_move.py -- --move turntable --out frames/

Moves
  turntable     360 orbit, constant speed. Classic showcase.
  perfect-loop  360 orbit whose last frame leads into the first. For GIF / web loops.
  slow-zoom     push-in from wide to a hero detail with a focal length ramp (reveal).
  dolly-rotate  camera moves in while rotating N degrees (sweeping shot).
  crane         low angle rising to a high reveal, pulling back as it rises.
  preview       4 low-res stills (front/right/back/left) to find the product's front. No video.

Common options
  --out DIR            frames folder (required, created). Frames are 0001.png ...
  --duration 5         seconds            --fps 24
  --width 1920 --height 1080              --engine eevee|cycles   --samples 64
  --opaque             solid background instead of transparent
  --distance D         camera distance (default: auto from object size)
  --height H           camera height above object center (default: auto)
  --lens 50            focal length mm
  --front-angle 0      degrees to rotate the orbit start (use after `preview`: right=90 back=180 left=270)
  --target NAME        orbit/focus around this object only (default: all meshes)
  --light PRESET       add studio lights if the scene has none (studio|dramatic|soft|sunset)
  --save out.blend     save the rigged scene
  --no-render          set up the rig and keyframes, skip rendering (open in GUI to inspect)

Move-specific
  slow-zoom:     --end-distance --end-height --end-lens --focus x,y,z
  dolly-rotate:  --rotation 90 --end-distance --end-height
  crane:         --start-height -0.2 --end-height --end-distance
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *  # noqa

p = argparse.ArgumentParser()
p.add_argument("--move", required=True,
               choices=["turntable", "perfect-loop", "slow-zoom", "dolly-rotate", "crane", "preview"])
p.add_argument("--out", required=True)
p.add_argument("--duration", type=float, default=5.0)
p.add_argument("--fps", type=int, default=24)
p.add_argument("--width", type=int, default=1920)
p.add_argument("--height", type=int, default=1080)
p.add_argument("--engine", default="eevee", choices=["eevee", "cycles"])
p.add_argument("--samples", type=int, default=64)
p.add_argument("--opaque", action="store_true")
p.add_argument("--distance", type=float)
p.add_argument("--height-cam", "--cam-height", dest="cam_height", type=float)
p.add_argument("--lens", type=float, default=50.0)
p.add_argument("--front-angle", type=float, default=0.0)
p.add_argument("--target")
p.add_argument("--light", choices=["studio", "dramatic", "soft", "sunset"])
p.add_argument("--save")
p.add_argument("--no-render", action="store_true")
# slow-zoom / dolly / crane
p.add_argument("--end-distance", type=float)
p.add_argument("--end-height", type=float)
p.add_argument("--end-lens", type=float)
p.add_argument("--focus", help="x,y,z point to zoom toward (slow-zoom)")
p.add_argument("--rotation", type=float, default=90.0, help="degrees (dolly-rotate)")
p.add_argument("--start-height", type=float, help="crane start height (relative to object center)")
a = parse(p)

scene = bpy.context.scene
objs = mesh_objects([a.target]) if a.target else mesh_objects()
if not objs:
    raise SystemExit("no mesh objects in scene (run import_model.py first)")
center, size, radius, mn, mx = scene_bounds(objs)
radius = max(radius, 0.05)

# Auto framing: distance so the object fills ~60% of frame at the chosen lens
sensor = 36.0
fov = 2 * math.atan(sensor / (2 * a.lens))
auto_dist = (radius / 0.6) / math.tan(fov / 2)
D = a.distance if a.distance else auto_dist
H = a.cam_height if a.cam_height is not None else radius * 0.9

if a.light and not any(o.type == "LIGHT" for o in bpy.data.objects):
    studio_lights(center, radius, preset=a.light)
    neutral_world()

# Remove rigs from previous runs
for o in [o for o in bpy.data.objects if o.name.startswith("CamRig")]:
    bpy.data.objects.remove(o, do_unlink=True)

out_dir = os.path.abspath(a.out)
os.makedirs(out_dir, exist_ok=True)
total = int(round(a.duration * a.fps))
scene.frame_start, scene.frame_end = 1, total
front = math.radians(a.front_angle)


def polar(dist, height, angle):
    """Camera position on a circle around center. angle 0 = in front (-Y)."""
    return (center.x + dist * math.sin(angle), center.y - dist * math.cos(angle), center.z + height)


def rig(name_suffix=""):
    tgt = add_empty("CamRigTarget" + name_suffix, center)
    cam = add_camera("CamRigCamera" + name_suffix, polar(D, H, front), tgt, lens=a.lens)
    return tgt, cam


def key(obj, path, frame, value=None):
    if value is not None:
        setattr(obj, path, value)
    obj.keyframe_insert(data_path=path, frame=frame)


# ------------------------------------------------------------------ moves
if a.move == "preview":
    tgt, cam = rig()
    scene.render.resolution_percentage = 100
    configure_render(640, 360, a.fps, not a.opaque, 16, a.engine)
    files = {}
    for label, deg in (("front", 0), ("right", 90), ("back", 180), ("left", 270)):
        cam.location = polar(D, H, math.radians(deg))
        fp = os.path.join(out_dir, f"preview_{label}.png")
        scene.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        files[label] = fp
    out({"move": "preview", "files": files, "hint": "pass --front-angle 0|90|180|270 to the real move"})
    raise SystemExit(0)

if a.move in ("turntable", "perfect-loop"):
    tgt, cam = rig()
    cam.parent = tgt
    cam.matrix_parent_inverse = tgt.matrix_world.inverted()
    key(tgt, "rotation_euler", 1, (0, 0, 0))
    # perfect-loop: 360 lands one frame PAST the last rendered frame so frame N -> frame 1 is seamless.
    last = total + 1 if a.move == "perfect-loop" else total
    key(tgt, "rotation_euler", last, (0, 0, math.radians(360)))
    set_interpolation(tgt, "LINEAR")

elif a.move == "slow-zoom":
    tgt, cam = rig()
    end_d = a.end_distance or D * 0.45
    end_h = a.end_height if a.end_height is not None else H * 0.4
    end_lens = a.end_lens or a.lens * 1.3
    start_lens = a.lens * 0.7
    if a.focus:
        fx, fy, fz = (float(v) for v in a.focus.split(","))
        key(tgt, "location", 1, tuple(center))
        key(tgt, "location", total, (fx, fy, fz))
    cam.data.lens = start_lens
    cam.data.keyframe_insert(data_path="lens", frame=1)
    key(cam, "location", 1, polar(D, H * 1.5, front))
    cam.data.lens = end_lens
    cam.data.keyframe_insert(data_path="lens", frame=total)
    key(cam, "location", total, polar(end_d, end_h, front))
    ease_in_out(cam); ease_in_out(tgt)
    for fc in iter_fcurves(cam.data.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"; kp.easing = "EASE_IN_OUT"

elif a.move == "dolly-rotate":
    tgt, cam = rig()
    cam.parent = tgt
    cam.matrix_parent_inverse = tgt.matrix_world.inverted()
    end_d = a.end_distance or D * 0.65
    end_h = a.end_height if a.end_height is not None else H * 0.75
    key(cam, "location", 1, polar(D, H, front))
    key(cam, "location", total, polar(end_d, end_h, front))
    key(tgt, "rotation_euler", 1, (0, 0, 0))
    key(tgt, "rotation_euler", total, (0, 0, math.radians(a.rotation)))
    ease_in_out(cam); ease_in_out(tgt)

elif a.move == "crane":
    tgt, cam = rig()
    start_h = a.start_height if a.start_height is not None else -radius * 0.6
    end_h = a.end_height if a.end_height is not None else radius * 1.8
    start_d = D * 0.75
    end_d = a.end_distance or D * 1.1
    key(cam, "location", 1, polar(start_d, start_h, front))
    key(cam, "location", total, polar(end_d, end_h, front))
    ease_in_out(cam)

# ------------------------------------------------------------------ render
configure_render(a.width, a.height, a.fps, not a.opaque, a.samples, a.engine)
if not scene.world:
    neutral_world()
scene.render.filepath = os.path.join(out_dir, "")  # Blender appends 0001.png
saved = save_blend(a.save)

if a.no_render:
    out({"move": a.move, "frames": total, "fps": a.fps, "camera": cam.name, "distance": D, "height": H,
         "saved": saved, "rendered": False})
    raise SystemExit(0)

bpy.ops.render.render(animation=True)
rendered = sorted(f for f in os.listdir(out_dir) if f.lower().endswith(".png"))
out({"move": a.move, "frames_dir": out_dir, "frames": len(rendered), "expected": total, "fps": a.fps,
     "pattern": os.path.join(out_dir, "%04d.png"), "distance": round(D, 3), "height": round(H, 3),
     "saved": saved, "rendered": True,
     "next": f"python3 encode_video.py --frames '{out_dir}' --fps {a.fps} --out video.mov"})

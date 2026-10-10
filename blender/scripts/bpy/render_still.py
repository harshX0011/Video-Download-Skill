"""Render one still image of the scene.

  blender -b scene.blend --python render_still.py -- --out shot.png [--angle 30] [--elevation 20]
        [--distance D] [--lens 50] [--width 1920 --height 1080] [--engine eevee|cycles] [--samples 64]
        [--opaque] [--light studio] [--use-scene-camera]

Without --use-scene-camera a temp camera is placed on an orbit around the meshes:
--angle is degrees around the object (0 = front, 90 = right), --elevation degrees above center.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *  # noqa

p = argparse.ArgumentParser()
p.add_argument("--out", required=True)
p.add_argument("--angle", type=float, default=30.0)
p.add_argument("--elevation", type=float, default=20.0)
p.add_argument("--distance", type=float)
p.add_argument("--lens", type=float, default=50.0)
p.add_argument("--width", type=int, default=1920)
p.add_argument("--height", type=int, default=1080)
p.add_argument("--engine", default="eevee", choices=["eevee", "cycles"])
p.add_argument("--samples", type=int, default=64)
p.add_argument("--opaque", action="store_true")
p.add_argument("--light", choices=["studio", "dramatic", "soft", "sunset"])
p.add_argument("--use-scene-camera", action="store_true")
p.add_argument("--target")
a = parse(p)

scene = bpy.context.scene
objs = mesh_objects([a.target]) if a.target else mesh_objects()
center, size, radius, _, _ = scene_bounds(objs)
radius = max(radius, 0.05)

if a.light and not any(o.type == "LIGHT" for o in bpy.data.objects):
    studio_lights(center, radius, preset=a.light)
    neutral_world()

if not a.use_scene_camera or not scene.camera:
    fov = 2 * math.atan(36.0 / (2 * a.lens))
    D = a.distance or (radius / 0.6) / math.tan(fov / 2)
    ang, el = math.radians(a.angle), math.radians(a.elevation)
    loc = (center.x + D * math.cos(el) * math.sin(ang),
           center.y - D * math.cos(el) * math.cos(ang),
           center.z + D * math.sin(el))
    tgt = add_empty("StillTarget", center)
    add_camera("StillCamera", loc, tgt, lens=a.lens)

configure_render(a.width, a.height, 24, not a.opaque, a.samples, a.engine)
if not scene.world:
    neutral_world()
out_path = os.path.abspath(a.out)
os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
scene.render.filepath = out_path
bpy.ops.render.render(write_still=True)
out({"file": out_path, "engine": scene.render.engine, "camera": scene.camera.name})

"""Import a model (glb/gltf/fbx/obj/stl/usd/blend) into a clean scene, center it, scale it.

  blender -b --python import_model.py -- --file model.glb [--size 2] [--keep] [--no-floor] [--save out.blend]

--size    largest dimension after scaling (Blender units / metres). 0 = keep original scale.
--keep    keep existing scene objects instead of clearing the scene.
--no-floor  center at origin instead of resting the model on z=0.
--save    write a .blend to continue with camera_move.py / render_still.py.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *  # noqa

p = argparse.ArgumentParser()
p.add_argument("--file", required=True)
p.add_argument("--size", type=float, default=2.0)
p.add_argument("--keep", action="store_true")
p.add_argument("--no-floor", action="store_true")
p.add_argument("--save")
a = parse(p)

path = os.path.abspath(a.file)
if not os.path.isfile(path):
    raise SystemExit(f"file not found: {path}")

if not a.keep:
    clear_scene()

new_objs = import_any(path)
meshes = [o for o in new_objs if o.type == "MESH"]
if not meshes:
    raise SystemExit("import produced no mesh objects")

root = None
if a.size > 0:
    root = center_and_scale(new_objs, target_size=a.size, floor=not a.no_floor)

center, size, radius, _, _ = scene_bounds(meshes)
saved = save_blend(a.save)
out({
    "imported": [o.name for o in new_objs],
    "meshes": len(meshes),
    "verts": sum(len(o.data.vertices) for o in meshes),
    "root": root.name if root else None,
    "bounds": {"center": list(center), "size": list(size), "radius": radius},
    "saved": saved,
})

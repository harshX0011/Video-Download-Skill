"""Product-shot finish: glossy materials + scaled 4-point studio lighting + neutral world.

  blender -b scene.blend --python product_polish.py -- [--preset studio|dramatic|soft|sunset]
        [--roughness 0.05] [--coat 1.0] [--metallic 0.1] [--keep-maps] [--engine eevee|cycles] [--save out.blend]

Run after import_model.py. Existing lights are removed and replaced.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *  # noqa

p = argparse.ArgumentParser()
p.add_argument("--preset", default="studio", choices=["studio", "dramatic", "soft", "sunset"])
p.add_argument("--roughness", type=float, default=0.05)
p.add_argument("--coat", type=float, default=1.0)
p.add_argument("--metallic", type=float, default=0.1)
p.add_argument("--keep-maps", action="store_true", help="do not strip normal/roughness textures")
p.add_argument("--no-material", action="store_true", help="lighting only, leave materials as is")
p.add_argument("--engine", default="eevee", choices=["eevee", "cycles"])
p.add_argument("--save")
a = parse(p)

for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:
    bpy.data.objects.remove(o, do_unlink=True)

center, size, radius, _, _ = scene_bounds()
lights = studio_lights(center, max(radius, 0.25), preset=a.preset)
touched = 0 if a.no_material else glossy_materials(a.roughness, a.coat, a.metallic, strip_maps=not a.keep_maps)
neutral_world()
engine = set_engine(a.engine)
saved = save_blend(a.save)
out({"preset": a.preset, "lights": [l.name for l in lights], "materials_touched": touched,
     "engine": engine, "saved": saved})

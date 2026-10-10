"""Export the scene (or selected objects) to GLB/GLTF/FBX/OBJ/USD.

  blender -b scene.blend --python export_glb.py -- --out model.glb [--draco] [--objects A,B]
        [--no-animation] [--no-apply]

Format is picked from the --out extension: .glb .gltf .fbx .obj .usd/.usdc/.usdz
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *  # noqa

p = argparse.ArgumentParser()
p.add_argument("--out", required=True)
p.add_argument("--objects", help="comma separated object names (default: all meshes + their parents)")
p.add_argument("--draco", action="store_true", help="Draco mesh compression (glb/gltf)")
p.add_argument("--no-animation", action="store_true")
p.add_argument("--no-apply", action="store_true", help="do not apply modifiers")
a = parse(p)

out_path = os.path.abspath(a.out)
os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
ext = os.path.splitext(out_path)[1].lower()

bpy.ops.object.select_all(action="DESELECT")
if a.objects:
    names = set(a.objects.split(","))
    sel = [o for o in bpy.data.objects if o.name in names]
else:
    sel = [o for o in bpy.data.objects if o.type == "MESH"]
    for o in list(sel):
        par = o.parent
        while par:
            sel.append(par); par = par.parent
for o in set(sel):
    o.select_set(True)

if ext in (".glb", ".gltf"):
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format="GLB" if ext == ".glb" else "GLTF_SEPARATE",
        use_selection=True,
        export_apply=not a.no_apply,
        export_animations=not a.no_animation,
        export_draco_mesh_compression_enable=a.draco,
        export_image_format="AUTO",
        export_materials="EXPORT",
        export_texcoords=True,
        export_normals=True,
        export_yup=True,
    )
elif ext == ".fbx":
    bpy.ops.export_scene.fbx(filepath=out_path, use_selection=True, bake_anim=not a.no_animation,
                             use_mesh_modifiers=not a.no_apply, path_mode="COPY", embed_textures=True)
elif ext == ".obj":
    if hasattr(bpy.ops.wm, "obj_export"):
        bpy.ops.wm.obj_export(filepath=out_path, export_selected_objects=True, apply_modifiers=not a.no_apply)
    else:
        bpy.ops.export_scene.obj(filepath=out_path, use_selection=True)
elif ext in (".usd", ".usdc", ".usda", ".usdz"):
    bpy.ops.wm.usd_export(filepath=out_path, selected_objects_only=True, export_animation=not a.no_animation)
else:
    raise SystemExit(f"unsupported export format: {ext}")

size_mb = os.path.getsize(out_path) / (1024 * 1024)
out({"file": out_path, "size_mb": round(size_mb, 2), "objects": sorted(o.name for o in set(sel))})

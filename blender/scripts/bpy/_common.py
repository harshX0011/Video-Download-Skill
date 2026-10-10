"""
Shared helpers for the bpy scripts in this folder.

Every script does:
    import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _common import *

Works in Blender 3.6 LTS, 4.x and 5.x. Version differences are handled here so
the scripts themselves stay simple.
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector

VERSION = bpy.app.version  # (major, minor, patch)


# ---------------------------------------------------------------- args
def script_args():
    """Arguments after '--' on the Blender command line."""
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def parse(parser: argparse.ArgumentParser):
    return parser.parse_args(script_args())


def out(obj):
    """Print one JSON line so callers can parse the result."""
    print("RESULT " + json.dumps(obj, default=str))


# ---------------------------------------------------------------- scene
def clear_scene(keep_types=()):
    """Delete every object except the given types (e.g. ('CAMERA',))."""
    for o in list(bpy.data.objects):
        if o.type in keep_types:
            continue
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.lights, bpy.data.cameras):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def mesh_objects(names=None):
    objs = [o for o in bpy.data.objects if o.type == "MESH"]
    if names:
        wanted = set(names)
        objs = [o for o in objs if o.name in wanted]
    return objs


def scene_bounds(objs=None):
    """World-space bounding box of the given (or all) mesh objects.

    Returns (center: Vector, size: Vector, radius: float, min: Vector, max: Vector)
    """
    objs = objs or mesh_objects()
    pts = []
    for o in objs:
        pts.extend(o.matrix_world @ Vector(c) for c in o.bound_box)
    if not pts:
        z = Vector((0, 0, 0))
        return z, Vector((1, 1, 1)), 1.0, z, z
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center = (mn + mx) / 2
    size = mx - mn
    return center, size, size.length / 2, mn, mx


def center_and_scale(objs, target_size=2.0, floor=True):
    """Move objects so their bbox center is at the origin (optionally resting on z=0)
    and uniformly scale so the largest dimension equals target_size."""
    center, size, _, mn, _ = scene_bounds(objs)
    biggest = max(size.x, size.y, size.z) or 1.0
    s = target_size / biggest
    # Parent everything to one empty so multi-object imports move together
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    root = bpy.context.active_object
    root.name = "ModelRoot"
    for o in objs:
        if o.parent is None:
            o.parent = root
    root.scale = (s, s, s)
    shift = -center * s
    if floor:
        shift.z = -mn.z * s
    root.location = shift
    bpy.context.view_layer.update()
    return root


# ---------------------------------------------------------------- render
def set_engine(engine="eevee"):
    """engine: 'eevee' | 'cycles' | 'workbench'. Handles enum renames across versions."""
    scene = bpy.context.scene
    engine = engine.lower()
    if engine == "cycles":
        scene.render.engine = "CYCLES"
        return "CYCLES"
    if engine == "workbench":
        scene.render.engine = "BLENDER_WORKBENCH"
        return "BLENDER_WORKBENCH"
    # EEVEE: 4.2 - 4.x => BLENDER_EEVEE_NEXT ; 5.x and <4.2 => BLENDER_EEVEE
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = name
            return name
        except TypeError:
            continue
    raise RuntimeError("no EEVEE engine enum found")


def configure_render(width=1920, height=1080, fps=24, transparent=True, samples=64,
                     engine="eevee", gpu=True, denoise=True, fmt="PNG"):
    scene = bpy.context.scene
    r = scene.render
    r.resolution_x, r.resolution_y = width, height
    r.resolution_percentage = 100
    r.fps = fps
    r.film_transparent = transparent
    r.image_settings.file_format = fmt
    r.image_settings.color_mode = "RGBA" if transparent else "RGB"
    if fmt == "PNG":
        r.image_settings.color_depth = "8"
    used = set_engine(engine)
    if used == "CYCLES":
        scene.cycles.samples = samples
        scene.cycles.use_denoising = denoise
        if gpu:
            try:
                scene.cycles.device = "GPU"
                prefs = bpy.context.preferences.addons["cycles"].preferences
                for backend in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
                    try:
                        prefs.compute_device_type = backend
                        prefs.get_devices()
                        for d in prefs.devices:
                            d.use = True
                        break
                    except Exception:
                        continue
            except Exception:
                scene.cycles.device = "CPU"
    else:
        try:
            scene.eevee.taa_render_samples = samples
        except AttributeError:
            pass
        # Ray-traced reflections where available (4.2+)
        try:
            scene.eevee.use_raytracing = True
        except AttributeError:
            pass
    return used


def neutral_world(color=(0.95, 0.95, 0.95), strength=0.3):
    scene = bpy.context.scene
    if not scene.world:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (*color, 1)
        bg.inputs["Strength"].default_value = strength


# ---------------------------------------------------------------- animation
def iter_fcurves(action):
    """Yield fcurves from legacy or layered (Blender 4.4+/5.x) actions."""
    layers = getattr(action, "layers", None)
    if layers:
        for layer in layers:
            for strip in layer.strips:
                for cb in getattr(strip, "channelbags", []):
                    for fc in cb.fcurves:
                        yield fc
        return
    for fc in getattr(action, "fcurves", []):
        yield fc


def set_interpolation(obj, mode="LINEAR"):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    for fc in iter_fcurves(ad.action):
        for kp in fc.keyframe_points:
            kp.interpolation = mode


def ease_in_out(obj):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    for fc in iter_fcurves(ad.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.easing = "EASE_IN_OUT"


# ---------------------------------------------------------------- camera / lights
def add_camera(name, location, target, lens=50.0):
    bpy.ops.object.camera_add(location=location)
    cam = bpy.context.active_object
    cam.name = name
    cam.data.lens = lens
    cam.data.clip_end = 1000
    trk = cam.constraints.new(type="TRACK_TO")
    trk.target = target
    trk.track_axis = "TRACK_NEGATIVE_Z"
    trk.up_axis = "UP_Y"
    bpy.context.scene.camera = cam
    return cam


def add_empty(name, location=(0, 0, 0)):
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=location)
    e = bpy.context.active_object
    e.name = name
    return e


def add_area_light(name, location, energy, size, color=(1, 1, 1), rotation=(0, 0, 0)):
    bpy.ops.object.light_add(type="AREA", location=location)
    l = bpy.context.active_object
    l.name = name
    l.data.energy = energy
    l.data.size = size
    l.data.color = color
    l.rotation_euler = tuple(math.radians(v) for v in rotation)
    return l


def aim(obj, target_location):
    """Point a light/camera at a location using a TRACK_TO constraint on a temp empty."""
    e = add_empty(obj.name + "_aim", target_location)
    e.hide_viewport = e.hide_render = True
    c = obj.constraints.new(type="TRACK_TO")
    c.target = e
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return e


def studio_lights(center, radius, preset="studio", warm=False):
    """4-point area light rig scaled to the object. Presets: studio | dramatic | soft | sunset."""
    presets = {
        "studio":   dict(key=350, fill=250, rim=250, bounce=100),
        "dramatic": dict(key=500, fill=80,  rim=400, bounce=50),
        "soft":     dict(key=200, fill=200, rim=150, bounce=150),
        "sunset":   dict(key=400, fill=200, rim=250, bounce=120),
    }
    p = presets.get(preset, presets["studio"])
    # Scale wattage with distance^2 so small/large objects look the same
    k = (radius / 1.0) ** 2
    d = radius
    if preset == "sunset" or warm:
        colors = dict(key=(1.0, 0.78, 0.45), fill=(1.0, 0.75, 0.4), rim=(1.0, 0.65, 0.3), bounce=(1.0, 0.92, 0.75))
    else:
        colors = dict(key=(1.0, 0.96, 0.9), fill=(0.9, 0.94, 1.0), rim=(1, 1, 1), bounce=(1, 1, 1))
    cx, cy, cz = center
    lights = [
        add_area_light("KeyLight",    (cx + 3 * d, cy - 3 * d, cz + 4 * d), p["key"] * k,    3 * d, colors["key"]),
        add_area_light("FillLight",   (cx - 3 * d, cy - 2 * d, cz + 3 * d), p["fill"] * k,   5 * d, colors["fill"]),
        add_area_light("RimLight",    (cx,         cy + 4 * d, cz + 2 * d), p["rim"] * k,    3 * d, colors["rim"]),
        add_area_light("BounceLight", (cx,         cy,         cz - 1.5 * d), p["bounce"] * k, 8 * d, colors["bounce"]),
    ]
    for l in lights:
        aim(l, center)
    return lights


# ---------------------------------------------------------------- materials
def set_input(node, names, value):
    """Set the first matching socket name (handles 3.x vs 4.x Principled renames)."""
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return True
    return False


def glossy_materials(roughness=0.05, coat=1.0, metallic=0.1, strip_maps=True):
    """Give every material a clean glossy product look. Strips noisy normal /
    roughness maps (common in AI generated GLBs) when strip_maps is True."""
    touched = 0
    for mat in bpy.data.materials:
        if not mat.use_nodes or not mat.node_tree:
            continue
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        if strip_maps:
            for link in [l for l in links if l.to_socket.name in ("Normal", "Roughness", "Metallic")]:
                links.remove(link)
            for n in [n for n in nodes if n.type in ("NORMAL_MAP", "SEPARATE_COLOR")]:
                nodes.remove(n)
            for n in [n for n in nodes if n.type == "TEX_IMAGE"]:
                if not any(l for o in n.outputs for l in o.links):
                    nodes.remove(n)
        for node in nodes:
            if node.type != "BSDF_PRINCIPLED":
                continue
            set_input(node, ("Roughness",), roughness)
            set_input(node, ("Metallic",), metallic)
            set_input(node, ("Coat Weight", "Clearcoat"), coat)
            set_input(node, ("Coat Roughness", "Clearcoat Roughness"), 0.0)
            set_input(node, ("Specular IOR Level", "Specular"), 1.0 if "Specular IOR Level" in node.inputs else 0.5)
            set_input(node, ("IOR",), 1.5)
            touched += 1
    return touched


# ---------------------------------------------------------------- io
def import_any(path):
    ext = os.path.splitext(path)[1].lower()
    before = set(bpy.data.objects)
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=path)
        else:
            bpy.ops.import_scene.obj(filepath=path)
    elif ext == ".stl":
        if hasattr(bpy.ops.wm, "stl_import"):
            bpy.ops.wm.stl_import(filepath=path)
        else:
            bpy.ops.import_mesh.stl(filepath=path)
    elif ext == ".usd" or ext == ".usdc" or ext == ".usdz" or ext == ".usda":
        bpy.ops.wm.usd_import(filepath=path)
    elif ext == ".blend":
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.objects = src.objects
        for o in dst.objects:
            if o is not None:
                bpy.context.scene.collection.objects.link(o)
    else:
        raise ValueError(f"unsupported model format: {ext}")
    return [o for o in bpy.data.objects if o not in before]


def save_blend(path):
    if path:
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=path)
    return path

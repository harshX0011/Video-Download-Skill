"""Dump the current scene as JSON: objects, cameras, lights, materials, render settings, bounds.

Usage (headless):  blender -b file.blend --python scene_info.py
Usage (live):      python3 blender_cli.py scene-info
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *  # noqa

scene = bpy.context.scene
center, size, radius, mn, mx = scene_bounds()
info = {
    "blender_version": ".".join(map(str, VERSION)),
    "file": bpy.data.filepath or None,
    "frame_range": [scene.frame_start, scene.frame_end],
    "fps": scene.render.fps,
    "engine": scene.render.engine,
    "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    "active_camera": scene.camera.name if scene.camera else None,
    "mesh_bounds": {"center": list(center), "size": list(size), "radius": radius},
    "objects": [
        {
            "name": o.name, "type": o.type,
            "location": [round(v, 4) for v in o.matrix_world.translation],
            "dimensions": [round(v, 4) for v in o.dimensions] if o.type == "MESH" else None,
            "verts": len(o.data.vertices) if o.type == "MESH" else None,
            "materials": [m.name for m in o.data.materials if m] if o.type == "MESH" else None,
            "parent": o.parent.name if o.parent else None,
            "animated": bool(o.animation_data and o.animation_data.action),
        }
        for o in bpy.data.objects
    ],
    "materials": [m.name for m in bpy.data.materials],
    "images": [i.name for i in bpy.data.images if i.name not in ("Render Result", "Viewer Node")],
}
out(info)

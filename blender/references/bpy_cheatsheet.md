# bpy cheatsheet (3.6 LTS, 4.x, 5.x)

Use `scripts/bpy/_common.py` helpers where one exists; they already handle the version
differences listed at the bottom.

## Run a script headless

```bash
blender --background                      --python script.py -- --arg value   # fresh scene
blender --background scene.blend          --python script.py -- --arg value   # open a file first
blender --background --factory-startup    --python script.py                  # ignore user prefs/addons
```

Arguments after `--` are yours: `sys.argv[sys.argv.index("--") + 1:]`.
Output files are written where the script says; Blender itself writes nothing unless asked.

## Scene basics

```python
import bpy, math
from mathutils import Vector

scene = bpy.context.scene
bpy.data.objects.remove(obj, do_unlink=True)        # delete one object
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)   # clear all
obj = bpy.data.objects["Cube"]
obj.location = (0, 0, 1); obj.rotation_euler = (0, 0, math.radians(45)); obj.scale = (2, 2, 2)
bpy.context.view_layer.update()                      # refresh matrix_world after edits
world_pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]   # world-space bbox corners
```

## Import / export

```python
bpy.ops.import_scene.gltf(filepath=p)                # .glb / .gltf
bpy.ops.import_scene.fbx(filepath=p)
bpy.ops.wm.obj_import(filepath=p)                    # 3.4+ (older: import_scene.obj)
bpy.ops.wm.stl_import(filepath=p)                    # 4.0+ (older: import_mesh.stl)
bpy.ops.export_scene.gltf(filepath=p, export_format="GLB", use_selection=True, export_apply=True,
                          export_draco_mesh_compression_enable=True)
bpy.ops.wm.save_as_mainfile(filepath="scene.blend")
```

## Camera that always looks at a point

```python
bpy.ops.object.empty_add(type="PLAIN_AXES", location=center); tgt = bpy.context.active_object
bpy.ops.object.camera_add(location=(0, -4, 2)); cam = bpy.context.active_object
cam.data.lens = 50
c = cam.constraints.new(type="TRACK_TO"); c.target = tgt
c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
scene.camera = cam
# orbit: parent the camera to the empty and keyframe the empty's Z rotation
cam.parent = tgt; cam.matrix_parent_inverse = tgt.matrix_world.inverted()
```

## Keyframes

```python
obj.rotation_euler = (0, 0, 0);               obj.keyframe_insert("rotation_euler", frame=1)
obj.rotation_euler = (0, 0, math.radians(360)); obj.keyframe_insert("rotation_euler", frame=121)
cam.data.lens = 35; cam.data.keyframe_insert("lens", frame=1)    # camera DATA, not object
scene.frame_start, scene.frame_end = 1, 120
```

Interpolation lives on fcurve keyframe points. Use `_common.set_interpolation(obj, "LINEAR")`
or `_common.ease_in_out(obj)`; see version notes for why.

## Lights

```python
bpy.ops.object.light_add(type="AREA", location=(3, -3, 4)); l = bpy.context.active_object
l.data.energy = 350   # watts; scale with distance squared when the object is big/small
l.data.size = 3.0     # bigger = softer shadows
l.data.color = (1.0, 0.78, 0.45)   # warm; put colour on lights, not on the world
```

## Materials (Principled BSDF)

```python
for mat in bpy.data.materials:
    if not mat.use_nodes: continue
    for n in mat.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            n.inputs["Base Color"].default_value = (0.8, 0.1, 0.1, 1)
            n.inputs["Roughness"].default_value = 0.05
            n.inputs["Metallic"].default_value = 0.1
```
AI-generated GLBs (Meshy, Tripo, Hyper3D) usually ship noisy normal and roughness maps that look
dotty under studio light. `_common.glossy_materials()` unlinks them.

## Render settings

```python
r = scene.render
r.resolution_x, r.resolution_y, r.fps = 1920, 1080, 24
r.film_transparent = True
r.image_settings.file_format = "PNG"; r.image_settings.color_mode = "RGBA"
r.filepath = "/abs/path/frames/"         # animation => frames/0001.png ...
bpy.ops.render.render(animation=True)     # or write_still=True for one frame
scene.cycles.samples = 64; scene.cycles.use_denoising = True; scene.cycles.device = "GPU"
```
Do not use Blender's FFMPEG output: it is missing in 5.x builds and alpha support is poor.
Render PNGs, then `scripts/encode_video.py`.

## Version differences (handled by `_common.py`)

| Topic | 3.6 / 4.0 / 4.1 | 4.2 to 4.5 | 5.x |
|-------|-----------------|------------|-----|
| EEVEE engine enum | `BLENDER_EEVEE` | `BLENDER_EEVEE_NEXT` | `BLENDER_EEVEE` |
| Principled sockets | `Clearcoat`, `Specular` | `Coat Weight`, `Specular IOR Level` | same as 4.2 |
| Action fcurves | `action.fcurves` | `action.fcurves` (4.4+ also layered) | `action.layers[0].strips[0].channelbags[*].fcurves` |
| OBJ / STL import | `import_scene.obj`, `import_mesh.stl` | `wm.obj_import`, `wm.stl_import` | same |
| EEVEE ray tracing | n/a | `scene.eevee.use_raytracing` | same |
| Video output | FFMPEG available | FFMPEG available | PNG sequence + ffmpeg |

Check at runtime with `bpy.app.version` (tuple) rather than guessing from the install path.

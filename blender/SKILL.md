---
name: blender
description: Drive a locally installed Blender from the terminal to import 3D models (GLB/FBX/OBJ/STL), give them a product-shot finish, render turntable / zoom / dolly / crane / seamless-loop videos and stills, export GLB, and generate a Three.js web viewer. Works headless (blender --background) with no addon, or live over the blender-mcp socket. Use when the user mentions Blender, 3D product videos, turntables, rendering a model, converting a 3D file, or showing a model on the web.
---

# Blender

Scripted control of the user's own Blender install. Nothing here needs pip, npm or a Blender
addon: `scripts/blender_cli.py` finds Blender, runs the `scripts/bpy/*.py` scripts headless, and
`scripts/encode_video.py` turns rendered frames into a video with ffmpeg.

Paths below are relative to this skill folder. Run scripts with `--help` first; they are black
boxes that print one `RESULT {...}` JSON line at the end. Read their source only when a
customised solution is really needed.

## 0. Check the environment (always first)

```bash
python3 scripts/blender_cli.py doctor
```

- `"blender": null` → Blender is not on PATH. Ask the user where it is, or set `BLENDER_PATH`.
  Never install Blender yourself.
- `"ffmpeg": null` → stills and GLB export still work; video encoding does not. Tell the user
  how to install ffmpeg (see `references/troubleshooting.md`) and continue with the rest.
- `live_socket.connected: true` → the user has Blender open with blender-mcp; see §4.
- This skill cannot run Blender inside a cloud sandbox that has no Blender. If `doctor` fails
  there, produce the exact commands for the user to run locally instead of pretending to render.

## 1. Standard pipeline: model file → product video

```bash
B="python3 scripts/blender_cli.py run"
# 1. import, centre, scale to 2 m, rest on the floor, save a working .blend
$B scripts/bpy/import_model.py -- --file product.glb --save work/scene.blend
# 2. glossy finish + 4-point studio lighting (studio | dramatic | soft | sunset)
$B scripts/bpy/product_polish.py --blend work/scene.blend -- --preset studio --save work/scene.blend
# 3. find the front: 4 quick stills, show them to the user, ask which is the front
$B scripts/bpy/camera_move.py --blend work/scene.blend -- --move preview --out work/preview
# 4. render the move (front-angle from step 3: front=0 right=90 back=180 left=270)
$B scripts/bpy/camera_move.py --blend work/scene.blend -- --move turntable --front-angle 90 \
     --out work/frames --duration 5 --fps 24
# 5. encode
python3 scripts/encode_video.py --frames work/frames --fps 24 --out work/turntable.mov
```

Move names: `turntable`, `perfect-loop`, `slow-zoom`, `dolly-rotate`, `crane`, `preview`.
Which to pick, and every parameter: `references/camera_moves.md`.

Output format rules (`encode_video.py` picks the codec from the extension):
- `.mov` ProRes 4444 with alpha for editors (default for "give me the video").
- `.webm` VP9 with alpha for websites. `.mp4` H.264, no alpha, for social / WhatsApp
  (pass `--bg "#ffffff"` to choose the backdrop). `.gif` for chat previews (`--width 720`).

Defaults: 1920x1080, 24 fps, 5 s, transparent background, EEVEE. Vertical: `--width 1080 --height 1920`.
Final-quality reflections: `--engine cycles --samples 128` (10x slower; preview with EEVEE first).

## 2. Other tasks

| Task | Command |
|------|---------|
| One hero still | `$B scripts/bpy/render_still.py --blend work/scene.blend -- --out shot.png --angle 30 --elevation 20` |
| Inspect a scene / .blend | `$B scripts/bpy/scene_info.py --blend file.blend` |
| Convert formats (glb/gltf/fbx/obj/usd) | `$B scripts/bpy/import_model.py -- --file in.fbx --size 0 --save w.blend` then `$B scripts/bpy/export_glb.py --blend w.blend -- --out out.glb --draco` |
| Web viewer for a GLB | `python3 scripts/threejs_viewer.py --glb out.glb --out viewer.html --embed` |
| Any one-off bpy tweak | `$B scripts/bpy/exec_snippet.py --blend w.blend -- --code "bpy.data.objects['Cube'].hide_render = True" --save w.blend` |
| Open the result in the Blender UI | `python3 scripts/blender_cli.py run --gui scripts/bpy/scene_info.py --blend w.blend` |

Writing a new bpy script: copy the header of any `scripts/bpy/*.py` (it imports `_common`), take
arguments after `--`, print `out({...})` at the end. `references/bpy_cheatsheet.md` has the
API snippets and the 3.6 / 4.x / 5.x differences that `_common.py` already absorbs (EEVEE enum,
Principled socket names, layered actions, OBJ/STL operators).

## 3. Working rules

- **Look at what you rendered.** Open the preview PNGs / a frame with the image reader before
  reporting success. Black frame, empty frame, clipped object and wrong front are all common and
  all visible.
- **Ask about the front and the hero detail**, do not guess: run `--move preview` and show the four
  images; for `slow-zoom` ask what to zoom into (logo, texture, clasp) and pass `--focus x,y,z`
  from `scene_info.py` bounds if needed.
- **Never overwrite the user's original .blend.** Save to a work file (`--save work/scene.blend`).
- **Long renders:** 120 frames at 1080p is 1 to 3 min in EEVEE, 10 to 30 min in Cycles. Run the
  render in the background, poll the frames folder for the expected count, then encode.
- **AI-generated models** (Meshy, Tripo, Hyper3D, Rodin): expect noisy normal/roughness maps.
  `product_polish.py` strips them by default; `--keep-maps` if the user wants the original look.
- **Scale:** `import_model.py --size 2` normalises any unit mess. Use `--size 0` only when the
  real-world size matters (architecture, CAD exports).
- State clearly what was rendered with which engine and resolution, and where the files are.

## 4. Live mode (Blender already open)

If `doctor` shows the socket connected, the same scripts run inside the open Blender:

```bash
python3 scripts/blender_cli.py scene-info
python3 scripts/blender_cli.py exec --file scripts/bpy/product_polish.py -- --preset dramatic
python3 scripts/blender_cli.py exec --code "import bpy; bpy.ops.mesh.primitive_cube_add()"
```

Socket calls time out at 120 s, so renders still go through headless mode on a saved copy.
Setup, protocol and limits: `references/blender_mcp.md`.

## 5. Getting a 3D model in the first place

This skill starts from a model file. When the user only has a photo:
- **Image to mesh services** (Meshy, Tripo, Hyper3D/Rodin) return a textured GLB that drops into
  step 1 above. They need the user's API key; call the API with curl, poll the task, download
  the GLB. Do not promise exact geometry: a single photo cannot show hidden sides.
- **Procedural Three.js instead of Blender**: when the deliverable is a code-only web model built
  from primitives (no mesh file at all), use the `img2threejs` skill
  (https://github.com/img2threejs/img2threejs) and skip Blender entirely. Its output can still be
  exported to GLB and brought here for rendering.
- The reference repository https://github.com/kevinbadi/blender-skills has Blender-MCP
  recipes for Meshy generation, PolyHaven HDRIs/textures, and Mixamo retargeting if the user
  asks for those specifically.

## References

- `references/camera_moves.md` — the six moves, triggers, parameters, timing rules
- `references/bpy_cheatsheet.md` — bpy snippets and version differences
- `references/blender_mcp.md` — live socket mode
- `references/troubleshooting.md` — symptom → fix

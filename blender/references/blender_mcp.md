# Live mode: driving an open Blender over the blender-mcp socket

Headless mode (`blender --background`) is the default in this skill because it needs nothing but
Blender installed. Use live mode when the user has Blender open and wants to watch changes happen,
tweak things by hand between steps, or when a scene is already open and unsaved.

## Setup (one time, on the user's machine)

1. Install the addon from https://github.com/ahujasid/blender-mcp
   (download `addon.py`, Blender: Edit > Preferences > Add-ons > Install, enable "Blender MCP").
2. In the 3D viewport press `N`, open the **BlenderMCP** tab, click **Connect to Claude**
   (this starts a TCP server on port 9876).
3. Optional: register the MCP server in Claude Code so `get_scene_info`, `execute_blender_code`,
   `get_viewport_screenshot` and the PolyHaven / Hyper3D / Sketchfab tools appear as MCP tools:
   ```bash
   claude mcp add blender -- uvx blender-mcp
   ```

## Talking to it without the MCP server

`scripts/blender_cli.py` speaks the addon's raw protocol, which is one JSON object per connection:

```json
{"type": "execute_code", "params": {"code": "import bpy\nprint(len(bpy.data.objects))"}}
```

```bash
python3 scripts/blender_cli.py doctor                                   # live_socket.connected ?
python3 scripts/blender_cli.py scene-info                                # JSON dump of the open scene
python3 scripts/blender_cli.py exec --code "import bpy; bpy.ops.mesh.primitive_cube_add()"
python3 scripts/blender_cli.py exec --file scripts/bpy/product_polish.py -- --preset dramatic
```

Every `scripts/bpy/*.py` script works in both modes: `exec --file` injects the arguments after
`--` into `sys.argv` the same way `blender --python script.py -- args` does. The `_common.py` import
works because the file path is known when sent with `--file`.

Other message types the addon understands: `get_scene_info`, `get_object_info` (`{"name": ...}`),
`get_viewport_screenshot` (`{"filepath": ..., "max_size": 800}`), plus the asset-provider calls.

## Rules for live mode

- The socket times out at 120 s. A full animation render takes longer. Either start the render
  with `--no-render` removed and poll the frames folder for the expected PNG count, or save the
  scene (`--save scene.blend`) and render it headless in a second terminal with
  `blender_cli.py run scripts/bpy/camera_move.py --blend scene.blend -- ...`.
- Grab `get_viewport_screenshot` (or `render_still.py` at low resolution) after a change and look
  at the image before claiming the change worked. The user sees the viewport; you do not.
- Do not call `bpy.ops.wm.save_mainfile()` on the user's open file unless they asked. Save to a
  new path.
- One connection per command. The addon processes commands on Blender's main thread, so a long
  snippet freezes the UI until it returns.

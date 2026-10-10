# Troubleshooting

**`blender_cli.py doctor` says `"blender": null`**
Blender is installed but not on PATH. Set `BLENDER_PATH` to the executable or pass `--blender`.
Typical locations: Windows `C:\Program Files\Blender Foundation\Blender 4.x\blender.exe`,
macOS `/Applications/Blender.app/Contents/MacOS/Blender`, Linux `/usr/bin/blender`, `/snap/bin/blender`.
On Windows, PowerShell may need the path quoted.

**Script prints nothing / no RESULT line**
Blender swallows Python exceptions into its own log. Re-run with `blender_cli.py run -v ...` and read
the traceback above the "Blender quit" line. Common causes: wrong `--file` path, running a script
that needs meshes on an empty scene (run `import_model.py` first), a `.blend` saved by a newer
Blender than the one installed.

**`Import failed: ... no module named io_scene_gltf2` or FBX**
The importer addon is disabled, usually because `--factory-startup` was used or the user disabled
it. Drop `--factory-startup`, or enable the addon in Edit > Preferences > Add-ons.

**Renders are black or empty**
No lights and no world: pass `--light studio` to `camera_move.py` / `render_still.py`, or run
`product_polish.py` first. With a transparent background and no object in frame the PNG is fully
transparent; open it on a dark checkerboard before concluding nothing rendered.

**Object is tiny or off-screen**
Imported at the wrong scale (mm vs m) or far from the origin. `import_model.py` centers and scales
to `--size 2` by default; if `--size 0` was used, re-import. The camera moves frame the bounding
box automatically only when the meshes are found: check `scene_info.py` output for `mesh_bounds`.

**Dotty, sparkly or noisy surfaces on an AI-generated model**
Normal and roughness maps from Meshy / Tripo style exports. `product_polish.py` strips them
(`--keep-maps` keeps them).

**Cycles on GPU fails ("CUDA error", "no device")**
`_common.configure_render` falls back to CPU automatically. Expect 5 to 10x longer renders; use
`--engine eevee` or lower `--samples`.

**EEVEE looks flat compared to Cycles**
Ray tracing is enabled when available (4.2+). Add `--engine cycles --samples 128` for the final
render only. Keep EEVEE for previews.

**Turntable speeds up and slows down**
Interpolation is Bezier. `camera_move.py` sets LINEAR; if you keyframed by hand, call
`_common.set_interpolation(obj, "LINEAR")`.

**Loop has a visible hitch**
Use `--move perfect-loop`, not `turntable`: turntable renders frame 1 and frame 120 at the same
angle, which duplicates a frame when looped.

**Video has a black background instead of transparent**
`.mp4` cannot carry alpha. Use `.mov` (ProRes 4444) for editing or `.webm` (VP9) for the web, and
check `--opaque` was not passed to the render.

**Blender socket: "Cannot reach Blender on localhost:9876"**
Blender is not open, the blender-mcp addon is not enabled, or "Connect to Claude" was not clicked.
The socket only listens on the machine where Blender runs; a cloud/remote session cannot reach a
desktop Blender. Use headless mode there, or have the user run the commands locally.

**`ffmpeg not found`**
Windows `winget install ffmpeg`, macOS `brew install ffmpeg`, Debian/Ubuntu `sudo apt install ffmpeg`.

**Viewer HTML shows a blank page**
Opened via `file://`, so the browser blocked the GLB fetch. Either `python3 -m http.server` in the
folder and open `http://localhost:8000/viewer.html`, or regenerate with `--embed`.

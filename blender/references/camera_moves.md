# Camera moves

All moves are produced by `scripts/bpy/camera_move.py` and rendered to a PNG sequence
(`0001.png ...`) that `scripts/encode_video.py` turns into a video. Every move orbits or
aims at the bounding-box centre of the meshes in the scene (or of `--target NAME`), and the
default distance is computed from the object's size so a 2 cm ring and a 2 m sofa both fill
about 60% of the frame.

| Move | Trigger words | What happens | Loops? |
|------|---------------|--------------|--------|
| `turntable` | spin, rotate around, orbit, 360, showcase all angles | Camera orbits the object once at constant speed. | Nearly (last frame = first frame) |
| `perfect-loop` | seamless, infinite loop, GIF, web background | Same orbit, but the 360 keyframe sits one frame past the end so frame N leads into frame 1 with no duplicated pose. | Yes, seamless |
| `slow-zoom` | zoom in, push in, close-up on the logo, reveal, hero shot | Wide shot eases into a tight close-up; focal length ramps (35 to 65 mm style) for a cinematic compression. `--focus x,y,z` aims the end of the move at a detail. | No |
| `dolly-rotate` | dolly, sweep, move and rotate, dynamic | Camera moves in while the orbit rotates `--rotation` degrees (default 90). | No |
| `crane` | crane, rise up, low to high, unveil, pedestal | Starts below the object looking up, rises above it and pulls back. | No |
| `preview` | which side is the front? | Renders four 640x360 stills (front/right/back/left) so the user can pick the front. | n/a |

## Picking the front

Imported models rarely face -Y, which is the orbit start. Run `preview` first, show the four
images, ask the user which one is the front, then pass `--front-angle 0|90|180|270` to the
real move. Do not guess the front from the file name.

## Duration and framing defaults

- 5 seconds at 24 fps (120 frames) is the default; social loops often want 3 to 4 s.
- 1920x1080 landscape by default. Vertical video: `--width 1080 --height 1920`.
- Transparent background (`film_transparent`) is on by default; `--opaque` turns it off.
- Lens 50 mm. Wider (35) exaggerates depth, longer (85) flattens and looks premium.

## Timing

- Orbits use LINEAR interpolation (constant speed). Blender's default Bezier would make the
  spin slow at the start and end, which reads as a mistake.
- Zoom, dolly and crane use Bezier EASE_IN_OUT so the camera settles instead of stopping dead.

## Headless rendering time

EEVEE: a 120-frame 1080p turntable takes roughly 1 to 3 minutes on a laptop GPU.
Cycles at 64 samples with denoising: 10 to 30 minutes. Start with EEVEE; switch to
`--engine cycles` only when the user wants true reflections or glass.

If you are driving a live Blender over the socket instead of headless, the socket call times
out long before a render finishes. Kick off the render, then poll the frames folder until the
expected number of PNGs exist (see `blender_mcp.md`).

# Claude Code skills

A collection of [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) for
Claude Code. Each top-level folder is one skill with a `SKILL.md`, runnable `scripts/`, and
`references/` that are loaded only when needed.

| Skill | What it does |
|-------|--------------|
| [`blender/`](blender/SKILL.md) | Drive a local Blender install headless: import GLB/FBX/OBJ/STL, product-shot polish, turntable / zoom / dolly / crane / seamless-loop renders, stills, GLB export, Three.js web viewer. Also works against an open Blender via the blender-mcp socket. |

## Install

Copy or symlink a skill folder into one of:

```
~/.claude/skills/<skill>/           # all projects
<project>/.claude/skills/<skill>/   # one project
```

```bash
git clone https://github.com/harshX0011/Video-Download-Skill.git
ln -s "$(pwd)/Video-Download-Skill/blender" ~/.claude/skills/blender
```

Then just ask: "make a turntable video of product.glb", "render a hero shot of this model",
"export this .blend as GLB and give me a web viewer".

## Requirements (blender skill)

- Blender 3.6 LTS, 4.x or 5.x installed (https://www.blender.org). Not on PATH? Set `BLENDER_PATH`.
- Python 3.8+ (the launcher and encoder are stdlib only).
- ffmpeg for video encoding (`winget install ffmpeg` / `brew install ffmpeg` / `apt install ffmpeg`).
- Optional: [blender-mcp](https://github.com/ahujasid/blender-mcp) addon for live control of an open Blender.

Quick check:

```bash
python3 blender/scripts/blender_cli.py doctor
```

## Credits

The Blender skill borrows camera-move recipes, the product-polish look and the Three.js viewer
layout from [kevinbadi/blender-skills](https://github.com/kevinbadi/blender-skills), and its
script-as-black-box, print-one-result-line structure from
[img2threejs/img2threejs](https://github.com/img2threejs/img2threejs).

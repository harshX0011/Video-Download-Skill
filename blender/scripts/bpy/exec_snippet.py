"""Run an arbitrary bpy snippet inside a .blend headlessly and optionally save.

  blender -b scene.blend --python exec_snippet.py -- --code "bpy.data.objects['Cube'].scale = (2,2,2)" --save scene.blend
  blender -b scene.blend --python exec_snippet.py -- --file my_snippet.py --save scene.blend

Handy for one-off tweaks without writing a full script.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *  # noqa

p = argparse.ArgumentParser()
p.add_argument("--code")
p.add_argument("--file")
p.add_argument("--save")
a = parse(p)

src = open(a.file, encoding="utf-8").read() if a.file else (a.code or "")
if not src:
    raise SystemExit("--code or --file required")
ns = {"bpy": bpy, "math": math, "Vector": Vector}
exec(compile(src, a.file or "<code>", "exec"), ns)
saved = save_blend(a.save)
out({"ok": True, "saved": saved})

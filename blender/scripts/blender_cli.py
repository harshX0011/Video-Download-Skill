#!/usr/bin/env python3
"""
blender_cli.py - find Blender, run bpy scripts headless, or talk to a live Blender.

Pure Python 3.8+ stdlib. No pip installs.

Commands
--------
  doctor                      Report Blender / ffmpeg / live-socket status as JSON.
  find                        Print the Blender executable path (exit 1 if not found).
  run <script.py> [options]   Run a bpy script in headless Blender (blender --background).
  exec (--code | --file)      Send Python to a running Blender via the blender-mcp socket.
  scene-info                  Shortcut: dump the open live scene as JSON (socket mode).

Examples
--------
  python3 blender_cli.py doctor
  python3 blender_cli.py run scripts/bpy/import_model.py -- --file model.glb --save out.blend
  python3 blender_cli.py run scripts/bpy/camera_move.py --blend out.blend -- --move turntable --out frames/
  python3 blender_cli.py exec --code "import bpy; print(len(bpy.data.objects))"
  python3 blender_cli.py exec --file scripts/bpy/scene_info.py

Blender location is resolved in this order:
  1. --blender <path>            2. $BLENDER_PATH            3. `blender` on PATH
  4. well-known install folders for Windows / macOS / Linux (newest version wins)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
from typing import List, Optional

DEFAULT_SOCKET_PORT = 9876  # blender-mcp addon default (ahujasid/blender-mcp)


# ---------------------------------------------------------------------------
# Locate Blender
# ---------------------------------------------------------------------------
def _version_key(path: str):
    m = re.search(r"(\d+)\.(\d+)", path)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def candidate_paths() -> List[str]:
    system = platform.system()
    pats: List[str] = []
    if system == "Windows":
        for root in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                     os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                     os.environ.get("LOCALAPPDATA", "")):
            if root:
                pats.append(os.path.join(root, "Blender Foundation", "Blender*", "blender.exe"))
        # Steam / Microsoft Store style installs
        pats.append(r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe")
        pats.append(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Blender*", "blender.exe"))
    elif system == "Darwin":
        pats.append("/Applications/Blender.app/Contents/MacOS/Blender")
        pats.append("/Applications/Blender*/Blender.app/Contents/MacOS/Blender")
        pats.append(os.path.expanduser("~/Applications/Blender*.app/Contents/MacOS/Blender"))
    else:
        pats += ["/usr/bin/blender", "/usr/local/bin/blender", "/snap/bin/blender",
                 "/opt/blender*/blender", os.path.expanduser("~/blender*/blender"),
                 os.path.expanduser("~/Applications/blender*/blender"),
                 "/var/lib/flatpak/exports/bin/org.blender.Blender",
                 os.path.expanduser("~/.local/share/flatpak/exports/bin/org.blender.Blender")]
    found: List[str] = []
    for p in pats:
        found.extend(glob.glob(p))
    found = [f for f in found if os.path.isfile(f) and os.access(f, os.X_OK)]
    return sorted(set(found), key=_version_key, reverse=True)


def find_blender(explicit: Optional[str] = None) -> Optional[str]:
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    env = os.environ.get("BLENDER_PATH")
    if env and os.path.isfile(env):
        return env
    on_path = shutil.which("blender") or shutil.which("Blender")
    if on_path:
        return on_path
    cands = candidate_paths()
    return cands[0] if cands else None


def blender_version(exe: str) -> Optional[str]:
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60).stdout
        m = re.search(r"Blender\s+(\d+\.\d+(?:\.\d+)?)", out)
        return m.group(1) if m else out.strip().splitlines()[0]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Headless run
# ---------------------------------------------------------------------------
def cmd_run(a: argparse.Namespace) -> int:
    exe = find_blender(a.blender)
    if not exe:
        print("Blender not found. Install it from https://www.blender.org or set BLENDER_PATH.", file=sys.stderr)
        return 2
    script = os.path.abspath(a.script)
    if not os.path.isfile(script):
        print(f"Script not found: {script}", file=sys.stderr)
        return 2
    cmd = [exe]
    if not a.gui:
        cmd.append("--background")
    if a.factory_startup:
        cmd.append("--factory-startup")
    if a.blend:
        cmd.append(os.path.abspath(a.blend))
    cmd += ["--python", script]
    if a.script_args:
        cmd += ["--"] + a.script_args
    if a.verbose:
        print("$ " + " ".join(cmd), file=sys.stderr)
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        return 130


# ---------------------------------------------------------------------------
# Live socket (blender-mcp addon)
# ---------------------------------------------------------------------------
def socket_send(payload: dict, host: str = "localhost", port: int = DEFAULT_SOCKET_PORT,
                timeout: float = 120.0) -> dict:
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall(json.dumps(payload).encode("utf-8"))
        buf = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
            try:
                return json.loads(buf.decode("utf-8"))
            except json.JSONDecodeError:
                continue
    if buf:
        return json.loads(buf.decode("utf-8"))
    raise RuntimeError("empty response from Blender socket")


def socket_alive(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


def cmd_exec(a: argparse.Namespace) -> int:
    if a.file:
        with open(a.file, "r", encoding="utf-8") as fh:
            code = fh.read()
        # The addon exec()s the string, so __file__ is undefined there; define it so the
        # bpy scripts can find _common.py next to themselves.
        code = "__file__ = %r\n" % os.path.abspath(a.file) + code
    elif a.code:
        code = a.code
    else:
        print("exec needs --code or --file", file=sys.stderr)
        return 2
    if a.script_args:
        # Expose args to the script the same way headless mode does (after "--").
        code = "import sys\nsys.argv = ['blender', '--'] + %r\n" % a.script_args + code
    try:
        res = socket_send({"type": "execute_code", "params": {"code": code}}, a.host, a.port, a.timeout)
    except OSError as e:
        print(f"Cannot reach Blender on {a.host}:{a.port} ({e}). "
              "Open Blender, press N, BlenderMCP tab, 'Connect to Claude' / start server.", file=sys.stderr)
        return 3
    print(json.dumps(res, indent=2) if a.json else _pretty(res))
    return 0 if res.get("status") != "error" else 1


def _pretty(res: dict) -> str:
    if res.get("status") == "error":
        return "ERROR: " + str(res.get("message"))
    r = res.get("result")
    if isinstance(r, dict) and "result" in r:
        return str(r["result"]).rstrip()
    return json.dumps(r, indent=2) if isinstance(r, (dict, list)) else str(r)


# ---------------------------------------------------------------------------
# doctor / find
# ---------------------------------------------------------------------------
def cmd_doctor(a: argparse.Namespace) -> int:
    exe = find_blender(a.blender)
    info = {
        "platform": platform.system(),
        "blender": exe,
        "blender_version": blender_version(exe) if exe else None,
        "other_blender_installs": [c for c in candidate_paths() if c != exe],
        "ffmpeg": shutil.which("ffmpeg"),
        "live_socket": {"host": a.host, "port": a.port, "connected": socket_alive(a.host, a.port)},
        "ready_headless": bool(exe),
    }
    print(json.dumps(info, indent=2))
    return 0 if exe else 1


def cmd_find(a: argparse.Namespace) -> int:
    exe = find_blender(a.blender)
    if exe:
        print(exe)
        return 0
    print("not found", file=sys.stderr)
    return 1


def cmd_scene_info(a: argparse.Namespace) -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    a.file = os.path.join(here, "bpy", "scene_info.py")
    a.code = None
    a.json = False
    a.script_args = []
    return cmd_exec(a)


# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--blender", help="explicit path to the Blender executable")
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=DEFAULT_SOCKET_PORT, help="blender-mcp socket port")
    p.add_argument("--timeout", type=float, default=120.0, help="socket timeout in seconds")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="environment check").set_defaults(fn=cmd_doctor)
    sub.add_parser("find", help="print Blender path").set_defaults(fn=cmd_find)

    r = sub.add_parser("run", help="run a bpy script headless")
    r.add_argument("script")
    r.add_argument("--blend", help=".blend file to open first")
    r.add_argument("--gui", action="store_true", help="open the Blender UI instead of --background")
    r.add_argument("--factory-startup", action="store_true")
    r.add_argument("-v", "--verbose", action="store_true")
    r.add_argument("script_args", nargs=argparse.REMAINDER, help="args for the script, after --")
    r.set_defaults(fn=cmd_run)

    e = sub.add_parser("exec", help="send code to a running Blender (socket)")
    e.add_argument("--code")
    e.add_argument("--file")
    e.add_argument("--json", action="store_true", help="print raw JSON response")
    e.add_argument("script_args", nargs=argparse.REMAINDER)
    e.set_defaults(fn=cmd_exec)

    sub.add_parser("scene-info", help="dump live scene as JSON").set_defaults(fn=cmd_scene_info)

    a = p.parse_args(argv)
    # strip a leading "--" that argparse.REMAINDER keeps
    if getattr(a, "script_args", None) and a.script_args[0] == "--":
        a.script_args = a.script_args[1:]
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
encode_video.py - turn a rendered PNG frame sequence into a video with ffmpeg.

  python3 encode_video.py --frames frames/ --fps 24 --out turntable.mov
  python3 encode_video.py --frames frames/ --out turntable.mp4 --bg "#111111"
  python3 encode_video.py --frames frames/ --out loop.webm
  python3 encode_video.py --frames frames/ --out loop.gif --width 720

Output container decides the codec:
  .mov   ProRes 4444 with alpha (transparent background preserved). Big files, edit-ready.
  .webm  VP9 with alpha. Small, plays in Chrome/Firefox with transparency.
  .mp4   H.264, no alpha. Transparent frames are composited on --bg (default black).
  .gif   palette-optimised GIF (use --width to shrink). Alpha becomes --bg.

Options
  --frames DIR     folder with 0001.png ... (from camera_move.py)      [required]
  --pattern        frame pattern inside DIR (default %04d.png)
  --fps 24
  --out FILE       output path                                         [required]
  --bg "#000000"   background colour for formats without alpha
  --width W        scale to this width (keeps aspect)
  --crf 18         quality for mp4/webm (lower = better)
  --loop N         repeat the sequence N extra times (for social loops)
"""
import argparse
import os
import shutil
import subprocess
import sys


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--frames", required=True)
    p.add_argument("--pattern", default="%04d.png")
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--out", required=True)
    p.add_argument("--bg", default="#000000")
    p.add_argument("--width", type=int)
    p.add_argument("--crf", type=int, default=18)
    p.add_argument("--loop", type=int, default=0)
    p.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    a = p.parse_args()

    if not a.ffmpeg:
        print("ffmpeg not found. Install: https://ffmpeg.org/download.html "
              "(Windows: winget install ffmpeg | macOS: brew install ffmpeg | Debian: apt install ffmpeg)",
              file=sys.stderr)
        return 2
    frames = os.path.abspath(a.frames)
    pngs = sorted(f for f in os.listdir(frames) if f.lower().endswith(".png")) if os.path.isdir(frames) else []
    if not pngs:
        print(f"no PNG frames in {frames}", file=sys.stderr)
        return 2
    first_num = int(os.path.splitext(pngs[0])[0]) if pngs[0][:-4].isdigit() else 1
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    ext = os.path.splitext(out)[1].lower()
    bg = a.bg.lstrip("#")

    cmd = [a.ffmpeg, "-y", "-framerate", str(a.fps), "-start_number", str(first_num)]
    if a.loop:
        cmd += ["-stream_loop", str(a.loop)]
    cmd += ["-i", os.path.join(frames, a.pattern)]

    vf = []
    if a.width:
        vf.append(f"scale={a.width}:-2:flags=lanczos")

    if ext == ".mov":
        cmd += ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"]
    elif ext == ".webm":
        cmd += ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-crf", str(a.crf), "-b:v", "0",
                "-auto-alt-ref", "0"]
    elif ext == ".mp4":
        # Composite alpha over a solid colour, force even dimensions, then H.264.
        scale = f",scale={a.width}:-2:flags=lanczos" if a.width else ""
        cmd += ["-filter_complex",
                f"[0:v]format=rgba{scale},pad=ceil(iw/2)*2:ceil(ih/2)*2[fg];"
                f"color=c=0x{bg}:s=16x16[c];[c][fg]scale2ref[c2][fg2];"
                f"[c2][fg2]overlay=shortest=1,format=yuv420p[v]",
                "-map", "[v]", "-c:v", "libx264", "-crf", str(a.crf), "-preset", "slow",
                "-movflags", "+faststart"]
        vf = []
    elif ext == ".gif":
        scale = f",scale={a.width}:-2:flags=lanczos" if a.width else ""
        cmd += ["-filter_complex",
                f"[0:v]format=rgba{scale}[fg];color=c=0x{bg}:s=16x16[c];[c][fg]scale2ref[c2][fg2];"
                f"[c2][fg2]overlay=shortest=1,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse[v]",
                "-map", "[v]", "-loop", "0"]
        vf = []
    else:
        print(f"unsupported output: {ext} (use .mov .webm .mp4 .gif)", file=sys.stderr)
        return 2

    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd.append(out)
    print("$ " + " ".join(cmd), file=sys.stderr)
    rc = subprocess.call(cmd)
    if rc == 0:
        mb = os.path.getsize(out) / (1024 * 1024)
        print(f"RESULT {{\"file\": \"{out}\", \"frames\": {len(pngs)}, \"fps\": {a.fps}, \"size_mb\": {mb:.2f}}}")
    return rc


if __name__ == "__main__":
    sys.exit(main())

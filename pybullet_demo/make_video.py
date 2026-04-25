"""
Stitch frame_*.png files into an animated GIF and optionally an MP4.

Usage:
    # GIF only (no extra deps):
    python pybullet_demo/make_video.py --dir pybullet_demo/frames --out demo.gif

    # MP4 via imageio[ffmpeg] (pip install imageio[ffmpeg]):
    python pybullet_demo/make_video.py --dir pybullet_demo/frames --out demo.mp4

    # Compare two model dirs side-by-side GIF:
    python pybullet_demo/make_video.py \
        --dir pybullet_demo/frames/M1 pybullet_demo/frames/Mstar \
        --out compare_M1_vs_M4star.gif --side-by-side
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def collect_frames(directory: str) -> list[Path]:
    d = Path(directory)
    frames = sorted(d.glob("frame_*.png"))
    if not frames:
        raise FileNotFoundError(f"No frame_*.png files found in {directory}")
    return frames


def make_gif(
    frame_paths: list[Path],
    out_path: str,
    fps: int = 20,
    scale: float = 0.5,
    label: str = "",
) -> None:
    images = []
    for p in frame_paths:
        img = Image.open(p).convert("RGBA")
        if scale != 1.0:
            w, h = img.size
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        if label:
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), label, fill=(255, 255, 255, 220))
        images.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))

    duration_ms = int(1000 / fps)
    images[0].save(
        out_path,
        save_all=True,
        append_images=images[1:],
        loop=0,
        duration=duration_ms,
        optimize=False,
    )
    print(f"GIF saved -> {out_path}  ({len(images)} frames @ {fps} fps)")


def make_side_by_side_gif(
    left_frames: list[Path],
    right_frames: list[Path],
    out_path: str,
    left_label: str = "M1 (random)",
    right_label: str = "M4* (auction+chain)",
    fps: int = 20,
    scale: float = 0.5,
) -> None:
    n = min(len(left_frames), len(right_frames))
    images = []
    for i in range(n):
        L = Image.open(left_frames[i]).convert("RGB")
        R = Image.open(right_frames[i]).convert("RGB")
        if scale != 1.0:
            w, h = L.size
            L = L.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            w, h = R.size
            R = R.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        # Pad to same height
        max_h = max(L.height, R.height)
        if L.height < max_h:
            pad = Image.new("RGB", (L.width, max_h), (20, 20, 20))
            pad.paste(L, (0, (max_h - L.height) // 2))
            L = pad
        if R.height < max_h:
            pad = Image.new("RGB", (R.width, max_h), (20, 20, 20))
            pad.paste(R, (0, (max_h - R.height) // 2))
            R = pad

        combo = Image.new("RGB", (L.width + R.width + 4, max_h), (40, 40, 40))
        combo.paste(L, (0, 0))
        combo.paste(R, (L.width + 4, 0))

        draw = ImageDraw.Draw(combo)
        draw.text((8, 8), left_label, fill=(255, 100, 100))
        draw.text((L.width + 12, 8), right_label, fill=(100, 200, 255))

        images.append(combo.convert("P", palette=Image.ADAPTIVE, colors=256))

    duration_ms = int(1000 / fps)
    images[0].save(
        out_path,
        save_all=True,
        append_images=images[1:],
        loop=0,
        duration=duration_ms,
        optimize=False,
    )
    print(f"Side-by-side GIF saved -> {out_path}  ({n} frames @ {fps} fps)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", nargs="+", required=True,
                    help="Frame directory/directories. Two dirs → side-by-side.")
    ap.add_argument("--out", default="demo.gif")
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--scale", type=float, default=0.5,
                    help="Resize factor (default 0.5 = half size)")
    ap.add_argument("--side-by-side", action="store_true")
    ap.add_argument("--left-label", default="M1 (random)")
    ap.add_argument("--right-label", default="M4* (auction+chain)")
    args = ap.parse_args()

    if args.side_by_side or len(args.dir) == 2:
        if len(args.dir) != 2:
            ap.error("--side-by-side requires exactly 2 --dir paths")
        left = collect_frames(args.dir[0])
        right = collect_frames(args.dir[1])
        make_side_by_side_gif(
            left, right, args.out,
            left_label=args.left_label,
            right_label=args.right_label,
            fps=args.fps, scale=args.scale,
        )
    else:
        frames = collect_frames(args.dir[0])
        make_gif(frames, args.out, fps=args.fps, scale=args.scale)


if __name__ == "__main__":
    main()

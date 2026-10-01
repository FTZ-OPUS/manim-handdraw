#!/usr/bin/env python3
"""Extract a faithful transparent ink patch from an aligned pencil drawing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def make_patch(pencil_path: Path, output: Path, box: tuple[int, int, int, int], *,
               scene_height: float = 7.3, scene_center: tuple[float, float] = (0, 0),
               dark: float = 100, light: float = 205, feather: float = 0.12,
               ink: str = "#23140F") -> dict:
    with Image.open(pencil_path) as source:
        gray = np.asarray(source.convert("L"))
        width, height = source.size
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError("box must be x0 y0 x1 y1 in aligned pencil pixels; end is exclusive")
    if not (0 <= dark < light <= 255 and 0 <= feather < 0.5 and scene_height > 0):
        raise ValueError("require 0 <= dark < light <= 255, 0 <= feather < 0.5, height > 0")
    if len(ink) != 7 or not ink.startswith("#"):
        raise ValueError("ink must be a six-digit colour such as #23140F")
    rgb = tuple(int(ink[i:i + 2], 16) for i in (1, 3, 5))

    crop = gray[y0:y1, x0:x1].astype(float)
    opacity = np.clip((light - crop) / (light - dark), 0, 1)
    h, w = crop.shape
    if feather:
        yy, xx = np.mgrid[:h, :w]
        x_distance = np.minimum(xx + 1, w - xx) / max(1.0, feather * w)
        y_distance = np.minimum(yy + 1, h - yy) / max(1.0, feather * h)
        opacity *= np.minimum(1.0, np.minimum(x_distance, y_distance))
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = np.rint(opacity * 255).astype(np.uint8)
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(output)

    scale = scene_height / height
    cx, cy = scene_center
    placement = {
        "source": pencil_path.name,
        "patch": output.name,
        "pixel_box_xyxy_exclusive": list(box),
        "manim_center": [cx + ((x0 + x1) / 2 - width / 2) * scale,
                         cy - ((y0 + y1) / 2 - height / 2) * scale],
        "manim_height": h * scale,
        "cut_window_xy_bottom_top": [cx + (x0 - width / 2) * scale,
                                      cx + (x1 - width / 2) * scale,
                                      cy - (y1 - height / 2) * scale,
                                      cy - (y0 - height / 2) * scale],
    }
    output.with_suffix(".placement.json").write_text(
        json.dumps(placement, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return placement


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pencil", required=True, type=Path,
                        help="pencil_aligned.png from prepare_pair.py")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--box", nargs=4, type=int, required=True,
                        metavar=("X0", "Y0", "X1", "Y1"))
    parser.add_argument("--scene-height", type=float, default=7.3)
    parser.add_argument("--scene-center", nargs=2, type=float, default=(0.0, 0.0),
                        metavar=("X", "Y"))
    parser.add_argument("--dark", type=float, default=100)
    parser.add_argument("--light", type=float, default=205)
    parser.add_argument("--feather", type=float, default=0.12)
    parser.add_argument("--ink", default="#23140F")
    args = parser.parse_args()
    placement = make_patch(args.pencil, args.output, tuple(args.box),
                           scene_height=args.scene_height,
                           scene_center=tuple(args.scene_center),
                           dark=args.dark, light=args.light,
                           feather=args.feather, ink=args.ink)
    print(json.dumps(placement, ensure_ascii=False, indent=2))
    print("Check this patch over a paper-coloured background; do not judge transparency on black.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Prepare matching pencil and colour references for a hand-drawn scene."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def prepare(pencil_path: Path, color_path: Path, output: Path, *,
            threshold: int = 150, scale: float = 1.0,
            aspect_tolerance: float = 0.02) -> dict:
    if not 1 <= threshold <= 254:
        raise ValueError("threshold must be between 1 and 254")
    if not 0 < scale <= 1:
        raise ValueError("scale must be in (0, 1]")

    with Image.open(pencil_path) as source:
        pencil = source.convert("RGB")
    with Image.open(color_path) as source:
        color = source.convert("RGB")
    pencil_ratio = pencil.width / pencil.height
    color_ratio = color.width / color.height
    aspect_error = abs(color_ratio / pencil_ratio - 1)
    if aspect_error > aspect_tolerance:
        raise ValueError(
            f"aspect ratios differ by {aspect_error:.1%}; align/crop the same composition first"
        )

    width = max(1, round(pencil.width * scale))
    height = max(1, round(pencil.height * scale))
    frame = (width, height)
    pencil = pencil.resize(frame, Image.Resampling.LANCZOS)
    color = color.resize(frame, Image.Resampling.LANCZOS)
    output.mkdir(parents=True, exist_ok=True)
    pencil.save(output / "pencil_aligned.png")
    color.save(output / "color_aligned.png")
    color.save(output / "full.png")

    gray = np.asarray(pencil.convert("L"))
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[..., :3] = (35, 20, 15)
    rgba[..., 3] = np.where(gray < threshold, 255, 0).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(output / "lineart.png")

    check = Image.new("RGB", (width * 3, height))
    check.paste(pencil, (0, 0))
    check.paste(color, (width, 0))
    check.paste(Image.blend(pencil, color, 0.5), (width * 2, 0))
    check.save(output / "alignment_check.png")

    manifest = {
        "pencil_input": pencil_path.name,
        "color_input": color_path.name,
        "width": width,
        "height": height,
        "scale": scale,
        "lineart_threshold": threshold,
        "aspect_error_fraction": round(aspect_error, 6),
        "alignment_check": "left=pencil; middle=color; right=50% blend; visually verify features align",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pencil", required=True, type=Path,
                        help="Original pencil drawing; source of strokes and facial features")
    parser.add_argument("--color", required=True, type=Path,
                        help="Matching colour reference; source of colour layers and final image")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--threshold", type=int, default=150)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--aspect-tolerance", type=float, default=0.02)
    args = parser.parse_args()
    result = prepare(args.pencil, args.color, args.output,
                     threshold=args.threshold, scale=args.scale,
                     aspect_tolerance=args.aspect_tolerance)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("Inspect alignment_check.png and lineart.png before extracting strokes.")


if __name__ == "__main__":
    main()

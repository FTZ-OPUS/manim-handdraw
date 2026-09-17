"""上色：把成品图切成竖条，一条条扫进去。

整层淡入会显得"啪"地一下突变；切成窄条依次浮现，看起来就像水彩一段段
浸润过去。切条用精确边界（而不是取整），否则相邻条之间会留下约 1 像素的
错位缝隙，在角色身上就是一条竖线。
"""

from __future__ import annotations

import json
import os

import numpy as np

__all__ = ["strip_bounds", "split_strips", "strip_group", "sweep_color"]

DEFAULT_LAYOUT = "strip_layout.json"


def strip_bounds(width, n=7):
    """把宽度 ``width`` 均分成 ``n`` 段，返回 ``n+1`` 个精确边界（像素）。"""
    return [round(i * width / n) for i in range(n + 1)]


def split_strips(image_path, n=7, *, out_dir=None, save=True, verbose=False):
    """把一张图竖切成 ``n`` 条，返回布局表 ``{image: [[x0, x1], ...]}``（像素）。

    ``out_dir`` 为 ``None`` 时切到 ``<image>_strips/`` 目录下。
    """
    from PIL import Image

    src = Image.open(image_path).convert("RGBA")
    w, h = src.width, src.height
    if out_dir is None:
        out_dir = os.path.splitext(image_path)[0] + "_strips"
    os.makedirs(out_dir, exist_ok=True)
    bounds = strip_bounds(w, n)
    spans = []
    for i in range(n):
        x0, x1 = bounds[i], bounds[i + 1]
        if save:
            src.crop((x0, 0, x1, h)).save(os.path.join(out_dir, f"s{i}.png"))
        spans.append([x0, x1])
    if verbose:
        print(f"[manim-handdraw] {os.path.basename(image_path)} -> {out_dir} "
              f"({n} 条，宽度 {[b - a for a, b in zip(bounds[:-1], bounds[1:])]})")
    return spans


def _layout_path(image_path):
    return os.path.join(os.path.dirname(os.path.abspath(image_path)), DEFAULT_LAYOUT)


def strip_group(image_path, *, n=7, size=7.0, center=(0.0, 0.0), fit="height",
                z_index=None, use_cache=True, verbose=False):
    """读（或生成）竖条，摆成一组 ``Group``。

    摆放位置由每条在原图中的精确像素区间换算而来，因此相邻条之间严丝合缝。

    Returns
    -------
    (group, spans)
    """
    from manim import Group, ImageMobject

    from .geometry import px_to_manim

    from PIL import Image

    layout_file = _layout_path(image_path)
    spans = None
    if use_cache and os.path.exists(layout_file):
        try:
            with open(layout_file) as f:
                spans = json.load(f).get(os.path.basename(image_path))
        except Exception:
            spans = None
    if spans is None or len(spans) != n:
        spans = split_strips(image_path, n, verbose=verbose)
        if use_cache:
            data = {}
            if os.path.exists(layout_file):
                try:
                    with open(layout_file) as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data[os.path.basename(image_path)] = spans
            try:
                with open(layout_file, "w") as f:
                    json.dump(data, f, indent=1)
            except Exception:
                pass

    with Image.open(image_path) as im:
        W, H = im.width, im.height

    strip_dir = os.path.splitext(image_path)[0] + "_strips"
    group = Group()
    for i, (x0, x1) in enumerate(spans):
        p = os.path.join(strip_dir, f"s{i}.png")
        if not os.path.exists(p):
            split_strips(image_path, n, verbose=False)
        img = ImageMobject(p)
        img.scale_to_fit_height(size)
        # 用精确区间换算出的宽度，抹掉切条取整带来的误差
        mx0, _ = px_to_manim(x0, 0, width=W, height=H, fit=fit, size=size, center=center)
        mx1, _ = px_to_manim(x1, 0, width=W, height=H, fit=fit, size=size, center=center)
        img.set(width=abs(mx1 - mx0))
        img.move_to([(mx0 + mx1) / 2.0, center[1], 0.0])
        if z_index is not None:
            img.set_z_index(z_index)
        group.add(img)
    return group, spans


def sweep_color(scene, image_path, *, n=7, size=7.0, center=(0.0, 0.0), fit="height",
                run_time=3.2, lag_ratio=0.28, shift=0.05, z_index=None,
                fade_out=(), verbose=False):
    """依次扫入一张成品图的各个竖条。

    返回 ``(animation_group, mobject_group)``：前者用来 ``self.play(...)``，
    后者留着以便后续整体淡出。

    ``fade_out`` 传入需要同时淡出的其它 mobject（比如上一层颜色），
    省得自己再拼一次 ``self.play``。
    """
    from manim import FadeIn, LaggedStart, UP

    group, _ = strip_group(image_path, n=n, size=size, center=center, fit=fit,
                           z_index=z_index, verbose=verbose)
    anim = LaggedStart(
        *[FadeIn(s, shift=UP * shift) for s in group],
        lag_ratio=lag_ratio, run_time=run_time,
    )
    return anim, group

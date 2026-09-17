"""manim-handdraw —— 把一张线稿图变成逐笔手绘动画。

快速开始::

    from manim import *
    import manim_handdraw as hd

    class Demo(hd.HandDrawScene):
        def construct(self):
            self.hand_draw("lineart.png", color="color.png")

只想要零件::

    strokes = hd.from_image("lineart.png")        # 抽取笔画（需 [extract] 依赖）
    stylus  = hd.Stylus()
    self.play(*stylus.draw_all(strokes))         # 逐笔生长

    self.play(hd.Compass(pivot, r).draw_circle())    # 圆规画圆
    self.play(*hd.trace_ellipse(c, a, b, tilt)["anims"])   # 参数方程构造椭圆

设计上刻意把重依赖（scikit-image / scipy / Pillow）挡在 ``from_image``
内部按需导入：Manim 插件在每次启动 manim 时都会导入本包，顶层引入这些库会
让所有 manim 命令都平白慢一截。
"""

from __future__ import annotations

__version__ = "0.1.0"

# ---- 轻量层：只依赖 manim + numpy -------------------------------------
from .geometry import (  # noqa: E402
    in_ellipse,
    manim_to_px,
    moment_ellipse,
    px_to_manim,
    ring_path,
    robust_circle_fit,
)
from .strokes import (  # noqa: E402
    StrokeSet,
    Stylus,
    draw_strokes,
    stroke_mobject,
)
from .shapes import (  # noqa: E402
    InkBlot,
    blot_fill,
    blot_grow,
    ellipse_outline,
    solid_from_path,
)
from .drafting import (  # noqa: E402
    Compass,
    arm_trace,
    construction_axes,
    construction_circle,
    sweep_circle,
    trace_ellipse,
)
from .coloring import (  # noqa: E402
    split_strips,
    strip_bounds,
    strip_group,
    sweep_color,
)
from .scene import (  # noqa: E402
    ACCENT,
    INK,
    MONO_FONT,
    MUTED,
    PAPER,
    TITLE_FONT,
    CanvasUI,
    HandDrawScene,
    tag_text,
)

__all__ = [
    "__version__",
    # geometry
    "px_to_manim", "manim_to_px", "ring_path", "in_ellipse",
    "moment_ellipse", "robust_circle_fit",
    # strokes
    "StrokeSet", "Stylus", "stroke_mobject", "draw_strokes",
    # shapes
    "InkBlot", "blot_fill", "blot_grow", "ellipse_outline", "solid_from_path",
    # drafting
    "Compass", "construction_circle", "construction_axes", "trace_ellipse",
    "arm_trace", "sweep_circle",
    # coloring
    "strip_bounds", "split_strips", "strip_group", "sweep_color",
    # scene
    "HandDrawScene", "CanvasUI", "tag_text",
    "PAPER", "INK", "MUTED", "ACCENT", "TITLE_FONT", "MONO_FONT",
    # 提取（延迟导入，见下）
    "from_image", "extract_strokes", "load_ink_mask", "find_solid_blobs",
]


# ---- 重依赖层：函数内延迟导入 ----------------------------------------
def from_image(*args, **kwargs):
    """从图片抽取笔画，返回 :class:`StrokeSet`（需要 ``manim-handdraw[extract]``）。"""
    from .extract import from_image as _impl
    return _impl(*args, **kwargs)


def extract_strokes(*args, **kwargs):
    """抽取笔画并返回原始字典（需要 ``manim-handdraw[extract]``）。"""
    from .extract import extract_strokes as _impl
    return _impl(*args, **kwargs)


def load_ink_mask(*args, **kwargs):
    """把线稿读成布尔掩膜（需要 ``manim-handdraw[extract]``）。"""
    from .extract import load_ink_mask as _impl
    return _impl(*args, **kwargs)


def find_solid_blobs(*args, **kwargs):
    """找出线稿中的实心墨块（需要 ``manim-handdraw[extract]``）。"""
    from .extract import find_solid_blobs as _impl
    return _impl(*args, **kwargs)


def __getattr__(name):
    """让 ``hd.extract`` / ``hd.drafting`` 等子模块可以懒加载访问。"""
    import importlib
    if name in {"extract", "geometry", "strokes", "shapes", "drafting",
                "coloring", "scene", "cli"}:
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

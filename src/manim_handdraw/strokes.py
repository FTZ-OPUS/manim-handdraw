"""笔画容器与"笔尖"——把一串坐标变成逐笔生长的动画。

对外最常用的两个东西：

    strokes = hd.from_image("lineart.png")     # 或 hd.StrokeSet.load(...)
    stylus  = hd.Stylus()
    self.play(*stylus.draw_all(strokes))       # 一句话画完

``Stylus`` 会沿笔画实时移动，让观众看见"正在画哪里"。
"""

from __future__ import annotations

import numpy as np
from manim import Create, Dot, Circle, Line, MoveAlongPath, VGroup, VMobject, linear

from .geometry import in_ellipse

__all__ = ["StrokeSet", "Stylus", "stroke_mobject", "draw_strokes"]

INK = "#23140F"
STYLUS = "#00B4D8"


def _as3d(pts):
    """补上 z 分量——Manim 的 ``move_to`` / ``Line`` 都要求三维点。"""
    pts = np.asarray(pts, float)
    if pts.ndim != 2 or pts.shape[1] == 3:
        return pts
    return np.concatenate([pts, np.zeros((len(pts), 1))], axis=1)


def stroke_mobject(pts, *, color=INK, stroke_width=3.0):
    """把点列变成一条 Manim 折线（不涉及动画）。"""
    mob = VMobject(stroke_color=color, stroke_width=stroke_width)
    mob.set_points_as_corners(_as3d(pts))
    return mob


class StrokeSet:
    """一组笔画，带缓存的几何量。

    Attributes
    ----------
    paths : list[np.ndarray]
        每个元素是 ``(n, 2)`` 的 Manim 坐标。
    widths : list[np.ndarray] | None
        每笔逐点的原始墨宽（想要"笔锋"变宽笔迹时用得上）。
    """

    def __init__(self, paths, *, size=7.0, center=(0.0, 0.0), widths=None,
                 blobs=None, image=None):
        self.paths = [_as3d(p)[:, :2] for p in paths]
        self.widths = [np.asarray(w, float) for w in widths] if widths is not None else None
        self.size = size
        self.center = tuple(center)
        self.blobs = list(blobs) if blobs else []
        self.image = image

    # ------------------------------------------------------------ 基本信息
    def __len__(self):
        return len(self.paths)

    def __iter__(self):
        return iter(self.paths)

    def __getitem__(self, i):
        return self.paths[i]

    @property
    def lengths(self):
        """每笔的弧长（Manim 单位）。"""
        out = []
        for p in self.paths:
            d = np.hypot(np.diff(p[:, 0]), np.diff(p[:, 1]))
            out.append(float(d.sum()))
        return np.array(out)

    @property
    def bounds(self):
        """整体包围盒 ``(x0, y0, x1, y1)``。"""
        allp = np.vstack(self.paths)
        return (float(allp[:, 0].min()), float(allp[:, 1].min()),
                float(allp[:, 0].max()), float(allp[:, 1].max()))

    def describe(self):
        L = self.lengths
        x0, y0, x1, y1 = self.bounds
        return (f"StrokeSet({len(self)} 笔，"
                f"总长 {L.sum():.1f} 单位，单笔 {L.min():.2f}~{L.max():.2f}，"
                f"范围 x[{x0:.2f},{x1:.2f}] y[{y0:.2f},{y1:.2f}])")

    # ------------------------------------------------------------ 变换 / 过滤
    def filter_inside(self, ellipses, *, margin=1.0, max_fraction=0.40):
        """剔除主要落在给定椭圆内的笔画，返回新的 :class:`StrokeSet`。

        典型用法是把眼睛这类实心块从逐笔绘制里拿掉，改成几何构造绘制::

            eyes = [(-0.333, 1.044, 0.286, 0.157, -83.5)]
            strokes = strokes.filter_inside(eyes)
        """
        if not len(ellipses):
            return self
        kept, keptw = [], []
        for i, p in enumerate(self.paths):
            hit = max(np.mean([in_ellipse(q, E, margin) for q in p]) for E in ellipses)
            if hit <= max_fraction:
                kept.append(p)
                if self.widths is not None:
                    keptw.append(self.widths[i])
        return StrokeSet(kept, size=self.size, center=self.center,
                         widths=keptw or None, blobs=self.blobs, image=self.image)

    def only_inside(self, ellipses, *, margin=1.4):
        """只保留落在给定椭圆内的笔画（``filter_inside`` 的反操作）。"""
        kept, keptw = [], []
        for i, p in enumerate(self.paths):
            hit = max(np.mean([in_ellipse(q, E, margin) for q in p]) for E in ellipses)
            if hit > 0.40:
                kept.append(p)
                if self.widths is not None:
                    keptw.append(self.widths[i])
        return StrokeSet(kept, size=self.size, center=self.center,
                         widths=keptw or None, blobs=self.blobs, image=self.image)

    def scaled(self, factor, *, about=(0.0, 0.0)):
        """整体缩放，返回新的 :class:`StrokeSet`。"""
        c = np.array([about[0], about[1]])
        return StrokeSet([(p - c) * factor + c for p in self.paths],
                         size=self.size * factor, center=self.center,
                         widths=self.widths, blobs=self.blobs, image=self.image)

    def shifted(self, dx, dy):
        return StrokeSet([p + np.array([dx, dy]) for p in self.paths],
                         size=self.size, center=(self.center[0] + dx, self.center[1] + dy),
                         widths=self.widths, blobs=self.blobs, image=self.image)

    # ------------------------------------------------------------ 存取
    def save(self, path):
        """存成 ``.npz``（``allow_pickle``），方便离线抽一次、反复渲染。"""
        payload = {
            "paths": np.array(self.paths, dtype=object),
            "meta": np.array([self.size, self.center[0], self.center[1]]),
            "image": np.array(self.image or ""),
        }
        if self.widths is not None:
            payload["widths"] = np.array(self.widths, dtype=object)
        np.savez_compressed(path, **payload)
        return path

    @classmethod
    def load(cls, path):
        d = np.load(path, allow_pickle=True)
        size, cx, cy = (float(v) for v in d["meta"][:3])
        widths = None
        if "widths" in d:
            arr = d["widths"]
            if getattr(arr, "dtype", None) == object and arr.size:
                widths = list(arr)
        image = None
        if "image" in d:
            v = d["image"]
            s = str(v.item()) if getattr(v, "shape", ()) == () else str(v)
            image = s or None
        return cls(list(d["paths"]), size=size, center=(cx, cy),
                   widths=widths, image=image)

    def __repr__(self):
        return f"<StrokeSet {len(self)} strokes>"


class Stylus(VGroup):
    """笔尖光标——一个实心点加一圈光晕，跟着笔画走。

    Parameters
    ----------
    dot_radius, ring_radius : float
        实心点与光晕圈的大小。
    color : str
        笔尖颜色。
    """

    def __init__(self, *, dot_radius=0.07, ring_radius=0.16, color=STYLUS, **kwargs):
        super().__init__(**kwargs)
        self.dot_radius = dot_radius
        self.dot = Dot(radius=dot_radius, color=color)
        self.ring = Circle(radius=ring_radius, stroke_color=color,
                           stroke_width=1.5, stroke_opacity=0.55)
        self.add(self.dot, self.ring)
        self.color = color

    # ------------------------------------------------------------ 单笔
    def draw(self, pts, *, color=INK, stroke_width=3.0, run_time=None,
             pen_speed=0.9, min_time=0.15, rate_func=linear):
        """画一笔，返回可直接塞进 ``self.play(...)`` 的动画列表。

        ``run_time`` 不给时按笔画长度自动分配（``min_time + 长度/pen_speed``），
        这样长线画得久、短线画得快，节奏像真人运笔。
        """
        mob = stroke_mobject(pts, color=color, stroke_width=stroke_width)
        if run_time is None:
            d = np.hypot(*np.diff(_as3d(pts)[:, :2], axis=0).T).sum()
            run_time = min_time + float(d) / pen_speed
        return [Create(mob, rate_func=rate_func),
                MoveAlongPath(self, mob.copy(), rate_func=rate_func)], run_time, mob

    def draw_all(self, strokes, *, color=INK, stroke_width=3.0, pen_speed=0.9,
                 min_time=0.15, on_stroke=None):
        """把所有笔画依次画完，返回动画列表。

        用法::

            anims = stylus.draw_all(strokes)
            self.play(*anims)          # 一次排完（总时长自动相加）
        """
        anims = []
        paths = strokes.paths if isinstance(strokes, StrokeSet) else list(strokes)
        for i, p in enumerate(paths):
            if on_stroke is not None:
                on_stroke(i, p)
            group, _, mob = self.draw(p, color=color, stroke_width=stroke_width,
                                      pen_speed=pen_speed, min_time=min_time)
            anims.extend(group)
        return anims

    # ------------------------------------------------------------ 复描
    def retrace(self, pts, *, color=INK, stroke_width=3.0, run_time=None,
                pen_speed=0.9, min_time=0.15, rate_func=linear):
        """沿一条既有路径再走一遍（"描"）。与 :meth:`draw` 等价，语义更清楚。"""
        return self.draw(pts, color=color, stroke_width=stroke_width,
                         run_time=run_time, pen_speed=pen_speed,
                         min_time=min_time, rate_func=rate_func)

    def go_to(self, point, *, run_time=0.25):
        """把笔尖挪到某处（提笔换位）。"""
        return self.animate.move_to(_as3d([point])[0]).set_run_time(run_time)


def draw_strokes(scene, strokes, *, stylus=None, color=INK, stroke_width=3.0,
                 pen_speed=0.9, min_time=0.15, show_stylus=True):
    """便捷函数：在一个 Scene 里把笔画逐笔播完。

    等价于 ``scene.play(*Stylus().draw_all(strokes))``，但会顺手处理笔尖的
    出现与收起。想要完全掌控节奏就直接用 :class:`Stylus`。
    """
    from manim import FadeIn, FadeOut

    own = stylus is None
    stylus = stylus or Stylus()
    paths = strokes.paths if isinstance(strokes, StrokeSet) else list(strokes)
    if len(paths) == 0:
        return
    stylus.move_to(_as3d([paths[0][0]])[0])
    if show_stylus:
        scene.play(FadeIn(stylus), run_time=0.4)
    for p in paths:
        group, rt, _ = stylus.draw(p, color=color, stroke_width=stroke_width,
                                   pen_speed=pen_speed, min_time=min_time)
        scene.play(*group, run_time=rt)
    if show_stylus:
        scene.play(FadeOut(stylus), run_time=0.4)

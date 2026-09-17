"""绘图工具：圆规、辅助几何、参数方程椭圆构造。

这一层负责把"用数学方法画圆/椭圆"演出来——先画浅色构造线，再用半径臂
扫出轨迹，最后交给笔尖描墨。三种构件都是现成的动画生成器：

    Compass(pivot, r).draw_circle()        # 圆规旋转一周画圆
    trace_ellipse(center, a, b, tilt)      # 辅助圆 + 长短轴 + 半径臂扫出椭圆
    construction_circle(center, r)         # 只要一条虚线参考圆
"""

from __future__ import annotations

import numpy as np
from manim import (
    Create, DashedLine, DashedVMobject, Dot, FadeIn, FadeOut, Line, Rotate,
    UpdateFromAlphaFunc, VGroup, VMobject, linear,
)

from .geometry import ring_path

__all__ = [
    "Compass",
    "construction_circle",
    "construction_axes",
    "trace_ellipse",
    "sweep_circle",
    "arm_trace",
]

CONSTRUCT = "#7FB3C8"      # 构造线青灰
PIVOT = "#E8B84B"          # 圆心金
PEN = "#00B4D8"            # 笔尖青蓝


class Compass(VGroup):
    """一把圆规：枢轴 + 两节摆臂 + 笔尖。

    几何上等价于"从枢轴出发、长度为 ``reach`` 的臂"，旋转它就能扫出半径为
    ``reach`` 的圆。``knee`` 高度按 ``reach`` 缩放，小半径时不会显得又高又瘦。
    """

    def __init__(self, pivot, reach, *, arm_color="#718096", **kwargs):
        super().__init__(**kwargs)
        pivot = np.array([pivot[0], pivot[1], 0.0], float)
        self.pivot = pivot
        self.reach = float(reach)
        knee = pivot + np.array([-reach * 0.30, reach * 1.15, 0.0])
        tip = pivot + np.array([reach, 0.0, 0.0])
        self.dot = Dot(pivot, radius=0.055, color=PIVOT)
        self.arm1 = Line(pivot, knee, stroke_color=arm_color, stroke_width=3.0)
        self.arm2 = Line(knee, tip, stroke_color=arm_color, stroke_width=3.0)
        self.pen = Dot(tip, radius=0.065, color=PEN)
        self.add(self.dot, self.arm1, self.arm2, self.pen)

    @property
    def tip(self):
        return self.pen.get_center()

    def draw_circle(self, radius=None, *, turns=1.0, run_time=2.6,
                    show_circle=True, dashed=False, dashes=64, color=CONSTRUCT,
                    rate_func=linear):
        """旋转 ``turns`` 圈，同时把半径圆画出来。

        Returns
        -------
        (animations, circle_mobject)
            ``animations`` 可展开进 ``self.play(*animations)``；圆对象记下来
            以便稍后 ``FadeOut``。
        """
        r = self.reach if radius is None else float(radius)
        circle = VMobject(stroke_color=color, stroke_width=2.0)
        circle.set_points_as_corners(ring_path(self.pivot, r, r, 0.0, n=120,
                                                overlap=False))
        target = DashedVMobject(circle, num_dashes=dashes) if dashed else circle
        anims = [Rotate(self, turns * 2 * np.pi, about_point=self.pivot,
                        rate_func=rate_func)]
        if show_circle:
            anims.append(Create(target, rate_func=rate_func))
        for a in anims:
            a.set_run_time(run_time)
        return anims, target

    def sweep(self, *, turns=1.0, run_time=2.6, rate_func=linear):
        """只转圈，不画东西。"""
        anim = Rotate(self, turns * 2 * np.pi, about_point=self.pivot,
                      rate_func=rate_func)
        anim.set_run_time(run_time)
        return anim


def construction_circle(center, radius, *, color=CONSTRUCT, dashed=True,
                        dashes=46, stroke_width=1.1):
    """浅色参考圆——"这是构造出来的，不是成品"。"""
    c = VMobject(stroke_color=color, stroke_width=stroke_width)
    c.set_points_as_corners(ring_path(center, radius, radius, 0.0, n=120, overlap=False))
    return DashedVMobject(c, num_dashes=dashes) if dashed else c


def construction_axes(center, a, b, tilt_deg, *, color=CONSTRUCT, dash_length=0.03,
                      stroke_width=1.4):
    """椭圆的长短轴虚线，返回 ``VGroup``。"""
    c = np.array([center[0], center[1], 0.0], float)
    t = np.radians(tilt_deg)
    ux = np.array([np.cos(t), np.sin(t), 0.0])       # 长轴方向
    uy = np.array([-np.sin(t), np.cos(t), 0.0])      # 短轴方向
    return VGroup(
        DashedLine(c - ux * a, c + ux * a, dash_length=dash_length,
                   stroke_color=color, stroke_width=stroke_width),
        DashedLine(c - uy * b, c + uy * b, dash_length=dash_length,
                   stroke_color=color, stroke_width=stroke_width),
    )


def arm_trace(center, pts, *, color=PEN, stroke_width=2.0, dot_radius=0.022):
    """一根从圆心指向轨迹点的半径臂，返回 ``(VGroup, 更新回调)``。

    配合 ``UpdateFromAlphaFunc(arm, update)`` 使用；用同一个 ``run_time`` 和
    ``linear`` 与 ``Create(轨迹)`` 并排播放，臂尖就会正好咬在轨迹的推进端。
    """
    c = np.array([center[0], center[1], 0.0], float)
    p0 = np.array([pts[0][0], pts[0][1], 0.0], float)
    arm = VGroup(
        Line(c, p0, stroke_color=color, stroke_width=stroke_width),
        Dot(p0, radius=dot_radius, color=color),
    )
    n = len(pts)

    def update(m, alpha):
        k = min(n - 1, max(0, int(round(float(alpha) * (n - 1)))))
        p = np.array([pts[k][0], pts[k][1], 0.0], float)
        m[0].put_start_and_end_on(c, p)
        m[1].move_to(p)

    return arm, update


def trace_ellipse(center, a, b, tilt_deg, *, run_time=1.7, n=110,
                  color=CONSTRUCT, show_axes=True, show_arm=True,
                  show_label=None, label_font_size=11, label_scale=1.0):
    """参数方程构造椭圆：辅助圆 + 长短轴 + 半径臂扫出轨迹。

    Returns
    -------
    dict
        含 ``anims``（塞进 ``self.play(*...)``）、``arm``、``path``、
        ``scaffold``（构造线合集，播完统一 ``FadeOut``）、``points``（轨迹点列，
        可直接交给笔尖复描）。
    """
    c = np.array([center[0], center[1], 0.0], float)
    pts = ring_path(c, a, b, tilt_deg, n=n, overlap=False)

    outline = VMobject(stroke_color=color, stroke_width=2.0)
    outline.set_points_as_corners(pts)
    dashed = DashedVMobject(outline, num_dashes=52)

    scaffolding = []
    if show_axes:
        scaffolding.append(construction_axes(c, a, b, tilt_deg, color=color))
    # 外接辅助圆：半径取长半轴
    scaffolding.append(construction_circle(c, max(a, b), color=color, dashes=46))

    label = None
    if show_label:
        from manim import Text
        from .scene import TITLE_FONT
        label = Text(show_label, font=TITLE_FONT, font_size=label_font_size, color=color)
        label.scale(label_scale)
        t = np.radians(tilt_deg)
        uy = np.array([-np.sin(t), np.cos(t), 0.0])
        label.move_to(c + uy * (min(a, b) + 0.14) + np.array([-0.04, 0.0, 0.0]))
        scaffolding.append(label)

    arm = None
    anims = [Create(dashed, rate_func=linear)]
    if show_arm:
        arm, update = arm_trace(c, pts)
        anims.append(UpdateFromAlphaFunc(arm, update, rate_func=linear))

    scaffold = VGroup(*[s for s in scaffolding])
    return {
        "anims": anims,
        "run_time": run_time,
        "arm": arm,
        "path": dashed,
        "scaffold": scaffold,
        "points": pts,
    }


def sweep_circle(compass, pivot=None, *, turns=1.0, run_time=2.6, rate_func=linear):
    """原地转圈（``Compass.sweep`` 的函数式写法）。"""
    return compass.sweep(turns=turns, run_time=run_time, rate_func=rate_func)

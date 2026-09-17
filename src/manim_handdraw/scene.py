"""``HandDrawScene``——一行搞定"图 -> 逐笔手绘 -> 上色"。

最省事的用法::

    from manim import *
    import manim_handdraw as hd

    class Demo(hd.HandDrawScene):
        def construct(self):
            self.hand_draw("lineart.png", color="color.png")

想自己编排节奏、插特写、加几何构造，就用 ``hand_draw(..., draw=False)``
拿到笔画，然后自己调度（见 examples/peashooter）。
"""

from __future__ import annotations

import numpy as np
from manim import (
    DOWN, FadeIn, FadeOut, Group, MovingCameraScene, Text, UP, VMobject, VGroup, config,
)

from .strokes import Stylus, stroke_mobject

__all__ = ["HandDrawScene", "TITLE_FONT", "MONO_FONT", "PAPER", "INK",
           "tag_text", "CanvasUI"]

PAPER = "#FAF7EE"
INK = "#23140F"
MUTED = "#8E8E93"
ACCENT = "#00A896"
TITLE_FONT = "PingFang SC"
MONO_FONT = "Menlo"


def tag_text(msg, *, font_size=13, color=MUTED, weight="NORMAL", scale=1.0,
             center=(0.0, 0.0, 0.0), font=TITLE_FONT, y=-3.55):
    """底部字幕。

    特写推近时，把 ``scale`` 设成摄像机缩放比、``center`` 设成镜头中心，
    字幕就能保持在屏幕上同样的位置与字号（见 :meth:`HandDrawScene.zoom_to`）。
    """
    t = Text(msg, font=font, font_size=font_size, color=color, weight=weight)
    t.scale(scale)
    t.move_to(np.array([center[0], center[1], 0.0]) + np.array([0.0, y * scale, 0.0]))
    return t


class CanvasUI(VGroup):
    """画纸四角的展签：左上角标题 + 顶部分隔线 + 底部进度槽。"""

    def __init__(self, *, title="Hand Draw", subtitle="", width=15.0,
                 line_color="#E5E1D3", **kwargs):
        super().__init__(**kwargs)
        t1 = Text(title, font=MONO_FONT, font_size=18, color="#2A2A2A", weight="BOLD")
        t1.to_corner(np.array([-1, 1, 0]), buff=0.4).shift(np.array([0.2, 0, 0]))
        self.add(t1)
        if subtitle:
            t2 = Text(subtitle, font=TITLE_FONT, font_size=13, color=MUTED)
            t2.next_to(t1, DOWN, buff=0.1).align_to(t1, np.array([-1, 0, 0]))
            self.add(t2)
        from manim import Line, Rectangle
        self.add(Line([-width / 2, 3.5, 0], [width / 2, 3.5, 0],
                      stroke_color=line_color, stroke_width=1.0))
        slot = Rectangle(width=width, height=0.04, stroke_width=0)
        slot.set_fill(line_color, 1.0).move_to([0, -3.8, 0])
        self.add(slot)


class HandDrawScene(MovingCameraScene):
    """带移动镜头的场景，附赠几个"一句话"辅助方法。"""

    # ------------------------------------------------------------ 全流程
    def hand_draw(self, image, color=None, *, size=7.0, center=(0.0, 0.05),
                  stroke_width=3.0, pen_speed=0.9, min_time=0.15,
                  show_stylus=True, ui=True, title=None, subtitle="",
                  draw=True, cache=True, **extract_kw):
        """从线稿图一路做到上色成品。

        Parameters
        ----------
        image : str
            线稿图路径。抽取结果会缓存成 ``<图名>.strokes.npz``。
        color : str | list[str] | None
            成品图（含高光/暗部）。给一个字符串是一步上色；给列表就按顺序分层
            扫入。``None`` 表示只画线稿不上色。
        draw : bool
            为 ``False`` 时只抽取不绘制，把 :class:`StrokeSet` 返回给调用方
            自行编排（想插特写、加几何构造时用）。
        **extract_kw
            透传给 :func:`manim_handdraw.extract.extract_strokes`，例如
            ``drop_inside=[眼睛椭圆]``、``merge_gap=9.0``。

        Returns
        -------
        StrokeSet | None
            ``draw=False`` 时返回笔画集合；否则返回 ``None``。
        """
        from .extract import from_image

        if ui:
            self.add(CanvasUI(title=title or "Hand Draw", subtitle=subtitle))

        strokes = from_image(image, cache=cache, size=size, center=center, **extract_kw)

        if not draw:
            return strokes

        stylus = Stylus() if show_stylus else None
        if stylus is not None:
            stylus.move_to(np.concatenate([strokes[0][0], [0.0]]))
            self.play(FadeIn(stylus), run_time=0.4)

        from manim import Create, MoveAlongPath, linear

        ink_layer = []
        for p in strokes:
            mob = stroke_mobject(p, stroke_width=stroke_width)
            ink_layer.append(mob)
            dur = min_time + float(np.hypot(*np.diff(p, axis=0).T).sum()) / pen_speed
            stage = [Create(mob, rate_func=linear)]
            if stylus is not None:
                stage.append(MoveAlongPath(stylus, mob.copy(), rate_func=linear))
            self.play(*stage, run_time=dur)

        if stylus is not None:
            self.play(FadeOut(stylus), run_time=0.4)

        if color:
            layers = [color] if isinstance(color, str) else list(color)
            holder = None
            for layer in layers:
                anim, grp = self.sweep_color(layer, size=size, center=center)
                stage = [anim]
                if holder is not None:
                    stage.append(FadeOut(holder))
                self.play(*stage)
                if holder is not None:
                    self.remove(holder)
                holder = grp
            # 成品接管画面后墨线必须退场：否则角色一旦位移（比如后坐力），
            # 底下的线稿就会从边缘露出来，看起来像多了一层"幽灵轮廓"。
            self.play(FadeOut(VGroup(*ink_layer)), run_time=0.8)
            self.remove(*ink_layer)

        return None

    # ------------------------------------------------------------ 上色
    def sweep_color(self, image_path, *, n=7, size=7.0, center=(0.0, 0.0),
                    run_time=3.2, lag_ratio=0.28, z_index=20, **kw):
        """扫入一层颜色，返回 ``(animation, mobject_group)``。"""
        from .coloring import sweep_color as _sweep
        return _sweep(self, image_path, n=n, size=size, center=center,
                      run_time=run_time, lag_ratio=lag_ratio, z_index=z_index, **kw)

    # ------------------------------------------------------------ 特写
    def zoom_to(self, point, factor=0.30, *, run_time=1.3, hide=(), show=(),
                tag=None, tag_kw=None):
        """推近到 ``point``，屏幕可见范围为原来的 ``factor`` 倍。

        ``hide`` 里的东西（角标题等）在推近期间先收起来，因为镜头放大后它们
        会跟着一起放大、跑出画面。``tag`` 是特写期间要显示的底部字幕，会自动
        按 ``factor`` 缩放并跟随镜头——见 :func:`tag_text`。
        """
        from manim import FadeIn as FI, FadeOut as FO

        point = np.array([point[0], point[1], 0.0], float)
        out = []
        if hide:
            out.append(FO(VGroup(*hide), run_time=0.5))
            self.play(*out)
            out = []
        self.play(self.camera.frame.animate.scale(factor).move_to(point),
                  run_time=run_time)
        if tag is not None:
            t = tag_text(tag, scale=factor, center=point, **(tag_kw or {}))
            self.play(FI(t), run_time=0.5)
            return t
        return None

    def zoom_out(self, *, factor=0.30, run_time=1.3, tag=None, show=()):
        """退出特写，恢复到整幅画面。"""
        from manim import FadeIn as FI, FadeOut as FO

        if tag is not None:
            self.play(FO(tag), run_time=0.4)
        self.play(self.camera.frame.animate.scale(1.0 / factor).move_to([0, 0, 0]),
                  run_time=run_time)
        if show:
            self.play(FI(VGroup(*show)), run_time=0.5)

    # ------------------------------------------------------------ 几何构造
    def construct_ellipse(self, center, a, b, tilt=0.0, *, label=None, label_scale=1.0,
                          run_time=1.7, fade_scaffold=True, pause=0.0):
        """演出一次参数方程构造椭圆，返回轨迹点列供后续描墨/填充。

        Returns
        -------
        np.ndarray
            ``(n, 3)`` 的椭圆轨迹点。
        """
        from .drafting import trace_ellipse

        info = trace_ellipse(center, a, b, tilt, run_time=run_time,
                             show_label=label, label_scale=label_scale)
        self.play(*info["anims"], run_time=run_time)
        if pause:
            self.wait(pause)
        if fade_scaffold:
            fade = [FadeOut(info["scaffold"])]
            if info["arm"] is not None:
                fade.append(FadeOut(info["arm"]))
            self.play(*fade, run_time=0.5)
        return info["points"]

    def construct_circle(self, center, radius, *, run_time=2.6, dashed=True,
                         fade_guide=False):
        """演出一次"圆规画圆"，返回 ``(圆对象, 圆规对象)``。"""
        from .drafting import Compass

        comp = Compass(center, radius)
        self.play(FadeIn(comp), run_time=0.5)
        anims, circle = comp.draw_circle(run_time=run_time, dashed=dashed)
        self.play(*anims, run_time=run_time)
        self.play(FadeOut(comp), run_time=0.5)
        if fade_guide:
            self.play(FadeOut(circle), run_time=0.4)
        return circle, comp

"""实心墨块：眼睛、炮口开口这类"涂实"的地方。

``InkBlot`` 是一个可以按进度重建自身的椭圆墨团，配合
``UpdateFromAlphaFunc(blot, blot_grow)`` 就能演出"墨从中心涨开、填实"的效果。
"""

from __future__ import annotations

import numpy as np
from manim import VMobject

from .geometry import ring_path

__all__ = ["InkBlot", "blot_grow", "blot_fill", "solid_from_path"]

INK = "#23140F"


class InkBlot(VMobject):
    """椭圆墨团，``rebuild(s)`` 让它按 ``s ∈ [0, 1]`` 从中心向外涨开。

    边缘带一点低频起伏，不至于像个数学圆那么死板。
    """

    def __init__(self, center, a, b, tilt_deg=0.0, *, color=INK, wobble=0.045,
                 n_points=96, **kwargs):
        super().__init__(**kwargs)
        self.cx, self.cy = float(center[0]), float(center[1])
        self.a, self.b = float(a), float(b)
        self.tilt = np.radians(tilt_deg)
        self.wobble = float(wobble)
        # NB: do not call this `self.points` — ``VMobject`` already owns that
        # name for its raw point array, and assigning to it silently routes
        # through a setter that turns the integer into a 0-d array.
        self.n_points = int(n_points)
        self.set_fill(color, 1.0).set_stroke(width=0)
        self.rebuild(1.0)

    def rebuild(self, s):
        """按比例 ``s`` 重建轮廓。"""
        s = float(np.clip(s, 0.0, 1.0))
        th = np.linspace(0, 2 * np.pi, self.n_points)
        w = 1.0
        if self.wobble > 0:
            w = 1.0 + self.wobble * np.sin(5 * th + 1.1) + 0.03 * np.sin(9 * th)
        ex, ey = self.a * s * np.cos(th) * w, self.b * s * np.sin(th) * w
        ct, st = np.cos(self.tilt), np.sin(self.tilt)
        X = self.cx + ex * ct - ey * st
        Y = self.cy + ex * st + ey * ct
        self.set_points_as_corners(np.stack([X, Y, np.zeros_like(X)], axis=1))

    @property
    def center_point(self):
        return np.array([self.cx, self.cy, 0.0])


def blot_grow(mob, alpha):
    """``UpdateFromAlphaFunc`` 的回调：把 ``alpha`` 映射成涨开进度。"""
    mob.rebuild(alpha)


def blot_fill(scene, center, a, b, tilt_deg=0.0, *, color=INK, run_time=0.9,
              from_scale=0.06, rate_func=None):
    """在场景里播一次"墨团涨开填实"，可直接 ``scene.play(blot_fill(...))`` 之外再用。

    返回 ``(animation, mobject)``，把 ``mobject`` 记下来以便稍后整体淡出
    （否则角色移动时它会露在后面）。
    """
    from manim import UpdateFromAlphaFunc, rush_into

    blot = InkBlot(center, a, b, tilt_deg, color=color)
    blot.rebuild(from_scale)
    scene.add(blot)
    anim = UpdateFromAlphaFunc(blot, blot_grow,
                               run_time=run_time,
                               rate_func=rate_func or rush_into)
    return anim, blot


def solid_from_path(pts, *, color=INK, closed=True):
    """把一条闭合路径直接变成实心色块（比 :class:`InkBlot` 更贴合原图形状）。"""
    mob = VMobject()
    arr = np.asarray(pts, float)
    if arr.shape[1] == 2:
        arr = np.concatenate([arr, np.zeros((len(arr), 1))], axis=1)
    if closed and not np.allclose(arr[0], arr[-1]):
        arr = np.vstack([arr, arr[:1]])
    mob.set_points_as_corners(arr)
    mob.set_fill(color, 1.0).set_stroke(width=0)
    return mob


def ellipse_outline(center, a, b, tilt_deg=0.0, *, n=96):
    """椭圆轮廓点列（闭合成环），常用于"沿轮廓描一圈"。"""
    return ring_path(center, a, b, tilt_deg, n=n, overlap=True)

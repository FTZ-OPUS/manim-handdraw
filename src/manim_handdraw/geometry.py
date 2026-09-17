"""纯 numpy 的几何工具：坐标映射、椭圆参数采样、椭圆/圆拟合。

这一层刻意不依赖 scikit-image / scipy —— Manim 插件在每次启动时都会导入本包，
所以只有真正需要读图的功能才允许引入重依赖（见 ``extract.py``）。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "px_to_manim",
    "manim_to_px",
    "ring_path",
    "moment_ellipse",
    "robust_circle_fit",
    "in_ellipse",
    "blob_ellipse_from_mask",
]


# ---------------------------------------------------------------- 坐标映射
def px_to_manim(px, py, *, width, height, fit="height", size=7.0, center=(0.0, 0.0)):
    """位图像素坐标 -> Manim 场景坐标。

    与 ``ImageMobject.scale_to_fit_height(size).move_to(center)`` 严格一致，
    因此从图里量出来的几何量可以直接拿去画图。

    Parameters
    ----------
    px, py : array-like
        像素坐标，原点在左上角，y 轴向下。
    width, height : int
        图像像素尺寸。
    fit : {"height", "width"}
        按哪一边缩放到 ``size``。
    size : float
        缩放后该边的 Manim 长度。
    center : tuple
        图像中心落在场景中的位置。
    """
    w, h = float(width), float(height)
    s = size / (h if fit == "height" else w)
    cx, cy = float(center[0]), float(center[1])
    x = (np.asarray(px, float) - w / 2.0) * s + cx
    y = (h / 2.0 - np.asarray(py, float)) * s + cy
    return x, y


def manim_to_px(x, y, *, width, height, fit="height", size=7.0, center=(0.0, 0.0)):
    """``px_to_manim`` 的逆变换。"""
    w, h = float(width), float(height)
    s = size / (h if fit == "height" else w)
    cx, cy = float(center[0]), float(center[1])
    px = (np.asarray(x, float) - cx) / s + w / 2.0
    py = h / 2.0 - (np.asarray(y, float) - cy) / s
    return px, py


# ---------------------------------------------------------------- 椭圆采样
def ring_path(c, a, b, tilt_deg=0.0, n=110, overlap=True, th0=0.0, th1=360.0):
    """椭圆参数方程的采样点，形状 ``(n, 3)``，可直接喂给 Manim。

    ``a`` 沿 ``tilt_deg`` 方向，``b`` 与之垂直；``th0/th1`` 限定角度范围（度），
    传 ``th0=155, th1=242`` 即可只取一段圆弧。

    ``overlap=True`` 时首尾多采两点闭合成环，适合当"描一圈"的笔迹。
    """
    th = np.radians(np.linspace(th0, th1, n))
    ct, st = np.cos(np.radians(tilt_deg)), np.sin(np.radians(tilt_deg))
    ex, ey = a * np.cos(th), b * np.sin(th)
    pts = np.stack(
        [c[0] + ex * ct - ey * st, c[1] + ex * st + ey * ct, np.zeros(n)], axis=1
    )
    return np.vstack([pts, pts[:2]]) if overlap else pts


def in_ellipse(p, E, margin=1.0):
    """点 ``p`` 是否落在椭圆 ``E = (cx, cy, a, b, tilt_deg)`` 内。"""
    cx, cy, a, b, deg = E
    t = np.radians(deg)
    dx, dy = p[0] - cx, p[1] - cy
    u = dx * np.cos(t) + dy * np.sin(t)
    v = -dx * np.sin(t) + dy * np.cos(t)
    return (u / (a * margin)) ** 2 + (v / (b * margin)) ** 2 <= 1.0


# ---------------------------------------------------------------- 拟合
def moment_ellipse(mask, *, width, height, fit="height", size=7.0, center=(0.0, 0.0)):
    """用二阶矩把实心区域拟合成椭圆，返回 ``(cx, cy, a, b, tilt_deg)``（Manim 坐标）。

    二阶矩对椭圆的估计是无偏的，比用外接矩形近似准得多——倾斜的椭圆用外接矩形
    会把长短轴同时算大，倾角也有偏差。

    ``a`` 是长半轴，沿 ``tilt_deg`` 方向。
    """
    ys, xs = np.nonzero(np.asarray(mask, bool))
    if len(xs) < 3:
        raise ValueError("掩膜像素太少，无法拟合椭圆")
    xm, ym = xs.mean(), ys.mean()
    cov = np.cov(np.stack([xs - xm, ys - ym]))
    vals, vecs = np.linalg.eigh(cov)          # 升序
    a = 2.0 * np.sqrt(vals[1])                # 长半轴
    b = 2.0 * np.sqrt(vals[0])                # 短半轴
    v_maj = vecs[:, 1]
    # 图像 y 轴向下，Manim y 轴向上，方向取反
    tilt = float(np.degrees(np.arctan2(-v_maj[1], v_maj[0])))
    mx, my = px_to_manim(xm, ym, width=width, height=height,
                         fit=fit, size=size, center=center)
    s = size / (float(height) if fit == "height" else float(width))
    return mx, my, a * s, b * s, tilt


def robust_circle_fit(x, y, *, iters=10, trim=88.0, floor=1.5):
    """稳健圆拟合：最小二乘 + 迭代剔除离群点。

    手绘轮廓往往不是严格的圆，直接用最小二乘会被少数偏远的点带跑；
    这里每轮丢掉残差最大的那部分点再重拟合。

    Returns
    -------
    (cx, cy, r, inlier_mask, residual)
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    keep = np.ones(len(x), bool)
    cx = cy = r = 0.0
    res = np.zeros(len(x))
    for _ in range(iters):
        if keep.sum() < 3:
            break
        A = np.stack([x[keep], y[keep], np.ones(keep.sum())], axis=1)
        rhs = x[keep] ** 2 + y[keep] ** 2
        sol, *_ = np.linalg.lstsq(A, rhs, rcond=None)
        cx, cy = sol[0] / 2.0, sol[1] / 2.0
        r = float(np.sqrt(sol[2] + cx ** 2 + cy ** 2))
        res = np.abs(np.hypot(x - cx, y - cy) - r)
        new = res < max(floor, np.percentile(res, trim))
        if new.sum() < 3 or np.array_equal(new, keep):
            break
        keep = new
    return cx, cy, r, keep, res


def blob_ellipse_from_mask(mask, **kw):
    """``moment_ellipse`` 的便捷别名（掩膜来自 ``extract.find_solid_blobs``）。"""
    return moment_ellipse(mask, **kw)

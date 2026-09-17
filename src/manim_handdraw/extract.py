"""位图线稿 -> 可逐笔绘制的笔画序列。

这一层依赖 scikit-image / scipy / Pillow，属于可选依赖：
    pip install "manim-handdraw[extract]"

整条流水线：

    读图取墨  ->  骨架化  ->  距离变换取墨宽  ->  交叉点断开  ->  逐段游走
      ->  合并（顺带补上接头缺口）  ->  剔除孤立碎点  ->  按作画习惯排序

``scikit-image`` 等只在函数内部导入，这样 Manim 插件启动时不会有额外开销。
"""

from __future__ import annotations

import os

import numpy as np

from .geometry import manim_to_px, px_to_manim

__all__ = [
    "load_ink_mask",
    "trace_skeleton_paths",
    "resample_path",
    "merge_paths",
    "clean_paths",
    "sort_for_drawing",
    "extract_strokes",
    "find_solid_blobs",
    "from_image",
]

_NEIGHBOURS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


# ---------------------------------------------------------------- 读图
def load_ink_mask(path, *, threshold=128, channel="alpha"):
    """把线稿读成布尔"有墨"掩膜。

    ``channel="alpha"``（默认）适合带透明通道的 PNG；``channel="luma"`` 则按
    亮度阈值，适合白底黑线的图。

    Returns
    -------
    mask : np.ndarray[bool]
    size : (width, height)
    """
    from PIL import Image

    img = Image.open(path).convert("RGBA")
    arr = np.array(img)
    if channel == "alpha":
        if arr[..., 3].min() == 255:
            # 没有透明信息（整图不透明），退回按亮度判断
            channel = "luma"
    if channel == "alpha":
        mask = arr[..., 3] > threshold
    else:
        luma = arr[..., :3].astype(float).mean(axis=2)
        mask = luma < threshold
    return mask, (img.width, img.height)


# ---------------------------------------------------------------- 骨架 -> 折线
def trace_skeleton_paths(skel, *, min_len=4):
    """把 1 像素宽的骨架拆成若干有序折线。

    做法：先把 8 邻域数 >= 3 的像素标记为交叉点并摘掉，剩下的连通块就是
    "一条不含分叉的线"；再从端点出发游走，得到有序点列。

    Returns
    -------
    list[np.ndarray]
        每个元素是 ``(n, 2)`` 的 ``[row, col]`` 序列。
    """
    ys, xs = np.nonzero(skel)
    if len(ys) == 0:
        return []
    pix = set(zip(ys.tolist(), xs.tolist()))

    def nbrs(p):
        y, x = p
        return [(y + dy, x + dx) for dy, dx in _NEIGHBOURS if (y + dy, x + dx) in pix]

    body = {p for p in pix if len(nbrs(p)) < 3}

    paths, seen = [], set()
    for seed in body:
        if seed in seen:
            continue
        stack, comp = [seed], []
        seen.add(seed)
        while stack:
            q = stack.pop()
            comp.append(q)
            for r in nbrs(q):
                if r in body and r not in seen:
                    seen.add(r)
                    stack.append(r)
        if len(comp) < min_len:
            continue

        cset = set(comp)
        deg = {p: sum(1 for r in nbrs(p) if r in cset) for p in comp}
        remaining = set(comp)
        while remaining:
            ends = [p for p in remaining if deg[p] <= 1]
            cur = ends[0] if ends else next(iter(remaining))
            walk = [cur]
            remaining.discard(cur)
            while True:
                cand = [r for r in nbrs(cur) if r in remaining]
                if not cand:
                    break
                # 优先正交邻居，避免对角跳步把线走出锯齿
                cand.sort(key=lambda r: abs(r[0] - cur[0]) + abs(r[1] - cur[1]))
                cur = cand[0]
                remaining.discard(cur)
                walk.append(cur)
            if len(walk) >= min_len:
                paths.append(np.array(walk, float))
    return paths


def resample_path(path, max_points=45):
    """按弧长等分重采样：既压掉像素级锯齿，也把点数控制在可渲染的规模。"""
    path = np.asarray(path, float)
    if len(path) < 3:
        return path
    seg = np.hypot(np.diff(path[:, 0]), np.diff(path[:, 1]))
    s = np.concatenate([[0.0], np.cumsum(seg)])
    total = s[-1]
    if total < 1e-9:
        return path
    n = min(max_points, max(2, int(total) + 1))
    t = np.linspace(0.0, total, n)
    return np.stack([np.interp(t, s, path[:, 0]), np.interp(t, s, path[:, 1])], axis=1)


# ---------------------------------------------------------------- 合并 / 清理
def _outward_tangent(P, end):
    """端点上朝外的单位切线。"""
    P = np.asarray(P, float)
    if len(P) < 2:
        return np.zeros(2)
    t = (P[-1] - P[-2]) if end == 1 else (P[0] - P[1])
    n = float(np.hypot(t[0], t[1]))
    return t / n if n > 1e-9 else np.zeros(2)


def _join(A, B, ea, eb):
    if (ea, eb) == (1, 0):
        return np.vstack([A, B])
    if (ea, eb) == (1, 1):
        return np.vstack([A, B[::-1]])
    if (ea, eb) == (0, 0):
        return np.vstack([A[::-1], B])
    return np.vstack([B, A])


def merge_paths(paths, *, max_gap=9.0, cos_thresh=0.30):
    """把端点相邻、走向连贯的小段接成整笔。

    这一步一举两得：既减少笔画数（免得整幅画被切成几百笔、频繁提笔），
    又顺手把交叉点处被切开的缺口补上——合并时那一段直线正好压住缺口。

    Parameters
    ----------
    max_gap : float
        允许合并的最大端点间距（像素）。
    cos_thresh : float
        方向一致性下限（1 为完全同向）。低于此值说明是个拐角/交叉，
        应当提笔而不是硬接。
    """
    paths = [np.array(p, float) for p in paths]
    merged = True
    while merged:
        merged = False
        n = len(paths)
        used = np.zeros(n, bool)
        out = []
        for i in range(n):
            if used[i]:
                continue
            A = paths[i]
            best = None
            for j in range(n):
                if j == i or used[j]:
                    continue
                B = paths[j]
                for ea in (1, 0):
                    pa = A[-1] if ea == 1 else A[0]
                    ta = _outward_tangent(A, ea)
                    for eb in (1, 0):
                        pb = B[-1] if eb == 1 else B[0]
                        gap = float(np.hypot(pb[0] - pa[0], pb[1] - pa[1]))
                        if gap > max_gap:
                            continue
                        tb = _outward_tangent(B, eb)
                        align = float(np.dot(ta, -tb))
                        if align < cos_thresh:
                            continue
                        if gap > 1e-6:
                            g = np.array([pb[0] - pa[0], pb[1] - pa[1]]) / gap
                            if float(np.dot(ta, g)) < cos_thresh:
                                continue
                        score = gap / max_gap + (1.0 - align)
                        if best is None or score < best[0]:
                            best = (score, j, ea, eb)
            if best is not None:
                _, j, ea, eb = best
                paths[i] = _join(A, paths[j], ea, eb)
                used[j] = True
                merged = True
            used[i] = True
            out.append(paths[i])
        paths = out
    return paths


def clean_paths(paths, *, min_length=4.3, neighbour_radius=7.0):
    """剔除孤立的碎点。

    只删"又短、附近又没有别的笔画"的段。短但有邻居的段要留着——它们是
    被交叉点切碎的真实细节（比如炮口里那条细高光线），合并后自然连成一线。
    """
    def arc_len(P):
        return float(np.sum(np.hypot(np.diff(P[:, 0]), np.diff(P[:, 1]))))

    keep, dropped = [], []
    for i, P in enumerate(paths):
        if arc_len(P) >= min_length:
            keep.append(i)
            continue
        far = True
        for j, Q in enumerate(paths):
            if j == i:
                continue
            for p in (P[0], P[-1]):
                if float(np.hypot(Q[:, 0] - p[0], Q[:, 1] - p[1]).min()) <= neighbour_radius:
                    far = False
                    break
            if not far:
                break
        (dropped if far else keep).append(i)
    return [paths[i] for i in keep], len(dropped)


def sort_for_drawing(paths, *, band=40.0):
    """排成自然的作画顺序：从上往下分带，带内就近接着画。

    纯粹按 y 排序会左右横跳，纯粹最近邻又会从角落开始；分带 + 贪心兼顾两者。
    """
    if not paths:
        return []
    cen = np.array([P.mean(axis=0) for P in paths])
    order = np.argsort(cen[:, 0])                    # row 小的在上
    bands, cur = [], [order[0]]
    for idx in order[1:]:
        if cen[idx, 0] - cen[cur[-1], 0] <= band:
            cur.append(idx)
        else:
            bands.append(cur)
            cur = [idx]
    bands.append(cur)

    result, used = [], np.zeros(len(paths), bool)
    pos = None
    for b in bands:
        pool = list(b)
        while pool:
            if pos is None:
                pick = pool[0]
            else:
                best, bd = pool[0], 1e9
                for j in pool:
                    for e in (paths[j][0], paths[j][-1]):
                        d = float(np.hypot(e[0] - pos[0], e[1] - pos[1]))
                        if d < bd:
                            bd, best = d, j
                pick = best
            pool.remove(pick)
            used[pick] = True
            result.append(pick)
            pos = paths[pick][-1]
    return result


# ---------------------------------------------------------------- 实心块
def find_solid_blobs(mask, *, min_area=400, disk_radius=6, box=None):
    """找出线稿里的实心墨块（眼睛、炮口开口这类）。

    这些地方骨架化会退化成一条穿过色块的细线，画出来完全不是原样，
    所以要把它们识别出来、改由几何构造绘制。

    Returns
    -------
    list[dict]
        每项含 ``mask``（该块的布尔掩膜）、``area``、``bbox``。
    """
    from skimage.measure import label, regionprops
    from skimage.morphology import disk, opening

    opened = opening(mask, disk(disk_radius))
    lab = label(opened)
    out = []
    for p in regionprops(lab):
        if p.area < min_area:
            continue
        cy, cx = p.centroid
        if box is not None:
            x0, y0, x1, y1 = box
            if not (x0 < cx < x1 and y0 < cy < y1):
                continue
        out.append({
            "mask": lab == p.label,
            "area": float(p.area),
            "centroid": (cx, cy),
            "bbox": p.bbox,
            "orientation": float(np.degrees(p.orientation)),
        })
    out.sort(key=lambda d: -d["area"])
    return out


# ---------------------------------------------------------------- 主入口
def extract_strokes(
    image,
    *,
    size=7.0,
    center=(0.0, 0.0),
    fit="height",
    threshold=128,
    channel="alpha",
    min_len=4,
    max_points=45,
    merge_gap=9.0,
    merge_angle=0.30,
    clean_short=4.3,
    order=True,
    drop_inside=(),
    verbose=False,
):
    """把一张线稿图抽成笔画序列（Manim 坐标）。

    Parameters
    ----------
    image : str | np.ndarray
        图片路径，或已是布尔掩膜。
    size, center, fit
        与 ``scale_to_fit_height(size).move_to(center)`` 保持一致。
    drop_inside : sequence
        椭圆 ``(cx, cy, a, b, tilt_deg)``；落在其中的笔画会被剔除。
        用来把眼睛这类实心块让给几何构造去画。
    order : bool
        是否重排成自然作画顺序。

    Returns
    -------
    dict
        ``{"paths": [...], "widths": [...], "size": (w, h), "blobs": [...]}``
        ``paths`` 中每项是 ``(n, 2)`` 的 Manim 坐标数组。
    """
    from skimage.morphology import skeletonize
    from scipy.ndimage import distance_transform_edt, maximum_filter

    if isinstance(image, np.ndarray):
        mask, (W, H) = image.astype(bool), (image.shape[1], image.shape[0])
    else:
        mask, (W, H) = load_ink_mask(image, threshold=threshold, channel=channel)

    blobs = find_solid_blobs(mask)
    skel = skeletonize(mask)
    dt = maximum_filter(distance_transform_edt(mask), size=5)

    raw = trace_skeleton_paths(skel, min_len=min_len)
    if verbose:
        print(f"[manim-handdraw] 骨架 {int(skel.sum())} 像素 -> 原始分段 {len(raw)}")

    paths = merge_paths(raw, max_gap=merge_gap, cos_thresh=merge_angle)
    paths, dropped = clean_paths(paths, min_length=clean_short)
    if verbose:
        print(f"[manim-handdraw] 合并清理 -> {len(paths)} 段（剔除碎点 {dropped}）")

    # 像素坐标 -> Manim 坐标，并顺手记录每笔的原始墨宽
    out_paths, out_widths = [], []
    for P in paths:
        row, col = P[:, 0], P[:, 1]
        x, y = px_to_manim(col, row, width=W, height=H, fit=fit, size=size, center=center)
        pts = np.stack([x, y], axis=1)
        if len(pts) > max_points:
            # 弧长重采样在 Manim 单位下再做一次，保证长短笔画点密度一致
            s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))])
            if s[-1] > 1e-9:
                t = np.linspace(0.0, s[-1], max_points)
                pts = np.stack([np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])], 1)
        widths = 2.0 * dt[np.clip(row.astype(int), 0, H - 1),
                          np.clip(col.astype(int), 0, W - 1)]
        widths = widths / (H if fit == "height" else W) * size
        out_paths.append(pts)
        out_widths.append(widths)

    # 剔除落在指定椭圆内的笔画（实心块改由几何构造绘制）
    if len(drop_inside):
        from .geometry import in_ellipse
        kept_p, kept_w = [], []
        for pts, w in zip(out_paths, out_widths):
            hit = max(np.mean([in_ellipse(p, E) for p in pts]) for E in drop_inside)
            if hit <= 0.40:
                kept_p.append(pts)
                kept_w.append(w)
        out_paths, out_widths = kept_p, kept_w
        if verbose:
            print(f"[manim-handdraw] 剔除实心块内笔画 -> {len(out_paths)} 段")

    if order:
        idx = sort_for_drawing(out_paths)
        out_paths = [out_paths[i] for i in idx]
        out_widths = [out_widths[i] for i in idx]

    return {"paths": out_paths, "widths": out_widths, "size": (W, H), "blobs": blobs}


def from_image(image, *, cache=True, **kw):
    """``extract_strokes`` 的便捷入口，返回 :class:`~manim_handdraw.strokes.StrokeSet`。

    默认会把结果缓存到 ``<图片名>.strokes.npz``，第二次调用直接读缓存——
    抽一次要几秒，缓存后重跑场景几乎零成本。
    """
    from .strokes import StrokeSet

    cache_path = None
    if cache and isinstance(image, str):
        cache_path = os.path.splitext(image)[0] + ".strokes.npz"
        if os.path.exists(cache_path):
            try:
                return StrokeSet.load(cache_path)
            except Exception:                      # 缓存损坏就重新抽
                pass

    data = extract_strokes(image, **kw)
    ss = StrokeSet(data["paths"], size=kw.get("size", 7.0),
                   center=kw.get("center", (0.0, 0.0)),
                   widths=data["widths"], blobs=data["blobs"],
                   image=str(image) if isinstance(image, str) else None)
    if cache_path:
        try:
            ss.save(cache_path)
        except Exception:
            pass
    return ss

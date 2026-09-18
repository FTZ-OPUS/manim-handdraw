#!/usr/bin/env python3
"""
extract_assets.py —— 从一张彩色插画派生「逐笔手绘动画」所需的全部素材。

    python3 extract_assets.py source.png -o assets/

产出
----
lineart.png        线稿（alpha 通道即墨迹），直接喂给 manim-handdraw 的 from_image()
lay_<name>.png     按色相分离的分层色块，用于分条扫入上色
full.png           去掉背景的完整角色
geo.json           暗色实心块（眼睛 / 炮口开口这类）的椭圆标定 + 眼内高光
diag_*.png         诊断图：每次跑完务必看一眼，确认阈值挑对了

流水线
------
  1. 分割人物   四边中位色当背景参考 → 到背景色的距离 → 形态学闭运算补洞
                → 取最大连通域 = 人物蒙版
  2. 炼线稿     mkbitmap 高通滤波把渐变阴影滤掉、只留线 → 阈值二值化
                → 用人物蒙版滤掉背景杂点 → 去掉过小的碎点
  3. 分层色块   HSV 分色相，切出白/绿/红/蓝/粉等若干层
  4. 几何标定   暗色实心块做二阶矩椭圆拟合（倾斜椭圆的严格解，不是外接框近似）

依赖：potrace 套件里的 mkbitmap（brew install potrace / apt install potrace），
     以及 numpy / scipy / scikit-image / Pillow
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw


# --------------------------------------------------------------------------- #
# 工具
# --------------------------------------------------------------------------- #
def _need_mkbitmap():
    exe = shutil.which("mkbitmap")
    if exe is None:
        sys.exit("找不到 mkbitmap。它随 potrace 一起发布：\n"
                 "  macOS : brew install potrace\n"
                 "  Debian: sudo apt install potrace")
    return exe


def save_gray(arr, path, size=420):
    a = np.asarray(arr, float)
    a = (a - a.min()) / max(1e-9, a.max() - a.min())
    Image.fromarray((a * 255).astype(np.uint8)).resize((size, size), Image.LANCZOS).save(path)


# --------------------------------------------------------------------------- #
# 1. 人物分割
# --------------------------------------------------------------------------- #
def segment(rgb, *, dist_threshold=40.0, core_threshold=60.0, verbose=True):
    """用「到背景色的距离」把角色从背景里拉出来。

    背景参考色取四边各 40px 的中位色 —— 对带渐变、带纹理、带飘落花瓣的
    背景都稳，因为中位数不受少数花瓣影响。
    """
    from scipy.ndimage import (binary_closing, binary_dilation, binary_fill_holes,
                               binary_opening, label)

    H, W = rgb.shape[:2]
    border = np.concatenate([
        rgb[:40].reshape(-1, 3), rgb[-40:].reshape(-1, 3),
        rgb[:, :40].reshape(-1, 3), rgb[:, -40:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
    if verbose:
        print(f"  背景参考色 RGB({bg[0]:.0f},{bg[1]:.0f},{bg[2]:.0f})   "
              f"距离中位 {np.median(dist):.0f} / 90% {np.percentile(dist, 90):.0f}")

    def biggest(m):
        m = binary_closing(m, np.ones((9, 9)))
        m = binary_fill_holes(m)
        m = binary_opening(m, np.ones((7, 7)))
        lab, _ = label(m)
        if lab.max() == 0:
            return np.zeros_like(m)
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0
        out = lab == sizes.argmax()
        out = binary_closing(out, np.ones((15, 15)))
        return binary_fill_holes(out)

    body = biggest(dist > dist_threshold)
    core = biggest(dist > core_threshold)
    if verbose:
        print(f"  人物蒙版（含发丝）{body.mean():.1%}   实心区 {core.mean():.1%}")
    return body, core, dist, bg


# --------------------------------------------------------------------------- #
# 2. 炼线稿
# --------------------------------------------------------------------------- #
def extract_lineart(rgb, body, *, tmpdir=".", filter_radius=6, threshold=0.45,
                    min_area=20, dilate=13, verbose=True):
    """mkbitmap 高通滤波 → 二值线稿 → 蒙版过滤 → 去碎点。

    `filter_radius` 是 mkbitmap 的高通半径。注意它**不是越大越干净**：半径越大
    高通保留的低频越多，反而会有更多渐变阴影被阈值判成"线"。实测 6 附近最好，
    调大只会让墨迹变多。
    """
    from scipy.ndimage import binary_dilation, label

    mk = _need_mkbitmap()
    H, W = rgb.shape[:2]
    gray = os.path.join(tmpdir, "_gray.pgm")
    pbm = os.path.join(tmpdir, "_line.pbm")
    Image.fromarray(rgb.astype(np.uint8)).convert("L").save(gray)
    subprocess.run([mk, "-f", str(filter_radius), "-s", "1", "-3",
                    "-t", str(threshold), gray, "-o", pbm], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ink = np.array(Image.open(pbm).convert("L")) < 128

    inside = binary_dilation(body, np.ones((dilate, dilate)))
    ink = ink & inside
    lab, _ = label(ink, structure=np.ones((3, 3)))
    cnt = np.bincount(lab.ravel())
    keep = cnt >= min_area
    keep[0] = False
    ink = keep[lab]
    if verbose:
        print(f"  线稿墨迹 {int(ink.sum())} px（{ink.mean():.2%}）")
    return ink


def write_lineart(ink, path, color=(35, 20, 15)):
    H, W = ink.shape
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = color
    rgba[..., 3] = np.where(ink, 255, 0).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(path)


# --------------------------------------------------------------------------- #
# 3. 分层色块
# --------------------------------------------------------------------------- #
DEFAULT_LAYERS = {
    # 名称: (色相区间列表, 最低饱和度, 最低明度) —— 区间是 [(lo, hi), ...]，单位「度」
    # 跨 0 度的颜色（红）就写成两段，别写成一个区间。
    "white": None,                                    # 特例：低饱和 + 高明度
    "green": ([(55, 130)], 0.25, 0.20),
    "red": ([(0, 25), (335, 360)], 0.35, 0.15),
    "blue": ([(175, 260)], 0.15, 0.00),
    "pink": ([(300, 360)], 0.08, 0.60),
}


def split_layers(rgb, body, *, spec=None, white_sat=0.22, white_val=0.55, verbose=True):
    """按 HSV 把角色切成若干层色块，每层单独存成透明 PNG。

    层是互斥的（各层并集≈人物），所以上色时可以逐层叠加、互相保留，
    而不是互相覆盖。
    """
    spec = spec or DEFAULT_LAYERS
    hsv = np.array(Image.fromarray(rgb.astype(np.uint8)).convert("HSV")).astype(float)
    hue = hsv[..., 0] / 255.0 * 360.0
    sat = hsv[..., 1] / 255.0
    val = hsv[..., 2] / 255.0

    out = {}
    if "white" in spec:
        out["white"] = (sat < white_sat) & (val > white_val)
    for name, rule in spec.items():
        if rule is None:
            continue
        ranges, slo, vlo = rule
        m = np.zeros_like(hue, bool)
        for lo, hi in ranges:                      # 每段区间单独取或，再合并
            m |= (hue >= lo) & (hue <= hi)
        out[name] = m & (sat > slo) & (val > vlo)
    if "pink" in out and "red" in out:
        out["pink"] = out["pink"] & ~out["red"]

    stats = {}
    for name, m in out.items():
        m = m & body
        out[name] = m
        stats[name] = int(m.sum())
        if verbose:
            print(f"    层 {name:6s} {m.sum():8d} px "
                  f"({m.sum()/max(1,body.sum()):5.1%} of 人物)")
    return out, stats


def write_layer(rgb, mask, path):
    H, W = rgb.shape[:2]
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = rgb.astype(np.uint8)
    rgba[..., 3] = np.where(mask, 255, 0).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(path)


# --------------------------------------------------------------------------- #
# 4. 几何标定
# --------------------------------------------------------------------------- #
def to_manim(px, py, W, H, size, center):
    s = size / H
    return ((np.asarray(px, float) - W / 2) * s + center[0],
            (H / 2 - np.asarray(py, float)) * s + center[1])


def manim_to_px(x, y, W, H, size, center):
    s = size / H
    return ((np.asarray(x, float) - center[0]) / s + W / 2,
            H / 2 - (np.asarray(y, float) - center[1]) / s)


def calibrate(rgb, *, size=7.0, center=(0.0, 0.05), dark_luma=95.0, dark_sat=60.0,
              bright_luma=170.0, min_area=2500, verbose=True):
    """找出暗色实心块并做二阶矩椭圆拟合，同时定位块内的白色高光。

    为什么必须标定它们：这些地方在原画里是**实心**的（眼睛、炮口开口），
    而 mkbitmap 只能给出它们的**轮廓**。骨架化描边会把一个实心眼睛画成一条
    穿中间的细线，完全不像。所以要把它们从逐笔绘制里剔除，改用几何构造
    （参数方程画椭圆 + 填墨）来画。
    """
    from skimage.measure import label, regionprops
    from skimage.morphology import disk, opening

    H, W = rgb.shape[:2]
    luma = rgb.mean(axis=2)
    sat = rgb.max(axis=2) - rgb.min(axis=2)

    def moment_ellipse(mask):
        ys, xs = np.nonzero(mask)
        xm, ym = xs.mean(), ys.mean()
        cov = np.cov(np.stack([xs - xm, ys - ym]))
        vals, vecs = np.linalg.eigh(cov)
        a = 2.0 * np.sqrt(vals[1])
        b = 2.0 * np.sqrt(vals[0])
        v = vecs[:, 1]
        tilt = float(np.degrees(np.arctan2(-v[1], v[0])))   # 图像 y 向下 → Manim y 向上
        mx, my = to_manim(xm, ym, W, H, size, center)
        return mx, my, a / H * size, b / H * size, tilt

    dark = (luma < dark_luma) & (sat < dark_sat)
    lab = label(opening(dark, disk(6)))

    blobs = []
    for p in regionprops(lab):
        if p.area < min_area:
            continue
        m = lab == p.label
        E = moment_ellipse(m)
        ex, ey, ea, eb, et = E

        # 高光：椭圆内部最亮的那块区域。
        # 不能按「~m 的连通域」找 —— 原画里眼珠高光常常贴着瞳孔边缘，
        # 在 ~m 里它和整片背景连成同一个连通域，会被当成一个巨大的背景块而漏掉。
        # regionprops.bbox 的顺序是 (min_row, min_col, max_row, max_col)，
        # 别顺手写成 (y0, y1, x0, x1) —— 那样 y1 会拿到列号，切片直接跑飞。
        y0, x0, y1, x1 = p.bbox
        yy, xx = np.mgrid[y0:y1, x0:x1]
        mx, my = to_manim(xx, yy, W, H, size, center)
        dx, dy = mx - ex, my - ey
        t = np.radians(et)
        u = dx * np.cos(t) + dy * np.sin(t)
        v = -dx * np.sin(t) + dy * np.cos(t)
        inside = (u / (ea * 0.92)) ** 2 + (v / (eb * 0.92)) ** 2 <= 1.0
        bright = inside & (luma[y0:y1, x0:x1] > bright_luma)
        hole = None
        if bright.any():
            lb = label(bright)          # 这里是 skimage 的 label，只返回数组
            best = max(regionprops(lb), key=lambda q: q.area, default=None)
            if best is not None and best.area >= 60:
                cy_, cx_ = best.centroid
                mx_, my_ = to_manim(x0 + cx_, y0 + cy_, W, H, size, center)
                hole = [float(mx_), float(my_),
                        float(np.sqrt(best.area / np.pi) / H * size)]
        blobs.append({"ellipse": [float(v) for v in E], "area": float(p.area),
                      "px_center": [float(p.centroid[1]), float(p.centroid[0])],
                      "hole": hole})

    blobs.sort(key=lambda d: -d["area"])
    if verbose:
        print(f"  暗色实心块 {len(blobs)} 个:")
        for i, d in enumerate(blobs):
            e = d["ellipse"]
            print(f"    [{i}] 面积 {d['area']:8.0f}  中心=({e[0]:+.3f},{e[1]:+.3f}) "
                  f"A={e[2]:.3f} B={e[3]:.3f} 倾角={e[4]:+.1f}"
                  f"{'  内含高光' if d['hole'] else ''}")

    # 眼睛 = 带高光的块；炮口开口 = 剩下的最大块。都只是**猜测**，
    # 请对照 diag_geo.png 确认，必要时在场景里按索引取用。
    eyes = [d["ellipse"] for d in blobs if d["hole"]][:2]
    highlights = [d["hole"] for d in blobs if d["hole"]][:2]
    rest = [d for d in blobs if not d["hole"]]
    cavity = rest[0]["ellipse"] if rest else None
    return {"size": size, "center": list(center),
            "eyes": eyes, "cavity": cavity, "highlights": highlights,
            "dark_blobs": blobs}


# --------------------------------------------------------------------------- #
# 自检：猜完之后先用几何常识验一遍，不满足就报警，而不是静默交出错的参数
# --------------------------------------------------------------------------- #
def sanity_check(geo, body):
    """用几何常识校验自动猜测的分类结果。

    提取流水线里最危险的不是"算错"，而是**算出一个看起来很正常、其实完全错的
    结果**（比如把背景的暗云当成眼睛）。这里用几条不依赖图像的常识把它拦下来。

    返回问题清单（空列表 = 通过）。
    """
    problems = []
    blobs = geo.get("dark_blobs", [])
    eyes = geo.get("eyes", [])
    cav = geo.get("cavity")

    # 1) 暗块总数。正常角色身上符合"实心暗块"特征的通常只有 1~4 个
    #    （眼睛 + 嘴巴/炮口开口 + 偶尔一两个细节）。数量爆炸基本只有一个原因：
    #    上游分割没把背景去掉，背景的暗部被当成角色的一部分。
    if len(blobs) > 6:
        problems.append(
            f"检出 {len(blobs)} 个暗色实心块（正常角色一般 1~4 个）。"
            f"很可能是上游分割没去干净背景，背景的暗部被算了进来。")

    # 2) 眼睛必须是成对的
    if len(eyes) == 0:
        problems.append("没找到眼睛候选（没有任何暗块包含高光）。")
    elif len(eyes) == 1:
        problems.append("只找到 1 个眼睛候选，眼睛应该是成对的。")
    elif len(eyes) > 2:
        problems.append(f"找到 {len(eyes)} 个眼睛候选，眼睛最多 2 个。")

    # 3) 两只眼睛的尺寸应当接近
    if len(eyes) >= 2:
        a0, a1 = eyes[0][2], eyes[1][2]
        ratio = max(a0, a1) / max(1e-9, min(a0, a1))
        if ratio > 2.5:
            problems.append(f"两只眼睛尺寸相差 {ratio:.1f} 倍（>2.5），不像同一张脸。")

    # 4) 两只眼睛应当大致在同一水平带上（允许侧脸造成的倾斜）
    if len(eyes) >= 2:
        dy = abs(eyes[0][1] - eyes[1][1])
        sa = 0.5 * (eyes[0][2] + eyes[1][2])
        if dy > 1.2 * sa:
            problems.append(
                f"两只眼睛纵向相差 {dy:.3f}，超过眼长的 {dy/max(1e-9,sa):.1f} 倍，"
                f"位置不像同一张脸的两只眼。")

    # 5) 眼睛中心要落在人物蒙版里面
    if len(eyes):
        for i, E in enumerate(eyes[:2]):
            px, py = None, None
            try:
                s_ = geo["size"] / body.shape[0]
                px = (E[0] - geo["center"][0]) / s_ + body.shape[1] / 2
                py = body.shape[0] / 2 - (E[1] - geo["center"][1]) / s_
                px, py = int(round(px)), int(round(py))
                if not (0 <= py < body.shape[0] and 0 <= px < body.shape[1]):
                    problems.append(f"第 {i+1} 只眼睛的中心落在图像外。")
                elif not body[py, px]:
                    problems.append(f"第 {i+1} 只眼睛的中心不在人物蒙版内。")
            except Exception:
                pass

    # 6) 应当能找到开口/嘴巴
    if cav is None:
        problems.append("没找到嘴巴/开口候选（剩余暗块里最大的那个）。")
    elif len(eyes) and cav[2] < max(e[2] for e in eyes) * 0.8:
        problems.append("开口候选比眼睛还小，可能认错了。")

    # 7) 人物蒙版占全图的比例 —— "上游分割失败"最直接的信号。
    #    角色插画的蒙版通常在 5%~80%；接近整张图说明背景压根没被分开，
    #    那后续的图层分离和几何标定全都是在一堆错的候选里挑，判据再准也没用。
    #    实测：一张角色插画 63%（正常）；一张动画截图（云层背景）跑到 95.6%，
    #    于是把背景的暗云当成眼睛、把云的颜色当成角色图层。
    frac = float(body.mean())
    if frac > 0.85:
        problems.append(
            f"人物蒙版占了整张图的 {frac:.1%}，背景基本没被分开。"
            f"图层与几何标定都不可信 —— 请换一张背景更干净的图（单色背景或"
            f"透明背景），或先单独做抠图。")
    elif frac < 0.02:
        problems.append(f"人物蒙版只占 {frac:.1%}，可能几乎没找到角色。")

    return problems


# --------------------------------------------------------------------------- #
# 诊断图
# --------------------------------------------------------------------------- #
def diagnose(rgb, dist, ink, body, layers, geo, outdir, size, center):
    H, W = rgb.shape[:2]
    S = 460
    sheet = Image.new("RGB", (S * 3 + 40, S * 2 + 30), (250, 247, 238))
    d = ImageDraw.Draw(sheet)

    def put(im, i, label):
        im = im.convert("RGB").resize((S, S), Image.LANCZOS)
        x, y = (i % 3) * (S + 10) + 10, (i // 3) * (S + 10) + 10
        sheet.paste(im, (x, y))
        d.text((x + 6, y + 4), label, fill=(200, 0, 0))

    put(Image.fromarray((np.clip(dist / dist.max(), 0, 1) * 255).astype(np.uint8)),
        0, "1. distance to background")
    put(Image.fromarray(np.where(body[..., None], rgb, 255).astype(np.uint8)),
        1, "2. character mask")
    put(Image.fromarray(np.where(ink[..., None], np.array([35, 20, 15], np.uint8), 250)
                        .astype(np.uint8)), 2, "3. lineart")
    put(Image.fromarray(np.where(layers.get("green", np.zeros_like(body))[..., None],
                                 rgb, 255).astype(np.uint8)), 3, "4. layer: green")
    put(Image.fromarray(np.where(layers.get("red", np.zeros_like(body))[..., None],
                                 rgb, 255).astype(np.uint8)), 4, "5. layer: red")
    sheet.save(os.path.join(outdir, "diag_pipeline.png"))

    # 几何叠加
    vis = Image.fromarray(rgb.astype(np.uint8))
    dr = ImageDraw.Draw(vis)

    def ring(E, color, w=4):
        ex, ey, a, b, t = E
        th = np.radians(np.linspace(0, 360, 220))
        ct, st = np.cos(np.radians(t)), np.sin(np.radians(t))
        X = ex + a * np.cos(th) * ct - b * np.sin(th) * st
        Y = ey + a * np.cos(th) * st + b * np.sin(th) * ct
        px, py = manim_to_px(X, Y, W, H, size, center)
        dr.line(list(zip(px, py)), fill=color, width=w)

    for E in geo["eyes"]:
        ring(E, (255, 0, 255))
    if geo["cavity"]:
        ring(geo["cavity"], (255, 140, 0))
    for h in geo["highlights"]:
        if h:
            px, py = manim_to_px(h[0], h[1], W, H, size, center)
            dr.ellipse([px - 6, py - 6, px + 6, py + 6], fill=(0, 200, 255))
    vis.resize((640, 640), Image.LANCZOS).save(os.path.join(outdir, "diag_geo.png"))
    print(f"  诊断图：diag_pipeline.png（分割/线稿/分层）、diag_geo.png（椭圆标定）")


# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="从一张彩色插画派生出逐笔手绘动画所需的全部素材。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("image", help="输入彩图")
    ap.add_argument("-o", "--outdir", default="assets", help="输出目录")
    ap.add_argument("--size", type=float, default=7.0,
                    help="角色在 Manim 场景里的高度（与 scale_to_fit_height 一致）")
    ap.add_argument("--center-y", type=float, default=0.05, help="图像中心 y 坐标")
    ap.add_argument("--dist-threshold", type=float, default=40.0,
                    help="分割阈值。人物残缺就调小，背景残留就调大")
    ap.add_argument("--core-threshold", type=float, default=60.0)
    ap.add_argument("--filter-radius", type=int, default=6, help="mkbitmap 高通半径")
    ap.add_argument("--line-threshold", type=float, default=0.45, help="mkbitmap 阈值")
    ap.add_argument("--min-speck-area", type=int, default=20, help="线稿碎点面积门槛")
    ap.add_argument("--bright-luma", type=float, default=170.0,
                    help="眼内高光的亮度门槛")
    ap.add_argument("--min-dark-area", type=float, default=2500,
                    help="暗色实心块面积门槛（眼睛/开口通常很大）")
    ap.add_argument("--layers-json", help="自定义分层规则的 JSON 文件")
    ap.add_argument("--keep-temp", action="store_true", help="保留中间文件便于调试")
    args = ap.parse_args(argv)

    if not os.path.exists(args.image):
        sys.exit(f"找不到文件：{args.image}")
    os.makedirs(args.outdir, exist_ok=True)

    print(f"[1/4] 读图并分割人物")
    raw_img = Image.open(args.image)
    rgba = raw_img.convert("RGBA")
    alpha = np.array(rgba)[..., 3]
    opaque = float((alpha > 128).mean())
    # 真带透明信息吗？（全不透明就当没有，全透明是坏图）
    has_alpha = raw_img.mode in ("RGBA", "LA") or "transparency" in raw_img.info
    use_alpha = has_alpha and 0.02 < opaque < 0.98

    rgb = np.array(rgba.convert("RGB")).astype(float)
    print(f"  图像 {rgb.shape[1]}x{rgb.shape[0]}"
          f"{'，带透明通道' if has_alpha else ''}")

    if use_alpha:
        # 透明通道是最可靠的"人物在哪"信号，直接拿来用，不做颜色分割。
        # 注意：如果退回按背景色分割，透明区填白的那种 PNG 会把角色的白色部分
        # （白发、白衣服）一起漏掉 —— 实测漏了 5.7 万像素。
        from scipy.ndimage import binary_erosion, binary_fill_holes as _fill
        print(f"  用透明通道当蒙版（不透明区域占 {opaque:.1%}）")
        body = _fill(alpha > 128)
        core = body
        dist = alpha.astype(float) / 255.0
        # 透明区要填成一个中性色再交给 mkbitmap。透明像素里存的 RGB 是任意的
        # （不同导出工具填白或填黑），而 mkbitmap 在轮廓处遇到强色阶会振铃：
        # 实测填黑会多出 49% 的假墨、填白多 12%。填成「轮廓内一圈的中位色」
        # 能把误差压到 1% 以内，而且这个颜色能从图本身算出来。
        band = body & ~binary_erosion(body, iterations=8)
        bg = np.median(rgb[band], axis=0) if band.any() else np.array([255.0] * 3)
        rgb[~body] = bg
        print(f"  透明区填充色 RGB({bg[0]:.0f},{bg[1]:.0f},{bg[2]:.0f})")
        print(f"  人物蒙版 {body.mean():.1%}")
    else:
        body, core, dist, bg = segment(rgb, dist_threshold=args.dist_threshold,
                                       core_threshold=args.core_threshold)

    print(f"[2/4] 炼线稿（mkbitmap -f {args.filter_radius} -t {args.line_threshold}）")
    ink = extract_lineart(rgb, body, tmpdir=args.outdir,
                          filter_radius=args.filter_radius,
                          threshold=args.line_threshold,
                          min_area=args.min_speck_area)
    write_lineart(ink, os.path.join(args.outdir, "lineart.png"))

    print(f"[3/4] 分层色块")
    spec = DEFAULT_LAYERS
    if args.layers_json:
        spec = json.load(open(args.layers_json, encoding="utf-8"))
    layers, stats = split_layers(rgb, body, spec=spec)
    for name, m in layers.items():
        write_layer(rgb, m, os.path.join(args.outdir, f"lay_{name}.png"))
    write_layer(rgb, body, os.path.join(args.outdir, "full.png"))
    write_layer(rgb, core, os.path.join(args.outdir, "core.png"))

    print(f"[4/4] 几何标定")
    geo = calibrate(rgb, size=args.size, center=(0.0, args.center_y),
                    bright_luma=args.bright_luma, min_area=args.min_dark_area)
    geo["bg_color"] = [float(v) for v in bg]
    geo["segmentation"] = {"dist_threshold": args.dist_threshold,
                           "core_threshold": args.core_threshold}
    geo["layers"] = stats
    with open(os.path.join(args.outdir, "geo.json"), "w", encoding="utf-8") as f:
        json.dump(geo, f, indent=1, ensure_ascii=False)

    diagnose(rgb, dist, ink, body, layers, geo, args.outdir, args.size,
             (0.0, args.center_y))

    problems = sanity_check(geo, body)
    if problems:
        print()
        print("!" * 68)
        print("自检未通过 —— 几何标定结果很可能不可用，请勿直接用于渲染：")
        for i, msg in enumerate(problems, 1):
            print(f"  {i}) {msg}")
        print("  → 打开 diag_geo.png 核对。若确认标错，先解决上游的分割问题")
        print("    （背景没去干净是最常见原因），或换一张背景更干净的图。")
        print("!" * 68)
    else:
        print("  自检通过：暗块分类看起来合理。")
    geo["sanity"] = {"passed": not problems, "problems": problems}

    if not args.keep_temp:
        for tmp in ("_gray.pgm", "_line.pbm"):
            p = os.path.join(args.outdir, tmp)
            if os.path.exists(p):
                os.remove(p)

    print(f"\n完成 → {args.outdir}/")
    print(f"  lineart.png   lineart 的墨迹像素 {int(ink.sum())}")
    print(f"  lay_*.png     {len(layers)} 层：" + " ".join(layers))
    print(f"  full.png      完整角色（去背景）")
    print(f"  geo.json      眼睛 {len(geo['eyes'])} 个，炮口开口 "
          f"{'有' if geo['cavity'] else '无'}")
    print(f"\n下一步：打开 diag_pipeline.png 和 diag_geo.png 确认阈值挑对了。")
    print(f"然后在场景里：")
    print(f"  strokes = hd.from_image('{args.outdir}/lineart.png', size={args.size},")
    print(f"                              center=(0.0, {args.center_y}),")
    print(f"                              drop_inside=[tuple(e) for e in geo['eyes']])")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""命令行入口：把"抽笔画"这一步放到 Manim 环境之外去跑。

    manim-handdraw prep lineart.png                  # 生成 lineart.strokes.npz
    manim-handdraw prep lineart.png --strips 7       # 顺便切好上色用的竖条
    manim-handdraw info lineart.strokes.npz          # 看看抽出来多少笔
    manim-handdraw demo -o demo/                     # 生成一个可跑的最小示例

渲染时场景只要 ``StrokeSet.load("lineart.strokes.npz")`` 就行，不必在
Manim 环境里装 scikit-image。
"""

from __future__ import annotations

import argparse
import os
import sys


def _cmd_prep(args):
    from .extract import extract_strokes
    from .strokes import StrokeSet
    from .coloring import split_strips

    if not os.path.exists(args.image):
        print(f"找不到文件：{args.image}", file=sys.stderr)
        return 1

    box = None
    if args.drop_ellipse:
        box = [tuple(float(v) for v in e.split(",")) for e in args.drop_ellipse]

    data = extract_strokes(
        args.image,
        size=args.size,
        center=(0.0, args.center_y),
        merge_gap=args.merge_gap,
        merge_angle=args.merge_angle,
        drop_inside=box or (),
        verbose=True,
    )
    ss = StrokeSet(data["paths"], size=args.size, center=(0.0, args.center_y),
                   widths=data["widths"], blobs=data["blobs"], image=args.image)
    out = args.output or os.path.splitext(args.image)[0] + ".strokes.npz"
    ss.save(out)
    print(f"已写出 {out}")
    print(f"  {ss.describe()}")

    if args.report:
        lines = ["index,points,length,x0,y0,x1,y1"]
        for i, p in enumerate(ss.paths):
            import numpy as np
            d = float(np.hypot(*np.diff(p, axis=0).T).sum())
            lines.append(f"{i},{len(p)},{d:.3f},{p[:,0].min():.3f},{p[:,1].min():.3f},"
                         f"{p[:,0].max():.3f},{p[:,1].max():.3f}")
        with open(args.report, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"已写出 {args.report}")

    if args.strips:
        for layer in args.strips:
            spans = split_strips(layer, args.strip_count, verbose=True)
            print(f"  {layer} -> {len(spans)} 条")

    return 0


def _cmd_info(args):
    from .strokes import StrokeSet

    if not os.path.exists(args.strokes):
        print(f"找不到文件：{args.strokes}", file=sys.stderr)
        return 1
    ss = StrokeSet.load(args.strokes)
    print(ss.describe())
    L = ss.lengths
    import numpy as np
    print(f"  长度分布: 中位 {np.median(L):.3f}  90% {np.percentile(L, 90):.3f}  "
          f"最大 {L.max():.3f}")
    print(f"  预计作画时长(pen_speed=0.9): {0.15 * len(ss) + L.sum() / 0.9:.1f} 秒")
    return 0


_DEMO_TEMPLATE = '''"""最小示例：一张图 -> 逐笔手绘 -> 上色。"""
from manim import *
import manim_handdraw as hd

config.frame_width = 16
config.frame_height = 9
config.background_color = hd.PAPER


class Demo(hd.HandDrawScene):
    def construct(self):
        self.hand_draw(
            "{image}",
            color={color},
            size=7.0,
            center=(0.0, 0.0),
        )
'''


def _cmd_demo(args):
    os.makedirs(args.output, exist_ok=True)
    path = os.path.join(args.output, "demo_scene.py")
    color = f'"{args.color}"' if args.color else "None"
    with open(path, "w") as f:
        f.write(_DEMO_TEMPLATE.format(image=os.path.abspath(args.image), color=color))
    print(f"已写出 {path}")
    print(f"运行：manim -ql {path} Demo")
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="manim-handdraw",
        description="把线稿图抽成可逐笔绘制的笔画序列。",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("prep", help="抽取笔画并写出 .npz")
    g.add_argument("image", help="线稿图路径")
    g.add_argument("-o", "--output", help="输出 .npz 路径（默认 <图名>.strokes.npz）")
    g.add_argument("--size", type=float, default=7.0, help="缩放后高度（Manim 单位）")
    g.add_argument("--center-y", type=float, default=0.05, help="图像中心 y 坐标")
    g.add_argument("--merge-gap", type=float, default=9.0,
                   help="允许合并的端点间距（像素，越大笔画越少）")
    g.add_argument("--merge-angle", type=float, default=0.30,
                   help="方向一致性下限，0~1，越大越严格")
    g.add_argument("--drop-ellipse", action="append", metavar="cx,cy,a,b,tilt",
                   help="剔除落在该椭圆内的笔画（可重复），例如眼睛")
    g.add_argument("--strips", action="append", metavar="PNG",
                   help="顺便把这张成品图切成竖条（可重复）")
    g.add_argument("--strip-count", type=int, default=7, help="竖条数量")
    g.add_argument("--report", help="把每笔的长度/包围盒写成 CSV")
    g.set_defaults(func=_cmd_prep)

    i = sub.add_parser("info", help="查看已抽取的 .npz")
    i.add_argument("strokes")
    i.set_defaults(func=_cmd_info)

    d = sub.add_parser("demo", help="生成一个最小可跑示例")
    d.add_argument("image", help="线稿图路径")
    d.add_argument("-o", "--output", default="demo", help="输出目录")
    d.add_argument("--color", help="成品图路径（可选）")
    d.set_defaults(func=_cmd_demo)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

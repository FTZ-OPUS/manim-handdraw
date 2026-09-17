"""Construct the face the way an illustrator would: measure, then draw with tools.

    manim -ql examples/02_construct_face.py Face

Shows the workflow the library is built around —

1. ``find_solid_blobs`` + ``moment_ellipse`` measure the eyes from the artwork
   (they are solid black, so skeletonisation would reduce them to a single thin
   line through the middle — quite different from what is actually there);
2. those strokes are *excluded* from the stroke-by-stroke pass;
3. a compass traces the muzzle's reference circle, and each eye is swept out from
   its parametric equation before being traced in ink and filled.

This is the same calibration the full peashooter example uses, trimmed down.
"""

import os

import numpy as np
from manim import FadeIn, FadeOut, Transform, UpdateFromAlphaFunc, config, rush_into

import manim_handdraw as hd

config.frame_width = 16
config.frame_height = 9
config.background_color = hd.PAPER

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "peashooter", "assets")
LINEART = os.path.join(ASSETS, "pea_lineart_opt.png")

SIZE = 7.0
CENTER = (0.0, 0.05)
INK_W = 3.0
ZOOM = 0.30
FOCUS = np.array([-0.95, 0.88, 0.0])


class Face(hd.HandDrawScene):
    def construct(self):
        # ---- 1. measure the eyes from the artwork -------------------------
        mask, (W, H) = hd.load_ink_mask(LINEART)
        blobs = hd.find_solid_blobs(mask, min_area=450, disk_radius=6)
        eyes = []
        for b in blobs:
            cx, cy, a, b_, tilt = hd.moment_ellipse(b["mask"], width=W, height=H,
                                                    size=SIZE, center=CENTER)
            if cy > 0.85 and abs(cx) < 1.0 and a < 0.40:
                eyes.append((cx, cy, a, b_, tilt))
        eyes.sort(key=lambda e: -e[0])                      # larger eye first
        assert len(eyes) == 2, "expected two eyes in this artwork"

        # ---- 2. extract strokes, minus the solid areas --------------------
        strokes = hd.from_image(LINEART, size=SIZE, center=CENTER)
        strokes = strokes.filter_inside(eyes)

        ui = hd.CanvasUI(title="Construct Face", subtitle="measure → construct → trace")
        self.add(ui)
        tag = hd.tag_text("逐笔手绘：实心区域已被剔除，稍后交给几何构造")
        self.play(FadeIn(tag), run_time=0.8)

        stylus = hd.Stylus()
        stylus.move_to(np.concatenate([strokes[0][0], [0.0]]))
        self.play(FadeIn(stylus), run_time=0.4)

        ink_layer = []
        head = [p for p in strokes.paths if p[:, 1].mean() > -0.40]
        for p in head:
            anims, rt, mob = stylus.draw(p, stroke_width=INK_W, pen_speed=4.0)
            ink_layer.append(mob)
            self.play(*anims, run_time=rt)
        self.wait(0.3)

        # ---- 3. close-up, and construct the eyes -------------------------
        self.play(FadeOut(tag), FadeOut(ui), run_time=0.5)
        self.play(self.camera.frame.animate.scale(ZOOM).move_to(FOCUS), run_time=1.3)

        for i, E in enumerate(eyes):
            name = "右眼 · 椭圆" if i == 0 else "左眼 · 椭圆（同构）"
            tag = hd.tag_text(name + "：x=a·cosθ , y=b·sinθ", color=hd.MUTED,
                              scale=ZOOM, center=FOCUS)
            self.play(FadeIn(tag), run_time=0.4)

            ex, ey, A, B, tilt = E
            info = hd.trace_ellipse((ex, ey), A, B, tilt, run_time=1.4,
                                    show_label=name, label_scale=ZOOM)
            self.play(*info["anims"], run_time=1.4)
            fade = [FadeOut(info["scaffold"])]
            if info["arm"] is not None:
                fade.append(FadeOut(info["arm"]))
            self.play(*fade, run_time=0.4)

            anims, rt, ring = stylus.retrace(hd.ellipse_outline((ex, ey), A, B, tilt),
                                             stroke_width=INK_W)
            ink_layer.append(ring)
            self.play(*anims, run_time=1.1)

            blot = hd.InkBlot((ex, ey), A * 0.97, B * 0.97, tilt)
            blot.set_z_index(-1)
            blot.rebuild(0.06)
            self.add(blot)
            ink_layer.append(blot)
            self.play(UpdateFromAlphaFunc(blot, hd.blot_grow), run_time=0.6,
                      rate_func=rush_into)
            self.play(FadeOut(tag), run_time=0.3)
            self.wait(0.2)

        # ---- 4. back out, and let the ink retire --------------------------
        self.play(self.camera.frame.animate.scale(1.0 / ZOOM).move_to([0, 0, 0]),
                  run_time=1.2)
        self.play(FadeIn(ui), run_time=0.4)

        for p in strokes.paths:
            if p[:, 1].mean() > -0.40:
                continue
            anims, rt, mob = stylus.draw(p, stroke_width=INK_W, pen_speed=4.0)
            ink_layer.append(mob)
            self.play(*anims, run_time=rt)

        self.play(FadeOut(stylus), run_time=0.4)
        tag = hd.tag_text("实心区域由几何构造绘制，其余仍是一笔一笔画出来的",
                          color=hd.ACCENT, weight="BOLD")
        self.play(FadeIn(tag), run_time=0.6)
        self.wait(2.0)

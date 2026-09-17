"""Peashooter Cowboy — the full ~2.5 minute video, end to end.

    cd examples/peashooter
    manim -ql peashooter.py CowboyPea            # quick preview
    manim -qh --fps 60 peashooter.py CowboyPea   # 1080p60

This is the long-form example: it hand-orchestrates the timeline instead of using
the ``hand_draw()`` one-liner, so it can push the camera in for the geometric
construction of the eyes and muzzle, then wash the colour in layer by layer.

Eyes and the muzzle opening are drawn *geometrically*, not stroke by stroke —
they are solid black areas in the artwork, and skeletonisation turns those into a
single thin line through the middle, which looks nothing like the original. Their
parameters come from ``calibrate.py``, measured from the artwork itself.
"""

import os

import numpy as np
from manim import (
    Circle, Create, Dot, Ellipse, FadeIn, FadeOut, Group, Line, MoveAlongPath,
    Rotate, Text, Transform, UpdateFromAlphaFunc, VGroup, config, linear, rush_into,
    smooth, wiggle,
)

import manim_handdraw as hd

import calibrate

config.frame_width = 16
config.frame_height = 9
config.background_color = hd.PAPER

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
LINEART = os.path.join(ASSETS, "pea_lineart_opt.png")
LAYERS = ["color_layer_green_opt.png", "color_layer_brown_opt.png",
          "color_layer_red_opt.png", "pea_transparent_opt.png"]

INK_W = 3.0
PAPER_GREEN = "#8CE03E"
PAPER_DARK = "#4B8B1E"
PAPER_HI = "#D4FF78"
GOLD = "#E8B84B"
RED = "#D9381E"
MUTED = "#8E8E93"
ACCENT = "#00A896"


class CowboyPea(hd.HandDrawScene):
    def construct(self):
        face = calibrate.load(verbose=False)
        eyes = [tuple(e) for e in face["eyes"]]
        mc = tuple(face["mouth_circle"])
        arc0, arc1 = face["mouth_arc"]
        cavity = tuple(face["cavity"])
        hl = face["highlight"]

        ui = hd.CanvasUI(title="Peashooter Cowboy",
                         subtitle="西部牛仔豌豆 · 逐笔手绘全流程")
        self.add(ui)
        tag = hd.tag_text("Act 1 / 绘图工具装配：旋转圆规定位头部基准与炮口基准圆")
        self.play(FadeIn(tag), run_time=1.0)
        self.wait(0.6)

        ink_layer = []          # 所有墨迹登记在册，上色完成后整体退场

        # =============================================================
        # Act 1 — compass and reference geometry
        # =============================================================
        head_c = np.array([-0.05, 0.90, 0.0])
        muzzle = np.array([mc[0], mc[1], 0.0])
        r_muzzle = mc[2]

        cross = VGroup(
            Line(head_c + np.array([-1.7, 0, 0]), head_c + np.array([1.7, 0, 0]),
                 stroke_color=hd.PAPER if False else "#00B4D8",
                 stroke_width=1.2, stroke_opacity=0.5),
            Line(head_c + np.array([0, -1.7, 0]), head_c + np.array([0, 1.7, 0]),
                 stroke_color="#00B4D8", stroke_width=1.2, stroke_opacity=0.5),
        )
        self.play(Create(cross), run_time=1.3)

        compass = hd.Compass(head_c, 1.25)
        self.play(FadeIn(compass), run_time=0.8)
        anims, head_ref = compass.draw_circle(run_time=3.0, dashed=False,
                                              color="#CBD5E1")
        self.play(*anims, run_time=3.0)
        self.play(FadeOut(compass), run_time=0.5)

        compass2 = hd.Compass(head_c, r_muzzle)
        self.add(compass2)
        self.play(compass2.animate.shift(muzzle - head_c), run_time=1.0)
        anims, mouth_ref = compass2.draw_circle(run_time=2.4, dashed=False,
                                                color="#CBD5E1")
        self.play(*anims, run_time=2.4)
        self.wait(0.3)
        # The muzzle circle is large and crosses the face — it would clutter the
        # whole drawing phase, so it retires with the compass.
        self.play(FadeOut(compass2), FadeOut(cross), FadeOut(mouth_ref), run_time=0.8)
        self.wait(0.7)

        # =============================================================
        # Act 2 — stroke by stroke (upper body), eyes excluded
        # =============================================================
        self.play(Transform(tag, hd.tag_text(
            "Act 2 / 逐笔手绘：等宽墨线逐笔生长，笔尖沿笔画实时跟随",
            color=hd.INK, weight="BOLD")), run_time=0.8)

        strokes = hd.from_image(LINEART, size=face["size"],
                                center=tuple(face["center"]))
        strokes = strokes.filter_inside(eyes)          # solid areas -> geometry
        upper = [p for p in strokes.paths if p[:, 1].mean() >= -0.40]
        lower = [p for p in strokes.paths if p[:, 1].mean() < -0.40]

        stylus = hd.Stylus()
        stylus.move_to(np.concatenate([upper[0][0], [0.0]]))
        self.play(FadeIn(stylus), run_time=0.5)

        self.play(Transform(tag, hd.tag_text(
            "笔 1/3 · 牛仔帽：帽冠折痕、宽大帽檐与金属帽带", color=hd.INK)),
            run_time=0.5)
        self.wait(0.3)
        self._draw(self, stylus, upper, ink_layer)

        # =============================================================
        # Act 3 — face close-up: geometric construction
        # =============================================================
        zoom = 0.30
        focus = np.array([-0.95, 0.88, 0.0])
        self.play(FadeOut(tag), FadeOut(ui), run_time=0.5)
        self.play(self.camera.frame.animate.scale(zoom).move_to(focus), run_time=1.3)

        def ztag(msg, color=MUTED, weight="NORMAL"):
            return hd.tag_text(msg, color=color, weight=weight, scale=zoom, center=focus)

        tag = ztag("Act 3 / 眼睛数学构造：椭圆参数方程 x=a·cosθ , y=b·sinθ",
                   color=hd.INK, weight="BOLD")
        self.play(FadeIn(tag), run_time=0.6)
        self.wait(0.4)

        for i, (E, name, times) in enumerate([
            (eyes[0], "右眼 · 椭圆", dict(axis=0.55, trace=1.7, ink=1.3, fill=0.7)),
            (eyes[1], "左眼 · 椭圆（同构）", dict(axis=0.45, trace=1.4, ink=1.1, fill=0.6)),
        ]):
            self._build_eye(stylus, ink_layer, E, name, zoom, times, hl if i == 0 else None, i)

        # ---- muzzle: compass circle, then retrace only the coincident arc ----
        self.play(Transform(tag, ztag(
            "Act 3 / 嘴巴数学构造：圆规旋转一周，画出炮口基准圆",
            color=hd.INK, weight="BOLD")), run_time=0.6)
        self.wait(0.3)

        comp = hd.Compass(muzzle, r_muzzle)
        comp.set_z_index(4)
        self.play(FadeIn(comp), run_time=0.6)
        anims, guide = comp.draw_circle(run_time=2.6, dashed=True)
        self.play(*anims, run_time=2.6)
        self.wait(0.3)
        self.play(FadeOut(comp), run_time=0.5)

        # Retrace only the angular span where the fitted circle actually lies on
        # the artwork's outline. Beyond it the circle drifts off the ink, and
        # drawing it would leave a stray arc floating next to the muzzle.
        outline = hd.ring_path(muzzle, r_muzzle, r_muzzle, 0.0, n=90, overlap=False,
                               th0=arc0 + 2.0, th1=arc1 - 2.0)
        anims, rt, ring = stylus.retrace(outline, stroke_width=INK_W)
        ink_layer.append(ring)
        self.play(*anims, run_time=1.7)
        self.play(FadeOut(guide), run_time=0.4)

        cav = hd.InkBlot((cavity[0], cavity[1]), cavity[2] * 0.95, cavity[3] * 0.95,
                         cavity[4])
        cav.set_z_index(-1)
        cav.rebuild(0.06)
        self.add(cav)
        ink_layer.append(cav)
        self.play(UpdateFromAlphaFunc(cav, hd.blot_grow), run_time=0.9,
                  rate_func=rush_into)
        self.wait(0.6)

        # ---- back to full frame ----
        self.play(FadeOut(tag), run_time=0.4)
        self.play(self.camera.frame.animate.scale(1.0 / zoom).move_to([0, 0, 0]),
                  run_time=1.3)
        tag = hd.tag_text("Act 4 / 逐笔手绘（续）：笔墨继续向下蔓延至领巾、双腿与长靴",
                          color=hd.INK, weight="BOLD")
        self.play(FadeIn(ui), FadeIn(tag), run_time=0.6)

        # =============================================================
        # Act 4 — stroke by stroke (lower body)
        # =============================================================
        self.play(Transform(tag, hd.tag_text(
            "笔 2/3 · 衣饰：三角领巾折线、飘带与四角星徽记", color=hd.INK)),
            run_time=0.5)
        legs = [False]

        def on_each(i, p):
            if not legs[0] and p[:, 1].mean() < -1.15:
                legs[0] = True
                self.play(Transform(tag, hd.tag_text(
                    "笔 3/3 · 身段：叉腰手臂、大步站姿与马刺长靴", color=hd.INK)),
                    run_time=0.5)

        self._draw(self, stylus, lower, ink_layer, on_each=on_each)
        self.play(FadeOut(stylus), run_time=0.6)
        self.wait(0.6)

        self.play(Transform(tag, hd.tag_text(
            f"白描墨线定稿 · 全 {len(strokes)} 笔闭合无瑕（纯矢量逐笔生长）",
            color=ACCENT, weight="BOLD")), run_time=0.7)
        scan = Line([-3.6, 3.2, 0], [3.6, 3.2, 0], stroke_color="#00B4D8",
                    stroke_width=3.0, stroke_opacity=0.8)
        self.play(scan.animate.move_to([0, -3.2, 0]), run_time=2.4, rate_func=smooth)
        self.play(FadeOut(scan), run_time=0.35)
        self.wait(1.2)

        # =============================================================
        # Act 5 — colour wash, layer by layer
        # =============================================================
        self.play(Transform(tag, hd.tag_text(
            "Act 5 / 水彩分层浸润：色彩一条条扫入，由浅入深", color=hd.INK, weight="BOLD")),
            run_time=0.8)

        labels = ["上色 1/3 · 豌豆表皮嫩绿自躯干向四肢蔓延",
                  "上色 2/3 · 牛仔帽与长靴注入焦糖皮革色",
                  "上色 3/3 · 三角领巾注入鲜红，白色四角星显现",
                  "高光点睛 · 瞳孔月牙高光点亮，炮口暗部立体感爆发"]
        holder = None
        full = None
        for name, label in zip(LAYERS, labels):
            anim, grp = self.sweep_color(os.path.join(ASSETS, name),
                                         n=7, size=face["size"],
                                         center=tuple(face["center"]))
            stage = [Transform(tag, hd.tag_text(
                label, color=ACCENT if name == LAYERS[-1] else MUTED,
                weight="BOLD" if name == LAYERS[-1] else "NORMAL")), anim]
            if holder is not None:
                stage.append(FadeOut(holder))
            self.play(*stage)
            if holder is not None:
                self.remove(holder)
            holder = grp
            self.wait(1.0)
        full = holder

        shadow = Ellipse(width=3.8, height=0.42, stroke_width=0)
        shadow.set_fill("#D4C7B0", 0.5).move_to([0.15, -3.18, 0]).set_z_index(18)
        # Colour has taken over — the ink must leave, or a later recoil slides the
        # colour image without the line art and leaks a ghost outline.
        self.play(FadeIn(shadow, scale=0.6), FadeOut(VGroup(*ink_layer)),
                  FadeOut(head_ref), run_time=1.2)
        self.remove(*ink_layer)
        self.wait(1.2)

        # =============================================================
        # Act 6 — recoil and rapid-fire peas
        # =============================================================
        self.play(Transform(tag, hd.tag_text(
            "Act 6 / 狂野西部！连发豌豆射击（后坐力翻帽 + 连环排珠）",
            color=RED, weight="BOLD")), run_time=0.8)
        self.wait(0.6)

        char = Group(full, shadow)
        muzzle_p = np.array([-1.78, 0.40, 0.0])

        def pea(scale=1.0):
            base = Circle(radius=0.32 * scale, stroke_color="#2E5A1C", stroke_width=2.5)
            base.set_fill(PAPER_GREEN, 1.0).move_to(muzzle_p)
            shade = Circle(radius=0.28 * scale, stroke_width=0)
            shade.set_fill(PAPER_DARK, 0.55).move_to(muzzle_p + np.array([0.04, -0.06, 0]) * scale)
            hi = Circle(radius=0.09 * scale, stroke_width=0)
            hi.set_fill(PAPER_HI, 0.9).move_to(muzzle_p + np.array([-0.09, 0.1, 0]) * scale)
            return VGroup(base, shade, hi).set_z_index(50)

        def blast(color="#FFFFFF", width=5.0, r=0.25):
            c = Circle(radius=r, stroke_color=color, stroke_width=width)
            return c.set_z_index(60).move_to(muzzle_p)

        self.play(char.animate.shift(np.array([0.4, 0.1, 0])).rotate(-0.07),
                  run_time=1.1, rate_func=rush_into)
        p1, b1 = pea(1.0), blast()
        self.play(char.animate.shift(np.array([-0.4, -0.1, 0])).rotate(0.07),
                  FadeIn(p1, scale=0.5), b1.animate.scale(3.5).set_opacity(0),
                  run_time=0.3, rate_func=wiggle)
        self.remove(b1)

        p2, b2 = pea(1.05), blast()
        self.play(p1.animate.shift(np.array([-3.0, 0.15, 0])).rotate(3 * np.pi),
                  char.animate.shift(np.array([0.15, 0.25, 0])).rotate(0.05),
                  FadeIn(p2, scale=0.6), b2.animate.scale(3.2).set_opacity(0),
                  run_time=0.45, rate_func=linear)
        self.remove(b2)

        p3, b3 = pea(1.0), blast("#A3E635", 4.5)
        self.play(p1.animate.shift(np.array([-3.5, 0.1, 0])).rotate(3 * np.pi),
                  p2.animate.shift(np.array([-3.0, -0.1, 0])).rotate(-3 * np.pi),
                  char.animate.shift(np.array([-0.15, -0.25, 0])).rotate(-0.05),
                  FadeIn(p3, scale=0.6), b3.animate.scale(3.2).set_opacity(0),
                  run_time=0.45, rate_func=linear)
        self.remove(p1, b3)

        self.play(p2.animate.shift(np.array([-3.5, -0.1, 0])).rotate(-3 * np.pi),
                  p3.animate.shift(np.array([-3.2, 0.1, 0])).rotate(3 * np.pi),
                  char.animate.shift(np.array([0.1, 0, 0])).rotate(-0.02),
                  run_time=0.45, rate_func=linear)
        self.remove(p2)
        self.play(p3.animate.shift(np.array([-3.5, 0.1, 0])).rotate(3 * np.pi),
                  char.animate.shift(np.array([-0.1, 0, 0])).rotate(0.02),
                  run_time=0.45, rate_func=linear)
        self.remove(p3)
        self.wait(0.4)

        self.play(Transform(tag, hd.tag_text("超级蓄力 · 终极巨型豌豆轰击！",
                                             color=RED, weight="BOLD")), run_time=0.45)
        self.play(char.animate.shift(np.array([0.55, 0.18, 0])).rotate(-0.14),
                  run_time=1.4, rate_func=rush_into)

        p4 = pea(1.8)
        s1, s2 = blast("#FFFFFF", 6.0, 0.35), blast(GOLD, 4.5, 0.15)
        self.play(char.animate.shift(np.array([-0.55, -0.18, 0])).rotate(0.14),
                  FadeIn(p4, scale=0.4),
                  s1.animate.scale(6.0).set_opacity(0),
                  s2.animate.scale(4.5).set_opacity(0),
                  run_time=0.3, rate_func=wiggle)
        self.remove(s1, s2)

        self.play(p4.animate.shift(np.array([-6.5, 0, 0])).rotate(5 * np.pi),
                  run_time=1.1, rate_func=linear)
        self.remove(p4)

        spray = VGroup(*[
            Dot(point=[-6.5 + np.random.uniform(-0.6, 0.6),
                       0.45 + np.random.uniform(-0.7, 0.7), 0],
                radius=np.random.uniform(0.08, 0.16), color=PAPER_GREEN).set_z_index(70)
            for _ in range(12)
        ])
        self.play(FadeIn(spray, scale=0.2), run_time=0.28)
        self.play(spray.animate.shift(np.array([0, -0.6, 0])).set_opacity(0), run_time=0.75)
        self.remove(spray)

        self.play(char.animate.rotate(0.03).shift(np.array([0.05, 0, 0])),
                  run_time=0.7, rate_func=wiggle)
        self.wait(0.8)
        self.play(Transform(tag, hd.tag_text(
            "Masterpiece · Western Cowboy Peashooter",
            font_size=15, color=hd.INK, weight="BOLD", font=hd.MONO_FONT)), run_time=1.1)
        self.wait(3.0)

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _draw(scene, stylus, paths, ink_layer, *, on_each=None):
        """Draw a list of stroke paths, keeping every ink mobject for later."""
        for i, p in enumerate(paths):
            if on_each is not None:
                on_each(i, p)
            anims, rt, mob = stylus.draw(p, stroke_width=INK_W, pen_speed=1.05)
            ink_layer.append(mob)
            scene.play(*anims, run_time=rt)

    def _build_eye(self, stylus, ink_layer, E, name, zoom, times, highlight, which):
        """One eye: parametric construction -> ink retrace -> blot fill -> highlight."""
        ex, ey, A, B, tilt = E
        c = (ex, ey)

        info = hd.trace_ellipse(c, A, B, tilt, run_time=times["trace"],
                                show_label=name, label_scale=zoom)
        self.play(*info["anims"], run_time=times["trace"])
        fade = [FadeOut(info["scaffold"])]
        if info["arm"] is not None:
            fade.append(FadeOut(info["arm"]))
        self.play(*fade, run_time=0.5)

        outline = hd.ellipse_outline(c, A, B, tilt)
        anims, rt, ring = stylus.retrace(outline, stroke_width=INK_W)
        ink_layer.append(ring)
        self.play(*anims, run_time=times["ink"])

        blot = hd.InkBlot(c, A * 0.97, B * 0.97, tilt)
        blot.set_z_index(-1)
        blot.rebuild(0.06)
        self.add(blot)
        ink_layer.append(blot)
        self.play(UpdateFromAlphaFunc(blot, hd.blot_grow), run_time=times["fill"],
                  rate_func=rush_into)

        # The larger eye's highlight was detected; the smaller one's is computed
        # from the same normalised offset (in the artwork it touches the outline,
        # so it is not an enclosed hole and cannot be detected directly).
        if highlight is not None:
            hx, hy, hr, nu, nv, ratio = highlight
            if which == 0:
                dot = Circle(radius=hr, stroke_width=0).set_fill(hd.PAPER, 1.0)
                dot.move_to([hx, hy, 0])
            else:
                t = np.radians(tilt)
                lx = ex + (nu * A) * np.cos(t) - (nv * B) * np.sin(t)
                ly = ey + (nu * A) * np.sin(t) + (nv * B) * np.cos(t)
                dot = Circle(radius=ratio * A, stroke_width=0).set_fill(hd.PAPER, 1.0)
                dot.move_to([lx, ly, 0])
            dot.set_z_index(3)
            ink_layer.append(dot)
            self.play(FadeIn(dot, scale=0.55), run_time=0.45)
            self.wait(0.25)

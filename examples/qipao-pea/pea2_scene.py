"""旗袍豌豆射手 · 逐笔手绘动画

素材来源全部由 source.png 现场派生：
  mkbitmap 高通滤波 -> lineart.png        骨架化 -> 逐笔笔画
  背景分割 -> lay_{white,green,red,blue,pink}.png  分条扫入上色
  moment_ellipse -> geo.json              眼睛/炮口的几何标定
"""
import json
import os

import numpy as np
from manim import (
    Circle, Create, Dot, Ellipse, FadeIn, FadeOut, Group, Line, MoveAlongPath,
    Rotate, Text, Transform, UpdateFromAlphaFunc, VGroup, config, linear,
    rush_into, smooth, wiggle,
)

import manim_handdraw as hd

config.frame_width = 16
config.frame_height = 9
config.background_color = hd.PAPER

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
LINEART = os.path.join(A, "lineart.png")
GEO = json.load(open(os.path.join(A, "geo.json")))

INK_W = 3.0
SIZE = 7.0
CENTER = (0.0, 0.05)
BREAK_Y = -0.70
ZOOM = 0.34
FOCUS = np.array([1.50, 0.60, 0.0])

PAPER_GREEN = "#8CE03E"
PAPER_DARK = "#4B8B1E"
PAPER_HI = "#D4FF78"
PETAL = "#F7BCD3"
RED = "#D9381E"
MUTED = "#8E8E93"
ACCENT = "#00A896"


class QipaoPea(hd.HandDrawScene):
    def construct(self):
        eyes = [tuple(e) for e in GEO["eyes"]]
        cav = tuple(GEO["cavity"])
        hl = GEO["highlights"]

        ui = hd.CanvasUI(title="Qipao Peashooter",
                         subtitle="旗袍豌豆 · 由彩图现场派生线稿与色层")
        self.add(ui)
        tag = hd.tag_text("Act 1 / 绘图工具装配：旋转圆规定位头部与炮口基准")
        self.play(FadeIn(tag), run_time=1.0)
        self.wait(0.6)

        ink_layer = []
        head_c = np.array([0.60, 0.90, 0.0])
        muzzle = np.array([cav[0], cav[1], 0.0])
        r_muzzle = cav[2]

        # ---------------- Act 1：圆规与基准几何 ----------------
        cross = VGroup(
            Line(head_c + np.array([-1.8, 0, 0]), head_c + np.array([1.8, 0, 0]),
                 stroke_color="#00B4D8", stroke_width=1.2, stroke_opacity=0.5),
            Line(head_c + np.array([0, -1.8, 0]), head_c + np.array([0, 1.8, 0]),
                 stroke_color="#00B4D8", stroke_width=1.2, stroke_opacity=0.5),
        )
        self.play(Create(cross), run_time=1.3)

        compass = hd.Compass(head_c, 1.30)
        self.play(FadeIn(compass), run_time=0.8)
        anims, head_ref = compass.draw_circle(run_time=3.0, dashed=False, color="#CBD5E1")
        self.play(*anims, run_time=3.0)
        self.play(FadeOut(compass), run_time=0.5)

        # 炮口基准：椭圆（开口是斜椭圆，用参数方程构造而不是圆规）
        self.play(Transform(tag, hd.tag_text(
            "炮口基准椭圆：由二阶矩从原画量出", color=MUTED)), run_time=0.6)
        info = hd.trace_ellipse((muzzle[0], muzzle[1]), cav[2], cav[3], cav[4],
                                run_time=2.2, show_label="炮口基准", label_scale=1.0)
        self.play(*info["anims"], run_time=2.2)
        mouth_guide = VGroup(info["scaffold"])
        if info["arm"] is not None:
            mouth_guide.add(info["arm"])
        self.wait(0.3)
        self.play(FadeOut(cross), run_time=0.8)
        self.wait(0.7)

        # ---------------- Act 2：逐笔手绘（上）----------------
        self.play(Transform(tag, hd.tag_text(
            "Act 2 / 逐笔手绘：等宽墨线逐笔生长，笔尖沿笔画实时跟随",
            color=hd.INK, weight="BOLD")), run_time=0.8)

        strokes = hd.from_image(LINEART, size=SIZE, center=CENTER,
                                merge_gap=14, merge_angle=0.15, clean_short=6.0,
                                drop_inside=eyes)
        upper = [p for p in strokes.paths if p[:, 1].mean() >= BREAK_Y]
        lower = [p for p in strokes.paths if p[:, 1].mean() < BREAK_Y]

        stylus = hd.Stylus()
        stylus.move_to(np.concatenate([upper[0][0], [0.0]]))
        self.play(FadeIn(stylus), run_time=0.5)
        self.play(Transform(tag, hd.tag_text(
            "笔 1/3 · 发丝与头部：蓬松银发、圆润豌豆头与喇叭炮口", color=hd.INK)),
            run_time=0.5)
        self.wait(0.3)
        self._draw(self, stylus, upper, ink_layer)

        # ---------------- Act 3：五官几何构造（特写）----------------
        self.play(FadeOut(tag), FadeOut(ui), run_time=0.5)
        self.play(self.camera.frame.animate.scale(ZOOM).move_to(FOCUS), run_time=1.3)

        def ztag(msg, color=MUTED, weight="NORMAL"):
            return hd.tag_text(msg, color=color, weight=weight, scale=ZOOM, center=FOCUS)

        tag = ztag("Act 3 / 眼睛数学构造：椭圆参数方程 x=a·cosθ , y=b·sinθ",
                   color=hd.INK, weight="BOLD")
        self.play(FadeIn(tag), run_time=0.6)
        self.wait(0.4)

        for i, (E, name, times) in enumerate([
            (eyes[0], "左眼 · 椭圆", dict(trace=1.6, ink=1.2, fill=0.7)),
            (eyes[1], "右眼 · 椭圆（同构）", dict(trace=1.3, ink=1.0, fill=0.6)),
        ]):
            self._build_eye(stylus, ink_layer, E, name, times, hl[i] if i < len(hl) else None)

        # ---- 炮口开口：参数方程构造 + 墨线描摹 + 填充 ----
        self.play(Transform(tag, ztag("Act 3 / 炮口开口：同法构造椭圆并填墨",
                                      color=hd.INK, weight="BOLD")), run_time=0.6)
        info = hd.trace_ellipse((muzzle[0], muzzle[1]), cav[2], cav[3], cav[4],
                                run_time=1.6, show_label="炮口开口", label_scale=ZOOM)
        self.play(*info["anims"], run_time=1.6)
        fade = [FadeOut(info["scaffold"])]
        if info["arm"] is not None:
            fade.append(FadeOut(info["arm"]))
        self.play(*fade, run_time=0.5)

        outline = hd.ellipse_outline((muzzle[0], muzzle[1]), cav[2], cav[3], cav[4])
        anims, rt, ring = stylus.retrace(outline, stroke_width=INK_W)
        ink_layer.append(ring)
        self.play(*anims, run_time=1.3)

        blot = hd.InkBlot((muzzle[0], muzzle[1]), cav[2] * 0.95, cav[3] * 0.95, cav[4])
        blot.set_z_index(-1)
        blot.rebuild(0.06)
        self.add(blot)
        ink_layer.append(blot)
        self.play(UpdateFromAlphaFunc(blot, hd.blot_grow), run_time=0.8, rate_func=rush_into)
        self.wait(0.5)

        # ---- 退出特写 ----
        self.play(FadeOut(tag), FadeOut(mouth_guide), FadeOut(head_ref),
                  run_time=0.4)
        self.play(self.camera.frame.animate.scale(1.0 / ZOOM).move_to([0, 0, 0]),
                  run_time=1.3)
        tag = hd.tag_text("Act 4 / 逐笔手绘（续）：笔墨继续向下蔓延至领巾与衫身",
                          color=hd.INK, weight="BOLD")
        self.play(FadeIn(ui), FadeIn(tag), run_time=0.6)

        # ---------------- Act 4：逐笔手绘（下）----------------
        self.play(Transform(tag, hd.tag_text(
            "笔 2/3 · 领巾：红巾折线与五角星", color=hd.INK)), run_time=0.5)
        marked = [False]

        def on_each(i, p):
            if not marked[0] and p[:, 1].mean() < -1.55:
                marked[0] = True
                self.play(Transform(tag, hd.tag_text(
                    "笔 3/3 · 衫身：立领盘扣、蓝白旗袍与襟前桃花", color=hd.INK)),
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

        # ---------------- Act 5：分色层浸润 ----------------
        self.play(Transform(tag, hd.tag_text(
            "Act 5 / 分色浸润：银发、绿头、红巾、蓝衫依次上色", color=hd.INK,
            weight="BOLD")), run_time=0.8)

        layers = [("lay_white.png", "上色 1/5 · 银发与白衫先行落墨"),
                  ("lay_green.png", "上色 2/5 · 豌豆头与炮口注入嫩绿"),
                  ("lay_red.png", "上色 3/5 · 红领巾上色，五角星留白"),
                  ("lay_blue.png", "上色 4/5 · 蓝白旗袍铺开，立领泛蓝"),
                  ("lay_pink.png", "上色 5/5 · 襟前桃花点染"),
                  ("full.png", "高光点睛 · 明暗与质感全面收束")]
        # 各分色层逐层叠加、互相保留：银发落下后不会被绿头盖掉，
        # 红巾上完也不会消失，画面是一层层累积到接近成品的。
        holders = []
        for name, label in layers:
            last = name == layers[-1][0]
            anim, grp = self.sweep_color(os.path.join(A, name), n=7, size=SIZE,
                                         center=CENTER)
            stage = [Transform(tag, hd.tag_text(
                label, color=ACCENT if last else MUTED,
                weight="BOLD" if last else "NORMAL")), anim]
            if last and holders:
                # 完整图铺上来的同时收掉分色层——它们已被完整图完全覆盖，
                # 这一步只是清理，画面上看不出任何变化。
                stage.append(FadeOut(Group(*holders)))
            self.play(*stage)
            if last and holders:
                for h in holders:
                    self.remove(h)
                holders = []
            holders.append(grp)
            self.wait(0.8)
        full = holders[-1]

        # 上色接管后墨线退场，否则角色一动就露出底下的线稿
        self.play(FadeOut(VGroup(*ink_layer)), run_time=1.2)
        self.remove(*ink_layer)
        self.wait(1.0)

        # ---------------- Act 6：连发豌豆 ----------------
        self.play(Transform(tag, hd.tag_text(
            "Act 6 / 发射！后坐力晃头 + 连环排珠", color=RED, weight="BOLD")),
            run_time=0.8)
        self.wait(0.5)

        char = Group(full)
        muzzle_p = np.array([2.62, 0.02, 0.0])

        def pea(scale=1.0):
            base = Circle(radius=0.30 * scale, stroke_color="#2E5A1C", stroke_width=2.5)
            base.set_fill(PAPER_GREEN, 1.0).move_to(muzzle_p)
            sh = Circle(radius=0.26 * scale, stroke_width=0)
            sh.set_fill(PAPER_DARK, 0.55).move_to(muzzle_p + np.array([0.04, -0.06, 0]) * scale)
            hi = Circle(radius=0.085 * scale, stroke_width=0)
            hi.set_fill(PAPER_HI, 0.9).move_to(muzzle_p + np.array([-0.08, 0.09, 0]) * scale)
            return VGroup(base, sh, hi).set_z_index(50)

        def blast(color="#FFFFFF", width=5.0, r=0.24):
            return Circle(radius=r, stroke_color=color, stroke_width=width).set_z_index(60).move_to(muzzle_p)

        # 吸气蓄力
        self.play(char.animate.shift(np.array([-0.35, 0.08, 0])).rotate(0.05),
                  run_time=1.1, rate_func=rush_into)
        p1, b1 = pea(1.0), blast()
        self.play(char.animate.shift(np.array([0.35, -0.08, 0])).rotate(-0.05),
                  FadeIn(p1, scale=0.5), b1.animate.scale(3.5).set_opacity(0),
                  run_time=0.3, rate_func=wiggle)
        self.remove(b1)

        p2, b2 = pea(1.05), blast()
        self.play(p1.animate.shift(np.array([3.2, 0.15, 0])).rotate(-3 * np.pi),
                  char.animate.shift(np.array([0.12, 0.2, 0])).rotate(-0.04),
                  FadeIn(p2, scale=0.6), b2.animate.scale(3.2).set_opacity(0),
                  run_time=0.45, rate_func=linear)
        self.remove(b2)

        p3, b3 = pea(1.0), blast("#A3E635", 4.5)
        self.play(p1.animate.shift(np.array([3.5, 0.1, 0])).rotate(-3 * np.pi),
                  p2.animate.shift(np.array([3.2, -0.1, 0])).rotate(3 * np.pi),
                  char.animate.shift(np.array([-0.12, -0.2, 0])).rotate(0.04),
                  FadeIn(p3, scale=0.6), b3.animate.scale(3.2).set_opacity(0),
                  run_time=0.45, rate_func=linear)
        self.remove(p1, b3)

        self.play(p2.animate.shift(np.array([3.5, -0.1, 0])).rotate(3 * np.pi),
                  p3.animate.shift(np.array([3.2, 0.1, 0])).rotate(-3 * np.pi),
                  char.animate.shift(np.array([0.08, 0, 0])).rotate(0.02),
                  run_time=0.45, rate_func=linear)
        self.remove(p2)
        self.play(p3.animate.shift(np.array([3.5, 0.1, 0])).rotate(-3 * np.pi),
                  char.animate.shift(np.array([-0.08, 0, 0])).rotate(-0.02),
                  run_time=0.45, rate_func=linear)
        self.remove(p3)
        self.wait(0.4)

        # 超级蓄力
        self.play(Transform(tag, hd.tag_text("超级蓄力 · 终极巨型豌豆！",
                                             color=RED, weight="BOLD")), run_time=0.45)
        self.play(char.animate.shift(np.array([-0.5, 0.15, 0])).rotate(0.1),
                  run_time=1.4, rate_func=rush_into)
        p4 = pea(1.8)
        s1, s2 = blast("#FFFFFF", 6.0, 0.34), blast("#E8B84B", 4.5, 0.15)
        self.play(char.animate.shift(np.array([0.5, -0.15, 0])).rotate(-0.1),
                  FadeIn(p4, scale=0.4),
                  s1.animate.scale(6.0).set_opacity(0),
                  s2.animate.scale(4.5).set_opacity(0),
                  run_time=0.3, rate_func=wiggle)
        self.remove(s1, s2)
        self.play(p4.animate.shift(np.array([6.5, 0, 0])).rotate(-5 * np.pi),
                  run_time=1.1, rate_func=linear)
        self.remove(p4)

        # 结尾：桃花瓣纷飞（呼应原画）
        petals = VGroup(*[
            self._petal(np.array([3.4 + np.random.uniform(-0.3, 0.4),
                                  0.05 + np.random.uniform(-0.5, 0.5), 0.0]),
                        np.random.uniform(0.09, 0.16), np.random.uniform(0, 360))
            for _ in range(14)
        ])
        self.play(FadeIn(petals, scale=0.3), run_time=0.35)
        self.play(petals.animate.shift(np.array([4.2, -0.9, 0])).set_opacity(0),
                  char.animate.rotate(-0.02), run_time=1.6, rate_func=linear)
        self.remove(petals)

        self.play(char.animate.rotate(0.015), run_time=0.6, rate_func=wiggle)
        self.wait(0.8)
        self.play(Transform(tag, hd.tag_text(
            "Masterpiece · Qipao Peashooter", font_size=15, color=hd.INK,
            weight="BOLD", font=hd.MONO_FONT)), run_time=1.1)
        self.wait(3.0)

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _petal(center, size, rot):
        """一枚桃花瓣：两段对称弧组成的柳叶形。"""
        from manim import ArcBetweenPoints
        a = ArcBetweenPoints(center + np.array([-size, 0, 0]),
                             center + np.array([size, 0, 0]), angle=1.1,
                             stroke_color=PETAL, stroke_width=2.0)
        b = ArcBetweenPoints(center + np.array([-size, 0, 0]),
                             center + np.array([size, 0, 0]), angle=-1.1,
                             stroke_color=PETAL, stroke_width=2.0)
        g = VGroup(a, b).set_fill(PETAL, 0.75)
        g.rotate(np.radians(rot))
        return g

    @staticmethod
    def _draw(scene, stylus, paths, ink_layer, *, on_each=None):
        for i, p in enumerate(paths):
            if on_each is not None:
                on_each(i, p)
            anims, rt, mob = stylus.draw(p, stroke_width=INK_W,
                                         pen_speed=1.5, min_time=0.10)
            ink_layer.append(mob)
            scene.play(*anims, run_time=rt)

    def _build_eye(self, stylus, ink_layer, E, name, times, highlight):
        ex, ey, A, B, tilt = E
        info = hd.trace_ellipse((ex, ey), A, B, tilt, run_time=times["trace"],
                                show_label=name, label_scale=ZOOM)
        self.play(*info["anims"], run_time=times["trace"])
        fade = [FadeOut(info["scaffold"])]
        if info["arm"] is not None:
            fade.append(FadeOut(info["arm"]))
        self.play(*fade, run_time=0.5)

        outline = hd.ellipse_outline((ex, ey), A, B, tilt)
        anims, rt, ring = stylus.retrace(outline, stroke_width=INK_W)
        ink_layer.append(ring)
        self.play(*anims, run_time=times["ink"])

        blot = hd.InkBlot((ex, ey), A * 0.97, B * 0.97, tilt)
        blot.set_z_index(-1)
        blot.rebuild(0.06)
        self.add(blot)
        ink_layer.append(blot)
        self.play(UpdateFromAlphaFunc(blot, hd.blot_grow), run_time=times["fill"],
                  rate_func=rush_into)

        if highlight:
            hx, hy, hr = highlight
            dot = Circle(radius=hr, stroke_width=0).set_fill(hd.PAPER, 1.0)
            dot.move_to([hx, hy, 0]).set_z_index(3)
            ink_layer.append(dot)
            self.play(FadeIn(dot, scale=0.55), run_time=0.45)
        self.wait(0.3)

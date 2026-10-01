"""秩序神女（奥奇传说冠军皮肤）· 铅笔稿描摹 + 原图上色。

本目录已包含渲染所需的线稿、分层色图和五官定位数据。
执行 ``manim -qh --fps 60 order_goddess.py OrderGoddess`` 即可渲染。
"""
import json
import os

import numpy as np
from manim import (
    Circle, Create, Dot, FadeIn, FadeOut, Group, ImageMobject, Line,
    MoveAlongPath, Transform, UpdateFromAlphaFunc, VMobject, VGroup, config,
    linear, rush_into, smooth, wiggle, UP,
)

import manim_handdraw as hd

config.frame_width = 16
config.frame_height = 9
config.background_color = hd.PAPER

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
GEO = json.load(open(os.path.join(A, "eye.json")))

INK_W = 3.0
SIZE = 7.6               # 竖向大构图 1200x972 → 7.6 高恰好占满
CENTER = (0.0, -0.05)

TAG_FS = 33
TAG_Y = -4.02
LAYER_FADE = 4.0
LAYER_PAUSE = 1.6

PEN_SPEED = 5.0          # 1502 笔 / 1015 单位 → 描摹约 3.4 分钟
MIN_TIME = 0.035

ZOOM = 0.26              # 全图退幕后放心深推：脸占画面 ~24%
FOCUS = np.array([-0.0665, 1.963, 0.0])   # 双眼中点（网格实测）

# 五官窗口（manim 坐标 x0, x1, y下限, y上限）——切段按此序解包：
# 眼睛区域切净后贴原稿眼贴片；嘴巴区域切净后由笔尖手绘淡弧
EYES_WIN = (-0.344, 0.2815, 1.866, 2.061)
MOUTH_WIN = (-0.185, 0.062, 1.70, 1.87)   # 嘴+鼻记号全切：鼻嘴都不画，上色由原图带

ACCENT = "#00A896"
GOLD = "#E8B84B"
MUTED = "#8E8E93"
FX_CENTER = np.array([0.0, 2.19, 0.0])    # 结尾动效中心：金冠


class OrderGoddess(hd.HandDrawScene):
    def _tag(self, msg, *, color=None, weight="NORMAL", scale=1.0, center=None,
             font=None):
        t = hd.tag_text(msg, font_size=TAG_FS,
                        color=MUTED if color is None else color,
                        weight=weight, scale=scale,
                        center=np.zeros(3) if center is None else center,
                        y=TAG_Y, font=font)
        t.set_z_index(40)
        return t

    @staticmethod
    def _layer(name, *, z=20):
        img = ImageMobject(os.path.join(A, name))
        img.scale_to_fit_height(SIZE)
        img.move_to([CENTER[0], CENTER[1], 0.0])
        img.set_z_index(z)
        return img

    @staticmethod
    def _face_ink(fname, cx, cy, h, ink_layer):
        """铅笔稿五官贴片：透明底墨色 PNG，置于色层之上逐步淡入。"""
        img = ImageMobject(os.path.join(A, fname))
        img.scale_to_fit_height(h)
        img.move_to([cx, cy, 0]).set_z_index(25)
        ink_layer.append(img)
        return img

    def construct(self):
        eyes = [tuple(e) for e in GEO["eyes"]]

        ui = hd.CanvasUI(title="Order Goddess",
                         subtitle="秩序神女 · 铅笔稿描摹 + 原图上色")
        self.add(ui)
        tag = self._tag("Act 1 / 绘图工具装配：旋转圆规定位面容基准圆")
        self.play(FadeIn(tag), run_time=1.0)
        self.wait(0.5)

        ink_layer = []

        # =============================================================
        # Act 1 — 面容基准圆
        # =============================================================
        face_c = FOCUS.copy()
        compass = hd.Compass(face_c, 0.65)
        self.play(FadeIn(compass), run_time=0.7)
        anims, face_ref = compass.draw_circle(run_time=2.2, dashed=False, color="#CBD5E1")
        self.play(*anims, run_time=2.2)
        self.wait(0.3)
        self.play(FadeOut(compass), run_time=0.5)
        self.wait(0.5)

        # =============================================================
        # Act 2 — 逐笔描摹：发型与颜面
        # =============================================================
        self.play(Transform(tag, self._tag(
            "Act 2 / 铅笔稿描摹：等宽墨线逐笔生长，笔尖沿笔画实时跟随",
            color=hd.INK, weight="BOLD")), run_time=0.8)

        strokes = hd.from_image(os.path.join(A, "lineart.png"), size=SIZE,
                                center=CENTER, merge_gap=36, merge_angle=0.15,
                                clean_short=8)

        # 五官窗口切段：眼睛/鼻嘴区域从笔画里清掉，改用铅笔稿贴片逐步淡入；
        # 穿越窗口的刘海/发丝只切窗内段、保住窗外主体。
        windows = [EYES_WIN, MOUTH_WIN]
        cut_paths = []
        for p in strokes.paths:
            p = np.asarray(p, float)
            inside = np.zeros(len(p), bool)
            for wx0, wx1, wy0, wy1 in windows:
                inside |= ((p[:, 0] >= wx0) & (p[:, 0] <= wx1) &
                           (p[:, 1] >= wy0) & (p[:, 1] <= wy1))
            keep = ~inside
            for s, e in np.flatnonzero(np.diff(np.r_[False, keep, False])).reshape(-1, 2):
                q = p[s:e]
                if len(q) >= 2 and np.linalg.norm(np.diff(q[:, :2], axis=0), axis=1).sum() > 0.05:
                    cut_paths.append(q)
        strokes.paths = cut_paths

        # 密集区自适应线宽
        from scipy.spatial import cKDTree
        all_pts = np.vstack(strokes.paths)
        ids = np.repeat(np.arange(len(strokes.paths)), [len(p) for p in strokes.paths])
        tree = cKDTree(all_pts)
        dens = []
        for i, p in enumerate(strokes.paths):
            lists = tree.query_ball_point(p[::3], 0.14)
            total = sum(len(n) for n in lists)
            own = sum(int((ids[n] == i).sum()) for n in lists)
            dens.append((total - own) / max(1, len(lists)))
        dens = np.array(dens)
        thin_th = float(np.percentile(dens, 70))
        widths = [1.8 if dd > thin_th else 2.4 for dd in dens]
        pairs = list(zip(strokes.paths, widths))

        head = [q for q in pairs if q[0][:, 1].mean() >= 1.5]
        torso = [q for q in pairs if -0.55 <= q[0][:, 1].mean() < 1.5]
        lower = [q for q in pairs if q[0][:, 1].mean() < -0.55]

        stylus = hd.Stylus()
        stylus.move_to(np.concatenate([head[0][0][0], [0.0]]))
        self.play(FadeIn(stylus), run_time=0.5)
        self.play(Transform(tag, self._tag(
            "笔 1/3 · 冠冕发丝：神冕华彩与流云长发", color=hd.INK)), run_time=0.5)
        self._draw(stylus, head, ink_layer)

        # =============================================================
        # Act 3 — 面容特写：假装构造 + 铅笔五官贴片逐步淡入
        # =============================================================
        self.play(FadeOut(tag), FadeOut(ui), FadeOut(face_ref), FadeOut(stylus),
                  run_time=0.5)

        # 反聚光：这角色头部装饰极密，任何保留半径都会让特写变成乱麻——
        # 全图铅笔稿整体退到 0.08，让贴片五官作为唯一主角浮现，拉远再恢复。
        # （逐笔 .animate，绝不经 VGroup——会把笔画压到相机框下消失）
        dim_mobs = [m for m in ink_layer if not isinstance(m, ImageMobject)]

        spot = [self.camera.frame.animate.scale(ZOOM).move_to(FOCUS)]
        # 只动描边透明度：set_opacity 会连 fill 一起恢复成 1，
        # 骨架路径被当多边形填充出白色斑块，正好盖死王冠
        spot += [m.animate.set_stroke(opacity=0.04) for m in dim_mobs]
        self.play(*spot, run_time=1.3)

        tag = self._tag("Act 3 / 眼睛数学构造：椭圆参数方程 x=a·cosθ , y=b·sinθ",
                        color=hd.INK, weight="BOLD", scale=ZOOM, center=FOCUS)
        self.play(FadeIn(tag), run_time=0.6)
        self.wait(0.4)

        # 假装圆规/参数方程构造（演出），定稿由贴片呈现
        eyes_draw = [(e[0], e[1], e[2] * 0.72, e[3] * 0.72, e[4]) for e in eyes]
        for E, name, times in [
            (eyes_draw[0], "左眼 · 椭圆", dict(trace=1.6)),
            (eyes_draw[1], "右眼 · 椭圆（同构）", dict(trace=1.4)),
        ]:
            self._show_eye_construct(E, name, times)

        # 眼睛贴片：原铅笔稿复刻，压过所有底稿乱线
        self.play(FadeIn(self._face_ink("eyes_ink.png", -0.0312, 1.9635,
                                        0.1950, ink_layer)), run_time=1.6)
        self.wait(0.6)
        # 嘴巴贴片：原铅笔稿嘴线复刻（鼻子不画，上色时由原图带出）
        self.play(FadeIn(self._face_ink("mouth_ink.png", -0.0615, 1.7480,
                                        0.0960, ink_layer)), run_time=1.3)
        self.wait(0.6)

        self.play(FadeOut(tag), run_time=0.4)
        out = [self.camera.frame.animate.scale(1.0 / ZOOM).move_to([0, 0, 0])]
        out += [m.animate.set_stroke(opacity=1.0) for m in dim_mobs]
        self.play(*out, run_time=1.3)
        # 保底：墨线全部提回渲染顺序最上层
        self.remove(*ink_layer)
        self.add(*ink_layer)

        tag = self._tag("Act 4 / 描摹（续）：衣饰、佩饰与裙摆",
                        color=hd.INK, weight="BOLD")
        self.play(FadeIn(ui), FadeIn(tag), FadeIn(stylus), run_time=0.6)

        # =============================================================
        # Act 4 — 描摹：躯干与下半身
        # =============================================================
        self.play(Transform(tag, self._tag(
            "笔 2/3 · 竖琴华服：鎏金竖琴与素纱礼服", color=hd.INK)), run_time=0.5)
        self._draw(stylus, torso, ink_layer)
        self.play(Transform(tag, self._tag(
            "笔 3/3 · 裙摆赤足：蝶舞缎带与流苏长裙", color=hd.INK)), run_time=0.5)
        self._draw(stylus, lower, ink_layer)

        self.play(FadeOut(stylus), run_time=0.6)
        self.wait(0.6)

        self.play(Transform(tag, self._tag(
            f"白描定稿 · 全 {len(strokes)} 笔，与铅笔稿逐线对齐",
            color=ACCENT, weight="BOLD")), run_time=0.7)
        scan = Line([-3.8, 3.4, 0], [3.8, 3.4, 0], stroke_color="#00B4D8",
                    stroke_width=3.0, stroke_opacity=0.8)
        self.play(scan.animate.move_to([0, -3.4, 0]), run_time=2.4, rate_func=smooth)
        self.play(FadeOut(scan), run_time=0.35)
        self.wait(1.0)

        # =============================================================
        # Act 5 — 原图分层浸润上色（层层累积互留，最后 full 统一收束）
        # =============================================================
        self.play(Transform(tag, self._tag(
            "Act 5 / 原图上色：缎带、肌肤、素裙、蓝发、金饰、蝶影依次浸润",
            color=hd.INK, weight="BOLD")), run_time=0.8)

        # 由浅入深：缎带星光 → 肌肤 → 素裙 → 蓝发 → 金饰 → 蝶影
        stages = [
            ("lay_ribbon.png",   "上色 1/6 · 缎带星光绕身"),
            ("lay_skin.png",     "上色 2/6 · 温润肌肤"),
            ("lay_white.png",    "上色 3/6 · 素纱礼服"),
            ("lay_hair.png",     "上色 4/6 · 湛蓝长发"),
            ("lay_gold.png",     "上色 5/6 · 鎏金竖琴"),
            ("lay_butterfly.png", "上色 6/6 · 蝶影纷飞"),
            ("full.png",         "最后一并点睛 · 秩序神女跃然纸上"),
        ]
        holders, partials = [], []
        for name, label in stages:
            last = name == stages[-1][0]
            grp = self._layer(name)
            stage = [Transform(tag, self._tag(
                label, color=ACCENT if last else MUTED,
                weight="BOLD" if last else "NORMAL")),
                FadeIn(grp, shift=UP * 0.05)]
            self.play(*stage, run_time=LAYER_FADE)
            holders.append(grp)
            if not last:
                partials.append(grp)
            self.wait(LAYER_PAUSE)
        full = holders[-1]

        # 分色层与墨线等完整图铺好后才收（Group：ink_layer 含贴片图片）
        self.play(FadeOut(Group(*ink_layer)), FadeOut(Group(*partials)),
                  run_time=1.2)
        self.remove(*ink_layer, *partials)
        self.wait(1.0)

        # =============================================================
        # Act 6 — 角色专属结尾动效
        # =============================================================
        # 金冠光晕、星屑与镜头缓推组成角色专属结尾。
        self.play(Transform(tag, self._tag(
            "Act 6 / 神辉觉醒 · 秩序降临", color=ACCENT, weight="BOLD")),
            run_time=0.7)

        glow = Circle(radius=0.35, stroke_color=GOLD, stroke_width=4.5)
        glow.move_to(FX_CENTER).set_z_index(50)
        self.play(Create(glow), run_time=0.8, rate_func=smooth)
        self.play(glow.animate.scale(2.5).set_opacity(0), run_time=0.7)

        rng = np.random.default_rng(42)
        sparks = VGroup(*[
            Dot(radius=np.random.uniform(0.015, 0.04),
                color="#FFE494" if k % 2 else "#75E6FF")
            .move_to([rng.uniform(-3.5, 3.5), rng.uniform(-3.2, 3.2), 0])
            .set_z_index(50)
            for k in range(22)
        ])
        self.play(FadeIn(sparks, scale=0.3), run_time=0.4)
        self.play(self.camera.frame.animate.scale(0.93).move_to([0.0, 0.4, 0]),
                  sparks.animate.shift(UP * 0.65).set_opacity(0),
                  run_time=2.0, rate_func=smooth)
        self.remove(sparks)
        self.wait(0.5)

        self.play(Transform(tag, self._tag(
            "Masterpiece · Order Goddess 秩序神女", color=ACCENT,
            weight="BOLD", font=hd.MONO_FONT)), run_time=1.1)
        self.wait(4.0)

    # ---------------------------------------------------------------- helpers
    def _draw(self, stylus, pairs, ink_layer):
        for p, w in pairs:
            anims, rt, mob = stylus.draw(p, stroke_width=w,
                                         pen_speed=PEN_SPEED, min_time=MIN_TIME)
            ink_layer.append(mob)
            self.play(*anims, run_time=rt)

    def _show_eye_construct(self, E, name, times):
        """假装用参数方程构造椭圆（演出），不落墨——定稿由贴片呈现。"""
        ex, ey, Ea, Eb, tilt = E
        info = hd.trace_ellipse((ex, ey), Ea, Eb, tilt, run_time=times["trace"],
                                show_label=name, label_scale=ZOOM)
        self.play(*info["anims"], run_time=times["trace"])
        fade = [FadeOut(info["scaffold"]), FadeOut(info["path"])]
        if info["arm"] is not None:
            fade.append(FadeOut(info["arm"]))
        self.play(*fade, run_time=0.4)

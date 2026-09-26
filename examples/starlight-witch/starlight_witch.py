"""星辉魔女 · 铅笔稿描摹 + 原图上色

与烈焰女王同一工作流。这张的特点：
  - 横构图（1.55 宽高比），双眼沿对角线一高一低（头的强倾斜）
  - 主色是蓝发（与淡蓝背景同色相族，靠饱和度区分）
  - 嘴极小且淡（10px），三点定弧
"""
# ============================================================
# ★ 最终修改版 ★（2026-09-25 定稿）
# 对应成片：星辉魔女_重描加粗_2.0版.mp4（1080p60，4分44秒）
# 本文件自包含：眼睛修复版场景 + 重描加粗线宽（refine 已内联），
# 渲染仅需同级 assets/ 素材目录。
# ============================================================
import json
import os

import numpy as np
from manim import (
    Circle, Create, Dot, FadeIn, FadeOut, Group, ImageMobject, Line,
    MoveAlongPath, Transform, UpdateFromAlphaFunc, VGroup, config, linear,
    rush_into, smooth, wiggle, UP,
)

import manim_handdraw as hd

config.frame_width = 16
config.frame_height = 9
config.background_color = hd.PAPER

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
GEO = json.load(open(os.path.join(A, "eye.json")))

INK_W = 3.0
SIZE = 7.3
CENTER = (0.0, 0.05)
MOUTH_CENTER = (-1.2784, 1.7954)

TAG_FS = 33
TAG_Y = -4.02
LAYER_FADE = 4.0
LAYER_PAUSE = 1.6

PEN_SPEED = 2.4
MIN_TIME = 0.07

ZOOM = 0.50
FOCUS = np.array([-1.38, 2.00, 0.0])     # 双眼中点（对角线中部）

ACCENT = "#00A896"
GOLD = "#E8B84B"
MUTED = "#8E8E93"
WAND = np.array([-3.39, 2.16, 0.0])      # 魔杖星尖



# ============================================================
# 局部矢量重描（原 refine_details.py，已内联）——线宽与几何为
# 「星辉魔女_重描加粗_2.0版.mp4」渲染所用的最终定稿数值。
# ============================================================
"""局部矢量重描。坐标使用 1561×1008 原铅笔稿，保留区域外所有笔画。"""
import numpy as np
class Path:
    def __init__(self, vertices):
        self.vertices = np.asarray(vertices, float)

    def contains_points(self, points):
        x, y = points.T
        inside = np.zeros(len(points), dtype=bool)
        for a, b in zip(self.vertices, np.roll(self.vertices, -1, axis=0)):
            if a[1] == b[1]:
                continue
            inside ^= ((a[1] > y) != (b[1] > y)) & (x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])
        return inside

SCALE = 7.3 / 1008

def world(points):
    p = np.asarray(points, dtype=float).copy()
    p[:, 0] = (p[:, 0] - 780.5) * SCALE
    p[:, 1] = 0.05 + (504 - p[:, 1]) * SCALE
    return p

def pixels(points):
    p = np.asarray(points, dtype=float)[:, :2].copy()
    p[:, 0] = p[:, 0] / SCALE + 780.5
    p[:, 1] = 504 - (p[:, 1] - 0.05) / SCALE
    return p

def refine(paths, widths):
    # 只切除落在重描区域内部的线段，不丢弃穿过区域的整根头发。
    regions = [
        [(587,327),(630,327),(677,371),(650,398),(630,433),
         (642,454),(622,468),(580,453),(565,425),(566,378)],
        [(628, 285), (649, 275), (668, 270), (686, 278),
         (717, 280), (752, 293), (764, 329), (758, 360),
         (742, 378), (700, 380), (667, 365), (634, 346), (619, 319)],
        [(267, 373), (305, 345), (379, 324), (431, 326),
         (445, 348), (429, 374), (408, 427), (427, 480),
         (456, 529), (452, 561), (408, 577), (329, 558),
         (279, 507), (247, 453), (249, 406)],
    ]
    masks = [Path(poly) for poly in regions]
    result = []
    for p, width in zip(paths, widths):
        p = pixels(p)
        dense = []
        for a, b in zip(p[:-1], p[1:]):
            n = max(1, int(np.ceil(np.linalg.norm(b-a) / 0.7)))
            dense.extend(a + (b-a)*t for t in np.arange(n)/n)
        dense.append(p[-1])
        dense = np.array(dense)
        keep = ~np.logical_or.reduce([m.contains_points(dense) for m in masks])
        edges = np.flatnonzero(np.diff(np.r_[False, keep, False])).reshape(-1, 2)
        for start, end in edges:
            q = dense[start:end]
            if len(q) > 1 and np.linalg.norm(np.diff(q, axis=0), axis=1).sum() > 1.2:
                result.append((world(q), width))

    original_ends = np.array([p for path, _ in result for p in pixels(path)[[0,-1]]])

    def line(points, w=1.65):
        result.append((world(points), w))

    def curve(start, segments, w=1.65):
        out = [np.asarray(start, float)]
        a = out[0]
        for c1, c2, end in segments:
            b, c, d = map(lambda x: np.asarray(x, float), (c1,c2,end))
            t = np.linspace(0,1,25)[1:,None]
            out.extend((1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t*t*c + t**3*d)
            a=d
        out = np.array(out)
        # 长弧叠加低频垂直抖动，模拟铅笔手绘的自然摆动，
        # 避免与提取笔画的玻璃光滑贝塞尔形成"两个 AI"的违和感。
        if len(out) >= 3:
            arc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(out, axis=0), axis=1))])
            if arc[-1] > 60:
                rng = np.random.default_rng(int(abs(out[0][0] * 7 + out[0][1] * 13 + w * 101)) + 7)
                step = 26.0
                n_ctrl = max(2, int(arc[-1] / step) + 2)
                ctrl = rng.normal(0.0, 1.1, n_ctrl)
                noise = np.interp(arc / step, np.arange(n_ctrl), ctrl)
                tan = np.gradient(out, axis=0)
                tan /= np.maximum(np.linalg.norm(tan, axis=1, keepdims=True), 1e-9)
                nrm = np.column_stack([-tan[:, 1], tan[:, 0]])
                out = out + nrm * noise[:, None]
        result.append((world(out),w))

    # 领口双边框：上方颈圈、下方月牙形护领。
    curve((651,289), [((665,276),(684,279),(697,293))], 2.1)
    curve((652,293), [((666,282),(682,284),(694,298))], 2.0)
    curve((653,294), [((669,302),(672,314),(668,324)),
                      ((686,331),(695,329),(699,329))], 1.9)
    curve((668,324), [((659,329),(651,329),(642,325))], 1.9)
    curve((642,325), [((656,345),(684,365),(715,368)),
                      ((744,374),(755,340),(753,313)),
                      ((747,303),(739,298),(729,298))], 2.3)
    curve((647,331), [((663,349),(686,362),(714,364)),
                      ((739,367),(749,338),(747,315))], 2.0)
    curve((731,286), [((738,298),(743,312),(746,326))], 1.9)
    # 宝石不是圆圈：倾斜的盾状外框、内框与三角切面。
    curve((699,288), [((713,288),(728,297),(735,309)),
                      ((738,324),(735,338),(731,350)),
                      ((713,350),(697,341),(690,331)),
                      ((688,317),(691,299),(699,288))], 2.2)
    curve((701,293), [((714,295),(725,302),(730,312)),
                      ((733,325),(730,336),(727,344)),
                      ((714,342),(702,336),(696,329)),
                      ((694,316),(697,301),(701,293))], 2.1)
    line([(702,298),(712,314),(706,327),(700,327),(702,298)],2.0)
    line([(712,314),(727,313),(723,338),(706,327),(712,314)],2.0)
    line([(712,314),(723,338)],2.0)
    line([(702,298),(727,313)],2.0)
    # 克制保留护领卷纹，给宝石留出空隙。
    curve((664,338), [((672,328),(678,333),(672,340)),
                      ((669,344),(677,345),(682,341))],2.0)
    curve((684,348), [((679,354),(688,359),(694,355)),
                      ((700,352),(694,347),(695,348))],2.0)
    curve((704,359), [((718,365),(729,361),(727,354)),
                      ((723,350),(720,356),(723,358))],2.0)
    curve((741,333), [((730,324),(735,321),(740,326)),
                      ((744,329),(739,333),(736,332))],2.0)
    # 画面左侧卷发主轮廓，连接根部到回卷发梢。
    # 线宽对齐主画档位（外粗内细渐变），消除与提取笔画粗细割裂的痕迹。
    curve((431,326), [((385,331),(300,350),(268,390)),
                      ((237,430),(257,476),(286,513)),
                      ((319,558),(391,578),(445,556))],3.0)
    curve((428,339), [((383,345),(313,364),(285,401)),
                      ((261,438),(287,493),(322,526)),
                      ((353,553),(406,566),(445,556))],2.8)
    curve((421,353), [((372,364),(320,385),(306,423)),
                      ((290,471),(326,515),(356,530)),
                      ((389,548),(419,544),(439,534))],2.6)
    curve((277,396), [((261,440),(285,487),(311,511))],2.2)
    # 肩前细长发束：消除与衣领混接的回折线，让发梢只回卷一次。
    curve((599,333), [((589,357),(577,391),(582,417)),
                      ((584,439),(607,457),(624,451)),
                      ((631,448),(628,439),(626,439))],2.8)
    curve((608,337), [((596,365),(588,397),(592,419)),
                      ((596,438),(611,447),(624,451))],2.6)
    curve((580,351), [((570,375),(566,406),(573,426)),
                      ((581,445),(600,458),(619,459))],2.5)
    # 领饰左下方三条纤细连接，避免旧轮廓连成一团黑结。
    line([(647,338),(631,364)],1.9)
    line([(665,353),(656,389)],1.9)
    line([(690,369),(683,390)],1.9)
    for cx, cy in [(630,365),(655,391),(682,392)]:
        t=np.linspace(0,2*np.pi,25)
        line(np.column_stack([cx+3*np.cos(t),cy+4*np.sin(t)]),1.9)
    curve((667,367), [((658,388),(647,413),(634,434))],1.9)
    # 补回被领饰清线区域触及的下颌、颈部与衣领连接。
    curve((623,291), [((633,292),(644,292),(651,289))],1.9)
    curve((662,256), [((660,270),(656,284),(651,289))],2.1)
    curve((674,265), [((676,279),(681,287),(686,291))],1.9)
    curve((636,327), [((626,336),(622,345),(617,355))],1.9)
    # 左发束两端接到保留轮廓的最近端点，避免局部重描产生悬空断口。
    # （410,376)/(400,520) 属已删除的误笔线，不再补连接。
    for endpoint in [(431,326),(428,339),(421,353),
                     (445,556),(439,534)]:
        distances = np.linalg.norm(original_ends-np.array(endpoint), axis=1)
        k = np.argmin(distances)
        if distances[k] < 24:
            line([endpoint, original_ends[k]],2.4)
    return result


class StarWitch(hd.HandDrawScene):
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

    def construct(self):
        eyes = [tuple(e) for e in GEO["eyes"]]

        ui = hd.CanvasUI(title="Star Witch",
                         subtitle="星辉魔女 · 铅笔稿描摹 + 原图上色")
        self.add(ui)
        tag = self._tag("Act 1 / 绘图工具装配：旋转圆规定位面容基准圆")
        self.play(FadeIn(tag), run_time=1.0)
        self.wait(0.5)

        ink_layer = []

        # =============================================================
        # Act 1 — 面容基准圆
        # =============================================================
        face_c = np.array([-1.38, 2.00, 0.0])
        compass = hd.Compass(face_c, 0.55)
        self.play(FadeIn(compass), run_time=0.7)
        anims, face_ref = compass.draw_circle(run_time=2.2, dashed=False, color="#CBD5E1")
        self.play(*anims, run_time=2.2)
        self.wait(0.3)
        self.play(FadeOut(compass), run_time=0.5)
        self.wait(0.5)

        # =============================================================
        # Act 2 — 逐笔描摹：发与颜
        # =============================================================
        self.play(Transform(tag, self._tag(
            "Act 2 / 铅笔稿描摹：等宽墨线逐笔生长，笔尖沿笔画实时跟随",
            color=hd.INK, weight="BOLD")), run_time=0.8)

        strokes = hd.from_image(os.path.join(A, "lineart.png"), size=SIZE,
                                center=CENTER, merge_gap=26, merge_angle=0.15,
                                clean_short=5.0)
        # 左眼周围的刘海与眼线在原线稿中被合并成了交叉笔画。
        # 降低命中比例并扩大左眼清线区，避免发丝再穿过眼睑。
        clear_features = [
            (eyes[0][0], eyes[0][1], eyes[0][2] * 1.25,
             eyes[0][3] * 1.25, eyes[0][4]),
            eyes[1],
            # 原线稿里这条嘴线方向错误，必须先从主线层清除；
            # 否则后面叠加正确的淡短线，画面仍会显示成“竖嘴”。
            (MOUTH_CENTER[0], MOUTH_CENTER[1], 0.075, 0.060, 0.0),
        ]
        strokes = strokes.filter_inside(clear_features, max_fraction=0.12)
        # 密集区自适应线宽：头身连接、胸饰这类线条聚集处放细（用户反馈）
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
        thin_th = float(np.percentile(dens, 78))
        widths = [2.1 if dd > thin_th else INK_W for dd in dens]
        # 局部重描函数 refine 已内联至本文件末尾的模块级定义
        pairs = refine(strokes.paths, widths)
        ys = np.array([p[:, 1].mean() for p in strokes.paths])
        head = [q for q in pairs if q[0][:, 1].mean() >= 0.90]
        torso = [q for q in pairs if -0.90 <= q[0][:, 1].mean() < 0.90]
        legs = [q for q in pairs if q[0][:, 1].mean() < -0.90]

        stylus = hd.Stylus()
        stylus.move_to(np.concatenate([head[0][0][0], [0.0]]))
        self.play(FadeIn(stylus), run_time=0.5)
        self.play(Transform(tag, self._tag(
            "笔 1/3 · 发与颜：流云长发、尖冠与斜眸", color=hd.INK)), run_time=0.5)
        self._draw(stylus, head, ink_layer)

        # =============================================================
        # Act 3 — 面容特写：双眼椭圆 + 微笑弧
        # =============================================================
        self.play(FadeOut(tag), FadeOut(ui), FadeOut(face_ref), FadeOut(stylus),
                  run_time=0.5)
        # 聚光：远离面部的墨线暂时调暗 —— 这张是躺姿对角构图，镜头推近后
        # 浓密发丝的粗墨线会盖住五官构造，只留面部附近清晰即可读。
        dim_mobs, keep_mobs = [], []
        for mob in ink_layer:
            pts = mob.points
            if not len(pts):
                continue
            dist = float(np.linalg.norm(pts[:, :2] - FOCUS[:2], axis=1).min())
            (keep_mobs if dist < 0.85 else dim_mobs).append(mob)
        spot = [self.camera.frame.animate.scale(ZOOM).move_to(FOCUS)]
        if dim_mobs:
            spot.append(VGroup(*dim_mobs).animate.set_opacity(0.12))
        self.play(*spot, run_time=1.3)

        tag = self._tag("Act 3 / 眼睛数学构造：椭圆参数方程 x=a·cosθ , y=b·sinθ",
                        color=hd.INK, weight="BOLD", scale=ZOOM, center=FOCUS)
        self.play(FadeIn(tag), run_time=0.6)
        self.wait(0.4)

        # 恢复原稿眼睛上方两缕最传神的小刘海。它们单独成层并置于眼睛下方，
        # 因而保留发型神态，同时不会再次穿过或盖住眼睑。
        bangs = ImageMobject(os.path.join(A, "bangs_ink.png"))
        bangs.scale_to_fit_height(200 * SIZE / 1008)
        bangs.move_to([-1.3805, 1.8897, 0.0]).set_z_index(24)
        ink_layer.append(bangs)
        self.play(FadeIn(bangs), run_time=0.55)

        # 椭圆只用来演示测量过程；定稿改用铅笔原稿中提取的真实眼睑笔画。
        # 原版把眼睛画成完整闭合椭圆，会穿过刘海，且丢失眼睑、瞳孔和睫毛。
        eyes_guide = [(e[0], e[1], e[2] * 0.72, e[3] * 0.72, e[4]) for e in eyes]
        for i, (E, name, times) in enumerate([
            (eyes_guide[0], "左下眼 · 眼睑定位", dict(trace=1.6, ink=1.1)),
            (eyes_guide[1], "右上眼 · 眼睑定位（同构）", dict(trace=1.3, ink=1.0)),
        ]):
            # 左眼被刘海切成多个交叉区，必须用局部图先裁眼、再骨架化；
            # 右眼不存在这个问题，继续复用原来已验收的笔画。
            self._build_eye_image(stylus, ink_layer, E, name, times, i)

        self.play(Transform(tag, self._tag(
            "嘴角一挑 · 微笑曲线", color=hd.INK, weight="BOLD",
            scale=ZOOM, center=FOCUS)), run_time=0.5)
        mouth_pts = np.load(os.path.join(A, "mouth.npy"))
        # 原图嘴角只是一条与双眼连线平行的淡弧，不使用主线稿的粗黑线。
        anims, rt, mmob = stylus.retrace(
            mouth_pts, color="#8E817B", stroke_width=1.25,
            pen_speed=0.4, min_time=0.6,
        )
        ink_layer.append(mmob)
        self.play(*anims, run_time=rt)
        self.wait(0.5)

        self.play(FadeOut(tag), run_time=0.4)
        out = [self.camera.frame.animate.scale(1.0 / ZOOM).move_to([0, 0, 0])]
        if dim_mobs:
            out.append(VGroup(*dim_mobs).animate.set_opacity(1.0))
        self.play(*out, run_time=1.3)
        tag = self._tag("Act 4 / 描摹（续）：衣饰、魔法书与裙摆",
                        color=hd.INK, weight="BOLD")
        self.play(FadeIn(ui), FadeIn(tag), FadeIn(stylus), run_time=0.6)

        # =============================================================
        # Act 4 — 描摹：躯干与腿
        # =============================================================
        self.play(Transform(tag, self._tag(
            "笔 2/3 · 衣饰与魔法书：宝石项链、流苏与星纹书封", color=hd.INK)),
            run_time=0.5)
        self._draw(stylus, torso, ink_layer)
        self.play(Transform(tag, self._tag(
            "笔 3/3 · 腿与裙摆：金饰缠足、飘带与赤足", color=hd.INK)), run_time=0.5)
        self._draw(stylus, legs, ink_layer)

        self.play(FadeOut(stylus), run_time=0.6)
        self.wait(0.6)

        self.play(Transform(tag, self._tag(
            f"白描定稿 · 全 {len(strokes)} 笔，与铅笔稿逐线对齐",
            color=ACCENT, weight="BOLD")), run_time=0.7)
        scan = Line([-5.4, 3.3, 0], [5.4, 3.3, 0], stroke_color="#00B4D8",
                    stroke_width=3.0, stroke_opacity=0.8)
        self.play(scan.animate.move_to([0, -3.3, 0]), run_time=2.4, rate_func=smooth)
        self.play(FadeOut(scan), run_time=0.35)
        self.wait(1.0)

        # =============================================================
        # Act 5 — 原图上色（色层依次浸润）
        # =============================================================
        self.play(Transform(tag, self._tag(
            "Act 5 / 原图上色：流光、白裙、肌肤、蓝发、金饰依次浸润",
            color=hd.INK, weight="BOLD")), run_time=0.8)

        stages = [
            ("lay_bg.png",   "上色 1/5 · 流光背景铺底"),
            ("lay_white.png", "上色 2/5 · 白裙披身"),
            ("lay_skin.png", "上色 3/5 · 肌肤透暖"),
            ("lay_hair.png", "上色 4/5 · 蓝发与魔法书"),
            ("lay_gold.png", "上色 5/5 · 金饰流辉"),
            ("full.png",     "最后一并点睛 · 线稿焕彩"),
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

        # 分色层与墨线等完整图铺好后才收
        self.play(FadeOut(Group(*ink_layer)), FadeOut(Group(*partials)),
                  run_time=1.2)
        self.remove(*ink_layer, *partials)
        self.wait(1.0)

        # =============================================================
        # Act 6 — 魔杖星辉（结尾动效）
        # =============================================================
        self.play(Transform(tag, self._tag(
            "Act 6 / 魔杖觉醒 · 星辉漫天", color=ACCENT, weight="BOLD")),
            run_time=0.7)

        glow = Circle(radius=0.4, stroke_color=GOLD, stroke_width=5.0)
        glow.move_to(WAND).set_z_index(50)
        self.play(Create(glow), run_time=0.9, rate_func=smooth)
        self.play(glow.animate.scale(2.2).set_opacity(0), run_time=0.8)

        rng = np.random.default_rng(23)
        sparks = VGroup(*[
            Dot(radius=np.random.uniform(0.015, 0.045),
                color="#FFE9B0" if k % 2 else "#9FD8FF")
            .move_to([rng.uniform(-5.5, 5.5), rng.uniform(-3.5, 3.5), 0])
            .set_z_index(50)
            for k in range(20)
        ])
        self.play(FadeIn(sparks, scale=0.4), run_time=0.4)
        self.play(self.camera.frame.animate.scale(0.94).move_to([0.0, 0.3, 0]),
                  sparks.animate.shift(UP * 0.7).set_opacity(0),
                  run_time=2.2, rate_func=smooth)
        self.remove(sparks)
        self.wait(0.5)

        self.play(Transform(tag, self._tag(
            "Masterpiece · Star Witch 星辉魔女", color=ACCENT,
            weight="BOLD", font=hd.MONO_FONT)), run_time=1.1)
        self.wait(4.0)

    # ---------------------------------------------------------------- helpers
    def _draw(self, stylus, pairs, ink_layer):
        for p, w in pairs:
            anims, rt, mob = stylus.draw(p, stroke_width=w,
                                         pen_speed=PEN_SPEED, min_time=MIN_TIME)
            ink_layer.append(mob)
            self.play(*anims, run_time=rt)

    def _build_eye(self, stylus, ink_layer, E, name, times, detail_paths):
        ex, ey, Ea, Eb, tilt = E
        info = hd.trace_ellipse((ex, ey), Ea, Eb, tilt, run_time=times["trace"],
                                show_label=name, label_scale=ZOOM)
        self.play(*info["anims"], run_time=times["trace"])
        # path（虚线轨迹）单独返回，必须一并淡出
        fade = [FadeOut(info["scaffold"]), FadeOut(info["path"])]
        if info["arm"] is not None:
            fade.append(FadeOut(info["arm"]))
        self.play(*fade, run_time=0.4)

        # 不再落一个会与头发相交的闭合椭圆，而是逐笔还原原画眼睑。
        per_stroke = times["ink"] / max(1, len(detail_paths))
        for path in detail_paths:
            anims, _, eye_mob = stylus.retrace(
                path, stroke_width=2.45, run_time=per_stroke,
            )
            ink_layer.append(eye_mob)
            self.play(*anims, run_time=per_stroke)
        self.wait(0.3)

    def _build_eye_image(self, stylus, ink_layer, E, name, times, index):
        """眼部定稿：保留原铅笔稿的完整睫毛、眼睑与瞳孔。"""
        ex, ey, Ea, Eb, tilt = E
        info = hd.trace_ellipse((ex, ey), Ea, Eb, tilt, run_time=times["trace"],
                                show_label=name, label_scale=ZOOM)
        self.play(*info["anims"], run_time=times["trace"])
        fade = [FadeOut(info["scaffold"]), FadeOut(info["path"])]
        if info["arm"] is not None:
            fade.append(FadeOut(info["arm"]))
        self.play(*fade, run_time=0.4)

        filenames = ["left_eye_ink.png", "right_eye_ink.png"]
        centers = [(-1.5358, 1.8066), (-1.2244, 2.2122)]
        eye = ImageMobject(os.path.join(A, filenames[index]))
        eye.scale_to_fit_height(75 * SIZE / 1008)
        eye.move_to([*centers[index], 0.0]).set_z_index(25)
        ink_layer.append(eye)
        self.play(FadeIn(eye), stylus.animate.move_to([ex, ey, 0]),
                  run_time=times["ink"])
        self.wait(0.3)

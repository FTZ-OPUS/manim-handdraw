# manim-handdraw

**把一张线稿图，变成一段"有人在画"的 Manim 手绘动画。**

Manim 能用 `Create()` 让一条线长出来，但它没法看一张 PNG 就告诉你：线在哪、人会按什么顺序画、怎么把过程包装成一次作画——圆规、构造线、墨块填实、色彩浸润。这个库把这一整套流水线收进几句平白的语句后面。

```python
from manim import *
import manim_handdraw as hd

class Demo(hd.HandDrawScene):
    def construct(self):
        self.hand_draw("lineart.png", color="color.png")
```

这一行会：抽出笔画 → 带笔尖光标逐笔生长 → 再一条条把颜色浸润进去。

![演示](docs/demo.gif)

> 演示片段：库自带的豌豆射手示例，完整视频由本库端到端渲染。

---

## 安装

```bash
pip install manim-handdraw                 # 只要渲染层（manim + numpy）
pip install "manim-handdraw[extract]"      # 加上「图 → 笔画」的抽取层
```

这个拆分是有意的：抽笔画需要 `scikit-image` / `scipy` / `Pillow`，但这些库是**在函数内部延迟导入**的。Manim 启动时会导入所有已注册的插件，所以只要顶层保持干净，装了本包就绝不会拖慢你其它无关的 `manim` 命令。

## 环境要求

- Python ≥ 3.9，Manim ≥ 0.18
- 抽取层另外需要 `scikit-image`、`scipy`、`Pillow`

---

## 快速开始

```bash
manim-handdraw demo lineart.png -o my_scene --color color.png
manim -ql my_scene/demo_scene.py Demo
```

或者自己写：

```python
from manim import *
import manim_handdraw as hd

config.frame_width, config.frame_height = 16, 9
config.background_color = hd.PAPER

class Demo(hd.HandDrawScene):
    def construct(self):
        self.hand_draw(
            "lineart.png",
            color="color.png",     # 也可以给列表 ["绿.png", "棕.png", "红.png"] 分层扫入
            size=7.0,              # 按高度缩放，与 ImageMobject.scale_to_fit_height 一致
            center=(0.0, 0.0),
            pen_speed=0.9,         # 每秒画多少 Manim 单位，越小越慢越有仪式感
        )
```

`hand_draw(..., draw=False)` 不播放、只把 `StrokeSet` 返回给你，方便自己插入特写镜头和几何构造——[`examples/peashooter`](examples/peashooter) 就是这么做的。

---

## 库的结构

三层，可以单独用。全都是标准 Manim 对象，没有自定义渲染器、没有 monkey-patch，所以能和你already会写的动画自由组合。

| 层 | 提供什么 | 需要 `[extract]`？ |
|---|---|---|
| **抽取层** | 位图 → 有序笔画（`from_image`、`extract_strokes`） | 需要 |
| **绘制层** | `StrokeSet`、`Stylus`、按长度自动分配时长、`InkBlot` 墨块 | 不需要 |
| **工具层** | `Compass` 圆规、`trace_ellipse` 参数方程构造、构造线、色彩扫描 | 不需要 |

### 绘制层 —— 笔画与笔尖

```python
strokes = hd.from_image("lineart.png", size=7.0)
print(strokes.describe())
# <StrokeSet 99 strokes, total length 52.4 units ...>

stylus = hd.Stylus()
self.play(*stylus.draw_all(strokes))        # 一句话画完，时长按笔画长度自动分配
```

想自己掌控节奏，就用 `Stylus.draw()`，它返回 `(动画列表, 时长, 对象)`：

```python
stylus.move_to(strokes[0][0])
self.play(FadeIn(stylus), run_time=0.4)
for p in strokes:
    group, rt, mob = stylus.draw(p)
    self.play(*group, run_time=rt)
```

### 工具层 —— 一场几何作画

用圆规画圆、用参数方程扫出椭圆，再用墨线描摹：

```python
# 圆规：枢轴 + 双关节臂，旋转与画圆严格同步
compass = hd.Compass(pivot, radius=0.67)
self.play(FadeIn(compass), run_time=0.5)
anims, guide = compass.draw_circle(dashed=True)
self.play(*anims, run_time=2.6)             # 虚线基准圆，一眼看出是「构造」
self.play(FadeOut(compass), run_time=0.5)

# 椭圆：外接辅助圆 + 长短轴 + 旋转半径臂
info = hd.trace_ellipse(center, a=0.29, b=0.16, tilt=-83.5, show_label="右眼 · 椭圆")
self.play(*info["anims"], run_time=info["run_time"])
self.play(FadeOut(info["scaffold"]), FadeOut(info["arm"]))

# 然后：墨线沿椭圆描一圈，再让墨团从中心涨开填实
self.play(*stylus.retrace(info["points"]))
blot = hd.InkBlot(center, a * 0.97, b * 0.97, tilt=-83.5)
self.play(UpdateFromAlphaFunc(blot, hd.blot_grow))
```

`HandDrawScene` 把这两段收成了 `self.construct_ellipse(...)` / `self.construct_circle(...)`。

### 上色 —— 浸润

把成品图切成竖条、一条条浮现，看起来就像水彩一段段浸润过去，而不是整层"啪"地突变：

```python
anim, group = self.sweep_color("color.png", n=7, run_time=3.2)
self.play(anim)
```

竖条按**精确**像素边界摆放。每条的宽度一旦取整，相邻两条之间就会有约 1 像素错位，在角色身上表现为一条竖直的细缝——这个 bug 很容易发出去，也很难查。

---

## 抽取流水线

`from_image()` 跑完这套流程后会把结果缓存成 `<图名>.strokes.npz`，所以重复渲染几乎零成本：

| 步骤 | 做什么 | 为什么 |
|---|---|---|
| **取墨** | alpha 通道（或亮度）→ 布尔掩膜 | 透明 PNG 和白底扫描件都能用 |
| **骨架化** | 把墨迹细化成 1 像素中心线 | 面变成线，同时保持拓扑结构 |
| **距离变换** | 沿中心线记录各处墨的半宽 | 之后想还原原始线宽时用得上 |
| **交叉点断开** | 8 邻域数 ≥ 3 判为交叉点，摘掉后做连通域 | 得到"不含分叉"的原子线段 |
| **游走** | 从端点出发顺次跟随邻居，得到有序点列 | 一笔必须有头有尾才能被画出来 |
| **合并** | 端点接近且走向连贯的段接起来 | **顺带把交叉点处的缺口补上**——一步解决两个问题 |
| **清理** | 删掉又短、附近又没别的笔画的碎点 | 清掉骨架噪点；短但有邻居的要留着，那是被交叉点切碎的真实细节 |
| **排序** | 按行分带，带内贪心就近 | 从上往下画，像人一样，且不左右横跳 |

线段最后按弧长重采样，一举两得：既压掉像素锯齿，又控制住点数。

两个最关键的参数：

```python
hd.extract_strokes(
    "lineart.png",
    merge_gap=9.0,        # 像素。越大 → 笔画越少越长
    merge_angle=0.30,     # 0~1，允许合并的方向一致性下限
    drop_inside=[(cx, cy, a, b, tilt)],   # 要剔除的椭圆（比如眼睛）
)
```

---

## 命令行 —— 把重依赖挡在 Manim 环境之外

```bash
manim-handdraw prep lineart.png --strips color.png
manim-handdraw info lineart.strokes.npz
```

```text
骨架 7666 像素 -> 原始分段 204
合并清理 -> 99 段（剔除碎点 0）
已写出 lineart.strokes.npz
  StrokeSet(99 笔，总长 52.4 单位，单笔 0.06~3.21，范围 x[-2.05,2.05] y[-2.80,3.00])
```

之后在只装了 `manim` + `numpy` 的环境里照样渲染：

```python
strokes = hd.StrokeSet.load("lineart.strokes.npz")
```

---

## 踩坑清单

下面这些是真花过时间才搞明白的。库内部都处理好了，但手写这套东西的人一定会撞上：

- **`VGroup` 装不了 `ImageMobject`。** 要用 `Group`。`VGroup` 只收 `VMobject`，而报错信息完全没提示这一点。
- **成品上色接管画面后必须把墨线层淡出。** 否则之后角色一旦位移（比如后坐力），动的是颜色图、底下的线稿不动，边缘就会漏出一层"幽灵轮廓"。
- **切片取整会产生接缝。** 边界要用 `round(i*W/n)` 算，每条按自己精确的 `[x0, x1]` 摆放；绝不能拿"单条宽 × 条数"去推位置。
- **镜头推近会把字幕一起放大。** 字幕要按 `frame.width / config.frame_width` 反向缩放，并放在 `镜头中心 + 原位 × 缩放比`。`tag_text()` 和 `HandDrawScene.zoom_to()` 已经处理。
- **`stroke_width` 不等于像素。** 1080p 下实际宽度约为 `1.2 × stroke_width`：`3.0 → 3.6px`，`5.0 → 6.0px`。
- **`UpdateFromAlphaFunc` 内部已经套过 `rate_func`。** 别再套第二遍。
- **`move_to` 需要三维点。** 而笔画数组天然是 `(n, 2)`，记得补 z。
- **实心区域骨架化会退化成伪影。** 一个实心眼睛会被抽成一条穿过中间的细线。用 `find_solid_blobs()` 找出来，交给几何构造去画。
- **别把 `VMobject` 子类的属性命名成 `points`。** `VMobject` 自己已经用这个名字存原始点数组，而且它是个 property，setter 内部会过一遍 `np.asarray`。往里存一个整数会被转成 0 维数组，报错要到很久之后才出现在 `np.linspace` 里——`TypeError: only integer scalar arrays can be converted to a scalar index`，完全看不出源头。

---

## 示例

| 文件 | 演示内容 |
|---|---|
| [`examples/01_minimal.py`](examples/01_minimal.py) | 一行式全流程 |
| [`examples/02_construct_face.py`](examples/02_construct_face.py) | 用圆规与参数方程构造替代实心区域 |
| [`examples/peashooter/`](examples/peashooter) | 完整 2.5 分钟成片：逐笔手绘、五官特写构造、色彩浸润、后坐力物理 |

```bash
cd examples/peashooter
manim -ql peashooter.py CowboyPea
```

---

## 局限

先说清楚边界，方便你判断它是否适合手上的素材：

- **它不认识画面内容。** 它只看到"墨"和"背景"。哪几笔构成眼睛、炮口圆心在哪、圆规该描哪个圆——这些要你自己给。库里提供了测量工具（`moment_ellipse` 矩法椭圆拟合、`robust_circle_fit` 稳健圆拟合、`find_solid_blobs` 实心块检测）帮你标定，豌豆射手示例里有完整的标定过程。
- **最适合干净的单色线稿**，背景透明或纯白。照片、纹理、边缘抗锯齿发灰的图会抽出噪点。
- **分层上色不等于自动分层。** 每一层的图要你自己准备，库负责切条与浮现。
- **线宽变化**已经被测出并存在 `StrokeSet.widths` 里，但默认渲染器画的是等宽线。想要毛笔提按的笔锋，用这些 `widths` 自己生成变宽带状多边形。

---

## 许可

MIT，见 [LICENSE](LICENSE)。

自带的示例素材（`examples/peashooter/assets/`）采用同样的许可。

---

[English →](README.md)

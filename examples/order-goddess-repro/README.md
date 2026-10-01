# 秩序神女 · 可直接复现的手绘动画

![秩序神女成品预览](preview.png)

这是 [manim-handdraw](https://github.com/FTZ-OPUS/manim-handdraw) 的完整作品案例：从复杂的铅笔线稿提取笔画，沿笔画描摹冠冕、发丝、竖琴和衣裙，再分层上色，最后用光晕、星屑与镜头运动收束成一段可直接发布的视频。画面线条密集，但动画编排集中在一份 Python 场景文件里；插件负责笔画提取、笔尖跟随与几何构造。本案例也保留了原铅笔稿的眼睛、嘴巴贴片，并非所有细节都由程序重新绘制。

本目录是**精简的可复现版本**：`order_goddess.py` 与 `assets/` 已包括这段动画需要的源码和素材，无须经历此前制作中的素材准备、工作流摸索与试错。原来的[成片展示案例](../order-goddess/)和它的完整版视频仍保留。

## 看成片 / 下载

- [下载压缩版 MOV（约 112 MiB）](https://github.com/FTZ-OPUS/manim-handdraw/releases/download/example-order-goddess/order-goddess-handdraw-1080p60-v6-compressed.mov)
- [下载此前发布的完整版 MP4（约 166 MiB）](https://github.com/FTZ-OPUS/manim-handdraw/releases/download/example-order-goddess/order-goddess-handdraw-1080p60-v6.mp4)
- [查看案例 Release](https://github.com/FTZ-OPUS/manim-handdraw/releases/tag/example-order-goddess)

视频约 5 分 42 秒，1080p60。两个下载文件作为 Release 附件提供，避免普通 Git 文件的大小限制；本目录保留直接渲染视频所需的代码和素材。

## 自己渲染

先安装 [Manim Community](https://docs.manim.community/en/stable/installation.html) 及其系统依赖（包括 Cairo、Pango、FFmpeg），建议 Python 3.11 或更新版本。然后在此目录执行：

```bash
python -m pip install "manim>=0.19" "manim-handdraw[extract]>=0.1.0"
manim -qh --fps 60 order_goddess.py OrderGoddess
```

`[extract]` 同时安装笔画提取需要的 scikit-image、SciPy 和 Pillow。首次运行会从 `assets/lineart.png` 提取笔画，并生成已被 Git 忽略的 `assets/lineart.strokes.npz` 缓存。低画质试跑可用 `manim -ql order_goddess.py OrderGoddess`。渲染输出通常在 `media/videos/order_goddess/1080p60/OrderGoddess.mp4`。字幕使用中文；请确保系统有可用的中文字体，字体不同可能影响排版。

## 文件与动画流程

| 文件 | 作用 |
| --- | --- |
| `order_goddess.py` | 单文件 Manim 场景与六幕动画编排 |
| `assets/lineart.png` | 用于提取逐笔描摹路径的线稿 |
| `assets/eyes_ink.png`、`assets/mouth_ink.png`、`assets/eye.json` | 五官贴片与眼睛构造定位参数 |
| `assets/lay_*.png`、`assets/full.png` | 六层颜色和最终成品图 |
| `preview.png` | 成片预览图 |

动画先用圆规定位面容，再逐笔描摹头部；随后镜头推进到眼睛，演出椭圆构造并引入原稿贴片；之后画完衣饰与裙摆，逐层上色，最后以金冠光晕和星屑结束。想学习怎样把复杂的绘画过程组织成完整成片，可从 `OrderGoddess.construct()` 的六幕编排读起。

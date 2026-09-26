# 星辉魔女（逆时空秩序圣女）

这是 `manim-handdraw` 的眼睛修复应用案例：以最终修改版源码逐笔描绘星辉魔女，使用椭圆构造修复双眼，并展示线稿提取、局部重描、分层上色和镜头特写。

![星辉魔女手绘案例预览](./preview.png)

## 成片

[观看／下载 4 分 44 秒成片（1920×1080，60 fps）](./星辉魔女2.0版.mp4)

## 文件

- `starlight_witch.py`：最终眼睛修复版 Manim 源码，场景名为 `StarWitch`。
- `assets/`：线稿、笔画缓存、眼睛几何数据和分层上色素材。
- `星辉魔女2.0版.mp4`：用户提供的最终成片。

## 运行

需要 Python、Manim Community 和手绘库的图像提取依赖。在本目录运行：

```bash
python -m pip install "manim-handdraw[extract]==0.1.0"
python -m manim -qh starlight_witch.py StarWitch
```

源码从同级 `assets/` 读取文件。重新渲染会在 `media/` 下生成 Manim 输出。

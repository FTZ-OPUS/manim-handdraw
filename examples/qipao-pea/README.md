# 旗袍豌豆：manim-handdraw 实战案例

从彩色插画派生线稿、颜色层和几何标定，再用 manim-handdraw 编排逐笔手绘、圆规与椭圆构造、分色上色和结尾动效。

## 成片与完整工程

- [观看／下载 31 秒视频（2560×1440）](https://github.com/FTZ-OPUS/manim-handdraw/releases/download/example-qipao-pea/qipao-pea-demo.mov)
- [完整工程下载：源码、原图、素材和视频](https://github.com/FTZ-OPUS/manim-handdraw/releases/download/example-qipao-pea/qipao-pea-complete.zip)
- [案例发布页](https://github.com/FTZ-OPUS/manim-handdraw/releases/tag/example-qipao-pea)

## 文件

- `extract_assets.py`：彩图处理脚本，背景分割、线稿提炼、HSV 颜色分层、几何标定与诊断图。
- `pea2_scene.py`：Manim 动画源码，场景名 `QipaoPea`。
- `手绘动画实战笔记.md`：实际遇到的问题、修复经验与 AI 核验流程。
- `source.png`：原始素材。
- `assets.zip`：预处理素材，解压后得到同级 `assets/` 目录。

## 使用

先准备好 Manim 运行环境。使用已有素材，只需解压 `assets.zip`，无需重新提取。

```bash
python -m pip install "manim-handdraw[extract]==0.1.0"
python -m zipfile -e assets.zip .
python -m manim -ql pea2_scene.py QipaoPea
```

需要重新从原图提取时，还需要 potrace 套件提供的 mkbitmap（macOS 可用 `brew install potrace`），然后运行：

```bash
python extract_assets.py source.png -o assets
```

重新提取后先检查 `assets/diag_pipeline.png` 和 `assets/diag_geo.png`。脚本依赖背景与主体可分离等条件，复杂背景和不同角色的几何标定需要调整、核验，不能保证任意图片直接得到同样效果。

本案例使用库的组件进行定制编排，不是仅调用一次 `hand_draw()` 的最小示例。成片为用户提供的案例视频；本次发布没有重新渲染。

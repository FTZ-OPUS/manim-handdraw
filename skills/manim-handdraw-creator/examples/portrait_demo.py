"""Fast preview of paired pencil/colour inputs and faithful face ink.

Run the two preparation commands in paired-inputs.md first. This scene draws
a sampled subset with the pen, then rapidly completes the remaining strokes;
the full
six-act film lives in ../../examples/order-goddess-repro/order_goddess.py.
"""

import json
from pathlib import Path

from manim import Create, FadeIn, FadeOut, Group, ImageMobject, LaggedStart, config

import manim_handdraw as hd


HERE = Path(__file__).resolve().parent
ASSETS = HERE / "generated"
SIZE = 7.6
CENTER = (0.0, -0.05)
config.frame_width, config.frame_height = 16, 9
config.background_color = hd.PAPER


class PortraitPreview(hd.HandDrawScene):
    def construct(self):
        placement_path = ASSETS / "eyes_ink.placement.json"
        if not placement_path.exists():
            raise FileNotFoundError("Run the two commands in paired-inputs.md first")
        placement = json.loads(placement_path.read_text(encoding="utf-8"))

        strokes = hd.from_image(str(ASSETS / "lineart.png"), size=SIZE,
                                center=CENTER, merge_gap=15,
                                merge_angle=0.15, clean_short=4)
        strokes = strokes.cut_out_rectangles(
            [placement["cut_window_xy_bottom_top"]]
        )
        widths = strokes.adaptive_widths(regular=2.2, fine=1.5,
                                          radius=0.14, thin_percentile=70)
        if not strokes.paths:
            raise ValueError("No line paths found; inspect lineart.png")

        # Preview the pen on about 90 paths, then reveal every remaining path.
        step = max(1, len(strokes) // 90)
        selected = set(range(0, len(strokes), step))
        ink_layer = []
        stylus = hd.Stylus()
        stylus.move_to([*strokes.paths[0][0], 0])
        self.play(FadeIn(stylus), run_time=0.15)
        for index in range(0, len(strokes), step):
            path = strokes.paths[index]
            anims, duration, ink = stylus.draw(path, stroke_width=widths[index],
                                                pen_speed=100, min_time=0.01)
            self.play(*anims, run_time=min(duration, 0.08))
            ink_layer.append(ink)
        self.play(FadeOut(stylus), run_time=0.15)

        rest = [hd.stroke_mobject(strokes.paths[index], stroke_width=widths[index])
                for index in range(len(strokes)) if index not in selected]
        if rest:
            self.play(LaggedStart(*(Create(mob) for mob in rest), lag_ratio=0.01),
                      run_time=4.0)
            ink_layer.extend(rest)

        # The eyes are original graphite pixels from the pencil input, not
        # a generic vector ellipse. Their Manim placement is calculated by
        # make_face_patch.py from the same source image used for tracing.
        face = ImageMobject(str(ASSETS / "eyes_ink.png"))
        face.scale_to_fit_height(placement["manim_height"])
        face.move_to([*placement["manim_center"], 0]).set_z_index(25)
        self.play(FadeIn(face), run_time=0.5)
        self.wait(0.2)

        finished = ImageMobject(str(ASSETS / "full.png"))
        finished.scale_to_fit_height(SIZE).move_to([*CENTER, 0]).set_z_index(30)
        self.play(FadeIn(finished), run_time=0.9)
        self.play(FadeOut(Group(*ink_layer, face)), run_time=0.2)
        self.wait(0.2)

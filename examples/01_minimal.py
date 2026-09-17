"""Minimal example — one call does the whole thing.

    manim -ql examples/01_minimal.py Leaf
    manim -qh --fps 60 examples/01_minimal.py Leaf

Reads ``examples/assets/leaf.png``, extracts its strokes on the first run
(cached next to the image as ``leaf.strokes.npz``), then draws them one at a
time with a moving pen cursor.
"""

import os

from manim import config

import manim_handdraw as hd

config.frame_width = 16
config.frame_height = 9
config.background_color = hd.PAPER

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


class Leaf(hd.HandDrawScene):
    def construct(self):
        self.hand_draw(
            os.path.join(ASSETS, "leaf.png"),
            size=7.0,
            center=(0.0, 0.0),
            pen_speed=1.1,
            title="Hand Draw",
            subtitle="one line: extract \u2192 draw \u2192 done",
        )

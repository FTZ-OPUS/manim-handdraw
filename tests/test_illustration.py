"""Regressions drawn from the portrait and dense-line examples."""

import numpy as np
import pytest

import manim_handdraw as hd


def test_face_window_splits_a_crossing_stroke_without_losing_the_hair():
    original = hd.StrokeSet(
        [np.array([[-2.0, 0.0], [2.0, 0.0]])],
        widths=[np.array([1.0, 3.0])],
    )
    cut = original.cut_out_rectangles([(-1.0, 1.0, -0.2, 0.2)])

    assert len(original) == 1  # non-mutating
    assert len(cut) == 2
    assert np.allclose(cut.paths[0][:, 0], [-2.0, -1.0])
    assert np.allclose(cut.paths[1][:, 0], [1.0, 2.0])
    assert np.allclose(cut.widths[0], [1.0, 1.5])
    assert np.allclose(cut.widths[1], [2.5, 3.0])


def test_face_window_rejects_reversed_vertical_bounds():
    strokes = hd.StrokeSet([np.array([[0.0, 0.0], [1.0, 1.0]])])
    with pytest.raises(ValueError, match="y_bottom"):
        strokes.cut_out_rectangles([(0.1, 0.9, 0.8, 0.2)])


def test_adaptive_widths_thin_crowded_strokes():
    x = np.linspace(-1.0, 1.0, 50)
    strokes = hd.StrokeSet([np.column_stack([x, np.full_like(x, y)])
                            for y in (0.0, 0.05, 1.0)])
    widths = strokes.adaptive_widths(regular=2.2, fine=1.4,
                                      radius=0.12, thin_percentile=25)
    assert widths == [1.4, 1.4, 2.2]


def test_cache_changes_with_parameters_and_source_image(tmp_path):
    from PIL import Image, ImageDraw

    path = tmp_path / "pencil.png"
    cache = tmp_path / "pencil.strokes.npz"

    def save_line(y):
        image = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
        ImageDraw.Draw(image).line((10, y, 110, y), fill=(20, 10, 5, 255), width=5)
        image.save(path)

    def key():
        with np.load(cache, allow_pickle=False) as data:
            return str(data["cache_key"].item())

    save_line(50)
    first = hd.from_image(path, size=4.0, max_points=10)
    first_key = key()
    assert first.widths is not None
    assert all(len(path) == len(width) for path, width in zip(first.paths, first.widths))

    second = hd.from_image(path, size=8.0, max_points=10)
    second_key = key()
    assert first_key != second_key
    assert second.bounds[2] - second.bounds[0] > first.bounds[2] - first.bounds[0]

    save_line(80)
    third = hd.from_image(path, size=8.0, max_points=10)
    assert key() != second_key
    assert third.bounds[1] < second.bounds[1]


def test_soft_colour_keeps_layers_until_full_image_is_visible(tmp_path):
    from PIL import Image, ImageDraw
    from manim import ImageMobject, tempconfig

    pencil = tmp_path / "line.png"
    layer = tmp_path / "layer.png"
    full = tmp_path / "full.png"
    image = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
    ImageDraw.Draw(image).line((10, 40, 70, 40), fill=(20, 10, 5, 255), width=5)
    image.save(pencil)
    Image.new("RGBA", (80, 80), (40, 150, 220, 90)).save(layer)
    Image.new("RGB", (80, 80), (240, 210, 160)).save(full)

    class SoftScene(hd.HandDrawScene):
        def construct(self):
            self.hand_draw(str(pencil), color=[str(layer)],
                           color_mode="soft", color_final=str(full),
                           color_layer_run_time=0.1, color_layer_pause=0,
                           ui=False, show_stylus=False,
                           pen_speed=500, min_time=0.01, cache=False)

    with tempconfig({"quality": "low_quality", "frame_rate": 5,
                     "media_dir": str(tmp_path / "media"),
                     "disable_caching": True, "progress_bar": "none",
                     "verbosity": "ERROR"}):
        scene = SoftScene()
        scene.render()

    assert list((tmp_path / "media").rglob("*.mp4"))
    images = [mob for mob in scene.mobjects if isinstance(mob, ImageMobject)]
    assert len(images) == 1  # early colour layer was removed after the full image appeared

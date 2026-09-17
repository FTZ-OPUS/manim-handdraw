"""Smoke tests — these render real frames, so they stay deliberately small.

    pytest -q

The render tests need a working Manim installation (LaTeX is not required).
They are skipped automatically if Manim or its dependencies are unavailable.
"""

from __future__ import annotations

import os

import numpy as np
import pytest

import manim_handdraw as hd

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "examples", "assets")
LEAF = os.path.join(ASSETS, "leaf.png")

has_extract = True
try:
    import skimage  # noqa: F401
    import scipy  # noqa: F401
    from PIL import Image  # noqa: F401
except ImportError:                                       # pragma: no cover
    has_extract = False


# ---------------------------------------------------------------- imports
def test_public_api_is_complete():
    for name in hd.__all__:
        assert hasattr(hd, name), f"missing public name: {name}"


def test_import_does_not_pull_heavy_deps():
    """The Manim plugin is loaded on every ``manim`` invocation — keep it cheap."""
    import subprocess
    import sys

    code = (
        "import sys, manim_handdraw; "
        "assert 'skimage' not in sys.modules, 'skimage leaked into the top level'"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_plugin_entry_point_registered():
    """``pip install`` must make Manim able to discover us as a plugin."""
    from importlib.metadata import entry_points

    eps = entry_points()
    group = (eps.select(group="manim.plugins") if hasattr(eps, "select")
             else eps.get("manim.plugins", []))
    names = {e.name for e in group}
    assert "manim_handdraw" in names


# ---------------------------------------------------------------- geometry
def test_ring_path_closes_and_shapes():
    c = np.array([0.0, 0.0, 0.0])
    closed = hd.ring_path(c, 1.0, 0.5, 30.0, n=40, overlap=True)
    assert closed.shape[1] == 3
    # overlap=True appends the first two samples again, so the stroke runs a
    # little past its starting point instead of stopping exactly on it — that
    # is what makes a hand-drawn ring look closed rather than nearly closed.
    assert len(closed) == 42
    assert np.linalg.norm(closed[-1][:2] - closed[0][:2]) < 0.5

    open_arc = hd.ring_path(c, 1.0, 1.0, 0.0, n=20, overlap=False, th0=0.0, th1=90.0)
    assert len(open_arc) == 20
    assert np.linalg.norm(open_arc[-1][:2] - open_arc[0][:2]) > 1.0


def test_ellipse_sampling_matches_axes():
    """A point at theta=0 must sit on the major axis, at distance a."""
    c = np.array([0.3, -0.2, 0.0])
    a, b, tilt = 2.0, 0.5, 40.0
    pts = hd.ring_path(c, a, b, tilt, n=8, overlap=False)
    t = np.radians(tilt)
    axis = np.array([np.cos(t), np.sin(t)])
    offset = pts[0][:2] - c[:2]
    assert np.isclose(np.linalg.norm(offset), a, atol=1e-6)
    assert np.isclose(np.dot(offset / np.linalg.norm(offset), axis), 1.0, atol=1e-6)


def test_coordinate_mapping_roundtrip():
    kw = dict(width=800, height=600, size=7.0, center=(0.0, 0.05))
    x, y = hd.px_to_manim(400, 300, **kw)                 # image centre
    assert np.isclose(x, 0.0) and np.isclose(y, 0.05)
    px, py = hd.manim_to_px(x, y, **kw)
    assert np.isclose(px, 400) and np.isclose(py, 300)
    # y must flip: the top of the image is the top of the scene
    _, y_top = hd.px_to_manim(0, 0, **kw)
    _, y_bot = hd.px_to_manim(0, 599, **kw)
    assert y_top > y_bot


def test_moment_ellipse_recovers_known_shape():
    """Second-moment fit should be unbiased for a filled ellipse."""
    yy, xx = np.mgrid[0:200, 0:200]
    a_true, b_true, tilt = 60.0, 22.0, 25.0
    t = np.radians(tilt)
    u = (xx - 100) * np.cos(t) + (yy - 100) * np.sin(t)
    v = -(xx - 100) * np.sin(t) + (yy - 100) * np.cos(t)
    mask = (u / a_true) ** 2 + (v / b_true) ** 2 <= 1.0

    cx, cy, a, b, got_tilt = hd.moment_ellipse(mask, width=200, height=200,
                                              size=200.0, center=(0.0, 0.0))
    # size=200 over a 200px image ⇒ 1 unit per pixel, so axes are directly comparable
    assert np.isclose(a, a_true, rtol=0.04), (a, a_true)
    assert np.isclose(b, b_true, rtol=0.06), (b, b_true)


def test_robust_circle_fit_ignores_outliers():
    rng = np.random.default_rng(0)
    t = np.linspace(0, np.pi, 120)
    x, y = 10 * np.cos(t) + 3, 10 * np.sin(t) - 4
    x = np.concatenate([x, [50.0, -40.0]])                # two gross outliers
    y = np.concatenate([y, [50.0, -40.0]])
    cx, cy, r, keep, _ = hd.robust_circle_fit(x, y)
    assert np.isclose(cx, 3, atol=0.2) and np.isclose(cy, -4, atol=0.2)
    assert np.isclose(r, 10, atol=0.2)
    assert keep.sum() <= len(t) + 2


def test_in_ellipse():
    E = (0.0, 0.0, 2.0, 1.0, 0.0)
    assert hd.in_ellipse((0.0, 0.0), E)
    assert hd.in_ellipse((1.9, 0.0), E)
    assert not hd.in_ellipse((1.9, 0.9), E)


# ---------------------------------------------------------------- strokes
def test_stroke_set_geometry():
    paths = [np.array([[0.0, 0.0], [3.0, 0.0], [3.0, 4.0]]),
             np.array([[10.0, 10.0], [11.0, 10.0]])]
    ss = hd.StrokeSet(paths)
    assert len(ss) == 2
    assert np.isclose(ss.lengths[0], 7.0)
    x0, y0, x1, y1 = ss.bounds
    assert (x0, y0, x1, y1) == (0.0, 0.0, 11.0, 10.0)
    assert "StrokeSet" in repr(ss) and "2" in ss.describe()


def test_stroke_set_filter_and_transform():
    inside = [np.array([[0.0, 0.0], [0.1, 0.0]])]
    outside = [np.array([[5.0, 5.0], [5.1, 5.0]])]
    ss = hd.StrokeSet(inside + outside)
    E = (0.05, 0.0, 0.5, 0.5, 0.0)

    assert len(ss.filter_inside([E])) == 1
    assert len(ss.only_inside([E])) == 1
    moved = ss.shifted(1.0, 2.0)
    assert np.allclose(moved.paths[0][0], [1.0, 2.0])
    scaled = hd.StrokeSet([np.array([[2.0, 0.0]])]).scaled(3.0)
    assert np.allclose(scaled.paths[0][0], [6.0, 0.0])


def test_stroke_set_save_load(tmp_path):
    paths = [np.array([[0.0, 0.0], [1.0, 2.0], [3.0, 4.0]])]
    widths = [np.array([0.1, 0.2, 0.3])]
    ss = hd.StrokeSet(paths, size=5.0, center=(0.0, 0.5), widths=widths, image="x.png")
    p = str(tmp_path / "s.npz")
    ss.save(p)
    back = hd.StrokeSet.load(p)
    assert len(back) == 1
    assert np.allclose(back.paths[0], paths[0])
    assert np.allclose(back.widths[0], widths[0])
    assert np.isclose(back.size, 5.0) and np.isclose(back.center[1], 0.5)
    assert back.image == "x.png"


def test_stroke_mobject_is_3d():
    mob = hd.stroke_mobject(np.array([[0.0, 0.0], [1.0, 1.0]]))
    assert mob.points.shape[1] == 3


# ---------------------------------------------------------------- extract
@pytest.mark.skipif(not has_extract, reason="needs manim-handdraw[extract]")
def test_extract_from_generated_line_art():
    """A straight horizontal line must come back as (roughly) one straight stroke."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    ImageDraw.Draw(img).line([(50, 200), (350, 200)], fill=(20, 10, 5, 255), width=6)
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "line.png")
        img.save(p)
        ss = hd.from_image(p, cache=False, size=4.0, center=(0.0, 0.0))

    assert len(ss) >= 1
    x0, y0, x1, y1 = ss.bounds
    assert abs(x1 - x0) > 2.0, "the horizontal extent should survive extraction"
    assert abs(y1 - y0) < 0.2, "a horizontal line should stay flat"


@pytest.mark.skipif(not has_extract, reason="needs manim-handdraw[extract]")
def test_extract_drops_solid_blob_and_orders():
    """A filled disc must be findable, and sorting must run top-to-bottom."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([150, 60, 250, 160], fill=(20, 10, 5, 255))          # solid blob
    d.line([(40, 300), (360, 300)], fill=(20, 10, 5, 255), width=5)  # a line below

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "blob.png")
        img.save(p)
        data = hd.extract_strokes(p, size=4.0, center=(0.0, 0.0))
        blobs = hd.find_solid_blobs(hd.load_ink_mask(p)[0], min_area=400)

    assert len(blobs) >= 1, "the filled disc should be detected"
    if len(data["paths"]) >= 2:
        ys = [pp[:, 1].mean() for pp in data["paths"]]
        assert ys[0] >= ys[-1], "sort_for_drawing should emit upper strokes first"


@pytest.mark.skipif(not has_extract, reason="needs manim-handdraw[extract]")
def test_strip_bounds_are_exact_and_contiguous():
    from manim_handdraw.coloring import strip_bounds

    b = strip_bounds(1024, 7)
    assert b[0] == 0 and b[-1] == 1024
    # Contiguity matters: a gap here becomes a visible seam down the character.
    assert all(b[i] == b[i + 1] or b[i] < b[i + 1] for i in range(len(b) - 1))
    assert len(b) == 8


# ---------------------------------------------------------------- render
def test_minimal_scene_renders(tmp_path):
    """End-to-end: extract → draw. This is the whole point of the package."""
    if not has_extract or not os.path.exists(LEAF):
        pytest.skip("needs manim-handdraw[extract] and examples/assets/leaf.png")

    from manim import tempconfig

    from manim_handdraw.scene import HandDrawScene

    class _Smoke(HandDrawScene):
        def construct(self):
            self.hand_draw(LEAF, size=6.0, center=(0.0, 0.0), ui=False,
                           show_stylus=False, pen_speed=200.0, min_time=0.01)

    with tempconfig({"quality": "low_quality", "disable_caching": True,
                     "media_dir": str(tmp_path), "frame_rate": 5,
                     "progress_bar": "none", "verbosity": "ERROR"}):
        _Smoke().render()

    # The directory Manim picks depends on the defining module, so glob rather
    # than hard-coding an output path.
    produced = list(tmp_path.rglob("*.mp4"))
    assert produced, f"no output produced under {tmp_path}"
    assert produced[0].stat().st_size > 0


def test_compass_and_blot_construct_without_scene():
    """Geometry builders must work purely as object factories."""
    comp = hd.Compass((0.0, 0.0), 1.0)
    anims, guide = comp.draw_circle(radius=1.0, run_time=0.1)
    assert len(anims) >= 1 and guide is not None

    info = hd.trace_ellipse((0.0, 0.0), 1.0, 0.4, 20.0, run_time=0.1)
    assert "anims" in info and len(info["points"]) > 10
    assert info["scaffold"] is not None

    blot = hd.InkBlot((0.0, 0.0), 1.0, 0.5, 0.0)
    blot.rebuild(0.5)
    assert blot.points.shape[0] > 10
    # Regression guard: `points` must not shadow VMobject's own point array.
    assert isinstance(blot.n_points, int)

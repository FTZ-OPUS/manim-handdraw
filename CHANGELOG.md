# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] — 2026-10-02

### Added
- `StrokeSet.cut_out_rectangles()` removes only the parts of traced paths inside
  face windows, preserving hair or outlines that cross a window.
- `StrokeSet.adaptive_widths()` offers a finer starting width for crowded
  regions while keeping isolated outlines readable.
- `HandDrawScene.hand_draw(color_mode="soft", color_final=...)` supports
  cumulative, softly revealed colour layers and a final full image.
- A portable [portrait creation skill](skills/manim-handdraw-creator/SKILL.md)
  with scripts, reference notes, a runnable preview, and a matched pencil/colour
  sample. Eyes and other facial details in that workflow are extracted from the
  original pencil pixels; they are not hand-traced vectors.

### Fixed
- Stroke caches now invalidate when the source image or extraction options change.
- Resampled stroke widths remain aligned to their resampled path points.
- `construct_ellipse()` removes its temporary guide path with the scaffold.

## [0.1.0] — 2026-09-18

First public release.

### Added
- **Extract layer** (`manim-handdraw[extract]`): bitmap line art → ordered stroke paths.
  Skeletonisation, junction splitting, graph walking, collinear merging (which also closes
  junction gaps), isolated-speck removal, and drawing-order sorting.
- **Geometry helpers**: pure-numpy pixel↔Manim coordinate mapping, parametric ellipse
  sampling (`ring_path`), second-moment ellipse fitting, robust iterative circle fitting,
  and solid-blob detection.
- **Draw layer**: `StrokeSet` container (save/load, filter/scale/shift), `Stylus` pen cursor
  with length-proportional timing, and `InkBlot` fills that grow from the centre.
- **Draft layer**: `Compass` with jointed arms and rotation synchronised to the circle being
  drawn, parametric `trace_ellipse` construction (auxiliary circle, axes, radius arm),
  and dashed construction guides.
- **Colour layer**: exact-boundary vertical strip splitting and lagged sweep reveal.
- **`HandDrawScene`**: `hand_draw()` one-liner, `zoom_to()` / `zoom_out()` close-ups with
  scale-correct captions, `construct_ellipse()` / `construct_circle()` helpers.
- **CLI**: `prep`, `info`, `demo` subcommands so stroke extraction can run outside the
  Manim environment.
- Registered as a Manim plugin via the `manim.plugins` entry point. Heavy dependencies are
  imported lazily so plugin load stays cheap.
- English and Chinese documentation.
- Peashooter example — the full 2.5-minute video, end to end.

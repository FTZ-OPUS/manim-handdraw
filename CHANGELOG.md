# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

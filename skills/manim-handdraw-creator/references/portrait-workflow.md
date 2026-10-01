# Paired-reference portrait workflow

This workflow distills repeated results from the Flame Queen, Starlight Witch, Purple Knight, and Order Goddess productions. The examples establish useful starting points, not constants that should be copied onto unrelated art.

## Inputs and alignment

- **Pencil drawing:** source for `lineart.png` and faithful eye/mouth ink patches. Read its real dimensions; do not reuse coordinates measured in a cropped screenshot.
- **Colour reference:** same composition, source for `full.png` and optional transparent `lay_*.png` colour layers. Align it to the pencil drawing, then inspect a 50% blend. A one-pixel or proportional mismatch can make the final colour appear to jump away from the traced lines.
- `scripts/prepare_pair.py` resizes images with near-identical aspect ratios and writes `alignment_check.png`, `lineart.png`, `full.png`, and a manifest. It does **not** register different poses automatically. If eyes, crown, or dress edges appear doubled in the blend, align/crop upstream before continuing.
- Try several line-art thresholds. For very soft or heavily shaded pencil work, ordinary thresholding can produce ink blobs; use `mkbitmap` on a BMP/PNM source (a tested starting point was `-s 1 -f 8 -t 0.45`) and inspect the resulting lines. `-s 1` avoids the default upscaling. Do not assume this one setting suits every pencil drawing.

## Cut a face window; preserve the original expression

The eyes are often too small and expressive for a convenient mathematical ellipse to reproduce. The practical approach in Purple Knight and Order Goddess was to animate a geometry/pen prelude, then reveal transparent ink extracted from the **pencil source**, not from the colour image. It is a staged hand-drawing effect. Explain that distinction when sharing code or showing how the film was made.

Choose a tight pixel rectangle after visually locating the eyes/mouth. `make_face_patch.py` converts its graphite darkness into warm-ink alpha and feathers the edge. It writes `.placement.json` with an exact cut window and patch size. The library's `StrokeSet.cut_out_rectangles()` splits paths at the window boundary; deleting the entire path would remove long bangs or hair that merely cross the eyes. Reversed Y bounds now fail loudly instead of silently leaving every facial stroke in place.

Inspect the patch composited over the intended paper colour. Transparent pixels shown against black conceal gray blocks and edge seams. For a crowded crown or very small face, a **single larger, softly feathered head patch** can look cleaner than several little rectangular patches. If a face patch includes stray shadows, increase the bright cutoff carefully and inspect again. Keep the original facial detail rather than replacing it with generic ovals.

The patch is an `ImageMobject`; mixed ink layers must use Manim `Group`, not `VGroup`. The patch should be in front of the colour layers during the drawing phase. Remove or fade guide circles, ellipse paths, and the stylus before judging the facial close-up.

## Line weight and path repair

Shape and alignment matter before thinness. First identify false joins, floating marks, missing connectors, and ornaments that turned into dark knots. Reconstruct small, structured details with explicit Bézier paths when necessary. Use a low-frequency pencil-like wobble only on long redrawn curves; random jitter on each sample creates digital noise.

At a 16:9 Manim frame, illustrated character height about 7.3–7.6, the Starlight Witch's approved fine-line repairs suggest these **starting** `stroke_width` ranges:

| Part | Initial range |
| --- | ---: |
| Main contour | 1.6–1.8 |
| Emphasised outer edge | 2.0–2.2 |
| Inner contour / hair | 1.15–1.5 |
| Facet / small ornament | 0.9–1.1 |

Actual rendered width depends on output resolution and camera scale. `StrokeSet.adaptive_widths(regular=2.2, fine=1.5, radius=0.14)` uses neighbouring strokes to thin crowded paths, but it cannot know which edge is the semantic outer contour. Inspect at final playback size and override individual widths where needed. Never infer that making a wrong shape thinner makes it correct.

`from_image()` in 0.1.1 checks image contents and extraction parameters before reusing its `.strokes.npz` cache. `merge_gap` and `clean_short` strongly affect whether hair and strings stay separate; choose them after looking at a static path preview, not just at a stroke count.

## Colour and shot review

Build colour layers from the aligned colour reference and fade whole layers in gently. The `HandDrawScene.hand_draw(..., color_mode="soft", color_final="full.png")` option preserves previous partial layers until the complete image is visible. The older sweep mode remains available. A single `full.png` can be passed as `color` if separate layers are not needed.

During a close-up, dim **stroke opacity**, not the object's fill: `mob.animate.set_stroke(opacity=0.04)` for a very dense head. Restore stroke opacity on individual objects, then confirm draw order. Using `set_opacity(1)` can fill an open line path into an opaque polygon and hide the crown. Grouping many existing strokes into a new `VGroup` animation can also alter their rendering order; inspect the actual exported frame.

Check at least four exported moments: clear pencil lines, face patch revealed without visible crop edge, cumulative colouring without vanishing layers, and the final image after guide/ink cleanup. For a local change, render a short segment first, then the full high-quality video once. Do not overwrite an accepted deliverable without a direct request.

# Paired input and runnable output example

Run from the root of this GitHub repository after installing Manim and `manim-handdraw[extract]`. The bundled sample has a **pencil original** and a matching **colour original** of the same composition. It is a real example, so the preparation output is generated locally instead of being stored twice in Git.

```bash
python skills/manim-handdraw-creator/scripts/prepare_pair.py \
  --pencil skills/manim-handdraw-creator/assets/order-goddess/pencil.png \
  --color skills/manim-handdraw-creator/assets/order-goddess/color_ref.png \
  --output skills/manim-handdraw-creator/examples/generated \
  --scale 0.5 --threshold 190
```

Open `skills/manim-handdraw-creator/examples/generated/alignment_check.png`: left is graphite, middle is the colour reference, right is their half-blend. The face, crown, hair and dress should land at the same positions. Inspect `lineart.png` too; a soft or blurry pencil may need a different threshold or the `mkbitmap` route in the reference.

The following pixel box is **only for this bundled image at 0.5 scale**. Select new boxes by viewing a new aligned pencil image rather than reusing these numbers.

```bash
python skills/manim-handdraw-creator/scripts/make_face_patch.py \
  --pencil skills/manim-handdraw-creator/examples/generated/pencil_aligned.png \
  --output skills/manim-handdraw-creator/examples/generated/eyes_ink.png \
  --box 316 116 360 143 --scene-height 7.6 --scene-center 0 -0.05

manim -ql skills/manim-handdraw-creator/examples/portrait_demo.py PortraitPreview
```

`eyes_ink.placement.json` provides the exact Manim patch centre, height and window for `cut_out_rectangles()`. `PortraitPreview` is deliberately short: the pen follows a sampled subset of paths, and a quick reveal completes the remaining traced paths. For the fully paced, finished Order Goddess film, inspect [`examples/order-goddess-repro/`](../../../examples/order-goddess-repro/) at the repository root.

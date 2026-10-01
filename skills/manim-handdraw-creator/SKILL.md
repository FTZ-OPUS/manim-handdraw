---
name: manim-handdraw-creator
description: Create and refine Manim hand-drawn anime animations from a matching pencil drawing and colour reference using manim-handdraw. Use for image preparation, faithful facial-detail patches, fine-line stroke animation, layered colouring, and visual review; not for unrelated Manim charts or geometry lessons.
---

# Manim hand-drawn animation

The standard portrait input is **two images of the same composition**: a pencil drawing supplies the line paths and original facial details; a matching colour reference supplies colour layers and the finished image. Do not extract portrait lines from the colour reference when the pencil drawing is available. Check alignment before any tracing or colour segmentation.

## Use this package

1. Locate the installed `manim-handdraw` API and use version 0.1.1 or newer for `StrokeSet.cut_out_rectangles()`, `StrokeSet.adaptive_widths()`, and cache invalidation. Install `manim-handdraw[extract]` for image extraction. Read [the portrait workflow](references/portrait-workflow.md) when preparing or reviewing a character animation.
2. Run [`scripts/prepare_pair.py`](scripts/prepare_pair.py) on the pencil drawing and matching colour reference. Inspect its alignment blend and line-art candidates. Do not accept matching aspect ratios as proof of matching facial features. For soft graphite that becomes a dark blob under a plain threshold, use the high-pass `mkbitmap` alternative in the reference.
3. Select facial windows on the **aligned pencil image**. Run [`scripts/make_face_patch.py`](scripts/make_face_patch.py) for the eyes, mouth, or a single face patch. Its placement JSON records both the Manim cut window `(x_left, x_right, y_bottom, y_top)` and the exact patch position. Use `cut_out_rectangles()` to remove only paths inside that window; preserve crossing hair outside. Overlay the patch on a paper-coloured background and inspect it at final display size.
4. Draw the remaining paths with a moving `Stylus`, use `adaptive_widths()` as a starting point for crowded regions, and refine important outlines or small ornaments by hand if the extracted shape is wrong. Keep the eye/mouth artwork faithful to the pencil drawing: show the original transparent ink patch after the construction/pen motion. Describe this honestly in technical documentation: the main paths are traced, while the facial details come from original pixels.
5. Reveal colour layers from the colour reference by soft cumulative fades. Only remove partial layers after the final aligned image is fully visible. Review an exported frame from each phase—line drawing, face close-up, colouring, final shot—before calling the scene finished. Rendering successfully does not establish visual fidelity.

The [paired-input example](examples/paired-inputs.md) gives executable commands using the bundled sample images. [`examples/portrait_demo.py`](examples/portrait_demo.py) is a short, runnable preview of the cut/patch/fine-line technique: the pen traces a subset, then all remaining paths appear in a quick reveal. The full six-act composition is in the repository's [`examples/order-goddess-repro/order_goddess.py`](../../examples/order-goddess-repro/order_goddess.py); it remains the reference for a finished film, not a quick test.

Preserve existing accepted videos and source files when iterating; save new versions under new names. The quality criteria and common failure modes are in [portrait-workflow.md](references/portrait-workflow.md).

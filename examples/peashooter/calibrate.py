"""Derive the peashooter's facial geometry from the artwork itself.

The library deliberately does not know what it is looking at — it sees ink and
background. So the circles the compass should trace, and the ellipses that have
to be excluded from stroke-by-stroke drawing, are measured here with the
library's own tools:

* :func:`~manim_handdraw.find_solid_blobs` — locate filled areas (eyes, muzzle opening)
* :func:`~manim_handdraw.moment_ellipse`   — second-moment ellipse fit
* :func:`~manim_handdraw.robust_circle_fit` — iterative circle fit to the muzzle rim

Results are cached to ``face.json`` next to the assets.
"""

from __future__ import annotations

import json
import os

import numpy as np

from manim_handdraw.extract import find_solid_blobs, load_ink_mask
from manim_handdraw.geometry import (
    manim_to_px,
    moment_ellipse,
    px_to_manim,
    robust_circle_fit,
)

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
LINEART = os.path.join(ASSETS, "pea_lineart_opt.png")

# Frame placement — must match hand_draw(size=..., center=...) in the scene.
SIZE = 7.0
CENTER = (0.0, 0.05)


def _fit(kw):
    return dict(width=kw["W"], height=kw["H"], size=SIZE, center=CENTER)


def calibrate(*, verbose=True):
    mask, (W, H) = load_ink_mask(LINEART)
    geo = {"W": W, "H": H}

    # ---- 1. filled areas: eyes + muzzle opening --------------------------
    blobs = find_solid_blobs(mask, min_area=450, disk_radius=6)
    eyes, cavity = [], None
    for b in blobs:
        cx, cy, a, b_, tilt = moment_ellipse(b["mask"], **_fit(geo))
        # Normalised layout: eyes sit high on the head; the muzzle opening is
        # lower and further left. Read from the artwork, not hard-coded to the
        # pixel grid, so the same rule survives a re-export at another size.
        if cy > 0.85 and abs(cx) < 1.0 and a < 0.40:
            eyes.append([cx, cy, a, b_, tilt])
        elif cx < -1.0 and 0.15 < cy < 0.85 and a < 0.70:
            cavity = [cx, cy, a, b_, tilt]
    eyes.sort(key=lambda e: -e[0])                      # larger (viewer-right) first
    assert len(eyes) == 2 and cavity is not None, "facial blobs not found"

    # ---- 2. muzzle rim: trace the left silhouette, fit a circle ---------
    # The scan band is derived from the opening we just found — the rim is the
    # silhouette beside it — instead of hard-coding rows, so the calibration
    # still works if the artwork is re-cropped or rescaled.
    cav_px, cav_py = manim_to_px(cavity[0], cavity[1], width=W, height=H,
                                 size=SIZE, center=CENTER)
    cav_a_px = cavity[2] / SIZE * H
    row0 = max(1, int(cav_py - 1.75 * cav_a_px))
    row1 = min(H - 1, int(cav_py + 1.75 * cav_a_px))
    x_hi = int(min(W * 0.46, cav_px + 10))
    arc = []
    for py in range(row0, row1):
        row = np.nonzero(mask[py, :x_hi])[0]
        if len(row):
            arc.append((row[0], py))
    arc = np.array(arc, float)
    ccx, ccy, cr, keep, _ = robust_circle_fit(arc[:, 0], arc[:, 1])
    mcx, mcy = px_to_manim(ccx, ccy, width=W, height=H, size=SIZE, center=CENTER)
    mr = cr / H * SIZE

    # ---- 3. angular span where the circle actually coincides with the ink --
    #     Outside this range the fit drifts off the artwork, so the ink retrace
    #     must stay inside it — otherwise a stray arc floats beside the rim.
    ang = np.degrees(np.arctan2(-(arc[keep, 1] - ccy), arc[keep, 0] - ccx)) % 360.0
    th0, th1 = float(ang.min()), float(ang.max())

    # ---- 4. eye highlight: the white hole inside the larger eye ----------
    non_ink = ~mask
    from skimage.measure import label, regionprops

    lab = label(non_ink)
    highlight = None
    for E in eyes:
        ex, ey, a, b_, tilt = E
        best = None
        for p in regionprops(lab):
            if p.area < 25:
                continue
            mx, my = px_to_manim(p.centroid[1], p.centroid[0],
                                 width=W, height=H, size=SIZE, center=CENTER)
            t = np.radians(tilt)
            hx, hy = mx - ex, my - ey
            u = hx * np.cos(t) + hy * np.sin(t)
            v = -hx * np.sin(t) + hy * np.cos(t)
            r2 = (u / a) ** 2 + (v / b_) ** 2
            if 0.02 < r2 <= 1.0 and (best is None or p.area > best[0]):
                best = (p.area, mx, my)
        if best is not None:
            area, mx, my = best
            rr = float(np.sqrt(area / np.pi) / H * SIZE)
            t = np.radians(tilt)
            hx, hy = mx - ex, my - ey
            nu = (hx * np.cos(t) + hy * np.sin(t)) / a
            nv = (-hx * np.sin(t) + hy * np.cos(t)) / b_
            highlight = [mx, my, rr, nu, nv, rr / a]
            break

    out = {
        "size": SIZE,
        "center": list(CENTER),
        "eyes": [[float(v) for v in e] for e in eyes],
        "mouth_circle": [float(mcx), float(mcy), float(mr)],
        "mouth_arc": [float(th0), float(th1)],
        "cavity": [float(v) for v in cavity],
        "highlight": [float(v) for v in highlight] if highlight else None,
        "rim_fit": {"center_px": [float(ccx), float(ccy)], "radius_px": float(cr),
                    "inliers": int(keep.sum()), "points": int(len(arc))},
    }
    if verbose:
        print(f"eyes          : "
              f"{[(round(e[0],3), round(e[1],3), round(e[2],3), round(e[3],3), round(e[4],1)) for e in eyes]}")
        print(f"mouth circle  : center=({mcx:+.4f},{mcy:+.4f}) r={mr:.4f} "
              f"(fit {keep.sum()}/{len(arc)} pts)")
        print(f"coincident arc: {th0:.1f}° ~ {th1:.1f}°")
        print(f"cavity        : center=({cavity[0]:+.4f},{cavity[1]:+.4f}) "
              f"a={cavity[2]:.4f} b={cavity[3]:.4f} tilt={cavity[4]:+.1f}°")
        print(f"highlight     : {highlight}")
    return out


def load(*, refresh=False, verbose=True):
    path = os.path.join(ASSETS, "face.json")
    if not refresh and os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    data = calibrate(verbose=verbose)
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=1)
    except Exception:
        pass
    return data


if __name__ == "__main__":
    load(refresh=True)

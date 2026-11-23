# fill: bucket fill that tolerates the noisy near-shades in AI pictures.
# Copyright (C) 2026 the pixeltools contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY; see the GNU General Public
# License for details: <https://www.gnu.org/licenses/>.
import numpy as np

from . import core
from . import tuning as T

NAME = "fill"
SUMMARY = "bucket fill with a tolerance, or fill a whole noisy background in one go"
EXAMPLE = ("Examples:\n"
           "  python sprite.py fill sprite.png --background --colour '#00000000'    (make the whole ground transparent)\n"
           "  python sprite.py fill sprite.png --at 40,12 --colour '#c83030' --tolerance 12\n"
           "  python sprite.py fill sprite.png --at 5,5 --everywhere --colour 0,0,0")


def describe(rec: dict) -> str:
    where = f" (ground colour {rec['background_colour']})" if "background_colour" in rec else ""
    if rec["pixels_filled"] == 0:
        return "nothing matched, so nothing was filled."
    return f"filled {rec['pixels_filled']} pixels{where}; {rec['pixels_changed']} actually changed."


def hex_of(c) -> str:
    return "#%02x%02x%02x%02x" % tuple(int(v) for v in c)


def border_ring(h: int, w: int) -> np.ndarray:
    """Flat indices of the pixels in the border ring."""
    band = max(T.BG_BAND_MIN, int(T.BG_BAND * min(h, w) + 0.5))
    band = min(band, max(1, min(h, w) // 2))
    yy, xx = np.mgrid[0:h, 0:w]
    ring = (yy < band) | (yy >= h - band) | (xx < band) | (xx >= w - band)
    return np.nonzero(ring.ravel())[0]


def ground_colour(flat: np.ndarray, ring: np.ndarray) -> np.ndarray:
    """The typical border colour: per channel, the middle value (the upper one when there are two)."""
    vals = np.sort(flat[ring], axis=0)
    return vals[len(ring) // 2].astype(np.int32)


def fit_plane(flat: np.ndarray, w: int, idx: np.ndarray, fallback: np.ndarray):
    """A gentle gradient colour = a + b*x + c*y per channel, fitted by least squares to the pixels idx.
    Returns 4 rows of (a, b, c) as Python floats. Written with plain float steps so the browser gives the same numbers."""
    y, x = np.divmod(idx, w)
    x, y = x.astype(np.int64), y.astype(np.int64)
    n, sx, sy = float(len(idx)), float(x.sum()), float(y.sum())
    sxx, sxy, syy = float((x * x).sum()), float((x * y).sum()), float((y * y).sum())
    det = n * (sxx * syy - sxy * sxy) - sx * (sx * syy - sxy * sy) + sy * (sx * sxy - sxx * sy)
    rows = []
    for ch in range(4):
        c = flat[idx, ch].astype(np.int64)
        sc, sxc, syc = float(c.sum()), float((x * c).sum()), float((y * c).sum())
        if det == 0.0:
            rows.append((float(fallback[ch]), 0.0, 0.0))
            continue
        a = (sc * (sxx * syy - sxy * sxy) - sx * (sxc * syy - sxy * syc) + sy * (sxc * sxy - sxx * syc)) / det
        b = (n * (sxc * syy - sxy * syc) - sc * (sx * syy - sxy * sy) + sy * (sx * syc - sxc * sy)) / det
        cc = (n * (sxx * syc - sxc * sxy) - sx * (sx * syc - sxc * sy) + sc * (sx * sxy - sxx * sy)) / det
        rows.append((a, b, cc))
    return rows


def plane_distance2(flat_ids: np.ndarray, w: int, flat: np.ndarray, rows) -> np.ndarray:
    """Squared distance of the pixels flat_ids to the fitted gradient."""
    y, x = np.divmod(flat_ids, w)
    x, y = x.astype(np.float64), y.astype(np.float64)
    total = np.zeros(len(flat_ids), dtype=np.float64)
    for ch, (a, b, c) in enumerate(rows):
        d = flat[flat_ids, ch].astype(np.float64) - ((a + b * x) + c * y)
        total = total + d * d
    return total


def apply(img: np.ndarray, opts: dict):
    h, w = img.shape[:2]
    tol = opts.get("tolerance")
    tol = T.FILL_TOLERANCE if tol is None else float(tol)
    cut2 = core.cutoff_sq(tol)
    colour = opts.get("colour")
    colour = core.clean_colour((0, 0, 0, 0) if colour is None else colour)
    corners = bool(opts.get("corners"))
    at = opts.get("at")
    flat = core.normalise(img).astype(np.int32).reshape(-1, 4)
    extra = {}
    if opts.get("background"):
        if at is not None:
            raise ValueError("Use either --at (a start point) or --background (start from the border), not both.")
        ring = border_ring(h, w)
        ref = ground_colour(flat, ring)
        range2 = cut2 * T.BG_RANGE * T.BG_RANGE
        first2 = cut2 * T.BG_FIT_FIRST * T.BG_FIT_FIRST
        kept = ring[((flat[ring] - ref) ** 2).sum(axis=1) <= first2]
        rows = fit_plane(flat, w, kept if len(kept) else ring, ref)
        for _ in range(T.BG_FIT_ROUNDS):
            again = ring[plane_distance2(ring, w, flat, rows) <= range2]
            if len(again) < 0.2 * len(ring):
                break
            rows = fit_plane(flat, w, again, ref)
        everyone = np.arange(h * w)
        d_bg = plane_distance2(everyone, w, flat, rows)
        seeds = ring[d_bg[ring] <= range2]
        if len(seeds) == 0:
            mask = np.zeros(h * w, dtype=bool)
        else:
            def edge_ok(p, q):
                return (((flat[p] - flat[q]) ** 2).sum(axis=1) <= cut2) & (d_bg[q] <= range2)
            mask = core.grow(h, w, seeds, edge_ok, corners)
        extra["background_colour"] = hex_of(ref)
    else:
        if at is None:
            raise ValueError("Say where to start: --at x,y (a point on the area to fill), or use --background.")
        x, y = core.check_point(img, at)
        ref = flat[y * w + x]
        cand = ((flat - ref) ** 2).sum(axis=1) <= cut2
        mask = cand if opts.get("everywhere") else core.grow(h, w, np.array([y * w + x]), lambda p, q: cand[q], corners)
    out = img.copy().reshape(-1, 4)
    out[mask] = colour
    out = out.reshape(h, w, 4)
    return out, dict({"pixels_filled": int(mask.sum()), "pixels_changed": core.changed_pixels(img, out)}, **extra)

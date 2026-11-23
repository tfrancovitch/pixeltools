#!/usr/bin/env python3
# Pixel Snap (Python version): rebuild true pixel art from an AI "pixel art" image.
# Copyright (C) 2026 the pixeltools contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY; see the GNU General Public
# License for details: <https://www.gnu.org/licenses/>.
"""Find the real pixel grid in a blown-up "pixel art" picture and shrink it so
that one visible pixel becomes exactly one real pixel.

Needs Python 3.9+, numpy and Pillow.

    python pixel_snap.py picture.png                 # writes picture_snapped.png
    python pixel_snap.py *.png --scale 8 -o out/     # many files, enlarged 8x for moodboards
    python pixel_snap.py picture.png --cell 12.5     # you tell it the pixel size
    python pixel_snap.py picture.png --colors 16     # also limit the palette
    python pixel_snap.py *.png --skip-isometric      # leave out isometric pictures
    python pixel_snap.py *.png --check-only          # just report what each picture is and its view
    python pixel_snap.py folder/*.png --sort sorted --want-view orthogonal   # sort a batch into folders
    python pixel_snap.py folder/*.png --sort sorted --brief                  # ...and print only what needs attention
    python pixel_snap.py sprite.png --transparent    # also make a plain background transparent
    python pixel_snap.py *.png --shadows remove-cast # drop cast (sun-angle) shadows, keep small contact shadows

The method matches the browser version (pixel-snap.html) in this folder.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))  # so tuning.py is found even in python -I
import facing as FC  # noqa: E402
import framing as F  # noqa: E402
import shadow as SH  # noqa: E402
import sorting as SORT  # noqa: E402
import subject as SUBJ  # noqa: E402
import viewcheck as V  # noqa: E402
import tuning as T  # noqa: E402

__all__ = ["analyse", "rebuild", "snap_image", "classify_view", "Analysis", "Result", "ViewVerdict", "Framing", "classify_subject", "find_shadow"]
Framing = F.Framing
classify_subject = SUBJ.classify_subject
find_shadow = SH.find_shadow
ViewVerdict = V.ViewVerdict
classify_view = V.classify_view


# --------------------------------------------------------------------------
# Finding the grid
# --------------------------------------------------------------------------

def edge_profile(rgb: np.ndarray, axis: int, gaps=(1,)) -> np.ndarray:
    """e[i] = average colour jump across the line between pixel i-1 and pixel i (axis 0: columns,
    1: rows). With gaps (1, 3) the jump is also measured between pixels further apart, which keeps
    soft, blurred edges visible. Every gap is centred on the same line."""
    a = rgb.astype(np.int32)
    if axis == 1:
        a = a.transpose(1, 0, 2)
    h, n = a.shape[0], a.shape[1]
    a = a[::max(1, h // 600)]
    e = np.zeros(n, dtype=np.float64)
    for d in gaps:                       # d odd: compare pixel i-1-half with pixel i+half
        half = (d - 1) // 2
        if n <= d:
            continue
        lo = half + 1                    # first line i with a left pixel (i-1-half >= 0)
        hi = n - half                    # one past the last line with a right pixel (i+half <= n-1)
        idx = np.arange(lo, hi)
        jump = np.abs(a[:, idx + half, :] - a[:, idx - 1 - half, :]).sum(axis=2).mean(axis=0)
        e[lo:hi] += jump
    return e


def smooth(e: np.ndarray, k: int) -> np.ndarray:
    n = len(e)
    w = np.array([k + 1 - abs(d) for d in range(-k, k + 1)], dtype=np.float64)
    m = np.ones(n)
    m[0] = 0.0
    num = np.convolve(e * m, w, mode="same")
    den = np.convolve(m, w, mode="same")
    return num / np.maximum(den, 1e-12)


def _scores(a: np.ndarray, p: float, offs: np.ndarray, mean: float) -> np.ndarray:
    n = len(a)
    ks = np.arange(int(n / p) + 2)
    x = offs[:, None] + ks[None, :] * p
    valid = (x >= 1) & (x < n - 1)
    vals = np.interp(x, np.arange(n), a)
    cnt = valid.sum(axis=1)
    tot = (vals * valid).sum(axis=1)
    return np.where(cnt > 0, tot / np.maximum(cnt, 1) / mean, 0.0)


def _best_phase(a, p, mean, step):
    offs = np.arange(0.0, p, step)
    sc = _scores(a, p, offs, mean)
    i = int(np.argmax(sc))
    return float(sc[i]), float(offs[i])


def _mean(e):
    return float(e[1:].mean()) if len(e) > 1 else 0.0




@dataclass
class Axis:
    p: float
    off: float
    score: float
    ok: bool
    borrowed: bool = False
    weak: bool = False          # a grid-like signal that is real but thin
    disagree: bool = False      # width and height gave different pixel sizes that could not be reconciled
    curve: tuple | None = field(default=None, repr=False)   # (sizes, scores) searched, for the square-pixel check


def _comb_curve(e: np.ndarray, min_p: float = T.GRID_MIN_PIXEL, harmonics: int = T.GRID_HARMONICS,
                win: int = T.GRID_DETREND_WINDOW):
    """Score every candidate pixel size by how strongly the edge signal repeats at
    that size (and its multiples) compared with the positions halfway between.

    Works on the autocorrelation of the edge signal, so it does not depend on where
    the grid starts, and a few lucky outline edges cannot fake a large grid."""
    x = np.sqrt(e[1:].astype(np.float64))
    n = len(x)
    # remove the slow background (figure vs. empty space) so only the comb is left
    csum = np.concatenate([[0.0], np.cumsum(x)])
    lo = np.clip(np.arange(n) - win // 2, 0, n)
    hi = np.clip(np.arange(n) + win // 2 + 1, 0, n)
    x = x - (csum[hi] - csum[lo]) / (hi - lo)
    f = np.fft.rfft(x, 2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:n]
    if ac[0] <= 0:
        return np.array([]), np.array([])
    # fewer samples overlap at long lags; undo that fade so big grids are not out-scored
    ac = ac / ac[0] * n / (n - np.arange(n))
    ac = np.convolve(ac, [0.25, 0.5, 0.25], mode="same")
    idx = np.arange(n)
    ps_, ss = [], []
    p, max_p = min_p, max(3.0, n * T.GRID_MAX_FRACTION)
    ks = np.arange(1, harmonics + 1)
    while p <= max_p:
        lags = ks * p
        lags = lags[lags < T.GRID_LAG_LIMIT * n]
        if len(lags) < T.GRID_MIN_LAGS:
            break
        on = np.interp(lags, idx, ac).mean()
        off = np.interp(lags - p / 2, idx, ac).mean()
        ps_.append(p)
        ss.append(on - off)
        p *= T.GRID_SIZE_STEP
    return np.array(ps_), np.array(ss)


def _thresholds(n: int) -> tuple[float, float]:
    """(strong, weak) score a grid needs on an axis of n pixels; smaller pictures need more."""
    strong = max(T.MIN_GRID_SCORE, T.NOISE_FACTOR / np.sqrt(n))
    return strong, strong * T.GRID_WEAK_SCORE / T.MIN_GRID_SCORE


def _refine_at(e_fine: np.ndarray, p0: float) -> tuple[float, float]:
    """Exact pixel size (within +-1.5% of p0) and where the grid starts, from the exact edge profile."""
    a1 = smooth(e_fine, 1)
    mean_fine = _mean(e_fine)
    best = (-1.0, p0, 0.0)
    for r in np.arange(T.GRID_REFINE_LOW, T.GRID_REFINE_HIGH, T.GRID_REFINE_STEP):
        pp = p0 * r
        sc, o = _best_phase(a1, pp, mean_fine, 0.25)
        if sc > best[0]:
            best = (sc, pp, o)
    return best[1], best[2]


def _axis_from(e: np.ndarray, e_fine: np.ndarray, p0: float, score: float, curve,
               judged_on: float | None = None, n: int | None = None) -> Axis:
    """judged_on: the score the strong/weak call is made on (default: this axis's own score)."""
    p, off = _refine_at(e_fine, p0)
    strong, weak = _thresholds(n or len(e))
    j = score if judged_on is None else judged_on
    return Axis(p, off, score, j >= strong, weak=weak <= j < strong, curve=curve)


def detect_axis(e: np.ndarray, e_fine: np.ndarray | None = None) -> Axis:
    """e finds the pixel size (wide edges); e_fine (exact edges, default e) fixes its exact value and start."""
    e_fine = e if e_fine is None else e_fine
    mean = _mean(e)
    if not mean > 1e-6:
        return Axis(1.0, 0.0, 0.0, False)
    ps, ss = _comb_curve(e)
    if len(ps) == 0:
        return Axis(1.0, 0.0, 0.0, False)
    if e_fine is not e:                 # wide edges help blurry grids, narrow edges help tiny pixels: use the better
        ps2, ss2 = _comb_curve(e_fine)
        n = min(len(ps), len(ps2))
        ps, ss = ps[:n], np.maximum(ss[:n], ss2[:n])
    smax = float(ss.max())
    # Multiples of the true size score the same as the true size, so take the
    # smallest size that scores almost as well as the best one.
    first = int(np.argmax(ss >= T.GRID_SMALLEST_FIT * smax))
    window = (ps <= ps[first] * T.GRID_WINDOW_RANGE) & (np.arange(len(ps)) >= first)
    pick = int(np.argmax(np.where(window, ss, -9.0)))
    return _axis_from(e, e_fine, ps[pick], smax, (ps, ss))


def _curve_at(curve, p: float) -> float | None:
    ps, ss = curve
    if p < ps[0] or p > ps[-1]:
        return None
    return float(np.interp(np.log(p), np.log(ps), ss))


def reconcile_square(dx: Axis, dy: Axis, wx, wy, ex, ey) -> tuple[Axis, Axis]:
    """Pixels are square, so width and height should agree. When they do not, test the likely common
    sizes (each axis's own answer, and halves and thirds of them, since one axis may have locked onto
    a multiple) against both signals together, and pick the smallest that scores nearly as well as
    the best. A direction with no signal at all simply borrows the other's size; a thin direction that
    points to a different size makes the grid contested."""
    if dx.curve is None or dy.curve is None:
        return dx, dy
    if not (dx.ok or dy.ok):            # neither is strong: nothing to reconcile
        return dx, dy
    if dx.ok != dy.ok and not (dy.weak if dx.ok else dx.weak):
        return dx, dy                   # a strong direction and one with no signal at all: it borrows the strong size
    if abs(dx.p - dy.p) / ((dx.p + dy.p) / 2) <= T.GRID_SQUARE_TOLERANCE:
        return dx, dy
    cands = {round(v / k, 3) for v in (dx.p, dy.p) for k in (1, 2, 3) if v / k >= T.GRID_MIN_PIXEL}
    scored = []
    for c in sorted(cands):
        sx, sy = _curve_at(dx.curve, c), _curve_at(dy.curve, c)
        if sx is None or sy is None:
            continue
        scored.append((c, sx, sy, sx + sy))
    if not scored:
        return dx, dy
    top = max(sc[3] for sc in scored)
    c, sx, sy, _ = next(sc for sc in scored if sc[3] >= T.GRID_SMALLEST_FIT * top)
    n = min(len(wx), len(wy))
    strong, weak = _thresholds(n)
    resolved = min(sx, sy) >= weak          # both directions support the common size
    ax = _axis_from(wx, ex, c, sx, dx.curve, max(sx, sy), n)
    ay = _axis_from(wy, ey, c, sy, dy.curve, max(sx, sy), n)
    if not resolved:
        # No common size. The pixels may simply not be square (the picture was stretched a little): if one
        # direction's size is a clean multiple of the other's, its finer reading was probably half a pixel.
        both = max(dx.score, dy.score)
        for k in (2, 3):
            if abs(dx.p - k * dy.p) / ((dx.p + k * dy.p) / 2) <= T.GRID_SQUARE_TOLERANCE:
                return (_axis_from(wx, ex, dx.p, dx.score, dx.curve, both, n),
                        _axis_from(wy, ey, k * dy.p, dy.score, dy.curve, both, n))
            if abs(dy.p - k * dx.p) / ((dy.p + k * dx.p) / 2) <= T.GRID_SQUARE_TOLERANCE:
                return (_axis_from(wx, ex, k * dx.p, dx.score, dx.curve, both, n),
                        _axis_from(wy, ey, dy.p, dy.score, dy.curve, both, n))                        # one direction has no support for the size: at best a weak grid
        for a in (ax, ay):
            a.weak, a.ok, a.disagree = max(sx, sy) >= weak, False, True
    return ax, ay


def fit_phase(e: np.ndarray, p: float) -> Axis:
    mean = _mean(e)
    if not mean > 1e-6:
        return Axis(p, 0.0, 0.0, True)
    s, o = _best_phase(smooth(e, 1), p, mean, 0.25)
    return Axis(p, o, s, True)


def make_bounds(e: np.ndarray, p: float, off: float, n: int, follow: bool) -> list[int]:
    """Cell edges along one axis. With `follow`, each edge snaps to the strongest
    nearby colour change, so a wobbly grid is tracked instead of assumed straight."""
    s = smooth(e, 1)
    pos = []
    x = off % p
    while x < n:
        if 0.01 < x < n - 0.01:
            pos.append(x)
        x += p
    if pos and pos[0] < 0.5 * p:
        pos.pop(0)
    if pos and n - pos[-1] < 0.5 * p:
        pos.pop()
    line_mean = float(np.mean(np.interp(pos, np.arange(n), s))) if pos else 0.0
    w = max(1, int(0.3 * p))
    out = [0]
    for x in pos:
        v = int(np.floor(x + 0.5))
        if follow and p >= 3:
            lo, hi = max(1, v - w), min(n - 1, v + w)
            seg = s[lo:hi + 1]
            bi = lo + int(np.argmax(seg))
            if seg.max() >= 0.5 * line_mean:
                v = bi
        if out[-1] < v < n:
            out.append(v)
    out.append(n)
    return out


# --------------------------------------------------------------------------
# Rebuilding the sprite
# --------------------------------------------------------------------------

def cell_flatness(rgb: np.ndarray, bx: list[int], by: list[int]) -> float:
    """Share of the picture's colour variation that the cell grid explains (1 - within-cell / total).
    Real pixel art, even blurred, has flat blocks (close to 1). Painted or smooth art varies inside
    every "block", so a grid that merely fits the edges explains much less."""
    a = rgb.astype(np.float64)
    h, w = a.shape[:2]
    cx = np.clip(np.searchsorted(bx, np.arange(w), side="right") - 1, 0, len(bx) - 2)
    cy = np.clip(np.searchsorted(by, np.arange(h), side="right") - 1, 0, len(by) - 2)
    idx = (cy[:, None] * (len(bx) - 1) + cx[None, :]).ravel()
    sel = np.arange(0, idx.size, max(1, idx.size // 400000))      # a sample is plenty
    idx_s, flat = idx[sel], a.reshape(-1, 3)[sel]
    n = (len(bx) - 1) * (len(by) - 1)
    cnt = np.maximum(np.bincount(idx_s, minlength=n), 1)
    total = ((flat - flat.mean(axis=0)) ** 2).sum()
    within = 0.0
    for c in range(3):
        mean = np.bincount(idx_s, weights=flat[:, c], minlength=n) / cnt
        within += ((flat[:, c] - mean[idx_s]) ** 2).sum()
    return float(1 - within / max(total, 1e-9))


def sample_cells(rgba: np.ndarray, bx: list[int], by: list[int]) -> np.ndarray:
    """One pixel per cell: the median colour of the cell's middle (edges are blurry)."""
    w, h = len(bx) - 1, len(by) - 1
    out = np.zeros((h, w, 4), dtype=np.uint8)
    for cy in range(h):
        y0, y1 = by[cy], by[cy + 1]
        iy = (y1 - y0) // 4
        if y1 - y0 - 2 * iy < 1:
            iy = 0
        for cx in range(w):
            x0, x1 = bx[cx], bx[cx + 1]
            ix = (x1 - x0) // 4
            if x1 - x0 - 2 * ix < 1:
                ix = 0
            xa, xb, ya, yb = x0 + ix, x1 - ix, y0 + iy, y1 - iy
            sx = max(1, -(-(xb - xa) // 20))
            sy = max(1, -(-(yb - ya) // 20))
            patch = rgba[ya:yb:sy, xa:xb:sx].reshape(-1, 4)
            opaque = patch[patch[:, 3] >= 128]
            if len(opaque) == 0 or len(opaque) < len(patch) / 2:
                continue
            n = len(opaque)
            for c in range(3):
                out[cy, cx, c] = np.sort(opaque[:, c])[n >> 1]
            out[cy, cx, 3] = 255
    return out


def _colour_keys(rgba):
    flat = rgba.reshape(-1, 4)
    op = flat[:, 3] >= 128
    key = (flat[:, 0].astype(np.int64) << 16) | (flat[:, 1].astype(np.int64) << 8) | flat[:, 2]
    return flat, op, key


def count_colours(rgba: np.ndarray) -> int:
    _, op, key = _colour_keys(rgba)
    return int(len(np.unique(key[op])))


def _apply_lut(rgba, lut):
    flat, op, key = _colour_keys(rgba)
    keys, inv = np.unique(key[op], return_inverse=True)
    table = np.array([lut[int(k)] for k in keys], dtype=np.uint8).reshape(-1, 3)
    flat[np.where(op)[0], :3] = table[inv]


def merge_similar(rgba: np.ndarray, tol: float = T.COLOUR_MERGE_TOLERANCE) -> None:
    """Colours that differ only by noise become the most common nearby colour."""
    _, op, key = _colour_keys(rgba)
    keys, counts = np.unique(key[op], return_counts=True)
    order = np.argsort(-counts, kind="stable")
    cols = [(int(keys[i]) >> 16, (int(keys[i]) >> 8) & 255, int(keys[i]) & 255, int(keys[i])) for i in order]
    reps, lut = [], {}
    t2 = tol * tol
    for c in cols:
        hit = None
        for r in reps:
            if (c[0] - r[0]) ** 2 + (c[1] - r[1]) ** 2 + (c[2] - r[2]) ** 2 <= t2:
                hit = r
                break
        if hit is None:
            reps.append(c)
            hit = c
        lut[c[3]] = hit[:3]
    _apply_lut(rgba, lut)


def quantize(rgba: np.ndarray, k: int) -> None:
    """Reduce to at most k colours (weighted k-means in RGB)."""
    _, op, key = _colour_keys(rgba)
    keys, counts = np.unique(key[op], return_counts=True)
    if len(keys) <= k:
        return
    order = np.argsort(-counts, kind="stable")
    keys, counts = keys[order], counts[order].astype(np.float64)
    cols = np.stack([keys >> 16, (keys >> 8) & 255, keys & 255], axis=1).astype(np.float64)
    cen = [cols[0].copy()]
    dm = np.full(len(cols), np.inf)
    while len(cen) < k:
        dm = np.minimum(dm, ((cols - cen[-1]) ** 2).sum(axis=1))
        cen.append(cols[int(np.argmax(dm * np.sqrt(counts)))].copy())
    cen = np.array(cen)
    for _ in range(12):
        d = ((cols[:, None, :] - cen[None, :, :]) ** 2).sum(axis=2)
        asg = d.argmin(axis=1)
        for j in range(len(cen)):
            m = asg == j
            if m.any():
                cen[j] = (cols[m] * counts[m, None]).sum(axis=0) / counts[m].sum()
    d = ((cols[:, None, :] - cen[None, :, :]) ** 2).sum(axis=2)
    asg = d.argmin(axis=1)
    lut = {int(keys[i]): tuple(int(round(v)) for v in cen[asg[i]]) for i in range(len(keys))}
    _apply_lut(rgba, lut)


@dataclass
class Analysis:
    ex: np.ndarray
    ey: np.ndarray
    dx: Axis
    dy: Axis
    found: bool
    status: str = "found"      # "found", "weak" (used, but check it) or "none" (no regular grid)
    note: str = ""             # one plain sentence about the grid, for reports


@dataclass
class Result:
    rgba: np.ndarray          # the sprite, one array element per real pixel
    bx: list[int]             # cell edges in the original, left to right
    by: list[int]             # cell edges in the original, top to bottom
    px: float                 # detected pixel width in the original
    py: float                 # detected pixel height in the original
    found: bool
    colours_raw: int
    colours: int
    view: "V.ViewVerdict"
    framing: "F.Framing"
    transparent: bool = False  # True when the background was made transparent
    grid_status: str = "found" # "found", "weak", "none" or "manual"
    grid_note: str = ""
    subject: "SUBJ.SubjectVerdict | None" = None   # character / building / scene / unclear
    shadow: "SH.ShadowInfo | None" = None   # ground shadow under a lone sprite, if any
    facing: "FC.FacingVerdict | None" = None   # which way a character faces (always "unclear" so far; carries the measured clues)
    flatness: float | None = None   # how flat the blocks are inside (see cell_flatness); None when nothing was snapped
    shadow_removed: int = 0         # sprite pixels turned back into ground by shadow removal

    @property
    def size(self) -> tuple[int, int]:
        return self.rgba.shape[1], self.rgba.shape[0]


def _weak_ok(axis: Axis, n: int) -> bool:
    return axis.weak and n / axis.p >= T.GRID_WEAK_MIN_CELLS


def analyse(rgba: np.ndarray) -> Analysis:
    rgb = rgba[..., :3]
    ex, ey = edge_profile(rgb, 0), edge_profile(rgb, 1)
    wx, wy = edge_profile(rgb, 0, T.EDGE_GAPS), edge_profile(rgb, 1, T.EDGE_GAPS)
    dx, dy = detect_axis(wx, ex), detect_axis(wy, ey)
    dx, dy = reconcile_square(dx, dy, wx, wy, ex, ey)
    h, w = rgb.shape[:2]
    guess = f"best guess {dx.p:.1f} x {dy.p:.1f} px, scores {dx.score:.2f} and {dy.score:.2f}"
    if dx.ok or dy.ok:
        if not dx.ok:
            dx = fit_phase(ex, dy.p)
            dx.borrowed = True
        elif not dy.ok:
            dy = fit_phase(ey, dx.p)
            dy.borrowed = True
        return Analysis(ex, ey, dx, dy, True, "found", "clear pixel grid found")
    okx, oky = _weak_ok(dx, w), _weak_ok(dy, h)
    if (okx or oky) and min(w / dx.p, h / dy.p) < T.GRID_WEAK_MIN_CELLS:
        okx = oky = False          # a weak grid that leaves too few cells across either side is not trusted
    if okx or oky:
        if okx and oky and abs(dx.p - dy.p) / ((dx.p + dy.p) / 2) > T.GRID_WEAK_AGREE:
            okx, oky = (dx.score >= dy.score), (dy.score > dx.score)   # disagree: trust the stronger axis only
        if okx and not oky:
            dy = fit_phase(ey, dx.p)
            dy.borrowed = True
        elif oky and not okx:
            dx = fit_phase(ex, dy.p)
            dx.borrowed = True
        return Analysis(ex, ey, dx, dy, True, "weak",
                        f"weak pixel grid ({dx.p:.1f} x {dy.p:.1f} px): "
                        + ("width and height gave different sizes, " if dx.disagree else "the blocks are soft or uneven, ")
                        + "so check the result")
    return Analysis(ex, ey, dx, dy, False, "none",
                    f"no regular pixel grid found ({guess}); the picture may be painted, smooth or already true size. "
                    "To pixelate it anyway, give a pixel size (--cell)")


def rebuild(rgba: np.ndarray, an: Analysis, cell: float | None = None,
            follow: bool = True, colours: int = 0, transparent: bool = False,
            shadows: str = "keep") -> Result:
    h, w = rgba.shape[:2]
    dx, dy, found = an.dx, an.dy, an.found
    if cell:
        dx, dy, found = fit_phase(an.ex, cell), fit_phase(an.ey, cell), True
    status, flat = ("manual" if cell else an.status), None
    note = f"pixel size set by hand ({cell:g})" if cell else an.note
    if found:
        bx = make_bounds(an.ex, dx.p, dx.off, w, follow)
        by = make_bounds(an.ey, dy.p, dy.off, h, follow)
        flat = cell_flatness(rgba[..., :3], bx, by)
        if not cell:
            if flat < T.FLAT_NONE:
                found, status = False, "none"
                note = (f"no usable pixel grid: the blocks are not flat inside (flatness {flat:.2f}), so the picture looks "
                        "painted or smooth, not pixel art. To pixelate it anyway, give a pixel size (--cell)")
            elif flat < T.FLAT_STRONG and status == "found":
                status = "weak"
                note = (f"pixel grid found ({dx.p:.1f} x {dy.p:.1f} px) but the blocks are not very flat inside "
                        f"(flatness {flat:.2f}): painted or soft, so check the result")
    if not found:
        # nothing to snap: hand the picture back as it is (and skip a pixel-by-pixel loop)
        dx = dy = Axis(1.0, 0.0, 0.0, False)
        bx, by = list(range(w + 1)), list(range(h + 1))
        out = rgba.copy()
    else:
        out = sample_cells(rgba, bx, by)
    framing = F.classify_framing(rgba)
    shadow = SH.find_shadow(rgba, framing)
    raw = count_colours(out)
    if found:  # merging shades is for sprites; a picture with no grid is returned untouched
        merge_similar(out, T.COLOUR_MERGE_TOLERANCE)
        if colours > 0:
            quantize(out, colours)
    shadow_removed = 0
    if found and shadows != "keep" and shadow.found and (shadows == "remove-all" or shadow.kind == "cast"):
        # last, once the palette is final, so that only shadow pixels change and nothing else does
        shadow_removed = SH.remove_shadow(out, bx, by, shadow, framing)
    crisp = found and flat is not None and flat >= T.VIEW_CELL_MIN_FLATNESS
    view = V.classify_view(rgba, (dx.p + dy.p) / 2 if crisp else None)   # no grid needed; crisp pixel art gets a pixel-sized blur
    subject = SUBJ.classify_subject(framing)
    removed = False
    if transparent and found and framing.kind == "isolated":
        removed = F.remove_background(out) > 0
    return Result(out, bx, by, dx.p, dy.p, found, raw, count_colours(out), view, framing, removed, status, note, subject, shadow, FC.classify_facing(framing, subject, shadow), flat, shadow_removed)


def snap_image(img: Image.Image, cell: float | None = None, follow: bool = True,
               colours: int = 0, transparent: bool = False, shadows: str = "keep") -> Result:
    """Convenience: Pillow image in, Result out. shadows: "keep", "remove-cast" (keep a contact shadow)
    or "remove-all"."""
    rgba = np.array(img.convert("RGBA"))
    return rebuild(rgba, analyse(rgba), cell, follow, colours, transparent, shadows)


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------

def brief_line(path: Path, res, tail: str = "") -> str:
    """One short line for a picture (about 100 characters): what it is, the grid, the view, the shadow."""
    w, h = res.size
    view = "facing ?" if res.subject.kind == "character" else f"view {res.view.kind}"
    shadow = f"shadow {res.shadow.kind}" if res.shadow.found else ("shadow ?" if res.shadow.unsure else "")
    bits = [res.subject.kind, f"grid {res.grid_status}", f"{w}x{h}" if res.grid_status != "none" else "", view, shadow, tail]
    return f"{path.name}: " + ", ".join(b for b in bits if b)


def run_sorted(args) -> int:
    """Batch mode: decide a folder for every picture, save or copy it there, and write report.csv."""
    import csv
    import shutil
    root = args.sort
    if not args.check_only:
        for b in SORT.BUCKETS:
            (root / b).mkdir(parents=True, exist_ok=True)
    else:
        root.mkdir(parents=True, exist_ok=True)
    rows, counts, status = [], {b: 0 for b in SORT.BUCKETS}, 0

    def free_name(folder: Path, name: str) -> Path:
        dest, n = folder / name, 2
        while dest.exists():
            dest = folder / f"{Path(name).stem}-{n}{Path(name).suffix}"
            n += 1
        return dest

    for path in args.inputs:
        try:
            res = snap_image(Image.open(path), args.cell, not args.no_follow, args.colours, args.transparent, args.shadows)
        except Exception as exc:
            print(f"{path}: could not read ({exc})", file=sys.stderr)
            status = 1
            continue
        d = SORT.decide(res, args.want_view, args.want_facing)
        counts[d.bucket] += 1
        saved = ""
        if not args.check_only:
            folder = root / d.bucket
            if d.bucket == "matches":
                w, h = res.size
                out = Image.fromarray(res.rgba, "RGBA")
                if args.scale > 1:
                    out = out.resize((w * args.scale, h * args.scale), Image.NEAREST)
                dest = free_name(folder, f"{path.stem}_snapped{'_WEAK' if d.weak else ''}.png")
                out.save(dest)
            else:
                dest = free_name(folder, path.name)
                shutil.copy2(path, dest)
            saved = str(dest.relative_to(root))
        rows.append(SORT.report_row(path, res, d, saved))
        if not args.brief:
            print(f"[{res.subject.kind.upper()}] {path.name}: {d.bucket}. {d.reason}")
        elif d.bucket != "matches":
            print(f"[{d.bucket}] {path.name}: {d.reason[:110]}")
    with open(root / "report.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SORT.REPORT_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print("\n" + ", ".join(f"{b}: {n}" for b, n in counts.items()) + f"  (report: {root / 'report.csv'})")
    return status


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Shrink an AI pixel-art image so one visible pixel becomes one real pixel.")
    ap.add_argument("inputs", nargs="+", type=Path, help="image files to convert")
    ap.add_argument("-o", "--output", type=Path, help="output file (one input) or folder (several inputs)")
    ap.add_argument("--cell", type=float, help="pixel size in the original, if you want to override auto-detection")
    ap.add_argument("--colors", "--colours", dest="colours", type=int, default=0, help="limit the palette to this many colours")
    ap.add_argument("--no-follow", action="store_true", help="assume a perfectly straight grid instead of following wobbles")
    ap.add_argument("--shadows", choices=["keep", "remove-cast", "remove-all"], default="keep",
                    help="ground shadows: keep them all (default), remove cast shadows but keep a small contact shadow, or remove all")
    ap.add_argument("--transparent", action="store_true", help="make the background transparent (lone sprites on a plain background only)")
    ap.add_argument("--skip-isometric", action="store_true", help="do not save pictures that look isometric (for when you need straight-on art)")
    ap.add_argument("--check-only", action="store_true", help="only report what each picture is and its view; save nothing")
    ap.add_argument("--want-view", choices=SORT.WANT_VIEW, default="either",
                    help="for buildings, objects and scenes: the view you need. Used with --sort")
    ap.add_argument("--want-facing", choices=SORT.WANT_FACING, default="either",
                    help="for characters: the facing you need (the facing check is not built yet, so a character is 'cant-tell'). Used with --sort")
    ap.add_argument("--brief", action="store_true",
                    help="short output, for scripts and AI sessions: one line per picture (with --sort, only pictures that are not matches, plus totals)")
    ap.add_argument("--sort", type=Path, metavar="FOLDER",
                    help="sort a batch into FOLDER/matches, mismatches, cant-tell and not-pixel-art, with a report.csv of every measurement")
    ap.add_argument("--scale", type=int, default=1, help="enlarge the saved picture by this whole number, without blur")
    args = ap.parse_args(argv)

    if args.sort:
        return run_sorted(args)
    many = len(args.inputs) > 1
    if many and args.output:
        args.output.mkdir(parents=True, exist_ok=True)
    status = 0
    for path in args.inputs:
        try:
            res = snap_image(Image.open(path), args.cell, not args.no_follow, args.colours, args.transparent, args.shadows)
        except Exception as exc:  # unreadable file: report and go on
            print(f"{path}: could not read ({exc})", file=sys.stderr)
            status = 1
            continue
        w, h = res.size
        tag = res.subject.kind.upper()
        is_character = res.subject.kind == "character"
        # characters are judged on which way they face, not on isometric vs orthographic (not built yet)
        view_text = res.facing.describe() if is_character else res.view.describe()
        shadow_text = f"; {res.shadow.describe()}" if (res.shadow.found or res.shadow.unsure) else ""
        if res.shadow.found and args.shadows != "keep":
            shadow_text += ("; shadow removed" if res.shadow_removed else
                            "; shadow kept (a contact shadow stays)" if args.shadows == "remove-cast" and res.shadow.kind == "contact"
                            else "; shadow NOT removed (no pixel grid to work on)")
        if args.check_only or (args.skip_isometric and res.view.kind == "isometric" and not is_character):
            why = "check only" if args.check_only else "skipped, because it is isometric"
            print(brief_line(path, res, f"not saved ({why})") if args.brief else
                  f"[{tag}] {path}: {res.subject.describe()}; {view_text}{shadow_text}; {w}x{h} pixels; not saved ({why})")
            continue
        if res.grid_status == "none":
            # nothing was snapped; a copy of the original under a "snapped" name would only mislead
            print(brief_line(path, res, "NOT SAVED") if args.brief else f"[{tag}] {path}: NOT SAVED. {res.grid_note}. {res.subject.describe()}")
            status = status or 2
            continue
        bg_note = ""
        if args.transparent:
            bg_note = ", background made transparent" if res.transparent else (
                ", background NOT removed (" + ("not a lone sprite on a plain background" if res.framing.kind != "isolated" else "no grid found or nothing to remove") + ")")
        out = Image.fromarray(res.rgba, "RGBA")
        if args.scale > 1:
            out = out.resize((w * args.scale, h * args.scale), Image.NEAREST)
        if args.output and not many:
            dest = args.output
        else:
            folder = args.output if args.output else path.parent
            dest = folder / f"{path.stem}_snapped.png"
        out.save(dest)
        note = f"pixel size {res.px:.2f} x {res.py:.2f}" + (" (WEAK grid: check the result)" if res.grid_status == "weak" else "")
        if args.brief:
            print(brief_line(path, res, f"saved {dest.name}" + (", shadow removed" if res.shadow_removed else "")))
        else:
            print(f"[{tag}] {path} -> {dest}: {w}x{h} pixels, {res.colours} colours, {note}; {view_text}; framing {res.framing.kind}{shadow_text}{bg_note}")
    return status


if __name__ == "__main__":
    sys.exit(main())

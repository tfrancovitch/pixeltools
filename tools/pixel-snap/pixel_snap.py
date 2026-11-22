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

The method matches the browser version (pixel-snap.html) in this folder.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

__all__ = ["analyse", "rebuild", "snap_image", "Analysis", "Result"]


# --------------------------------------------------------------------------
# Finding the grid
# --------------------------------------------------------------------------

def edge_profile(rgb: np.ndarray, axis: int) -> np.ndarray:
    """e[i] = average colour jump between line i-1 and line i (axis 0: columns, 1: rows)."""
    a = rgb.astype(np.int32)
    if axis == 1:
        a = a.transpose(1, 0, 2)
    h = a.shape[0]
    step = max(1, h // 600)
    a = a[::step]
    jump = np.abs(np.diff(a, axis=1)).sum(axis=2).mean(axis=0)  # length n-1
    e = np.zeros(a.shape[1], dtype=np.float64)
    e[1:] = jump
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


def detect_axis(e: np.ndarray) -> Axis:
    n = len(e)
    mean = _mean(e)
    if not mean > 1e-6:
        return Axis(1.0, 0.0, 0.0, False)
    min_p, max_p = 2.0, max(3.0, n / 6)
    a = smooth(e, 2)
    ps, ss = [], []
    p = min_p
    while p <= max_p:
        s, _ = _best_phase(a, p, mean, 1.0)
        ps.append(p)
        ss.append(s)
        p *= 1.001
    ps, ss = np.array(ps), np.array(ss)
    smax = float(ss.max())
    # Multiples of the true size score the same as the true size, so take the
    # smallest size that scores almost as well as the best one.
    first = int(np.argmax(ss >= 0.75 * smax))
    window = ps <= ps[first] * 1.06
    window[:first] = False
    pick = int(np.argmax(np.where(window, ss, -1)))
    pick = pick if ss[pick] > ss[first] else first
    a1 = smooth(e, 1)
    best = (-1.0, ps[pick], 0.0)
    for r in np.arange(0.996, 1.0041, 0.0001):
        pp = ps[pick] * r
        s, o = _best_phase(a1, pp, mean, 0.25)
        if s > best[0]:
            best = (s, pp, o)
    return Axis(best[1], best[2], smax, smax >= 1.5)


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


def merge_similar(rgba: np.ndarray, tol: float = 14.0) -> None:
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

    @property
    def size(self) -> tuple[int, int]:
        return self.rgba.shape[1], self.rgba.shape[0]


def analyse(rgba: np.ndarray) -> Analysis:
    rgb = rgba[..., :3]
    ex, ey = edge_profile(rgb, 0), edge_profile(rgb, 1)
    dx, dy = detect_axis(ex), detect_axis(ey)
    if not dx.ok and dy.ok:
        dx = fit_phase(ex, dy.p)
        dx.borrowed = True
    elif not dy.ok and dx.ok:
        dy = fit_phase(ey, dx.p)
        dy.borrowed = True
    return Analysis(ex, ey, dx, dy, dx.ok or dy.ok)


def rebuild(rgba: np.ndarray, an: Analysis, cell: float | None = None,
            follow: bool = True, colours: int = 0) -> Result:
    h, w = rgba.shape[:2]
    dx, dy, found = an.dx, an.dy, an.found
    if cell:
        dx, dy, found = fit_phase(an.ex, cell), fit_phase(an.ey, cell), True
    if not found:
        dx = dy = Axis(1.0, 0.0, 0.0, False)
    bx = make_bounds(an.ex, dx.p, dx.off, w, follow)
    by = make_bounds(an.ey, dy.p, dy.off, h, follow)
    out = sample_cells(rgba, bx, by)
    raw = count_colours(out)
    merge_similar(out, 14.0)
    if colours > 0:
        quantize(out, colours)
    return Result(out, bx, by, dx.p, dy.p, found, raw, count_colours(out))


def snap_image(img: Image.Image, cell: float | None = None, follow: bool = True,
               colours: int = 0) -> Result:
    """Convenience: Pillow image in, Result out."""
    rgba = np.array(img.convert("RGBA"))
    return rebuild(rgba, analyse(rgba), cell, follow, colours)


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Shrink an AI pixel-art image so one visible pixel becomes one real pixel.")
    ap.add_argument("inputs", nargs="+", type=Path, help="image files to convert")
    ap.add_argument("-o", "--output", type=Path, help="output file (one input) or folder (several inputs)")
    ap.add_argument("--cell", type=float, help="pixel size in the original, if you want to override auto-detection")
    ap.add_argument("--colors", "--colours", dest="colours", type=int, default=0, help="limit the palette to this many colours")
    ap.add_argument("--no-follow", action="store_true", help="assume a perfectly straight grid instead of following wobbles")
    ap.add_argument("--scale", type=int, default=1, help="enlarge the saved picture by this whole number, without blur")
    args = ap.parse_args(argv)

    many = len(args.inputs) > 1
    if many and args.output:
        args.output.mkdir(parents=True, exist_ok=True)
    status = 0
    for path in args.inputs:
        try:
            res = snap_image(Image.open(path), args.cell, not args.no_follow, args.colours)
        except Exception as exc:  # unreadable file: report and go on
            print(f"{path}: could not read ({exc})", file=sys.stderr)
            status = 1
            continue
        w, h = res.size
        out = Image.fromarray(res.rgba, "RGBA")
        if args.scale > 1:
            out = out.resize((w * args.scale, h * args.scale), Image.NEAREST)
        if args.output and not many:
            dest = args.output
        else:
            folder = args.output if args.output else path.parent
            dest = folder / f"{path.stem}_snapped.png"
        out.save(dest)
        if res.found or args.cell:
            note = f"pixel size {res.px:.2f} x {res.py:.2f}"
        else:
            note = "NO CLEAR GRID FOUND (image may already be true size; try --cell)"
            status = status or 2
        print(f"{path} -> {dest}: {w}x{h} pixels, {res.colours} colours, {note}")
    return status


if __name__ == "__main__":
    sys.exit(main())

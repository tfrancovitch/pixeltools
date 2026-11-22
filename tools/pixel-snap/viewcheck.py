# Isometric or orthographic? For buildings, objects and scenes. No AI, no pixel grid needed.
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
"""Isometric art is built from long straight lines at about 26 to 30 degrees, in two directions (rising
and falling walls), with almost no horizontal edges. Straight-on (orthographic) and top-down art is built
from horizontal and vertical lines.

A picture full of trees and grass hides those lines among edges that point every which way. So each
spot is weighed by how coherent its edge direction is across a wider neighbourhood: a long straight
edge is coherent, foliage is not. Only coherent spots vote.

Characters are not judged here: for a character the useful question is which way it faces (slice C2).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

import tuning as T


@dataclass
class ViewVerdict:
    kind: str                  # "isometric", "orthogonal" or "unclear"
    horizontal: float          # share of coherent edge weight on horizontal lines
    vertical: float            # ... on vertical lines
    diagonal: float            # ... on the isometric slopes (about 23 to 34 degrees, either direction)
    weaker_diagonal: float = 0.0   # the smaller of the rising and falling diagonal shares
    coverage: float = 0.0      # share of the picture that had a coherent edge direction

    def describe(self) -> str:
        return (f"{self.kind} (diagonals {self.diagonal:.0%} with both directions {self.weaker_diagonal:.0%}+, "
                f"horizontals {self.horizontal:.0%}, verticals {self.vertical:.0%})")


def _gauss(a: np.ndarray, s: float) -> np.ndarray:
    r = int(3 * s) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2)
    k /= k.sum()
    h, w = a.shape
    p = np.pad(a, r, mode="edge")
    x = sum(k[i] * p[:, i:i + w] for i in range(2 * r + 1))
    return sum(k[i] * x[i:i + h, :] for i in range(2 * r + 1))


def _normalised(rgba: np.ndarray) -> tuple[np.ndarray, int]:
    """The picture at a standard size (float, h x w x 4), so one set of numbers fits every picture,
    and the whole-number factor it was enlarged by (1 if it was not)."""
    im = Image.fromarray(rgba, "RGBA")
    long_side = max(im.size)
    if long_side > T.VIEW_SIDE:
        k = T.VIEW_SIDE / long_side
        im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.BOX)
        return np.array(im).astype(np.float64), 1
    if long_side < T.VIEW_MIN_SIDE:
        k = -(-T.VIEW_MIN_SIDE // long_side)            # whole-number enlargement keeps pixel-art stair steps crisp
        im = im.resize((im.width * k, im.height * k), Image.NEAREST)
        return np.array(im).astype(np.float64), k
    return np.array(im).astype(np.float64), 1


def classify_view(rgba: np.ndarray, cell: float | None = None) -> ViewVerdict:
    """cell: the pixel size in the original picture, when known. Crisp pixel art has staircase edges, so
    the blur is sized to the pixel; without it (painted or soft pictures) a small fixed blur is used."""
    a, enlarged = _normalised(rgba)
    long_side = max(a.shape[:2])
    s_grad, s_win = T.VIEW_GRAD_SIGMA, max(1.5, T.VIEW_WINDOW_FRACTION * long_side)
    if cell is None and enlarged > 1:
        cell = 1.0                                              # a small picture is native pixel art: one pixel per art pixel
    if cell:
        cell_norm = cell * a.shape[1] / rgba.shape[1]           # the pixel size after standardising the picture
        s_grad = max(s_grad, T.VIEW_CELL_BLUR * cell_norm)
        s_win = max(s_win, T.VIEW_CELL_WINDOW * cell_norm)
    jxx = jyy = jxy = 0.0
    for c in range(4):                                   # colour channels and transparency
        b = _gauss(a[..., c], s_grad)
        dx = np.zeros_like(b)
        dy = np.zeros_like(b)
        dx[:, 1:-1] = (b[:, 2:] - b[:, :-2]) / 2
        dy[1:-1, :] = (b[2:, :] - b[:-2, :]) / 2
        jxx, jyy, jxy = jxx + dx * dx, jyy + dy * dy, jxy + dx * dy
    energy = jxx + jyy
    sxx, syy, sxy = _gauss(jxx, s_win), _gauss(jyy, s_win), _gauss(jxy, s_win)
    coherence = np.sqrt((sxx - syy) ** 2 + 4 * sxy ** 2) / np.maximum(sxx + syy, 1e-9)
    line = (np.degrees(0.5 * np.arctan2(2 * sxy, sxx - syy)) + 90) % 180      # 0 = horizontal line
    keep = (coherence >= T.VIEW_COHERENCE_MIN) & (energy > np.percentile(energy, T.VIEW_ENERGY_PERCENTILE))
    coverage = float(keep.mean())
    if coverage < T.VIEW_MIN_COVERAGE:
        return ViewVerdict("unclear", 0.0, 0.0, 0.0, 0.0, coverage)
    w = (energy * coherence ** 2)[keep]
    ln = line[keep]
    dev = np.abs(((ln + 90) % 180) - 90)                 # 0..90 away from horizontal
    tot = w.sum()
    horiz = float(w[dev <= T.VIEW_AXIS_TOLERANCE].sum() / tot)
    vert = float(w[dev >= 90 - T.VIEW_AXIS_TOLERANCE].sum() / tot)
    rising = float(w[(ln >= T.VIEW_ISO_MIN_DEG) & (ln <= T.VIEW_ISO_MAX_DEG)].sum() / tot)
    falling = float(w[(ln >= 180 - T.VIEW_ISO_MAX_DEG) & (ln <= 180 - T.VIEW_ISO_MIN_DEG)].sum() / tot)
    diag = rising + falling
    weaker = min(rising, falling)
    counts, _ = np.histogram(ln, bins=180, range=(0, 180), weights=w)
    pr = counts[counts > 0] / counts.sum()
    entropy = float(-(pr * np.log(pr)).sum() / np.log(180))      # 1 = edges point every which way equally
    if entropy >= T.VIEW_MAX_ENTROPY:
        return ViewVerdict("unclear", horiz, vert, diag, weaker, coverage)
    if diag - horiz >= T.ISO_DIAGONAL_MARGIN and weaker >= T.ISO_BOTH_FAMILIES_MIN:
        kind = "isometric"
    elif horiz + vert >= T.ORTHO_AXIS_MIN and diag - horiz < T.ISO_DIAGONAL_MARGIN:
        kind = "orthogonal"
    else:
        kind = "unclear"
    return ViewVerdict(kind, horiz, vert, diag, weaker, coverage)

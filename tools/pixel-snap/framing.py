# Background, subject mask and framing for Pixel Snap.
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
"""Is this a lone sprite on a plain background, or a whole scene? And which pixels are background?

    estimate_background(rgba)   -> Background   (a plain colour or a gentle gradient, from the border)
    classify_framing(rgba)      -> Framing      ("isolated" or "scene", with the evidence)
    remove_background(sprite)   -> None         (makes background that touches the edge transparent)

No AI: the border is sampled, a gentle gradient is fitted to it, and the subject is whatever differs
from that. A subject standing on a full painted or textured background ("subject on background")
cannot be told from a scene by this test yet and is reported as "scene".
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np

import tuning as T


@dataclass
class Background:
    coef: np.ndarray                  # 3 channels x [constant, x slope, y slope]
    colour: tuple[int, int, int]      # typical border colour
    uniform: float                    # share of border pixels within tolerance of the fitted background

    def field(self, h: int, w: int) -> np.ndarray:
        """The fitted background colour at every pixel, as floats (h, w, 3)."""
        yy, xx = np.mgrid[0:h, 0:w]
        feat = np.stack([np.ones((h, w)), xx / max(w, 1), yy / max(h, 1)], axis=-1)
        return feat @ self.coef.T

    def distance(self, rgb: np.ndarray) -> np.ndarray:
        """How far each pixel is from the background (sum of channel differences)."""
        h, w = rgb.shape[:2]
        return np.abs(rgb.astype(np.float32) - self.field(h, w).astype(np.float32)).sum(axis=2)


def _border_samples(rgb: np.ndarray, band: int):
    h, w = rgb.shape[:2]
    band = min(band, max(1, min(h, w) // 2))
    ys, xs = [], []
    for sl_y, sl_x in ((slice(0, band), slice(0, w)), (slice(h - band, h), slice(0, w)),
                       (slice(band, h - band), slice(0, band)), (slice(band, h - band), slice(w - band, w))):
        yy, xx = np.mgrid[sl_y, sl_x]
        ys.append(yy.ravel())
        xs.append(xx.ravel())
    ys, xs = np.concatenate(ys), np.concatenate(xs)
    return ys, xs, rgb[ys, xs].astype(np.float64)


def estimate_background(rgba: np.ndarray, band_px: int | None = None) -> Background:
    """Fit a gentle gradient to the border. Pixels that do not fit (the sprite's feet touching
    the edge, say) are dropped and the fit repeated."""
    rgb = rgba[..., :3]
    h, w = rgb.shape[:2]
    band = band_px or max(T.BG_BORDER_MIN_PX, int(round(T.BG_BORDER_BAND * min(h, w))))
    ys, xs, col = _border_samples(rgb, band)
    feat = np.stack([np.ones(len(xs)), xs / max(w, 1), ys / max(h, 1)], axis=1)
    keep = np.ones(len(xs), dtype=bool)
    coef = np.zeros((3, 3))
    med = np.median(col, axis=0)
    coef[:, 0] = med
    for _ in range(T.BG_FIT_ROUNDS):
        if keep.sum() < 3:
            break
        sol, *_ = np.linalg.lstsq(feat[keep], col[keep], rcond=None)   # (3 features, 3 channels)
        coef = sol.T
        resid = np.abs(col - feat @ coef.T).sum(axis=1)
        new_keep = resid <= T.BG_TOLERANCE
        if new_keep.sum() < 0.2 * len(xs):      # the border is mostly not background: stop refining
            break
        keep = new_keep
    resid = np.abs(col - feat @ coef.T).sum(axis=1)
    return Background(coef, tuple(int(v) for v in med), float((resid <= T.BG_TOLERANCE).mean()))


def _components(mask: np.ndarray):
    """Connected blobs (8-neighbour) of a boolean mask: list of (cells, area)."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    for y0, x0 in zip(*np.nonzero(mask)):
        if seen[y0, x0]:
            continue
        cells, dq = [], deque([(y0, x0)])
        seen[y0, x0] = True
        while dq:
            y, x = dq.popleft()
            cells.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        dq.append((ny, nx))
        out.append(cells)
    return out


@dataclass
class Framing:
    kind: str                         # "isolated", "scene" or "unclear" (nothing found)
    border_uniform: float             # share of the border that is plain background
    subject_share: float              # share of the picture covered by the subject
    fill: float                       # share of the subject's bounding box it covers
    aspect: float                     # subject height / width
    touches_border: bool
    bbox: tuple[int, int, int, int]   # x0, y0, x1, y1 in the original picture
    background: Background = field(repr=False)
    mask: np.ndarray = field(repr=False, default=None)   # subject mask, coarse
    scale: int = 1                    # original pixels per mask cell

    def describe(self) -> str:
        return (f"{self.kind} (border {self.border_uniform:.0%} plain, subject covers {self.subject_share:.0%}, "
                f"height/width {self.aspect:.1f})")


def classify_framing(rgba: np.ndarray) -> Framing:
    h, w = rgba.shape[:2]
    bg = estimate_background(rgba)
    s = max(1, -(-max(h, w) // T.MASK_MAX_SIDE))
    hh, ww = h // s * s, w // s * s
    dist = bg.distance(rgba[:hh, :ww, :3])
    ds = (dist > T.SUBJECT_DISTANCE).reshape(hh // s, s, ww // s, s).mean(axis=(1, 3)) > 0.5
    comps = _components(ds)
    total = ds.size
    big = [c for c in comps if len(c) >= T.SPECK_SHARE * total] or sorted(comps, key=len)[-1:]
    mask = np.zeros_like(ds)
    for c in big:
        for y, x in c:
            mask[y, x] = True
    area = int(mask.sum())
    if area == 0:
        return Framing("unclear", bg.uniform, 0.0, 0.0, 0.0, False, (0, 0, 0, 0), bg, mask, s)
    ys, xs = np.nonzero(mask)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    bh, bw = y1 - y0 + 1, x1 - x0 + 1
    share = area / total
    touches = bool(y0 == 0 or x0 == 0 or y1 == mask.shape[0] - 1 or x1 == mask.shape[1] - 1)
    isolated = bg.uniform >= T.FRAMING_UNIFORM_MIN and share <= T.FRAMING_SUBJECT_MAX
    return Framing("isolated" if isolated else "scene", bg.uniform, share, area / (bh * bw), bh / bw, touches,
                   (int(x0 * s), int(y0 * s), int((x1 + 1) * s), int((y1 + 1) * s)), bg, mask, s)


def remove_background(sprite: np.ndarray) -> int:
    """Make the background of a snapped sprite transparent, in place. Only background that
    connects to the sprite's edge is removed, so a background-coloured patch inside the sprite
    (a white shirt on a white ground, the gap inside a ring) is kept. Returns pixels removed."""
    h, w = sprite.shape[:2]
    bg = estimate_background(sprite, band_px=1)
    near = bg.distance(sprite[..., :3]) <= T.TRANSPARENT_TOLERANCE
    reach = np.zeros_like(near)
    dq = deque()
    for y in range(h):
        for x in (0, w - 1):
            if near[y, x] and not reach[y, x]:
                reach[y, x] = True
                dq.append((y, x))
    for x in range(w):
        for y in (0, h - 1):
            if near[y, x] and not reach[y, x]:
                reach[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and near[ny, nx] and not reach[ny, nx]:
                reach[ny, nx] = True
                dq.append((ny, nx))
    sprite[reach] = 0
    return int(reach.sum())

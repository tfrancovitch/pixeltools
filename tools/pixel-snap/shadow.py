# Find the ground shadow under a lone sprite. No AI.
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
"""A ground shadow is the ground colour made darker by a steady amount: a flat patch of "darker ground"
attached to the base of the subject. This module finds it.

How, in plain steps:

1. The ground colour at every spot is already known from the border (framing.py fits a plain colour or a
   gentle gradient).
2. A pixel is shadow-like if it is the ground colour times one factor between 0.15 and 0.92, the same
   factor in all three colour channels (a shadow keeps the ground's hue). Black outlines are darker than
   that; the ground itself is lighter.
3. Shadow-like pixels form patches. A patch counts as a shadow only if it sits at the subject's base
   (its centre at or below the base line, within a body width or so), touches the subject, is flat
   (steady darkness) and is big enough.

Self-shading on the sprite itself is never touched: sprite pixels are not the ground colour made
darker, and patches higher up the sprite fail the base test.

Only lone sprites on a plain or gradient ground are examined. Whole scenes, and sprites on a full
painted background, have shadows that are part of the picture.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import framing as F
import tuning as T


@dataclass
class ShadowInfo:
    found: bool
    reason: str                       # one plain sentence
    unsure: bool = False              # True when the picture cannot be judged (a white ground), as opposed to "no shadow"
    share: float = 0.0                # shadow area / subject area (subject = everything that is not shadow or ground)
    darkness: float = 1.0             # typical factor the ground colour is multiplied by (smaller = darker)
    dx: float = 0.0                   # shadow centre relative to the subject's base centre, in subject widths (right = positive)
    dy: float = 0.0                   # ... in subject heights (down = positive)
    mask: np.ndarray | None = field(default=None, repr=False)   # coarse shadow mask
    scale: int = 1                    # original pixels per mask cell

    def describe(self) -> str:
        if self.unsure:
            return f"shadow: can't tell ({self.reason})"
        if not self.found:
            return f"no ground shadow ({self.reason})"
        side = "to the left" if self.dx < -0.15 else "to the right" if self.dx > 0.15 else "under the base"
        return f"ground shadow {side} ({self.share:.0%} of the subject, {self.darkness:.0%} of the ground brightness)"


def _blocks(a: np.ndarray, s: int) -> np.ndarray:
    h, w = a.shape[0] // s * s, a.shape[1] // s * s
    a = a[:h, :w]
    return a.reshape(h // s, s, w // s, s, *a.shape[2:]).mean(axis=(1, 3))


def find_shadow(rgba: np.ndarray, framing: F.Framing) -> ShadowInfo:
    if framing.kind != "isolated" or framing.mask is None:
        return ShadowInfo(False, "not a lone sprite on a plain ground")
    colour = np.array(framing.background.colour, dtype=float)
    if colour.mean() >= T.SHADOW_WHITE_GROUND and colour.max() - colour.min() <= 20:
        return ShadowInfo(False, "on a white ground a pale shadow looks the same as pale grey parts of the sprite", unsure=True)
    s = framing.scale
    rgb = _blocks(rgba[..., :3].astype(np.float64), s)
    hh, ww = rgb.shape[:2]
    # the ground colour at the middle of every block (same plane as the full-size fit, evaluated at block centres)
    yy, xx = np.mgrid[0:hh, 0:ww]
    full_h, full_w = rgba.shape[:2]
    feat = np.stack([np.ones((hh, ww)), (xx * s + s / 2) / full_w, (yy * s + s / 2) / full_h], axis=-1)
    ground = feat @ framing.background.coef.T
    brightness = ground.mean(axis=2)
    ratio = rgb / np.maximum(ground, 1.0)
    k = ratio.mean(axis=2)
    chroma = np.abs(ratio - k[..., None]).max(axis=2)
    like = (k >= T.SHADOW_K_MIN) & (k <= T.SHADOW_K_MAX) & (chroma <= T.SHADOW_CHROMA_DEV) & (brightness >= T.SHADOW_MIN_GROUND)

    mask = framing.mask[:hh, :ww]
    open_ground = ~mask & (k > T.SHADOW_K_MAX) & (k < 1.15)          # plain ground well away from the subject

    # Step 1: connected regions of darker ground that lie on open ground. Clothing, and blurry blends inside
    # the sprite, are enclosed by the sprite; a shadow's outer edge meets the open ground.
    eligible = np.zeros_like(like)
    notes = []
    for region in F._components(like):
        if len(region) < T.SHADOW_MIN_CELLS:
            continue
        ry = np.array([c[0] for c in region])
        rx = np.array([c[1] for c in region])
        patch = np.zeros_like(like)
        patch[ry, rx] = True
        ring = patch.copy()
        ring[1:] |= patch[:-1]; ring[:-1] |= patch[1:]; ring[:, 1:] |= patch[:, :-1]; ring[:, :-1] |= patch[:, 1:]
        ring &= ~patch
        if ring.sum() == 0 or open_ground[ring].mean() < T.SHADOW_GROUND_CONTACT:
            notes.append("enclosed by the sprite, not lying on open ground")
            continue
        eligible |= patch

    # The subject is everything that differs from the ground and is not such a region.
    core = mask & ~eligible
    if core.sum() < 4:
        return ShadowInfo(False, "no subject found")
    comps = F._components(core)
    keep = max(comps, key=len)
    big = [c for c in comps if len(c) >= 0.15 * len(keep)] or [keep]
    core = np.zeros_like(core)
    for c in big:
        for y, x in c:
            core[y, x] = True
    ys, xs = np.nonzero(core)
    cy0, cy1, cx0, cx1 = ys.min(), ys.max(), xs.min(), xs.max()
    core_h, core_w = cy1 - cy0 + 1, cx1 - cx0 + 1
    base_y, base_x = cy1, (cx0 + cx1) / 2

    # grow the subject by two cells: a shadow touches it
    near = core.copy()
    for _ in range(2):
        n = near.copy()
        n[1:] |= near[:-1]; n[:-1] |= near[1:]; n[:, 1:] |= near[:, :-1]; n[:, :-1] |= near[:, 1:]
        near = n

    # Step 2: a flat shadow lives inside one band of darkness. Looking at the bands one at a time keeps it
    # apart from other dark parts that touch it. Bands overlap so a shadow is never split.
    accepted = np.zeros_like(like)
    width = 2 * T.SHADOW_FLAT_STD
    for lo in np.arange(T.SHADOW_K_MIN, T.SHADOW_K_MAX, width / 2):
        band = eligible & (k >= lo) & (k < lo + width)
        for comp in F._components(band):
            if len(comp) < T.SHADOW_MIN_CELLS:
                continue
            cys = np.array([c[0] for c in comp])
            cxs = np.array([c[1] for c in comp])
            if len(comp) < T.SHADOW_PIECE_SHARE * core.sum():
                notes.append("too small")
                continue
            if cys.mean() < base_y - T.SHADOW_BASE_ALLOWANCE * core_h:
                notes.append("higher up the subject, not at the base")
                continue
            if abs(cxs.mean() - base_x) > T.SHADOW_REACH * core_w + core_w / 2:
                notes.append("too far to the side")
                continue
            if not near[cys, cxs].any():
                notes.append("does not touch the subject")
                continue
            accepted[cys, cxs] = True
    if not accepted.any():
        return ShadowInfo(False, notes[0] if notes else "no darker-ground patch at the base")
    if accepted.sum() < T.SHADOW_MIN_SHARE * core.sum():
        return ShadowInfo(False, "only small darker patches at the base")
    if accepted.sum() > T.SHADOW_MAX_SHARE * core.sum():
        return ShadowInfo(False, "the darker patch is as big as the subject itself: probably its own dark colours")
    sy, sx = np.nonzero(accepted)
    if (sx.max() - sx.min() + 1) < T.SHADOW_MIN_ASPECT * (sy.max() - sy.min() + 1):
        return ShadowInfo(False, "the darker patch is taller than wide, like a limb or trunk, not a shadow lying on the ground")
    return ShadowInfo(True, "a flat patch of darker ground at the base",
                      share=float(accepted.sum() / core.sum()), darkness=float(k[accepted].mean()),
                      dx=float((sx.mean() - base_x) / core_w), dy=float((sy.mean() - base_y) / core_h),
                      mask=accepted, scale=s)

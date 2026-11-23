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
    reach_left: float = 0.0           # how far the shadow sticks out past the subject on the left, in subject widths
    reach_right: float = 0.0          # ... on the right
    kind: str = ""                    # "contact" (a small patch under the base) or "cast" (reaches clearly to one side)

    def describe(self) -> str:
        if self.unsure:
            return f"shadow: can't tell ({self.reason})"
        if not self.found:
            return f"no ground shadow ({self.reason})"
        side = "falling to the left" if self.dx < -0.15 else "falling to the right" if self.dx > 0.15 else "under the base"
        return f"{self.kind} shadow {side} ({self.share:.0%} of the subject, {self.darkness:.0%} of the ground brightness)"


def _blocks(a: np.ndarray, s: int) -> np.ndarray:
    h, w = a.shape[0] // s * s, a.shape[1] // s * s
    a = a[:h, :w]
    return a.reshape(h // s, s, w // s, s, *a.shape[2:]).mean(axis=(1, 3))


def _kind(dx: float, reach_left: float, reach_right: float) -> str:
    """A cast shadow falls to one side: its centre is off to the side, or it sticks out much further on one
    side than the other. A contact shadow sits under the base, about as far out on both sides."""
    if abs(dx) >= T.SHADOW_CAST_OFFSET or abs(reach_left - reach_right) >= T.SHADOW_CAST_ASYMMETRY:
        return "cast"
    return "contact"


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
    reach_left = max(0.0, (cx0 - sx.min()) / core_w)
    reach_right = max(0.0, (sx.max() + 1 - (cx1 + 1)) / core_w)
    if (sx.max() - sx.min() + 1) < T.SHADOW_MIN_ASPECT * (sy.max() - sy.min() + 1):
        return ShadowInfo(False, "the darker patch is taller than wide, like a limb or trunk, not a shadow lying on the ground")
    return ShadowInfo(True, "a flat patch of darker ground at the base",
                      share=float(accepted.sum() / core.sum()), darkness=float(k[accepted].mean()),
                      dx=float((sx.mean() - base_x) / core_w), dy=float((sy.mean() - base_y) / core_h),
                      mask=accepted, scale=s, reach_left=float(reach_left), reach_right=float(reach_right),
                      kind=_kind((sx.mean() - base_x) / core_w, reach_left, reach_right))


def remove_shadow(sprite: np.ndarray, bx: list[int], by: list[int], info: ShadowInfo, framing: F.Framing) -> int:
    """Turn the ground shadow in a snapped sprite back into plain ground, in place. Returns how many
    sprite pixels were changed.

    A sprite pixel is changed only if BOTH hold: it lies inside the shadow found in the original
    picture (grown by one coarse cell, to take the soft fringe), and its colour is the ground colour
    made darker. Everything else, the sprite itself above all, is left exactly as it was."""
    if not info.found or info.mask is None:
        return 0
    s = info.scale
    full_w, full_h = bx[-1], by[-1]
    ox = (np.array(bx[:-1]) + np.array(bx[1:])) / 2          # centre of every sprite pixel in the original picture
    oy = (np.array(by[:-1]) + np.array(by[1:])) / 2
    h, w = len(oy), len(ox)
    feat = np.stack([np.ones((h, w)), np.broadcast_to(ox / full_w, (h, w)), np.broadcast_to((oy / full_h)[:, None], (h, w))], axis=-1)
    ground = feat @ framing.background.coef.T
    grown = info.mask.copy()
    grown[1:] |= info.mask[:-1]; grown[:-1] |= info.mask[1:]
    grown[:, 1:] |= info.mask[:, :-1]; grown[:, :-1] |= info.mask[:, 1:]
    cy = np.clip((oy / s).astype(int), 0, grown.shape[0] - 1)
    cx = np.clip((ox / s).astype(int), 0, grown.shape[1] - 1)
    inside = grown[cy[:, None], cx[None, :]]
    ratio = sprite[..., :3].astype(np.float64) / np.maximum(ground, 1.0)
    k = ratio.mean(axis=2)
    chroma = np.abs(ratio - k[..., None]).max(axis=2)
    darker_ground = (k >= T.SHADOW_K_MIN) & (k <= T.SHADOW_REMOVE_K_MAX) & (chroma <= T.SHADOW_CHROMA_DEV) & (sprite[..., 3] >= 128)
    remove = inside & darker_ground
    if not remove.any():
        return 0
    # Put back the sprite's own ground colour: the colour already used by the open-ground pixels that is closest
    # to the fitted ground at that spot. That way no new off-by-a-few colour appears.
    open_px = ~grown[cy[:, None], cx[None, :]] & (k >= 0.97) & (k <= 1.05) & (chroma <= 0.05)
    palette = np.unique(sprite[open_px][:, :3], axis=0) if open_px.any() else np.zeros((0, 3), np.uint8)
    wanted = np.clip(np.rint(ground[remove]), 0, 255)
    if len(palette):
        d = np.abs(wanted[:, None, :] - palette[None, :, :].astype(float)).sum(axis=2)
        best = d.argmin(axis=1)
        pick = np.where(d[np.arange(len(wanted)), best] <= 2 * T.COLOUR_MERGE_TOLERANCE, best, -1)
        wanted = np.where((pick >= 0)[:, None], palette[np.maximum(pick, 0)].astype(float), wanted)
    sprite[remove, :3] = wanted.astype(np.uint8)
    return int(remove.sum())

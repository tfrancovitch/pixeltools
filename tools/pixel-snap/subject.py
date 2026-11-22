# What is it? character / building / scene, from the shape of the subject. No AI.
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
"""Decide whether a picture shows a character, a building or a whole scene.

The framing check (framing.py) already separates a lone sprite on a plain background from a scene.
For a lone sprite, the silhouette's shape decides:

  building   roughly square, a pointed bottom (the diamond footprint of an isometric base) and a roof
             narrower than the body
  character  tall: at least 1.4 times as high as wide
  unclear    anything else, for example a chibi character (nearly square) or a flat-based box

Silhouettes include any ground shadow for now (the shadow slices will trim them). "Object" is not
a category yet: it needs real examples (the object tuning batch). Orthographic (front-view) buildings
are not recognised yet for the same reason, and come back "unclear".
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import framing as F
import tuning as T


@dataclass
class SubjectVerdict:
    kind: str          # "character", "building", "scene" or "unclear"
    reason: str        # one plain sentence
    aspect: float      # silhouette height / width
    top: float         # top-quarter width relative to the middle
    base: float        # bottom-row width relative to the widest row

    def describe(self) -> str:
        return f"{self.kind} ({self.reason})"


def silhouette_shape(mask: np.ndarray) -> tuple[float, float, float]:
    """(height / width, top width / middle width, bottom width / widest row) of a subject mask."""
    ys, xs = np.nonzero(mask)
    sub = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = sub.shape
    widths = sub.sum(axis=1) / w
    mid = widths[h // 4: 3 * h // 4].mean() if h >= 4 else widths.mean()
    top = widths[:max(1, h // 4)].mean()
    return h / w, float(top / max(mid, 1e-9)), float(widths[-1] / max(widths.max(), 1e-9))


def classify_subject(framing: F.Framing) -> SubjectVerdict:
    if framing.kind == "scene":
        return SubjectVerdict("scene", "the border is busy, so the picture is a whole scene, not a lone sprite", 0.0, 0.0, 0.0)
    if framing.kind != "isolated" or framing.mask is None or not framing.mask.any():
        return SubjectVerdict("unclear", "no subject found", 0.0, 0.0, 0.0)
    aspect, top, base = silhouette_shape(framing.mask)
    if aspect <= T.SUBJECT_BUILDING_ASPECT_MAX and base <= T.SUBJECT_BUILDING_BASE_MAX and top <= T.SUBJECT_BUILDING_TOP_MAX:
        return SubjectVerdict("building", "roughly square, with a pointed base and a narrower top, like an isometric building", aspect, top, base)
    if aspect >= T.SUBJECT_CHARACTER_ASPECT_MIN:
        return SubjectVerdict("character", f"a tall figure ({aspect:.1f} times as high as wide)", aspect, top, base)
    return SubjectVerdict("unclear", f"nearly square ({aspect:.1f}) without the pointed base of an isometric building: "
                          "could be a chibi character, an object or a front-view building", aspect, top, base)

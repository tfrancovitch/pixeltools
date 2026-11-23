# Which way is a character facing? Result of the C2 experiment: the tool measures, but does not decide.
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
"""Facing (diagonal, cardinal or mixed) for characters.

STATUS: no rule is adopted. The verdict is always "unclear" for a character.

Why. Slice C2 of the plan was an experiment with a stop rule: find at least 5 of the 6 clearly diagonal
characters in batch 1, call at most 3 of the 43 clearly cardinal ones diagonal, within two tuning passes.
The clues that mean something about facing are geometric: left-right symmetry of the silhouette, where
the feet are, how far the head sits off the torso, how far the torso sits off the legs. An exhaustive
search over single clues and pairs of clues found no rule that met the gate (best: 4 of 6 with 3 false
calls, or 5 of 6 with 7 false calls) and, with thousands of candidate rules and six examples, even
those are likely chance. The only features that did separate the six pictures were "has a ground
shadow" and "squat, chibi proportions". Those describe the style of the six pictures (chibi figures
standing on coloured ground), not which way they face, so using them would be overfitting.

What would change this: many more labelled characters (the labelling game), or a face and pose reader,
which is a model and therefore outside the "no AI" rule. See eval/facing_probe.py to reproduce the search.

So the tool measures the clues and writes them to the report, for people and for later fitting, and
says "can't tell".
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import framing as F


@dataclass
class FacingVerdict:
    kind: str                                  # "unclear" for a character, "n/a" for anything else
    reason: str
    clues: dict = field(default_factory=dict)  # measurements, for the report

    def describe(self) -> str:
        return f"facing: can't tell ({self.reason})" if self.kind == "unclear" else f"facing: {self.kind}"


def measure_clues(framing: F.Framing, shadow=None) -> dict:
    """Geometric clues from the subject's silhouette (ground shadow cut away). All are shares of the
    silhouette's width or height, so they do not depend on the picture's size."""
    m = framing.mask.copy()
    if shadow is not None and shadow.found and shadow.mask is not None:
        sm = shadow.mask
        m[:sm.shape[0], :sm.shape[1]] &= ~sm
    if m.sum() < 20:
        return {}
    ys, xs = np.nonzero(m)
    sub = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = sub.shape
    cols = np.arange(w)

    def centre(mask):
        t = mask.sum()
        return (mask.sum(axis=0) * cols).sum() / t if t else w / 2

    nb = max(2, int(0.14 * h))                                         # the feet: the bottom 14 percent of rows
    blobs = sorted(F._components(sub[-nb:]), key=len, reverse=True)
    blobs = [b for b in blobs if len(b) >= 0.012 * sub.sum()] or blobs[:1]
    feet_dx = feet_dy = 0.0
    if len(blobs) >= 2:
        (c1, c2) = blobs[0], blobs[1]
        feet_dx = abs(np.mean([p[1] for p in c1]) - np.mean([p[1] for p in c2])) / w
        feet_dy = abs(np.mean([p[0] for p in c1]) - np.mean([p[0] for p in c2])) / h
    top, bottom = sub[:int(0.4 * h)], sub[int(0.6 * h):]
    head, torso = sub[:max(2, int(0.22 * h))], sub[int(0.25 * h):int(0.6 * h)]
    return {
        "symmetry": round(float((sub & sub[:, ::-1]).sum() / sub.sum()), 3),     # 1 = mirror-symmetric (front or back view)
        "feet_apart": round(float(feet_dx), 3),                                    # sideways gap between the two feet
        "feet_level": round(float(feet_dy), 3),                                    # height difference between the feet
        "torso_leg_shift": round(float((centre(top) - centre(bottom)) / w), 3),    # upper body off the legs (signed)
        "head_off_torso": round(float((centre(head) - centre(torso)) / w), 3),     # head off the torso (signed)
        "height_over_width": round(float(h / w), 2),
    }


def classify_facing(framing: F.Framing, subject, shadow=None) -> FacingVerdict:
    if subject.kind != "character" or framing.kind != "isolated" or framing.mask is None:
        return FacingVerdict("n/a", "only characters are judged on facing")
    return FacingVerdict("unclear",
                         "the geometric clues did not separate diagonal from straight-on facing; see facing.py",
                         measure_clues(framing, shadow))

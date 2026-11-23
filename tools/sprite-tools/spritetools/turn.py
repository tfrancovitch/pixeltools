# turn: flip (and later rotate and scale) without blur.
# Copyright (C) 2026 the pixeltools contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY; see the GNU General Public
# License for details: <https://www.gnu.org/licenses/>.
import numpy as np

from . import core

NAME = "turn"
SUMMARY = "flip a sprite left-right or top-bottom, exactly (rotate and scale come next)"
EXAMPLE = "Example:  python sprite.py turn hero.png --flip h     (writes hero_turn.png, mirrored left-right)"


def describe(rec: dict) -> str:
    return f"turned; {rec['pixels_changed']} pixels differ from the original."


def apply(img: np.ndarray, opts: dict):
    flip = opts.get("flip")
    out = img
    if flip == "h":
        out = out[:, ::-1]
    elif flip == "v":
        out = out[::-1, :]
    elif flip is not None:
        raise ValueError(f"--flip must be h or v, not {flip}.")
    out = np.ascontiguousarray(out)
    return out, {"pixels_changed": core.changed_pixels(img, out)}

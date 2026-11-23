# The drawn pictures and the list of cases shared by the tests (and by the browser parity test).
# Copyright (C) 2026 the pixeltools contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY; see the GNU General Public
# License for details: <https://www.gnu.org/licenses/>.
"""Add every tool's option sets to CASES. tests/make_parity.py runs them in Python; tests/parity.js runs them in the
browser core and compares every pixel."""
import numpy as np


def rng(seed):
    return np.random.default_rng(seed)


def solid(w, h, colour):
    a = np.zeros((h, w, 4), dtype=np.uint8)
    a[:] = colour
    return a


def rect(a, x0, y0, x1, y1, colour):
    a[y0:y1, x0:x1] = colour
    return a


def noisy(a, amount, seed):
    """Add up to +-amount of random noise to the colour channels (not the alpha)."""
    n = rng(seed).integers(-amount, amount + 1, a.shape[:2] + (3,))
    out = a.copy()
    out[..., :3] = np.clip(a[..., :3].astype(int) + n, 0, 255).astype(np.uint8)
    return out


def figure_on_sky(w=48, h=48, noise=5, seed=1):
    """A figure (red shirt, skin, dark trousers) on a vertical gradient sky, with noise. Returns the picture and a mask of the sky."""
    a = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        a[y, :] = (150 + y, 190 + y // 2, 220, 255)
    sky = np.ones((h, w), dtype=bool)
    for (x0, y0, x1, y1, c) in ((18, 8, 30, 18, (226, 178, 140, 255)), (16, 18, 32, 34, (200, 40, 40, 255)),
                                (10, 20, 16, 32, (226, 178, 140, 255)), (32, 20, 38, 32, (226, 178, 140, 255)),
                                (18, 34, 30, 46, (60, 70, 140, 255))):
        rect(a, x0, y0, x1, y1, c)
        sky[y0:y1, x0:x1] = False
    return noisy(a, noise, seed), sky


def stripes():
    """Four flat colours side by side, 4 wide each, 6 tall."""
    a = np.zeros((6, 16, 4), dtype=np.uint8)
    for i, c in enumerate(((255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 0, 255))):
        a[:, i * 4:(i + 1) * 4] = c
    return a


def with_transparency():
    a = solid(8, 8, (0, 0, 0, 0))
    rect(a, 2, 2, 6, 6, (200, 30, 30, 255))
    a[0, 0] = (9, 9, 9, 0)           # a transparent pixel with a different (hidden) colour
    return a


def pictures():
    sky, _ = figure_on_sky()
    return {"sky": sky, "stripes": stripes(), "alpha": with_transparency(), "tiny": solid(1, 1, (5, 6, 7, 255))}


CASES = [
    ("turn flip h", "turn", "sky", {"flip": "h"}),
    ("turn flip v", "turn", "sky", {"flip": "v"}),
    ("turn flip h on a transparent picture", "turn", "alpha", {"flip": "h"}),
    ("turn none", "turn", "stripes", {}),
    ("turn tiny", "turn", "tiny", {"flip": "v"}),
]

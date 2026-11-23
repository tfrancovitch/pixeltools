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


def jpeg_damage(a, quality=60):
    """Save as JPEG and read back: the blocky damage Midjourney downloads carry (alpha is dropped)."""
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(a[..., :3], "RGB").save(buf, format="JPEG", quality=quality)
    out = np.array(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"))
    return np.concatenate([out, np.full(out.shape[:2] + (1,), 255, dtype=np.uint8)], axis=-1)


def figure_on_sky(w=48, h=48, noise=5, seed=1):
    """A figure (red shirt, skin, dark trousers) on a vertical gradient sky, with noise. Returns the picture and a mask of the sky."""
    a = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        a[y, :] = (150 + y * 60 // h, 190 + y * 30 // h, 220, 255)
    sky = np.ones((h, w), dtype=bool)
    sx, sy = w / 48, h / 48
    for (x0, y0, x1, y1, c) in ((18, 8, 30, 18, (226, 178, 140, 255)), (16, 18, 32, 34, (200, 40, 40, 255)),
                                (10, 20, 16, 32, (226, 178, 140, 255)), (32, 20, 38, 32, (226, 178, 140, 255)),
                                (18, 34, 30, 46, (60, 70, 140, 255))):
        X0, Y0, X1, Y1 = int(x0 * sx), int(y0 * sy), int(x1 * sx), int(y1 * sy)
        rect(a, X0, Y0, X1, Y1, c)
        sky[Y0:Y1, X0:X1] = False
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


def diagonal():
    """Two flat red cells that touch only at a corner, on blue."""
    a = solid(4, 4, (0, 0, 255, 255))
    a[1, 1] = a[2, 2] = (255, 0, 0, 255)
    return a


def ring_sprite():
    """A dark ring on a grey ground with a grey pocket inside (the pocket is enclosed, so background fill must keep it)."""
    a = solid(20, 20, (120, 120, 120, 255))
    rect(a, 4, 4, 16, 16, (30, 30, 30, 255))
    rect(a, 7, 7, 13, 13, (120, 120, 120, 255))
    return a


def pictures():
    sky, _ = figure_on_sky()
    big, _ = figure_on_sky(96, 96, 4, 3)
    return {"sky": sky, "stripes": stripes(), "alpha": with_transparency(), "tiny": solid(1, 1, (5, 6, 7, 255)),
            "jpeg": jpeg_damage(big, 60), "diagonal": diagonal(), "ring": ring_sprite()}


CASES = [
    ("turn flip h", "turn", "sky", {"flip": "h"}),
    ("turn flip v", "turn", "sky", {"flip": "v"}),
    ("turn flip h on a transparent picture", "turn", "alpha", {"flip": "h"}),
    ("turn none", "turn", "stripes", {}),
    ("turn tiny", "turn", "tiny", {"flip": "v"}),
]
CASES += [
    ("fill connected", "fill", "sky", {"at": [2, 2], "colour": [255, 0, 255, 255]}),
    ("fill low tolerance", "fill", "sky", {"at": [2, 2], "colour": [255, 0, 255, 255], "tolerance": 2}),
    ("fill everywhere", "fill", "stripes", {"at": [1, 1], "colour": [9, 9, 9, 255], "everywhere": True, "tolerance": 100}),
    ("fill corners off", "fill", "diagonal", {"at": [1, 1], "colour": [0, 255, 0, 255]}),
    ("fill corners on", "fill", "diagonal", {"at": [1, 1], "colour": [0, 255, 0, 255], "corners": True}),
    ("fill with transparent by default", "fill", "alpha", {"at": [3, 3]}),
    ("fill transparent area", "fill", "alpha", {"at": [0, 0], "colour": [1, 2, 3, 255]}),
    ("fill background of the sky", "fill", "sky", {"background": True}),
    ("fill background of a damaged picture", "fill", "jpeg", {"background": True, "colour": [255, 255, 255, 0]}),
    ("fill background keeps an enclosed pocket", "fill", "ring", {"background": True, "colour": [0, 0, 0, 0]}),
    ("fill background with corners", "fill", "ring", {"background": True, "corners": True, "tolerance": 5}),
    ("fill without a point is refused", "fill", "sky", {}),
    ("fill point outside is refused", "fill", "sky", {"at": [99, 0]}),
    ("fill background and point is refused", "fill", "sky", {"at": [1, 1], "background": True}),
    ("fill background of one pixel", "fill", "tiny", {"background": True, "colour": [1, 1, 1, 255]}),
]

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
    dmg, _ = damaged(character_rgba())
    return {"character": character_rgba(), "damaged": dmg, "sky": sky, "stripes": stripes(), "alpha": with_transparency(), "tiny": solid(1, 1, (5, 6, 7, 255)),
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


# ---- a drawn pixel-art character, for the flatten gate ----------------------------------
PAL = {"ground": (120, 170, 110), "outline": (30, 24, 40), "skin": (232, 180, 140), "shirt": (200, 44, 48),
       "shirt_dark": (140, 28, 36), "trousers": (52, 74, 150), "hair": (110, 80, 40), "white": (245, 245, 245), "pupil": (10, 10, 120),
       "highlight": (255, 230, 120), "boots": (60, 130, 90)}


def pixel_character(w=40, h=48):
    """A flat pixel-art character (true size, no noise): outline, skin, hair, eyes with pupils, a shirt with a shaded side
    and a highlight, trousers and boots on a plain ground. Returns an RGB array (h, w, 3) uint8."""
    a = np.zeros((h, w, 3), dtype=np.uint8)
    a[:] = PAL["ground"]

    def box(x0, y0, x1, y1, c):
        a[y0:y1, x0:x1] = PAL[c]
    box(13, 3, 27, 19, "outline")                       # head with an outline
    box(14, 4, 26, 18, "skin")
    box(14, 4, 26, 8, "hair")
    box(16, 11, 19, 14, "white"); box(21, 11, 24, 14, "white")      # eyes
    box(17, 12, 18, 14, "pupil"); box(22, 12, 23, 14, "pupil")     # pupils
    box(11, 19, 29, 35, "outline")                      # body with an outline
    box(12, 20, 28, 34, "shirt")
    box(22, 20, 28, 34, "shirt_dark")
    box(14, 22, 16, 24, "highlight")
    box(8, 21, 11, 33, "outline"); box(9, 22, 11, 32, "skin")      # arms
    box(29, 21, 32, 33, "outline"); box(29, 22, 31, 32, "skin")
    box(12, 35, 28, 45, "outline"); box(13, 35, 27, 44, "trousers")
    box(19, 38, 21, 45, "outline")
    box(12, 44, 20, 47, "boots"); box(20, 44, 28, 47, "boots")
    return a


def character_rgba():
    sp = pixel_character()
    return np.concatenate([sp, np.full(sp.shape[:2] + (1,), 255, np.uint8)], axis=-1)


def damaged(orig, noise=6, blend_share=0.5, specks=0.004, seed=11):
    """A flat sprite the way a rough AI picture leaves it after snapping: noise on every pixel, the pixels on an edge
    often a mix of the two areas (mostly their own colour), and a few lone stray pixels inside flat areas.
    Returns the damaged picture and the number of stray pixels added."""
    r = rng(seed)
    h, w = orig.shape[:2]
    out = orig.astype(np.int32).copy()
    o = orig.astype(np.int32)
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            for (a, b) in (((y - 1, x), (y + 1, x)), ((y, x - 1), (y, x + 1))):
                na, nb = o[a], o[b]
                if (na != nb).any() and (o[y, x] == na).all() != (o[y, x] == nb).all() and r.random() < blend_share:
                    mine, other = (na, nb) if (o[y, x] == na).all() else (nb, na)
                    t = r.uniform(0.6, 0.85)                       # the share of the pixel's own colour that is left
                    out[y, x] = np.round(t * mine + (1 - t) * other)
                    break
    flat_spot = np.zeros((h, w), dtype=bool)
    for y in range(2, h - 2):
        for x in range(2, w - 2):
            flat_spot[y, x] = (o[y - 2:y + 3, x - 2:x + 3] == o[y, x]).all()
    ys, xs = np.nonzero(flat_spot)
    pick = r.choice(len(ys), size=min(len(ys), max(1, int(specks * h * w))), replace=False)
    for k in pick:
        out[ys[k], xs[k], :3] = np.clip(out[ys[k], xs[k], :3] + r.choice([-30, 30], size=3), 0, 255)
    out[..., :3] = np.clip(out[..., :3] + r.integers(-noise, noise + 1, (h, w, 3)), 0, 255)
    return out.astype(np.uint8), len(pick)


CASES += [
    ("flatten everything", "flatten", "damaged", {}),
    ("flatten merge only", "flatten", "damaged", {"edges": False, "min_speck": 0}),
    ("flatten edges only", "flatten", "damaged", {"merge": False, "min_speck": 0}),
    ("flatten specks only", "flatten", "damaged", {"merge": False, "edges": False, "min_speck": 2}),
    ("flatten bigger specks", "flatten", "damaged", {"min_speck": 5, "tolerance": 9}),
    ("flatten one area", "flatten", "damaged", {"at": [20, 26]}),
    ("flatten one area, merge only", "flatten", "damaged", {"at": [20, 26], "edges": False, "min_speck": 0}),
    ("flatten a noisy sky", "flatten", "sky", {}),
    ("flatten a clean picture changes nothing", "flatten", "character", {}),
    ("flatten a transparent picture", "flatten", "alpha", {}),
    ("flatten a damaged jpeg", "flatten", "jpeg", {"tolerance": 8}),
    ("flatten point outside is refused", "flatten", "sky", {"at": [99, 99]}),
    ("flatten one pixel", "flatten", "tiny", {}),
]

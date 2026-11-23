# Shared helpers for the Sprite Tools: reading and writing pictures, colours, distance, connected areas.
# Copyright (C) 2026 the pixeltools contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY; see the GNU General Public
# License for details: <https://www.gnu.org/licenses/>.
"""A picture is a numpy array (height, width, 4) of 8-bit RGBA. Nothing here smooths or resamples.

Colour difference is the straight-line distance in RGBA. Tolerance is a percentage: the cut-off is
tolerance / 100 * 510. Fully transparent pixels count as one colour whatever their RGB.
"""
from __future__ import annotations

import re

import numpy as np
from PIL import Image

from . import tuning as T


# ---------------------------------------------------------------- pictures
def read_image(path) -> np.ndarray:
    with Image.open(path) as im:
        return np.array(im.convert("RGBA"), dtype=np.uint8)


def write_png(path, img: np.ndarray) -> None:
    Image.fromarray(img, "RGBA").save(path, format="PNG")


def normalise(img: np.ndarray) -> np.ndarray:
    """A copy in which every fully transparent pixel is (0, 0, 0, 0)."""
    out = img.copy()
    out[img[..., 3] == 0] = 0
    return out


def pack(img: np.ndarray) -> np.ndarray:
    """Each pixel as one number (r<<24 | g<<16 | b<<8 | a), as uint32 (h, w)."""
    p = img.astype(np.uint32)
    return (p[..., 0] << 24) | (p[..., 1] << 16) | (p[..., 2] << 8) | p[..., 3]


def unpack(values) -> np.ndarray:
    v = np.asarray(values, dtype=np.uint32)
    return np.stack([(v >> 24) & 255, (v >> 16) & 255, (v >> 8) & 255, v & 255], axis=-1).astype(np.uint8)


def count_colours(img: np.ndarray) -> int:
    return int(len(np.unique(pack(normalise(img)))))


# ---------------------------------------------------------------- colours and points
def parse_colour(text: str) -> tuple[int, int, int, int]:
    """#rrggbb, #rrggbbaa, or r,g,b[,a] (0 to 255)."""
    s = text.strip()
    if s.startswith("#"):
        h = s[1:]
        if re.fullmatch(r"[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", h):
            v = [int(h[i:i + 2], 16) for i in range(0, len(h), 2)]
            return (v[0], v[1], v[2], v[3] if len(v) == 4 else 255)
    else:
        parts = [p.strip() for p in s.split(",")]
        if len(parts) in (3, 4) and all(re.fullmatch(r"\d{1,3}", p) and int(p) <= 255 for p in parts):
            v = [int(p) for p in parts]
            return (v[0], v[1], v[2], v[3] if len(v) == 4 else 255)
    raise ValueError(f"'{text}' is not a colour. Write #rrggbb, #rrggbbaa, or r,g,b (0 to 255), for example #ff0000 or 255,0,0.")


def parse_point(text: str) -> tuple[int, int]:
    m = re.fullmatch(r"\s*(\d+)\s*,\s*(\d+)\s*", text)
    if not m:
        raise ValueError(f"'{text}' is not a point. Write x,y in pixels from the top-left, for example 12,40.")
    return int(m.group(1)), int(m.group(2))


def clean_colour(c) -> tuple[int, int, int, int]:
    """A colour tuple with the transparent colour made canonical."""
    c = tuple(int(v) for v in c)
    return (0, 0, 0, 0) if c[3] == 0 else c


def check_point(img: np.ndarray, at) -> tuple[int, int]:
    x, y = int(at[0]), int(at[1])
    h, w = img.shape[:2]
    if not (0 <= x < w and 0 <= y < h):
        raise ValueError(f"The point {x},{y} is outside the picture, which is {w} by {h} pixels (x from 0 to {w - 1}, y from 0 to {h - 1}).")
    return x, y


# ---------------------------------------------------------------- distance
def cutoff_sq(tolerance: float) -> float:
    """The squared cut-off distance for a tolerance in percent."""
    if not (0 <= tolerance <= 100):
        raise ValueError(f"The tolerance must be between 0 and 100 (percent), not {tolerance}.")
    cut = tolerance * T.MAX_DISTANCE / 100
    return cut * cut


def dist2(img_i32: np.ndarray, colour) -> np.ndarray:
    """Squared distance of every pixel of a normalised int32 picture to one colour."""
    diff = img_i32 - np.asarray(colour, dtype=np.int32)
    return (diff * diff).sum(axis=-1)


# ---------------------------------------------------------------- connected areas
def grow(h: int, w: int, seeds: np.ndarray, edge_ok, corners: bool = False) -> np.ndarray:
    """Everything reachable from the seed pixels (flat indices) by stepping to a touching pixel q
    from a reached pixel p whenever edge_ok(p, q) (arrays of flat indices) is true. Returns a flat
    boolean mask. The answer does not depend on the order of the search."""
    reached = np.zeros(h * w, dtype=bool)
    seeds = np.unique(np.asarray(seeds, dtype=np.int64))
    reached[seeds] = True
    frontier = seeds
    steps = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if corners:
        steps += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    while frontier.size:
        y, x = np.divmod(frontier, w)
        found = []
        for dy, dx in steps:
            ny, nx = y + dy, x + dx
            inside = (ny >= 0) & (ny < h) & (nx >= 0) & (nx < w)
            p = frontier[inside]
            q = ny[inside] * w + nx[inside]
            fresh = ~reached[q]
            p, q = p[fresh], q[fresh]
            if q.size:
                q = q[edge_ok(p, q)]
                reached[q] = True
                found.append(q)
        frontier = np.unique(np.concatenate(found)) if found else np.empty(0, dtype=np.int64)
    return reached


def changed_pixels(before: np.ndarray, after: np.ndarray) -> int:
    return int((normalise(before) != normalise(after)).any(axis=-1).sum())

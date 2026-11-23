# flatten: the opposite of dithering. Even colours, sharp edges. (Plan section 6: three passes, each switchable.)
# Copyright (C) 2026 the pixeltools contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY; see the GNU General Public
# License for details: <https://www.gnu.org/licenses/>.
"""Pass 1 merges near colours, pass 2 gives the in-between pixels on an edge to the nearer side, pass 3 absorbs
lone stray pixels. Every decision in a pass is made on the picture as it was when the pass started, so the answer
does not depend on the order pixels are visited. The browser version (web/core.js) follows these steps exactly."""
from math import isqrt

import numpy as np

from . import core
from . import tuning as T

NAME = "flatten"
SUMMARY = "make areas one even colour and the edges between them sharp (the opposite of dithering)"
EXAMPLE = ("Examples:\n"
           "  python sprite.py flatten sprite.png                      (the whole picture)\n"
           "  python sprite.py flatten sprite.png --at 30,28           (only the red shirt around 30,28, and its edges)\n"
           "  python sprite.py flatten sprite.png --no-edges --min-speck 0 --tolerance 8     (only pass 1)")

DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]   # the order matters (ties go to the earlier)
OPPOSITE = [(1, 6), (3, 4)]   # a blend is squeezed between two areas: up and down, or left and right (diagonals would cut real corners)


def describe(rec: dict) -> str:
    return (f"flattened: {rec['colours_before']} colours became {rec['colours_after']}. "
            f"Pass 1 (merge) changed {rec['pass1_pixels']} pixels, pass 2 (edges) {rec['pass2_pixels']}, pass 3 (specks) {rec['pass3_pixels']}.")


def packed(flat: np.ndarray) -> np.ndarray:
    f = flat.astype(np.int64)
    return (f[:, 0] << 24) | (f[:, 1] << 16) | (f[:, 2] << 8) | f[:, 3]


# ---------------------------------------------------------------- pass 1
def merge_all(flat: np.ndarray, cut2: float) -> np.ndarray:
    """Leader clustering: colours in order of use (ties: smaller colour number first); a colour within the
    cut-off of an earlier leader joins the nearest one, otherwise it becomes a leader."""
    pk = packed(flat)
    colours, inverse, counts = np.unique(pk, return_inverse=True, return_counts=True)
    order = np.lexsort((colours, -counts))                        # most used first, ties by colour number
    rgba = np.stack([(colours >> 24) & 255, (colours >> 16) & 255, (colours >> 8) & 255, colours & 255], axis=1).astype(np.int64)
    leaders: list[int] = []
    target = np.zeros(len(colours), dtype=np.int64)
    for k in order:
        if leaders:
            d = ((rgba[leaders] - rgba[k]) ** 2).sum(axis=1)
            j = int(np.argmin(d))                                  # the first of equally near leaders
            if d[j] <= cut2:
                target[k] = leaders[j]
                continue
        leaders.append(int(k))
        target[k] = k
    return rgba[target][inverse.reshape(-1)].astype(np.int32)


# ---------------------------------------------------------------- pass 2
def neighbour_stack(pk: np.ndarray, h: int, w: int) -> np.ndarray:
    """(8, h, w): the packed colour of each neighbour, -1 off the edge."""
    pad = np.full((h + 2, w + 2), -1, dtype=np.int64)
    pad[1:-1, 1:-1] = pk
    return np.stack([pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w] for dy, dx in DIRS])


def unpack_arr(v: np.ndarray) -> np.ndarray:
    return np.stack([(v >> 24) & 255, (v >> 16) & 255, (v >> 8) & 255, v & 255], axis=-1).astype(np.int64)


def edge_round(flat: np.ndarray, h: int, w: int, cut2: float, change_ok: np.ndarray) -> np.ndarray:
    pk = packed(flat).reshape(h, w)
    nb = neighbour_stack(pk, h, w)
    differs = (nb != pk) & (nb >= 0)
    cand = differs.any(axis=0) & change_ok.reshape(h, w)
    ys, xs = np.nonzero(cand)
    out = flat.copy()
    if len(ys) == 0:
        return out
    c = unpack_arr(pk[ys, xs])
    nbc = nb[:, ys, xs]                                            # (8, K)
    lim = cut2 * T.FLATTEN_EDGE_LINE * T.FLATTEN_EDGE_LINE
    best = np.full(len(ys), np.inf)
    pick = c[:, 0] * 0 - 1                                         # chosen colour number, -1: none
    for i, j in OPPOSITE:
        ok = (nbc[i] >= 0) & (nbc[j] >= 0) & (nbc[i] != nbc[j]) & (nbc[i] != pk[ys, xs]) & (nbc[j] != pk[ys, xs])
        if not ok.any():
            continue
        a = unpack_arr(np.where(ok, nbc[i], 0))
        b = unpack_arr(np.where(ok, nbc[j], 0))
        ab, ac = b - a, c - a
        len2 = (ab * ab).sum(axis=1)
        dot = (ac * ab).sum(axis=1)
        perp = (ac * ac).sum(axis=1) * len2 - dot * dot          # exact integers
        between = ok & (dot > 0) & (dot < len2)
        line = between & (perp <= lim * len2)
        score = np.where(line, perp / np.where(len2 == 0, 1, len2), np.inf)
        better = line & (score < best)
        if better.any():
            twice = 2 * dot
            to_a = (twice < len2) | ((twice == len2) & (nbc[i] < nbc[j]))
            chosen = np.where(to_a, nbc[i], nbc[j])
            pick = np.where(better, chosen, pick)
            best = np.where(better, score, best)
    hit = pick >= 0
    out[(ys[hit] * w + xs[hit])] = unpack_arr(pick[hit]).astype(np.int32)
    return out


# ---------------------------------------------------------------- pass 3
def small_components(pk: np.ndarray, limit: int):
    """Connected (side by side) patches of one colour with at most `limit` pixels: list of lists of (y, x)."""
    h, w = pk.shape
    k = isqrt(limit) + 1                                           # a k by k block has more than `limit` pixels
    big = np.zeros((h, w), dtype=bool)
    if h >= k and w >= k:
        ok = np.ones((h - k + 1, w - k + 1), dtype=bool)
        base = pk[:h - k + 1, :w - k + 1]
        for dy in range(k):
            for dx in range(k):
                ok &= pk[dy:dy + h - k + 1, dx:dx + w - k + 1] == base
        for dy in range(k):
            for dx in range(k):
                big[dy:dy + h - k + 1, dx:dx + w - k + 1] |= ok
    seen = big.copy()
    found = []
    for y0, x0 in zip(*np.nonzero(~big)):
        if seen[y0, x0]:
            continue
        colour = pk[y0, x0]
        cells, stack, local = [], [(y0, x0)], {(y0, x0)}
        too_big = False
        while stack:
            y, x = stack.pop()
            cells.append((y, x))
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in local and pk[ny, nx] == colour:
                    if big[ny, nx]:
                        too_big = True
                    local.add((ny, nx))
                    stack.append((ny, nx))
            if len(local) > limit or too_big:
                too_big = True
                break
        if too_big:
            for cell in local:
                seen[cell] = True        # not a speck (these pixels are not started again)
            seen[y0, x0] = True
        else:
            for cell in cells:
                seen[cell] = True
            found.append(cells)
    return found


def speck_pass(flat: np.ndarray, h: int, w: int, limit: int, reach2: float, change_ok: np.ndarray) -> np.ndarray:
    pk = packed(flat).reshape(h, w)
    out = flat.copy()
    for cells in small_components(pk, limit):
        inside = set(cells)
        around = set()
        for y, x in cells:
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in inside:
                    around.add(int(pk[ny, nx]))
        if len(around) != 1 or not all(change_ok[y * w + x] for y, x in cells):
            continue
        target = around.pop()
        t = unpack_arr(np.array([target]))[0]
        s = flat[cells[0][0] * w + cells[0][1]].astype(np.int64)
        if ((t - s) ** 2).sum() <= reach2:
            for y, x in cells:
                out[y * w + x] = t
    return out


# ---------------------------------------------------------------- the tool
def apply(img: np.ndarray, opts: dict):
    h, w = img.shape[:2]
    tol = opts.get("tolerance")
    tol = T.FLATTEN_TOLERANCE if tol is None else float(tol)
    cut2 = core.cutoff_sq(tol)
    do_merge = opts.get("merge", True) is not False
    do_edges = opts.get("edges", True) is not False
    limit = opts.get("min_speck")
    limit = T.FLATTEN_MIN_SPECK if limit is None else int(limit)
    if limit < 0:
        raise ValueError("--min-speck must be 0 or more (0 skips the speck pass).")
    at = opts.get("at")
    flat = core.normalise(img).astype(np.int32).reshape(-1, 4)
    start = flat.copy()
    n = h * w
    region = None
    change_ok = np.ones(n, dtype=bool)
    if at is not None:
        x, y = core.check_point(img, at)
        seed = y * w + x
        cand = ((flat - flat[seed]) ** 2).sum(axis=1) <= cut2
        region = core.grow(h, w, np.array([seed]), lambda p, q: cand[q], False)
        pad = np.zeros((h + 2, w + 2), dtype=bool)
        pad[1:-1, 1:-1] = region.reshape(h, w)
        near = np.zeros((h, w), dtype=bool)
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                near |= pad[dy:dy + h, dx:dx + w]
        change_ok = near.ravel()
    # pass 1
    if do_merge:
        if region is None:
            flat = merge_all(flat, cut2)
        else:
            ids = packed(flat[region])
            values, counts = np.unique(ids, return_counts=True)
            mode = values[np.lexsort((values, -counts))[0]]
            flat = flat.copy()
            flat[region] = unpack_arr(np.array([mode]))[0].astype(np.int32)
    p1 = int((flat != start).any(axis=1).sum())
    # pass 2
    p2 = 0
    if do_edges:
        for _ in range(T.FLATTEN_EDGE_ROUNDS):
            new = edge_round(flat, h, w, cut2, change_ok)
            moved = int((new != flat).any(axis=1).sum())
            flat = new
            p2 += moved
            if moved == 0:
                break
    # pass 3
    before3 = flat.copy()
    if limit > 0:
        flat = speck_pass(flat, h, w, limit, core.cutoff_sq(T.FLATTEN_SPECK_REACH), change_ok)
    p3 = int((flat != before3).any(axis=1).sum())
    out = flat.reshape(h, w, 4).astype(np.uint8)
    return out, {"pixels_changed": core.changed_pixels(img, out), "pass1_pixels": p1, "pass2_pixels": p2, "pass3_pixels": p3}

# replace: change one colour (and everything close to it) into another, or swap a whole palette.
# Copyright (C) 2026 the pixeltools contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY; see the GNU General Public
# License for details: <https://www.gnu.org/licenses/>.
import numpy as np

from . import core
from . import tuning as T

NAME = "replace"
SUMMARY = "change one colour (and everything close to it) into another, or swap a whole palette with --map"
EXAMPLE = ("Examples:\n"
           "  python sprite.py replace sprite.png --from '#c83030' --to '#3070c8'\n"
           "  python sprite.py replace sprite.png --at 30,28 --to 0,200,0 --tolerance 12 --connected     (only the area around 30,28)\n"
           "  python sprite.py replace sprite.png --map swap.txt          (a palette swap; one pair per line, like: #c83030 #3070c8)")


def describe(rec: dict) -> str:
    extra = f" ({rec['pairs_used']} of {rec['pairs']} colour pairs matched)" if "pairs" in rec else ""
    if rec["pixels_replaced"] == 0:
        return "nothing matched, so nothing was changed" + extra + "."
    return f"replaced {rec['pixels_replaced']} pixels{extra}; {rec['pixels_changed']} actually changed."


def parse_map(text: str):
    """One pair per line: two colours separated by spaces or ->. Lines that are empty or start with ; or // are ignored."""
    pairs = []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(";") or line.startswith("//"):
            continue
        parts = [p.strip() for p in line.replace("=>", "->").split("->")] if ("->" in line or "=>" in line) else line.split()
        if len(parts) != 2:
            raise ValueError(f"Line {n} of the map is not a pair of colours: '{line}'. Write one pair per line, like #aabbcc #112233.")
        try:
            pairs.append((core.parse_colour(parts[0]), core.parse_colour(parts[1])))
        except ValueError as e:
            raise ValueError(f"Line {n} of the map: {e}") from None
    if not pairs:
        raise ValueError("The map has no colour pairs. Write one pair per line, like #aabbcc #112233.")
    return pairs


def read_map(path) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def apply(img: np.ndarray, opts: dict):
    h, w = img.shape[:2]
    tol = opts.get("tolerance")
    tol = T.REPLACE_TOLERANCE if tol is None else float(tol)
    cut2 = core.cutoff_sq(tol)
    flat = core.normalise(img).astype(np.int32).reshape(-1, 4)
    out = img.copy().reshape(-1, 4)
    extra = {}
    map_text = opts.get("map_text")
    pairs = opts.get("map")
    if map_text is not None:
        pairs = parse_map(map_text)
    if pairs is not None:
        if any(opts.get(k) for k in ("from", "to", "at", "connected")):
            raise ValueError("--map already says what to change into what; do not combine it with --from, --to, --at or --connected.")
        if not len(pairs):
            raise ValueError("The map has no colour pairs. Write one pair per line, like #aabbcc #112233.")
        froms = np.array([core.clean_colour(p[0]) for p in pairs], dtype=np.int32)
        tos = np.array([core.clean_colour(p[1]) for p in pairs], dtype=np.int32)
        dist = ((flat[:, None, :] - froms[None, :, :]) ** 2).sum(axis=2)       # (pixels, pairs)
        best = dist.argmin(axis=1)                                             # the first of equally near pairs
        hit = dist[np.arange(len(flat)), best] <= cut2
        out[hit] = tos[best[hit]]
        mask = hit
        extra = {"pairs": len(pairs), "pairs_used": int(len(np.unique(best[hit])))}
    else:
        to = opts.get("to")
        if to is None:
            raise ValueError("Say what to change it into: --to COLOUR.")
        src, at = opts.get("from"), opts.get("at")
        if src is not None and at is not None:
            raise ValueError("Use either --from (a colour) or --at (a point to take the colour from), not both.")
        if src is None and at is None:
            raise ValueError("Say which colour to change: --from COLOUR, or --at x,y to take it from the picture.")
        if opts.get("connected") and at is None:
            raise ValueError("--connected needs --at (the area around that point).")
        if at is not None:
            x, y = core.check_point(img, at)
            ref = flat[y * w + x]
        else:
            ref = np.array(core.clean_colour(src), dtype=np.int32)
        cand = ((flat - ref) ** 2).sum(axis=1) <= cut2
        mask = core.grow(h, w, np.array([y * w + x]), lambda p, q: cand[q], bool(opts.get("corners"))) if opts.get("connected") else cand
        out[mask] = core.clean_colour(to)
    result = out.reshape(h, w, 4)
    return result, dict({"pixels_replaced": int(mask.sum()), "pixels_changed": core.changed_pixels(img, result)}, **extra)

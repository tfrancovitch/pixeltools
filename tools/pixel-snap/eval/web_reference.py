#!/usr/bin/env python3
# Make the Python side of the browser-parity check: key results for every picture in a folder, as JSON.
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
"""    python eval/web_reference.py <image folder> <out.json>

Then:  node eval/web_parity.js <image folder> <out.json>   compares the browser version against it."""
import json
import sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import pixel_snap  # noqa: E402


def summarise(res) -> dict:
    sh = res.shadow
    return {
        "grid": res.grid_status, "px": round(res.px, 3), "py": round(res.py, 3), "w": res.size[0], "h": res.size[1],
        "flat": None if res.flatness is None else round(res.flatness, 4), "colours": res.colours,
        "framing": res.framing.kind, "border": round(res.framing.border_uniform, 3), "share": round(res.framing.subject_share, 3),
        "subject": res.subject.kind, "view": res.view.kind, "diag": round(res.view.diagonal, 3),
        "horiz": round(res.view.horizontal, 3), "vert": round(res.view.vertical, 3), "weaker": round(res.view.weaker_diagonal, 3),
        "shadow": "unsure" if sh.unsure else ("found" if sh.found else "none"), "shadow_kind": sh.kind if sh.found else "",
        "shadow_share": round(sh.share, 3) if sh.found else 0, "shadow_dx": round(sh.dx, 3) if sh.found else 0,
        "facing": res.facing.kind, "clues": res.facing.clues,
    }


def work(path):
    a = np.array(Image.open(path).convert("RGBA"))
    an = pixel_snap.analyse(a)
    out = summarise(pixel_snap.rebuild(a, an))
    r = pixel_snap.rebuild(a, an, shadows="remove-all", transparent=True)
    out["removed_all"] = r.shadow_removed
    out["transparent"] = bool(r.transparent)
    out["colours_16"] = pixel_snap.rebuild(a, an, colours=16).colours
    return path.name, out


if __name__ == "__main__":
    files = sorted(Path(sys.argv[1]).glob("*.png")) + sorted(Path(sys.argv[1]).glob("*.jpg"))
    with Pool(4) as pool:
        data = dict(pool.map(work, files))
    Path(sys.argv[2]).write_text(json.dumps(data, indent=1), encoding="utf-8")
    print("wrote", len(data), "pictures to", sys.argv[2])

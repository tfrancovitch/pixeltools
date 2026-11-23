#!/usr/bin/env python3
# Run every case in tests/cases.py in Python and write the pictures and answers as JSON for tests/parity.js.
# Copyright (C) 2026 the pixeltools contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY; see the GNU General Public
# License for details: <https://www.gnu.org/licenses/>.
"""    python tests/make_parity.py OUT.json"""
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cases  # noqa: E402
import sprite  # noqa: E402
from spritetools import core  # noqa: E402


def b64(a):
    return base64.b64encode(core.normalise(a).tobytes()).decode()


def jsonable(v):
    if isinstance(v, dict):
        return {k: jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v]
    return v


def main(out_path):
    pics = cases.pictures()
    data = []
    for name, tool, pic, opts in cases.CASES:
        img = pics[pic]
        try:
            out, info = sprite.MODULES[tool].apply(img, opts)
            info = dict(info, colours_before=core.count_colours(img), colours_after=core.count_colours(out))
            data.append({"name": name, "tool": tool, "w": int(img.shape[1]), "h": int(img.shape[0]), "input": b64(img), "opts": jsonable(opts),
                         "expected": b64(out), "ow": int(out.shape[1]), "oh": int(out.shape[0]), "info": info})
        except ValueError as e:
            data.append({"name": name, "tool": tool, "w": int(img.shape[1]), "h": int(img.shape[0]), "input": b64(img), "opts": jsonable(opts), "error": str(e)})
    Path(out_path).write_text(json.dumps(data), encoding="utf-8")
    print("wrote", len(data), "cases to", out_path)


if __name__ == "__main__":
    main(sys.argv[1])

#!/usr/bin/env python3
# sprite.py: the command for the Sprite Tools (small exact tools for pixel-art sprites).
# Copyright (C) 2026 the pixeltools contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY; see the GNU General Public
# License for details: <https://www.gnu.org/licenses/>.
"""    python sprite.py --list
    python sprite.py turn hero.png --flip h                 # writes hero_turn.png
    python sprite.py <tool> INPUT... [-o OUT.png | --out-dir DIR] [tool options] [--json] [--brief] [--jobs N]

Needs Python 3.9+, numpy and Pillow. No network, no AI. Exit code 0: all worked; 1: a file could not be
read; 2: a tool could not do its job on some picture (the reason is printed)."""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spritetools import __version__, core, fill, flatten, replace, turn  # noqa: E402

MODULES = {m.NAME: m for m in (fill, flatten, replace, turn)}   # the order here is the order of --list


# ---------------------------------------------------------------- options, per tool
def add_tool_options(name: str, p: argparse.ArgumentParser) -> None:
    if name == "turn":
        p.add_argument("--flip", choices=["h", "v"], help="h: mirror left-right; v: mirror top-bottom")
    elif name == "fill":
        p.add_argument("--at", metavar="X,Y", help="start here (pixels from the top-left, from 0)")
        p.add_argument("--colour", "--color", metavar="COLOUR", default=None, help="paint with this colour: #rrggbb, #rrggbbaa or r,g,b[,a]. Default: transparent")
        p.add_argument("--tolerance", type=float, default=None, metavar="PCT", help="how close counts as the same colour, 0 to 100 (default: %g)" % fill.T.FILL_TOLERANCE)
        p.add_argument("--everywhere", action="store_true", help="fill every close pixel in the picture, not only the connected area")
        p.add_argument("--background", action="store_true", help="start from the border colour and fill the whole ground, however much it varies")
        p.add_argument("--corners", action="store_true", help="count corner-touching pixels as connected")
    elif name == "replace":
        p.add_argument("--from", dest="from_", metavar="COLOUR", help="the colour to change (with everything close to it)")
        p.add_argument("--at", metavar="X,Y", help="take the colour to change from this point")
        p.add_argument("--to", metavar="COLOUR", help="the new colour")
        p.add_argument("--tolerance", type=float, default=None, metavar="PCT", help="how close counts as the same colour (default: %g)" % replace.T.REPLACE_TOLERANCE)
        p.add_argument("--connected", action="store_true", help="only the area around --at, not the whole picture")
        p.add_argument("--corners", action="store_true", help="with --connected: count corner-touching pixels as connected")
        p.add_argument("--map", metavar="FILE", help="many from-to pairs at once (a palette swap); one pair per line: #aabbcc #112233")
    elif name == "flatten":
        p.add_argument("--tolerance", type=float, default=None, metavar="PCT", help="what counts as the same colour (default: %g)" % flatten.T.FLATTEN_TOLERANCE)
        p.add_argument("--at", metavar="X,Y", help="flatten only the area around this point (and its edges)")
        p.add_argument("--no-merge", action="store_true", help="skip pass 1 (merge near colours)")
        p.add_argument("--edges", dest="edges", action="store_true", default=True, help="pass 2: sharpen edges (default)")
        p.add_argument("--no-edges", dest="edges", action="store_false", help="skip pass 2 (sharpen edges)")
        p.add_argument("--min-speck", type=int, default=None, metavar="N", help="pass 3: absorb lone patches up to N pixels, 0 to skip (default: %d)" % flatten.T.FLATTEN_MIN_SPECK)


def opts_from_args(name: str, a: argparse.Namespace) -> dict:
    if name == "turn":
        return {"flip": a.flip}
    if name == "fill":
        return {"at": core.parse_point(a.at) if a.at else None, "colour": core.parse_colour(a.colour) if a.colour else None,
                "tolerance": a.tolerance, "everywhere": a.everywhere, "background": a.background, "corners": a.corners}
    if name == "replace":
        text = replace.read_map(a.map) if a.map else None
        return {"from": core.parse_colour(a.from_) if a.from_ else None, "at": core.parse_point(a.at) if a.at else None,
                "to": core.parse_colour(a.to) if a.to else None, "tolerance": a.tolerance, "connected": a.connected,
                "corners": a.corners, "map_text": text}
    if name == "flatten":
        return {"tolerance": a.tolerance, "at": core.parse_point(a.at) if a.at else None, "merge": not a.no_merge,
                "edges": a.edges, "min_speck": a.min_speck}
    raise KeyError(name)


# ---------------------------------------------------------------- doing the work
def output_path(src: str, tool: str, args) -> str:
    if args.out and len(args.inputs) == 1:
        return args.out
    stem = Path(src).stem + "_" + tool + ".png"
    folder = args.out_dir or str(Path(src).parent)
    return str(Path(folder) / stem)


def work(job):
    """Runs in a worker process. Returns a dict describing what happened (never raises)."""
    src, dst, tool, opts = job
    rec = {"input": src, "output": None, "tool": tool}
    try:
        img = core.read_image(src)
    except Exception as e:  # noqa: BLE001
        rec.update(error="could not read the picture: " + str(e), kind="read")
        return rec
    rec["size"] = [int(img.shape[1]), int(img.shape[0])]
    try:
        before = core.count_colours(img)
        out, info = MODULES[tool].apply(img, opts)
        rec.update(info)
        rec["colours_before"], rec["colours_after"] = before, core.count_colours(out)
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        core.write_png(dst, out)
        rec["output"] = dst
        rec["size_after"] = [int(out.shape[1]), int(out.shape[0])]
    except ValueError as e:
        rec.update(error=str(e), kind="tool")
    return rec


def sentence(rec: dict) -> str:
    n = Path(rec["input"]).name
    if "error" in rec:
        return f"{n}: {rec['error']}"
    return f"{n}: {MODULES[rec['tool']].describe(rec)} Saved {rec['output']}."


def brief(rec: dict) -> str:
    n = Path(rec["input"]).name
    if "error" in rec:
        return f"{n}: FAILED, {rec['error']}"
    return f"{n} -> {Path(rec['output']).name}: {rec['pixels_changed']} changed, colours {rec['colours_before']} -> {rec['colours_after']}"


def main(argv=None) -> int:
    top = argparse.ArgumentParser(prog="sprite.py", description="Small, exact tools for pixel-art sprites. No AI, no network.",
                                  epilog="python sprite.py <tool> --help explains one tool.")
    top.add_argument("--list", action="store_true", help="list the tools, one line each")
    top.add_argument("--version", action="version", version="Sprite Tools " + __version__)
    sub = top.add_subparsers(dest="tool", metavar="<tool>")
    for name, mod in MODULES.items():
        p = sub.add_parser(name, help=mod.SUMMARY, description=mod.SUMMARY + "\n\n" + mod.EXAMPLE, formatter_class=argparse.RawDescriptionHelpFormatter)
        p.add_argument("inputs", nargs="+", metavar="INPUT", help="picture file(s); wildcards are fine")
        p.add_argument("-o", "--out", metavar="OUT.png", help="output file (one input only)")
        p.add_argument("--out-dir", metavar="DIR", help="folder for the outputs, named <name>_%s.png" % name)
        p.add_argument("--json", action="store_true", help="print one JSON object per picture")
        p.add_argument("--brief", action="store_true", help="print one short line per picture")
        p.add_argument("--jobs", type=int, default=1, metavar="N", help="pictures at once (0: one per core)")
        add_tool_options(name, p)
    args = top.parse_args(argv)
    if args.list:
        for name, mod in MODULES.items():
            print(f"{name:10} {mod.SUMMARY}")
        return 0
    if not args.tool:
        top.print_help()
        return 0
    files = []
    for pattern in args.inputs:
        hits = sorted(glob.glob(pattern)) if any(c in pattern for c in "*?[") else [pattern]
        files += hits or [pattern]
    args.inputs = files
    if args.out and len(files) != 1:
        print("-o works with exactly one input; use --out-dir for several.", file=sys.stderr)
        return 2
    try:
        opts = opts_from_args(args.tool, args)
    except (ValueError, OSError) as e:
        print("Problem with the options: " + str(e), file=sys.stderr)
        return 2
    jobs = [(f, output_path(f, args.tool, args), args.tool, opts) for f in files]
    n = args.jobs if args.jobs > 0 else (os.cpu_count() or 1)
    if n > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(max_workers=n) as pool:
            recs = list(pool.map(work, jobs))
    else:
        recs = [work(j) for j in jobs]
    code = 0
    for rec in recs:
        if "error" in rec:
            code = 1 if rec["kind"] == "read" else (code or 2)
            if rec["kind"] == "read":
                code = 1
        if args.json:
            print(json.dumps({k: v for k, v in rec.items() if k != "kind"}))
        elif args.brief:
            print(brief(rec))
        else:
            print(sentence(rec))
    return code


if __name__ == "__main__":
    sys.exit(main())

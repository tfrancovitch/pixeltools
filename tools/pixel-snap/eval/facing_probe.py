#!/usr/bin/env python3
# Reproduces the C2 stop-rule experiment: does any geometry-only rule find the clearly diagonal characters?
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
"""    python eval/facing_probe.py <image folder> <labels.csv>

Measures the geometric facing clues (facing.measure_clues) for every labelled character, prints how the
clues are distributed for clearly diagonal and clearly cardinal characters, then exhaustively searches single
clues and pairs of clues for a rule that finds at least 5 of the clearly diagonal characters while calling
at most 3 of the clearly cardinal ones diagonal (the plan's gate). On batch 1 no rule meets the gate.
Mind the arithmetic: thousands of candidate rules against six positives means a "good" rule is expected
by chance alone, so even a near miss proves nothing.
"""
import csv
import itertools
import sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import facing  # noqa: E402
import framing as F  # noqa: E402
import shadow as SH  # noqa: E402

CLUES = ["symmetry", "feet_apart", "feet_level", "torso_leg_shift", "head_off_torso"]


def measure(path):
    a = np.array(Image.open(path).convert("RGBA"))
    fr = F.classify_framing(a)
    if fr.kind != "isolated":
        return None
    return facing.measure_clues(fr, SH.find_shadow(a, fr)) or None


def main():
    folder, labels = Path(sys.argv[1]), Path(sys.argv[2])
    rows = [r for r in csv.DictReader(open(labels, encoding="utf-8")) if r["subject"] == "character" and r["facing"]]
    files = {p.name: p for p in folder.rglob("*.png")}
    with Pool(4) as pool:
        clues = pool.map(measure, [files[r["file"]] for r in rows])
    diag = [c for r, c in zip(rows, clues) if c and r["facing"] == "diagonal" and r["facing_clear"] == "y"]
    card = [c for r, c in zip(rows, clues) if c and r["facing"] == "cardinal" and r["facing_clear"] == "y"]
    print(f"clearly diagonal: {len(diag)}   clearly cardinal: {len(card)}   (gate: find >= 5 diagonal, call <= 3 cardinal diagonal)\n")
    val = lambda d, k: abs(d[k]) if k in ("torso_leg_shift", "head_off_torso") else d[k]
    for k in CLUES:
        for name, g in (("diagonal", diag), ("cardinal", card)):
            v = np.array([val(d, k) for d in g])
            print(f"  {k:16s} {name:9s} min {v.min():.2f}  median {np.median(v):.2f}  max {v.max():.2f}")
    results = []
    def rules():
        for k in CLUES:
            for t in sorted({round(val(d, k), 3) for d in diag + card}):
                for sign in (1, -1):
                    yield ((k, t, sign),)
        for a, b in itertools.combinations(CLUES, 2):
            for x in sorted({round(val(d, a), 2) for d in diag}):
                for y in sorted({round(val(d, b), 2) for d in diag}):
                    for sa, sb in itertools.product((1, -1), repeat=2):
                        yield ((a, x, sa), (b, y, sb))
    n = 0
    for r in rules():
        n += 1
        ok = lambda d: all((val(d, k) >= t) if s == 1 else (val(d, k) <= t) for k, t, s in r)
        results.append((sum(ok(d) for d in diag), sum(ok(d) for d in card), r))
    results.sort(key=lambda x: -(x[0] - 0.4 * x[1]))
    print(f"\nsearched {n} candidate rules. Best (found of {len(diag)}, false calls of {len(card)}):")
    for tp, fp, r in results[:5]:
        print(f"  {tp} found, {fp} false calls: {r}")
    print("rules meeting the gate:", sum(1 for tp, fp, _ in results if tp >= 5 and fp <= 3))


if __name__ == "__main__":
    main()

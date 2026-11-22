#!/usr/bin/env python3
# Scorecard: grade Pixel Snap against a labelled folder of real pictures.
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
"""Run Pixel Snap on every labelled picture and report how often each check is right.

    python eval/scorecard.py <image folder> <labels.csv> [--out eval/SCORECARD.md] [--jobs 4]

The labels file is a CSV with a `file` column and any of these columns (blank = not scored):

    view         iso | ort        buildings, objects, scenes: isometric or straight-on? (blank for characters)
    view_clear   y | n            was it a clear case?
    facing       diagonal | cardinal | mixed    characters only: turned to a diagonal, or straight (front, back, side)?
    facing_clear y | n            was it a clear case?
    subject      character | building | object | scene     (checked once the check exists)
    framing      isolated | subject_on_background | scene   (checked once the check exists)
    shadow       none | contact | cast          (checked once the check exists)

Pictures are read from the folder and never copied or changed. Only the report is saved.
A check answers "cant" when it declines to decide; that is counted separately from a wrong answer.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import pixel_snap  # noqa: E402
from PIL import Image  # noqa: E402

VIEW_NAMES = {"isometric": "iso", "orthogonal": "ort", "unclear": "cant"}


def run_one(path: str) -> dict:
    """The pipeline's answers for one picture. Add new checks here as slices land."""
    t0 = time.time()
    try:
        res = pixel_snap.snap_image(Image.open(path))
        return {
            "ok": True,
            "found": bool(res.found),
            "px": round(res.px, 2), "py": round(res.py, 2),
            "sprite_w": res.size[0], "sprite_h": res.size[1],
            "view": VIEW_NAMES[res.view.kind],
            "diag": round(res.view.diagonal, 3), "horiz": round(res.view.horizontal, 3),
            "vert": round(res.view.vertical, 3),
            "framing": "cant" if res.framing.kind == "unclear" else res.framing.kind,
            "border_plain": round(res.framing.border_uniform, 2), "subject_share": round(res.framing.subject_share, 2),
            "seconds": round(time.time() - t0, 1),
        }
    except Exception as exc:  # report it, keep going
        return {"ok": False, "error": str(exc)[:80], "found": False, "view": "cant", "framing": "cant", "seconds": round(time.time() - t0, 1)}


def find_images(folder: Path) -> dict[str, Path]:
    return {p.name: p for p in folder.rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")}


def table(c, classes, pred_classes) -> list[str]:
    """c counts (labelled, tool said); the tool may also say 'cant'."""
    head = "| labelled \\ tool said | " + " | ".join(pred_classes) + " | right | wrong | can't tell |"
    out = [head, "|" + "---|" * (len(pred_classes) + 4)]
    for t in classes:
        n = sum(c[(t, p)] for p in pred_classes)
        right, cant = c[(t, t)], c[(t, "cant")]
        out.append(f"| {t} (n={n}) | " + " | ".join(str(c[(t, p)]) for p in pred_classes) +
                   f" | {right} | {n - right - cant} | {cant} |")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", type=Path, help="folder with the pictures (searched recursively)")
    ap.add_argument("labels", type=Path, help="labels CSV")
    ap.add_argument("--out", type=Path, default=HERE / "SCORECARD.md", help="where to save the report")
    ap.add_argument("--jobs", type=int, default=4, help="pictures processed at once")
    args = ap.parse_args(argv)

    labels = list(csv.DictReader(open(args.labels, newline="", encoding="utf-8")))
    files = find_images(args.images)
    missing = [r["file"] for r in labels if r["file"] not in files]
    labels = [r for r in labels if r["file"] in files]
    t0 = time.time()
    with Pool(args.jobs) as pool:
        results = pool.map(run_one, [str(files[r["file"]]) for r in labels], chunksize=2)
    rows = [{"file": lab["file"], **res} for lab, res in zip(labels, results)]
    elapsed = time.time() - t0

    L = [f"# Pixel Snap scorecard", "",
         f"Labels: `{args.labels.name}` · pictures scored: {len(rows)} · run time: {elapsed:.0f} s",
         f"Code version: tuning.py as committed; see git log. Pictures are not stored in the repository.", ""]
    if missing:
        L += [f"**Labelled pictures not found in the folder ({len(missing)}):** " + ", ".join(missing[:10]) + (" ..." if len(missing) > 10 else ""), ""]
    errors = [r for r in rows if not r["ok"]]
    if errors:
        L += [f"**Crashed on {len(errors)} pictures:** " + ", ".join(f"{r['file']} ({r['error']})" for r in errors), ""]

    # ---- grid -------------------------------------------------------------------
    nf = [r for r in rows if not r["found"]]
    L += ["## Pixel grid found", "",
          f"Found on **{len(rows) - len(nf)} of {len(rows)}**. Missed: " + (", ".join(r["file"][-8:-4] for r in nf) or "none"), ""]

    # ---- view -------------------------------------------------------------------
    scored = []                       # the labelled answer and the tool's answer, kept apart
    for lab, res in zip(labels, results):
        if lab.get("view") in ("iso", "ort"):
            scored.append({"file": lab["file"], "truth": lab["view"], "clear": lab.get("view_clear", ""),
                           "said": res["view"], "diag": res.get("diag"), "horiz": res.get("horiz"), "vert": res.get("vert")})
    for title, subset in (("all labelled pictures", scored),
                          ("clear cases only (view_clear = y)", [s for s in scored if s["clear"] == "y"]),
                          ("not-clear cases (view_clear = n)", [s for s in scored if s["clear"] == "n"])):
        if not subset:
            continue
        c = Counter((s["truth"], s["said"]) for s in subset)
        L += [f"## View check (buildings, objects, scenes): {title}", ""] + table(c, ["iso", "ort"], ["iso", "ort", "cant"]) + [""]
    clear = [s for s in scored if s["clear"] == "y"]
    false_iso = [s for s in clear if s["truth"] == "ort" and s["said"] == "iso"]
    missed_iso = [s for s in clear if s["truth"] == "iso" and s["said"] != "iso"]
    L += ["### Misses among clear cases", "",
          f"- Clear isometric not found ({len(missed_iso)}): " + (", ".join(s["file"][-8:-4] for s in missed_iso) or "none"),
          f"- Clear orthographic called isometric ({len(false_iso)}): " + (", ".join(s["file"][-8:-4] for s in false_iso) or "none"), ""]

    # ---- checks not built yet ---------------------------------------------------
    # ---- framing -----------------------------------------------------------------
    fr = [(lab["file"], lab["framing"], res.get("framing", "cant"), res.get("border_plain"), res.get("subject_share"))
          for lab, res in zip(labels, results) if lab.get("framing")]
    if fr:
        c = Counter((t, said) for _, t, said, *_ in fr)
        right = sum(1 for _, t, said, *_ in fr if t == said)
        wrong = [f for f in fr if f[1] != f[2]]
        L += ["## Framing check", "", f"**Right on {right} of {len(fr)}.**", ""]
        L += table(c, ["isolated", "subject_on_background", "scene"], ["isolated", "subject_on_background", "scene", "cant"]) + [""]
        L += ["Wrong: " + (", ".join(f"{f[0][-8:-4]} (labelled {f[1]}, said {f[2]}; border {f[3]} plain, subject {f[4]})" for f in wrong) or "none"), ""]
    for col, plan in (("subject", "slice B1"), ("facing", "slice C2"), ("shadow", "slice D1")):
        n = sum(1 for lab in labels if lab.get(col))
        L += [f"## {col.capitalize()} check", "", f"Not built yet ({plan}). {n} labelled pictures are waiting for it.", ""]

    text = "\n".join(L)
    args.out.write_text(text + "\n", encoding="utf-8")
    # per-picture detail next to the report (ignored by git)
    detail = args.out.with_name("last_run.csv")
    with open(detail, "w", newline="", encoding="utf-8") as f:
        keys = ["file", "found", "px", "py", "sprite_w", "sprite_h", "view", "diag", "horiz", "vert", "framing", "border_plain", "subject_share", "seconds"]
        w = csv.writer(f)
        w.writerow(["file", "label_view", "label_clear"] + keys[1:])
        for lab, res in zip(labels, results):
            w.writerow([lab["file"], lab.get("view", ""), lab.get("view_clear", "")] + [res.get(k, "") for k in keys[1:]])
    print(text)
    print(f"\nSaved {args.out} and {detail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

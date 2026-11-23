# Batch sorting: which folder does a picture belong in, given what the user wants? No AI.
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
"""Four folders, decided from the tool's own verdicts:

  matches/         the picture is pixel art, and its view (or facing) is what you asked for.
                   Holds the finished, snapped sprite.
  mismatches/      it is pixel art but the wrong view: you wanted straight-on, it is isometric (or the reverse).
                   Holds a copy of the original, so you can look and decide.
  cant-tell/       the tool could not judge the view or facing. A copy of the original.
  not-pixel-art/   no usable pixel grid: painted, smooth, or already true size. A copy of the original.

Settings:
  want_view    "orthogonal", "isometric" or "either"   (buildings, objects and scenes; anything that is not a character)
  want_facing  "diagonal", "cardinal" or "either"       (characters; the facing check could not be made to work
                                                         without AI (see facing.py), so a character is "can't tell"
                                                         whenever a facing is wanted)

The two settings are independent: a game can want diagonal-facing characters in an orthographic world.
"""
from __future__ import annotations

from dataclasses import dataclass

BUCKETS = ("matches", "mismatches", "cant-tell", "not-pixel-art")
WANT_VIEW = ("orthogonal", "isometric", "either")
WANT_FACING = ("diagonal", "cardinal", "either")


@dataclass
class Decision:
    bucket: str
    reason: str            # one plain sentence, written to the report
    weak: bool = False     # the grid was weak: the sprite is saved, but the file name says so


def decide(res, want_view: str = "either", want_facing: str = "either") -> Decision:
    """res: a pixel_snap.Result (only grid_status, grid_note, subject, view and facing are read)."""
    if res.grid_status == "none":
        return Decision("not-pixel-art", res.grid_note)
    weak = res.grid_status == "weak"
    if res.subject.kind == "character":
        if want_facing == "either":
            return Decision("matches", "a character; no facing was asked for", weak)
        facing = getattr(res, "facing", None)
        if facing is None or facing.kind in ("unclear", "mixed", "n/a"):
            why = ("the facing check is not built yet" if facing is None else
                   "the tool cannot judge facing yet (see facing.py)" if facing.kind in ("unclear", "n/a") else "the facing is mixed")
            return Decision("cant-tell", f"a character, and you asked for {want_facing} facing, but {why}")
        if facing.kind == want_facing:
            return Decision("matches", f"a character facing {facing.kind}, as asked", weak)
        return Decision("mismatches", f"a character facing {facing.kind}; you asked for {want_facing}")
    if want_view == "either":
        return Decision("matches", f"{res.subject.kind}; no view was asked for", weak)
    seen = res.view.kind
    if seen == "unclear":
        return Decision("cant-tell", f"{res.subject.kind}, and you asked for {want_view}, but the view is unclear")
    if seen == want_view:
        return Decision("matches", f"{res.subject.kind}, {seen}, as asked", weak)
    return Decision("mismatches", f"{res.subject.kind}; you asked for {want_view} but it is {seen}")


REPORT_COLUMNS = [
    "file", "folder", "reason", "subject", "view", "facing", "facing_clues", "grid", "pixel_w", "pixel_h", "sprite_w", "sprite_h",
    "flatness", "framing", "shadow", "shadow_kind", "shadow_removed_pixels", "colours",
    "view_diagonal", "view_horizontal", "view_vertical", "saved_as",
]


def report_row(path, res, decision: Decision, saved_as: str) -> dict:
    facing = getattr(res, "facing", None)
    return {
        "file": str(path), "folder": decision.bucket, "reason": decision.reason,
        "subject": res.subject.kind, "view": "n/a (character)" if res.subject.kind == "character" else res.view.kind,
        "facing": facing.kind if facing is not None else "not checked",
        "facing_clues": "" if facing is None or not facing.clues else "; ".join(f"{k} {v}" for k, v in facing.clues.items()),
        "grid": res.grid_status, "pixel_w": round(res.px, 2), "pixel_h": round(res.py, 2),
        "sprite_w": res.size[0], "sprite_h": res.size[1],
        "flatness": "" if res.flatness is None else round(res.flatness, 3),
        "framing": res.framing.kind,
        "shadow": "can't tell" if res.shadow.unsure else (res.shadow.kind if res.shadow.found else "none"),
        "shadow_kind": res.shadow.kind if res.shadow.found else "",
        "shadow_removed_pixels": res.shadow_removed, "colours": res.colours,
        "view_diagonal": round(res.view.diagonal, 3), "view_horizontal": round(res.view.horizontal, 3),
        "view_vertical": round(res.view.vertical, 3), "saved_as": saved_as,
    }

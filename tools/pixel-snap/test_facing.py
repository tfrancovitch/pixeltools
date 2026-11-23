# Tests for facing.py: the clues are measured, the verdict is honest ("can't tell"). Slice C2.
# Run from this folder: python -m unittest test_facing -v
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import facing
import pixel_snap
from test_framing import figure, on_background, plain
from test_pixel_snap import make_fake, scene
from test_subject import iso_building
from test_shadow import compose, GROUNDS


def snap_figure(extra=None, ground=(255, 255, 255)):
    fg, mask = figure()
    pic = on_background(fg, mask, plain(ground, mask.shape))
    if extra:
        extra(pic)
    return pixel_snap.snap_image(make_fake(pic, 12.6, 1.0, 4))


class FacingTests(unittest.TestCase):
    def test_a_character_gets_clues_and_an_honest_cant_tell(self):
        res = snap_figure()
        self.assertEqual(res.subject.kind, "character")
        self.assertEqual(res.facing.kind, "unclear")
        self.assertIn("can't tell", res.facing.describe())
        self.assertEqual(set(res.facing.clues), {"symmetry", "feet_apart", "feet_level", "torso_leg_shift", "head_off_torso", "height_over_width"})

    def test_the_symmetry_clue_follows_the_drawing(self):
        symmetric = snap_figure().facing.clues["symmetry"]

        def lopsided(pic):                                    # a long arm out to one side
            pic[30:34, 38:52] = (180, 40, 40)
            pic[30:34, 12:16] = (180, 40, 40)

        def very_lopsided(pic):
            pic[22:30, 4:12] = (180, 40, 40)
            pic[40:50, 4:14] = (180, 40, 40)

        self.assertGreater(symmetric, 0.85)
        self.assertLess(snap_figure(very_lopsided).facing.clues["symmetry"], symmetric)

    def test_the_two_feet_show_up_as_a_gap(self):
        self.assertGreater(snap_figure().facing.clues["feet_apart"], 0.2)

    def test_style_is_not_mistaken_for_facing(self):
        # The six diagonal characters of batch 1 all stood on coloured ground with a shadow. That is style, not
        # facing, so a drawn figure with a shadow on coloured ground must get the same honest answer.
        pic, sprite, shadow = compose(GROUNDS["green"], "contact", 0.7)
        res = pixel_snap.snap_image(make_fake(pic, 11.6, 1.0, 4))
        self.assertTrue(res.shadow.found)
        self.assertEqual(res.facing.kind, "unclear")

    def test_only_characters_are_judged_on_facing(self):
        fg, mask = iso_building(8, 14)
        res = pixel_snap.snap_image(make_fake(on_background(fg, mask, plain((255, 255, 255), mask.shape)), 12.6, 1.0, 4))
        self.assertEqual(res.subject.kind, "building")
        self.assertEqual(res.facing.kind, "n/a")
        res = pixel_snap.snap_image(make_fake(scene("front", 2), 8.3, 0.9, 4))
        self.assertEqual(res.facing.kind, "n/a")

    def test_the_command_line_says_so(self):
        fg, mask = figure()
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "hero.png"
            make_fake(on_background(fg, mask, plain((255, 255, 255), mask.shape)), 12.6, 1.0, 4).save(src)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                pixel_snap.main([str(src), "--check-only"])
            self.assertIn("facing: can't tell", buf.getvalue())

    def test_wanting_a_facing_sends_a_character_to_cant_tell_with_the_reason(self):
        fg, mask = figure()
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "hero.png"
            make_fake(on_background(fg, mask, plain((255, 255, 255), mask.shape)), 12.6, 1.0, 4).save(src)
            out = Path(d) / "sorted"
            with contextlib.redirect_stdout(io.StringIO()):
                pixel_snap.main([str(src), "--sort", str(out), "--want-facing", "diagonal"])
            self.assertEqual([p.name for p in (out / "cant-tell").iterdir()], ["hero.png"])
            import csv
            row = next(csv.DictReader(open(out / "report.csv", newline="", encoding="utf-8")))
            self.assertIn("cannot judge facing yet", row["reason"])
            self.assertIn("symmetry", row["facing_clues"])


if __name__ == "__main__":
    unittest.main()

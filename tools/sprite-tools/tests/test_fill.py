# Tests for fill (S1). Run from tools/sprite-tools: python -m unittest discover tests -v
# Copyright (C) 2026 the pixeltools contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY; see the GNU General Public
# License for details: <https://www.gnu.org/licenses/>.
import contextlib
import io
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cases  # noqa: E402
import sprite  # noqa: E402
from spritetools import core, fill  # noqa: E402

RED = (255, 0, 0, 255)
GREEN = (0, 255, 0, 255)


def row(values):
    """A one-row picture of colours (v, 0, 0, 255): the distance between two is exactly the difference of v."""
    return np.array([[[v, 0, 0, 255] for v in values]], dtype=np.uint8)


class FillTests(unittest.TestCase):
    def test_tolerance_edge_is_exact(self):
        # 10 percent is a cut-off of exactly 51: 51 apart is the same colour, 52 apart is not
        img = row([100, 151, 152, 203])
        out, info = fill.apply(img, {"at": (0, 0), "colour": GREEN, "tolerance": 10, "everywhere": True})
        self.assertEqual([tuple(p) for p in out[0]], [GREEN, GREEN, (152, 0, 0, 255), (203, 0, 0, 255)])
        self.assertEqual(info["pixels_filled"], 2)

    def test_zero_tolerance_fills_only_the_exact_colour(self):
        img = row([100, 100, 101, 100])
        out, _ = fill.apply(img, {"at": (0, 0), "colour": GREEN, "tolerance": 0})
        self.assertEqual([tuple(p) for p in out[0]], [GREEN, GREEN, (101, 0, 0, 255), (100, 0, 0, 255)])  # the last is cut off by the 101

    def test_connected_fill_stops_at_a_wall_everywhere_does_not(self):
        img = row([100, 100, 200, 100])
        conn, c = fill.apply(img, {"at": (0, 0), "colour": GREEN})
        self.assertEqual(c["pixels_filled"], 2)
        every, e = fill.apply(img, {"at": (0, 0), "colour": GREEN, "everywhere": True})
        self.assertEqual(e["pixels_filled"], 3)

    def test_corner_touching_counts_only_when_asked(self):
        img = cases.diagonal()
        _, off = fill.apply(img, {"at": (1, 1), "colour": GREEN})
        _, on = fill.apply(img, {"at": (1, 1), "colour": GREEN, "corners": True})
        self.assertEqual((off["pixels_filled"], on["pixels_filled"]), (1, 2))

    def test_the_default_colour_is_transparent_and_alpha_is_filled_exactly(self):
        img = cases.solid(3, 3, (50, 60, 70, 255))
        out, _ = fill.apply(img, {"at": (1, 1)})
        self.assertTrue((out == 0).all())
        out, _ = fill.apply(img, {"at": (1, 1), "colour": (10, 20, 30, 40)})
        self.assertTrue((out == (10, 20, 30, 40)).all())

    def test_transparent_pixels_are_one_colour_whatever_their_hidden_rgb(self):
        img = cases.with_transparency()
        out, info = fill.apply(img, {"at": (7, 7), "colour": GREEN, "tolerance": 0})
        self.assertEqual(info["pixels_filled"], 64 - 16)          # every transparent pixel, including the one hiding (9, 9, 9)
        self.assertTrue((out[0, 0] == GREEN).all())

    def test_a_noisy_area_is_filled_in_one_tap_where_an_exact_fill_is_not(self):
        img = cases.noisy(cases.solid(40, 40, (200, 40, 40, 255)), 6, 3)
        _, exact = fill.apply(img, {"at": (5, 5), "colour": GREEN, "tolerance": 0})
        _, tolerant = fill.apply(img, {"at": (5, 5), "colour": GREEN})
        self.assertLess(exact["pixels_filled"], 100)               # the owner's problem: it stops at the exact colour
        self.assertEqual(tolerant["pixels_filled"], 1600)

    def test_background_fills_a_noisy_gradient_ground_and_spares_the_sprite(self):
        img, sky = cases.figure_on_sky(96, 96, 6, 5)
        out, info = fill.apply(img, {"background": True, "colour": (0, 0, 0, 0)})
        gone = out[..., 3] == 0
        self.assertEqual(int((sky & ~gone).sum()), 0)               # all of the ground
        # the sprite pixels are untouched (they differ from the sky by far more than the tolerance)
        self.assertEqual(int((~sky & gone).sum()), 0)
        self.assertEqual(info["pixels_filled"], int(sky.sum()))
        self.assertRegex(info["background_colour"], r"^#[0-9a-f]{8}$")

    def test_background_copes_with_jpeg_damage_on_a_gradient(self):
        for quality in (50, 70, 90):
            with self.subTest(quality=quality):
                img, sky = cases.figure_on_sky(160, 160, 4, 2)
                out, _ = fill.apply(cases.jpeg_damage(img, quality), {"background": True})
                gone = out[..., 3] == 0
                self.assertLess((sky & ~gone).sum(), 0.005 * sky.sum())            # at most 0.5 percent of the ground missed
                # almost nothing leaks into the sprite's inside: the figure shrunk by 3 pixels (at most 0.2 percent)
                inner = ~sky
                for _ in range(3):
                    p = np.pad(inner, 1, constant_values=False)
                    inner = inner & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
                self.assertLessEqual(int((gone & inner).sum()), 0.002 * inner.sum())

    def test_background_keeps_a_pocket_that_the_sprite_encloses(self):
        out, info = fill.apply(cases.ring_sprite(), {"background": True})
        self.assertEqual(tuple(out[10, 10]), (120, 120, 120, 255))      # the pocket in the middle of the ring
        self.assertEqual(out[0, 0, 3], 0)                               # the ground outside is gone
        self.assertEqual(info["pixels_filled"], 400 - 144)

    def test_background_follows_corners_only_when_asked(self):
        # a ground that is split into two by a diagonal line of sprite pixels
        a = cases.solid(6, 6, (120, 120, 120, 255))
        for i in range(6):
            a[i, i] = (30, 30, 30, 255)
        _, plain = fill.apply(a, {"background": True})
        _, diag = fill.apply(a, {"background": True, "corners": True})
        self.assertEqual(plain["pixels_filled"], 30)       # the ring touches both sides, so both halves are reached anyway
        self.assertEqual(diag["pixels_filled"], 30)

    def test_the_input_picture_is_never_changed(self):
        img = cases.pictures()["sky"]
        before = img.copy()
        fill.apply(img, {"background": True})
        fill.apply(img, {"at": (1, 1)})
        self.assertTrue((img == before).all())

    def test_mistakes_are_refused_in_plain_words(self):
        img = cases.pictures()["sky"]
        for opts, words in (({}, "Say where to start"), ({"at": (99, 0)}, "outside the picture"),
                            ({"at": (1, 1), "background": True}, "not both"), ({"at": (1, 1), "tolerance": 150}, "between 0 and 100")):
            with self.subTest(opts=opts):
                with self.assertRaisesRegex(ValueError, words):
                    fill.apply(img, opts)

    def test_a_one_pixel_picture_works(self):
        out, info = fill.apply(cases.solid(1, 1, (5, 6, 7, 255)), {"background": True, "colour": (1, 1, 1, 255)})
        self.assertEqual((tuple(out[0, 0]), info["pixels_filled"]), ((1, 1, 1, 255), 1))

    def test_a_big_picture_is_fast_enough(self):
        img, _ = cases.figure_on_sky(1024, 1024, 6, 1)
        start = time.time()
        fill.apply(img, {"background": True})
        fill.apply(img, {"at": (512, 20), "colour": GREEN})
        self.assertLess(time.time() - start, 2.0 * 2)       # two fills, a budget of 2 seconds each


class FillCommandTests(unittest.TestCase):
    def test_the_command_fills_a_background_and_reports_in_json(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "hero.png"
            img, sky = cases.figure_on_sky(64, 64, 5, 2)
            core.write_png(src, img)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = sprite.main(["fill", str(src), "--background", "--json"])
            self.assertEqual(code, 0)
            rec = json.loads(out.getvalue())
            self.assertEqual(rec["pixels_filled"], int(sky.sum()))
            self.assertTrue(rec["output"].endswith("hero_fill.png"))
            self.assertEqual(core.read_image(rec["output"])[0, 0, 3], 0)

    def test_the_command_reports_a_mistake_with_exit_code_2(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "a.png"
            core.write_png(src, cases.solid(4, 4, (1, 2, 3, 255)))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = sprite.main(["fill", str(src)])
            self.assertEqual(code, 2)
            self.assertIn("Say where to start", out.getvalue())

    def test_colour_and_point_options_are_read(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "a.png"
            core.write_png(src, cases.solid(4, 4, (1, 2, 3, 255)))
            with contextlib.redirect_stdout(io.StringIO()):
                code = sprite.main(["fill", str(src), "--at", "1,1", "--colour", "#ff0000", "-o", str(Path(d) / "o.png")])
            self.assertEqual(code, 0)
            self.assertTrue((core.read_image(Path(d) / "o.png") == RED).all())


if __name__ == "__main__":
    unittest.main()

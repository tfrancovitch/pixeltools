# Tests for turn (S0). Run from the tools/sprite-tools folder: python -m unittest discover tests -v
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
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sprite  # noqa: E402
from spritetools import core, turn  # noqa: E402


def small():
    """3 wide, 2 tall, every pixel different: row 0 is R G B, row 1 is C M Y."""
    return np.array([[[255, 0, 0, 255], [0, 255, 0, 255], [0, 0, 255, 255]],
                     [[0, 255, 255, 255], [255, 0, 255, 255], [255, 255, 0, 128]]], dtype=np.uint8)


class TurnTests(unittest.TestCase):
    def test_flip_h_mirrors_left_right_exactly(self):
        out, info = turn.apply(small(), {"flip": "h"})
        self.assertTrue((out == small()[:, ::-1]).all())
        self.assertEqual(info["pixels_changed"], 4)       # the middle column stays, 2 columns x 2 rows change

    def test_flip_v_mirrors_top_bottom_exactly(self):
        out, info = turn.apply(small(), {"flip": "v"})
        self.assertTrue((out == small()[::-1]).all())
        self.assertEqual(info["pixels_changed"], 6)

    def test_flipping_twice_gives_the_original_back(self):
        for f in "hv":
            once, _ = turn.apply(small(), {"flip": f})
            twice, _ = turn.apply(once, {"flip": f})
            self.assertTrue((twice == small()).all())

    def test_no_flip_changes_nothing_and_a_wrong_flip_is_refused(self):
        out, info = turn.apply(small(), {})
        self.assertTrue((out == small()).all())
        self.assertEqual(info["pixels_changed"], 0)
        with self.assertRaisesRegex(ValueError, "h or v"):
            turn.apply(small(), {"flip": "x"})

    def test_the_input_picture_is_never_changed(self):
        a = small()
        turn.apply(a, {"flip": "h"})
        self.assertTrue((a == small()).all())


class CoreTests(unittest.TestCase):
    def test_colours_are_read_in_every_written_form(self):
        self.assertEqual(core.parse_colour("#ff8000"), (255, 128, 0, 255))
        self.assertEqual(core.parse_colour("#ff800040"), (255, 128, 0, 64))
        self.assertEqual(core.parse_colour("1, 2, 3"), (1, 2, 3, 255))
        self.assertEqual(core.parse_colour("1,2,3,4"), (1, 2, 3, 4))
        for bad in ("red", "#12345", "256,0,0", "1,2", "#gg0000"):
            with self.assertRaisesRegex(ValueError, "not a colour"):
                core.parse_colour(bad)

    def test_points_are_read_and_checked(self):
        self.assertEqual(core.parse_point("12, 40"), (12, 40))
        with self.assertRaisesRegex(ValueError, "not a point"):
            core.parse_point("12")
        with self.assertRaisesRegex(ValueError, "outside the picture"):
            core.check_point(small(), (3, 0))

    def test_tolerance_is_a_percentage_of_the_largest_distance(self):
        self.assertEqual(core.cutoff_sq(0), 0)
        self.assertAlmostEqual(core.cutoff_sq(100) ** 0.5, 510)
        self.assertAlmostEqual(core.cutoff_sq(10) ** 0.5, 51)
        with self.assertRaises(ValueError):
            core.cutoff_sq(101)

    def test_all_transparent_pixels_count_as_one_colour(self):
        a = np.zeros((1, 3, 4), dtype=np.uint8)
        a[0, 1] = (9, 9, 9, 0)
        a[0, 2] = (200, 0, 0, 0)
        self.assertEqual(core.count_colours(a), 1)

    def test_grow_stops_at_walls_and_corners_are_optional(self):
        # a diagonal pair of open cells: connected only with corners
        open_ = np.zeros(9, dtype=bool)
        open_[[0, 4]] = True
        ok = lambda p, q: open_[q]  # noqa: E731
        self.assertEqual(core.grow(3, 3, np.array([0]), ok, False).sum(), 1)
        self.assertEqual(core.grow(3, 3, np.array([0]), ok, True).sum(), 2)


class CommandTests(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = sprite.main(list(argv))
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def test_list_shows_the_tools(self):
        code, out, _ = self.run_cli("--list")
        self.assertEqual(code, 0)
        self.assertIn("turn", out)

    def test_json_gives_one_object_per_picture_and_the_file_is_written(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "hero.png"
            core.write_png(src, small())
            code, out, _ = self.run_cli("turn", str(src), "--flip", "h", "--json")
            self.assertEqual(code, 0)
            rec = json.loads(out)
            self.assertEqual((rec["size"], rec["pixels_changed"], rec["colours_before"], rec["colours_after"]), ([3, 2], 4, 6, 6))
            self.assertTrue((core.read_image(Path(d) / "hero_turn.png") == small()[:, ::-1]).all())

    def test_brief_and_plain_output_and_out_dir(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.png", Path(d) / "b.png"
            core.write_png(a, small())
            core.write_png(b, small())
            code, out, _ = self.run_cli("turn", str(a), str(b), "--flip", "v", "--brief", "--out-dir", str(Path(d) / "out"))
            self.assertEqual(code, 0)
            self.assertEqual(len(out.strip().splitlines()), 2)
            self.assertTrue((Path(d) / "out" / "a_turn.png").exists())
            code, out, _ = self.run_cli("turn", str(a), "--flip", "v", "-o", str(Path(d) / "x.png"))
            self.assertIn("Saved", out)

    def test_exit_codes_unreadable_file_is_1_and_the_rest_still_work(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "a.png"
            core.write_png(a, small())
            code, out, _ = self.run_cli("turn", str(Path(d) / "missing.png"), str(a), "--flip", "h", "--brief")
            self.assertEqual(code, 1)
            self.assertIn("FAILED", out)
            self.assertTrue((Path(d) / "a_turn.png").exists())

    def test_several_pictures_in_parallel(self):
        with tempfile.TemporaryDirectory() as d:
            files = []
            for i in range(3):
                p = Path(d) / f"p{i}.png"
                core.write_png(p, small())
                files.append(str(p))
            code, out, _ = self.run_cli("turn", *files, "--flip", "h", "--brief", "--jobs", "2")
            self.assertEqual(code, 0)
            self.assertEqual(len(out.strip().splitlines()), 3)


if __name__ == "__main__":
    unittest.main()

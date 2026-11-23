# Tests for replace (S3), including the palette swap (--map).
# Run from tools/sprite-tools: python -m unittest tests.test_replace -v
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
from spritetools import core, replace  # noqa: E402

RED, GREEN, BLUE = (255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)


def row(values):
    return np.array([[[v, 0, 0, 255] for v in values]], dtype=np.uint8)


class ReplaceOne(unittest.TestCase):
    def test_a_colour_and_everything_close_to_it_is_replaced_exactly_at_the_edge(self):
        img = row([100, 140, 141, 160])                   # 8 percent is a cut-off of 40.8
        out, info = replace.apply(img, {"from": (100, 0, 0, 255), "to": GREEN})
        self.assertEqual([tuple(p) for p in out[0]], [GREEN, GREEN, (141, 0, 0, 255), (160, 0, 0, 255)])
        self.assertEqual((info["pixels_replaced"], info["pixels_changed"]), (2, 2))

    def test_the_colour_can_be_taken_from_a_point(self):
        img = row([100, 100, 200])
        out, _ = replace.apply(img, {"at": (0, 0), "to": GREEN})
        self.assertEqual([tuple(p) for p in out[0]], [GREEN, GREEN, (200, 0, 0, 255)])

    def test_everywhere_by_default_but_only_the_connected_area_when_asked(self):
        img = row([100, 100, 200, 100])
        every, e = replace.apply(img, {"at": (0, 0), "to": GREEN})
        conn, c = replace.apply(img, {"at": (0, 0), "to": GREEN, "connected": True})
        self.assertEqual((e["pixels_replaced"], c["pixels_replaced"]), (3, 2))

    def test_corners_only_with_connected_and_when_asked(self):
        img = cases.diagonal()
        _, off = replace.apply(img, {"at": (1, 1), "to": GREEN, "connected": True})
        _, on = replace.apply(img, {"at": (1, 1), "to": GREEN, "connected": True, "corners": True})
        _, all_ = replace.apply(img, {"at": (1, 1), "to": GREEN})
        self.assertEqual((off["pixels_replaced"], on["pixels_replaced"], all_["pixels_replaced"]), (1, 2, 2))

    def test_the_new_colour_is_exact_including_alpha_and_transparent(self):
        img = cases.solid(3, 3, (50, 60, 70, 255))
        out, _ = replace.apply(img, {"at": (0, 0), "to": (1, 2, 3, 77)})
        self.assertTrue((out == (1, 2, 3, 77)).all())
        out, _ = replace.apply(img, {"at": (0, 0), "to": (9, 9, 9, 0)})
        self.assertTrue((out == 0).all())

    def test_transparent_pixels_are_one_colour(self):
        out, info = replace.apply(cases.with_transparency(), {"from": (0, 0, 0, 0), "to": GREEN, "tolerance": 0})
        self.assertEqual(info["pixels_replaced"], 64 - 16)
        self.assertTrue((out[0, 0] == GREEN).all())

    def test_replacing_a_colour_with_itself_changes_nothing(self):
        img = cases.pictures()["character"]
        out, info = replace.apply(img, {"from": (200, 44, 48, 255), "to": (200, 44, 48, 255), "tolerance": 0})
        self.assertTrue((out == img).all())
        self.assertGreater(info["pixels_replaced"], 0)
        self.assertEqual(info["pixels_changed"], 0)

    def test_the_input_is_never_changed(self):
        img = cases.pictures()["character"]
        keep = img.copy()
        replace.apply(img, {"at": (20, 26), "to": GREEN})
        self.assertTrue((img == keep).all())

    def test_mistakes_are_refused_in_plain_words(self):
        img = cases.pictures()["sky"]
        for opts, words in (({"from": RED}, "Say what to change it into"), ({"to": RED}, "Say which colour to change"),
                            ({"from": RED, "to": GREEN, "at": (1, 1)}, "not both"), ({"from": RED, "to": GREEN, "connected": True}, "needs --at"),
                            ({"at": (99, 0), "to": GREEN}, "outside the picture"), ({"at": (1, 1), "to": GREEN, "tolerance": -1}, "between 0 and 100")):
            with self.subTest(opts=opts):
                with self.assertRaisesRegex(ValueError, words):
                    replace.apply(img, opts)

    def test_a_big_picture_is_fast_enough(self):
        img, _ = cases.figure_on_sky(1024, 1024, 5, 1)
        start = time.time()
        replace.apply(img, {"at": (512, 600), "to": GREEN})
        replace.apply(img, {"map_text": "#c82828 #2828c8\n#e2b28c #00c800\n#3c468c #ffffff"})
        self.assertLess(time.time() - start, 4.0)


class PaletteSwap(unittest.TestCase):
    def test_a_swap_changes_every_listed_colour_at_once(self):
        img = cases.stripes()                              # red, green, blue, yellow
        out, info = replace.apply(img, {"map": [(RED, BLUE), (BLUE, RED)], "tolerance": 0})
        self.assertTrue((out[:, 0:4] == BLUE).all() and (out[:, 8:12] == RED).all())
        self.assertTrue((out[:, 4:8] == GREEN).all())
        self.assertEqual((info["pairs"], info["pairs_used"], info["pixels_replaced"]), (2, 2, 48))

    def test_a_swap_is_not_a_chain(self):
        # red -> green and green -> red: nothing turns red-green-red; both colours trade places in one go
        img = cases.stripes()
        out, _ = replace.apply(img, {"map": [(RED, GREEN), (GREEN, RED)], "tolerance": 0})
        self.assertTrue((out[:, 0:4] == GREEN).all() and (out[:, 4:8] == RED).all())

    def test_a_pixel_goes_to_the_nearest_listed_colour(self):
        img = row([70, 120, 170])
        pairs = [((60, 0, 0, 255), (1, 0, 0, 255)), ((180, 0, 0, 255), (2, 0, 0, 255))]
        out, _ = replace.apply(img, {"map": pairs, "tolerance": 10})
        self.assertEqual([int(v) for v in out[0, :, 0]], [1, 120, 2])                    # 120 is 60 from both: more than 51

    def test_the_first_of_two_equally_near_pairs_wins(self):
        img = row([100])
        pairs = [((90, 0, 0, 255), (1, 0, 0, 255)), ((110, 0, 0, 255), (2, 0, 0, 255))]
        out, _ = replace.apply(img, {"map": pairs, "tolerance": 10})
        self.assertEqual(int(out[0, 0, 0]), 1)

    def test_a_swap_with_noise_still_works_through_the_tolerance(self):
        img = cases.noisy(cases.pictures()["character"], 5, 2)
        out, info = replace.apply(img, {"map_text": "#c82c30 #2c30c8\n#6e5028 #ff00ff"})
        self.assertEqual(info["pixels_replaced"], 136 + 48)       # the shirt's light side and the hair
        self.assertEqual(core.count_colours(out) - core.count_colours(img) < 0, True)

    def test_the_map_text_format(self):
        text = "; a comment\n\n#c82c30 -> #2c30c8\n  232,180,140   0,200,0  \n// another\n#00000000 => #ffffffff\n1,2,3,4 5,6,7"
        self.assertEqual(replace.parse_map(text), [((200, 44, 48, 255), (44, 48, 200, 255)), ((232, 180, 140, 255), (0, 200, 0, 255)),
                                                    ((0, 0, 0, 0), (255, 255, 255, 255)), ((1, 2, 3, 4), (5, 6, 7, 255))])

    def test_bad_maps_say_which_line_and_why(self):
        for text, words in (("#ff0000 #00ff00\nnonsense", "Line 2 of the map is not a pair"), ("#ff0000", "Line 1 of the map is not a pair"),
                            ("#ff0000 #00ff0", "Line 1 of the map: '#00ff0' is not a colour"), ("; only a comment", "no colour pairs")):
            with self.subTest(text=text):
                with self.assertRaisesRegex(ValueError, words):
                    replace.parse_map(text)

    def test_a_swap_cannot_be_mixed_with_the_single_colour_options(self):
        with self.assertRaisesRegex(ValueError, "do not combine"):
            replace.apply(cases.stripes(), {"map": [(RED, BLUE)], "to": GREEN})

    def test_swapping_every_colour_of_a_sprite_to_itself_in_a_new_palette(self):
        # the same palette swapped there and back gives the original (colours well apart, tolerance small)
        img = cases.pictures()["character"]
        pal = [tuple(c) + (255,) for c in cases.PAL.values()]
        other = [tuple(255 - v for v in c[:3]) + (255,) for c in pal]
        there, _ = replace.apply(img, {"map": list(zip(pal, other)), "tolerance": 2})
        back, _ = replace.apply(there, {"map": list(zip(other, pal)), "tolerance": 2})
        self.assertTrue((back == img).all())


class ReplaceCommand(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = sprite.main(list(argv))
        return code, out.getvalue()

    def test_the_command_replaces_a_colour(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "a.png"
            core.write_png(src, cases.pictures()["character"])
            code, out = self.run_cli("replace", str(src), "--from", "#c82c30", "--to", "0,255,0", "--json")
            self.assertEqual(code, 0)
            rec = json.loads(out)
            self.assertGreater(rec["pixels_replaced"], 100)
            self.assertTrue(rec["output"].endswith("a_replace.png"))

    def test_the_command_does_a_palette_swap_from_a_file(self):
        with tempfile.TemporaryDirectory() as d:
            src, swap = Path(d) / "a.png", Path(d) / "swap.txt"
            core.write_png(src, cases.pictures()["character"])
            swap.write_text("; shirt and skin\n#c82c30 #2c30c8\n#e8b48c #00c800\n", encoding="utf-8")
            code, out = self.run_cli("replace", str(src), "--map", str(swap), "--json")
            self.assertEqual(code, 0)
            rec = json.loads(out)
            self.assertEqual((rec["pairs"], rec["pairs_used"]), (2, 2))
            got = core.read_image(rec["output"])
            self.assertEqual(tuple(got[26, 16]), (44, 48, 200, 255))

    def test_a_bad_map_file_is_exit_code_2_with_the_line(self):
        with tempfile.TemporaryDirectory() as d:
            src, swap = Path(d) / "a.png", Path(d) / "swap.txt"
            core.write_png(src, cases.pictures()["character"])
            swap.write_text("#ff0000\n", encoding="utf-8")
            code, out = self.run_cli("replace", str(src), "--map", str(swap))
            self.assertEqual(code, 2)
            self.assertIn("Line 1 of the map", out)


if __name__ == "__main__":
    unittest.main()

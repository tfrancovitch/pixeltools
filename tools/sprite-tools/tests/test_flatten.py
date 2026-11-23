# Tests for flatten (S2): each of the three passes alone, the switches, one area, and the drawn-picture gate.
# Run from tools/sprite-tools: python -m unittest tests.test_flatten -v
# Copyright (C) 2026 the pixeltools contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY; see the GNU General Public
# License for details: <https://www.gnu.org/licenses/>.
import contextlib
import io
import itertools
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
from spritetools import core, flatten  # noqa: E402

ONLY_MERGE = {"edges": False, "min_speck": 0}
ONLY_EDGES = {"merge": False, "min_speck": 0}
ONLY_SPECKS = {"merge": False, "edges": False}


def close_to(out, want, distance=12):
    """Share of pixels whose colour is within `distance` of the wanted picture's colour (the same colour, to the eye)."""
    return float((np.sqrt(((out[..., :3].astype(int) - want[..., :3].astype(int)) ** 2).sum(-1)) <= distance).mean())


def two_areas(left=(200, 40, 40, 255), right=(40, 40, 200, 255), w=12, h=6):
    a = cases.solid(w, h, left)
    a[:, w // 2:] = right
    return a


class PassOneMerge(unittest.TestCase):
    def test_noise_inside_an_area_becomes_one_colour(self):
        flat = two_areas()
        noisy = cases.noisy(flat, 5, 4)
        out, info = flatten.apply(noisy, ONLY_MERGE)
        self.assertEqual(core.count_colours(out), 2)
        self.assertTrue((np.abs(out[:, :6].astype(int) - out[0, 0]).sum() == 0))
        self.assertEqual(close_to(out, flat, 10), 1.0)
        self.assertEqual((info["pass2_pixels"], info["pass3_pixels"]), (0, 0))

    def test_the_most_used_colour_in_a_group_wins(self):
        a = cases.solid(5, 1, (100, 100, 100, 255))
        a[0, 0] = (110, 100, 100, 255)                            # one odd pixel among four
        out, _ = flatten.apply(a, ONLY_MERGE)
        self.assertTrue((out == (100, 100, 100, 255)).all())

    def test_colours_further_apart_than_the_tolerance_stay_apart(self):
        a = np.array([[[100, 100, 100, 255], [100 + 31, 100, 100, 255], [100 + 31, 100, 100, 255]]], dtype=np.uint8)
        out, _ = flatten.apply(a, dict(ONLY_MERGE, tolerance=6))            # 6 percent is 30.6
        self.assertEqual(core.count_colours(out), 2)
        out, _ = flatten.apply(a, dict(ONLY_MERGE, tolerance=7))            # 7 percent is 35.7
        self.assertEqual(core.count_colours(out), 1)

    def test_a_gradient_is_not_chained_into_one_colour(self):
        a = np.array([[[v, v, v, 255] for v in range(0, 240, 6)]], dtype=np.uint8)
        out, _ = flatten.apply(a, ONLY_MERGE)
        self.assertGreater(core.count_colours(out), 3)

    def test_transparent_pixels_stay_transparent_and_apart(self):
        out, _ = flatten.apply(cases.with_transparency(), ONLY_MERGE)
        self.assertEqual(core.count_colours(out), 2)
        self.assertEqual(out[0, 0, 3], 0)


class PassTwoEdges(unittest.TestCase):
    def test_a_one_pixel_blend_goes_to_the_nearer_side(self):
        a = cases.solid(7, 3, (200, 40, 40, 255))
        a[:, 4:] = (40, 40, 200, 255)
        a[:, 3] = (160, 40, 80, 255)           # a mix, nearer the red side (0.75 red)
        out, info = flatten.apply(a, ONLY_EDGES)
        self.assertTrue((out[:, 3] == (200, 40, 40, 255)).all())
        self.assertEqual(info["pass2_pixels"], 3)
        b = a.copy()
        b[:, 3] = (80, 40, 160, 255)           # nearer the blue side
        out, _ = flatten.apply(b, ONLY_EDGES)
        self.assertTrue((out[:, 3] == (40, 40, 200, 255)).all())

    def test_a_pixel_that_is_not_between_its_neighbours_is_never_touched(self):
        a = cases.solid(7, 3, (200, 40, 40, 255))
        a[:, 4:] = (40, 40, 200, 255)
        a[:, 3] = (40, 220, 40, 255)           # a green stripe: not on the line from red to blue
        out, info = flatten.apply(a, ONLY_EDGES)
        self.assertTrue((out == a).all())
        self.assertEqual(info["pass2_pixels"], 0)

    def test_a_shading_step_that_is_an_area_is_kept(self):
        # outline, then a three-wide band of a dark red, then red: the band lies on the line between them but is an area
        a = np.zeros((6, 12, 4), dtype=np.uint8)
        a[:, :2] = (30, 24, 40, 255)
        a[:, 2:5] = (115, 34, 44, 255)
        a[:, 5:] = (200, 44, 48, 255)
        out, info = flatten.apply(a, ONLY_EDGES)
        self.assertTrue((out == a).all())

    def test_two_pixel_wide_blends_are_settled_over_the_rounds(self):
        a = cases.solid(10, 2, (200, 40, 40, 255))
        a[:, 5:] = (40, 40, 200, 255)
        a[:, 3] = (170, 40, 70, 255)
        a[:, 4] = (110, 40, 130, 255)
        out, _ = flatten.apply(a, ONLY_EDGES)
        self.assertEqual(core.count_colours(out), 2)

    def test_the_corner_of_a_shaded_area_is_not_eaten(self):
        a = cases.solid(10, 10, (200, 44, 48, 255))
        a[:2] = (30, 24, 40, 255)
        a[2:6, 3:] = (140, 28, 36, 255)       # the dark side, whose corner touches the outline and the red
        out, _ = flatten.apply(a, ONLY_EDGES)
        self.assertTrue((out == a).all())


class PassThreeSpecks(unittest.TestCase):
    def area(self):
        return cases.solid(10, 10, (200, 40, 40, 255))

    def test_a_lone_pixel_and_a_pair_are_absorbed_by_default(self):
        a = self.area()
        a[2, 2] = (215, 55, 40, 255)
        a[6, 6] = a[6, 7] = (190, 30, 55, 255)
        out, info = flatten.apply(a, ONLY_SPECKS)
        self.assertTrue((out == (200, 40, 40, 255)).all())
        self.assertEqual(info["pass3_pixels"], 3)

    def test_a_patch_bigger_than_the_limit_is_kept(self):
        a = self.area()
        a[2:4, 2:4] = (215, 55, 40, 255)      # four pixels
        out, _ = flatten.apply(a, ONLY_SPECKS)
        self.assertTrue((out == a).all())
        out, _ = flatten.apply(a, dict(ONLY_SPECKS, min_speck=4))
        self.assertTrue((out == (200, 40, 40, 255)).all())

    def test_a_very_different_pixel_is_kept_so_an_eye_survives(self):
        a = self.area()
        a[4, 4] = (20, 20, 120, 255)
        out, _ = flatten.apply(a, ONLY_SPECKS)
        self.assertTrue((out == a).all())

    def test_a_patch_touching_two_colours_is_not_a_speck(self):
        a = two_areas(w=10, h=10)
        a[4, 4] = (190, 50, 50, 255)
        a[4, 5] = (50, 50, 190, 255)         # each of these touches both areas
        out, _ = flatten.apply(a, ONLY_SPECKS)
        self.assertTrue((out == a).all())

    def test_a_speck_at_the_picture_edge_is_absorbed(self):
        a = self.area()
        a[0, 0] = (215, 55, 40, 255)
        out, _ = flatten.apply(a, ONLY_SPECKS)
        self.assertTrue((out == (200, 40, 40, 255)).all())

    def test_zero_turns_the_pass_off(self):
        a = self.area()
        a[2, 2] = (215, 55, 40, 255)
        out, _ = flatten.apply(a, {"merge": False, "edges": False, "min_speck": 0})
        self.assertTrue((out == a).all())


class SwitchesAndAreas(unittest.TestCase):
    def test_every_pass_off_changes_nothing(self):
        d = cases.pictures()["damaged"]
        out, info = flatten.apply(d, {"merge": False, "edges": False, "min_speck": 0})
        self.assertTrue((out == d).all())
        self.assertEqual(info["pixels_changed"], 0)

    def test_flattening_twice_is_the_same_as_once(self):
        d = cases.pictures()["damaged"]
        once, _ = flatten.apply(d, {})
        twice, _ = flatten.apply(once, {})
        self.assertGreater(close_to(twice, once, 0), 0.99)

    def test_with_a_point_only_that_area_and_its_edge_change(self):
        orig = cases.character_rgba()
        d, _ = cases.damaged(orig, 6, 0.5, 0.0, 3)
        out, info = flatten.apply(d, {"at": (20, 26)})            # the shirt
        shirt = (np.abs(orig[..., :3].astype(int) - (200, 44, 48)).sum(-1) == 0)
        near_shirt = shirt.copy()
        for _ in range(2):
            p = np.pad(near_shirt, 1)
            near_shirt = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
        # everything away from the shirt (the legs, head, ground) is exactly as it was
        changed = (out != d).any(-1)
        self.assertEqual(int((changed & ~_grow(near_shirt, 3)).sum()), 0)
        self.assertGreater(int(changed.sum()), 100)
        # and the shirt itself became one colour
        inner = shirt & _shrink(shirt, 3)
        self.assertEqual(len({tuple(v) for v in out[inner]}), 1)
        self.assertGreater(info["pass1_pixels"], 0)

    def test_the_point_must_be_inside_the_picture(self):
        with self.assertRaisesRegex(ValueError, "outside the picture"):
            flatten.apply(cases.pictures()["sky"], {"at": (500, 1)})

    def test_bad_numbers_are_refused(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 100"):
            flatten.apply(cases.pictures()["sky"], {"tolerance": 120})
        with self.assertRaisesRegex(ValueError, "0 or more"):
            flatten.apply(cases.pictures()["sky"], {"min_speck": -1})

    def test_the_input_is_never_changed_and_one_pixel_works(self):
        d = cases.pictures()["damaged"]
        keep = d.copy()
        flatten.apply(d, {})
        self.assertTrue((d == keep).all())
        out, _ = flatten.apply(cases.solid(1, 1, (1, 2, 3, 255)), {})
        self.assertEqual(tuple(out[0, 0]), (1, 2, 3, 255))

    def test_a_big_picture_is_fast_enough(self):
        img, _ = cases.figure_on_sky(1024, 1024, 5, 1)
        start = time.time()
        flatten.apply(img, {})
        self.assertLess(time.time() - start, 2.0)


def _grow(mask, n):
    for _ in range(n):
        p = np.pad(mask, 1)
        mask = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return mask


def _shrink(mask, n):
    return ~_grow(~mask, n)


class TheGate(unittest.TestCase):
    """Plan section 6, the part that can be tested on drawn pictures: a flat sprite is enlarged, blurred, noised and shrunk
    back with Pixel Snap; flatten must then give the original colours back on at least 97 percent of the pixels, and
    the original number of colours exactly. (The part that needs twenty real pictures is NOT tested here.)"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pixel-snap"))
        try:
            import pixel_snap
            from test_pixel_snap import make_fake
        except Exception as e:  # noqa: BLE001
            raise unittest.SkipTest("Pixel Snap is not importable: " + str(e))
        cls.snap, cls.fake = staticmethod(pixel_snap.snap_image), staticmethod(make_fake)

    def test_flatten_gives_back_the_original_after_pixel_snap(self):
        sprite_rgb = cases.pixel_character()
        orig = cases.character_rgba()
        runs = 0
        for cell, blur, noise, jpeg, seed in itertools.product((8.4, 12.6, 15.1), (1.0, 1.8), (6, 12), (None, 60), (1,)):
            snapped = self.snap(self.fake(sprite_rgb, cell, blur, noise, jpeg, seed)).rgba
            if snapped.shape != orig.shape:
                continue                                 # Pixel Snap found a different size: nothing for flatten to judge
            out, _ = flatten.apply(snapped, {})
            runs += 1
            with self.subTest(cell=cell, blur=blur, noise=noise, jpeg=jpeg, seed=seed):
                self.assertGreaterEqual(close_to(out, orig), 0.97)
                self.assertEqual(core.count_colours(out), len(cases.PAL))
        self.assertGreaterEqual(runs, 20)   # (the sweep is 24 pictures; Pixel Snap takes most of the time)

    def test_flatten_repairs_a_badly_damaged_sprite_a_great_deal(self):
        # a harsher test of our own: half the edge pixels are mixes, plus noise and stray pixels. Exact recovery is not
        # promised here; we check that it gets a lot better and loses almost every stray colour.
        orig = cases.character_rgba()
        for seed in (1, 2, 3):
            damaged, _ = cases.damaged(orig, 6, 0.5, 0.004, seed)
            out, _ = flatten.apply(damaged, {})
            with self.subTest(seed=seed):
                self.assertGreater(close_to(out, orig), close_to(damaged, orig) + 0.02)
                self.assertGreater(close_to(out, orig), 0.87)
                self.assertLess(core.count_colours(out), 0.03 * core.count_colours(damaged))

    def test_pass_two_does_not_hurt_a_clean_sprite_and_the_eyes_survive(self):
        orig = cases.character_rgba()
        out, info = flatten.apply(orig, {})
        self.assertTrue((out == orig).all())
        self.assertEqual(info["pixels_changed"], 0)


class FlattenCommand(unittest.TestCase):
    def test_the_command_reports_the_passes(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "hero.png"
            core.write_png(src, cases.pictures()["damaged"])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = sprite.main(["flatten", str(src), "--json"])
            self.assertEqual(code, 0)
            rec = json.loads(out.getvalue())
            self.assertGreater(rec["colours_before"], 1000)
            self.assertLess(rec["colours_after"], 40)
            self.assertGreater(rec["pass1_pixels"], 0)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                sprite.main(["flatten", str(src), "--no-merge", "--no-edges", "--min-speck", "0", "--brief"])
            self.assertIn("0 changed", out.getvalue())


if __name__ == "__main__":
    unittest.main()

# Tests for viewcheck.py (isometric or orthographic?). Run from this folder: python -m unittest test_view -v
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
import unittest

import numpy as np
from PIL import Image, ImageDraw

import pixel_snap
import viewcheck
from test_pixel_snap import make_fake, scene
from test_subject import iso_building
from test_framing import on_background, plain


def verdict(img):
    return pixel_snap.snap_image(img).view.kind


def round_object(seed, size=96):
    """Barrels, pots, apples: smooth round shapes with a highlight, on a plain ground."""
    rng = np.random.default_rng(seed)
    im = Image.new("RGB", (size, size), (230, 225, 215))
    d = ImageDraw.Draw(im)
    for _ in range(3):
        x, y = int(rng.integers(8, size - 40)), int(rng.integers(8, size - 40))
        a, b = int(rng.integers(16, 34)), int(rng.integers(16, 34))
        base = tuple(int(v) for v in rng.integers(60, 200, 3))
        d.ellipse([x, y, x + a, y + b], fill=base)
        d.ellipse([x + a // 4, y + b // 5, x + a // 2, y + b // 2], fill=tuple(min(255, v + 50) for v in base))
    return im


class ViewTests(unittest.TestCase):
    def test_round_objects_are_never_called_isometric(self):
        for seed in range(8):
            with self.subTest(seed=seed):
                img = make_fake(np.array(round_object(seed)), 9.4, 1.0, 4)
                self.assertNotEqual(verdict(img), "isometric")

    def test_an_isometric_building_on_its_own_is_isometric(self):
        for s, hgt in ((8, 10), (8, 14), (10, 12)):
            with self.subTest(size=s, height=hgt):
                fg, mask = iso_building(s, hgt)
                img = make_fake(on_background(fg, mask, plain((255, 255, 255), mask.shape)), 12.6, 1.0, 4)
                self.assertEqual(verdict(img), "isometric")

    def test_foliage_hiding_some_of_the_lines_does_not_hide_the_view(self):
        for seed in range(4):
            with self.subTest(seed=seed):
                base = Image.fromarray(scene("iso", seed))
                rng = np.random.default_rng(seed + 50)
                d = ImageDraw.Draw(base)
                for _ in range(40):                       # trees and bushes: round, scattered, a fifth of the picture
                    x, y, r = int(rng.integers(0, 120)), int(rng.integers(0, 120)), int(rng.integers(3, 8))
                    g = int(rng.integers(90, 170))
                    d.ellipse([x, y, x + r, y + r], fill=(40, g, 50))
                self.assertEqual(verdict(make_fake(np.array(base), 8.3, 0.9, 4)), "isometric")

    def test_soft_blurry_pictures_with_no_pixel_grid_are_still_judged(self):
        fg, mask = iso_building(8, 14)
        img = make_fake(on_background(fg, mask, plain((255, 255, 255), mask.shape)), 14.0, 5.0, 3)   # very soft
        res = pixel_snap.snap_image(img)
        self.assertEqual(res.view.kind, "isometric")            # whatever the grid-finder made of it

    def test_native_size_pixel_art_is_judged_without_enlarging_it_first(self):
        for seed in range(3):
            with self.subTest(seed=seed):
                rgba = np.dstack([scene("iso", seed), np.full((128, 128), 255, np.uint8)])
                self.assertEqual(viewcheck.classify_view(rgba).kind, "isometric")
                rgba = np.dstack([scene("front", seed), np.full((128, 128), 255, np.uint8)])
                self.assertNotEqual(viewcheck.classify_view(rgba).kind, "isometric")

    def test_a_featureless_picture_is_unclear(self):
        flat = np.dstack([np.full((200, 200, 3), 128, np.uint8), np.full((200, 200), 255, np.uint8)])
        self.assertEqual(viewcheck.classify_view(flat).kind, "unclear")

    def test_front_view_with_two_to_one_roofs_is_not_isometric(self):
        # gable roofs have rising and falling 2:1 slopes too, but also eaves, walls and ground lines
        for seed in range(6):
            with self.subTest(seed=seed):
                self.assertNotEqual(verdict(make_fake(scene("front", seed), 7.4, 0.9, 4)), "isometric")


if __name__ == "__main__":
    unittest.main()

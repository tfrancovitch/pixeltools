# Tests for the grid-finder's graded answers (slice A3): clear / weak / none, non-square pixels.
# Run from this folder: python -m unittest test_grid -v
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

import pixel_snap
from test_framing import figure, on_background, plain
from test_pixel_snap import make_fake, make_sprite


class GradedGridTests(unittest.TestCase):
    def test_clear_grid_is_reported_as_found(self):
        res = pixel_snap.snap_image(make_fake(make_sprite(40, 40), 12.6, 1.0, 5))
        self.assertEqual(res.grid_status, "found")
        self.assertGreaterEqual(res.flatness, 0.9)

    def test_soft_blurry_pixel_art_is_still_snapped(self):
        sprite = make_sprite(72, 72)
        res = pixel_snap.snap_image(make_fake(sprite, 14.3, 3.0, 4))     # enlarged with a heavy blur
        self.assertIn(res.grid_status, ("found", "weak"))
        self.assertEqual(res.size, (72, 72))
        self.assertAlmostEqual(res.px, 14.3, delta=0.5)

    def test_non_square_pixels_are_measured_separately(self):
        # a picture stretched a little more in one direction, as some Midjourney portraits are
        sprite = make_sprite(40, 60)
        res = pixel_snap.snap_image(make_fake(sprite, 12.6, 1.0, 4, cell_y=14.3))
        self.assertEqual(res.grid_status, "found")
        self.assertEqual(res.size, (40, 60))
        self.assertAlmostEqual(res.px, 12.6, delta=0.5)
        self.assertAlmostEqual(res.py, 14.3, delta=0.5)

    def test_narrow_figure_on_a_wide_canvas_with_non_square_pixels(self):
        # like the tall portraits: most of the width is empty, so the width signal is thin
        fg, mask = figure()
        img = make_fake(on_background(fg, mask, plain((255, 255, 255), mask.shape)), 12.6, 1.0, 4, cell_y=14.3)
        res = pixel_snap.snap_image(img)
        self.assertIn(res.grid_status, ("found", "weak"))
        self.assertEqual(res.size, (40, 64))

    def test_a_painted_picture_has_no_grid(self):
        rng = np.random.default_rng(4)
        wash = Image.fromarray(rng.integers(0, 256, (500, 500, 3), dtype=np.uint8)).filter(ImageFilter.GaussianBlur(9))
        res = pixel_snap.snap_image(wash)
        self.assertEqual(res.grid_status, "none")
        self.assertFalse(res.found)
        self.assertIn("pixel size", res.grid_note)

    def test_detailed_texture_inside_blocks_makes_the_grid_weak_or_none(self):
        sprite = make_sprite(40, 40)
        res = pixel_snap.snap_image(make_fake(sprite, 12.6, 1.0, 45))    # heavy texture inside every block
        self.assertNotEqual(res.grid_status, "found")           # weak, or none: never a confident answer

    def test_manual_size_overrides_everything(self):
        wash = Image.fromarray(np.random.default_rng(4).integers(0, 256, (500, 500, 3), dtype=np.uint8)).filter(ImageFilter.GaussianBlur(9))
        res = pixel_snap.snap_image(wash, cell=20)
        self.assertEqual(res.grid_status, "manual")
        self.assertAlmostEqual(res.size[0], 25, delta=1)     # a partial last column may count
        self.assertAlmostEqual(res.size[1], 25, delta=1)

    def test_nothing_is_saved_when_there_is_no_grid(self):
        wash = Image.fromarray(np.random.default_rng(4).integers(0, 256, (500, 500, 3), dtype=np.uint8)).filter(ImageFilter.GaussianBlur(9))
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "painting.png"
            wash.save(src)
            self.assertEqual(pixel_snap.main([str(src)]), 2)
            self.assertFalse((Path(d) / "painting_snapped.png").exists())
            self.assertEqual(pixel_snap.main([str(src), "--cell", "20"]), 0)     # a hand-set size does save
            self.assertTrue((Path(d) / "painting_snapped.png").exists())


if __name__ == "__main__":
    unittest.main()

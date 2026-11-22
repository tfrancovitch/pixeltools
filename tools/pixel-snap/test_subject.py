# Tests for subject.py: character / building / scene. Run from this folder: python -m unittest test_subject -v
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import pixel_snap
from test_framing import figure, on_background, plain
from test_pixel_snap import make_fake, scene


def iso_building(s=8, hgt=14, size=64):
    """An isometric block (2:1 slopes) on its own: a hexagon silhouette with a pointed base.
    Returns the picture's colours and an exact mask of the block."""
    cx, cy = size // 2, size // 2 - (2 * s + hgt) // 2
    faces = [  # (corner points, colour): left wall, right wall, top
        ([(cx - 2 * s, cy + s), (cx, cy + 2 * s), (cx, cy + 2 * s + hgt), (cx - 2 * s, cy + s + hgt)], (150, 40, 40)),
        ([(cx + 2 * s, cy + s), (cx, cy + 2 * s), (cx, cy + 2 * s + hgt), (cx + 2 * s, cy + s + hgt)], (110, 30, 30)),
        ([(cx, cy), (cx + 2 * s, cy + s), (cx, cy + 2 * s), (cx - 2 * s, cy + s)], (190, 60, 60)),
    ]
    colours, mask = Image.new("RGB", (size, size), (0, 0, 0)), Image.new("L", (size, size), 0)
    for points, colour in faces:
        ImageDraw.Draw(colours).polygon(points, fill=colour)
        ImageDraw.Draw(mask).polygon(points, fill=255)
    ImageDraw.Draw(colours).line([(cx - 2 * s + 3, cy + s + 4), (cx - 3, cy + 2 * s + 3)], fill=(240, 220, 120))   # a window sill
    return np.array(colours), np.array(mask) > 0


def subject_of(fg, mask, bg=(255, 255, 255), cell=12.6):
    img = make_fake(on_background(fg, mask, plain(bg, mask.shape)), cell, 1.0, 4)
    return pixel_snap.snap_image(img).subject


class SubjectTests(unittest.TestCase):
    def test_isometric_buildings_are_buildings(self):
        for s, hgt in ((8, 10), (8, 14), (10, 12), (6, 8)):
            for bg in ((255, 255, 255), (90, 160, 90), (20, 20, 40)):
                with self.subTest(size=s, height=hgt, background=bg):
                    fg, mask = iso_building(s, hgt)
                    self.assertEqual(subject_of(fg, mask, bg).kind, "building")

    def test_tall_figures_are_characters(self):
        fg, mask = figure()
        for bg in ((255, 255, 255), (0, 0, 0), (90, 160, 90)):
            with self.subTest(background=bg):
                self.assertEqual(subject_of(fg, mask, bg).kind, "character")

    def test_whole_scenes_are_scenes(self):
        for kind in ("front", "iso"):
            with self.subTest(kind=kind):
                img = make_fake(scene(kind, 1), 8.3, 0.9, 4)
                self.assertEqual(pixel_snap.snap_image(img).subject.kind, "scene")

    def test_a_character_is_never_called_a_building(self):
        fg, mask = figure()
        for cell in (8.3, 12.6, 20.0):
            self.assertNotEqual(subject_of(fg, mask, cell=cell).kind, "building")

    def test_a_nearly_square_figure_is_unclear_not_guessed(self):
        # a chibi character: big head, short body, so it is nearly as wide as tall
        im = Image.new("RGB", (48, 48), (255, 255, 255))
        d = ImageDraw.Draw(im)
        d.ellipse([8, 4, 40, 30], fill=(200, 150, 110))
        d.rectangle([14, 30, 34, 44], fill=(180, 40, 40))
        d.rectangle([14, 44, 22, 47], fill=(40, 40, 120))
        d.rectangle([26, 44, 34, 47], fill=(40, 40, 120))
        for y in (8, 12, 16, 20, 24):
            d.line([(10, y), (38, y)], fill=(180, 120, 80))
        arr = np.array(im)
        mask = (arr != 255).any(axis=2)
        self.assertEqual(subject_of(arr, mask).kind, "unclear")

    def test_a_flat_based_box_is_unclear_for_now(self):
        # a front-view house: documented limit until batch 2 gives real examples
        im = Image.new("RGB", (64, 64), (255, 255, 255))
        d = ImageDraw.Draw(im)
        d.rectangle([12, 28, 52, 58], fill=(180, 120, 80))
        d.polygon([(8, 28), (56, 28), (32, 8)], fill=(150, 50, 50))
        d.rectangle([28, 44, 36, 58], fill=(70, 40, 30))
        for y in (32, 36, 40, 50, 54):
            d.line([(12, y), (52, y)], fill=(160, 100, 60))
        arr = np.array(im)
        self.assertEqual(subject_of(arr, (arr != 255).any(axis=2)).kind, "unclear")

    def test_command_line_report_starts_with_what_it_is(self):
        fg, mask = figure()
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "hero.png"
            make_fake(on_background(fg, mask, plain((255, 255, 255), mask.shape)), 12.6, 1.0, 4).save(src)
            import contextlib, io
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(pixel_snap.main([str(src), "--check-only"]), 0)
            self.assertTrue(buf.getvalue().startswith("[CHARACTER]"), buf.getvalue())
            self.assertIn("facing: not checked yet", buf.getvalue())


if __name__ == "__main__":
    unittest.main()

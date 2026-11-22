# Tests for pixel_snap.py. Run from this folder:  python -m unittest -v
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
import io
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

import pixel_snap

PALETTE = np.array([[200, 40, 40], [30, 30, 60], [240, 220, 180], [60, 140, 90],
                    [90, 160, 220], [250, 200, 40], [120, 80, 50], [255, 255, 255]], dtype=np.uint8)


def make_sprite(cols, rows, seed=7):
    """A blobby sprite with flat regions, a few colours, and hard edges."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:rows, 0:cols]
    k = np.floor((np.sin(x * 0.7) + np.cos(y * 0.5) + rng.random((rows, cols)) * 1.2) * 1.6 + 4).astype(int)
    return PALETTE[k % 8]


def make_fake(sprite, cell, blur=1.0, noise=5, jpeg=None, seed=1):
    """Enlarge a sprite by a non-whole factor, soften the edges, add noise, maybe JPEG it."""
    rows, cols = sprite.shape[:2]
    size = (round(cols * cell), round(rows * cell))
    img = Image.fromarray(sprite, "RGB").resize(size, Image.NEAREST)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    arr = np.array(img).astype(np.float64)
    if noise:
        arr += np.random.default_rng(seed).uniform(-noise, noise, arr.shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    if jpeg:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=jpeg)
        img = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    return img


def wrong_cells(res, sprite, tol=40):
    got = res.rgba[..., :3].astype(int)
    return int((np.abs(got - sprite.astype(int)).sum(axis=2) > tol).sum())


class SnapTests(unittest.TestCase):
    CASES = [  # (cols, rows, cell, blur, noise, jpeg)
        (32, 32, 12.4, 1.2, 6, None),
        (64, 64, 9.3, 1.0, 8, None),
        (67, 45, 15.7, 1.5, 5, None),   # odd, non-square sprite
        (40, 40, 20.0, 0.8, 4, 90),     # lightly JPEG-damaged
        (24, 24, 31.6, 2.0, 10, 90),
        (16, 16, 64.0, 2.0, 3, None),   # very large cells
        (48, 48, 8.0, 0, 0, None),      # clean whole-number case
    ]

    def test_recovers_exact_sprite(self):
        for cols, rows, cell, blur, noise, jpeg in self.CASES:
            with self.subTest(sprite=f"{cols}x{rows}", cell=cell):
                sprite = make_sprite(cols, rows)
                res = pixel_snap.snap_image(make_fake(sprite, cell, blur, noise, jpeg))
                self.assertEqual(res.size, (cols, rows))
                self.assertEqual(wrong_cells(res, sprite), 0)
                self.assertAlmostEqual(res.px, cell, delta=0.15)
                self.assertAlmostEqual(res.py, cell, delta=0.15)

    def test_real_world_shapes(self):
        """Shapes seen in real Midjourney output: many small cells, heavy JPEG, tall narrow
        sprites. A first version of the detector failed these. Only the size is checked,
        because heavy JPEG at small cells smears some colours."""
        for cols, rows, cell, blur, noise, jpeg in [(160, 160, 6.4, 0.8, 3, None),
                                                    (200, 200, 5.12, 0.7, 2, 75),
                                                    (40, 88, 12.4, 2.0, 4, 70)]:
            with self.subTest(sprite=f"{cols}x{rows}", cell=cell, jpeg=jpeg):
                res = pixel_snap.snap_image(make_fake(make_sprite(cols, rows), cell, blur, noise, jpeg))
                self.assertTrue(res.found)
                self.assertAlmostEqual(res.px, cell, delta=0.1 * cell)
                self.assertAlmostEqual(res.size[0], cols, delta=1)
                self.assertAlmostEqual(res.size[1], rows, delta=1)

    def test_noise_is_merged_into_flat_colours(self):
        sprite = make_sprite(32, 32)
        res = pixel_snap.snap_image(make_fake(sprite, 12.4, 1.2, 6))
        self.assertLessEqual(res.colours, len(np.unique(sprite.reshape(-1, 3), axis=0)))

    def test_colour_limit(self):
        res = pixel_snap.snap_image(make_fake(make_sprite(32, 32), 12.4, 1.2, 6), colours=4)
        self.assertLessEqual(res.colours, 4)

    def test_manual_cell_size(self):
        sprite = make_sprite(32, 32)
        res = pixel_snap.snap_image(make_fake(sprite, 12.4, 1.2, 6), cell=12.4)
        self.assertEqual(res.size, (32, 32))
        self.assertEqual(wrong_cells(res, sprite), 0)

    def test_pure_noise_has_no_grid(self):
        for size in (120, 200, 400, 1024):
            for seed in range(5):
                with self.subTest(size=size, seed=seed):
                    rng = np.random.default_rng(100 + seed)
                    img = Image.fromarray(rng.integers(0, 256, (size, size, 3), dtype=np.uint8), "RGB")
                    self.assertFalse(pixel_snap.snap_image(img).found)

    def test_transparency_is_kept(self):
        sprite = make_sprite(20, 20)
        rgba = np.dstack([sprite, np.full((20, 20), 255, np.uint8)])
        rgba[:5, :5, 3] = 0
        img = Image.fromarray(rgba, "RGBA").resize((250, 250), Image.NEAREST)
        res = pixel_snap.snap_image(img)
        self.assertEqual(res.size, (20, 20))
        self.assertTrue((res.rgba[:5, :5, 3] == 0).all())
        self.assertTrue((res.rgba[6:, 6:, 3] == 255).all())

    def test_command_line(self):
        sprite = make_sprite(32, 32)
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "pic.png"
            make_fake(sprite, 12.4, 1.2, 6).save(src)
            self.assertEqual(pixel_snap.main([str(src), "--scale", "4"]), 0)
            with Image.open(Path(d) / "pic_snapped.png") as out:
                self.assertEqual(out.size, (128, 128))


if __name__ == "__main__":
    unittest.main()

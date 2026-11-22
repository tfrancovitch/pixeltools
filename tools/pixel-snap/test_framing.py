# Tests for framing.py and the transparent-background option. Run from this folder: python -m unittest -v
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import framing as F
import pixel_snap
from test_pixel_snap import make_fake, scene


def figure(cols=40, rows=64, hole=False, patch=None):
    """A drawn figure as (foreground colours, mask). The mask is exact: pixels that are the figure."""
    def draw(bg):
        im = Image.new("RGB", (cols, rows), bg)
        d = ImageDraw.Draw(im)
        d.ellipse([14, 4, 26, 16], fill=(200, 150, 110))
        d.rectangle([12, 17, 28, 40], fill=(180, 40, 40))
        d.rectangle([13, 41, 19, 60], fill=(40, 40, 120))
        d.rectangle([21, 41, 27, 60], fill=(40, 40, 120))
        # detail, as in real sprites: a plain flat figure has too few edges for the grid-finder
        # to find its rhythm (a known limit, slice A3 of the plan)
        for y in (19, 22, 27, 31, 35, 38):
            d.line([(12, y), (28, y)], fill=(230, 200, 60))
        for y in (44, 47, 52, 55, 58):
            d.line([(13, y), (19, y)], fill=(220, 220, 220))
            d.line([(21, y), (27, y)], fill=(220, 220, 220))
        for x in (15, 20, 25):
            d.line([(x, 17), (x, 40)], fill=(90, 20, 20))
        d.point([(18, 9), (22, 9), (20, 12)], fill=(30, 30, 30))
        d.rectangle([14, 4, 26, 6], fill=(70, 40, 20))
        if hole:
            d.rectangle([16, 22, 24, 30], fill=bg)      # the same colour as the background, fully enclosed
        if patch:
            d.rectangle([16, 22, 24, 30], fill=patch)
        return np.array(im)
    a, b = draw((0, 0, 0)), draw((255, 255, 255))
    mask = (a == b).all(axis=2)          # the same on black and on white = the figure itself
    return draw((0, 0, 0)), mask


def on_background(fg, mask, bg_array):
    out = bg_array.copy()
    out[mask] = fg[mask]
    return out


def plain(colour, shape):
    return np.full(shape + (3,), colour, dtype=np.uint8)


def gradient(shape, top, bottom):
    rows, cols = shape
    t = np.linspace(0, 1, rows)[:, None, None]
    return (np.array(top) * (1 - t) + np.array(bottom) * t).repeat(cols, axis=1).astype(np.uint8)


def iou(framing, truth):
    m = framing.mask
    t = np.array(Image.fromarray(truth.astype(np.uint8) * 255).resize((m.shape[1], m.shape[0]), Image.NEAREST)) > 127
    return (m & t).sum() / max(1, (m | t).sum())


class FramingTests(unittest.TestCase):
    def backgrounds(self, shape):
        return {
            "white": plain((255, 255, 255), shape),
            "black": plain((0, 0, 0), shape),
            "green": plain((90, 160, 90), shape),
            "sky gradient": gradient(shape, (170, 200, 235), (225, 235, 250)),
            "dark gradient": gradient(shape, (10, 10, 30), (60, 50, 70)),
        }

    def test_lone_sprites_are_isolated_and_the_mask_matches(self):
        fg, mask = figure()
        for name, bg in self.backgrounds(mask.shape).items():
            for blur, noise, jpeg in ((0.0, 0, None), (1.0, 5, None), (0.9, 4, 70)):
                with self.subTest(background=name, blur=blur, noise=noise, jpeg=jpeg):
                    img = make_fake(on_background(fg, mask, bg), 12.6, blur, noise, jpeg)
                    f = F.classify_framing(np.array(img.convert("RGBA")))
                    self.assertEqual(f.kind, "isolated")
                    self.assertGreaterEqual(f.border_uniform, 0.9)
                    self.assertGreaterEqual(iou(f, mask), 0.85)

    def test_sprite_touching_the_edge_is_still_isolated(self):
        fg, mask = figure(rows=62)               # feet reach the bottom edge of the picture
        bg = plain((255, 255, 255), mask.shape)
        f = F.classify_framing(np.array(make_fake(on_background(fg, mask, bg), 12.6, 1.0, 4).convert("RGBA")))
        self.assertEqual(f.kind, "isolated")

    def test_full_scenes_are_scenes(self):
        for kind in ("front", "iso"):
            for seed in range(3):
                with self.subTest(kind=kind, seed=seed):
                    img = make_fake(scene(kind, seed), 8.3, 0.9, 4)
                    self.assertEqual(F.classify_framing(np.array(img.convert("RGBA"))).kind, "scene")

    def test_textured_full_bleed_picture_is_a_scene(self):
        rng = np.random.default_rng(2)
        tiles = rng.integers(0, 255, (16, 16, 3), dtype=np.uint8)
        img = Image.fromarray(tiles).resize((512, 512), Image.NEAREST)
        self.assertEqual(F.classify_framing(np.array(img.convert("RGBA"))).kind, "scene")

    def test_background_estimate_handles_a_gradient(self):
        fg, mask = figure()
        bg = gradient(mask.shape, (170, 200, 235), (225, 235, 250))
        rgba = np.array(Image.fromarray(on_background(fg, mask, bg)).resize((400, 640), Image.NEAREST).convert("RGBA"))
        field = F.estimate_background(rgba).field(*rgba.shape[:2])
        want = np.array(Image.fromarray(bg).resize((400, 640), Image.NEAREST)).astype(float)
        self.assertLess(np.abs(field[:20] - want[:20]).mean(), 3)      # near the top
        self.assertLess(np.abs(field[-20:] - want[-20:]).mean(), 3)    # near the bottom


class TransparentTests(unittest.TestCase):
    def snap(self, fg, mask, bg, transparent=True):
        img = make_fake(on_background(fg, mask, bg), 12.6, 1.0, 4)
        return pixel_snap.snap_image(img, transparent=transparent)

    def test_background_becomes_transparent_and_the_sprite_stays_opaque(self):
        fg, mask = figure()
        for name, bg in (("white", plain((255, 255, 255), mask.shape)), ("green", plain((90, 160, 90), mask.shape)),
                         ("gradient", gradient(mask.shape, (170, 200, 235), (225, 235, 250)))):
            with self.subTest(background=name):
                res = self.snap(fg, mask, bg)
                self.assertTrue(res.transparent)
                alpha = res.rgba[..., 3] > 0
                self.assertEqual(res.size, (40, 64))
                self.assertEqual(int(res.rgba[0, 0, 3]), 0)                       # a corner is background
                self.assertGreaterEqual((alpha & mask).sum() / mask.sum(), 0.97)  # the sprite is kept
                self.assertLessEqual((alpha & ~mask).sum() / (~mask).sum(), 0.05)  # the background is gone

    def test_enclosed_background_coloured_patches_are_kept(self):
        fg, mask = figure(hole=True)                 # a hole in the sprite, the same colour as the background
        res = self.snap(fg, mask, plain((255, 255, 255), mask.shape))
        self.assertEqual(int(res.rgba[26, 20, 3]), 255)    # inside the body: kept, not punched out
        fg, mask = figure(patch=(255, 255, 255))     # a white patch on the shirt
        res = self.snap(fg, mask, plain((255, 255, 255), mask.shape))
        self.assertEqual(int(res.rgba[26, 20, 3]), 255)

    def test_scenes_are_left_alone(self):
        img = make_fake(scene("iso", 1), 8.3, 0.9, 4)
        res = pixel_snap.snap_image(img, transparent=True)
        self.assertFalse(res.transparent)
        self.assertTrue((res.rgba[..., 3] == 255).all())

    def test_command_line_option(self):
        fg, mask = figure()
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "hero.png"
            make_fake(on_background(fg, mask, plain((255, 255, 255), mask.shape)), 12.6, 1.0, 4).save(src)
            self.assertEqual(pixel_snap.main([str(src), "--transparent"]), 0)
            with Image.open(Path(d) / "hero_snapped.png") as out:
                self.assertEqual(out.mode, "RGBA")
                self.assertEqual(out.getpixel((0, 0))[3], 0)


if __name__ == "__main__":
    unittest.main()

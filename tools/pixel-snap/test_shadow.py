# Tests for shadow.py (slice D1): finding the ground shadow under a lone sprite.
# Run from this folder: python -m unittest test_shadow -v
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
import unittest

import numpy as np
from PIL import Image, ImageDraw

import pixel_snap
from test_framing import figure
from test_pixel_snap import make_fake

W, H = 64, 76          # picture size in sprite pixels; the figure stands at x offset 12 with its feet at row 60


def compose(ground, shadow_kind, factor=0.65, texture=0.0, seed=0):
    """A drawn figure on a ground, with an optional drawn shadow. Returns (picture, sprite mask, shadow mask).
    The shadow is the ground colour times `factor`: a real, flat, darker copy of the ground."""
    fg, mask = figure(cols=40, rows=H)
    pic = np.zeros((H, W, 3), np.uint8)
    pic[:] = ground
    if texture:
        rng = np.random.default_rng(seed)
        pic = np.clip(pic * (1 + rng.uniform(-texture, texture, (H, W, 1))), 0, 255).astype(np.uint8)
    sprite = np.zeros((H, W), bool)
    sprite[:, 12:52] = mask
    sh = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(sh)
    if shadow_kind == "contact":                        # an oval under the feet
        d.ellipse([14, 57, 50, 67], fill=255)
    elif shadow_kind == "cast_left":                    # falls to the lower left
        d.polygon([(24, 58), (40, 58), (14, 70), (2, 66)], fill=255)
    elif shadow_kind == "cast_right":
        d.polygon([(24, 58), (40, 58), (62, 66), (50, 71)], fill=255)
    shadow = (np.array(sh) > 0) & ~sprite
    out = pic.copy()
    out[shadow] = np.clip(pic[shadow] * factor, 0, 255).astype(np.uint8)
    full = np.zeros_like(out)
    full[:, 12:52] = fg
    out[sprite] = full[sprite]
    return out, sprite, shadow


def overlap(found, truth):
    """(recall of the true shadow, precision of what was found) on the detector's coarse grid."""
    m = found.mask
    t = np.array(Image.fromarray(truth.astype(np.uint8) * 255).resize((m.shape[1], m.shape[0]), Image.BILINEAR)) > 100
    recall = (m & t).sum() / max(1, t.sum())
    near = np.array(Image.fromarray(truth.astype(np.uint8) * 255).resize((m.shape[1], m.shape[0]), Image.BILINEAR)) > 10
    precision = (m & near).sum() / max(1, m.sum())
    return recall, precision


GROUNDS = {"green": (90, 160, 90), "sky blue": (120, 180, 230), "sand": (230, 195, 110), "mid grey": (140, 140, 150)}


class ShadowTests(unittest.TestCase):
    def snap(self, picture, cell=11.6):
        return pixel_snap.snap_image(make_fake(picture, cell, 1.0, 4))

    def test_shadows_are_found_and_match_the_drawn_shadow(self):
        for gname, ground in GROUNDS.items():
            for kind in ("contact", "cast_left", "cast_right"):
                for factor in (0.55, 0.7, 0.8):
                    with self.subTest(ground=gname, shadow=kind, darkness=factor):
                        pic, sprite, shadow = compose(ground, kind, factor)
                        res = self.snap(pic)
                        self.assertTrue(res.shadow.found, res.shadow.reason)
                        recall, precision = overlap(res.shadow, shadow)
                        self.assertGreaterEqual(recall, 0.8)
                        self.assertGreaterEqual(precision, 0.9)
                        self.assertAlmostEqual(res.shadow.darkness, factor, delta=0.1)

    def test_shadow_direction_is_reported(self):
        left = self.snap(compose(GROUNDS["green"], "cast_left")[0]).shadow
        right = self.snap(compose(GROUNDS["green"], "cast_right")[0]).shadow
        contact = self.snap(compose(GROUNDS["green"], "contact")[0]).shadow
        self.assertLess(left.dx, -0.15)
        self.assertGreater(right.dx, 0.15)
        self.assertLess(abs(contact.dx), 0.15)

    def test_a_gradient_ground_and_mild_texture_are_fine(self):
        pic, sprite, shadow = compose(GROUNDS["green"], "cast_left", 0.65, texture=0.05)
        res = self.snap(pic)
        self.assertTrue(res.shadow.found, res.shadow.reason)
        t = np.linspace(0, 1, H)[:, None, None]
        grad = (np.array([100, 170, 100]) * (1 - t) + np.array([60, 120, 70]) * t).repeat(W, axis=1)
        pic, sprite, shadow = compose((0, 0, 0), "contact")
        base, _, _ = compose((0, 0, 0), "none")
        # ground gradient with a multiplicative shadow, the figure on top
        g = np.clip(grad, 0, 255)
        out = g.copy()
        out[shadow] = g[shadow] * 0.65
        out[sprite] = pic[sprite]
        res = self.snap(out.astype(np.uint8))
        self.assertTrue(res.shadow.found, res.shadow.reason)

    def test_no_shadow_means_none(self):
        for gname, ground in GROUNDS.items():
            with self.subTest(ground=gname):
                res = self.snap(compose(ground, "none")[0])
                self.assertFalse(res.shadow.found)
                self.assertFalse(res.shadow.unsure)

    def test_the_sprites_own_shading_is_never_taken_for_shadow(self):
        for gname, ground in GROUNDS.items():
            for kind in ("none", "contact", "cast_left"):
                with self.subTest(ground=gname, shadow=kind):
                    pic, sprite, shadow = compose(ground, kind)
                    res = self.snap(pic)
                    if res.shadow.found:
                        m = res.shadow.mask
                        s_small = np.array(Image.fromarray(sprite.astype(np.uint8) * 255).resize((m.shape[1], m.shape[0]), Image.BILINEAR)) > 200
                        self.assertLess((m & s_small).sum() / max(1, m.sum()), 0.1)   # almost none of it is on the sprite proper

    def test_a_white_ground_says_cant_tell(self):
        res = self.snap(compose((255, 255, 255), "contact", 0.8)[0])
        self.assertTrue(res.shadow.unsure)
        self.assertFalse(res.shadow.found)

    def test_scenes_have_no_separate_shadow(self):
        from test_pixel_snap import scene
        res = pixel_snap.snap_image(make_fake(scene("iso", 1), 8.3, 0.9, 4))
        self.assertFalse(res.shadow.found)


if __name__ == "__main__":
    unittest.main()

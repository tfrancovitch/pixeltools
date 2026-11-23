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


class ContactOrCastTests(unittest.TestCase):
    def snap(self, picture, **kw):
        return pixel_snap.snap_image(make_fake(picture, 11.6, 1.0, 4), **kw)

    def test_contact_and_cast_shadows_are_told_apart(self):
        for gname, ground in GROUNDS.items():
            for factor in (0.55, 0.7, 0.8):
                with self.subTest(ground=gname, darkness=factor):
                    self.assertEqual(self.snap(compose(ground, "contact", factor)[0]).shadow.kind, "contact")
                    self.assertEqual(self.snap(compose(ground, "cast_left", factor)[0]).shadow.kind, "cast")
                    self.assertEqual(self.snap(compose(ground, "cast_right", factor)[0]).shadow.kind, "cast")


class RemovalTests(unittest.TestCase):
    def pair(self, ground, kind, factor, mode, **kw):
        """(kept, removed, sprite mask, shadow mask, the same picture drawn without any shadow). The first two
        share one grid analysis, so they differ only by what shadow removal did."""
        pic, sprite, shadow = compose(ground, kind, factor)
        rgba = np.array(make_fake(pic, 11.6, 1.0, 4).convert("RGBA"))
        an = pixel_snap.analyse(rgba)
        clean = pixel_snap.snap_image(make_fake(compose(ground, "none", factor)[0], 11.6, 1.0, 4))
        return (pixel_snap.rebuild(rgba, an), pixel_snap.rebuild(rgba, an, shadows=mode, **kw), sprite, shadow, clean)

    @staticmethod
    def grown(mask):
        g = mask.copy()
        g[1:] |= mask[:-1]; g[:-1] |= mask[1:]; g[:, 1:] |= mask[:, :-1]; g[:, :-1] |= mask[:, 1:]
        return g

    def test_removal_changes_only_the_shadow_and_never_the_sprite(self):
        for gname, ground in GROUNDS.items():
            for kind in ("contact", "cast_left", "cast_right"):
                for factor in (0.55, 0.8):
                    with self.subTest(ground=gname, shadow=kind, darkness=factor):
                        keep, gone, sprite, shadow, clean = self.pair(ground, kind, factor, "remove-all")
                        self.assertEqual(keep.size, (W, H))
                        changed = (keep.rgba != gone.rgba).any(axis=2)
                        self.assertFalse((changed & sprite).any(), "a sprite pixel was changed")
                        self.assertTrue(not (changed & ~self.grown(shadow)).any(), "something outside the shadow was changed")
                        self.assertGreaterEqual((changed & shadow).sum() / shadow.sum(), 0.85)     # the shadow is gone
                        # the result looks like the same picture drawn without any shadow
                        off = (np.abs(gone.rgba[..., :3].astype(int) - clean.rgba[..., :3].astype(int)).sum(axis=2) > 30)
                        self.assertLess(off.mean(), 0.03)

    def test_remove_cast_keeps_a_contact_shadow(self):
        keep, gone, _, _, _ = self.pair(GROUNDS["green"], "contact", 0.7, "remove-cast")
        self.assertTrue((keep.rgba == gone.rgba).all())
        self.assertEqual(gone.shadow_removed, 0)
        keep, gone, _, shadow, _ = self.pair(GROUNDS["green"], "cast_left", 0.7, "remove-cast")
        self.assertGreater(gone.shadow_removed, 0)

    def test_keep_changes_nothing(self):
        keep, gone, _, _, _ = self.pair(GROUNDS["sand"], "cast_right", 0.7, "keep")
        self.assertTrue((keep.rgba == gone.rgba).all())

    def test_a_removed_shadow_is_transparent_when_the_background_is_too(self):
        keep, gone, sprite, shadow, _ = self.pair(GROUNDS["green"], "cast_left", 0.7, "remove-all", transparent=True)
        self.assertTrue(gone.transparent)
        inner = shadow & ~self.grown(sprite)
        self.assertGreaterEqual((gone.rgba[..., 3][inner] == 0).mean(), 0.9)          # the shadow went transparent with the ground
        self.assertTrue((gone.rgba[..., 3][sprite & ~self.grown(~sprite)] == 255).all())   # the sprite's inside stayed opaque

    def test_a_white_ground_is_left_alone(self):
        pic = compose((255, 255, 255), "cast_left", 0.8)[0]
        img = make_fake(pic, 11.6, 1.0, 4)
        a, b = pixel_snap.snap_image(img), pixel_snap.snap_image(img, shadows="remove-all")
        self.assertTrue((a.rgba == b.rgba).all())

    def test_scenes_are_left_alone(self):
        from test_pixel_snap import scene
        img = make_fake(scene("iso", 1), 8.3, 0.9, 4)
        a, b = pixel_snap.snap_image(img), pixel_snap.snap_image(img, shadows="remove-all")
        self.assertTrue((a.rgba == b.rgba).all())

    def test_command_line_option(self):
        import contextlib, io, tempfile
        from pathlib import Path
        pic = compose(GROUNDS["green"], "cast_left", 0.7)[0]
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "hero.png"
            make_fake(pic, 11.6, 1.0, 4).save(src)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(pixel_snap.main([str(src), "--shadows", "remove-cast", "-o", str(Path(d) / "out.png")]), 0)
            self.assertIn("cast shadow", buf.getvalue())
            self.assertIn("shadow removed", buf.getvalue())


if __name__ == "__main__":
    unittest.main()

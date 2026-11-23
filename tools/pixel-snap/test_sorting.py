# Tests for sorting.py and the --sort / --want-view / --want-facing options (slice C3).
# Run from this folder: python -m unittest test_sorting -v
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image, ImageFilter

import pixel_snap
import sorting
from test_framing import figure, on_background, plain
from test_pixel_snap import make_fake, scene
from test_subject import iso_building


def stub(grid="found", subject="building", view="isometric", facing=None):
    r = SimpleNamespace(grid_status=grid, grid_note="no usable grid", subject=SimpleNamespace(kind=subject),
                        view=SimpleNamespace(kind=view))
    if facing is not None:
        r.facing = SimpleNamespace(kind=facing)
    return r


class DecisionTable(unittest.TestCase):
    def test_no_grid_is_not_pixel_art_whatever_is_wanted(self):
        for wv in sorting.WANT_VIEW:
            for wf in sorting.WANT_FACING:
                self.assertEqual(sorting.decide(stub(grid="none"), wv, wf).bucket, "not-pixel-art")

    def test_view_wanted_for_buildings_objects_and_scenes(self):
        for subject in ("building", "scene", "unclear"):
            for seen, want, bucket in (("isometric", "isometric", "matches"), ("orthogonal", "orthogonal", "matches"),
                                       ("isometric", "orthogonal", "mismatches"), ("orthogonal", "isometric", "mismatches"),
                                       ("unclear", "orthogonal", "cant-tell"), ("unclear", "isometric", "cant-tell"),
                                       ("isometric", "either", "matches"), ("unclear", "either", "matches")):
                with self.subTest(subject=subject, seen=seen, want=want):
                    self.assertEqual(sorting.decide(stub(subject=subject, view=seen), want).bucket, bucket)

    def test_characters_ignore_the_view_setting(self):
        for want in sorting.WANT_VIEW:
            self.assertEqual(sorting.decide(stub(subject="character", view="isometric"), want, "either").bucket, "matches")

    def test_characters_need_the_facing_check_when_a_facing_is_wanted(self):
        # the facing check is not built yet: a wanted facing can only be "can't tell"
        self.assertEqual(sorting.decide(stub(subject="character"), "either", "diagonal").bucket, "cant-tell")
        self.assertEqual(sorting.decide(stub(subject="character", facing="unclear"), "either", "cardinal").bucket, "cant-tell")
        # once a facing rule exists, the same table applies
        for seen, want, bucket in (("diagonal", "diagonal", "matches"), ("cardinal", "diagonal", "mismatches"),
                                   ("cardinal", "cardinal", "matches"), ("mixed", "diagonal", "cant-tell"),
                                   ("unclear", "cardinal", "cant-tell")):
            with self.subTest(seen=seen, want=want):
                self.assertEqual(sorting.decide(stub(subject="character", facing=seen), "either", want).bucket, bucket)

    def test_the_two_settings_are_independent(self):
        # an orthographic world with diagonal-facing characters: each setting only judges its own kind of picture
        char, house = stub(subject="character", facing="diagonal"), stub(subject="building", view="orthogonal")
        self.assertEqual(sorting.decide(char, "orthogonal", "diagonal").bucket, "matches")
        self.assertEqual(sorting.decide(house, "orthogonal", "diagonal").bucket, "matches")
        self.assertEqual(sorting.decide(stub(subject="building", view="isometric"), "orthogonal", "diagonal").bucket, "mismatches")

    def test_a_weak_grid_is_flagged_but_still_sorted_by_its_view(self):
        d = sorting.decide(stub(grid="weak", view="orthogonal"), "orthogonal")
        self.assertEqual((d.bucket, d.weak), ("matches", True))
        self.assertEqual(sorting.decide(stub(grid="weak", view="isometric"), "orthogonal").bucket, "mismatches")


def make_batch(folder: Path):
    """Four drawn pictures: a character, an isometric building, a front-view scene, a painting with no grid."""
    fg, mask = figure()
    make_fake(on_background(fg, mask, plain((255, 255, 255), mask.shape)), 12.6, 1.0, 4).save(folder / "hero.png")
    fg, mask = iso_building(8, 14)
    make_fake(on_background(fg, mask, plain((255, 255, 255), mask.shape)), 12.6, 1.0, 4).save(folder / "house_iso.png")
    make_fake(scene("front", 2), 8.3, 0.9, 4).save(folder / "village_front.png")
    wash = Image.fromarray(np.random.default_rng(4).integers(0, 256, (500, 500, 3), dtype=np.uint8)).filter(ImageFilter.GaussianBlur(9))
    wash.save(folder / "painting.png")
    return sorted(folder.glob("*.png"))


def rows_by_file(root: Path):
    with open(root / "report.csv", newline="", encoding="utf-8") as f:
        return {Path(r["file"]).name: r for r in csv.DictReader(f)}


class SortRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.src = Path(cls.tmp.name) / "in"
        cls.src.mkdir()
        cls.files = make_batch(cls.src)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_sort(self, name, *extra):
        out = Path(self.tmp.name) / name
        self.assertEqual(pixel_snap.main([*map(str, self.files), "--sort", str(out), *extra]), 0)
        return out

    def test_wanting_orthogonal(self):
        out = self.run_sort("ortho", "--want-view", "orthogonal")
        rows = rows_by_file(out)
        self.assertEqual({k: v["folder"] for k, v in rows.items()},
                         {"hero.png": "matches", "house_iso.png": "mismatches", "village_front.png": "matches", "painting.png": "not-pixel-art"})
        self.assertEqual(sorted(p.name for p in (out / "matches").iterdir()), ["hero_snapped.png", "village_front_snapped.png"])
        self.assertEqual([p.name for p in (out / "mismatches").iterdir()], ["house_iso.png"])     # a copy of the original
        self.assertEqual([p.name for p in (out / "not-pixel-art").iterdir()], ["painting.png"])
        self.assertEqual(list((out / "cant-tell").iterdir()), [])
        with Image.open(out / "mismatches" / "house_iso.png") as copy, Image.open(self.src / "house_iso.png") as original:
            self.assertEqual(copy.size, original.size)

    def test_wanting_isometric_reverses_the_buildings_and_scenes(self):
        rows = rows_by_file(self.run_sort("iso", "--want-view", "isometric"))
        self.assertEqual(rows["house_iso.png"]["folder"], "matches")
        self.assertEqual(rows["village_front.png"]["folder"], "mismatches")
        self.assertEqual(rows["hero.png"]["folder"], "matches")          # the view setting does not apply to characters

    def test_wanting_a_facing_puts_characters_in_cant_tell_while_the_tool_cannot_judge_it(self):
        rows = rows_by_file(self.run_sort("facing", "--want-facing", "diagonal"))
        self.assertEqual(rows["hero.png"]["folder"], "cant-tell")
        self.assertIn("cannot judge facing yet", rows["hero.png"]["reason"])
        self.assertEqual(rows["house_iso.png"]["folder"], "matches")      # no view was asked for

    def test_the_report_has_every_measurement(self):
        rows = rows_by_file(self.run_sort("report"))
        for r in rows.values():
            self.assertEqual(list(r.keys()), sorting.REPORT_COLUMNS)
        hero = rows["hero.png"]
        self.assertEqual((hero["subject"], hero["view"], hero["grid"]), ("character", "n/a (character)", "found"))
        self.assertEqual((hero["sprite_w"], hero["sprite_h"]), ("40", "64"))
        self.assertEqual(rows["house_iso.png"]["view"], "isometric")
        self.assertEqual(rows["painting.png"]["grid"], "none")
        self.assertTrue((Path(self.tmp.name) / "report" / hero["saved_as"]).exists())

    def test_check_only_writes_a_report_and_nothing_else(self):
        out = self.run_sort("check", "--want-view", "orthogonal", "--check-only")
        self.assertEqual([p.name for p in out.iterdir()], ["report.csv"])
        self.assertEqual(rows_by_file(out)["house_iso.png"]["folder"], "mismatches")

    def test_pictures_with_the_same_name_from_different_folders_are_both_kept(self):
        other = Path(self.tmp.name) / "other"
        other.mkdir(exist_ok=True)
        Image.open(self.src / "hero.png").save(other / "hero.png")
        out = Path(self.tmp.name) / "twins"
        pixel_snap.main([str(self.src / "hero.png"), str(other / "hero.png"), "--sort", str(out)])
        self.assertEqual(sorted(p.name for p in (out / "matches").iterdir()), ["hero_snapped-2.png", "hero_snapped.png"])

    def test_options_still_apply_to_the_saved_sprites(self):
        out = self.run_sort("scaled", "--scale", "4", "--transparent")
        with Image.open(out / "matches" / "hero_snapped.png") as im:
            self.assertEqual(im.size, (160, 256))
            self.assertEqual(im.mode, "RGBA")
            self.assertEqual(im.getpixel((0, 0))[3], 0)


if __name__ == "__main__":
    unittest.main()

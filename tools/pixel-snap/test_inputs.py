# Tests for odd inputs and the command-line extras: tiny pictures, 16-bit and rotated photos, --jobs, --version.
# Run from this folder: python -m unittest test_inputs -v
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

import pixel_snap
from test_pixel_snap import make_fake, make_sprite


class OddInputTests(unittest.TestCase):
    def test_a_tiny_picture_is_refused_clearly_and_quickly(self):
        for size in ((1, 1), (3, 3), (15, 40)):
            with self.subTest(size=size):
                with self.assertRaisesRegex(ValueError, "too small to analyse"):
                    pixel_snap.snap_image(Image.new("RGB", size, (200, 50, 50)))

    def test_the_command_line_reports_a_tiny_picture_and_carries_on(self):
        with tempfile.TemporaryDirectory() as d:
            tiny, ok = Path(d) / "tiny.png", Path(d) / "ok.png"
            Image.new("RGB", (3, 3)).save(tiny)
            make_fake(make_sprite(32, 32), 12.4, 1.2, 6).save(ok)
            err, out = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                code = pixel_snap.main([str(tiny), str(ok), "--brief"])
            self.assertEqual(code, 1)
            self.assertIn("too small to analyse", err.getvalue())
            self.assertTrue((Path(d) / "ok_snapped.png").exists())          # the good picture was still done

    def test_a_16_bit_picture_reads_like_its_8_bit_twin(self):
        eight = make_fake(make_sprite(32, 32), 12.4, 1.2, 6).convert("L")
        sixteen = Image.fromarray(np.asarray(eight, dtype=np.uint16) * 257)           # 'I;16'
        a, b = pixel_snap.snap_image(eight), pixel_snap.snap_image(sixteen)
        self.assertEqual(b.grid_status, a.grid_status)
        self.assertEqual(b.size, a.size)
        self.assertAlmostEqual(b.px, a.px, delta=0.05)

    def test_a_rotated_phone_photo_is_turned_upright(self):
        pic = make_fake(make_sprite(32, 20), 12.4, 1.2, 6)                              # 397 wide, 248 tall
        exif = Image.Exif()
        exif[0x0112] = 6                                                                # "rotate 90 degrees to view"
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "photo.jpg"
            pic.save(path, exif=exif)
            with Image.open(path) as im:
                rgba = pixel_snap.to_rgba(im)
        self.assertEqual(rgba.shape[:2], (pic.width, pic.height))                       # width and height swapped

    def test_other_picture_modes_are_fine(self):
        base = make_fake(make_sprite(32, 32), 12.4, 1.2, 6)
        for mode in ("P", "L", "LA", "RGBA", "CMYK"):
            with self.subTest(mode=mode):
                res = pixel_snap.snap_image(base.convert(mode))
                self.assertEqual(res.size, (32, 32))


class JobsAndVersionTests(unittest.TestCase):
    def test_jobs_gives_the_same_result_as_one_at_a_time(self):
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for i, (n, cell) in enumerate(((32, 12.4), (40, 10.3), (24, 14.7))):
                p = Path(d) / f"p{i}.png"
                make_fake(make_sprite(n, n), cell, 1.0, 5).save(p)
                paths.append(str(p))
            outs = {}
            for jobs in (1, 2):
                folder = Path(d) / f"out{jobs}"
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(pixel_snap.main([*paths, "-o", str(folder), "--jobs", str(jobs), "--brief"]), 0)
                outs[jobs] = {f.name: np.array(Image.open(f)) for f in sorted(folder.iterdir())}
            self.assertEqual(outs[1].keys(), outs[2].keys())
            for name in outs[1]:
                self.assertTrue((outs[1][name] == outs[2][name]).all(), name)

    def test_the_version_is_reported(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            pixel_snap.main(["--version"])
        self.assertIn(pixel_snap.__version__, out.getvalue())
        self.assertRegex(pixel_snap.__version__, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()

# Tests for --brief: short output for scripts and AI sessions.
# Run from this folder: python -m unittest test_brief -v
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import pixel_snap
from test_sorting import make_batch


class BriefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.src = Path(cls.tmp.name) / "in"
        cls.src.mkdir()
        cls.files = [str(p) for p in make_batch(cls.src)]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_main(self, *args, expect=0):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = pixel_snap.main([*args])
        self.assertEqual(code, expect)
        return buf.getvalue().strip().splitlines()

    def test_every_brief_line_is_short(self):
        lines = self.run_main(*self.files, "--brief", "-o", str(Path(self.tmp.name) / "out"), expect=2)   # 2: the painting was not saved
        self.assertEqual(len(lines), 4)
        for line in lines:
            self.assertLessEqual(len(line), 140, line)
        self.assertTrue(any("NOT SAVED" in line for line in lines))        # the painting

    def test_brief_check_only(self):
        lines = self.run_main(*self.files, "--brief", "--check-only")
        self.assertTrue(all("not saved" in l for l in lines))
        self.assertTrue(all(len(l) <= 140 for l in lines))

    def test_sorted_brief_prints_only_what_needs_attention_and_the_totals(self):
        out = Path(self.tmp.name) / "sorted"
        lines = self.run_main(*self.files, "--sort", str(out), "--want-view", "orthogonal", "--brief")
        needs = [l for l in lines if l.startswith("[")]
        self.assertEqual(sorted(l.split("]")[0] for l in needs), ["[mismatches", "[not-pixel-art"])     # the isometric house and the painting
        self.assertFalse(any("hero" in l or "village_front" in l for l in lines))                  # matches are not listed
        self.assertTrue(any(l.startswith("matches: 2") for l in lines), lines)                     # the totals line
        for l in needs:
            self.assertLessEqual(len(l), 140, l)
        self.assertTrue((out / "report.csv").exists())                                             # the full table is still written

    def test_the_long_form_is_still_the_default(self):
        lines = self.run_main(*self.files[:1], "--check-only")
        self.assertGreater(len(lines[0]), 140)


if __name__ == "__main__":
    unittest.main()

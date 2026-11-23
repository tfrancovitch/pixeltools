# Tests for the browser version (web/): it must give the same answers as the Python tool, and the page must work.
# Skipped when Node and Playwright are not installed. Run from this folder: python -m unittest test_web -v
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent


def node_ready() -> bool:
    if not shutil.which("node"):
        return False
    return subprocess.run(["node", "-e", "require('playwright')"], capture_output=True, env=node_env()).returncode == 0


def node_env():
    env = dict(os.environ)
    root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip() if shutil.which("npm") else ""
    if root:
        env["NODE_PATH"] = root + os.pathsep + env.get("NODE_PATH", "")
    return env


def drawn_pictures(folder: Path):
    """Drawn pictures with known features: a character, an isometric building, scenes, shadows, no-grid art."""
    from test_framing import figure, on_background, plain
    from test_pixel_snap import make_fake, scene
    from test_shadow import GROUNDS, compose
    from test_subject import iso_building

    fg, mask = figure()
    make_fake(on_background(fg, mask, plain((255, 255, 255), mask.shape)), 12.6, 1.0, 4).save(folder / "hero_white.png")
    fg, mask = iso_building(8, 14)
    make_fake(on_background(fg, mask, plain((255, 255, 255), mask.shape)), 12.6, 1.0, 4).save(folder / "house_iso.png")
    make_fake(scene("front", 2), 8.3, 0.9, 4).save(folder / "village_front.png")
    make_fake(scene("iso", 1), 8.3, 0.9, 4).save(folder / "village_iso.png")
    make_fake(compose(GROUNDS["green"], "cast_left", 0.65)[0], 11.6, 1.0, 4).save(folder / "hero_cast_shadow.png")
    make_fake(compose(GROUNDS["sand"], "contact", 0.7)[0], 11.6, 1.0, 4).save(folder / "hero_contact_shadow.png")
    make_fake(compose(GROUNDS["sky blue"], "cast_right", 0.7)[0], 11.6, 1.0, 4).save(folder / "hero_sky_shadow.png")
    wash = Image.fromarray(np.random.default_rng(4).integers(0, 256, (500, 500, 3), dtype=np.uint8)).filter(ImageFilter.GaussianBlur(9))
    wash.save(folder / "painting.png")


@unittest.skipUnless(node_ready(), "Node and Playwright are not installed")
class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.pics = Path(cls.tmp.name) / "pics"
        cls.pics.mkdir()
        drawn_pictures(cls.pics)
        subprocess.run([sys.executable, str(HERE / "web" / "build_web.py")], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_browser_version_gives_the_same_answers_as_python(self):
        ref = Path(self.tmp.name) / "ref.json"
        subprocess.run([sys.executable, str(HERE / "eval" / "web_reference.py"), str(self.pics), str(ref)], check=True, capture_output=True)
        done = subprocess.run(["node", str(HERE / "eval" / "web_parity.js"), str(self.pics), str(ref)], capture_output=True, text=True, env=node_env())
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("8 pictures, 8 identical", done.stdout)

    def test_the_page_works_in_a_browser(self):
        done = subprocess.run(["node", str(HERE / "eval" / "web_ui_smoke.js"), str(self.pics)], capture_output=True, text=True, env=node_env())
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_the_page_still_works_when_the_background_worker_is_blocked(self):
        # the Claude viewer is stricter than a plain browser; without a worker the page runs the same code on the main thread
        done = subprocess.run(["node", str(HERE / "eval" / "web_ui_smoke.js"), str(self.pics), "--no-worker"], capture_output=True, text=True, env=node_env())
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()

# Tests for the browser versions: same pixels as Python (parity) and the pages work at phone width.
# Skipped when Node and Playwright are not installed. Run from tools/sprite-tools: python -m unittest tests.test_web -v
# Copyright (C) 2026 the pixeltools contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY; see the GNU General Public
# License for details: <https://www.gnu.org/licenses/>.
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TOOLS_WITH_PAGES = ["turn", "fill", "flatten", "replace"]


def node_env():
    env = dict(os.environ)
    root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip() if shutil.which("npm") else ""
    if root:
        env["NODE_PATH"] = root + os.pathsep + env.get("NODE_PATH", "")
    return env


def have(module):
    return bool(shutil.which("node")) and subprocess.run(["node", "-e", f"require('{module}')"], capture_output=True, env=node_env()).returncode == 0


@unittest.skipUnless(shutil.which("node"), "Node is not installed")
class ParityTests(unittest.TestCase):
    def test_the_browser_core_gives_every_pixel_the_same_as_python(self):
        subprocess.run([sys.executable, str(ROOT / "web" / "build.py")], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as d:
            ref = Path(d) / "cases.json"
            subprocess.run([sys.executable, str(HERE / "make_parity.py"), str(ref)], check=True, capture_output=True)
            done = subprocess.run(["node", str(HERE / "parity.js"), str(ref)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertRegex(done.stdout, r"(\d+) cases, \1 identical, 0 different")


@unittest.skipUnless(have("playwright"), "Node and Playwright are not installed")
class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(ROOT / "web" / "build.py")], check=True, capture_output=True)

    def smoke(self, tool, *extra):
        done = subprocess.run(["node", str(HERE / "smoke.js"), tool, *extra], capture_output=True, text=True, env=node_env())
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_every_page_works_at_phone_width(self):
        for tool in TOOLS_WITH_PAGES:
            with self.subTest(tool=tool):
                self.smoke(tool)

    def test_every_page_works_when_the_background_worker_is_blocked(self):
        for tool in TOOLS_WITH_PAGES:
            with self.subTest(tool=tool):
                self.smoke(tool, "--no-worker")

    def test_the_hub_lists_every_tool_and_makes_no_network_requests(self):
        text = (ROOT / "pages" / "index.html").read_text(encoding="utf-8")
        for tool in TOOLS_WITH_PAGES:
            self.assertIn(f'href="{tool}.html"', text)
        self.assertNotRegex(text, r'(src|href)="https?://(?!github.com/tfrancovitch/pixeltools)')


if __name__ == "__main__":
    unittest.main()

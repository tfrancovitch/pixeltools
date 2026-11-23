#!/usr/bin/env python3
# Build the browser version: copy tuning.py's numbers into core.js, then inline everything into one HTML file.
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
"""    python web/build_web.py            # writes web/core.built.js (for tests) and pixel-snap.html (the single-file page)

The browser version keeps no tuning numbers of its own: they come from tuning.py every time this runs, so
the Python and browser versions cannot drift apart."""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import tuning  # noqa: E402


def tuning_json() -> str:
    values = {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(tuning).items() if k.isupper()}
    return json.dumps(values, indent=1)


def version() -> str:
    m = re.search(r'__version__ = "([^"]+)"', (ROOT / "pixel_snap.py").read_text(encoding="utf-8"))
    return m.group(1) if m else "0"


def built_core() -> str:
    src = (HERE / "core.js").read_text(encoding="utf-8")
    out = re.sub(r"/\*TUNING_START\*/.*?/\*TUNING_END\*/", lambda m: "/*TUNING_START*/" + tuning_json() + "/*TUNING_END*/", src, count=1, flags=re.S)
    return out.replace("/*VERSION*/", version())


def artifact_fragment(page: str) -> str:
    """The same page as a fragment for the Claude artifact system, which supplies the html, head and body itself."""
    out = re.sub(r"<!doctype html>\s*<html[^>]*>\s*<head>\s*", "", page, count=1, flags=re.I)
    out = re.sub(r'<meta charset="utf-8">\s*<meta name="viewport"[^>]*>\s*', "", out, count=1)
    out = out.replace("</head>\n<body>\n", "", 1).replace("</body>\n</html>", "").rstrip() + "\n"
    out = out.replace("<title>Pixel Snap</title>", '<title>Pixel Snap</title>\n<meta name="claude:viewport-fit-sides" content="cover">', 1)
    return out


def make_icon(size: int):
    """The five-square pixel mark (as in the page header) on a teal tile; it sits inside the central 60% so it survives round and squircle crops."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (size, size), (11, 122, 117, 255))
    d = ImageDraw.Draw(img)
    cell = size * 0.6 / 3                       # the mark is five squares of a 3 by 3 grid (an X), in the middle
    x0 = y0 = size * 0.2
    for gx, gy in ((0, 0), (2, 0), (1, 1), (0, 2), (2, 2)):
        d.rectangle([x0 + gx * cell, y0 + gy * cell, x0 + (gx + 1) * cell - 1, y0 + (gy + 1) * cell - 1], fill=(255, 255, 255, 255))
    return img


def build_site(page: str) -> None:
    """site/: the page as a small installable web app (works offline once opened), ready for GitHub Pages."""
    site = ROOT.parent.parent / "site"
    site.mkdir(exist_ok=True)
    head = ('<meta name="theme-color" content="#0b7a75">\n<link rel="manifest" href="manifest.webmanifest">\n'
            '<link rel="icon" href="icon-192.png">\n<link rel="apple-touch-icon" href="icon-192.png">\n')
    register = ("<script>\nif ('serviceWorker' in navigator && location.protocol.indexOf('http') === 0) {\n"
                "  window.addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));\n}\n</script>\n")
    index = page.replace("<title>Pixel Snap</title>\n", "<title>Pixel Snap</title>\n" + head, 1).replace("</body>", register + "</body>", 1)
    (site / "index.html").write_text(index, encoding="utf-8")
    manifest = {
        "name": "Pixel Snap", "short_name": "Pixel Snap", "description": "Turn AI pixel art into true pixel sprites, and sort a batch. Runs on your device.",
        "start_url": "./", "scope": "./", "display": "standalone", "background_color": "#eceff3", "theme_color": "#0b7a75",
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}],
    }
    (site / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    make_icon(192).save(site / "icon-192.png")
    make_icon(512).save(site / "icon-512.png")
    version = hashlib.sha256(index.encode("utf-8")).hexdigest()[:10]
    (site / "sw.js").write_text(f"""// Keeps the page on the device so it opens offline. The cache name changes whenever the page does.
const CACHE = 'pixel-snap-{version}';
const FILES = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png'];
self.addEventListener('install', e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting())));
self.addEventListener('activate', e => e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener('fetch', e => {{
  if (e.request.method !== 'GET') return;
  e.respondWith(caches.match(e.request, {{ ignoreSearch: true }}).then(hit => hit || fetch(e.request).catch(() => caches.match('./'))));
}});
""", encoding="utf-8")
    (site / ".nojekyll").write_text("", encoding="utf-8")
    print("wrote site/ (index.html, manifest, service worker, icons)")


def main() -> None:
    core = built_core()
    (HERE / "core.built.js").write_text(core, encoding="utf-8")
    print("wrote web/core.built.js", len(core), "bytes")
    template = HERE / "app.template.html"
    if template.exists():
        page = template.read_text(encoding="utf-8").replace("/*CORE_JS*/", core.replace("</script", "<\\/script")).replace("/*VERSION*/", version())
        (ROOT / "pixel-snap.html").write_text(page, encoding="utf-8")
        (HERE / "artifact.built.html").write_text(artifact_fragment(page), encoding="utf-8")
        print("wrote pixel-snap.html", len(page), "bytes and web/artifact.built.html")
        build_site(page)


if __name__ == "__main__":
    main()

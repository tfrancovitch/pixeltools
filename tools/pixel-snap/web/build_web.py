#!/usr/bin/env python3
# Build the browser version: copy tuning.py's numbers into core.js, then inline everything into one HTML file.
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
"""    python web/build_web.py            # writes web/core.built.js (for tests) and pixel-snap.html (the single-file page)

The browser version keeps no tuning numbers of its own: they come from tuning.py every time this runs, so
the Python and browser versions cannot drift apart."""
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


def built_core() -> str:
    src = (HERE / "core.js").read_text(encoding="utf-8")
    return re.sub(r"/\*TUNING_START\*/.*?/\*TUNING_END\*/", lambda m: "/*TUNING_START*/" + tuning_json() + "/*TUNING_END*/", src, count=1, flags=re.S)


def artifact_fragment(page: str) -> str:
    """The same page as a fragment for the Claude artifact system, which supplies the html, head and body itself."""
    out = re.sub(r"<!doctype html>\s*<html[^>]*>\s*<head>\s*", "", page, count=1, flags=re.I)
    out = re.sub(r'<meta charset="utf-8">\s*<meta name="viewport"[^>]*>\s*', "", out, count=1)
    out = out.replace("</head>\n<body>\n", "", 1).replace("</body>\n</html>", "").rstrip() + "\n"
    out = out.replace("<title>Pixel Snap</title>", '<title>Pixel Snap</title>\n<meta name="claude:viewport-fit-sides" content="cover">', 1)
    return out


def main() -> None:
    core = built_core()
    (HERE / "core.built.js").write_text(core, encoding="utf-8")
    print("wrote web/core.built.js", len(core), "bytes")
    template = HERE / "app.template.html"
    if template.exists():
        page = template.read_text(encoding="utf-8").replace("/*CORE_JS*/", core.replace("</script", "<\\/script"))
        (ROOT / "pixel-snap.html").write_text(page, encoding="utf-8")
        (HERE / "artifact.built.html").write_text(artifact_fragment(page), encoding="utf-8")
        print("wrote pixel-snap.html", len(page), "bytes and web/artifact.built.html")


if __name__ == "__main__":
    main()

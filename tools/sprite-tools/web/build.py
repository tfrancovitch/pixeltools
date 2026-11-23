#!/usr/bin/env python3
# Build the browser versions: copy tuning.py's numbers into core.js, then make one self-contained page per tool.
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
"""    python web/build.py        # writes web/core.built.js (for tests) and pages/<tool>.html plus pages/index.html

The browser version keeps no tuning numbers of its own: they come from spritetools/tuning.py every time this
runs, so the Python and browser versions cannot drift apart."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from spritetools import __version__, tuning  # noqa: E402

# One entry per tool that has a page. Controls are drawn by the shared page template (web/page.template.html).
# type: seg (pick one), range (percent slider), check, colour, text (a box for a list).
PAGES = {
    "turn": {
        "title": "Turn",
        "lede": "Flip a sprite left-right or top-bottom. Exact: no blur, no smoothing.",
        "actions": [{"label": "Flip left-right", "opts": {"flip": "h"}}, {"label": "Flip top-bottom", "opts": {"flip": "v"}}],
        "controls": [],
        "point": False,
    },
    "fill": {
        "title": "Fill",
        "lede": "Bucket fill that copes with noisy AI pictures: it fills every close shade, not only the exact colour. Or fill a whole background in one tap.",
        "controls": [
            {"id": "colour", "type": "colour", "label": "Fill with", "value": "#00000000", "hint": "Write #00000000 for transparent. Colours are #rrggbb or #rrggbbaa."},
            {"id": "tolerance", "type": "range", "label": "How close counts as the same colour", "min": 0, "max": 100, "step": 1, "value": 10, "unit": "%"},
            {"id": "background", "type": "check", "label": "Fill the whole background (start from the border; no tap needed)", "value": False},
            {"id": "everywhere", "type": "check", "label": "Fill every close pixel in the picture, not only the connected area", "value": False},
            {"id": "corners", "type": "check", "label": "Count corner-touching pixels as connected", "value": False},
        ],
        "point": True, "pointNeeded": True, "pointIgnoredWhen": "background",
        "pointHelp": "Tap the picture where you want to fill, or choose \"Fill the whole background\".",
        "actions": [{"label": "Fill", "primary": True}],
    },
}
ORDER = ["fill", "replace", "flatten", "turn"]   # the order on the hub page


def tuning_json() -> str:
    values = {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(tuning).items() if k.isupper()}
    return json.dumps(values, indent=1)


def built_core() -> str:
    src = (HERE / "core.js").read_text(encoding="utf-8")
    out = re.sub(r"/\*TUNING_START\*/.*?/\*TUNING_END\*/", lambda m: "/*TUNING_START*/" + tuning_json() + "/*TUNING_END*/", src, count=1, flags=re.S)
    return out.replace("/*VERSION*/", __version__)


def style() -> str:
    return (HERE / "style.css").read_text(encoding="utf-8")


def page(tool: str, cfg: dict, core: str, template: str) -> str:
    config = dict(cfg, tool=tool, version=__version__)
    return (template.replace("/*STYLE*/", style()).replace("/*TITLE*/", cfg["title"]).replace("/*LEDE*/", cfg["lede"]).replace("/*VERSION*/", __version__)
            .replace("/*CONFIG*/", json.dumps(config).replace("</", "<\\/")).replace("/*CORE_JS*/", core.replace("</script", "<\\/script")))


def hub(template: str) -> str:
    items = "\n".join(f'    <a class="tool" href="{t}.html"><b>{PAGES[t]["title"]}</b><span>{PAGES[t]["lede"]}</span></a>' for t in ORDER if t in PAGES)
    return template.replace("/*STYLE*/", style()).replace("/*VERSION*/", __version__).replace("<!--TOOLS-->", items)


def main() -> None:
    core = built_core()
    (HERE / "core.built.js").write_text(core, encoding="utf-8")
    print("wrote web/core.built.js", len(core), "bytes")
    pages = ROOT / "pages"
    pages.mkdir(exist_ok=True)
    template = (HERE / "page.template.html").read_text(encoding="utf-8")
    for tool in ORDER:
        if tool in PAGES:
            html = page(tool, PAGES[tool], core, template)
            (pages / f"{tool}.html").write_text(html, encoding="utf-8")
            print(f"wrote pages/{tool}.html", len(html), "bytes")
    (pages / "index.html").write_text(hub((HERE / "hub.template.html").read_text(encoding="utf-8")), encoding="utf-8")
    print("wrote pages/index.html")


if __name__ == "__main__":
    main()

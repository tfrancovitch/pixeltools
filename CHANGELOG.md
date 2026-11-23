# Changelog

## 1.0.0 (2026-11-23)

First release of **Pixel Snap**.

- **Finds the real pixel grid** in AI "pixel art", including soft or blurry blocks and slightly stretched (non-square) pixels, and rebuilds the picture at true size. The answer is graded: clear, weak (used, flagged) or none (nothing saved, with a plain reason).
- **Says what each picture is**: lone sprite or whole scene; character, building, scene or unclear.
- **Isometric or straight-on** for buildings, objects and scenes, from long straight edges, without needing the pixel grid.
- **Ground shadows**: found, named contact or cast, and removable (`--shadows keep | remove-cast | remove-all`) without touching the sprite.
- **Transparent backgrounds** for lone sprites on a plain or gradient ground.
- **Batch sorting** into `matches/`, `mismatches/`, `cant-tell/` and `not-pixel-art/` with a `report.csv` of every measurement; `--want-view` and `--want-facing` say what you need; `--brief` prints only what needs attention; `--jobs N` works on N pictures at once.
- **Browser version**: one self-contained file (and an installable web app in `site/`) giving the same answers as the Python tool on all 102 test pictures. Runs entirely on the device, makes no network requests, works offline.
- **AI skill**: `.claude/skills/pixel-snap/SKILL.md`.
- Tests: Python, browser parity, and the page itself in a real browser at phone width.

Known limits: character facing cannot be judged (reported as "can't tell" with measured clues); objects and front-view buildings are "unclear"; thresholds are provisional, tuned on one batch of 102 pictures.

Planned for version 2: use many labelled pictures to tune the thresholds, add objects, and retry character facing.

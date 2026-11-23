# Sprite Tools: plan

**Author:** Victor (planning on Opus) · **For:** the owner, and the sessions that build it · **Date:** 2026-11-23 · **Status:** accepted in outline by the owner; the design decisions below are the builder's instructions, not suggestions

## 1. What we are building

A set of **small, separate sprite tools**. Each does one job well, and each can be used two ways:

- **By an AI**, as a command it runs (so it never has to write the same code again), with short machine-readable output.
- **By a person on a phone**, as its own small page: open, pick a picture, tap, save. One file, works offline, nothing uploaded.

They share one core, so they behave identically everywhere. They are built **a few at a time**, each one finished and tested before the next, so a working set exists early and grows. A doodle editor comes last and is made from the same pieces.

**Not the goal:** a Photoshop-style program. Every tool must be explainable in two sentences.

## 2. Ground rules (every slice)

1. **No AI inside the tools.** numpy and Pillow in Python; plain JavaScript in the browser. Same rule as Pixel Snap.
2. **Exact pixels.** Never smooth, blur or resample with interpolation. Scaling is nearest-neighbour or block-majority. Colours are 8-bit RGBA.
3. **Python is the reference; the browser version must give identical results.** Every operation has a parity test (Python and JavaScript on the same pictures, every pixel compared). This is how Pixel Snap's browser version was proven, reuse that harness.
4. **Every tuning number lives in one file** (`tuning.py`), copied into the JavaScript at build time, never typed twice.
5. **Every operation has exact tests** on drawn pictures where the right answer is known, pixel for pixel.
6. **License:** GNU GPL v3 or later; each file carries the short header used in Pixel Snap.
7. **Public repository:** never write the owner's name, the names of private projects, or anything about the owner's other work into this repository.
8. **Plain words** in pages, help text, reports and documents.

## 3. Where things live

```
tools/sprite-tools/
  spritetools/            the Python package: one module per tool, plus shared helpers
    core.py               image in/out, colour distance, neighbours, masks
    palette.py            palette model and file formats
    fill.py, replace.py, flatten.py, outline.py, turn.py, crop.py, ...
    tuning.py             every threshold and default
  sprite.py               the command: `python sprite.py <tool> ...`
  web/                    the JavaScript core (mirrors spritetools/) and the page template
  pages/                  built pages: one per tool (fill.html, flatten.html, ...) and index.html linking them
  tests/                  exact tests, parity tests, page smoke tests
  README.md               every tool: what it does, the command, the page, limits
```

Pixel Snap stays where it is (`tools/pixel-snap/`). Later, the sprite tools may call Pixel Snap (for example "snap, then flatten"), never the other way round.

## 4. Shared conventions (decided)

### Colours and "close enough"

- A colour is written `#rrggbb`, `#rrggbbaa`, or `r,g,b[,a]`. A picked point is written `--at x,y` (pixels, from the top-left, 0-based).
- **Colour difference** is the straight-line distance in RGBA, `sqrt(dr² + dg² + db² + da²)`. Simple, explainable, and good enough for the noisy near-copies AI pictures make.
- **Tolerance** is a percentage, 0 to 100: 0 means exactly this colour, 100 means every colour. Internally the cut-off is `tolerance / 100 × 510` (510 is the largest possible RGBA distance). Defaults per tool are in `tuning.py` and are **provisional until tested on real Midjourney pictures** (the 102-picture batch used for Pixel Snap, run through Pixel Snap first).
- Fully transparent pixels count as one colour ("transparent"), whatever their RGB.

### Connected

- "Connected" means touching side by side. The option **`--corners`** (page: "count corner-touching as connected") also counts diagonal neighbours. Default: off. (These are what other editors call 4-way and 8-way fill.)

### The command (for AI and scripts)

```
python sprite.py <tool> INPUT... [-o OUT.png | --out-dir DIR] [tool options] [--json] [--brief] [--jobs N]
```

- Several inputs, or a glob, process a batch. `--out-dir` names outputs `<name>_<tool>.png`.
- `--json` prints one JSON object per picture: input, output, size, and what changed (for example `"pixels_changed": 412, "colours_before": 87, "colours_after": 9`). This is what an AI reads.
- `--brief` prints one short line per picture. Default output is a plain sentence per picture.
- Exit code 0 when everything worked, 1 when a file could not be read, 2 when a tool could not do its job on some picture (with the reason).
- `python sprite.py --list` lists the tools with one line each. `python sprite.py <tool> --help` explains every option in plain words, with an example.

### The pages (for people)

- One self-contained page per tool, built from a shared template (same look as Pixel Snap: same colours, light and dark, phone first, no network requests, works offline). `index.html` lists all tools.
- Pattern: **Choose picture → tap the picture where it matters (picking a point or a colour) → adjust one or two settings → before/after toggle → press and hold the result to save.** Zoom by pinch; the picture is shown with crisp pixels.
- Undo on every page (at least ten steps), so tools can be applied repeatedly.
- Pages built by one script (`web/build.py`) like Pixel Snap's `build_web.py`; built pages are committed so the owner can download them.

### The AI skill

`.claude/skills/sprite-tools/SKILL.md`: what each tool does in one line, the command, the `--json` fields, and the rule "run the tool, do not write code for the same job, do not look at the pictures unless asked".

## 5. The tools

Each tool is either an **operation** (works on a whole picture, given settings; an AI can run it, and it gets a page) or an **editor feature** (only makes sense while drawing by hand; it lives in the doodle editor, phase 4). Most of the owner's list are operations.

### Release 1: the first working set (phases 1 and 2)

| # | Tool | What it does | Options (decided) |
|---|---|---|---|
| 1 | **fill** | Bucket fill that tolerates the noisy near-shades in AI pictures | `--at x,y` start point; `--colour`; `--tolerance` (default 10); `--everywhere` (every close pixel in the picture, not only the connected area); `--background` (shortcut: start from the picture's border colour and fill the whole ground, however much it varies; uses the same background estimate as Pixel Snap's framing); `--corners` |
| 2 | **replace** | Change one colour (and everything close to it) into another, everywhere or only where connected | `--from` colour or `--at x,y`; `--to` colour; `--tolerance` (default 8); `--connected` (only the area around `--at`); `--map FILE` (many from→to pairs at once: a palette swap) |
| 3 | **flatten** | The opposite of dithering: makes areas one even colour and makes the edges between them sharp | `--tolerance` (default 6) for what counts as "the same colour"; `--at x,y` to flatten only that area (the red shirt) or the whole picture; `--edges` / `--no-edges` (sharpen edges, default on); `--min-speck N` (absorb lone stray pixels up to N in size, default 2). Design in section 6 |
| 4 | **outline** | Draw a one-pixel outline around the subject | `--colour` (default: the darkest colour already in the sprite); `--outside` (default, on transparent pixels around the shape) or `--inside` (on the shape's own edge pixels); `--corners` (diagonal outline too); `--thickness 1..3` |
| 5 | **turn** | Rotate, flip and scale without blur (the sprite turner) | `--rotate 90|180|270`; `--flip h|v`; `--scale N` (whole-number enlarge, nearest) or `--shrink N` (whole-number reduce: each N×N block becomes its most common colour); `--fit WxH` (largest whole-number scale that fits) |
| 6 | **crop** | Trim to the subject, and add padding | `--trim` (cut away transparent or background border; background = border colour within `--tolerance`); `--pad N` or `--pad-to WxH` with `--anchor` (centre, bottom, ...); `--multiple N` (grow the canvas to a multiple of N, for tile grids); padding transparent or `--colour` |
| 7 | **palette** | Read, reduce, apply and save palettes; one-click palette swap | `extract` (the colours, most used first; writes a palette file and a swatch strip PNG); `reduce --colours N`; `apply FILE` (every pixel to the nearest palette colour); `swap FROM_FILE TO_FILE` (same-order colour swap). File formats: `.hex` (Lospec), `.gpl` (GIMP), a PNG swatch strip, and `.txt` one colour per line |
| 8 | **transparent** | Make the background transparent (Pixel Snap's method, as its own tool) | `--tolerance`; `--keep-enclosed` (default on: background-coloured gaps inside the sprite stay) |

### Release 2 (phase 3)

| # | Tool | What it does |
|---|---|---|
| 9 | **shade** | Lighter or darker by palette steps on a region (a colour ramp), not by mixing colours |
| 10 | **dither** | Fill a region with a two-colour pattern (checker, 25%, 50%, 75%, Bayer 2×2/4×4) |
| 11 | **mirror** | Make a sprite symmetric: copy the left half onto the right (or top onto bottom) |
| 12 | **sheet** | Cut a sprite sheet into frames by grid or by gaps; pack frames into a sheet; GIF from frames |
| 13 | **tile** | Show a picture repeated 3×3 to check it tiles; make a tile seamless by blending only at the seam; cut a tilesheet |
| 14 | **rotate any angle** | Pixel-art-aware rotation at any angle (the RotSprite method: enlarge with edge-aware rules, rotate, shrink back), added to `turn` |
| 15 | **draw** | Lines, rectangles and ellipses (filled or not) from coordinates, for an AI to draw precisely without writing code |

### Phase 4: the doodle editor

The hand-drawing program, built on the same core, after release 2: pencil with brush sizes, eraser, colour picker, line, rectangle, ellipse (filled or not), the fill / replace / flatten tools above, palette, rectangle and same-colour selection with move, copy, paste, flip and 90° turns, undo and redo, zoom, pan, pixel grid, mirror drawing, layers, frames, onion skin, GIF and sheet export, tile mode with live repeat. It gets its own plan when phase 3 is done. Autotile is deliberately left for after that.

### How the owner's two lists map onto this

| Owner's item | Where |
|---|---|
| Fill (tolerance, fill background, corner-touching) | tool 1 |
| Replace colour | tool 2 (with `--map` for palette swaps) |
| Flatten | tool 3 |
| Outline | tool 4 |
| Rotate, flip, scale without blur | tool 5; any angle in tool 14 |
| Crop to content, padding | tool 6 |
| Palette, indexed colour, palette swap | tool 7 (indexed colour is how `palette` and the editor store pictures) |
| Shading, dither, mirror | tools 9, 10, 11 |
| Layers, frames, onion skin, GIF and sheet export | tool 12 (sheets and GIF) and the editor |
| Tile mode, tilesheet, autotile | tool 13 and the editor; autotile after the editor |
| Pencil, brush sizes, eraser, picker, line, rectangle, ellipse, selection, undo, zoom, pan, grid | the editor; tool 15 gives an AI the shapes |
| PNG in and out with exact pixels | every tool (section 4) |

## 6. Flatten: the design (the one tool that needs real care)

Midjourney colours are never flat: a red shirt is twenty slightly different reds, and the edge between the shirt and the arm is a band of in-between colours. Flatten does three passes, each switchable and each tested on its own:

1. **Merge near colours.** Group colours that are within the tolerance of each other (the most used colour in a group wins, as in Pixel Snap's colour merge). With `--at`, only the connected area of the touched colour (within tolerance) is merged, and everything else is left exactly alone.
2. **Sharpen edges.** A pixel is an "edge blend" when its colour lies close to the straight line between the colours of two neighbouring areas (it is a mix of them). It is given whichever of the two it is nearer to. Repeat until nothing changes (at most three times). Pixels that are not blends are never touched.
3. **Absorb specks.** A patch of at most `--min-speck` pixels, surrounded by one other colour, takes that colour.

**Gate:** on drawn tests (a flat sprite enlarged, blurred and noised, then shrunk back with Pixel Snap) flatten must give back the original colours on at least 97% of pixels and the original colour count exactly; on twenty real Midjourney sprites after Pixel Snap, the colour count must drop by at least half, and a before/after sheet must be checked by eye for damaged details (eyes, outlines, highlights). If the gate is not met after two tuning passes, ship passes 1 and 3 only, and keep pass 2 behind an option marked experimental.

## 7. Phases and slices

Each slice: build in Python, exact tests, mirror in JavaScript with a parity test, its page, its README section, its line in the skill file, a commit, and a line in `docs/PROGRESS_SPRITE_TOOLS.md`.

| Phase | Slice | Content | Gate |
|---|---|---|---|
| 0 | **S0 foundations** | Package layout, `core.py` (read any picture to 8-bit RGBA, write PNG, colour parsing, distance, neighbours, connected areas), `sprite.py` command framework with `--json/--brief/--jobs/--list`, the JavaScript core skeleton, the parity harness, the page template and build script, the hub page, CLAUDE.md conventions followed | One trivial tool (`turn --flip h`) works end to end: command, page, parity test, page smoke test at phone width |
| 1 | **S1 fill** | Tool 1 | Exact tests (tolerance edges, corners on/off, everywhere, background on a noisy gradient ground); fills a whole noisy Midjourney background in one tap on the owner's sample pictures |
| 1 | **S2 flatten** | Tool 3 | Section 6 gate |
| 1 | **S3 replace** | Tool 2 | Exact tests; a palette swap by `--map` |
| 2 | **S4 turn** | Tool 5 (whole rotate, flip, scale, shrink, fit) | Exact tests; turning four times by 90 gives the original back |
| 2 | **S5 crop** | Tool 6 | Exact tests; trim then pad to a 32-pixel multiple |
| 2 | **S6 outline** | Tool 4 | Exact tests for outside, inside, corners, thickness |
| 2 | **S7 palette** | Tool 7 | Round trip of every file format; apply and swap exact |
| 2 | **S8 transparent** | Tool 8 | Same answers as Pixel Snap's background removal on its tests |
| 2 | **R1 release** | README, skill, hub page, CHANGELOG `sprite-tools 1.0.0`, tag | Every test green; owner tries the pages on a phone |
| 3 | **S9 to S15** | Release 2 tools, one slice each | Per tool |
| 4 | Editor | Own plan | |

Order reason: foundations first, then the two tools the owner named as real problems (fill could not fill a whole background; flatten for the red shirt), then the rest of release 1.

## 8. Tests and checks

- **Exact tests** for every option of every tool, on drawn pictures with known answers.
- **Parity tests**: Python and JavaScript on the same pictures, every pixel equal, for every tool.
- **Page smoke test** per page at phone width: loads, works with a sample picture, no network requests, no errors, no sideways scrolling.
- **Real pictures**: the owner's Midjourney test batch (outside the repository) through Pixel Snap, then the tool; looked at by eye on a contact sheet where a judgement is needed.
- **Speed budget**: a 1024 by 1024 picture in under 2 seconds in Python for every release 1 tool.

## 9. Recommended models

| Work | Model |
|---|---|
| Every slice | Sonnet |
| Checking a slice, running tests, contact sheets | Haiku |
| Flatten if its gate fails twice; the editor's plan; a whole review before release 1 | Opus |

## 10. Risks

| Risk | Guard |
|---|---|
| Flatten damages small details (eyes, highlights) | Pass-by-pass switches; the speck size kept small; eye check on real sprites; the stop rule in section 6 |
| Tolerance defaults wrong for real pictures | Defaults provisional; tuned in each slice on the owner's sample pictures |
| Python and browser drift apart | Parity test per tool; numbers from one file |
| Scope creep toward a big editor | Release 1 is eight operations; the editor waits for its own plan |
| Phone speed | Speed budget; pages do work in a background worker with a main-thread fallback (as Pixel Snap) |

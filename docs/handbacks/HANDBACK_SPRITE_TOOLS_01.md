# Handback 01: Sprite Tools, slices S0 to S3

**From:** the build session (Sonnet) · **To:** the owner and the next session · **Date:** 2026-11-23

## Summary (plain words)

S0, S1, S2 and S3 are built: four tools (turn with flip, fill, flatten, replace), each as a command and as a phone page, and each checked against the other pixel for pixel. 86 tests pass.

**The big open item: none of this has been tried on real Midjourney pictures**, because none were in the repository. Every tolerance number is a first guess, tuned on drawn pictures with noise and JPEG damage. Fill and flatten in particular need a look at real pictures before the numbers are trusted. When you send a few pictures, the first job is to run them through Pixel Snap, then fill `--background` and flatten, and look at the results.

The plan's flatten gate has two halves. The half that can be tested on drawn pictures passes (24 of 24). The half that needs twenty real sprites and an eye check is **not done**.

I stopped after S3, as the handoff says. The whole session took about 20 minutes on the clock, so the 60-minute checkpoint was never reached.

## What differs from the handoff

- **Branch:** the handoff says `sprite-tools/s0-s3`. This session was only allowed to push to `ccr-286e9eb5-d9bunc`, so the work is there, started from `plan-sprite-tools` (which holds the plan), not from `main`. Rename it or merge as you like; nothing is on `main`.
- **Models:** Sonnet only. No Haiku subagents were used (the test runs were quick enough to do directly). No Opus review was needed: the flatten gate did not fail twice.

## Results by slice

| Slice | Built | Gate | Evidence |
|---|---|---|---|
| **S0 foundations** | `spritetools/core.py` (read and write pictures, colours, points, distance, connected areas), `tuning.py`, `sprite.py` (`--list`, `--json`, `--brief`, `--jobs`, `-o`, `--out-dir`, exit codes 0/1/2), JavaScript core, page template, `web/build.py`, hub page, parity harness, phone-width smoke test, README, skill file | `turn --flip h` end to end: command, page, parity, smoke test. **Met.** | 15 tests in `tests/test_s0.py` (exact flips, colour and point parsing, tolerance, transparent as one colour, connected areas, command output and exit codes, `--jobs`). Parity: 5 of 5 turn cases identical. Smoke: `turn` page 9 checks pass, with and without the background worker. |
| **S1 fill** | `fill`: `--at`, `--colour` (default transparent), `--tolerance` (10), `--everywhere`, `--corners`, `--background` (fits a gentle gradient to the border, grows from the border in steps of one tolerance, keeps enclosed pockets). Page with a one-tap background fill. | Exact tests incl. tolerance edges, corners on/off, everywhere, background on a noisy gradient ground. **Met on drawn pictures.** "Fills a whole noisy background on the owner's samples" is **not verified** (no samples). | 18 tests in `tests/test_fill.py`. On drawn pictures with noise ±8 and JPEG quality 50 to 90, `--background` at the default tolerance misses under 0.5 percent of the ground and leaks at most 0.2 percent into the figure's inside (tests assert this). 1024×1024: 0.38 s. Smoke: 11 checks incl. a one-press background fill. |
| **S2 flatten** | `flatten`: pass 1 merge near colours, pass 2 sharpen edges, pass 3 absorb specks; each switchable (`--no-merge`, `--no-edges`, `--min-speck 0`); `--at` for one area; page with a switch per pass | Section 6 gate. **Drawn half met; real-picture half open.** | 27 tests in `tests/test_flatten.py` (each pass alone, switches, `--at` leaves the rest exactly alone, clean sprite unchanged). Drawn gate: 24 of 24 round trips (enlarge, blur, noise, JPEG, shrink with Pixel Snap) give the original colours on at least 97 percent of pixels and the exact colour count (11). Harsher own damage: about 90 to 95 percent right (from about 86), 1700 colours down to 22 to 27. 1024×1024: 0.59 s. Before/after picture: `docs/handbacks/evidence/flatten_drawn_before_after.png` (I looked at it: eyes, outline and highlight survive on the Pixel Snap output; on the harsh damage a few stray dark bits stay). |
| **S3 replace** | `replace`: `--from` / `--at`, `--to`, `--tolerance` (8), `--connected`, `--corners`, `--map` (palette swap: nearest pair wins, all pairs applied at once, a swap trades places), map file format with line-numbered errors; page with a swap box | Exact tests; a palette swap by `--map`. **Met.** | 22 tests in `tests/test_replace.py`, incl. a palette swapped there and back gives the original. Smoke: 12 checks incl. a typed swap and a bad list explained in plain words. 1024×1024: 0.06 s (one colour), 0.17 s (map). |

Across all slices: parity **51 of 51 cases identical** (every pixel, every info number, and every error message, Python against the page code), and **all four pages pass the phone-width smoke test (400 px wide)** both with the background worker and with it blocked: loads, works on the sample, changes the picture, before/after and undo work, no network requests, no page errors, no sideways scrolling.

## Commands run, and what they printed

```
$ cd tools/sprite-tools && NODE_PATH=$(npm root -g) python3 -m unittest discover tests
Ran 86 tests in 35.625s
OK

$ python3 tests/make_parity.py /tmp/par.json && node tests/parity.js /tmp/par.json
wrote 51 cases to /tmp/par.json
51 cases, 51 identical, 0 different

$ node tests/smoke.js <tool>            (turn, fill, flatten, replace: "ok" lines 9, 11, 9, 12; FAIL lines 0, also with --no-worker)

$ python sprite.py --list
fill       bucket fill with a tolerance, or fill a whole noisy background in one go
flatten    make areas one even colour and the edges between them sharp (the opposite of dithering)
replace    change one colour (and everything close to it) into another, or swap a whole palette with --map
turn       flip a sprite left-right or top-bottom, exactly (rotate and scale come next)

$ python sprite.py flatten hero.png --json        (a drawn, badly damaged 40x48 sprite)
{"input": "hero.png", "output": "hero_flatten.png", "tool": "flatten", "size": [40, 48], "pixels_changed": 1901, "pass1_pixels": 1877, "pass2_pixels": 234, "pass3_pixels": 9, "colours_before": 1697, "colours_after": 22, "size_after": [40, 48]}

$ python sprite.py fill sky.png --background --brief
sky.png -> sky_fill.png: 11666 changed, colours 11163 -> 3333

$ python sprite.py replace hero.png --at 20,26 --to '#3070c8' --connected
hero.png: replaced 121 pixels; 121 actually changed. Saved hero_replace.png.
```

Speed on a 1024×1024 noisy picture (budget 2 seconds): turn 0.03 s, fill `--background` 0.38 s, fill `--at` 0.21 s, flatten 0.59 s, replace 0.06 s, replace `--map` 0.17 s.

## Decisions made while building (all in the code and the README)

- **Background fill model.** A plain "same as the border colour" test cannot fill a gradient sky. `--background` fits a gentle gradient (least squares) to the border ring and fills pixels that touch the border, stay within 1.5 tolerances of that gradient, and are reached in steps of at most one tolerance. A first version, which allowed a loose range around the border colour, leaked into pale skin; the gradient version fixed that. This is the plan's "same estimate as Pixel Snap's framing" in spirit (a gradient fitted to the border), but it is a separate, smaller implementation so the browser version stays exact.
- **Flatten pass 2 looks only up/down and left/right.** Looking along diagonals ate the corners of a shaded area (a dark shirt side next to an outline). A pixel is a blend only if it is squeezed between two different areas on opposite sides and lies on the line between their colours; a shading band that is an area of its own is kept.
- **Flatten pass 3 keeps a speck that is very different from its surroundings** (more than 25 percent away), so a one-pixel eye or highlight survives the default `--min-speck 2`.
- **`--at` in flatten** changes only the touched area and its one-pixel edge.
- Core error messages use the command's option names (`--at`, `--to`); the pages translate them into plain words.

## Not verified, stated plainly

1. **Real Midjourney pictures.** None were available. Fill's default tolerance (10), the background model's numbers, flatten's tolerance (6), edge line width, speck reach (25) and replace's tolerance (8) are all provisional. The plan's flatten gate on twenty real sprites with a by-eye check of eyes, outlines and highlights has **not been done**.
2. **Flatten on hard pictures.** On drawn damage harsher than Pixel Snap normally leaves, flatten improves a lot but does not reach the original exactly (see S2). Whether real pictures look like the mild or the harsh case is unknown.
3. **Phone use by a person.** The pages were tested in a headless desktop browser emulating a 400-pixel-wide screen, not on a real phone. Press-and-hold saving is the same method as Pixel Snap's page and was not tried.
4. **Semi-transparent pixels in the browser.** The page reads and writes pictures through a canvas, which can change the colour of semi-transparent pixels by a small amount. Fully opaque and fully transparent pixels are exact. (The Python tool is exact for all of them.)
5. **Pictures over 16 million pixels** are refused by the page (use the command).
6. **Not built yet, by design:** installable offline site (Pixel Snap has one), pinch-zoom controls beyond the browser's own, the rest of `turn` (rotate, scale, shrink, fit: slice S4), and everything from S5 on.

## Next

S4 turn (rotate, scale, shrink, fit), then S5 crop, S6 outline, S7 palette, S8 transparent, R1. Before more tools: ask the owner for a few real pictures and tune fill and flatten on them.

# Handoff 01: Sprite Tools, slices S0 to S3

**From:** Victor (planning) · **To:** the next build session in the `pixeltools` repository · **Date:** 2026-11-23

## Read first, in this order

1. `CLAUDE.md` (repository rules)
2. `docs/PLAN_SPRITE_TOOLS.md` (the plan; its decisions are instructions)
3. `docs/PROGRESS_SPRITE_TOOLS.md` if it exists (resume from the last finished slice; do not redo finished work)
4. For reuse: `tools/pixel-snap/` (how a tool, its tests, its browser version, its parity harness and its page build are done here). Copy patterns, not code paths: the sprite tools are a separate package.

## The job

Build slices **S0 foundations, S1 fill, S2 flatten, S3 replace** from the plan, in that order. Stop after S3, or earlier if time runs short (see "Checkpoints").

## Recommended models

- This session: **Sonnet**.
- Small checks (running tests, comparing outputs, contact sheets): **Haiku** subagents, at most 3 at a time.
- If the flatten gate (plan section 6) fails twice: stop flatten, record what was tried, and recommend an **Opus** review in the handback. Do not keep stacking rules.

## Per slice: definition of done

1. Python: the tool in `tools/sprite-tools/spritetools/`, its command in `sprite.py`, defaults in `tuning.py`.
2. Exact tests for every option (drawn pictures, known answers, pixel for pixel).
3. JavaScript: the same tool in `web/`, a parity test that every pixel matches Python.
4. The page in `pages/`, built by `web/build.py`; a smoke test at phone width (loads, works on a sample, no network requests, no errors, no sideways scrolling).
5. A section in `tools/sprite-tools/README.md`; a line in `.claude/skills/sprite-tools/SKILL.md`.
6. A commit, and one line in `docs/PROGRESS_SPRITE_TOOLS.md`: done, numbers, what is next, anything half-finished.

## Slice notes

**S0 foundations.** The gate is one trivial tool end to end (`turn --flip h`: command, page, parity, smoke test). Keep the framework small: no plug-in system, no config files. `sprite.py --list` and `--json` must work from the start.

**S1 fill.** The owner's real problem: another editor's fill stopped at the exact colour and could not fill a noisy AI background. The fix is tolerance plus `--background` (start from the border colour, fill the whole ground). Tune the default tolerance on real pictures: the owner's Midjourney test batch is not in this repository; ask the owner for a few pictures, or use drawn pictures with noise and JPEG damage and say so.

**S2 flatten.** Follow plan section 6 exactly: three passes, each switchable, each tested alone. Its gate needs real sprites: run the owner's pictures through Pixel Snap first (`tools/pixel-snap/pixel_snap.py ... --brief`), then flatten. Make a before/after contact sheet and look at it for damaged eyes, outlines and highlights.

**S3 replace.** Straightforward; include `--map` (a palette swap) from the start.

## Rules that matter here

- **Public repository:** do not write the owner's name, private project names, or anything about the owner's other work into any file or commit.
- **Ask before long jobs:** anything expected to take more than about 10 minutes (a long test run, a big batch) needs the owner's yes first, with an estimate.
- **Checkpoints:** commit after every slice. Run `date` at the start and before each slice; after about 60 minutes of work, finish the current slice and stop, with a "where I stopped" line in the progress file.
- **Branch:** work on `sprite-tools/s0-s3`, branched from `main`. Do not merge to `main`: the owner decides.
- **Plain words** to the owner, who reads on a phone and is not a programmer.

## Handback

Write `docs/handbacks/HANDBACK_SPRITE_TOOLS_01.md`: a summary first; then a table, one row per slice, with what was built, the gate result and the evidence (test counts, parity result, numbers); the commands you ran and their real output; and anything not verified, stated plainly. Do not mark anything done without evidence in the same row.

# pixeltools: rules for Claude sessions

Free, GPL v3 tools for pixel-art sprites: **Pixel Snap** (`tools/pixel-snap/`, version 1.0.0) and the **Sprite Tools** (`tools/sprite-tools/`, being built; plan in `docs/PLAN_SPRITE_TOOLS.md`).

## Before starting

Read the current handoff in `docs/handoffs/` and the matching progress file in `docs/`. Resume from the last finished slice.

## The owner

Works mostly from an Android phone and is not a programmer. Write to the owner in plain language, with no jargon to look up. Give a recommendation, not a list of options to choose from. Ask before any job expected to take more than about 10 minutes (say what, how long, and a faster alternative if there is one).

## This repository is public

Never write the owner's name, the names of private projects, or anything about the owner's other work into files, commits or pull requests. Refer to "the owner".

## How tools are built here

- No AI inside the tools: numpy and Pillow in Python; plain JavaScript in the browser.
- Python is the reference; each browser version must give identical results, proven by a parity test.
- Every threshold lives in a `tuning.py` and is copied into the JavaScript at build time.
- Every tool has exact tests on drawn pictures, a command an AI can run (`--json`, `--brief`), and a phone page that works offline and makes no network requests.
- Every file carries the short GPL v3 header used in the existing tools.

## Git

Work on a branch named for the handoff (for example `sprite-tools/s0-s3`), branched from `main`. Commit after every slice, with a plain description. Only the owner decides merges to `main`.

## Models

Sonnet for building, Haiku for small checks (at most 3 subagents at once), Opus for planning and for reviews the plan calls for. Note in each handback which were used.

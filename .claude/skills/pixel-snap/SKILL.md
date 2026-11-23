---
name: pixel-snap
description: Turn AI-generated "pixel art" (Midjourney and similar) into true-size pixel sprites, and sort a batch by what it is (character, building, scene), whether it is isometric or straight-on, ground shadows and transparent backgrounds. Use when the user has big AI pixel-art pictures to convert, sort, check or clean up. It runs offline in Python with no AI calls, so it is far cheaper than looking at the pictures yourself.
---

# Pixel Snap (for AI sessions)

Midjourney "pixel art" is a big picture of pixel art: each visible pixel is really a block of many soft, noisy pixels, on a grid that wobbles and is often slightly stretched. Pixel Snap finds the real grid and rebuilds the picture at its true size, and decides what each picture is. **Run the tool. Do not look at the pictures to judge them.** One picture costs far more to look at than a whole folder costs to run.

## Set up (once)

```
git clone https://github.com/tfrancovitch/pixeltools     # skip if already in the repo
pip install numpy pillow
```

Needs Python 3.9 or newer. The tool is `tools/pixel-snap/pixel_snap.py`. It uses no network and no AI.

## The commands you will use

Sort a whole folder, printing only what needs attention (the cheap default):

```
python tools/pixel-snap/pixel_snap.py IN/*.png --sort OUT --brief --want-view orthogonal
```

- `--want-view orthogonal | isometric | either`: for buildings, objects and scenes. Pictures in the other view go to `OUT/mismatches/`.
- `--want-facing diagonal | cardinal | either`: for characters. **The tool cannot judge facing**, so a wanted facing sends every character to `OUT/cant-tell/`. Use `either` unless a person will sort those by eye.
- `--shadows keep | remove-cast | remove-all`: `remove-cast` drops sun-angle shadows and keeps a small contact shadow under the feet.
- `--transparent`: makes a plain background transparent (lone sprites only).
- `--colors 16`: limits the palette; Midjourney output has 80 to 200 slightly different colours, so use this for clean sprites.
- `--scale 8`: saves the sprite enlarged 8 times without blur (for moodboards); omit for the true-size sprite.
- `--cell 16`: pixelates a painted picture anyway, one pixel per 16 by 16 block of the original.

One picture or a quick look, no folders: `python tools/pixel-snap/pixel_snap.py pic.png --brief` (add `--check-only` to save nothing).

## What you get

`OUT/` holds four folders and a report:

| Folder | Meaning | Holds |
|---|---|---|
| `matches/` | pixel art, the view you asked for | the snapped sprite (`_WEAK` in the name = the grid was uncertain: look at it) |
| `mismatches/` | pixel art, the wrong view | a copy of the original |
| `cant-tell/` | view or facing could not be judged | a copy of the original |
| `not-pixel-art/` | no usable pixel grid (painted, smooth, already true size) | a copy of the original |

`OUT/report.csv` has every measurement per picture (subject, view, grid status and size, flatness, shadow, facing clues, reason for its folder). Read the totals the command printed first; open `report.csv` only for the pictures you need.

## Rules that keep it cheap

1. Run on the whole folder in one command. Do not process pictures one at a time.
2. Use `--brief`. Read the totals and the few lines it prints; do not open the sprites.
3. Look at a picture only when a person asks, or for `_WEAK` sprites and `cant-tell/` where a decision is needed. Look at a contact sheet of several, not one at a time.
4. Trust the grid status: "weak" means check, "none" means the picture is not pixel art (say so; do not force it, unless the user gives a size with `--cell`).
5. Each picture takes about 1 to 3 seconds. A batch of 100 is a few minutes: tell the user the estimate before a very large batch.

## What it can and cannot do

- Finds the grid, including non-square pixels and soft or blurry blocks; reports clear, weak or none.
- Says character, building, scene or unclear. Object, and front-view buildings, come back "unclear" (not enough examples yet).
- Says isometric, orthogonal or unclear for non-characters. Provisional: tuned on a small set. A few pictures sit near the line.
- **Cannot judge which way a character faces** (diagonal or straight). It measures clues into `report.csv` and answers "can't tell".
- Finds ground shadows and names them contact or cast; on white or near-white grounds it says "can't tell" because a pale shadow looks like pale grey clothing.
- Cannot convert isometric art into straight-on art. It only sorts and flags.

## For people

The same method runs in a phone browser from one file, `tools/pixel-snap/pixel-snap.html` (nothing is uploaded). Full documentation: `tools/pixel-snap/README.md`. Tests: `cd tools/pixel-snap && python -m unittest`.

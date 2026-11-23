---
name: sprite-tools
description: Exact, no-blur pixel-art operations as commands - flip, fill with tolerance, flatten noisy colours, replace or swap colours. Use when the user wants a sprite edited in a way a script could do. Offline Python, no AI calls; far cheaper than writing the code again or looking at the pictures.
---

# Sprite Tools (for AI sessions)

**Run the tool. Do not write code for the same job, and do not look at the pictures unless asked.** Every tool prints what changed; read that.

Set up once: `pip install -r tools/sprite-tools/requirements.txt` (Python 3.9+). Command: `python tools/sprite-tools/sprite.py <tool> INPUT... [-o OUT.png | --out-dir DIR] [options] --json`. `--list` shows the tools; `<tool> --help` explains options. Colours are `#rrggbb` or `r,g,b[,a]`; points are `--at x,y`; tolerance is 0-100 percent.

`--json` prints one object per picture: `input`, `output`, `size`, `size_after`, `pixels_changed`, `colours_before`, `colours_after`, plus tool-specific fields. Exit 0 all fine, 1 a file unreadable, 2 a tool could not do its job (reason printed).

Tools:
- `turn --flip h|v`: mirror a sprite exactly.
- `fill --at x,y --colour C [--tolerance PCT] [--everywhere] [--corners]`: bucket fill that tolerates noisy near-shades. `fill --background [--colour C]`: starts from the border and fills the whole ground (default colour: transparent). Extra JSON: `pixels_filled`, `background_colour`.
- `flatten [--tolerance PCT] [--at x,y] [--no-merge] [--no-edges] [--min-speck N]`: make noisy areas one even colour and sharpen edges (three passes, each switchable). Run it on a Pixel Snap output, not on the raw big picture. Extra JSON: `pass1_pixels`, `pass2_pixels`, `pass3_pixels`. Not yet checked on real Midjourney sprites: look at a before/after sheet before trusting it on details.
- `replace --from C | --at x,y  --to C [--tolerance PCT] [--connected] [--corners]`: change one colour and its close shades into another. `replace --map FILE`: a palette swap (one `old new` pair per line, nearest pair wins). Extra JSON: `pixels_replaced`, `pairs`, `pairs_used`.

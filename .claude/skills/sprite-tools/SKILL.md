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

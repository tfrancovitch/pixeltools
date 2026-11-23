# Sprite Tools

Small, exact tools for pixel-art sprites. No AI inside, no blur, no smoothing: Python (numpy and Pillow) is the reference, and each phone page gives the same pixels (proved by a test). Free, GNU GPL v3 or later.

```
pip install -r tools/sprite-tools/requirements.txt
python tools/sprite-tools/sprite.py --list
python tools/sprite-tools/sprite.py <tool> INPUT... [-o OUT.png | --out-dir DIR] [options] [--json] [--brief] [--jobs N]
```

- Several inputs (or a wildcard) process a batch. Outputs are named `<name>_<tool>.png`, next to the input unless `--out-dir` says otherwise.
- `--json` prints one JSON object per picture (input, output, size, what changed, colours before and after). `--brief` prints one short line. The default is a plain sentence.
- Exit code 0: all worked. 1: a file could not be read. 2: a tool could not do its job on some picture (the reason is printed).
- `python sprite.py <tool> --help` explains every option, with an example.
- Pages for phones are in `pages/` (open `pages/index.html`); they work offline and make no network requests. Rebuild them with `python web/build.py`.

**Colours** are written `#rrggbb`, `#rrggbbaa` or `r,g,b[,a]`. A point is `--at x,y` (pixels from the top-left, starting at 0). **Tolerance** is a percentage: 0 means exactly this colour, 100 means every colour (the cut-off is tolerance / 100 × 510, in straight-line RGBA distance). Fully transparent pixels count as one colour. "Connected" means touching side by side; `--corners` also counts diagonals.

**Not yet tuned on real pictures.** The tolerance defaults and other numbers in `spritetools/tuning.py` were set on drawn pictures with noise and JPEG damage, because no real Midjourney pictures were available. Treat them as provisional.

## turn

Flip a sprite exactly. `--flip h` mirrors left-right, `--flip v` top-bottom. (Rotate and scale arrive in a later slice.)

```
python sprite.py turn hero.png --flip h
```

Page: `pages/turn.html`, two buttons. Both versions give the same pixels.

## fill

Bucket fill that copes with noisy AI pictures. A normal fill stops at the exact colour; this one fills every close shade.

```
python sprite.py fill sprite.png --at 40,12 --colour '#c83030'            # fill the connected area around 40,12
python sprite.py fill sprite.png --background                             # make the whole ground transparent
python sprite.py fill sprite.png --at 5,5 --everywhere --colour 0,0,0     # every close pixel, connected or not
```

- `--at x,y`: where to start. The colour at that point is the one that is matched.
- `--colour`: what to paint (default: transparent, `#00000000`).
- `--tolerance PCT`: how close counts as the same colour (default 10).
- `--everywhere`: fill every close pixel in the picture, not only the connected area.
- `--background`: needs no point. It looks at the picture's border, fits a gentle gradient to it, and fills every pixel that touches the border and stays close to that gradient, however much the ground varies. A ground-coloured pocket the sprite fully encloses (the gap inside a ring) is kept.
- `--corners`: count corner-touching pixels as connected.

`--json` fields: `pixels_filled`, `pixels_changed`, and for `--background` the `background_colour` it found.

Limits: a sprite part that is very close in colour to the ground (skin against a pale sky) can be partly eaten by `--background` if its edge is blurred; lower the tolerance for those. The defaults are provisional (not tuned on real Midjourney pictures yet): on drawn pictures with noise and JPEG damage at quality 50 to 90, `--background` at the default tolerance fills all of the ground except under 0.5 percent.

Page: `pages/fill.html` (tap the picture, or tick "fill the whole background").

## flatten

The opposite of dithering. AI pictures are never flat: a red shirt is twenty slightly different reds, and the edge between the shirt and an arm is a band of in-between colours. Flatten makes areas one even colour and the edges sharp, in three passes. Each pass can be switched off, and each is tested alone.

```
python sprite.py flatten sprite.png                        # the whole picture
python sprite.py flatten sprite.png --at 30,28             # only the shirt around 30,28 (and its edge)
python sprite.py flatten sprite.png --no-edges --min-speck 0 --tolerance 8     # only pass 1
```

1. **Merge near colours.** Colours within `--tolerance` (default 6) of each other become one: the most used colour in a group wins. Gradients are not chained into one colour.
2. **Sharpen edges** (`--edges` / `--no-edges`, default on). A pixel squeezed between two different areas (above and below, or left and right) whose colour lies on the straight line between them is a mix; it is given to the nearer side. Repeated up to three times. A pixel that is not a mix is never touched, and a shading step that is an area of its own (a dark band of the shirt) is kept, because it is not squeezed between two areas.
3. **Absorb specks** (`--min-speck N`, default 2, 0 turns it off). A patch of up to N pixels, touching only one other colour, takes that colour. To keep a one-pixel eye or highlight, it is only absorbed when its colour is also close to its surroundings (within 25 percent).

With `--at x,y` only the connected area of the touched colour (within tolerance) is merged, and only that area and its one-pixel edge may change; everything else is left exactly alone.

`--json` fields: `pixels_changed`, `pass1_pixels`, `pass2_pixels`, `pass3_pixels`, `colours_before`, `colours_after`.

What is proven, and what is not: on drawn sprites (a flat sprite enlarged, blurred, noised, JPEG-damaged, shrunk back with Pixel Snap) flatten returns the original colours on at least 97 percent of the pixels and the original number of colours exactly (24 of 24 runs). On a harsher damage of our own (half the edge pixels are mixes, plus noise and strays) it repairs most but not all: about 90 to 95 percent right, and it removes over 97 percent of the stray colours. **It has not been tried on real Midjourney pictures**: that part of the plan's gate is open, and the numbers in `tuning.py` are provisional. A before/after picture of the drawn tests is in `docs/handbacks/evidence/`.

Page: `pages/flatten.html` (switches for each pass; tap the picture to flatten one area).

## Tests

```
cd tools/sprite-tools
python -m unittest discover tests -v     # exact tests; the browser parts run when Node and Playwright are installed
```
The browser parts are a pixel-for-pixel comparison of Python and the page code on the same pictures (`tests/parity.js`), and a phone-width check of every page (`tests/smoke.js`).

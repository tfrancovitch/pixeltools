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

## Tests

```
cd tools/sprite-tools
python -m unittest discover tests -v     # exact tests; the browser parts run when Node and Playwright are installed
```
The browser parts are a pixel-for-pixel comparison of Python and the page code on the same pictures (`tests/parity.js`), and a phone-width check of every page (`tests/smoke.js`).

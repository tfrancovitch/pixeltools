# Pixel Snap

AI image tools such as Midjourney draw "pixel art" as a big picture of pixel art. Each chunky square you see is really dozens of real pixels with soft edges and small colour noise, and the grid wobbles. Pixel Snap finds the real grid and rebuilds the picture so **one visible pixel becomes one actual pixel**. The result can be any size (64×64, 67×45, whatever the picture really is), and it opens cleanly in a pixel editor.

Two versions, same method:

| File | Use it for |
|------|------------|
| `pixel-snap.html` | One picture at a time, on a phone or computer. Open the file in a browser. Works offline; nothing is uploaded. |
| `pixel_snap.py` | Batches and scripts. Needs Python 3.9+, numpy and Pillow (`pip install numpy pillow`). |

## Python

```
python pixel_snap.py picture.png                  # writes picture_snapped.png
python pixel_snap.py *.png --scale 8 -o out/      # many files, enlarged 8x (for moodboards)
python pixel_snap.py picture.png --cell 12.5      # you set the pixel size
python pixel_snap.py picture.png --colors 16      # also limit the palette
python pixel_snap.py picture.png --no-follow      # assume a perfectly straight grid
python pixel_snap.py *.png --check-only           # only report each picture's view; save nothing
python pixel_snap.py *.png --skip-isometric       # convert everything except isometric pictures
python pixel_snap.py sprite.png --transparent     # also make the plain background transparent
```

Every line of output starts with what the picture is: `[CHARACTER]`, `[BUILDING]`, `[SCENE]` or `[UNCLEAR]`. For anything that is not a character, the line also gives the view (isometric, orthogonal or unclear). Characters are judged on which way they face, not on isometric or orthogonal; that check is not built yet, so the line says so.

From Python code: `pixel_snap.snap_image(PIL_image)` returns a `Result` whose `.rgba` is the sprite.

## What is it? (character, building, scene)

The first question the tool answers, from the shape of the subject:

- **Scene**: the picture's border is busy (a whole landscape or village), not a lone sprite on a plain background.
- **Building**: a lone subject that is roughly square, with a pointed bottom (the diamond footprint of an isometric base) and a roof narrower than the body.
- **Character**: a lone subject at least 1.4 times as tall as wide.
- **Unclear**: anything else. A chibi character (nearly square), an object, or a front-view building with a flat base lands here, and the report says so. "Object" is not a category yet; it needs real examples.

On the 102 test pictures: right on 98. No building was called a character. The misses are two chibi characters (nearly square, so "unclear") and two subjects standing on a full painted background (called "scene"). The building rule was set from only three isometric buildings, so it is provisional until more examples arrive.

## Is there a ground shadow? (finding only so far)

For a lone sprite on a plain or gradient ground, the tool looks for a **ground shadow**: a flat patch of the ground colour made darker by a steady amount (between about 45% and 92% of the ground brightness), lying on the open ground at the subject's base and touching the subject, wider than tall. The report says where it falls ("to the left", "under the base") and how dark it is. Removing shadows comes in the next step; this step only finds them.

What it deliberately does not do:

- **White or near-white grounds.** A pale grey shadow looks the same as pale grey shoes or clothing, so the tool answers "can't tell" rather than guess.
- **Very dark shadows** (darker than 45% of the ground, for example a black shadow on a dark floor): treated as part of the subject.
- **Whole scenes** and **sprites on a full painted background**: their shadows are part of the picture.
- Sprite shading is never touched: only patches that lie on the open ground count.

On the 102 test pictures: of 10 labelled shadows, 7 found; no false alarms among 16 shadow-free pictures; 64 pictures on white grounds answered "can't tell". On 36 drawn sprites with drawn shadows (four grounds, three shapes, three darknesses), the found shadow overlaps the true one by 91% on average (worst 87%).

## How sure is the grid? (clear, weak, none)

The tool reports one of three answers and always says why:

- **Clear grid.** Strong, regular edges, and the blocks are flat inside. The picture is snapped.
- **Weak grid** (used, but flagged "check the result"). Real but thin evidence: soft or blurry blocks, a painted look, or width and height that disagree about the pixel size. It is snapped anyway; look at the result before using it.
- **No grid.** Nothing is saved, and the report says what it found (best guess and scores). Smooth anime or vector art, sketches and paintings end up here. To pixelate such a picture anyway, give a size: `--cell 16` makes each 16 by 16 block of the original one pixel.

Two details that matter on real Midjourney pictures:

- **Pixels are not always square.** Some portraits are stretched a little, so width and height are measured separately (for example 35.8 by 40.7). When one direction latches onto half the true size, the other direction's answer corrects it.
- **Flatness.** The test that tells pixel art from a painting: how much of the picture's colour variation does the grid explain? Real sprites, even blurry ones, are above 0.90. Painted landscapes with pixel edges are around 0.8 (weak). Smooth art is around 0.7 or lower (no grid).

## Lone sprite or whole scene? (framing)

The tool first looks at the picture's border. A plain colour or a gentle gradient all the way round means a **lone sprite on a background** ("isolated"); a busy border means a **scene**. It also makes a rough mask of the subject (everything that differs from the background). Option `--transparent` then makes the background around a lone sprite transparent. Only background that connects to the edge is removed, so a white shirt on a white background, or the gap inside an arm held against the hip, stays. Ground shadows are not background and stay too (they are handled in a later step).

Tested on 102 real pictures: right on 100. The two it gets wrong are a character standing on a full textured field and a church painted into its landscape; those look like scenes to the test ("subject on background" is not separated from "scene" yet).

## Isometric or straight-on? (buildings, objects and scenes)

Midjourney often draws isometric art (diamond floors, blocks seen from a corner) when you want straight-on or top-down art. For buildings, objects and scenes the tool reports the view; characters are judged on which way they face instead (not built yet).

How it decides, with no AI and **no pixel grid needed**:

1. Find the edges, and keep only spots where the edge direction stays consistent over a wider neighbourhood. A long straight edge is consistent; foliage, grass and texture are not, so trees stop hiding the lines.
2. Measure how that consistent edge weight is spread over the directions.
   - **Isometric**: a good share sits on the classic slopes (about 23 to 34 degrees, which covers the 2:1 pixel slope and the 30 degree slope), in **both** directions (rising and falling walls), with far less on horizontal lines.
   - **Orthogonal**: most of it sits on horizontal and vertical lines.
   - **Unclear**: neither, or the edge directions are spread evenly in every direction. Smooth round things (barrels, pots, apples) look like that, so the tool says so instead of guessing.
3. For crisp pixel art, the blur is sized to the pixel so that staircase edges read as the line they approximate.

On the 15 batch-1 pictures that are not characters: **all 15 right** (6 isometric, 9 straight-on), none "unclear". The closest call is the painted church 0090 (isometric, weaker diagonal direction 0.07 against a cut-off of 0.045). The cut-offs come from those 15 pictures plus drawn scenes, so they are provisional until the held-back batch and the object batch confirm them. Option `--skip-isometric` leaves isometric buildings, objects and scenes out of a batch.

## How it works

1. **Find the grid.** Add up the colour jumps along every column and row. Real pixel edges show up as a regular comb of peaks. Check how strongly that signal repeats at every candidate pixel size (fractions allowed, such as 12.4) and at its multiples, compared with the spots halfway between. Multiples of the true size repeat equally well, so the smallest size that scores almost as well as the best wins. Then the size and starting offset are fine-tuned over the whole image.
2. **Follow the wobble.** Each cell edge snaps to the strongest colour change nearby, so a grid that drifts is tracked rather than assumed straight.
3. **One pixel per cell.** Each cell becomes the median colour of its middle, which skips the blurry edges.
4. **Tidy the colours.** Shades that differ only by noise merge. An optional limit reduces the palette further.

Width and height are measured separately.

## Limits

- Very small cells (about 6 px or less) in a heavily JPEG-compressed image can smear colours between neighbours. The size is still found; some colours come out wrong.
- A picture with no regular grid (a photo, or art that is already true size) reports "no clear grid". Use the manual pixel size.
- The view check only sees straight lines. An isometric *character* (no hard diagonals) comes back "unclear", not "isometric". It has been tested on drawn isometric, front-view, top-down and blob scenes (made to look like Midjourney output), and on four real Midjourney characters (all "unclear", as expected). It has **not** yet been tested on real Midjourney isometric images; the cut-offs are set from drawn scenes and may need adjusting.
- A very flat picture with few edges (for example, a few plain rectangles on one background) can fail grid-finding, and then the view is reported as "unclear" too.
- Midjourney does not keep to a small palette, so a result can still hold 80 to 200 slightly different colours. For a clean sprite, limit them (`--colors 16` or the "Limit colors" slider) and finish by hand in a pixel editor.
- Testing so far: pictures made by enlarging known sprites with soft edges, noise and JPEG damage (exact answers known), plus four real Midjourney images checked by eye (no exact answers known). The first version of the detector failed all four real images; the tests now include shapes like them. Real-world failures are welcome as bug reports.

## Tests

```
python -m unittest -v
```

Each test draws a known sprite, enlarges it by an awkward amount, damages it, and checks that the exact sprite comes back.

## License

GNU GPL v3 or later. See `LICENSE` at the top of the repository.

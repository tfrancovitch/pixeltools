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

Every line of output starts with the verdict: `[ISOMETRIC]`, `[ORTHOGONAL]` or `[UNCLEAR]`.

From Python code: `pixel_snap.snap_image(PIL_image)` returns a `Result` whose `.rgba` is the sprite.

## Lone sprite or whole scene? (framing)

The tool first looks at the picture's border. A plain colour or a gentle gradient all the way round means a **lone sprite on a background** ("isolated"); a busy border means a **scene**. It also makes a rough mask of the subject (everything that differs from the background). Option `--transparent` then makes the background around a lone sprite transparent. Only background that connects to the edge is removed, so a white shirt on a white background, or the gap inside an arm held against the hip, stays. Ground shadows are not background and stay too (they are handled in a later step).

Tested on 102 real pictures: right on 100. The two it gets wrong are a character standing on a full textured field and a church painted into its landscape; those look like scenes to the test ("subject on background" is not separated from "scene" yet).

## Isometric or straight-on?

Midjourney often draws isometric art (diamond floors, blocks seen from a corner) when you want straight-on or top-down art. Pixel Snap reports the view first, before anything else:

- **Isometric**: most of the edge strength is on straight lines at about 22 to 38 degrees (the 2:1 pixel slope and the 30 degree slope), and there are almost no horizontal edges.
- **Orthogonal**: most of the edge strength is on horizontal and vertical lines (front views, top-down maps).
- **Unclear**: neither. People, animals and other round shapes have no long straight lines to judge by, so they land here. The tool says so instead of guessing.

The test runs on the snapped sprite, so it needs the pixel grid first, but it is reported first and `--skip-isometric` stops an isometric picture from being saved.

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

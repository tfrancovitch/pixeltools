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
```

From Python code: `pixel_snap.snap_image(PIL_image)` returns a `Result` whose `.rgba` is the sprite.

## How it works

1. **Find the grid.** Add up the colour jumps along every column and row. Real pixel edges show up as a regular comb of peaks. A search over pixel sizes (fractions allowed, such as 12.4) and offsets picks the comb that explains the peaks best. Multiples of the true size fit equally well, so the smallest size that fits almost as well as the best wins.
2. **Follow the wobble.** Each cell edge snaps to the strongest colour change nearby, so a grid that drifts is tracked rather than assumed straight.
3. **One pixel per cell.** Each cell becomes the median colour of its middle, which skips the blurry edges.
4. **Tidy the colours.** Shades that differ only by noise merge. An optional limit reduces the palette further.

Width and height are measured separately.

## Limits

- Very small cells (about 6 px or less) in a heavily JPEG-compressed image can smear colours between neighbours. The size is still found; some colours come out wrong.
- A picture with no regular grid (a photo, or art that is already true size) reports "no clear grid". Use the manual pixel size.
- Tested on pictures made by enlarging known sprites with soft edges, noise and JPEG damage, which is a stand-in for Midjourney output, not the same thing. Real-world failures are welcome as bug reports.

## Tests

```
python -m unittest -v
```

Each test draws a known sprite, enlarges it by an awkward amount, damages it, and checks that the exact sprite comes back.

## License

GNU GPL v3 or later. See `LICENSE` at the top of the repository.

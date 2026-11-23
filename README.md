# pixeltools

Free tools for pixel-art sprites, for game art and other projects.

## Pixel Snap 1.0

AI image tools such as Midjourney draw "pixel art" as a big picture of pixel art: each chunky square you see is really a block of dozens of soft, noisy pixels, on a grid that wobbles and is sometimes slightly stretched. Pixel Snap finds the real grid and rebuilds the picture so **one visible pixel becomes one real pixel**, and it tells you what each picture is, so a whole batch can be sorted without looking at it:

- **A character, a building or a whole scene.**
- **Isometric or straight-on**, for buildings, objects and scenes.
- **Ground shadows**: found, named *contact* or *cast* (a cast shadow implies a sun angle), and removable.
- **Pixel art or not**: painted or smooth pictures are reported as such instead of being forced.

Three ways to use it, with the same method and the same answers:

| For | Use | Needs |
|---|---|---|
| A phone or computer, by hand | `tools/pixel-snap/pixel-snap.html`: one file, installable as an app, works offline, nothing is uploaded | A browser |
| Big batches, scripts | `python tools/pixel-snap/pixel_snap.py in/*.png --sort out --want-view orthogonal --brief --jobs 4` | Python 3.9 or newer, `pip install -r tools/pixel-snap/requirements.txt` |
| An AI assistant doing the above cheaply | `.claude/skills/pixel-snap/SKILL.md` | The Python tool |

Full documentation, with every option, how it works and its limits: [`tools/pixel-snap/README.md`](tools/pixel-snap/README.md). A free public web address for the page is prepared in `site/` (see "A free public web address" in that file).

### What it cannot do yet

- **Which way a character faces** (straight on or turned to a diagonal). Tried without AI and it did not work; the tool reports "can't tell" and writes the measured clues to its report. The case is written up in `tools/pixel-snap/facing.py`.
- **Objects** (barrels, crates, trees) and **front-view buildings** come back "unclear": there were no examples to tune on.
- The isometric check and the character / building rule were tuned on one batch of 102 pictures, so a few pictures sit near the line. See `tools/pixel-snap/eval/SCORECARD.md` for exactly how it did on that batch.
- It sorts and flags; it cannot turn an isometric picture into a straight-on one.

### Planned for version 2

Many more labelled pictures (a labelling game where people answer "isometric or straight-on?", "which way is it facing?"), used to tune the thresholds, add objects, and try again on character facing. Later: a sprite maker and sprite turner.

## Repository

| Path | What |
|---|---|
| `tools/pixel-snap/` | The tool: Python module, browser version (`web/`), tests, scorecard and labels (`eval/`), documentation |
| `site/` | The browser version as an installable web app, ready for GitHub Pages |
| `.claude/skills/pixel-snap/` | The instruction file for AI assistants |
| `docs/` | The build plan, progress log and checklist |
| `CHANGELOG.md` | What is in each version |

## License

GNU General Public License, version 3 or later. See [LICENSE](LICENSE). You may use, study, change and share it; anything built from it stays under the same license.

# Pixel Snap: checklist

Updated 2026-11-23, at version 1.0.0. Plan: `PLAN_PIXEL_SNAP_V1.md`. Progress log: `PROGRESS_V1.md`. What is in the release: `../CHANGELOG.md`.

## Version 1.0.0: built

- [x] Scorecard and tuning file (A1)
- [x] Lone sprite or scene, transparent background (A2)
- [x] Graded grid answers: clear, weak, none (A3)
- [x] What is it: character, building, scene (B1)
- [x] Isometric or straight-on for buildings, objects and scenes (C1)
- [x] Wanted view and facing, sorting into four folders with a report (C3)
- [x] Ground shadows: find, name contact or cast, remove (D1, D2)
- [x] Character facing: tried without AI and ended as "can't tell", clues measured (C2)
- [x] Browser version, identical answers to Python on all 102 test pictures (E1, E2)
- [x] AI skill, `--brief` output, `--jobs`
- [x] Installable web app and publishing workflow prepared (`site/`, `.github/workflows/pages.yml`)
- [x] Odd inputs: tiny pictures refused clearly, 16-bit and rotated photos read correctly, huge pictures refused in the browser, no network requests from the page
- [x] Documentation: root README, tool README, CHANGELOG, requirements

## To release 1.0.0 (needs the owner)

- [ ] **Merge to `main`**: the license, Pixel Snap and plan branches are all still on side branches; `main` has only the first commit
- [ ] **Tag `pixel-snap-v1.0.0`** (after the merge)
- [ ] **Switch on the free web address**: Settings, Pages, Source: GitHub Actions (the workflow has not been run on GitHub yet)
- [ ] **Try the page on a phone** (the TCL 30 XE 5G): speed and layout are untested there; tell me what you see
- [ ] **Delete or keep** the public `mj-test-samples` branch (the test pictures are public while it exists)

## Version 2 (planned)

- [ ] **Labelling game** (L1 to L3): people answer "isometric or straight-on?", "which way is it facing?", "what is it?"; the answers become the labels file, with how many people agreed as the measure of how clear a picture is
- [ ] **Object batch** (about 30 pictures) to add an "object" category (B2)
- [ ] **Held-back batch** (never used for tuning) for an honest final score
- [ ] **Character facing**: retry with many labelled characters; or decide to allow a small offline model for characters only (outside the "no AI" rule)
- [ ] **Re-tune** the isometric check, the character / building rule and the shadow thresholds on the larger set (today: 15, 3 and 10 examples)
- [ ] Check the label files (the six clear diagonal characters, the shadow column); decide whether a base pad under a building counts as a shadow
- [ ] Already-true-size sprites: say so, instead of "not pixel art"
- [ ] A real Android app (APK), only if the installed web app is not enough
- [ ] The owner's earlier sprite-drawing code (`make_looks.py` was not in any repository I could see), a sprite maker and a sprite turner
- [ ] Pixelc (stated to be GPLv3, not yet checked): read its LICENSE before copying any code

## Known soft spots in 1.0.0

- The building rule rests on 3 isometric buildings, the isometric check on 15 pictures, the shadow check on 10 labelled shadows.
- Shadows 0034 (black on a dark floor), 0061 and 0091 are not found; stray dots can remain at the edge of a removed shadow.
- Pictures 0036 and 0055 get a weak grid because width and height disagree; which is right is unknown.
- The full test suite takes about 8 minutes.

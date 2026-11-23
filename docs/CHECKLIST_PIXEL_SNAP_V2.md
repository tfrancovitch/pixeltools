# Pixel Snap v2: checklist

Updated 2026-11-22 after slice C2. Plan: `PLAN_PIXEL_SNAP_V2.md`. Progress log: `PROGRESS_V2.md`.

## Built (Python tool, branch `plan-pixel-snap-v2`)

- [x] **A1** Scorecard, tuning file, shadow labels
- [x] **A2** Background, subject mask, lone sprite or scene, transparent background
- [x] **A3** Graded grid answers: clear, weak, none (the plan's gate was not met as written; weak counted as found there)
- [x] **B1** What is it: character, building, scene (building rule from only 3 examples)
- [x] **C1** Isometric or orthographic for buildings, objects, scenes (15 of 15 on batch 1; margins thin)
- [x] **C3** `--want-view`, `--want-facing`, `--sort` folders and `report.csv`
- [x] **D1** Find ground shadows (7 of 10; white grounds "can't tell")
- [x] **D2** Contact or cast, and `--shadows keep | remove-cast | remove-all`
- [x] **C2** Character facing: **tried, did not work without AI.** Clues are measured and reported; verdict is "can't tell". Stop rule applied.

## Still to build

- [ ] **B2** "Object" category. Blocked on the object tuning batch.
- [ ] **E1** Decide how to port to the browser page (hand-port, or run the Python in the browser)
- [ ] **E2** Browser page with all of the above. The phone page is still on the first version (grid-finder and old view check only).
- [ ] **L1** Labelling game: questions, wording, how many answers per picture, catching careless players
- [ ] **L2** Labelling game: build it and check it works for friends who are not signed in
- [ ] **L3** Labelling game: export answers to the labels file
- [ ] **F** Final: rewrite the README, tag `pixel-snap-v2.0`, score the held-back batch once, merge to `main`

## Needs Thomas

- [ ] **Object tuning batch**: about 30 objects, half isometric, half straight-on (list given earlier)
- [ ] **Held-back batch 2**: never used for tuning; section 7 of the plan says what it should hold
- [ ] **Decision on facing**: accept "can't tell" plus manual sorting, or allow a small offline model for characters only (outside the "no AI" rule), or wait for the labelling game's data
- [ ] **Check labels** in `tools/pixel-snap/eval/labels_mj_test_v1.csv`: the 6 clear diagonal characters (0031, 0033, 0034, 0069, 0092, 0093) and the shadow column (rows with notes first)
- [ ] **Base pads**: is the grey floor diamond under an isometric house (0089) a shadow to remove or part of the building?
- [ ] **Merge to `main`**: the license, Pixel Snap and plan branches are all on side branches; `main` still holds only the first commit
- [ ] **Delete or keep** the public `mj-test-samples` branch (your pictures are public while it exists)

## Outside the 16 slices of the plan

- [ ] **Sprite maker**: I could not find `make_looks.py` in Homestead; need its location or the file
- [ ] **Sprite turner**: nothing built yet
- [ ] **Pixelc**: you say it is GPLv3 like this repo; I still need to read its LICENSE file before copying any code

## Known soft spots (not blocking)

- Building rule rests on 3 isometric buildings; the isometric view check on 15 pictures. Both provisional until the batches arrive.
- Shadows: 0034 (black on dark floor), 0061 and 0091 are not found; stray dots can remain at the edge of a removed shadow.
- Grid: 0036 and 0055 are weak because width and height disagree; which is right is unknown.

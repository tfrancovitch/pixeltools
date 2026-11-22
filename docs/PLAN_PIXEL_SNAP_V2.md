# Pixel Snap v2: plan

**Author:** Victor (planning on Opus) · **For:** Thomas, and the Sonnet sessions that build it · **Date:** 2026-11-22 · **Status:** accepted by Thomas 2026-11-22, with two changes: an object batch for tuning (section 7) and a labelling game (Phase L)

## 1. What we are building, in one paragraph

Pixel Snap takes a Midjourney "pixel art" picture and turns it into a clean, true-size sprite. Version 2 adds three checks in front of the snapping, all without AI (no trained models, no internet, no paid services):

1. **What is it?** A character, a building, an object, or a whole scene.
2. **Which view, or which way is it facing?** For **buildings, objects and scenes**: isometric or orthographic (straight on). For **characters**: facing straight (front, back or side) or turned to a diagonal, and "mixed" when the torso and legs disagree. You set what you want; pictures that do not match are flagged or left out. (See Amendment 1: projection only matters for buildings, objects and scenes.)
3. **Shadows.** Keep them, or remove the cast shadows that show a sun angle while keeping the small contact shadows under feet and bases. Mixing sun angles across sprites in one game looks wrong, so this matters.

Then it snaps to the real pixel grid (the part that works today), can make the background transparent, and reports every decision with a reason. Every automatic decision has a manual override, and every check can answer "can't tell" instead of guessing.

## Amendment 1 (2026-11-22): characters are about facing, not projection

Thomas pointed out that orthographic art can also have diagonal movement and facing, so asking "isometric or orthographic?" of a character is the wrong question. The plan now splits by subject:

| Subject | Question | Why |
|---|---|---|
| Building, object, scene | Isometric or orthographic? | It is a property of how the whole thing is drawn, and it matters a lot for game tiles |
| Character | Facing straight (cardinal) or diagonal? Or mixed? | A character's projection is not what a game needs to match; its facing is |

What changed: the labels file (Thomas's old "iso" on a character is now `facing = diagonal`, "ort" is `cardinal`; he should check the six clear diagonal characters 0031, 0033, 0034, 0069, 0092, 0093), the scorecard (view scored on non-characters only; facing check added as a placeholder), slice C1 and C2 gates, the settings in C3, and the labelling game's questions. The baseline view check now has only 15 non-character pictures (6 isometric, 9 orthographic) to score against, which is another reason the object tuning batch matters.

## 2. What the first real test taught us

Thomas sent 102 Midjourney images and labelled each one isometric or orthographic, clear or not clear (`tools/pixel-snap/eval/labels_mj_test_v1.csv`). Victor added a subject label (character, building, scene) by eye.

| Finding | Evidence | What it means for the plan |
|---|---|---|
| The current view check fails on real images | All 102 came back "unclear"; it found 0 of the 4 clearly isometric buildings | Rebuild the view check (Phase C) |
| The grid-finder failed on 7 of 102 | 1, 2, 50 (smooth anime-style art, not really pixel art), 88, 89, 90 (isometric buildings), 100 (scene) | Fix or report "not pixel art" (slice A3) |
| For characters, "isometric" meant **turned to a diagonal** | Thomas labelled 23 characters "iso" (6 clear) and 64 "ort" (43 clear). Thomas, 2026-11-22: orthographic art can also have diagonal facings, so characters should be judged on facing, not projection | Characters get their own **facing** label and check (slice C2); the labels file now has `facing` columns for characters and `view` columns for everything else |
| AI characters mix views | Shoulders can face one way while hips and legs face another (Thomas) | Add a **mixed view** answer for characters |
| Isolated sprite vs full scene is easy | Border uniformity: every isolated sprite 0.92 or more, every scene 0.68 or less; two exceptions (78, 90) are a subject on a full background | Framing comes first and is cheap (slice A2) |
| Character vs building looks possible from shape | Height ÷ width: characters median 2.4, buildings 0.9 to 1.3; the overlaps (69, 92) are widened by a shadow or a sword | Remove shadows from the shape before judging it |
| Data gaps | **No objects** at all; only 4 buildings; no shadow labels | Thomas collects batch 2 (section 7) |

## 3. The new order of checks

Plain version: the report always starts with "what is it", then "which view", then "shadows", then the snapped result. Under the hood a few measurements are taken first, because the checks need them as inputs, but nothing is changed or saved until all checks have answered.

| Pass | Name | Answers | Override |
|---|---|---|---|
| 0 | Measure | Background colour, subject mask, pixel grid size | Pixel size (exists) |
| 1 | Subject | Framing (isolated / subject on background / scene), then category (character / building / object / scene / can't tell) | "Treat as" setting |
| 2 | Orientation | **Buildings, objects, scenes:** isometric / orthographic / can't tell. **Characters:** facing diagonal / cardinal (straight) / mixed / can't tell. With the reasons | "Want" setting: orthographic, isometric or either (buildings etc.); diagonal, cardinal or either (characters) |
| 3 | Shadows | No shadow / contact shadow / cast shadow, and its direction | Keep all / remove cast shadows / remove all ground shadows |
| 4 | Snap | True-size sprite (exists), optional transparent background | Existing settings |
| 5 | Report and save | One line or one banner per picture; batch mode sorts into folders | Skip or keep mismatches |

**What the tool cannot do:** turn an isometric picture into an orthographic one. That needs redrawing. The view setting filters and flags; it does not convert.

## 4. Ground rules for every slice

- **No AI.** numpy and Pillow only in Python; plain JavaScript in the browser. Every rule must be explainable in one sentence in the README.
- **Python first, browser later.** The Python version is the reference and the test bed. The browser version is ported once the methods stop changing (Phase E). This avoids building everything twice while it is still changing.
- **All tuning numbers in one place:** `tools/pixel-snap/tuning.py` (one named constant per number, with a comment saying where it came from). No loose numbers in the logic.
- **Every verdict carries its evidence** (the measured numbers) and a confidence. "Can't tell" is a correct answer, never an error.
- **Two kinds of test, both required:**
  1. *Exact tests* on drawn pictures where the right answer is known (as today: `test_pixel_snap.py`).
  2. *Scorecard* on Thomas's labelled real images: `python eval/scorecard.py <image folder> <labels.csv>` prints accuracy per check, a confusion table, and the list of misses. The scorecard file is saved after each slice (`eval/SCORECARD.md`) so we can see progress and catch slips.
- **Held-out set.** Tuning uses batch 1 (these 102). Batch 2 is **not looked at while tuning**; it is only scored once, at the end of each phase, to check that the rules work on pictures they were not tuned on. Overfitting to 102 images, 6 of them clear isometric characters, is the biggest risk in this plan.
- **Checkpoints.** Each slice ends with a commit and one line in `docs/PROGRESS_V2.md`: done, next, anything half-finished. A cut-off session loses at most one slice.
- **Images stay out of `main`.** The scorecard reads images from a folder you point it at. Only the labels file is committed.

## 5. Phases and slices

Each slice lists what to build, how it is checked, and the gate to pass before moving on. Times are rough working estimates for one Sonnet session; ask Thomas before anything expected to run past about 10 minutes of wall-clock compute.

### Phase A: foundations

**A1. Scorecard and labels** (small)
- Build `eval/scorecard.py`: runs the pipeline on a folder, compares with the labels CSV, prints and saves the scorecard. Columns it understands: `subject, framing, view, view_clear, facing, facing_clear, shadow`. Blank label = not scored.
- Move all existing numbers from `pixel_snap.py` into `tuning.py`.
- Pre-fill the `shadow` column for batch 1 by looking at each image (none / contact / cast), for Thomas to correct.
- Gate: scorecard runs on batch 1 in under 2 minutes and reproduces today's numbers (0 of 4 clear iso buildings found; 7 grid misses).

**A2. Background and framing** (medium)
- Estimate the background: the main border colour, allowing a gentle gradient. Build a subject mask (pixels far from the background, cleaned of specks, largest connected parts kept).
- Framing: isolated / subject on background / scene, from border uniformity plus the subject mask's share of the frame.
- New option: transparent background on output (isolated subjects only).
- Exact tests: drawn sprites on plain, gradient and noisy backgrounds; mask matches the drawn sprite.
- Gate: framing right on at least 100 of 102.

**A3. Grid-finder misses** (medium)
- Diagnose the 7 misses (1, 2, 50, 88, 89, 90, 100). Try measuring the grid on the subject mask only, and allow a weaker signal when the subject is clearly blocky.
- Add a "not pixel art" answer for smooth art (expected for 1, 2, 50) instead of a silent failure.
- Gate: grid found on at least 3 of 88, 89, 90, 100; no regressions in the exact tests; "not pixel art" on 1, 2, 50 or the reason they look blocky recorded.

### Phase B: what is it?

**B1. Character / building / scene** (medium)
- Measurements on the subject mask, with any ground shadow trimmed off (a rough trim is enough here; Phase D does it properly): height ÷ width, fill, share of long straight edges, left-right balance, a head-like narrower part on top, a gap between legs at the bottom, skin-like colours.
- A small, readable rule set (a score per category; highest wins; low margin = "can't tell"). No decision trees grown by code, so Thomas can read why.
- Gate on batch 1: characters vs buildings vs scenes at least 97 of 102 right, and no building called a character.

**B2. Objects** (small, needs the object tuning batch)
- Add "object" once real examples exist (barrels, crates, furniture, trees, tools, rocks). Likely cues: small or compact, not tall like a character, fewer long straight edges than a building.
- Gate: set after batch 2 arrives; at minimum, objects never called characters.

### Phase C: view (buildings, objects, scenes) and facing (characters)

**C1. Buildings, objects and scenes: line test, rebuilt** (medium)
- Work on the original picture (no grid needed), at two or three blur scales so trees and grass fade and long edges stay.
- Find long straight segments (a simple line finder on the edge map). Score the share of long-segment length on the isometric slopes (2:1 and 30 degrees, both ways) against horizontal and vertical.
- Extra isometric clue: a diamond-shaped top or base (two diagonal pairs meeting).
- Gate on batch 1, clear cases only (non-characters: 6 isometric = 88, 89, 90, 91, 95, 96; 7 orthographic = 94, 97 to 102): all 6 isometric found, **no orthographic picture called isometric**, at most 1 can't-tell among the orthographic. Batch 1 has only 13 clear non-character pictures, so this gate is rechecked once the object tuning batch arrives (slice B2).

**C2. Characters: facing (diagonal or straight)** (large, experimental; has a stop rule)
- Projection does not matter here: a character in a top-down (orthographic) game can face a diagonal, and a character in an isometric picture can face straight ahead. The test asks only which way the body is turned.
- Clues, each measured separately and reported:
  1. Face: where the eyes and nose sit inside the head (centred = front or back; at one edge = side; in between = diagonal).
  2. Feet: the line through both feet (level = side or front; tilted = diagonal) and their spacing.
  3. Torso vs legs: the left-right balance of the top half compared with the bottom half. If they point different ways, answer **mixed view** (Thomas's shoulders-versus-legs case).
  4. Ground shadow: a wide flat oval under the feet hints at a raised viewpoint.
- Combine by simple voting; disagreement between torso and legs gives "mixed"; weak signals give "can't tell".
- Gate on batch 1, clear cases only (6 diagonal = 31, 33, 34, 69, 92, 93; 43 cardinal): at least 5 of 6 diagonal found and at most 3 cardinal called diagonal.
- **Stop rule:** if the gate is not met after two tuning passes, stop. Ship characters as "can't tell" with the manual setting, and record which clues helped. Do not keep stacking rules to fit 6 examples.

**C3. The "want" setting and batch sorting** (small)
- Settings: for buildings, objects and scenes, want orthographic / isometric / either. For characters, want diagonal / cardinal / either. (A game might want diagonal-facing characters in an orthographic world, so these two settings are independent.)
- Batch mode writes into folders: `matches/`, `mismatches/`, `cant-tell/`, `not-pixel-art/`, plus a `report.csv` with every measurement.
- Gate: exact tests for the folder sorting; a batch-1 run produces the folders and the report.

### Phase D: shadows

**D1. Find ground shadows** (medium)
- A ground shadow is a region that is the background colour made darker by a steady amount, attached to the bottom of the subject. Find it by colour ratio to the background, connection to the subject's base, and flatness.
- Self-shading on the sprite itself is never touched.
- Exact tests: drawn sprites with drawn shadows (contact ovals and cast shadows at several angles), on plain and textured ground.
- Gate: shadows found on the drawn tests with at least 90 percent overlap; scorecard against the `shadow` labels from A1.

**D2. Contact or cast, and the setting** (medium)
- Contact shadow: small, roughly centred under the base, roughly symmetric. Cast shadow: reaches clearly to one side; report its direction (for example "falls to the lower left").
- Setting: keep all / remove cast shadows (keep contact) / remove all ground shadows. Removed shadow becomes background, or transparent when that option is on.
- Gate: on drawn tests, removal leaves the sprite untouched (pixel-exact outside the shadow); on batch 1, cast shadows found where labelled, with no sprite pixels removed (checked by eye on a contact sheet).

### Phase E: browser version

**E1. Decide the port route** (small): hand-port to JavaScript (what we do today), or run the Python itself in the browser with Pyodide (one codebase, but a slow first load on a phone, roughly 10 to 20 MB). Measure Pyodide's first load on a phone-sized test before deciding.

**E2. Port and settings** (medium to large): the new checks, the three settings (treat as, want, shadows), transparent background, and the verdict banners. Same results as Python on batch 1 (the scorecard must match).

### Phase F: release

- README rewrite, version tag `pixel-snap-v2.0`, final held-out scorecard on batch 2, merge to `main` on Thomas's yes.

## 6. Order and size

| Order | Slice | Size | Needs |
|---|---|---|---|
| 1 | A1 scorecard and labels | small | nothing |
| 2 | A2 background and framing | medium | A1 |
| 3 | A3 grid misses | medium | A2 |
| 4 | B1 character / building / scene | medium | A2 |
| 5 | C1 line test rebuilt | medium | A1 |
| 6 | D1 find shadows | medium | A2 |
| 7 | D2 contact or cast, setting | medium | D1 |
| 8 | C2 character facing (experiment) | large | B1, D1 |
| 9 | C3 want setting, batch folders | small | B1, C1 |
| 10 | B2 objects | small | batch 2 |
| 11 | E1, E2 browser | medium to large | everything above settled |
| 12 | F release | small | batch 2 held-out score |
| any time | L1 to L3 labelling game | small, medium, small | nothing (L3 needs A1's label format) |

Reasoning: the scorecard comes first because every later slice is judged by it. Shadows come before the character facing test because shadows distort the character's shape. The risky experiment (C2) is late and fenced by its stop rule, so the dependable parts ship even if it fails.

## 7. What Thomas needs to provide

**Object tuning batch** (used for tuning, like batch 1): about 30 objects (barrels, crates, furniture, tools, trees, rocks, plants), roughly half isometric and half orthographic. Needed before slice B2.

**Batch 2** (kept back for checking, not tuning), roughly:
- 20 **objects**: barrels, crates, furniture, tools, trees, rocks, plants. Half isometric, half orthographic.
- 15 more **buildings**: about half isometric, half orthographic (front view or top-down).
- 10 **characters** clearly turned to a diagonal, and 10 clearly straight on.
- 10 pictures with obvious **cast shadows** (sun to one side), and 10 with only a small shadow under the feet.

Victor or the builder pre-fills the label sheet; Thomas corrects it. Thomas never has to start a label sheet from blank.

## 8. Decisions (answered by Thomas, 2026-11-22: yes to all four)

1. **The view setting filters and flags; it does not convert.** Converting isometric art into orthographic art means redrawing it, which this tool can't do without AI. *Recommendation: accept.*
2. **Python first, browser later.** The phone page keeps today's features until Phase E. *Recommendation: accept; it halves the rework while the methods are still moving.*
3. **Where the test images live.** They are on the public branch `mj-test-samples` now. *Recommendation: keep test images off `main`. If you'd rather they weren't public, delete that branch and share images another way (for example the Remote Control folder on your PC).*
4. **Batch 2 is held out.** Builders never tune on it. *Recommendation: accept; it is the only honest check that the rules work beyond these 102.*

## Phase L: the labelling game (Thomas's idea, 2026-11-22)

A simple page where people see one picture at a time. First they say what it is (character, building, object or scene). Then, for a **character**: facing **straight** (front, back or side), **diagonal**, **mixed** (torso and legs disagree), or not sure. For anything else: **isometric**, **straight-on**, or not sure. Many people answering the same picture turns "clear or borderline" into a number (the share who agree), which is better than one person's judgement.

**L1. Design** (small): the questions and their wording (plain words, with one example picture of each answer so players share the same meaning; "mixed" offered for characters), how many answers per picture are enough (start at 5), and how to catch careless answers (a few pictures with known answers mixed in; answers from players who miss those are set aside).

**L2. Build** (medium): a page that shows pictures in random order, records answers in a shared store, and shows the player a running count. Likely a claude.ai artifact with a shared database, so no server is needed; check this works for players who are not signed in to Thomas's account before building on it. Pictures are uploaded to the page's own storage, not linked from GitHub.

**L3. Export** (small): a script that turns the answers into the labels CSV the scorecard reads, adding `agree_share` and `answers` columns; `view_clear` and `facing_clear` become "agree_share at least 0.8".

Rules: collect no names, emails or anything else about players beyond their answers; say so on the page. Pictures from the game used for tuning are not used for the held-out check, and the reverse.

Order: L1 and L2 can run alongside Phase A, because they touch none of the snap code. The scorecard (A1) reads whatever labels the game produces.

## 9. Recommended models

| Work | Model | Why |
|---|---|---|
| A1, A2, A3, B1, B2, C1, C3, D1, D2, E2, F | Sonnet | Normal coding against clear gates |
| Checking a slice's commit, re-running the scorecard, contact sheets | Haiku | Mechanical |
| C2 design review if its gate fails twice; E1 decision; final review before release | Opus | Judgement calls |

## 10. Risks

| Risk | Guard |
|---|---|
| Rules tuned to 102 pictures fail on the next 102 | Held-out batch 2; stop rule on C2; scorecard history |
| Character facing can't be judged reliably without AI | Stop rule; "can't tell" plus manual setting is an acceptable end state |
| AI art keeps surprising us (mixed views, painted backgrounds) | Every answer allows "can't tell" and "mixed"; every setting has a manual override |
| Two versions (Python and browser) drift apart | Port only settled methods; the scorecard must match on both |
| Phone performance in the browser | Measure in E1 before committing to a route |

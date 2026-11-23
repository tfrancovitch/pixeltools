# Pixel Snap scorecard

Labels: `labels_mj_test_v1.csv` · pictures scored: 102 · run time: 48 s
Code version: tuning.py as committed; see git log. Pictures are not stored in the repository.

## Pixel grid

Clear grid on **88**, weak grid (used, flagged) on **9**, no grid on **5** of 102.
- Weak: 0036, 0055, 0089, 0090, 0094, 0095, 0096, 0098, 0100
- None: 0001, 0002, 0006, 0050, 0088

## View check (buildings, objects, scenes): all labelled pictures

| labelled \ tool said | iso | ort | cant | right | wrong | can't tell |
|---|---|---|---|---|---|---|
| iso (n=6) | 6 | 0 | 0 | 6 | 0 | 0 |
| ort (n=9) | 0 | 9 | 0 | 9 | 0 | 0 |

## View check (buildings, objects, scenes): clear cases only (view_clear = y)

| labelled \ tool said | iso | ort | cant | right | wrong | can't tell |
|---|---|---|---|---|---|---|
| iso (n=6) | 6 | 0 | 0 | 6 | 0 | 0 |
| ort (n=7) | 0 | 7 | 0 | 7 | 0 | 0 |

## View check (buildings, objects, scenes): not-clear cases (view_clear = n)

| labelled \ tool said | iso | ort | cant | right | wrong | can't tell |
|---|---|---|---|---|---|---|
| iso (n=0) | 0 | 0 | 0 | 0 | 0 | 0 |
| ort (n=2) | 0 | 2 | 0 | 2 | 0 | 0 |

### Misses among clear cases

- Clear isometric not found (0): none
- Clear orthographic called isometric (0): none

## Framing check

**Right on 100 of 102.**

| labelled \ tool said | isolated | subject_on_background | scene | cant | right | wrong | can't tell |
|---|---|---|---|---|---|---|---|
| isolated (n=89) | 89 | 0 | 0 | 0 | 89 | 0 | 0 |
| subject_on_background (n=2) | 0 | 0 | 2 | 0 | 0 | 2 | 0 |
| scene (n=11) | 0 | 0 | 11 | 0 | 11 | 0 | 0 |

Wrong: 0078 (labelled subject_on_background, said scene; border 0.01 plain, subject 0.99), 0090 (labelled subject_on_background, said scene; border 0.39 plain, subject 0.66)

## Subject check (character / building / scene)

**Right on 98 of 102.**

| labelled \ tool said | character | building | object | scene | cant | right | wrong | can't tell |
|---|---|---|---|---|---|---|---|---|
| character (n=87) | 84 | 0 | 0 | 1 | 2 | 84 | 1 | 2 |
| building (n=4) | 0 | 3 | 0 | 1 | 0 | 3 | 1 | 0 |
| scene (n=11) | 0 | 0 | 0 | 11 | 0 | 11 | 0 | 0 |

Wrong or unsure: 0069 (labelled character, said cant), 0078 (labelled character, said scene), 0090 (labelled building, said scene), 0092 (labelled character, said cant)

**Buildings called characters: 0**

## Ground shadow found (slice D1)

Of 90 lone sprites with a shadow label: **23 of 26 right** where the tool made a call; 64 on white or near-white grounds were answered "can't tell" (a pale shadow cannot be told from pale grey parts of the sprite).

| labelled \ tool said | yes | no | cant | right | wrong | can't tell |
|---|---|---|---|---|---|---|
| yes (n=10) | 7 | 3 | 0 | 7 | 3 | 0 |
| no (n=80) | 0 | 16 | 64 | 16 | 0 | 64 |

Wrong: 0034 (labelled yes, said no), 0061 (labelled yes, said no), 0091 (labelled yes, said no)

## Contact or cast shadow (slice D2)

Of 10 labelled shadows, **7 named correctly** (a shadow the tool did not find counts as can't tell). The labels are drafts made by eye and are the weakest part of this check.

| labelled \ tool said | contact | cast | cant | right | wrong | can't tell |
|---|---|---|---|---|---|---|
| contact (n=4) | 3 | 0 | 1 | 3 | 0 | 1 |
| cast (n=6) | 0 | 4 | 2 | 4 | 0 | 2 |

Not matching: 0034 (labelled cast, said cant), 0061 (labelled contact, said cant), 0091 (labelled cast, said cant)

## Facing check (slice C2): ended as can't tell

87 characters carry a facing label (clear diagonal: 6, clear cardinal: 43). The tool answered: unclear 84, n/a 3.

The plan's stop rule applied: no geometry-only rule found at least 5 of the 6 clear diagonal characters while calling at most 3 of the 43 clear cardinal ones diagonal (best of 1,042 candidate rules: 4 found with 3 false calls). The clues are measured and written to the report; `python eval/facing_probe.py <images> <labels>` reproduces the search.


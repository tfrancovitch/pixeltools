# Pixel Snap scorecard

Labels: `labels_mj_test_v1.csv` · pictures scored: 102 · run time: 37 s
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

## Facing check

Not built yet (slice C2). 87 labelled pictures are waiting for it.

## Shadow check

Not built yet (slice D1). 90 labelled pictures are waiting for it.


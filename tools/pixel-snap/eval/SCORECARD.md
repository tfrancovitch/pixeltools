# Pixel Snap scorecard

Labels: `labels_mj_test_v1.csv` · pictures scored: 102 · run time: 23 s
Code version: tuning.py as committed; see git log. Pictures are not stored in the repository.

## Pixel grid found

Found on **95 of 102**. Missed: 0001, 0002, 0050, 0088, 0089, 0090, 0100

## View check: all labelled pictures

| labelled \ tool said | iso | ort | cant | right | wrong | can't tell |
|---|---|---|---|---|---|---|
| iso (n=29) | 0 | 0 | 29 | 0 | 0 | 29 |
| ort (n=73) | 0 | 0 | 73 | 0 | 0 | 73 |

## View check: clear cases only (view_clear = y)

| labelled \ tool said | iso | ort | cant | right | wrong | can't tell |
|---|---|---|---|---|---|---|
| iso (n=12) | 0 | 0 | 12 | 0 | 0 | 12 |
| ort (n=50) | 0 | 0 | 50 | 0 | 0 | 50 |

## View check: not-clear cases (view_clear = n)

| labelled \ tool said | iso | ort | cant | right | wrong | can't tell |
|---|---|---|---|---|---|---|
| iso (n=17) | 0 | 0 | 17 | 0 | 0 | 17 |
| ort (n=23) | 0 | 0 | 23 | 0 | 0 | 23 |

### Misses among clear cases

- Clear isometric not found (12): 0031, 0033, 0034, 0069, 0088, 0089, 0090, 0091, 0092, 0093, 0095, 0096
- Clear orthographic called isometric (0): none

## Framing check

**Right on 100 of 102.**

| labelled \ tool said | isolated | subject_on_background | scene | cant | right | wrong | can't tell |
|---|---|---|---|---|---|---|---|
| isolated (n=89) | 89 | 0 | 0 | 0 | 89 | 0 | 0 |
| subject_on_background (n=2) | 0 | 0 | 2 | 0 | 0 | 2 | 0 |
| scene (n=11) | 0 | 0 | 11 | 0 | 11 | 0 | 0 |

Wrong: 0078 (labelled subject_on_background, said scene; border 0.01 plain, subject 0.99), 0090 (labelled subject_on_background, said scene; border 0.39 plain, subject 0.66)

## Subject check

Not built yet (slice B1). 102 labelled pictures are waiting for it.

## Shadow check

Not built yet (slice D1). 90 labelled pictures are waiting for it.


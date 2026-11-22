# Pixel Snap v2: progress

One line per finished slice (see docs/PLAN_PIXEL_SNAP_V2.md). Newest last.

- 2026-11-22 Plan written; batch-1 labels saved in tools/pixel-snap/eval/labels_mj_test_v1.csv (view labels: Thomas; subject and framing: Victor, by eye). Next: A1 scorecard, after Thomas answers the plan's section 8.
- 2026-11-22 Thomas said yes to the plan's four decisions; added an object tuning batch and Phase L (labelling game). Next: A1 scorecard.
- 2026-11-22 **A1 done.** All tuning numbers moved into `tools/pixel-snap/tuning.py` (behaviour unchanged: 12 tests pass). `eval/scorecard.py` grades the tool against a labels CSV; batch 1 runs in 17 s and reproduces today's numbers: grid found 95 of 102 (misses 0001, 0002, 0050, 0088, 0089, 0090, 0100); view check 0 of 12 clear isometric found, 0 clear orthographic called isometric, everything "cant". Shadow column pre-filled by eye from thumbnails (draft: contact 6, cast 4, none 82, scenes left blank); Thomas to correct. Next: A2 background and framing.

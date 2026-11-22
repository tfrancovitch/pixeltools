# Tuning numbers for Pixel Snap: every threshold lives here, with where it came from.
# Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
#
# Change a number here, then run eval/scorecard.py to see what it did to the real test
# pictures. Do not tune against the held-out batch (see docs/PLAN_PIXEL_SNAP_V2.md).

# ---- grid finding -------------------------------------------------------------------
GRID_MIN_PIXEL = 2.0           # smallest pixel size searched (in original pixels)
GRID_MAX_FRACTION = 1 / 6      # largest pixel size searched, as a share of the picture's side
GRID_SIZE_STEP = 1.001         # coarse search step (0.1%); finer than the grid can drift
GRID_HARMONICS = 10            # how many multiples of a candidate size are checked
GRID_LAG_LIMIT = 0.7           # multiples are checked only up to this share of the side
GRID_MIN_LAGS = 6              # fewer multiples than this = too few to trust (chance matches)
GRID_DETREND_WINDOW = 33       # removes slow background from the edge signal
GRID_SMALLEST_FIT = 0.8        # smallest size scoring this share of the best wins (multiples tie)
GRID_REFINE_LOW = 0.985        # fine search range around the coarse answer: -1.5% ...
GRID_REFINE_HIGH = 1.0151      # ... to +1.5%
GRID_REFINE_STEP = 0.0001
GRID_WINDOW_RANGE = 1.06       # look this far above the smallest fit for the best local score
MIN_GRID_SCORE = 0.15          # below this the picture has no clear grid (real images scored 0.19+)
NOISE_FACTOR = 3.5             # small pictures need a stronger signal: threshold >= factor / sqrt(side)

# ---- colours ------------------------------------------------------------------------
COLOUR_MERGE_TOLERANCE = 14.0  # shades closer than this (RGB distance) become one colour

# ---- view check (isometric / orthogonal), v1 line test ------------------------------
# Known to fail on real Midjourney scenes (batch 1: 0 of 14 clear isometric found). Phase C replaces it.
VIEW_BLUR_SIGMA = 1.2
VIEW_MAGNITUDE_KEEP = 0.15     # edges weaker than this share of the strongest are ignored
VIEW_AXIS_TOLERANCE = 6        # degrees: within this of horizontal or vertical counts as axis-aligned
VIEW_ISO_MIN_DEG = 20          # isometric slopes: 2:1 pixel lines (26.6) and 30 degree lines
VIEW_ISO_MAX_DEG = 38
ISO_DIAGONAL_MIN = 0.35        # share of edge strength on isometric slopes
ISO_HORIZONTAL_MAX = 0.12      # isometric art has almost no horizontal edges
ORTHO_AXIS_MIN = 0.45          # share of edge strength on horizontal or vertical lines

# ---- background and framing (slice A2) ----------------------------------------------
BG_BORDER_BAND = 0.02          # border strip examined for the background: this share of the short side ...
BG_BORDER_MIN_PX = 2           # ... but at least this many pixels
BG_TOLERANCE = 40              # RGB distance (sum of channel differences) still counted as background
BG_FIT_ROUNDS = 3              # rounds of "fit a gentle gradient, drop outliers (the sprite's feet), refit"
SUBJECT_DISTANCE = 60          # a pixel this far from the background is part of the subject
MASK_MAX_SIDE = 256            # the subject mask is built at this size, for speed
SPECK_SHARE = 0.002            # blobs smaller than this share of the picture are dust, not subject
FRAMING_UNIFORM_MIN = 0.8      # border at least this plain = isolated (batch 1: sprites 0.92+, scenes 0.68-)
FRAMING_SUBJECT_MAX = 0.9      # a "subject" covering more of the picture than this is the whole scene
TRANSPARENT_TOLERANCE = 40     # background removal: how close to the background colour still goes transparent

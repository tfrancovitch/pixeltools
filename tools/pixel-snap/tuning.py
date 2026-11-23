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

# ---- view check (isometric / orthogonal), rebuilt in slice C1 -----------------------
# Works on the original picture, no grid needed. Spots where the edge direction is coherent over a wider
# neighbourhood (long straight edges) count; foliage and texture, whose edges point every which way, do not.
# Thresholds are set from batch 1's 15 non-character pictures (6 isometric, 9 orthographic): provisional.
VIEW_SIDE = 512                # pictures are shrunk to this long side (or enlarged to at least VIEW_MIN_SIDE)
VIEW_MIN_SIDE = 384
VIEW_GRAD_SIGMA = 1.0          # blur before taking edges, at VIEW_SIDE
VIEW_CELL_BLUR = 0.7           # when the pixel size is known, blur by this share of a pixel, so a stair step reads as part of a line
VIEW_CELL_MIN_FLATNESS = 0.92  # ... but only for crisp pixel art (flat blocks); soft or painted pictures do better with the small fixed blur
VIEW_CELL_WINDOW = 2.5         # ... and make the coherence window at least this many pixels wide
VIEW_WINDOW_FRACTION = 0.008   # coherence window (sigma) as a share of the long side: 4 px at 512
VIEW_COHERENCE_MIN = 0.8       # a spot counts only if its edge direction is this consistent (0 = random, 1 = a straight line)
VIEW_ENERGY_PERCENTILE = 60    # ... and only if its edge strength is above this percentile of the picture
VIEW_MIN_COVERAGE = 0.002      # fewer coherent spots than this share of the picture = nothing to judge by
VIEW_AXIS_TOLERANCE = 6        # degrees: within this of horizontal or vertical counts as axis-aligned
VIEW_ISO_MIN_DEG = 23          # the classic isometric slopes: 2:1 pixel lines (26.6) and 30 degree lines, with a little room
VIEW_ISO_MAX_DEG = 34
VIEW_MAX_ENTROPY = 0.92        # edge directions spread this evenly (1 = perfectly even) mean round or organic shapes: nothing to judge by
                               # (round drawn shapes 0.97+; every real picture in batch 1 is 0.84 or lower)
ISO_DIAGONAL_MARGIN = 0.05     # isometric: diagonal share exceeds horizontal share by at least this (batch 1: 0.12 to 0.69; straight-on: -0.08 and below)
ISO_BOTH_FAMILIES_MIN = 0.045  # ... and the weaker of the two diagonal directions (rising, falling) carries at least this (isometric 0.07 and up, straight-on 0.02 and below: midpoint)
ORTHO_AXIS_MIN = 0.45          # orthogonal: horizontal plus vertical share at least this

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

# ---- weak grids and wide edges (slice A3) -------------------------------------------
EDGE_GAPS = (1, 3)             # grid-finding compares pixels this far apart, so soft (blurred) edges still count
GRID_WEAK_SCORE = 0.10         # between this and MIN_GRID_SCORE the grid is "weak": used, but flagged
GRID_WEAK_MIN_CELLS = 32       # a weak grid must leave at least this many cells across the picture (else: no grid)
GRID_WEAK_AGREE = 0.08         # two weak axes must agree on the pixel size within this share to be trusted together
GRID_SQUARE_TOLERANCE = 0.15   # width and height pixel sizes this close count as agreeing (Midjourney pixels are nearly square)
FLAT_STRONG = 0.90             # cell flatness (share of colour variation the grid explains): below this a clear grid is only weak
FLAT_NONE = 0.72               # below this the "blocks" are not flat inside: painted or smooth art, no usable grid
                               # (batch 1: sprites 0.90-1.00, median 0.96; painted landscapes 0.81-0.84; blurry pixel scene 0.75;
                               #  smooth anime or sketch 0.68-0.70)

# ---- subject check: character / building / scene (slice B1) -------------------------
# Set from batch 1: 86 isolated characters, 3 isolated isometric buildings (0088, 0089, 0091).
# Only 3 buildings, so these are provisional: batch 2 and the object tuning batch must confirm them.
SUBJECT_BUILDING_ASPECT_MAX = 1.3   # isometric buildings are roughly square (batch 1: 0.88-1.17)
SUBJECT_BUILDING_BASE_MAX = 0.05    # bottom row width / widest row: a diamond footprint is pointed (0.00-0.02); characters 0.03 and up, median 0.36
SUBJECT_BUILDING_TOP_MAX = 0.70     # top quarter width / middle width: roof narrower than the body (0.51-0.65); characters median 0.92
SUBJECT_CHARACTER_ASPECT_MIN = 1.4  # tall figures (batch 1: 83 of 86 characters are 1.5 or taller)

# ---- ground shadows (slice D1) ------------------------------------------------------
# A ground shadow is the ground colour made darker by a steady amount, in a flat patch attached to the subject's base.
SHADOW_K_MIN = 0.45            # a shadow pixel is this fraction of the ground colour or more (real shadows 0.60-0.79; anything darker, such as navy trousers on a blue ground, boots, hair and outlines, is the subject)
SHADOW_K_MAX = 0.92            # ... and at most this (lighter = it is the ground itself)
SHADOW_CHROMA_DEV = 0.20       # all three colour channels darken by nearly the same factor (a shadow keeps the ground's hue; on grass it shifts a little)
SHADOW_MIN_GROUND = 20         # on a ground darker than this (near black) shadows cannot be told from the ground
SHADOW_MIN_CELLS = 6           # a shadow patch is at least this many cells of the coarse mask ...
SHADOW_PIECE_SHARE = 0.008    # each piece of a shadow (one darkness band of it) is at least this share of the subject's area ...
SHADOW_MIN_SHARE = 0.03        # ... and all the pieces together at least this share (real shadows 0.07 and up; small dark details are 0.03 or less)
SHADOW_BASE_ALLOWANCE = 0.15   # the patch's centre is at or below the subject's base line, less this share of the subject's height
SHADOW_REACH = 0.6             # and within this many subject-widths sideways of the subject
SHADOW_FLAT_STD = 0.10         # darkness varies at most this much across the patch (flat, not a pattern)
SHADOW_GROUND_CONTACT = 0.25   # at least this share of a patch's outer edge touches open ground (a shadow lies on the ground; clothing is enclosed by the sprite's outline)
SHADOW_WHITE_GROUND = 235      # on a ground this bright (and neutral), a pale grey shadow cannot be told from pale grey parts of the sprite: answer "can't tell"
SHADOW_MAX_SHARE = 0.5         # a "shadow" bigger than this share of the subject is more likely the sprite's own dark colours (real: 0.03-0.44)
SHADOW_MIN_ASPECT = 1.0        # a shadow lies flat on the ground: its box is at least this many times wider than tall (legs and trunks are taller than wide)

# ---- contact or cast, and removal (slice D2) -----------------------------------------
SHADOW_CAST_OFFSET = 0.20      # a shadow whose centre is this many subject-widths off to the side is a cast shadow
SHADOW_CAST_ASYMMETRY = 0.25   # ... or one that sticks out this much further on one side than the other
SHADOW_REMOVE_K_MAX = 0.97     # removal also takes the faint fringe of a shadow (up to this fraction of the ground colour)

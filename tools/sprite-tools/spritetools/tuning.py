# Tuning numbers for the Sprite Tools: every threshold and default lives here, with where it came from.
# Copyright (C) 2026 the pixeltools contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY; see the GNU General Public
# License for details: <https://www.gnu.org/licenses/>.
#
# These are copied into the browser version by web/build.py; never type a number twice.
# PROVISIONAL: nothing here has been tuned on real Midjourney pictures yet (none were available when
# these were set). They were set on drawn pictures with noise and JPEG damage. Re-tune on the real batch.

# ---- colour difference ----------------------------------------------------------------
MAX_DISTANCE = 510.0           # largest possible RGBA distance: sqrt(4 * 255^2)

# ---- fill -------------------------------------------------------------------------------
FILL_TOLERANCE = 10.0          # percent: close enough to count as the same colour
BG_BAND = 0.02                 # --background: the border ring is this share of the short side ...
BG_BAND_MIN = 2                # ... but at least this many pixels
BG_RANGE = 1.5                 # --background: a pixel is ground when it is within this many tolerances of the gradient
                               # fitted to the border, and it joins only by a step of at most one tolerance
BG_FIT_FIRST = 3.0             # the first fit uses border pixels within this many tolerances of the middle border colour
BG_FIT_ROUNDS = 2              # then the gradient is refitted this many times on the border pixels that fit

# ---- replace ----------------------------------------------------------------------------
REPLACE_TOLERANCE = 8.0

# ---- flatten ----------------------------------------------------------------------------
FLATTEN_TOLERANCE = 6.0        # percent: "the same colour" (plan section 6)
FLATTEN_MIN_SPECK = 2          # patches of at most this many pixels may be absorbed
FLATTEN_EDGE_LINE = 0.5        # an edge blend lies within this many tolerances of the line between two colours
FLATTEN_EDGE_ROUNDS = 3        # sharpen edges at most this many times
FLATTEN_SPECK_REACH = 25.0     # percent: a speck is absorbed only if it is this close to its surroundings
                               # (so a one-pixel eye or highlight of a very different colour is kept)

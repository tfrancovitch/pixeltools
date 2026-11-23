# Sprite Tools: small, exact tools for pixel-art sprites (the Python reference version).
# Copyright (C) 2026 the pixeltools contributors
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY; see the GNU General Public
# License for details: <https://www.gnu.org/licenses/>.
"""Each tool is a module with NAME, SUMMARY and apply(img, opts) -> (new_img, info).
img is a numpy array (height, width, 4) of 8-bit RGBA; opts is a plain dict (the same one the browser version takes)."""
__version__ = "0.1.0"

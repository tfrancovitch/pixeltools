/* Sprite Tools core (JavaScript): the same tools as the Python package spritetools/, with no page code in it.
 * Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
 *
 * Every function mirrors one in spritetools/. The tuning numbers are copied from spritetools/tuning.py by
 * web/build.py (never edited by hand). A picture is {w, h, data: Uint8ClampedArray of RGBA}.
 * Check it against Python with tests/parity.js. Use: SpriteCore.run('turn', img, {flip: 'h'}) -> {img, info}.
 */
(function (root) {
'use strict';

const T = /*TUNING_START*/{}/*TUNING_END*/;
const VERSION = '/*VERSION*/';

/* ---------------------------------------------------------------- helpers shared by the tools */
function cutoffSq(tolerance) {
  if (!(tolerance >= 0 && tolerance <= 100)) throw new Error('The tolerance must be between 0 and 100 (percent), not ' + tolerance + '.');
  const cut = tolerance * T.MAX_DISTANCE / 100;
  return cut * cut;
}
function normalised(img) {                  // a copy in which every fully transparent pixel is (0,0,0,0)
  const d = new Uint8ClampedArray(img.data);
  for (let i = 0; i < d.length; i += 4) if (d[i + 3] === 0) { d[i] = 0; d[i + 1] = 0; d[i + 2] = 0; }
  return { w: img.w, h: img.h, data: d };
}
function packAt(d, i) { return ((d[i] << 24) | (d[i + 1] << 16) | (d[i + 2] << 8) | d[i + 3]) >>> 0; }
function countColours(img) {
  const n = normalised(img), seen = new Set();
  for (let i = 0; i < n.data.length; i += 4) seen.add(packAt(n.data, i));
  return seen.size;
}
function changedPixels(a, b) {
  const x = normalised(a).data, y = normalised(b).data;
  let n = 0;
  for (let i = 0; i < x.length; i += 4) if (x[i] !== y[i] || x[i + 1] !== y[i + 1] || x[i + 2] !== y[i + 2] || x[i + 3] !== y[i + 3]) n++;
  return n;
}
function cleanColour(c) { return c[3] === 0 ? [0, 0, 0, 0] : [c[0], c[1], c[2], c[3]]; }
function checkPoint(img, at) {
  const x = at[0], y = at[1];
  if (!(x >= 0 && x < img.w && y >= 0 && y < img.h))
    throw new Error('The point ' + x + ',' + y + ' is outside the picture, which is ' + img.w + ' by ' + img.h + ' pixels (x from 0 to ' + (img.w - 1) + ', y from 0 to ' + (img.h - 1) + ').');
  return [x, y];
}
/* Everything reachable from the seeds (flat pixel indices) by stepping to a touching pixel q from a reached
 * pixel p whenever edgeOk(p, q). The answer does not depend on the order of the search. Returns a Uint8Array mask. */
function grow(w, h, seeds, edgeOk, corners) {
  const reached = new Uint8Array(w * h), stack = new Int32Array(w * h);
  let top = 0;
  for (const s of seeds) if (!reached[s]) { reached[s] = 1; stack[top++] = s; }
  while (top) {
    const p = stack[--top], y = (p / w) | 0, x = p - y * w;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      if ((dx === 0 && dy === 0) || (!corners && dx !== 0 && dy !== 0)) continue;
      const ny = y + dy, nx = x + dx;
      if (ny < 0 || ny >= h || nx < 0 || nx >= w) continue;
      const q = ny * w + nx;
      if (!reached[q] && edgeOk(p, q)) { reached[q] = 1; stack[top++] = q; }
    }
  }
  return reached;
}

const tools = {};

/* ---------------------------------------------------------------- turn */
tools.turn = {
  apply(img, opts) {
    const w = img.w, h = img.h, flip = opts.flip || null;
    if (flip !== null && flip !== 'h' && flip !== 'v') throw new Error('--flip must be h or v, not ' + flip + '.');
    const out = new Uint8ClampedArray(img.data.length);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const sx = flip === 'h' ? w - 1 - x : x, sy = flip === 'v' ? h - 1 - y : y;
      const s = (sy * w + sx) * 4, d = (y * w + x) * 4;
      out[d] = img.data[s]; out[d + 1] = img.data[s + 1]; out[d + 2] = img.data[s + 2]; out[d + 3] = img.data[s + 3];
    }
    const res = { w, h, data: out };
    return [res, { pixels_changed: changedPixels(img, res) }];
  },
};

/*TOOLS_HERE*/

/* ---------------------------------------------------------------- the one entry point */
function run(name, img, opts) {
  if (!tools[name]) throw new Error('There is no tool called ' + name + '.');
  const [out, info] = tools[name].apply(img, opts || {});
  info.colours_before = countColours(img);
  info.colours_after = countColours(out);
  return { img: out, info };
}

root.SpriteCore = { run, tools, T, VERSION, countColours, changedPixels };
})(typeof self !== 'undefined' ? self : globalThis);

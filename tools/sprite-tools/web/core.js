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

/* ---------------------------------------------------------------- fill */
const hexOf = c => '#' + c.map(v => (v < 16 ? '0' : '') + v.toString(16)).join('');
tools.fill = {
  apply(img, opts) {
    const w = img.w, h = img.h, n = w * h;
    const tol = opts.tolerance == null ? T.FILL_TOLERANCE : Number(opts.tolerance);
    const cut2 = cutoffSq(tol);
    const colour = cleanColour(opts.colour == null ? [0, 0, 0, 0] : opts.colour);
    const corners = !!opts.corners, at = opts.at;
    const f = normalised(img).data;
    const d2 = (i, j) => { const a = f[i * 4] - f[j * 4], b = f[i * 4 + 1] - f[j * 4 + 1], c = f[i * 4 + 2] - f[j * 4 + 2], e = f[i * 4 + 3] - f[j * 4 + 3]; return a * a + b * b + c * c + e * e; };
    const d2c = (i, r) => { const a = f[i * 4] - r[0], b = f[i * 4 + 1] - r[1], c = f[i * 4 + 2] - r[2], e = f[i * 4 + 3] - r[3]; return a * a + b * b + c * c + e * e; };
    let mask, extra = {};
    if (opts.background) {
      if (at != null) throw new Error('Use either --at (a start point) or --background (start from the border), not both.');
      let band = Math.max(T.BG_BAND_MIN, Math.floor(T.BG_BAND * Math.min(h, w) + 0.5));
      band = Math.min(band, Math.max(1, Math.floor(Math.min(h, w) / 2)));
      const ring = [];
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (y < band || y >= h - band || x < band || x >= w - band) ring.push(y * w + x);
      const ref = [0, 1, 2, 3].map(c => { const v = Int32Array.from(ring, i => f[i * 4 + c]).sort(); return v[Math.floor(ring.length / 2)]; });
      const range2 = cut2 * T.BG_RANGE * T.BG_RANGE, first2 = cut2 * T.BG_FIT_FIRST * T.BG_FIT_FIRST;
      const fit = idx => {                       // same plain float steps as fit_plane in fill.py
        let n = idx.length, sx = 0, sy = 0, sxx = 0, sxy = 0, syy = 0;
        for (const i of idx) { const y = Math.floor(i / w), x = i - y * w; sx += x; sy += y; sxx += x * x; sxy += x * y; syy += y * y; }
        const det = n * (sxx * syy - sxy * sxy) - sx * (sx * syy - sxy * sy) + sy * (sx * sxy - sxx * sy);
        return [0, 1, 2, 3].map(ch => {
          if (det === 0) return [ref[ch], 0, 0];
          let sc = 0, sxc = 0, syc = 0;
          for (const i of idx) { const y = Math.floor(i / w), x = i - y * w, c = f[i * 4 + ch]; sc += c; sxc += x * c; syc += y * c; }
          const a = (sc * (sxx * syy - sxy * sxy) - sx * (sxc * syy - sxy * syc) + sy * (sxc * sxy - sxx * syc)) / det;
          const b = (n * (sxc * syy - sxy * syc) - sc * (sx * syy - sxy * sy) + sy * (sx * syc - sxc * sy)) / det;
          const cc = (n * (sxx * syc - sxc * sxy) - sx * (sx * syc - sxc * sy) + sc * (sx * sxy - sxx * sy)) / det;
          return [a, b, cc];
        });
      };
      const planeD2 = (i, rows) => {
        const y = Math.floor(i / w), x = i - y * w; let t = 0;
        for (let ch = 0; ch < 4; ch++) { const d = f[i * 4 + ch] - ((rows[ch][0] + rows[ch][1] * x) + rows[ch][2] * y); t = t + d * d; }
        return t;
      };
      const firstKept = ring.filter(i => d2c(i, ref) <= first2);
      let rows = fit(firstKept.length ? firstKept : ring);
      for (let r = 0; r < T.BG_FIT_ROUNDS; r++) {
        const again = ring.filter(i => planeD2(i, rows) <= range2);
        if (again.length < 0.2 * ring.length) break;
        rows = fit(again);
      }
      const dBg = new Float64Array(n);
      for (let i = 0; i < n; i++) dBg[i] = planeD2(i, rows);
      const seeds = ring.filter(i => dBg[i] <= range2);
      mask = grow(w, h, seeds, (p, q) => d2(p, q) <= cut2 && dBg[q] <= range2, corners);
      extra.background_colour = hexOf(ref);
    } else {
      if (at == null) throw new Error('Say where to start: --at x,y (a point on the area to fill), or use --background.');
      const [x, y] = checkPoint(img, at), s = y * w + x;
      const cand = new Uint8Array(n);
      for (let i = 0; i < n; i++) cand[i] = d2(i, s) <= cut2 ? 1 : 0;
      mask = opts.everywhere ? cand : grow(w, h, [s], (p, q) => cand[q] === 1, corners);
    }
    const out = new Uint8ClampedArray(img.data);
    let filled = 0;
    for (let i = 0; i < n; i++) if (mask[i]) { filled++; out[i * 4] = colour[0]; out[i * 4 + 1] = colour[1]; out[i * 4 + 2] = colour[2]; out[i * 4 + 3] = colour[3]; }
    const res = { w, h, data: out };
    return [res, Object.assign({ pixels_filled: filled, pixels_changed: changedPixels(img, res) }, extra)];
  },
};

/* ---------------------------------------------------------------- flatten */
tools.flatten = {
  apply(img, opts) {
    const w = img.w, h = img.h, n = w * h;
    const tol = opts.tolerance == null ? T.FLATTEN_TOLERANCE : Number(opts.tolerance);
    const cut2 = cutoffSq(tol);
    const doMerge = opts.merge !== false, doEdges = opts.edges !== false;
    const limit = opts.min_speck == null ? T.FLATTEN_MIN_SPECK : Math.trunc(Number(opts.min_speck));
    if (limit < 0) throw new Error('--min-speck must be 0 or more (0 skips the speck pass).');
    const at = opts.at;
    let flat = normalised(img).data, start = Int32Array.from(flat);
    flat = Int32Array.from(flat);
    const pk = (a, i) => a[i * 4] * 16777216 + a[i * 4 + 1] * 65536 + a[i * 4 + 2] * 256 + a[i * 4 + 3];
    const d2 = (a, i, b, j) => { const p = a[i * 4] - b[j * 4], q = a[i * 4 + 1] - b[j * 4 + 1], r = a[i * 4 + 2] - b[j * 4 + 2], t = a[i * 4 + 3] - b[j * 4 + 3]; return p * p + q * q + r * r + t * t; };
    const setPk = (a, i, v) => { a[i * 4] = Math.floor(v / 16777216) & 255; a[i * 4 + 1] = Math.floor(v / 65536) & 255; a[i * 4 + 2] = Math.floor(v / 256) & 255; a[i * 4 + 3] = v & 255; };
    let region = null, changeOk = new Uint8Array(n).fill(1);
    if (at != null) {
      const [x, y] = checkPoint(img, at), seed = y * w + x;
      const cand = new Uint8Array(n);
      for (let i = 0; i < n; i++) cand[i] = d2(flat, i, flat, seed) <= cut2 ? 1 : 0;
      region = grow(w, h, [seed], (p, q) => cand[q] === 1, false);
      changeOk = new Uint8Array(n);
      for (let i = 0; i < n; i++) if (region[i]) {
        const y0 = (i / w) | 0, x0 = i - y0 * w;
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const yy = y0 + dy, xx = x0 + dx; if (yy >= 0 && yy < h && xx >= 0 && xx < w) changeOk[yy * w + xx] = 1; }
      }
    }
    const differs = (a, b) => { for (let i = 0; i < n; i++) if (a[i * 4] !== b[i * 4] || a[i * 4 + 1] !== b[i * 4 + 1] || a[i * 4 + 2] !== b[i * 4 + 2] || a[i * 4 + 3] !== b[i * 4 + 3]) return true; return false; };
    const countDiff = (a, b) => { let c = 0; for (let i = 0; i < n; i++) if (a[i * 4] !== b[i * 4] || a[i * 4 + 1] !== b[i * 4 + 1] || a[i * 4 + 2] !== b[i * 4 + 2] || a[i * 4 + 3] !== b[i * 4 + 3]) c++; return c; };
    // pass 1: merge near colours
    if (doMerge) {
      if (region === null) {
        const counts = new Map();
        for (let i = 0; i < n; i++) { const k = pk(flat, i); counts.set(k, (counts.get(k) || 0) + 1); }
        const order = [...counts.keys()].sort((a, b) => counts.get(b) - counts.get(a) || a - b);
        const leaders = [], target = new Map();
        const col = k => [Math.floor(k / 16777216) & 255, Math.floor(k / 65536) & 255, Math.floor(k / 256) & 255, k & 255];
        for (const k of order) {
          const c = col(k);
          let bestJ = -1, bestD = Infinity;
          for (let j = 0; j < leaders.length; j++) { const l = leaders[j].c; const d = (l[0] - c[0]) ** 2 + (l[1] - c[1]) ** 2 + (l[2] - c[2]) ** 2 + (l[3] - c[3]) ** 2; if (d < bestD) { bestD = d; bestJ = j; } }
          if (bestJ >= 0 && bestD <= cut2) target.set(k, leaders[bestJ].k);
          else { leaders.push({ k, c }); target.set(k, k); }
        }
        for (let i = 0; i < n; i++) setPk(flat, i, target.get(pk(flat, i)));
      } else {
        const counts = new Map();
        for (let i = 0; i < n; i++) if (region[i]) { const k = pk(flat, i); counts.set(k, (counts.get(k) || 0) + 1); }
        let mode = null;
        for (const [k, c] of counts) if (mode === null || c > counts.get(mode) || (c === counts.get(mode) && k < mode)) mode = k;
        for (let i = 0; i < n; i++) if (region[i]) setPk(flat, i, mode);
      }
    }
    const p1 = countDiff(flat, start);
    // pass 2: sharpen edges
    let p2 = 0;
    if (doEdges) {
      const lim = cut2 * T.FLATTEN_EDGE_LINE * T.FLATTEN_EDGE_LINE;
      for (let round = 0; round < T.FLATTEN_EDGE_ROUNDS; round++) {
        const out = Int32Array.from(flat);
        let moved = 0;
        for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
          const i = y * w + x;
          if (!changeOk[i]) continue;
          const c = pk(flat, i);
          let best = Infinity, pick = -1;
          for (const [dy1, dx1, dy2, dx2] of [[-1, 0, 1, 0], [0, -1, 0, 1]]) {
            const y1 = y + dy1, x1 = x + dx1, y2 = y + dy2, x2 = x + dx2;
            if (y1 < 0 || y1 >= h || x1 < 0 || x1 >= w || y2 < 0 || y2 >= h || x2 < 0 || x2 >= w) continue;
            const ia = y1 * w + x1, ib = y2 * w + x2, na = pk(flat, ia), nb = pk(flat, ib);
            if (na === nb || na === c || nb === c) continue;
            let len2 = 0, dot = 0, ac2 = 0;
            for (let k = 0; k < 4; k++) { const ab = flat[ib * 4 + k] - flat[ia * 4 + k], ac = flat[i * 4 + k] - flat[ia * 4 + k]; len2 += ab * ab; dot += ac * ab; ac2 += ac * ac; }
            const perp = ac2 * len2 - dot * dot;
            if (!(dot > 0 && dot < len2) || !(perp <= lim * len2)) continue;
            const score = perp / len2;
            if (score < best) { best = score; const twice = 2 * dot; pick = (twice < len2 || (twice === len2 && na < nb)) ? na : nb; }
          }
          if (pick >= 0) { setPk(out, i, pick); if (pk(out, i) !== c) moved++; }
        }
        flat = out; p2 += moved;
        if (moved === 0) break;
      }
    }
    // pass 3: absorb specks
    const before3 = Int32Array.from(flat);
    if (limit > 0) {
      const reach2 = cutoffSq(T.FLATTEN_SPECK_REACH), out = Int32Array.from(flat), seen = new Uint8Array(n);
      for (let s0 = 0; s0 < n; s0++) {
        if (seen[s0]) continue;
        const colour = pk(before3, s0), cells = [s0], mark = new Set([s0]);
        seen[s0] = 1;
        for (let k = 0; k < cells.length; k++) {
          const p = cells[k], y = (p / w) | 0, x = p - y * w;
          for (const [ny, nx] of [[y - 1, x], [y + 1, x], [y, x - 1], [y, x + 1]]) {
            if (ny < 0 || ny >= h || nx < 0 || nx >= w) continue;
            const q = ny * w + nx;
            if (!seen[q] && pk(before3, q) === colour) { seen[q] = 1; cells.push(q); }
          }
        }
        if (cells.length > limit) continue;
        for (const c of cells) mark.add(c);
        const around = new Set();
        for (const p of cells) {
          const y = (p / w) | 0, x = p - y * w;
          for (const [ny, nx] of [[y - 1, x], [y + 1, x], [y, x - 1], [y, x + 1]]) {
            if (ny < 0 || ny >= h || nx < 0 || nx >= w) continue;
            const q = ny * w + nx;
            if (!mark.has(q)) around.add(pk(before3, q));
          }
        }
        if (around.size !== 1 || !cells.every(c => changeOk[c])) continue;
        const target = [...around][0], t = [Math.floor(target / 16777216) & 255, Math.floor(target / 65536) & 255, Math.floor(target / 256) & 255, target & 255];
        let d = 0;
        for (let k = 0; k < 4; k++) { const e = t[k] - before3[s0 * 4 + k]; d += e * e; }
        if (d <= reach2) for (const c of cells) setPk(out, c, target);
      }
      flat = out;
    }
    const p3 = countDiff(flat, before3);
    const res = { w, h, data: Uint8ClampedArray.from(flat) };
    return [res, { pixels_changed: changedPixels(img, res), pass1_pixels: p1, pass2_pixels: p2, pass3_pixels: p3 }];
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

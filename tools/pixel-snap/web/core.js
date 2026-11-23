/* Pixel Snap core (JavaScript): the same method as the Python tool, with no page code in it.
 * Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
 *
 * Every function mirrors one in pixel_snap.py, framing.py, subject.py, viewcheck.py, shadow.py, facing.py
 * or sorting.py. The tuning numbers are copied from tuning.py by build_web.py (never edited by hand).
 * An image is {w, h, data: Uint8ClampedArray of RGBA}. Check it against the Python tool with
 * eval/web_parity.js.
 */
(function (root) {
'use strict';

const T = /*TUNING_START*/{}/*TUNING_END*/;

/* ---------------------------------------------------------------- small helpers */

function pyRound(x) {                       // Python's round(): halves go to the even number
  const f = Math.floor(x), d = x - f;
  if (d < 0.5) return f;
  if (d > 0.5) return f + 1;
  return f % 2 === 0 ? f : f + 1;
}
function median(values) {                   // numpy.median
  const a = Float64Array.from(values).sort();
  const n = a.length, m = n >> 1;
  return n % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
}
function percentile(sortedAsc, q) {         // numpy.percentile (linear), on already sorted data
  const idx = (q / 100) * (sortedAsc.length - 1), lo = Math.floor(idx), hi = Math.ceil(idx);
  return sortedAsc[lo] + (sortedAsc[hi] - sortedAsc[lo]) * (idx - lo);
}
function interp(a, x) {                     // numpy.interp on an array indexed 0..n-1, clamped at the ends
  const n = a.length;
  if (x <= 0) return a[0];
  if (x >= n - 1) return a[n - 1];
  const i = Math.floor(x), f = x - i;
  return a[i] * (1 - f) + a[i + 1] * f;
}
function interpCurve(ps, ss, p) {           // _curve_at: interpolate a (sizes, scores) curve on a log scale
  if (p < ps[0] || p > ps[ps.length - 1]) return null;
  const lx = Math.log(p);
  let lo = 0, hi = ps.length - 1;
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (Math.log(ps[mid]) <= lx) lo = mid; else hi = mid; }
  const x0 = Math.log(ps[lo]), x1 = Math.log(ps[hi]);
  return x1 === x0 ? ss[lo] : ss[lo] + (ss[hi] - ss[lo]) * (lx - x0) / (x1 - x0);
}
function fmt(x, d) { return x.toFixed(d); }

/* ---------------------------------------------------------------- finding the grid */

function edgeProfile(img, axis, gaps) {
  const { w, h, data } = img;
  const n = axis === 0 ? w : h, other = axis === 0 ? h : w;
  const step = Math.max(1, Math.floor(other / 600));
  let rows = 0;
  for (let r = 0; r < other; r += step) rows++;
  const e = new Float64Array(n);
  for (const d of gaps) {
    const half = (d - 1) >> 1;
    if (n <= d) continue;
    const lo = half + 1, hi = n - half;
    const sum = new Float64Array(n);
    for (let r = 0; r < other; r += step) {
      for (let i = lo; i < hi; i++) {
        const ia = axis === 0 ? (r * w + i + half) * 4 : ((i + half) * w + r) * 4;
        const ib = axis === 0 ? (r * w + i - 1 - half) * 4 : ((i - 1 - half) * w + r) * 4;
        sum[i] += Math.abs(data[ia] - data[ib]) + Math.abs(data[ia + 1] - data[ib + 1]) + Math.abs(data[ia + 2] - data[ib + 2]);
      }
    }
    for (let i = lo; i < hi; i++) e[i] += sum[i] / rows;
  }
  return e;
}

function smooth(e, k) {
  const n = e.length, out = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    let num = 0, den = 0;
    for (let d = -k; d <= k; d++) {
      const j = i + d;
      if (j < 1 || j >= n) continue;          // line 0 is excluded (m[0] = 0), as is anything off the ends
      const wt = k + 1 - Math.abs(d);
      num += e[j] * wt; den += wt;
    }
    out[i] = num / Math.max(den, 1e-12);
  }
  return out;
}

function meanOf(e) { let s = 0; for (let i = 1; i < e.length; i++) s += e[i]; return e.length > 1 ? s / (e.length - 1) : 0; }

function bestPhase(a, p, mean, step) {
  const n = a.length, count = Math.ceil(p / step);
  const kmax = Math.floor(n / p) + 2;
  let best = -Infinity, bo = 0;
  for (let i = 0; i < count; i++) {
    const off = i * step;
    let tot = 0, cnt = 0;
    for (let k = 0; k < kmax; k++) {
      const x = off + k * p;
      if (x >= 1 && x < n - 1) { tot += interp(a, x); cnt++; }
    }
    const sc = cnt > 0 ? tot / cnt / mean : 0;
    if (sc > best) { best = sc; bo = off; }
  }
  return [best, bo];
}

function combCurve(e) {
  const n = e.length - 1;
  const x = new Float64Array(n);
  for (let i = 0; i < n; i++) x[i] = Math.sqrt(e[i + 1]);
  const cs = new Float64Array(n + 1);
  for (let i = 0; i < n; i++) cs[i + 1] = cs[i] + x[i];
  const win = T.GRID_DETREND_WINDOW, half = Math.floor(win / 2);
  const d = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const lo = Math.max(0, Math.min(n, i - half)), hi = Math.max(0, Math.min(n, i + half + 1));
    d[i] = x[i] - (cs[hi] - cs[lo]) / (hi - lo);
  }
  const L = Math.min(n - 1, Math.floor(T.GRID_LAG_LIMIT * n) + 3);
  const raw = new Float64Array(L + 1);
  for (let l = 0; l <= L; l++) { let t = 0; for (let i = 0; i + l < n; i++) t += d[i] * d[i + l]; raw[l] = t; }
  if (!(raw[0] > 0)) return { ps: [], ss: [] };
  const ac = new Float64Array(L + 1);
  for (let l = 0; l <= L; l++) ac[l] = raw[l] / raw[0] * n / (n - l);
  const acs = new Float64Array(L + 1);
  acs[0] = 0.5 * ac[0] + 0.25 * ac[1];
  for (let l = 1; l < L; l++) acs[l] = 0.25 * ac[l - 1] + 0.5 * ac[l] + 0.25 * ac[l + 1];
  acs[L] = 0.25 * ac[L - 1] + 0.5 * ac[L];
  const ps = [], ss = [];
  let p = T.GRID_MIN_PIXEL;
  const maxP = Math.max(3.0, n * T.GRID_MAX_FRACTION);
  while (p <= maxP) {
    const lags = [];
    for (let k = 1; k <= T.GRID_HARMONICS; k++) { const lag = k * p; if (lag < T.GRID_LAG_LIMIT * n) lags.push(lag); }
    if (lags.length < T.GRID_MIN_LAGS) break;
    let on = 0, off = 0;
    for (const lag of lags) { on += interp(acs, lag); off += interp(acs, lag - p / 2); }
    ps.push(p); ss.push((on - off) / lags.length);
    p *= T.GRID_SIZE_STEP;
  }
  return { ps, ss };
}

function thresholds(n) {
  const strong = Math.max(T.MIN_GRID_SCORE, T.NOISE_FACTOR / Math.sqrt(n));
  return [strong, strong * T.GRID_WEAK_SCORE / T.MIN_GRID_SCORE];
}

function refineAt(eFine, p0) {
  const a1 = smooth(eFine, 1), meanFine = meanOf(eFine);
  let best = [-1.0, p0, 0.0];
  const count = Math.ceil((T.GRID_REFINE_HIGH - T.GRID_REFINE_LOW) / T.GRID_REFINE_STEP);
  for (let i = 0; i < count; i++) {
    const pp = p0 * (T.GRID_REFINE_LOW + i * T.GRID_REFINE_STEP);
    const [sc, o] = bestPhase(a1, pp, meanFine, 0.25);
    if (sc > best[0]) best = [sc, pp, o];
  }
  return [best[1], best[2]];
}

function axisFrom(e, eFine, p0, score, curve, judgedOn, n) {
  const [p, off] = refineAt(eFine, p0);
  const [strong, weak] = thresholds(n || e.length);
  const j = judgedOn === undefined || judgedOn === null ? score : judgedOn;
  return { p, off, score, ok: j >= strong, borrowed: false, weak: weak <= j && j < strong, disagree: false, curve };
}

function detectAxis(e, eFine) {
  if (!eFine) eFine = e;
  const mean = meanOf(e);
  if (!(mean > 1e-6)) return { p: 1, off: 0, score: 0, ok: false, borrowed: false, weak: false, disagree: false, curve: null };
  let { ps, ss } = combCurve(e);
  if (!ps.length) return { p: 1, off: 0, score: 0, ok: false, borrowed: false, weak: false, disagree: false, curve: null };
  if (eFine !== e) {
    const c2 = combCurve(eFine);
    const n = Math.min(ps.length, c2.ps.length);
    ps = ps.slice(0, n);
    ss = ss.slice(0, n).map((v, i) => Math.max(v, c2.ss[i]));
  }
  let smax = -Infinity;
  for (const v of ss) if (v > smax) smax = v;
  let first = 0;
  while (first < ss.length && !(ss[first] >= T.GRID_SMALLEST_FIT * smax)) first++;
  if (first >= ss.length) first = 0;
  let pick = -1, pv = -9;
  for (let i = first; i < ps.length && ps[i] <= ps[first] * T.GRID_WINDOW_RANGE; i++) {
    if (ss[i] > pv) { pv = ss[i]; pick = i; }
  }
  if (pick < 0) pick = first;
  return axisFrom(e, eFine, ps[pick], smax, { ps, ss });
}

function reconcileSquare(dx, dy, wx, wy, ex, ey) {
  if (!dx.curve || !dy.curve) return [dx, dy];
  if (!(dx.ok || dy.ok)) return [dx, dy];
  if (dx.ok !== dy.ok && !(dx.ok ? dy.weak : dx.weak)) return [dx, dy];
  if (Math.abs(dx.p - dy.p) / ((dx.p + dy.p) / 2) <= T.GRID_SQUARE_TOLERANCE) return [dx, dy];
  const cands = new Set();
  for (const v of [dx.p, dy.p]) for (const k of [1, 2, 3]) if (v / k >= T.GRID_MIN_PIXEL) cands.add(Math.round(v / k * 1000) / 1000);
  const scored = [];
  for (const c of [...cands].sort((a, b) => a - b)) {
    const sx = interpCurve(dx.curve.ps, dx.curve.ss, c), sy = interpCurve(dy.curve.ps, dy.curve.ss, c);
    if (sx === null || sy === null) continue;
    scored.push([c, sx, sy, sx + sy]);
  }
  if (!scored.length) return [dx, dy];
  let top = -Infinity;
  for (const s of scored) if (s[3] > top) top = s[3];
  const chosen = scored.find(s => s[3] >= T.GRID_SMALLEST_FIT * top);
  const [c, sx, sy] = chosen;
  const n = Math.min(wx.length, wy.length);
  const [, weak] = thresholds(n);
  const resolved = Math.min(sx, sy) >= weak;
  const ax = axisFrom(wx, ex, c, sx, dx.curve, Math.max(sx, sy), n);
  const ay = axisFrom(wy, ey, c, sy, dy.curve, Math.max(sx, sy), n);
  if (!resolved) {
    const both = Math.max(dx.score, dy.score);
    for (const k of [2, 3]) {
      if (Math.abs(dx.p - k * dy.p) / ((dx.p + k * dy.p) / 2) <= T.GRID_SQUARE_TOLERANCE)
        return [axisFrom(wx, ex, dx.p, dx.score, dx.curve, both, n), axisFrom(wy, ey, k * dy.p, dy.score, dy.curve, both, n)];
      if (Math.abs(dy.p - k * dx.p) / ((dy.p + k * dx.p) / 2) <= T.GRID_SQUARE_TOLERANCE)
        return [axisFrom(wx, ex, k * dx.p, dx.score, dx.curve, both, n), axisFrom(wy, ey, dy.p, dy.score, dy.curve, both, n)];
    }
    for (const a of [ax, ay]) { a.weak = Math.max(sx, sy) >= weak; a.ok = false; a.disagree = true; }
  }
  return [ax, ay];
}

function fitPhase(e, p) {
  const mean = meanOf(e);
  if (!(mean > 1e-6)) return { p, off: 0, score: 0, ok: true, borrowed: false, weak: false, disagree: false, curve: null };
  const [s, o] = bestPhase(smooth(e, 1), p, mean, 0.25);
  return { p, off: o, score: s, ok: true, borrowed: false, weak: false, disagree: false, curve: null };
}

function makeBounds(e, p, off, n, follow) {
  const s = smooth(e, 1);
  let pos = [];
  let x = ((off % p) + p) % p;
  while (x < n) { if (x > 0.01 && x < n - 0.01) pos.push(x); x += p; }
  if (pos.length && pos[0] < 0.5 * p) pos.shift();
  if (pos.length && n - pos[pos.length - 1] < 0.5 * p) pos.pop();
  let lineMean = 0;
  if (pos.length) { for (const q of pos) lineMean += interp(s, q); lineMean /= pos.length; }
  const w = Math.max(1, Math.floor(0.3 * p));
  const out = [0];
  for (const q of pos) {
    let v = Math.floor(q + 0.5);
    if (follow && p >= 3) {
      const lo = Math.max(1, v - w), hi = Math.min(n - 1, v + w);
      let bi = lo, bv = -Infinity;
      for (let i = lo; i <= hi; i++) if (s[i] > bv) { bv = s[i]; bi = i; }
      if (bv >= 0.5 * lineMean) v = bi;
    }
    if (out[out.length - 1] < v && v < n) out.push(v);
  }
  out.push(n);
  return out;
}

function cellFlatness(img, bx, by) {
  const { w, h, data } = img;
  const cx = new Int32Array(w), cy = new Int32Array(h);
  for (let x = 0, c = 0; x < w; x++) { while (c + 1 < bx.length - 1 && bx[c + 1] <= x) c++; cx[x] = c; }
  for (let y = 0, c = 0; y < h; y++) { while (c + 1 < by.length - 1 && by[c + 1] <= y) c++; cy[y] = c; }
  const ncx = bx.length - 1, ncy = by.length - 1, ncell = ncx * ncy;
  const N = w * h, step = Math.max(1, Math.floor(N / 400000));
  const cnt = new Float64Array(ncell), sums = [new Float64Array(ncell), new Float64Array(ncell), new Float64Array(ncell)];
  const mean = [0, 0, 0];
  let m = 0;
  for (let t = 0; t < N; t += step) {
    const y = (t / w) | 0, x = t - y * w, ci = cy[y] * ncx + cx[x], o = t * 4;
    cnt[ci]++; m++;
    for (let c = 0; c < 3; c++) { sums[c][ci] += data[o + c]; mean[c] += data[o + c]; }
  }
  for (let c = 0; c < 3; c++) mean[c] /= m;
  let total = 0, within = 0;
  for (let t = 0; t < N; t += step) {
    const y = (t / w) | 0, x = t - y * w, ci = cy[y] * ncx + cx[x], o = t * 4;
    for (let c = 0; c < 3; c++) {
      const v = data[o + c], cm = sums[c][ci] / Math.max(cnt[ci], 1);
      total += (v - mean[c]) * (v - mean[c]);
      within += (v - cm) * (v - cm);
    }
  }
  return 1 - within / Math.max(total, 1e-9);
}

function sampleCells(img, bx, by) {
  const { w: W, data } = img;
  const w = bx.length - 1, h = by.length - 1;
  const out = new Uint8ClampedArray(w * h * 4);
  const R = new Uint8Array(500), G = new Uint8Array(500), B = new Uint8Array(500);
  for (let cy = 0; cy < h; cy++) {
    const y0 = by[cy], y1 = by[cy + 1];
    let iy = (y1 - y0) >> 2;
    if (y1 - y0 - 2 * iy < 1) iy = 0;
    for (let cx = 0; cx < w; cx++) {
      const x0 = bx[cx], x1 = bx[cx + 1];
      let ix = (x1 - x0) >> 2;
      if (x1 - x0 - 2 * ix < 1) ix = 0;
      const xa = x0 + ix, xb = x1 - ix, ya = y0 + iy, yb = y1 - iy;
      const sx = Math.max(1, Math.ceil((xb - xa) / 20)), sy = Math.max(1, Math.ceil((yb - ya) / 20));
      let n = 0, total = 0;
      for (let y = ya; y < yb; y += sy) {
        for (let x = xa; x < xb; x += sx) {
          const i = (y * W + x) * 4;
          total++;
          if (data[i + 3] >= 128) { R[n] = data[i]; G[n] = data[i + 1]; B[n] = data[i + 2]; n++; }
        }
      }
      const o = (cy * w + cx) * 4;
      if (n === 0 || n < total / 2) continue;
      const mid = n >> 1;
      out[o] = R.subarray(0, n).sort()[mid];
      out[o + 1] = G.subarray(0, n).sort()[mid];
      out[o + 2] = B.subarray(0, n).sort()[mid];
      out[o + 3] = 255;
    }
  }
  return { w, h, data: out };
}

/* ---------------------------------------------------------------- colours */

function colourCounts(img) {
  const m = new Map();
  const d = img.data;
  for (let i = 0; i < d.length; i += 4) {
    if (d[i + 3] < 128) continue;
    const key = (d[i] << 16) | (d[i + 1] << 8) | d[i + 2];
    m.set(key, (m.get(key) || 0) + 1);
  }
  return m;
}
function countColours(img) { return colourCounts(img).size; }
function applyLut(img, lut) {
  const d = img.data;
  for (let i = 0; i < d.length; i += 4) {
    if (d[i + 3] < 128) continue;
    const q = lut.get((d[i] << 16) | (d[i + 1] << 8) | d[i + 2]);
    d[i] = q[0]; d[i + 1] = q[1]; d[i + 2] = q[2];
  }
}
function sortedByCount(m) {            // most common first; ties by colour value (numpy.unique order, then a stable sort)
  return [...m.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0]);
}
function mergeSimilar(img, tol) {
  const cols = sortedByCount(colourCounts(img)).map(([k]) => [k >> 16, (k >> 8) & 255, k & 255, k]);
  const reps = [], lut = new Map(), t2 = tol * tol;
  for (const c of cols) {
    let hit = null;
    for (const r of reps) {
      const dr = c[0] - r[0], dg = c[1] - r[1], db = c[2] - r[2];
      if (dr * dr + dg * dg + db * db <= t2) { hit = r; break; }
    }
    if (!hit) { reps.push(c); hit = c; }
    lut.set(c[3], [hit[0], hit[1], hit[2]]);
  }
  applyLut(img, lut);
}
function quantize(img, k) {
  const entries = sortedByCount(colourCounts(img));
  if (entries.length <= k) return;
  const n = entries.length;
  const keys = entries.map(e => e[0]), counts = entries.map(e => e[1]);
  const cols = keys.map(key => [key >> 16, (key >> 8) & 255, key & 255]);
  const d2 = (a, b) => (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2;
  const cen = [cols[0].slice()];
  const dm = new Float64Array(n).fill(Infinity);
  while (cen.length < k) {
    const last = cen[cen.length - 1];
    let bi = 0, bv = -Infinity;
    for (let i = 0; i < n; i++) {
      const dd = d2(cols[i], last);
      if (dd < dm[i]) dm[i] = dd;
      const v = dm[i] * Math.sqrt(counts[i]);
      if (v > bv) { bv = v; bi = i; }
    }
    cen.push(cols[bi].slice());
  }
  const asg = new Int32Array(n);
  const assign = () => {
    for (let i = 0; i < n; i++) {
      let bj = 0, bd = Infinity;
      for (let j = 0; j < cen.length; j++) { const dd = d2(cols[i], cen[j]); if (dd < bd) { bd = dd; bj = j; } }
      asg[i] = bj;
    }
  };
  for (let it = 0; it < 12; it++) {
    assign();
    for (let j = 0; j < cen.length; j++) {
      let s0 = 0, s1 = 0, s2 = 0, sw = 0;
      for (let i = 0; i < n; i++) if (asg[i] === j) { s0 += cols[i][0] * counts[i]; s1 += cols[i][1] * counts[i]; s2 += cols[i][2] * counts[i]; sw += counts[i]; }
      if (sw) cen[j] = [s0 / sw, s1 / sw, s2 / sw];
    }
  }
  assign();
  const lut = new Map();
  for (let i = 0; i < n; i++) { const q = cen[asg[i]]; lut.set(keys[i], [pyRound(q[0]), pyRound(q[1]), pyRound(q[2])]); }
  applyLut(img, lut);
}

/* ---------------------------------------------------------------- background and framing */

function components(mask, w, h) {          // 8-neighbour blobs of a Uint8Array mask; each blob is an array of cell indices
  const seen = new Uint8Array(w * h), out = [];
  for (let start = 0; start < w * h; start++) {
    if (!mask[start] || seen[start]) continue;
    const cells = [start];
    seen[start] = 1;
    for (let head = 0; head < cells.length; head++) {
      const idx = cells[head], y = (idx / w) | 0, x = idx - y * w;
      for (let dy = -1; dy <= 1; dy++) {
        const ny = y + dy;
        if (ny < 0 || ny >= h) continue;
        for (let dx = -1; dx <= 1; dx++) {
          const nx = x + dx;
          if (nx < 0 || nx >= w) continue;
          const ni = ny * w + nx;
          if (mask[ni] && !seen[ni]) { seen[ni] = 1; cells.push(ni); }
        }
      }
    }
    out.push(cells);
  }
  return out;
}

function solve3(A, b) {                    // 3x3 linear solve by Gaussian elimination with a tiny ridge for safety
  const M = [A[0].slice(), A[1].slice(), A[2].slice()], v = b.slice();
  for (let i = 0; i < 3; i++) M[i][i] += 1e-9;
  for (let i = 0; i < 3; i++) {
    let p = i;
    for (let r = i + 1; r < 3; r++) if (Math.abs(M[r][i]) > Math.abs(M[p][i])) p = r;
    [M[i], M[p]] = [M[p], M[i]]; [v[i], v[p]] = [v[p], v[i]];
    for (let r = i + 1; r < 3; r++) {
      const f = M[r][i] / M[i][i];
      for (let c = i; c < 3; c++) M[r][c] -= f * M[i][c];
      v[r] -= f * v[i];
    }
  }
  const x = [0, 0, 0];
  for (let i = 2; i >= 0; i--) {
    let s = v[i];
    for (let c = i + 1; c < 3; c++) s -= M[i][c] * x[c];
    x[i] = s / M[i][i];
  }
  return x;
}

function groundAt(coef, x, y) {            // fitted ground colour at normalised position (x, y)
  return [coef[0] + coef[1] * x + coef[2] * y, coef[3] + coef[4] * x + coef[5] * y, coef[6] + coef[7] * x + coef[8] * y];
}

function estimateBackground(img, bandPx) {
  const { w, h, data } = img;
  let band = bandPx || Math.max(T.BG_BORDER_MIN_PX, pyRound(T.BG_BORDER_BAND * Math.min(h, w)));
  band = Math.min(band, Math.max(1, Math.min(h, w) >> 1));
  const xs = [], ys = [];
  const add = (y0, y1, x0, x1) => { for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) { ys.push(y); xs.push(x); } };
  add(0, band, 0, w); add(h - band, h, 0, w); add(band, h - band, 0, band); add(band, h - band, w - band, w);
  const m = xs.length;
  const col = [new Float64Array(m), new Float64Array(m), new Float64Array(m)];
  for (let i = 0; i < m; i++) { const o = (ys[i] * w + xs[i]) * 4; col[0][i] = data[o]; col[1][i] = data[o + 1]; col[2][i] = data[o + 2]; }
  const fx = new Float64Array(m), fy = new Float64Array(m);
  for (let i = 0; i < m; i++) { fx[i] = xs[i] / Math.max(w, 1); fy[i] = ys[i] / Math.max(h, 1); }
  const med = [median(col[0]), median(col[1]), median(col[2])];
  const coef = [med[0], 0, 0, med[1], 0, 0, med[2], 0, 0];
  let keep = new Uint8Array(m).fill(1), kcount = m;
  const residuals = () => {
    const r = new Float64Array(m);
    for (let i = 0; i < m; i++) {
      let s = 0;
      for (let c = 0; c < 3; c++) s += Math.abs(col[c][i] - (coef[c * 3] + coef[c * 3 + 1] * fx[i] + coef[c * 3 + 2] * fy[i]));
      r[i] = s;
    }
    return r;
  };
  for (let round = 0; round < T.BG_FIT_ROUNDS; round++) {
    if (kcount < 3) break;
    const A = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], bvec = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
    for (let i = 0; i < m; i++) {
      if (!keep[i]) continue;
      const f = [1, fx[i], fy[i]];
      for (let a = 0; a < 3; a++) {
        for (let b = 0; b < 3; b++) A[a][b] += f[a] * f[b];
        for (let c = 0; c < 3; c++) bvec[c][a] += f[a] * col[c][i];
      }
    }
    for (let c = 0; c < 3; c++) { const s = solve3(A, bvec[c]); coef[c * 3] = s[0]; coef[c * 3 + 1] = s[1]; coef[c * 3 + 2] = s[2]; }
    const resid = residuals();
    const nk = new Uint8Array(m);
    let cnt = 0;
    for (let i = 0; i < m; i++) if (resid[i] <= T.BG_TOLERANCE) { nk[i] = 1; cnt++; }
    if (cnt < 0.2 * m) break;
    keep = nk; kcount = cnt;
  }
  const resid = residuals();
  let ok = 0;
  for (let i = 0; i < m; i++) if (resid[i] <= T.BG_TOLERANCE) ok++;
  return { coef, colour: med.map(v => Math.trunc(v)), uniform: ok / m };
}

// distance of every pixel of an (h x w) crop of img from the fitted ground; the plane is normalised by the crop's size
function backgroundDistance(bg, img, cropW, cropH) {
  const { w: W, data } = img;
  const out = new Float32Array(cropW * cropH);
  const c = bg.coef;
  for (let y = 0; y < cropH; y++) {
    const ny = y / Math.max(cropH, 1);
    for (let x = 0; x < cropW; x++) {
      const nx = x / Math.max(cropW, 1), o = (y * W + x) * 4;
      const g0 = Math.fround(c[0] + c[1] * nx + c[2] * ny), g1 = Math.fround(c[3] + c[4] * nx + c[5] * ny), g2 = Math.fround(c[6] + c[7] * nx + c[8] * ny);
      out[y * cropW + x] = Math.abs(data[o] - g0) + Math.abs(data[o + 1] - g1) + Math.abs(data[o + 2] - g2);
    }
  }
  return out;
}

function classifyFraming(img) {
  const { w, h } = img;
  const bg = estimateBackground(img);
  const s = Math.max(1, Math.ceil(Math.max(h, w) / T.MASK_MAX_SIDE));
  const hh = Math.floor(h / s) * s, ww = Math.floor(w / s) * s;
  const dist = backgroundDistance(bg, img, ww, hh);
  const mw = ww / s, mh = hh / s;
  const ds = new Uint8Array(mw * mh);
  for (let my = 0; my < mh; my++) {
    for (let mx = 0; mx < mw; mx++) {
      let c = 0;
      for (let yy = 0; yy < s; yy++) for (let xx = 0; xx < s; xx++) if (dist[(my * s + yy) * ww + mx * s + xx] > T.SUBJECT_DISTANCE) c++;
      ds[my * mw + mx] = c / (s * s) > 0.5 ? 1 : 0;
    }
  }
  const comps = components(ds, mw, mh);
  const total = ds.length;
  let big = comps.filter(c => c.length >= T.SPECK_SHARE * total);
  if (!big.length && comps.length) { let b = comps[0]; for (const c of comps) if (c.length >= b.length) b = c; big = [b]; }
  const mask = new Uint8Array(total);
  for (const c of big) for (const i of c) mask[i] = 1;
  let area = 0, x0 = Infinity, x1 = -1, y0 = Infinity, y1 = -1;
  for (let i = 0; i < total; i++) if (mask[i]) { area++; const y = (i / mw) | 0, x = i - y * mw; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  const base = { borderUniform: bg.uniform, background: bg, mask, mw, mh, scale: s };
  if (area === 0) return Object.assign({ kind: 'unclear', subjectShare: 0, fill: 0, aspect: 0, touchesBorder: false, bbox: [0, 0, 0, 0] }, base);
  const bh = y1 - y0 + 1, bw = x1 - x0 + 1, share = area / total;
  const touches = y0 === 0 || x0 === 0 || y1 === mh - 1 || x1 === mw - 1;
  const isolated = bg.uniform >= T.FRAMING_UNIFORM_MIN && share <= T.FRAMING_SUBJECT_MAX;
  return Object.assign({
    kind: isolated ? 'isolated' : 'scene', subjectShare: share, fill: area / (bh * bw), aspect: bh / bw, touchesBorder: touches,
    bbox: [x0 * s, y0 * s, (x1 + 1) * s, (y1 + 1) * s],
  }, base);
}

function removeBackground(sprite) {        // sprite: {w,h,data}; background touching the edge becomes transparent; returns count
  const { w, h, data } = sprite;
  const bg = estimateBackground(sprite, 1);
  const dist = backgroundDistance(bg, sprite, w, h);
  const near = new Uint8Array(w * h);
  for (let i = 0; i < near.length; i++) near[i] = dist[i] <= T.TRANSPARENT_TOLERANCE ? 1 : 0;
  const reach = new Uint8Array(w * h), q = [];
  const seed = (y, x) => { const i = y * w + x; if (near[i] && !reach[i]) { reach[i] = 1; q.push(i); } };
  for (let y = 0; y < h; y++) { seed(y, 0); seed(y, w - 1); }
  for (let x = 0; x < w; x++) { seed(0, x); seed(h - 1, x); }
  for (let head = 0; head < q.length; head++) {
    const i = q[head], y = (i / w) | 0, x = i - y * w;
    if (y > 0) seed(y - 1, x);
    if (y < h - 1) seed(y + 1, x);
    if (x > 0) seed(y, x - 1);
    if (x < w - 1) seed(y, x + 1);
  }
  let n = 0;
  for (let i = 0; i < reach.length; i++) if (reach[i]) { data[i * 4] = data[i * 4 + 1] = data[i * 4 + 2] = data[i * 4 + 3] = 0; n++; }
  return n;
}

/* ---------------------------------------------------------------- what is it? */

function silhouetteShape(mask, mw, mh) {
  let x0 = Infinity, x1 = -1, y0 = Infinity, y1 = -1;
  for (let i = 0; i < mask.length; i++) if (mask[i]) { const y = (i / mw) | 0, x = i - y * mw; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  const h = y1 - y0 + 1, w = x1 - x0 + 1;
  const widths = new Float64Array(h);
  for (let y = 0; y < h; y++) { let c = 0; for (let x = 0; x < w; x++) if (mask[(y0 + y) * mw + x0 + x]) c++; widths[y] = c / w; }
  const avg = (a, lo, hi) => { let s = 0; for (let i = lo; i < hi; i++) s += a[i]; return s / (hi - lo); };
  const mid = h >= 4 ? avg(widths, h >> 2, (3 * h) >> 2) : avg(widths, 0, h);
  const top = avg(widths, 0, Math.max(1, h >> 2));
  let wmax = 0; for (const v of widths) if (v > wmax) wmax = v;
  return [h / w, top / Math.max(mid, 1e-9), widths[h - 1] / Math.max(wmax, 1e-9)];
}

function classifySubject(framing) {
  if (framing.kind === 'scene') return { kind: 'scene', reason: 'the border is busy, so the picture is a whole scene, not a lone sprite', aspect: 0, top: 0, base: 0 };
  let any = false;
  if (framing.mask) for (let i = 0; i < framing.mask.length; i++) if (framing.mask[i]) { any = true; break; }
  if (framing.kind !== 'isolated' || !any) return { kind: 'unclear', reason: 'no subject found', aspect: 0, top: 0, base: 0 };
  const [aspect, top, base] = silhouetteShape(framing.mask, framing.mw, framing.mh);
  if (aspect <= T.SUBJECT_BUILDING_ASPECT_MAX && base <= T.SUBJECT_BUILDING_BASE_MAX && top <= T.SUBJECT_BUILDING_TOP_MAX)
    return { kind: 'building', reason: 'roughly square, with a pointed base and a narrower top, like an isometric building', aspect, top, base };
  if (aspect >= T.SUBJECT_CHARACTER_ASPECT_MIN)
    return { kind: 'character', reason: 'a tall figure (' + fmt(aspect, 1) + ' times as high as wide)', aspect, top, base };
  return { kind: 'unclear', reason: 'nearly square (' + fmt(aspect, 1) + ') without the pointed base of an isometric building: could be a chibi character, an object or a front-view building', aspect, top, base };
}

/* ---------------------------------------------------------------- isometric or orthographic? */

function gauss(a, w, h, sigma) {            // separable Gaussian blur with edge padding, Float64Array in and out
  const r = Math.floor(3 * sigma) + 1, k = new Float64Array(2 * r + 1);
  let t = 0;
  for (let i = -r; i <= r; i++) { k[i + r] = Math.exp(-0.5 * (i / sigma) * (i / sigma)); t += k[i + r]; }
  for (let i = 0; i < k.length; i++) k[i] /= t;
  const tmp = new Float64Array(w * h), out = new Float64Array(w * h);
  for (let y = 0; y < h; y++) {
    const row = y * w;
    for (let x = 0; x < w; x++) {
      let v = 0;
      for (let i = -r; i <= r; i++) { let xx = x + i; if (xx < 0) xx = 0; else if (xx >= w) xx = w - 1; v += k[i + r] * a[row + xx]; }
      tmp[row + x] = v;
    }
  }
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      let v = 0;
      for (let i = -r; i <= r; i++) { let yy = y + i; if (yy < 0) yy = 0; else if (yy >= h) yy = h - 1; v += k[i + r] * tmp[yy * w + x]; }
      out[y * w + x] = v;
    }
  }
  return out;
}

function normalisedForView(img) {           // the picture at a standard size, as 4 Float64 channels; PIL's BOX / NEAREST resize
  const { w, h, data } = img;
  const longSide = Math.max(w, h);
  if (longSide > T.VIEW_SIDE) {
    const k = T.VIEW_SIDE / longSide;
    const ow = Math.max(1, pyRound(w * k)), oh = Math.max(1, pyRound(h * k));
    // Pillow's BOX resize, step for step: whole source pixels inside the window, coefficients rounded to 22-bit
    // integers, horizontal pass then vertical pass, each rounded to 8 bits.
    const axisWeights = (inN, outN) => {
      const scale = inN / outN, support = 0.5 * scale, list = [];
      for (let xx = 0; xx < outN; xx++) {
        const center = (xx + 0.5) * scale;
        let xmin = Math.trunc(center - support + 0.5), xmax = Math.trunc(center + support + 0.5);
        if (xmin < 0) xmin = 0;
        if (xmax > inN) xmax = inN;
        const raw = []; let sum = 0;
        for (let x = xmin; x < xmax; x++) { const v = (x - center + 0.5) / scale; const wt = (v > -0.5 && v <= 0.5) ? 1 : 0; raw.push(wt); sum += wt; }
        list.push({ xmin, ks: raw.map(v => Math.trunc(0.5 + (v / (sum || 1)) * 4194304)) });
      }
      return list;
    };
    const clip8 = acc => { const v = Math.floor((acc + 2097152) / 4194304); return v < 0 ? 0 : v > 255 ? 255 : v; };
    const wx = axisWeights(w, ow), wy = axisWeights(h, oh);
    const tmp = [new Float64Array(ow * h), new Float64Array(ow * h), new Float64Array(ow * h), new Float64Array(ow * h)];
    for (let y = 0; y < h; y++) for (let x = 0; x < ow; x++) {
      const { xmin, ks } = wx[x];
      for (let c = 0; c < 4; c++) { let v = 0; for (let i = 0; i < ks.length; i++) v += ks[i] * data[(y * w + xmin + i) * 4 + c]; tmp[c][y * ow + x] = clip8(v); }
    }
    const ch = [new Float64Array(ow * oh), new Float64Array(ow * oh), new Float64Array(ow * oh), new Float64Array(ow * oh)];
    for (let y = 0; y < oh; y++) { const { xmin, ks } = wy[y]; for (let x = 0; x < ow; x++) for (let c = 0; c < 4; c++) { let v = 0; for (let i = 0; i < ks.length; i++) v += ks[i] * tmp[c][(xmin + i) * ow + x]; ch[c][y * ow + x] = clip8(v); } }
    return { ch, w: ow, h: oh, enlarged: 1 };
  }
  if (longSide < T.VIEW_MIN_SIDE) {
    const k = Math.ceil(T.VIEW_MIN_SIDE / longSide), ow = w * k, oh = h * k;
    const ch = [new Float64Array(ow * oh), new Float64Array(ow * oh), new Float64Array(ow * oh), new Float64Array(ow * oh)];
    for (let y = 0; y < oh; y++) for (let x = 0; x < ow; x++) { const o = (((y / k) | 0) * w + ((x / k) | 0)) * 4; for (let c = 0; c < 4; c++) ch[c][y * ow + x] = data[o + c]; }
    return { ch, w: ow, h: oh, enlarged: k };
  }
  const ch = [new Float64Array(w * h), new Float64Array(w * h), new Float64Array(w * h), new Float64Array(w * h)];
  for (let i = 0; i < w * h; i++) for (let c = 0; c < 4; c++) ch[c][i] = data[i * 4 + c];
  return { ch, w, h, enlarged: 1 };
}

function classifyView(img, cell) {
  const norm = normalisedForView(img);
  const { ch, w, h } = norm;
  const longSide = Math.max(w, h);
  let sGrad = T.VIEW_GRAD_SIGMA, sWin = Math.max(1.5, T.VIEW_WINDOW_FRACTION * longSide);
  if ((cell === null || cell === undefined) && norm.enlarged > 1) cell = 1.0;
  if (cell) {
    const cellNorm = cell * w / img.w;
    sGrad = Math.max(sGrad, T.VIEW_CELL_BLUR * cellNorm);
    sWin = Math.max(sWin, T.VIEW_CELL_WINDOW * cellNorm);
  }
  const n = w * h;
  const jxx = new Float64Array(n), jyy = new Float64Array(n), jxy = new Float64Array(n);
  for (let c = 0; c < 4; c++) {
    const b = gauss(ch[c], w, h, sGrad);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {      // dx exists for every row, dy for every column (as in numpy)
      const i = y * w + x;
      const dx = (x >= 1 && x <= w - 2) ? (b[i + 1] - b[i - 1]) / 2 : 0;
      const dy = (y >= 1 && y <= h - 2) ? (b[i + w] - b[i - w]) / 2 : 0;
      jxx[i] += dx * dx; jyy[i] += dy * dy; jxy[i] += dx * dy;
    }
  }
  const energy = new Float64Array(n);
  for (let i = 0; i < n; i++) energy[i] = jxx[i] + jyy[i];
  const sxx = gauss(jxx, w, h, sWin), syy = gauss(jyy, w, h, sWin), sxy = gauss(jxy, w, h, sWin);
  const thr = percentile(Float64Array.from(energy).sort(), T.VIEW_ENERGY_PERCENTILE);
  const wts = [], lines = [];
  for (let i = 0; i < n; i++) {
    const tr = Math.max(sxx[i] + syy[i], 1e-9);
    const coh = Math.sqrt((sxx[i] - syy[i]) * (sxx[i] - syy[i]) + 4 * sxy[i] * sxy[i]) / tr;
    if (!(coh >= T.VIEW_COHERENCE_MIN && energy[i] > thr)) continue;
    let ln = (0.5 * Math.atan2(2 * sxy[i], sxx[i] - syy[i]) * 180 / Math.PI + 90) % 180;
    if (ln < 0) ln += 180;
    wts.push(energy[i] * coh * coh); lines.push(ln);
  }
  const coverage = wts.length / n;
  if (coverage < T.VIEW_MIN_COVERAGE) return { kind: 'unclear', horizontal: 0, vertical: 0, diagonal: 0, weakerDiagonal: 0, coverage };
  let tot = 0, hz = 0, vt = 0, rising = 0, falling = 0;
  const counts = new Float64Array(180);
  for (let i = 0; i < wts.length; i++) {
    const ln = lines[i], wv = wts[i];
    let dev = Math.abs(((ln + 90) % 180) - 90);
    tot += wv;
    if (dev <= T.VIEW_AXIS_TOLERANCE) hz += wv;
    if (dev >= 90 - T.VIEW_AXIS_TOLERANCE) vt += wv;
    if (ln >= T.VIEW_ISO_MIN_DEG && ln <= T.VIEW_ISO_MAX_DEG) rising += wv;
    if (ln >= 180 - T.VIEW_ISO_MAX_DEG && ln <= 180 - T.VIEW_ISO_MIN_DEG) falling += wv;
    counts[Math.min(179, Math.floor(ln))] += wv;
  }
  const horiz = hz / tot, vert = vt / tot, diag = (rising + falling) / tot, weaker = Math.min(rising, falling) / tot;
  let csum = 0; for (const v of counts) csum += v;
  let ent = 0; for (const v of counts) if (v > 0) { const p = v / csum; ent -= p * Math.log(p); }
  ent /= Math.log(180);
  if (ent >= T.VIEW_MAX_ENTROPY) return { kind: 'unclear', horizontal: horiz, vertical: vert, diagonal: diag, weakerDiagonal: weaker, coverage };
  let kind;
  if (diag - horiz >= T.ISO_DIAGONAL_MARGIN && weaker >= T.ISO_BOTH_FAMILIES_MIN) kind = 'isometric';
  else if (horiz + vert >= T.ORTHO_AXIS_MIN && diag - horiz < T.ISO_DIAGONAL_MARGIN) kind = 'orthogonal';
  else kind = 'unclear';
  return { kind, horizontal: horiz, vertical: vert, diagonal: diag, weakerDiagonal: weaker, coverage };
}

/* ---------------------------------------------------------------- ground shadows */

function shadowKind(dx, reachLeft, reachRight) {
  return (Math.abs(dx) >= T.SHADOW_CAST_OFFSET || Math.abs(reachLeft - reachRight) >= T.SHADOW_CAST_ASYMMETRY) ? 'cast' : 'contact';
}

function dilate(mask, w, h, times) {
  let cur = mask;
  for (let t = 0; t < times; t++) {
    const n = Uint8Array.from(cur);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = y * w + x;
      if (cur[i]) continue;
      if ((y > 0 && cur[i - w]) || (y < h - 1 && cur[i + w]) || (x > 0 && cur[i - 1]) || (x < w - 1 && cur[i + 1])) n[i] = 1;
    }
    cur = n;
  }
  return cur;
}

function noShadow(reason, unsure) { return { found: false, unsure: !!unsure, reason, share: 0, darkness: 1, dx: 0, dy: 0, mask: null, scale: 1, mw: 0, mh: 0, reachLeft: 0, reachRight: 0, kind: '' }; }

function findShadow(img, framing) {
  if (framing.kind !== 'isolated' || !framing.mask) return noShadow('not a lone sprite on a plain ground');
  const col = framing.background.colour;
  const cmean = (col[0] + col[1] + col[2]) / 3;
  if (cmean >= T.SHADOW_WHITE_GROUND && Math.max(...col) - Math.min(...col) <= 20)
    return noShadow('on a white ground a pale shadow looks the same as pale grey parts of the sprite', true);
  const s = framing.scale, { w: W, h: H, data } = img;
  const hh = Math.floor(H / s), ww = Math.floor(W / s), n = hh * ww;
  const like = new Uint8Array(n), kk = new Float64Array(n), bright = new Float64Array(n);
  const c = framing.background.coef;
  for (let y = 0; y < hh; y++) for (let x = 0; x < ww; x++) {
    let r = 0, g = 0, b = 0;
    for (let yy = 0; yy < s; yy++) for (let xx = 0; xx < s; xx++) { const o = ((y * s + yy) * W + x * s + xx) * 4; r += data[o]; g += data[o + 1]; b += data[o + 2]; }
    const cnt = s * s; r /= cnt; g /= cnt; b /= cnt;
    const nx = (x * s + s / 2) / W, ny = (y * s + s / 2) / H;
    const gr = groundAt(c, nx, ny);
    const rr = r / Math.max(gr[0], 1), rg = g / Math.max(gr[1], 1), rb = b / Math.max(gr[2], 1);
    const k = (rr + rg + rb) / 3, chroma = Math.max(Math.abs(rr - k), Math.abs(rg - k), Math.abs(rb - k));
    const i = y * ww + x;
    kk[i] = k; bright[i] = (gr[0] + gr[1] + gr[2]) / 3;
    like[i] = (k >= T.SHADOW_K_MIN && k <= T.SHADOW_K_MAX && chroma <= T.SHADOW_CHROMA_DEV && bright[i] >= T.SHADOW_MIN_GROUND) ? 1 : 0;
  }
  const mask = new Uint8Array(n);                 // the framing mask, cropped to the same grid
  for (let y = 0; y < hh; y++) for (let x = 0; x < ww; x++) if (x < framing.mw && y < framing.mh) mask[y * ww + x] = framing.mask[y * framing.mw + x];
  const openGround = new Uint8Array(n);
  for (let i = 0; i < n; i++) openGround[i] = (!mask[i] && kk[i] > T.SHADOW_K_MAX && kk[i] < 1.15) ? 1 : 0;

  const eligible = new Uint8Array(n);
  const notes = [];
  for (const region of components(like, ww, hh)) {
    if (region.length < T.SHADOW_MIN_CELLS) continue;
    const patch = new Uint8Array(n);
    for (const i of region) patch[i] = 1;
    const grown = dilate(patch, ww, hh, 1);
    let ring = 0, open = 0;
    for (let i = 0; i < n; i++) if (grown[i] && !patch[i]) { ring++; if (openGround[i]) open++; }
    if (ring === 0 || open / ring < T.SHADOW_GROUND_CONTACT) { notes.push('enclosed by the sprite, not lying on open ground'); continue; }
    for (const i of region) eligible[i] = 1;
  }
  let core = new Uint8Array(n), coreCount = 0;
  for (let i = 0; i < n; i++) if (mask[i] && !eligible[i]) { core[i] = 1; coreCount++; }
  if (coreCount < 4) return noShadow('no subject found');
  const comps = components(core, ww, hh);
  let keep = comps[0];
  for (const cc of comps) if (cc.length > keep.length) keep = cc;
  const big = comps.filter(cc => cc.length >= 0.15 * keep.length);
  core = new Uint8Array(n); coreCount = 0;
  for (const cc of (big.length ? big : [keep])) for (const i of cc) { core[i] = 1; coreCount++; }
  let cy0 = Infinity, cy1 = -1, cx0 = Infinity, cx1 = -1;
  for (let i = 0; i < n; i++) if (core[i]) { const y = (i / ww) | 0, x = i - y * ww; if (y < cy0) cy0 = y; if (y > cy1) cy1 = y; if (x < cx0) cx0 = x; if (x > cx1) cx1 = x; }
  const coreH = cy1 - cy0 + 1, coreW = cx1 - cx0 + 1, baseY = cy1, baseX = (cx0 + cx1) / 2;
  const near = dilate(core, ww, hh, 2);

  const accepted = new Uint8Array(n);
  const width = 2 * T.SHADOW_FLAT_STD, step = width / 2;
  const bands = Math.ceil((T.SHADOW_K_MAX - T.SHADOW_K_MIN) / step);
  for (let bi = 0; bi < bands; bi++) {
    const lo = T.SHADOW_K_MIN + bi * step;
    const band = new Uint8Array(n);
    for (let i = 0; i < n; i++) if (eligible[i] && kk[i] >= lo && kk[i] < lo + width) band[i] = 1;
    for (const comp of components(band, ww, hh)) {
      if (comp.length < T.SHADOW_MIN_CELLS) continue;
      let sy = 0, sx = 0, touches = false;
      for (const i of comp) { const y = (i / ww) | 0; sy += y; sx += i - y * ww; if (near[i]) touches = true; }
      const my = sy / comp.length, mx = sx / comp.length;
      if (comp.length < T.SHADOW_PIECE_SHARE * coreCount) { notes.push('too small'); continue; }
      if (my < baseY - T.SHADOW_BASE_ALLOWANCE * coreH) { notes.push('higher up the subject, not at the base'); continue; }
      if (Math.abs(mx - baseX) > T.SHADOW_REACH * coreW + coreW / 2) { notes.push('too far to the side'); continue; }
      if (!touches) { notes.push('does not touch the subject'); continue; }
      for (const i of comp) accepted[i] = 1;
    }
  }
  let acc = 0;
  for (let i = 0; i < n; i++) if (accepted[i]) acc++;
  if (!acc) return noShadow(notes.length ? notes[0] : 'no darker-ground patch at the base');
  if (acc < T.SHADOW_MIN_SHARE * coreCount) return noShadow('only small darker patches at the base');
  if (acc > T.SHADOW_MAX_SHARE * coreCount) return noShadow('the darker patch is as big as the subject itself: probably its own dark colours');
  let sxMin = Infinity, sxMax = -1, syMin = Infinity, syMax = -1, sxSum = 0, sySum = 0, kSum = 0;
  for (let i = 0; i < n; i++) if (accepted[i]) { const y = (i / ww) | 0, x = i - y * ww; if (x < sxMin) sxMin = x; if (x > sxMax) sxMax = x; if (y < syMin) syMin = y; if (y > syMax) syMax = y; sxSum += x; sySum += y; kSum += kk[i]; }
  const reachLeft = Math.max(0, (cx0 - sxMin) / coreW), reachRight = Math.max(0, (sxMax + 1 - (cx1 + 1)) / coreW);
  if ((sxMax - sxMin + 1) < T.SHADOW_MIN_ASPECT * (syMax - syMin + 1)) return noShadow('the darker patch is taller than wide, like a limb or trunk, not a shadow lying on the ground');
  const dx = (sxSum / acc - baseX) / coreW, dy = (sySum / acc - baseY) / coreH;
  return {
    found: true, unsure: false, reason: 'a flat patch of darker ground at the base', share: acc / coreCount, darkness: kSum / acc,
    dx, dy, mask: accepted, mw: ww, mh: hh, scale: s, reachLeft, reachRight, kind: shadowKind(dx, reachLeft, reachRight),
    core, coreBox: [cx0, cy0, cx1, cy1],
  };
}

function removeShadow(sprite, bx, by, info, framing) {   // sprite: {w,h,data}; returns the number of pixels changed
  if (!info.found || !info.mask) return 0;
  const s = info.scale, fullW = bx[bx.length - 1], fullH = by[by.length - 1];
  const w = bx.length - 1, h = by.length - 1;
  const ox = new Float64Array(w), oy = new Float64Array(h);
  for (let i = 0; i < w; i++) ox[i] = (bx[i] + bx[i + 1]) / 2;
  for (let j = 0; j < h; j++) oy[j] = (by[j] + by[j + 1]) / 2;
  const grown = dilate(info.mask, info.mw, info.mh, 1);
  const c = framing.background.coef, d = sprite.data;
  const remove = new Uint8Array(w * h), kOf = new Float64Array(w * h), chromaOf = new Float64Array(w * h), inside = new Uint8Array(w * h);
  const groundAtCell = new Float64Array(w * h * 3);
  for (let j = 0; j < h; j++) {
    const cyy = Math.max(0, Math.min(info.mh - 1, Math.trunc(oy[j] / s)));
    for (let i = 0; i < w; i++) {
      const cxx = Math.max(0, Math.min(info.mw - 1, Math.trunc(ox[i] / s)));
      const g = groundAt(c, ox[i] / fullW, oy[j] / fullH), o = (j * w + i) * 4, idx = j * w + i;
      const r0 = d[o] / Math.max(g[0], 1), r1 = d[o + 1] / Math.max(g[1], 1), r2 = d[o + 2] / Math.max(g[2], 1);
      const k = (r0 + r1 + r2) / 3, ch = Math.max(Math.abs(r0 - k), Math.abs(r1 - k), Math.abs(r2 - k));
      kOf[idx] = k; chromaOf[idx] = ch; inside[idx] = grown[cyy * info.mw + cxx];
      groundAtCell[idx * 3] = g[0]; groundAtCell[idx * 3 + 1] = g[1]; groundAtCell[idx * 3 + 2] = g[2];
      const darker = k >= T.SHADOW_K_MIN && k <= T.SHADOW_REMOVE_K_MAX && ch <= T.SHADOW_CHROMA_DEV && d[o + 3] >= 128;
      remove[idx] = (inside[idx] && darker) ? 1 : 0;
    }
  }
  let count = 0;
  for (let i = 0; i < remove.length; i++) if (remove[i]) count++;
  if (!count) return 0;
  const palette = new Map();
  for (let i = 0; i < w * h; i++) {
    if (!inside[i] && kOf[i] >= 0.97 && kOf[i] <= 1.05 && chromaOf[i] <= 0.05) { const o = i * 4; palette.set((d[o] << 16) | (d[o + 1] << 8) | d[o + 2], [d[o], d[o + 1], d[o + 2]]); }
  }
  const pal = [...palette.values()];
  for (let i = 0; i < w * h; i++) {
    if (!remove[i]) continue;
    const want = [0, 1, 2].map(cc => Math.max(0, Math.min(255, Math.round(groundAtCell[i * 3 + cc]))));   // numpy.rint ~ Math.round except exact halves
    let best = null, bd = Infinity;
    for (const p of pal) { const dd = Math.abs(want[0] - p[0]) + Math.abs(want[1] - p[1]) + Math.abs(want[2] - p[2]); if (dd < bd) { bd = dd; best = p; } }
    const use = (best && bd <= 2 * T.COLOUR_MERGE_TOLERANCE) ? best : want;
    const o = i * 4; d[o] = use[0]; d[o + 1] = use[1]; d[o + 2] = use[2];
  }
  return count;
}

/* ---------------------------------------------------------------- facing (measured, never decided) */

function measureFacingClues(framing, shadow) {
  const mw = framing.mw, mh = framing.mh;
  const m = Uint8Array.from(framing.mask);
  if (shadow && shadow.found && shadow.mask) for (let y = 0; y < Math.min(mh, shadow.mh); y++) for (let x = 0; x < Math.min(mw, shadow.mw); x++) if (shadow.mask[y * shadow.mw + x]) m[y * mw + x] = 0;
  let total = 0, x0 = Infinity, x1 = -1, y0 = Infinity, y1 = -1;
  for (let i = 0; i < m.length; i++) if (m[i]) { total++; const y = (i / mw) | 0, x = i - y * mw; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  if (total < 20) return {};
  const h = y1 - y0 + 1, w = x1 - x0 + 1;
  const sub = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) sub[y * w + x] = m[(y0 + y) * mw + x0 + x];
  let subTotal = 0, sym = 0;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (sub[y * w + x]) { subTotal++; if (sub[y * w + (w - 1 - x)]) sym++; }
  const centre = (y0r, y1r) => { let num = 0, den = 0; for (let y = y0r; y < y1r; y++) for (let x = 0; x < w; x++) if (sub[y * w + x]) { num += x; den++; } return den ? num / den : w / 2; };
  const nb = Math.max(2, Math.floor(0.14 * h));
  const bottom = new Uint8Array(w * nb);
  for (let y = 0; y < nb; y++) for (let x = 0; x < w; x++) bottom[y * w + x] = sub[(h - nb + y) * w + x];
  let blobs = components(bottom, w, nb).sort((a, b) => b.length - a.length);
  const filtered = blobs.filter(b => b.length >= 0.012 * subTotal);
  blobs = filtered.length ? filtered : blobs.slice(0, 1);
  let feetDx = 0, feetDy = 0;
  if (blobs.length >= 2) {
    const mean = (b, fn) => b.reduce((s, i) => s + fn(i), 0) / b.length;
    const cx = b => mean(b, i => i % w), cy = b => mean(b, i => (i / w) | 0);
    feetDx = Math.abs(cx(blobs[0]) - cx(blobs[1])) / w; feetDy = Math.abs(cy(blobs[0]) - cy(blobs[1])) / h;
  }
  const r3 = v => Math.round(v * 1000) / 1000;
  const headEnd = Math.max(2, Math.floor(0.22 * h));
  return {
    symmetry: r3(sym / subTotal), feet_apart: r3(feetDx), feet_level: r3(feetDy),
    torso_leg_shift: r3((centre(0, Math.floor(0.4 * h)) - centre(Math.floor(0.6 * h), h)) / w),
    head_off_torso: r3((centre(0, headEnd) - centre(Math.floor(0.25 * h), Math.floor(0.6 * h))) / w),
    height_over_width: Math.round(h / w * 100) / 100,
  };
}

function classifyFacing(framing, subject, shadow) {
  if (subject.kind !== 'character' || framing.kind !== 'isolated' || !framing.mask) return { kind: 'n/a', reason: 'only characters are judged on facing', clues: {} };
  return { kind: 'unclear', reason: 'the geometric clues did not separate diagonal from straight-on facing', clues: measureFacingClues(framing, shadow) };
}

/* ---------------------------------------------------------------- putting it together */

function analyse(img) {
  if (Math.min(img.w, img.h) < T.MIN_PICTURE_SIDE)
    throw new Error('picture too small to analyse (' + img.w + 'x' + img.h + '): it needs at least ' + T.MIN_PICTURE_SIDE + ' pixels on each side');
  const ex = [edgeProfile(img, 0, [1]), edgeProfile(img, 1, [1])];
  const wx = [edgeProfile(img, 0, T.EDGE_GAPS), edgeProfile(img, 1, T.EDGE_GAPS)];
  let dx = detectAxis(wx[0], ex[0]), dy = detectAxis(wx[1], ex[1]);
  [dx, dy] = reconcileSquare(dx, dy, wx[0], wx[1], ex[0], ex[1]);
  const { w, h } = img;
  const guess = 'best guess ' + fmt(dx.p, 1) + ' x ' + fmt(dy.p, 1) + ' px, scores ' + fmt(dx.score, 2) + ' and ' + fmt(dy.score, 2);
  const weakOk = (a, n) => a.weak && n / a.p >= T.GRID_WEAK_MIN_CELLS;
  const out = (found, status, note) => ({ ex: ex[0], ey: ex[1], dx, dy, found, status, note });
  if (dx.ok || dy.ok) {
    if (!dx.ok) { dx = fitPhase(ex[0], dy.p); dx.borrowed = true; }
    else if (!dy.ok) { dy = fitPhase(ex[1], dx.p); dy.borrowed = true; }
    return out(true, 'found', 'clear pixel grid found');
  }
  let okx = weakOk(dx, w), oky = weakOk(dy, h);
  if ((okx || oky) && Math.min(w / dx.p, h / dy.p) < T.GRID_WEAK_MIN_CELLS) okx = oky = false;
  if (okx || oky) {
    if (okx && oky && Math.abs(dx.p - dy.p) / ((dx.p + dy.p) / 2) > T.GRID_WEAK_AGREE) { const a = dx.score >= dy.score, b = dy.score > dx.score; okx = a; oky = b; }
    if (okx && !oky) { dy = fitPhase(ex[1], dx.p); dy.borrowed = true; }
    else if (oky && !okx) { dx = fitPhase(ex[0], dy.p); dx.borrowed = true; }
    return out(true, 'weak', 'weak pixel grid (' + fmt(dx.p, 1) + ' x ' + fmt(dy.p, 1) + ' px): ' + (dx.disagree ? 'width and height gave different sizes, ' : 'the blocks are soft or uneven, ') + 'so check the result');
  }
  return out(false, 'none', 'no regular pixel grid found (' + guess + '); the picture may be painted, smooth or already true size. To pixelate it anyway, give a pixel size');
}

/* opts: {cell, follow, colours, transparent, shadows: 'keep'|'remove-cast'|'remove-all'} */
function rebuild(img, an, opts) {
  opts = Object.assign({ cell: null, follow: true, colours: 0, transparent: false, shadows: 'keep' }, opts || {});
  const { w, h } = img;
  let dx = an.dx, dy = an.dy, found = an.found;
  if (opts.cell) { dx = fitPhase(an.ex, opts.cell); dy = fitPhase(an.ey, opts.cell); found = true; }
  let status = opts.cell ? 'manual' : an.status, flat = null, bx, by, out;
  let note = opts.cell ? 'pixel size set by hand (' + opts.cell + ')' : an.note;
  if (found) {
    bx = makeBounds(an.ex, dx.p, dx.off, w, opts.follow);
    by = makeBounds(an.ey, dy.p, dy.off, h, opts.follow);
    flat = cellFlatness(img, bx, by);
    if (!opts.cell) {
      if (flat < T.FLAT_NONE) {
        found = false; status = 'none';
        note = 'no usable pixel grid: the blocks are not flat inside (flatness ' + fmt(flat, 2) + '), so the picture looks painted or smooth, not pixel art. To pixelate it anyway, give a pixel size';
      } else if (flat < T.FLAT_STRONG && status === 'found') {
        status = 'weak';
        note = 'pixel grid found (' + fmt(dx.p, 1) + ' x ' + fmt(dy.p, 1) + ' px) but the blocks are not very flat inside (flatness ' + fmt(flat, 2) + '): painted or soft, so check the result';
      }
    }
  }
  if (!found) { dx = dy = { p: 1, off: 0 }; bx = []; by = []; out = null; }
  else out = sampleCells(img, bx, by);
  const framing = classifyFraming(img);
  const shadow = findShadow(img, framing);
  let raw = 0;
  if (found) {
    raw = countColours(out);
    mergeSimilar(out, T.COLOUR_MERGE_TOLERANCE);
    if (opts.colours > 0) quantize(out, opts.colours);
  }
  let shadowRemoved = 0;
  if (found && opts.shadows !== 'keep' && shadow.found && (opts.shadows === 'remove-all' || shadow.kind === 'cast'))
    shadowRemoved = removeShadow(out, bx, by, shadow, framing);
  const crisp = found && flat !== null && flat >= T.VIEW_CELL_MIN_FLATNESS;
  const view = classifyView(img, crisp ? (dx.p + dy.p) / 2 : null);
  const subject = classifySubject(framing);
  let transparent = false;
  if (opts.transparent && found && framing.kind === 'isolated') transparent = removeBackground(out) > 0;
  const facing = classifyFacing(framing, subject, shadow);
  return {
    sprite: out, bx, by, px: dx.p, py: dy.p, found, coloursRaw: raw, colours: found ? countColours(out) : 0,
    view, framing, transparent, gridStatus: status, gridNote: note, subject, shadow, facing, flatness: flat, shadowRemoved,
  };
}

function snap(img, opts) { return rebuild(img, analyse(img), opts); }

/* ---------------------------------------------------------------- sorting a batch */

const BUCKETS = ['matches', 'mismatches', 'cant-tell', 'not-pixel-art'];
function decide(res, wantView, wantFacing) {
  wantView = wantView || 'either'; wantFacing = wantFacing || 'either';
  if (res.gridStatus === 'none') return { bucket: 'not-pixel-art', reason: res.gridNote, weak: false };
  const weak = res.gridStatus === 'weak';
  if (res.subject.kind === 'character') {
    if (wantFacing === 'either') return { bucket: 'matches', reason: 'a character; no facing was asked for', weak };
    const f = res.facing;
    if (!f || f.kind === 'unclear' || f.kind === 'mixed' || f.kind === 'n/a') {
      const why = !f ? 'the facing check is not built yet' : (f.kind === 'mixed' ? 'the facing is mixed' : 'the tool cannot judge facing yet');
      return { bucket: 'cant-tell', reason: 'a character, and you asked for ' + wantFacing + ' facing, but ' + why, weak: false };
    }
    if (f.kind === wantFacing) return { bucket: 'matches', reason: 'a character facing ' + f.kind + ', as asked', weak };
    return { bucket: 'mismatches', reason: 'a character facing ' + f.kind + '; you asked for ' + wantFacing, weak: false };
  }
  if (wantView === 'either') return { bucket: 'matches', reason: res.subject.kind + '; no view was asked for', weak };
  const seen = res.view.kind;
  if (seen === 'unclear') return { bucket: 'cant-tell', reason: res.subject.kind + ', and you asked for ' + wantView + ', but the view is unclear', weak: false };
  if (seen === wantView) return { bucket: 'matches', reason: res.subject.kind + ', ' + seen + ', as asked', weak };
  return { bucket: 'mismatches', reason: res.subject.kind + '; you asked for ' + wantView + ' but it is ' + seen, weak: false };
}

root.SnapCore = { VERSION: '/*VERSION*/', T, normalisedForView, gauss, analyse, rebuild, snap, decide, BUCKETS, classifyFraming, classifyView, findShadow, estimateBackground };
})(typeof self !== 'undefined' ? self : this);

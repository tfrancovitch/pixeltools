// Compare the browser version (web/core.built.js) with the Python tool, picture by picture.
// Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
//   python web/build_web.py && python eval/web_reference.py <folder> ref.json && node eval/web_parity.js <folder> ref.json [limit]
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const [folder, refPath, limitArg] = process.argv.slice(2);
const ref = JSON.parse(fs.readFileSync(refPath, 'utf8'));
const core = fs.readFileSync(path.join(__dirname, '..', 'web', 'core.built.js'), 'utf8');
let names = Object.keys(ref).sort();
if (limitArg) names = names.slice(0, parseInt(limitArg, 10));

const near = (a, b, tol) => Math.abs(a - b) <= tol;
const sameKeys = ['grid', 'w', 'h', 'framing', 'subject', 'view', 'shadow', 'shadow_kind', 'facing'];
const numTol = { px: 0.15, py: 0.15, flat: 0.01, border: 0.02, share: 0.02, diag: 0.03, horiz: 0.03, vert: 0.03, weaker: 0.03, shadow_share: 0.02, shadow_dx: 0.05 };

async function worker(browser, queue, results) {
  const page = await browser.newPage();
  await page.setContent('<html><body></body></html>');
  await page.addScriptTag({ content: core });
  while (queue.length) {
    const name = queue.shift();
    const b64 = fs.readFileSync(path.join(folder, name)).toString('base64');
    const t0 = Date.now();
    const got = await page.evaluate(async ({ b64, name }) => {
      const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
      const bmp = await createImageBitmap(new Blob([bin]), { colorSpaceConversion: 'none' });
      const c = new OffscreenCanvas(bmp.width, bmp.height), ctx = c.getContext('2d', { willReadFrequently: true });
      ctx.drawImage(bmp, 0, 0);
      const d = ctx.getImageData(0, 0, bmp.width, bmp.height);
      const img = { w: bmp.width, h: bmp.height, data: d.data };
      const S = SnapCore;
      const an = S.analyse(img);
      const r = S.rebuild(img, an, {});
      const out = {
        grid: r.gridStatus, px: r.px, py: r.py, w: r.found ? r.sprite.w : img.w, h: r.found ? r.sprite.h : img.h, flat: r.flatness,
        colours: r.colours, framing: r.framing.kind, border: r.framing.borderUniform, share: r.framing.subjectShare,
        subject: r.subject.kind, view: r.view.kind, diag: r.view.diagonal, horiz: r.view.horizontal, vert: r.view.vertical, weaker: r.view.weakerDiagonal,
        shadow: r.shadow.unsure ? 'unsure' : (r.shadow.found ? 'found' : 'none'), shadow_kind: r.shadow.found ? r.shadow.kind : '',
        shadow_share: r.shadow.found ? r.shadow.share : 0, shadow_dx: r.shadow.found ? r.shadow.dx : 0, facing: r.facing.kind,
      };
      const r2 = S.rebuild(img, an, { shadows: 'remove-all', transparent: true });
      out.removed_all = r2.shadowRemoved; out.transparent = !!r2.transparent;
      return out;
    }, { b64, name });
    results[name] = { got, ms: Date.now() - t0 };
  }
  await page.close();
}

(async () => {
  const browser = await chromium.launch();
  const queue = names.slice(), results = {};
  await Promise.all([0, 1, 2, 3].map(() => worker(browser, queue, results)));
  await browser.close();
  const bad = [];
  let slow = 0, maxMs = 0;
  for (const name of names) {
    const { got, ms } = results[name], want = ref[name];
    maxMs = Math.max(maxMs, ms); slow += ms;
    const diffs = [];
    for (const k of sameKeys) if (got[k] !== want[k]) diffs.push(`${k}: browser ${got[k]} vs python ${want[k]}`);
    for (const [k, tol] of Object.entries(numTol)) if (got[k] !== null && want[k] !== null && !near(got[k], want[k], tol)) diffs.push(`${k}: browser ${Number(got[k]).toFixed(3)} vs python ${want[k]}`);
    if (got.removed_all !== want.removed_all && Math.abs(got.removed_all - want.removed_all) > 0.05 * Math.max(1, want.removed_all)) diffs.push(`removed_all: browser ${got.removed_all} vs python ${want.removed_all}`);
    if (diffs.length) bad.push([name, diffs]);
  }
  console.log(`${names.length} pictures, ${names.length - bad.length} identical on every checked value, ${bad.length} with differences; average ${(slow / names.length / 1000).toFixed(1)} s each (4 at a time), slowest ${(maxMs / 1000).toFixed(1)} s`);
  for (const [n, d] of bad.slice(0, 40)) console.log('  ' + n + ': ' + d.join('; '));
  process.exitCode = bad.length ? 1 : 0;
})();

// Smoke test of one built page in a real browser at phone width. Run: node tests/smoke.js turn [--no-worker]
// Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
// Checks: loads, works on the sample, the tool changes the picture, undo and before/after work, no network
// requests, no page errors, no sideways scrolling.
const path = require('path');
const { chromium } = require('playwright');
const tool = process.argv[2], noWorker = process.argv.includes('--no-worker');
const url = 'file://' + path.join(__dirname, '..', 'pages', tool + '.html') + (noWorker ? '#no-worker' : '');
// What to press for each tool: optionally tap the picture, then press a button.
const STEPS = {
  turn: { tap: false, button: 'Flip left-right' },
  fill: { tap: [0.5, 0.05], button: 'Fill' },
  replace: { tap: [0.5, 0.3], button: 'Replace' },
  flatten: { tap: false, button: 'Flatten' },
};
(async () => {
  const fail = [];
  const check = (ok, what) => { if (!ok) fail.push(what); console.log((ok ? 'ok   ' : 'FAIL ') + what); };
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 400, height: 900 } });
  const errs = [], outside = [];
  page.on('pageerror', e => errs.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  page.on('request', r => { const u = r.url(); if (!/^(file:|data:|blob:|about:)/.test(u)) outside.push(u); });
  await page.goto(url);
  const sideways = () => page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  check(!(await sideways()), 'no sideways scrolling before a picture is loaded');
  await page.click('#sampleBtn');
  await page.waitForFunction(() => document.getElementById('shown').naturalWidth > 0);
  check(true, 'the sample loads');
  const before = await page.evaluate(() => document.getElementById('shown').src);
  const step = STEPS[tool];
  if (step.tap) {
    const box = await page.locator('#shown').boundingBox();
    await page.mouse.click(box.x + box.width * step.tap[0], box.y + box.height * step.tap[1]);
    check(await page.evaluate(() => !document.getElementById('mark').hidden), 'tapping the picture shows the chosen point');
  }
  await page.click('button:has-text("' + step.button + '")');
  await page.waitForFunction(() => /changed|Nothing changed/.test(document.getElementById('status').textContent), null, { timeout: 60000 });
  const status = await page.textContent('#status');
  console.log('     status: ' + status);
  const after = await page.evaluate(() => document.getElementById('shown').src);
  check(after !== before, 'the tool changed the picture');
  check(!status.includes('Tap the picture') && !/is not a/.test(status), 'the tool ran without a complaint');
  if (tool === 'fill') {   // the owner's real problem: the whole noisy ground in one press, with no tap
    await page.click('#undoBtn');
    await page.click('#c_background');
    await page.click('button:has-text("Fill")');
    await page.waitForFunction(() => /pixels changed/.test(document.getElementById('status').textContent));
    const st = await page.textContent('#status');
    const n = parseInt(st.replace(/,/g, ''), 10);
    check(n > 2000, 'fill background: most of the sample ground is filled (' + st + ')');
  }
  await page.click('#beforeBtn');
  check(await page.evaluate(() => document.getElementById('shown').src) === before, '"Show before" shows the original');
  await page.click('#beforeBtn');
  await page.click('#undoBtn');
  check(await page.evaluate(() => document.getElementById('shown').src) === before, 'undo brings the original back');
  check(!(await sideways()), 'no sideways scrolling at phone width with a picture loaded');
  check(outside.length === 0, 'the page makes no network requests' + (outside.length ? ': ' + outside[0] : ''));
  check(errs.length === 0, 'no page errors' + (errs.length ? ': ' + errs[0] : ''));
  await browser.close();
  process.exitCode = fail.length ? 1 : 0;
})();

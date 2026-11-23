// Smoke test of the single-file page in a real browser at phone width. Run: node eval/web_ui_smoke.js [folder with pictures]
// Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const noWorker = process.argv.includes('--no-worker');
const page_url = 'file://' + path.join(__dirname, '..', 'pixel-snap.html') + (noWorker ? '#no-worker' : '');
const folder = process.argv.slice(2).find(a => !a.startsWith('--'));
(async () => {
  const fail = [];
  const check = (ok, what) => { if (!ok) fail.push(what); console.log((ok ? 'ok   ' : 'FAIL ') + what); };
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 400, height: 900 } });
  const errs = [];
  page.on('pageerror', e => errs.push(e.message));
  await page.goto(page_url);
  await page.waitForFunction(() => document.getElementById('status').textContent.includes('picture'), null, { timeout: 90000 });
  check(await page.$$eval('.card', c => c.length) === 1, 'the sample loads by itself and shows one card');
  await page.click('.card');
  await page.waitForFunction(() => document.getElementById('result').naturalWidth > 0, null, { timeout: 20000 });
  check(true, 'tapping a card shows the sprite');
  check(!(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)), 'no sideways scrolling at phone width');
  if (folder) {
    const files = fs.readdirSync(folder).filter(f => /\.(png|jpg)$/i.test(f)).sort().map(f => path.join(folder, f));
    await page.click('#clearBtn');
    await page.click('#segView button[data-v="orthogonal"]');
    await page.setInputFiles('#file', files);
    await page.waitForFunction(n => document.querySelectorAll('.card .tag').length === n && ![...document.querySelectorAll('.card .tag')].some(t => /Working|Waiting/.test(t.textContent)), files.length, { timeout: 180000 });
    const tagsOrtho = await page.$$eval('.card', c => Object.fromEntries(c.map(x => [x.querySelector('.name').textContent, x.querySelector('.tag').textContent])));
    check(Object.keys(tagsOrtho).length === files.length, 'every picture in the batch got a result');
    check(Object.values(tagsOrtho).some(t => t === 'Wrong view'), 'wanting straight-on puts an isometric picture in "Wrong view"');
    await page.click('#segView button[data-v="isometric"]');
    await page.waitForFunction(() => ![...document.querySelectorAll('.card .tag')].some(t => /Working|Waiting/.test(t.textContent)), null, { timeout: 180000 });
    await page.waitForTimeout(500);
    const tagsIso = await page.$$eval('.card', c => Object.fromEntries(c.map(x => [x.querySelector('.name').textContent, x.querySelector('.tag').textContent])));
    check(JSON.stringify(tagsIso) !== JSON.stringify(tagsOrtho), 'changing the wanted view re-sorts the batch');
    const csv = await page.evaluate(() => reportCsv());
    check(csv.split('\n').length === files.length + 1 && csv.startsWith('file,folder,reason'), 'the CSV report has a header and one row per picture');
  }
  check(errs.length === 0, 'no page errors' + (errs.length ? ': ' + errs[0] : ''));
  await browser.close();
  process.exitCode = fail.length ? 1 : 0;
})();

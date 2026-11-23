// Checks the site/ folder behaves as an installable, offline web app, served the way GitHub Pages serves it.
// Run: node eval/web_pwa_check.js <port of a static server serving site/>
// Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
const { chromium } = require('playwright');
const base = `http://127.0.0.1:${process.argv[2]}/`;
(async () => {
  const fail = [];
  const check = (ok, what) => { if (!ok) fail.push(what); console.log((ok ? 'ok   ' : 'FAIL ') + what); };
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 400, height: 900 } });
  const page = await context.newPage();
  const errs = []; page.on('pageerror', e => errs.push(e.message));
  await page.goto(base);
  await page.waitForFunction(() => /^\d+ pictures?:/.test(document.getElementById('status').textContent), null, { timeout: 90000 });
  check(true, 'the page loads over http and processes the sample');
  const ready = await page.evaluate(async () => { const r = await navigator.serviceWorker.ready; return !!r.active; });
  check(ready, 'the service worker is active');
  const manifest = await (await page.request.get(base + 'manifest.webmanifest')).json();
  check(manifest.name === 'Pixel Snap' && manifest.display === 'standalone' && manifest.start_url === './', 'the manifest names the app and opens it standalone');
  const sizes = manifest.icons.map(i => i.sizes).sort();
  check(sizes.includes('192x192') && sizes.includes('512x512'), 'the manifest has 192 and 512 pixel icons');
  for (const i of manifest.icons) check((await page.request.get(base + i.src)).ok(), 'icon file ' + i.src + ' is served');
  check(await page.evaluate(() => !!document.querySelector('link[rel=manifest]') && !!document.querySelector('meta[name=theme-color]')), 'the page links its manifest and theme color');
  // go offline and open it again: it must come from the device
  await context.setOffline(true);
  const offline = await context.newPage();
  await offline.goto(base);
  await offline.waitForFunction(() => /^\d+ pictures?:/.test(document.getElementById('status').textContent), null, { timeout: 90000 });
  check(true, 'offline: the page opens and processes the sample with no network');
  check(errs.length === 0, 'no page errors' + (errs.length ? ': ' + errs[0] : ''));
  await browser.close();
  process.exitCode = fail.length ? 1 : 0;
})();

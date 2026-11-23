// Run the browser core on every case from make_parity.py and compare every pixel with Python's answer.
// Needs only Node. Run: node tests/parity.js cases.json
// Copyright (C) 2026 the pixeltools contributors. Licensed under the GNU GPL v3 or later.
const fs = require('fs'), vm = require('vm'), path = require('path');
const ctx = {}; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'web', 'core.built.js'), 'utf8'), ctx);
const core = ctx.SpriteCore;
const cases = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const norm = u8 => { const d = Uint8ClampedArray.from(u8); for (let i = 0; i < d.length; i += 4) if (d[i + 3] === 0) { d[i] = d[i + 1] = d[i + 2] = 0; } return d; };
let bad = 0, same = 0;
for (const c of cases) {
  const input = { w: c.w, h: c.h, data: new Uint8ClampedArray(Buffer.from(c.input, 'base64')) };
  let got, err = null;
  try { got = core.run(c.tool, input, c.opts); } catch (e) { err = e.message; }
  const problems = [];
  if (c.error !== undefined) { if (err !== c.error) problems.push('error: browser "' + err + '" vs python "' + c.error + '"'); }
  else if (err) problems.push('browser failed: ' + err);
  else {
    const want = new Uint8ClampedArray(Buffer.from(c.expected, 'base64')), have = norm(got.img.data);
    if (got.img.w !== c.ow || got.img.h !== c.oh) problems.push('size ' + got.img.w + 'x' + got.img.h + ' vs ' + c.ow + 'x' + c.oh);
    else { let n = 0; for (let i = 0; i < want.length; i++) if (want[i] !== have[i]) n++; if (n) problems.push(n + ' channel values differ'); }
    for (const k of Object.keys(c.info)) if (got.info[k] !== c.info[k]) problems.push(k + ': browser ' + got.info[k] + ' vs python ' + c.info[k]);
  }
  if (problems.length) { bad++; console.log('DIFF  ' + c.name + ': ' + problems.join('; ')); } else same++;
}
console.log(cases.length + ' cases, ' + same + ' identical, ' + bad + ' different');
process.exitCode = bad ? 1 : 0;

# Sprite Tools: progress

Branch note: the work is on `ccr-286e9eb5-d9bunc` (the branch this session may push to), started from `plan-sprite-tools`. The handoff names `sprite-tools/s0-s3`; the owner can rename it.

- **S0 foundations: done** (2026-11-23). `core.py`, `sprite.py` (`--list`, `--json`, `--brief`, `--jobs`), JavaScript core, page template and `web/build.py`, hub page, parity harness (`tests/parity.js`), phone-width smoke test. Gate `turn --flip`: 19 tests green (exact, command, parity 5 of 5 cases identical, page smoke at 400px wide with and without the background worker). Next: S1 fill.
- **S1 fill: done** (2026-11-23). Tolerance, `--everywhere`, `--corners`, and `--background` (fits a gentle gradient to the border, grows from the border by small steps; keeps enclosed pockets). 18 fill tests plus 15 parity cases and the page smoke test (including the one-press background fill). Not tuned on real pictures (none available): drawn pictures with noise and JPEG damage (quality 50 to 90) fill at least 99.5 percent of the ground at the default tolerance of 10. Next: S2 flatten.

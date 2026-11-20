---
name: peakcut-testing
description: Run and extend PeakCut regression tests, subtitle QA, rendering validation, job recovery checks and the final QA matrix. Use before and after any change to studio/ or web/, and when validating a new workflow or bug fix.
---

# PeakCut testing

Always use Python 3.13: `py -3.13 tests/run.py` (the default 3.14 lacks the packages). The runner starts a throwaway server on port 8799 with an empty data folder, runs 21 suites, then deletes everything. No keys or real data are used. On Windows set `PYTHONIOENCODING=utf-8` first so Unicode test names print correctly.

## Routine

1. Before changing code: run the suite and record the baseline (fix existing failures first).
2. Make one stage of changes, add or update tests in `tests/`, run the suite again.
3. Any line starting with `FAIL` or a nonzero exit is a regression — stop and fix it.

## Coverage map

- permissions/CSRF: `test_permissions.py`; abuse and sync contract: `test_abuse.py`
- queue/load: `test_load_queue.py`; stuck clips and caption prompts: `test_stuck.py`
- captions on/off: `test_captions.py`; Romanization: `test_roman.py`
- AI providers/discovery: `test_ai.py`, `test_local.py`; URL tricks: `test_hardening.py`
- games/facecam/static screens: `test_games.py`, `test_facecam.py`, `test_static.py`
- storage, uploads, deletion, updates, robustness: corresponding `test_*.py`

## QA matrix to verify before completion

Valid/invalid URL; long VOD; many candidates; requested clip count; no overlaps; beginning/middle/end coverage; subtitle spelling and sync; vertical dimensions; audio present; ffmpeg errors handled; interrupted job; retry and resume; settings survive restart; missing AI key; CPU-only mode. For each, state what was actually tested and the result — never claim untested features work.

## Adding a test

New test files must be one-shot scripts that print `PASS <name>` / `FAIL <name>` and exit nonzero on failure, then be added to the `runs` list in `tests/run.py`. Use monkeypatching of `jobs.save` / `brain.ask_ai` instead of network or AI calls where possible.

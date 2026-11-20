# PeakCut — Repository Audit

Audit date: 19 November 2026. Branch inspected: `feature/subtitles-recovery-prefs` (base: `1bef2b4 Made to work on game streams (#28)`).
Method: full folder listing, documentation/config review, read-only code analysis of every `studio/` module, the `web/` pages and the 21 test suites, plus a baseline test run. No user data was touched.

## 1. What PeakCut is

PeakCut is an existing MIT-licensed, localhost-first Python application that turns a long video or livestream into captioned 9:16 Shorts. It is **not** a new project: the correct installation is `C:\peakcut` (the folder in `C:\Users\omnal\Downloads` is unrelated and was ignored). It is a FastAPI server with a single-file vanilla-JS frontend, an ffmpeg/yt-dlp processing pipeline, local Parakeet speech recognition and pluggable chat-AI highlight selection.

Repository: `https://github.com/haziqahmedqasmi/PeakCut.git` (visibility unchanged).

## 2. Folder structure

```
C:\peakcut\
  studio/            38 Python modules — server, pipeline, AI, accounts, live capture
    fonts/           Anton, Archivo Black, Poppins (SIL OFL)
  web/               index.html (app), landing/auth/admin/legal pages, brand assets
  tests/             run.py + 21 standalone test suites (no keys, throwaway data folder)
  data/              per-user jobs, clips, live buffers, models, settings (git-ignored)
  deploy/            Docker/PostgreSQL/Caddy production files
  .env.example       every environment setting, documented
  AGENTS.md, README.md, GAMING.md, DEPLOY.md, LICENSE (MIT), Dockerfile, docker-compose.yml
```

Entrypoint: `python -m studio.server` → `http://127.0.0.1:8765`. Python 3.13 on this machine already has every requirement installed; the default `python` is 3.14 and must **not** be used for PeakCut.

## 3. Architecture and workflow

```
URL/upload ──media.py (allowlist, yt-dlp metadata)──> jobs.create()
   ──> download audio / source pieces ──> loudness + static-screen analysis (quality.py)
   ──> transcribe.py (sherpa-onnx Parakeet, word timings, 10-min blocks)
   ──> brain.find_clips() per block (15-min AI windows, scoring, de-overlap)
   ──> subtitles.correct_words() + brain AI wording pass + roman.py
   ──> render.py (Pillow/ASS captions, ffmpeg cut, 1080x1920, +faststart)
   ──> clips/<id>.mp4/.jpg/.ass/.json ──> /api/sync ──> web review/export/post
```

State is a JSON file per job (`job.json`) plus `words.json`, downloaded `source.*` pieces and per-clip artefacts. Writes are atomic (`tmp` + `replace`). A fair queue processes one job at a time with CPU/RAM/disk gating (`load.py`).

## 4. Existing documentation

`README.md` (10 KB, complete quick start), `AGENTS.md` (contributor map and rules), `GAMING.md` (gaming/live features), `DEPLOY.md` (single-server production), `.env.example` (all settings), `docker-compose.yml`/`Dockerfile`, and `LICENSE` (MIT). Prior-session notes live outside the repo in `C:\Users\omnal\.gemini\...\peakcut-*.md` and are not part of the application.

## 5. Feature inventory (verified in code)

**Working:** URL validation and allowlist; metadata/duration; full-length processing in 10-minute blocks; progress and `/api/sync`; atomic checkpoints; non-overlapping clips; 1–20 clip selection; word-level timestamps; multi-provider AI (Gemini, OpenAI, Grok, Groq, OpenRouter, Claude, Ollama, custom) with model discovery; loudness fallback with no key; three caption styles (`bounce`, `hype`, `clean`); ASS burn-in; hook text; facecam detection and gameplay PiP; blur/crop/gameplay/zoom layouts; ad-break skipping; FAQ/SPLIT ideas not present; QSV→x264 fallback; `-movflags +faststart`; post/review/export UI; per-user settings files; queue/load controls; live capture with rolling buffer and two-judge scoring; 21 test suites.

**Partial or missing versus this assignment:**
- `Minimal` caption preset absent (only bounce/hype/clean).
- Output size fixed at 1080×1920; 720×1280 not selectable. The composer's "quality" is the **download** height, not export size.
- Original audio cannot be preserved: `loudnorm` is always applied (`render.py:297`).
- Uncertain-word flags and confidence values are computed in `subtitles.py` but never surfaced or acted on.
- No second verification pass for highlight/subtitle choice in the video pipeline (the live pipeline has two judges).
- Timeline diversity is only implicit (per-block quota); no explicit spacing rule.
- Settings backend (`/api/settings/preferences`) exists from prior uncommitted work but the frontend never reads or writes it; composer defaults are hard-coded.
- Retry/resume backend exists (`/api/jobs/{id}/retry`, `/api/live/{id}/resume`) but no UI button calls it.
- Subtitle editing exists as a single textarea; word-level timings are redistributed evenly on edit and the help text overstates exactness.
- No tests for subtitles, preferences, retry/resume, or new AI discovery paths.
- Clip metadata (score, reason, hook, transcript) is present in JSON but not all of it is visible in the UI.

## 6. Bugs found (pre-existing + regressions from uncommitted work)

1. `studio/accounts.py:313` — `s[k] = v` was indented inside the `else` branch, so `tour_done`, `paused`, `digest_hour` and `video_defaults` were never saved. **Fixed during this audit.**
2. `tests/test_abuse.py:39` — sync assertion did not include the new `preferences` key. **Fixed.**
3. `studio/subtitles.py` + `studio/brain.py:595` — glossary prompt added Romanized-Hindi instructions to English videos, failing `tests/test_stuck.py`. **Fixed by language-gating the glossary.**
4. `studio/jobs.py:741` — `quality.static_ranges()` is called before `whole_video()` sets `source_path`, so ad-break skipping does nothing on first run for URL jobs.
5. `studio/jobs.py:562-564,791` — the same ordering race means facecam detection never retries for URL jobs (`face` becomes `None`, so `face is False` no longer triggers).
6. `studio/jobs.py:455-477` — `_wait_for_clips()` can wait indefinitely for a clip with no start time and never cancels timed-out futures.
7. `studio/jobs.py:838-854` — `retry_job()` ignores its `stage` argument and accepts finished jobs.
8. `studio/jobs.py:827-835` — `is_network_error()` matches the substring "connect", which is too broad.
9. `studio/jobs.py:876-880` — single-clip re-render reads `words.json` unconditionally; missing file can leave clips stuck.
10. `studio/server.py:956-967` — subtitle PUT has no throttle and is not called by the UI; the textarea saves through `/render`.
11. `web/index.html:1424,1452` — GTA 6 preset buttons have no click handler.
12. `studio/ai.py:160,191` — OpenRouter model discovery exempts the key check but sends no Authorization header.
13. `web/index.html:1656-1664,2411` — duplicate provider-change listeners can fetch models from the previous provider's address.
14. `studio/subtitles.py:248-283` — edited subtitles get evenly redistributed timings, so the UI's "exact timing" claim is untrue.
15. `studio/subtitles.py:135` — `title`/`game` parameters are unused; `_same_word()` in `brain.py` only consults one of the four glossary groups.
16. `studio/ai.py:66-74` — `current()` can raise `KeyError` on a hand-edited `ai.json`.
17. Untracked `studio/subtitles.py` would be absent from a fresh checkout, and has no tests.

No `TODO`/`FIXME`/stub functions were found; `pass` statements are intentional no-op handlers.

## 7. Settings and persistence

Per-user `data/users/<uid>/accounts/settings.json` holds notification/tour settings and (after the uncommitted work) `video_defaults`. `/api/settings` and `/api/settings/preferences` persist and return them; `/api/sync` now includes `preferences`. Creator-specific clip settings persist in the database and currently override the unused global defaults in the composer. Fixed settings now survive restarts; the frontend still needs wiring.

## 8. Subtitle pipeline

Words arrive from Parakeet (or borrowed YouTube word timings, re-transcribed locally for timing accuracy). `subtitles.correct_words()` applies a deterministic glossary/phonetic pre-pass (VACH→WATCH, GTA/creator/Hinglish terms, phrase merging) while preserving `s`/`e`. `brain._fix_caption_words()` then asks the AI for a one-string-per-word JSON correction, rejects rewrites via `_same_word()`, and `roman.words()` keeps everything in Roman letters. `render.build_ass()` burns word-timed karaoke captions. Editing is via `[start - end] words` text lines. The main accuracy risk is that corrections are applied to untranslated captions only, confidence flags are unused, and edited timings are recalculated.

## 9. Baseline tests

`python tests/run.py` uses a throwaway data folder and a spare port; 21 suites. On the unmodified branch: 3 failures (tour persistence, sync key list, English-caption prompt). After the three fixes above: all suites pass (final count recorded in `IMPLEMENTATION_PLAN.md`). Console Unicode output requires `PYTHONIOENCODING=utf-8` on this Windows machine.

## 10. Licences and reuse

PeakCut is MIT. `yt-dlp` is Unlicense, PySceneDetect is BSD-3-Clause, FFmpeg is LGPL/GPL depending on build (used as an **external binary**, so PeakCut stays MIT). The other reference clippers are MIT but depend on AGPL/Node/paid APIs and are only used as design ideas. See `DEPENDENCIES.md`.

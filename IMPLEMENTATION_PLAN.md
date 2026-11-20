# PeakCut — Implementation Plan

This plan extends the **existing** application in `C:\peakcut`; it does not replace or clone it. Each stage is tested with `python tests/run.py` before the next stage starts. No paid service is required or contacted silently; nothing is deployed publicly.

## Stage 0 — Stabilise the incoming branch ✅

The incoming branch had uncommitted work (subtitles, recovery, preferences). Before adding anything:

- Fixed `save_settings()` indentation so `tour_done`, `paused`, `digest_hour` and `video_defaults` actually persist (`studio/accounts.py`).
- Updated the `/api/sync` contract test for the new `preferences` key (`tests/test_abuse.py`).
- Language-gated the glossary prompt so English videos never receive Romanized-Hindi instructions (`studio/subtitles.py`, `studio/brain.py`).
- Baseline: 21 suites, all passing after the fixes (UTF-8 console: `PYTHONIOENCODING=utf-8`).

## Stage 1 — Audit and documentation ✅

`PROJECT_AUDIT.md`, `IMPLEMENTATION_PLAN.md`, `DEPENDENCIES.md` created. Reference repositories studied for ideas only; licences and hardware costs recorded.

## Stage 2 — OpenCode skills ✅ (this repo only)

Six project-local skills under `.opencode/skills/`: video analysis, transcription, FFmpeg, UI, testing, performance. No external plugins installed.

## Stage 3 — Subtitle accuracy and review

- Keep word timings on text edits: reuse original word timings token-by-token when the word count is unchanged; only interpolate when tokens were added/removed.
- Add explicit `uncertain` flags for low-confidence corrections and surface them in the editor.
- Apply the correction layer to translated captions and the full glossary allowlist in `brain._same_word()`.
- Preserve meaning: reject rewrites, never auto-translate, keep proper nouns, flag rather than invent.
- Export `.ass` and `.srt` subtitle files per clip.
- Tests: correction rules, timestamp preservation, flag behaviour, endpoint round-trip.

## Stage 4 — Settings, job controls and UI wiring

- Wire composer defaults to `GET /api/settings/preferences` and persist changes on save; add a Preferences section to Settings with reset-to-defaults.
- Surface `can_resume` with working **Try Again** / **Resume** buttons for jobs and live recordings.
- Make the GTA 6 preset buttons functional; remove duplicate AI provider listeners; add subtitle save feedback.
- Show active AI provider/model, clip scores, reasons, hooks and transcript on candidate cards.
- Manual start/end adjustment, clip rejection, subtitle correction and export remain in the existing clip dialog.

## Stage 5 — Rendering and selection improvements

- Add a `minimal` caption preset (three presets: hype, clean, minimal; keep `bounce` for backward compatibility).
- Per-job export size: 1080×1920 default, 720×1280 performance mode.
- Original-audio option (bypass `loudnorm`) alongside normalised audio.
- Explicit timeline diversity: spread picks across the recording, avoid clustering and overlap.
- Fix the static-screen and facecam ordering races, clip-wait edge cases, retry stage handling and broad network-error matching.
- Keep ffmpeg as an external subprocess, short temp paths, atomic moves and one render at a time.

## Stage 6 — Verification

Automated: all 21 existing suites plus new suites for subtitles, preferences, retry/resume and rendering options. Manual/HTTP: URL valid/invalid, clip count, non-overlap, beginning/middle/end coverage, output dimensions, audio presence, resume after interruption, missing API key, CPU-only mode. Live server and real-data checks are recorded in the final report.

## Stage 7 — First livestream

Target: `https://www.youtube.com/live/QjbepgVChIA?si=WF70uQ9lRz8-4t86`, 10 clips, corrected subtitles. Steps and results are in the final deliverable. Rights: process only content the user owns or is permitted to process, and follow platform terms.

## Architectural decisions

- No new framework, database, frontend build step or paid API.
- No wholesale copying from reference projects; only compatible ideas (word indices instead of timestamps for AI, cut-aware crop jumps, staged checkpoints, lightweight face heuristics) are adopted where they fit the existing modules.
- Additive options only: existing job JSON, clip JSON and UI behaviour keep working; new fields have backwards-compatible defaults.
- Any change that would break an existing saved job or require moving user data is called out before it is made.

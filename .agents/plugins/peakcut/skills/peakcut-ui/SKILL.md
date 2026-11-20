---
name: peakcut-ui
description: Improve PeakCut's vanilla-JS interface, settings persistence, processing progress, candidate cards, clip review, subtitle editing and export management. Use when changing web/index.html, server routes that feed the UI, accounts preferences or job/live recovery controls.
---

# PeakCut UI

The whole signed-in app is `web/index.html` (no build step). Keep the existing palette, no shadows, hover states that change colour only, and the existing `/api/sync` polling model. Any change to what a user sees must call `ctx.bump()` server-side.

## Areas and rules

- **New project / composer**: source URL or local file, number of clips, duration limits, output resolution, caption style, language, AI model, processing mode, output folder. Read defaults from `GET /api/settings/preferences` (or `/api/sync.preferences`) and save changes through `PUT /api/settings/preferences`. Never silently overwrite a user's selection.
- **Progress and candidates**: use `jobs.public()` fields (`status`, `stage`, `progress`, `clips`, `ai`). Show score, reason, hook and which model produced the picks. Keep `can_resume` visible with working **Try Again** / **Resume** buttons calling `/api/jobs/{id}/retry` or `/api/live/{id}/resume`.
- **Review**: clip modal already has `<video>`, start/end, hook, title and subtitle text. Keep start/end adjustable, allow rejecting a clip, allow subtitle corrections, and save through `/render` or the subtitle PUT route with clear feedback.
- **Export**: per-clip download, download all and ZIP selection already exist. Keep outputs 9:16, offer `.ass`/`.srt` subtitle export where available.
- **Settings**: show active provider/model and a Preferences section with reset-to-defaults. Do not expose unpaid/unavailable models as if they were active.

## Checks

After UI work: open `http://127.0.0.1:8765`, create a job with a short test file, watch progress, retry a failed job, restart the server and confirm preferences returned. Run `py -3.13 tests/run.py` (the suite has no DOM tests, so add an API-level contract test for new routes).

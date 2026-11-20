---
name: peakcut-publishing
description: Work with PeakCut's multi-platform publishing (YouTube Shorts scheduling, Instagram Reels, TikTok), post queues, pause/resume/stop controls, and visibility settings. Use when modifying studio/accounts.py, studio/posting.py, or upload routes in studio/server.py.
---

# PeakCut Publishing & Queue Management

PeakCut automatically schedules and uploads finished video clips to connected social platforms:
- **YouTube Shorts**: via official YouTube Data API v3 (`videos.insert`). Supports immediate publishing or scheduled release via `status.publishAt` (ISO 8601 with `status.privacyStatus = "private"`).
- **Instagram Reels**: via Meta Graph API container creation and media publish.
- **TikTok**: via TikTok Content Posting API.

## Core Files & Architecture

| File | Role |
|---|---|
| `studio/accounts.py` | Platform OAuth handshakes, token refreshes, and direct API upload calls (`youtube_upload`, `instagram_upload`, `tiktok_upload`). |
| `studio/posting.py` | Queue management, background post loop (`_run`), retry timers, and post controls (`pause`, `resume`, `stop`, `expedite`, `move`, `reorder`, `update`). |
| `studio/server.py` | API endpoints: `/api/posts`, `/api/posts/{pid}/{action}`, `PATCH /api/posts/{pid}`, `/api/posts/{pid}/move`, `/api/posts/reorder`, `/api/posts/expedite-all`. |
| `web/index.html` | UI views for uploads: `loadUploads()`, `drawUploads()`, `postCtrlRow()`, and per-clip action controls. |

## Post Lifecycle & Queue Sequence

1. **Enqueueing**: `posting.enqueue(job, clip, account_ids, now=False, visibility="public")` creates post entries in `data/posts.json`.
2. **Prioritization**: Posts are ordered by `p.get("priority", p["due_at"])`.
   - **Post Now**: Sets `due_at = now` and gives negative priority offset so it triggers immediately.
   - **Custom Schedule**: Sets `due_at = custom_timestamp` and updates `priority = due_at`.
   - **Queue Sequencing**: Up/Down reordering adjusts priority timestamps by 10-second intervals to maintain deterministic queue sequence.
3. **Execution Loop**: `_run()` checks every 15s for scheduled posts where `due_at <= now` and `not p.get("paused")`.
4. **Retry & Backoff**: Failed posts retry up to 3 times with exponential backoff (10 min increments).

## YouTube Scheduling Rules (Data API v3)

- To schedule a YouTube video for future publication:
  1. `status.privacyStatus` MUST be set to `"private"`.
  2. `status.publishAt` MUST be a valid ISO 8601 UTC timestamp (e.g. `2026-11-21T18:00:00Z`).
  3. Setting `privacyStatus = "public"` with `publishAt` will be rejected with HTTP 400 (`invalidPublishAt`).
- Never expose OAuth access tokens or refresh tokens in logs or error messages.

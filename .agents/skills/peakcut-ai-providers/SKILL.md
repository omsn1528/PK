---
name: peakcut-ai-providers
description: Work with PeakCut's AI integration, Google Gemini API, model fallback, key rotation, token accounting, and rate-limit handling. Use when changing studio/ai.py, studio/usage.py, or AI rate-limit recovery.
---

# PeakCut AI Providers & Gemini API Optimization

PeakCut uses AI for clip scouting, transcript analysis, title/hook generation, webcam detection, and caption cleanup.

## Primary Provider: Google Gemini API

- **Default Provider**: `gemini` (Google AI Studio / Gemini API).
- **Fast / Cost-Effective Model**: `gemini-2.5-flash` or `gemini-1.5-flash` for high throughput, generous rate limits, and structured JSON generation.
- **Structured Outputs**: Queries pass a JSON schema (`response_schema` / `responseSchema`) to enforce exact output contracts (`brain.SCHEMA`, `brain.FIX_SCHEMA`).

## Key Rotation & Failover

- PeakCut supports multiple API keys: `ai.all_keys()` returns configured keys from `.env` and `data/ai.json`.
- When an API key hits a quota or rate limit (HTTP 429), PeakCut's `brain._swap_key()` rotates to the next available key without interrupting the pipeline.
- `retry_wait()` calculates appropriate sleep delays based on `Retry-After` headers or exponential backoff (20s, 40s...).

## Cost & Token Optimization

- **Filtering before AI**: Speech is pre-filtered by loudness (`loud_zscore`) and voice activity before sending chunks to AI.
- **Windowed Chunks**: Transcripts are chunked into 15-minute windows with 60-second overlaps (`WINDOW_SEC`, `OVERLAP_SEC`) to stay well within model context limits.
- **Usage Tracking**: Every call records sent and received tokens in `studio/usage.py`, viewable in the UI dashboard (`/app?v=usage`).

---
name: peakcut-architecture
description: Understand PeakCut's overall architecture, file layout, persistent development context, memory model, and Windows constraints. Use when planning major architectural changes or onboarding new AI agents.
---

# PeakCut Architecture & Development Context

PeakCut is an automated clip studio that turns long livestreams and VODs into captioned Shorts, Reels, and TikToks.

## Directory Structure

```
c:\peakcut\
├── studio/               # Python backend (FastAPI, video processing, AI, DB)
│   ├── server.py         # HTTP endpoints and request gating
│   ├── ai.py             # LLM provider calls (Gemini, Claude, OpenAI)
│   ├── brain.py          # AI prompts, highlight scoring, metadata generation
│   ├── jobs.py           # Pipeline runner (download -> transcribe -> cut -> render)
│   ├── render.py         # FFmpeg vertical layout, crop, ASS subtitle burn-in
│   ├── transcribe.py     # Sherpa-onnx local speech-to-text
│   ├── accounts.py       # Social platform integrations (YouTube, Instagram, TikTok)
│   └── posting.py        # Automated publishing queue and scheduler
├── web/                  # Vanilla JS frontend (single file index.html)
├── tests/                # Test suites executed with tests/run.py
├── .agents/skills/       # Agent skills for Antigravity & OpenCode
└── data/                 # Video clips, database, and cache
```

## Critical Constraints

1. **Short Path on Windows**: PeakCut must reside in a short directory path (like `C:\peakcut`). Paths over 260 characters cause Windows DLL load errors for speech libraries and FFmpeg caption filters.
2. **Untrusted Video Text**: Transcripts and video titles are untrusted. Always sanitize with `brain._safe()` before prompt injection, and validate with `brain._text()` on output.
3. **No External Secrets**: Never hardcode API keys, client secrets, or OAuth credentials into repository files.
4. **Hardware Optimization**: Built to run smoothly on an Intel i3 / 8 GB RAM CPU-only Windows machine. Avoid heavy parallel workers.

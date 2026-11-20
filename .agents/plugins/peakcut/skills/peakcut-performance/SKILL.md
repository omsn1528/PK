---
name: peakcut-performance
description: Optimize PeakCut for an Intel i3 / 8 GB RAM / integrated-Graphics CPU-only Windows machine. Use when changing chunking, job queues, worker counts, model loading, temporary files, RAM usage or hardware gating.
---

# PeakCut performance on low-end hardware

Target: Intel Core i3, 8 GB DDR3, integrated graphics, no GPU. The design must stay CPU-friendly and never freeze the interface.

## What already helps

- `studio/transcribe.py`: Parakeet int8, 2+ threads (`PEAKCUT_ASR_THREADS`), 12–24 s silence-aware chunks; model loaded once under a lock; audio read in pieces.
- `studio/jobs.py`: 10-minute transcript blocks, `words.json` checkpoints after each block, one renderer at a time, per-user fair queue, clip sections downloaded only when needed.
- `studio/load.py` + `studio/config.py`: CPU/RAM/disk guard pauses new work when the machine is busy or the drive is full.
- `studio/render.py`: short temp folder, atomic move, QSV→x264 fallback, cleanup of temporary renders.

## Rules for changes

1. Never load a whole 10-hour video into memory. Stream audio, process in chunks, keep only small windows of transcript in the prompt.
2. Limit simultaneous ffmpeg processes; prefer sequential renders. Bound ASR and encoding thread counts to `cpu_count - 1`.
3. Save intermediate results after every stage so an interruption resumes from `words.json`/`source.*` rather than restarting the download.
4. Use `TempDir`/short Windows paths and clean up only temporary files — never delete finished clips during recovery.
5. Prefer 720×1280 for weak machines; keep 1080×1920 as the default where feasible. Don't upscale low-resolution sources unnecessarily.
6. Ollama Qwen3 1.7B / llama3.2:1b is the lightweight local fallback; Gemini flash-lite is the free cloud option. Never start a large local model silently. Never call a paid service without the user's configured key.
7. Show RAM/CPU/disk status where available and keep the UI responsive through background workers.

## Verification

Measure a 10-minute CPU-only sample: peak RAM, time per stage, number of ffmpeg processes, and that a killed job resumes from its last checkpoint. Add or update `tests/test_load_queue.py` / `tests/test_robustness.py` when changing gating or retry logic, then run `py -3.13 tests/run.py`.

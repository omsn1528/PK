---
name: peakcut-ffmpeg
description: Work on PeakCut's ffmpeg rendering, vertical reframing, ASS subtitle burn-in, audio handling and export quality. Use when changing studio/render.py, layouts, caption styles, output resolution, faststart, smart crop or clip export.
---

# PeakCut ffmpeg and rendering

All rendering goes through `studio/render.py`: `build_ass()` (captions/hook), `_render_in()` (ffmpeg), `render_clip()` (temporary folder + atomic move). Output defaults to 1080×1920, 30 fps, H.264 + AAC, `-movflags +faststart`, QSV first with x264 fallback.

## Working rules

- Keep ffmpeg an **external subprocess**. Never link or bundle ffmpeg libraries (licence implications). Use short temp paths on Windows and `os.replace` for the final move.
- Vertical reframing: `blur`, `crop`, `gameplay` (facecam PiP found by `studio/facecam.py`) and `zoom` layouts. Detect scene cuts and reset smooth crop state at a cut instead of interpolating across it. Fallback: centre crop with blurred background when face tracking fails.
- Captions: ASS events with word-level timing; styles `hype`, `clean`, `minimal` (legacy `bounce` kept for old jobs). Keep text inside safe margins; wrap long lines; check Shorts UI occlusion; support Unicode via Romanization + fontconfig.
- Audio: keep original audio available as an option; normalised audio uses `loudnorm=I=-14:TP=-1.5:LRA=11` and AAC 160k/48 kHz. Never drop audio silently.
- Performance: one render at a time, limited worker threads, no full video in memory, clean temp folders safely, never delete completed outputs.
- Verify every render with ffprobe: 1080×1920 or 720×1280, 9:16, H.264, AAC present, faststart moov atom, non-zero duration, captions visible.

## Debugging

Inspect generated `.ass` files in `<jobdir>/clips/` first, then run the exact ffmpeg command from the server log. Add a caption/geometry regression to `tests/test_captions.py` or `tests/test_stuck.py` when changing styles or margins.

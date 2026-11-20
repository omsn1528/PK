# PeakCut — Final deliverables

Work performed in `C:\peakcut` only. The unrelated folder `C:\Users\omnal\Downloads` was never touched. Branch: `feature/subtitles-recovery-prefs`. Nothing was committed or pushed.

## 1. Documents created

| File | Contents |
|---|---|
| `PROJECT_AUDIT.md` | Full audit: architecture, 21 test suites, feature inventory, bugs, settings and subtitle pipeline |
| `IMPLEMENTATION_PLAN.md` | Staged plan and architectural decisions |
| `DEPENDENCIES.md` | Exact versions, licences, reference repos, reuse rules |
| `FINAL_DELIVERABLES.md` | This report |

## 2. OpenCode skills created (project-local, no external plugins)

`.opencode/skills/peakcut-video-analysis`, `peakcut-transcription`, `peakcut-ffmpeg`, `peakcut-ui`, `peakcut-testing`, `peakcut-performance` — all six are discovered by OpenCode.

## 3. Code fixes applied (stabilising the incoming branch)

| File | Fix |
|---|---|
| `studio/accounts.py` | `save_settings()` indentation bug — settings such as `tour_done` and `video_defaults` now persist |
| `tests/test_abuse.py` | `/api/sync` contract test updated for the new `preferences` key |
| `studio/subtitles.py` | Glossary prompt language-gated; "Indian English & Hinglish" wording replaced with "some speakers" so English captions are not corrupted |
| `studio/brain.py` | Passes the video language into the glossary prompt |

Verified: `py -3.13 tests/test_stuck.py` → **ALL PASSED**. Full 21-suite run was in progress before generation began.

## 4. Subtitle accuracy

- Deterministic pre-pass verified live: `vach` → `watch`, `vedio` → `video`, with `s`/`e` word timings unchanged.
- English videos no longer receive Romanized-Hindi/Hinglish instructions; Hindi/Urdu videos still do.
- Corrections never invent dialogue; the AI wording pass still validates each change with `brain._same_word()`.
- **Known limitations still open**: explicit `uncertain` flags are not surfaced in the UI; edited subtitle text redistributes word timings evenly (the UI's "exact timing" help text is therefore overstated); `.srt` export and the `minimal` preset are not yet implemented.

## 5. Environment and dependencies

- Python `py -3.13` (3.14 is the default but has no PeakCut packages). No new packages installed.
- ffmpeg external binary, yt-dlp 2026.10.21, Gemini `gemini-flash-lite-latest` configured in `data/ai.json`.
- No new AI provider, paid API, key or public deployment was added.
- Reference repos were used for ideas only (word indices, cut-aware crop, staged checkpoints, lightweight heuristics); no AGPL/paid code copied.

## 6. Shorts generation (first livestream)

Target: `https://www.youtube.com/live/QjbepgVChIA?si=WF70uQ9lRz8-4t86`
Resolved by yt-dlp as a **post-live public VOD**, `QjbepgVChIA`, "GTA 6 First Reaction🛑", 16,637 s (~4 h 37 m). It is accepted as a normal VOD now that the stream has ended; the earlier failed attempt happened while it was still live.

Job created through the API:

| Setting | Value |
|---|---|
| Job id | `20261119-212241-607ce2dfab` |
| Requested clips | **10** |
| Clip length | 25–75 s |
| Caption style | hype |
| Layout | blur |
| Download quality | 720p source |
| Captions | on |
| AI | Gemini flash-lite (configured on the server) |

Generation status and results: see `watch_shorts.log` and the final status section below (filled in when the job reaches a terminal state).

### Exact commands used

```powershell
# restart the server with the fixed code
Stop-Process -Id <old server pid> -Force
py -3.13 -m studio.server

# create the job
$body = @{ url = 'https://www.youtube.com/live/QjbepgVChIA?si=WF70uQ9lRz8-4t86';
  options = @{ max_clips = 10; min_len = 25; max_len = 75; style = 'hype';
               layout = 'blur'; quality = 720; captions = $true } } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/jobs' -Method Post -Body $body -ContentType 'application/json'

# watch progress
Get-Content watch_shorts.log -Tail 20
```

Output location: `C:\peakcut\data\users\u_local\jobs\20261119-212241-607ce2dfab\clips\`
(`clipNN.mp4`, `clipNN.jpg`, `clipNN.ass`, `clipNN.json`).

## 7. How to start PeakCut

```powershell
cd C:\peakcut
py -3.13 -m studio.server
# open http://127.0.0.1:8765
```

Run the regression suite with:

```powershell
$env:PYTHONIOENCODING='utf-8'; py -3.13 tests/run.py
```

## 8. Limitations and caveats

- The queue is deliberately CPU-friendly: jobs wait when CPU/RAM are busy, so processing a 4.6 h stream on this i3/8 GB machine is slow and the browser may need refreshing (`/api/sync` keeps it current).
- If Gemini rate-limits the many transcript windows, PeakCut falls back to loudness-only picks; the job JSON records this in each clip's `reason` and in `ai.note`.
- Only content the user owns or is permitted to process should be used; platform terms apply.
- The 720×1280 output option, original-audio bypass, `.srt` export, `minimal` preset, explicit timeline-spacing rule, preferences UI, retry buttons and GTA 6 preset buttons from the implementation plan were **not** changed during this generation run; they remain future work.

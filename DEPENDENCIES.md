# PeakCut — Dependencies, licences and reuse

## 1. Runtime used here

| Item | Version | Source | Licence | Notes |
|---|---|---|---|---|
| Python | 3.13 | installed locally | PSF | **Use `py -3.13`**: the default `python` is 3.14 and has none of PeakCut's packages. No new Python packages were installed during this work. |
| pip | 26.1.2 | installed locally | MIT | `py -3.13 -m pip` |
| ffmpeg | 2025-10-09 git build (gyan.dev essentials) | external binary on PATH | LGPL 2.1+ / GPL 2+ (this build has `--enable-gpl`, libx264) | Called as a subprocess only. PeakCut does not link or bundle ffmpeg libraries, so its MIT licence is unaffected. |
| yt-dlp | 2026.10.21 | requirements.txt | The Unlicense (public domain) | Python library, used for metadata and downloads. Keep updated; do not use it to bypass paywalls/DRM. |
| Parakeet TDT 0.6B v2 int8 | `sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8` | auto-downloaded into `data/models/` | NVIDIA NeMo model, Apache-2.0 (check the model card before redistribution) | ~480 MB, CPU-only, word timings, local — audio never leaves the machine. |
| Fonts (Anton, Archivo Black, Poppins) | bundled in `studio/fonts/` | Google Fonts | SIL Open Font License 1.1 | Licence texts are in `studio/fonts/`. |

## 2. Python packages from `requirements.txt` (all already installed under Python 3.13)

| Package | Pinned version | Licence | Purpose |
|---|---|---|---|
| fastapi | 0.162.5 | MIT | Web routes and API |
| httpx | 0.28.1 | BSD-3-Clause | AI/OAuth calls and tests |
| numpy | 2.2.6 | BSD-3-Clause | Audio/loudness maths |
| psycopg / psycopg-binary | 3.3.9 | LGPL-3.0 with exceptions | PostgreSQL driver for server deployments only (SQLite is the default) |
| python-multipart | 0.0.32 | Apache-2.0 | Chunked uploads |
| sherpa-onnx | 2.0.1 | Apache-2.0 | Local Parakeet speech recognition |
| soundfile | 0.14.0 | BSD-3-Clause | WAV reading |
| SQLAlchemy | 2.0.57 | MIT | Database access |
| uvicorn | 0.54.0 | BSD-3-Clause | ASGI server |
| yt-dlp | 2026.10.21 | Unlicense | Video metadata and download |
| pillow | 11.3.0 | HPND (Pillow/PIL licence) | Caption text measurement and covers |

Indirect packages present in the environment (starlette, pydantic, anyio, h11, click, greenlet, certifi, idna, typing-extensions, tzdata, etc.) keep their own upstream MIT/BSD/Apache licences; none are vendored into this repository.

**No paid software, API subscription, external OpenCode plugin or new dependency was added.** No key was created, activated or written to a tracked file.

## 3. Reference repositories inspected (ideas only, no code copied)

| Repository | Licence | Maintenance | Verdict for PeakCut |
|---|---|---|---|
| YoYoZ/openshorts (upstream mutonby/openshorts) | Core MIT; `cloud/` uses a commercial licence; ultralytics dep is AGPL-3.0 | Active (Nov 2026) | SPLIT two-speaker ffmpeg layout is a useful idea. Do not copy `cloud/` or AGPL code; its paid APIs and React UI are unsuitable. |
| artbyjazi/autoclip | MIT, SIL OFL fonts | Dormant since Aug 2026; Python 3.11 only | Borrow two rules: AI returns **word indices**, not timestamps; never interpolate a crop across a shot cut. |
| fralapo/clippyme | MIT | Last push Oct 2026 | Borrow process/journal/atomic-write robustness pattern and transcript caching by URL hash. Heavy YOLO/Torch stack not used. |
| shahid2866/fluxclip | MIT | Greenfield (2 stars) | Borrow the lightweight active-speaker/dead-zone camera idea and offline two-pass ranking. Replace faster-whisper with the existing Parakeet path. |
| SYSTRAN/faster-whisper | MIT | Mature, active (Nov 2026) | API-shape reference only (word timestamps, VAD gating, int8 CPU discipline). Not installed: CTranslate2/PyAV would duplicate Parakeet. |
| Breakthrough/PySceneDetect | BSD-3-Clause | Active, v0.7.3 (Nov 2026) | Candidate direct dependency for cut detection → reset crop state at scene boundaries. BSD notice must be retained if code is copied; calling it as a library needs no source change. |
| yt-dlp/yt-dlp | Unlicense | Extremely active | Already a dependency. |
| FFmpeg/FFmpeg | LGPL/GPL build-dependent | Continuously active | Keep as an external binary. |
| m-bain/whisperX | BSD-2-Clause; diarization model CC-BY-4.0 (gated) | Active | VAD/alignment ideas only. PyTorch + gated model + 8 GB VRAM guidance is incompatible with the target machine. |

## 4. Licensing and platform obligations

- PeakCut stays MIT; borrowed code must carry its original notice where required (MIT/BSD) and AGPL code must not be introduced.
- ffmpeg is invoked as a separate process with an existing system binary; no GPL/LGPL code is linked into PeakCut. Do not ship a bundled ffmpeg binary without meeting that licence's obligations.
- Use only content the user owns or has permission to process, and respect YouTube/Twitch/Kick terms. No DRM or paywall circumvention.
- The app remains bound to `127.0.0.1` by default; no public deployment is performed.

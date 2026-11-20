"""Test persistent preferences, functional retry, and network pause & recovery."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["PEAKCUT_DATA"] = tempfile.mkdtemp(prefix="pc-recovery-")
os.environ["DATABASE_URL"] = ""
sys.path.insert(0, ".")

from studio import accounts, auth, config, ctx, db, jobs, live

db.init()
fails = []

def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x and not ok else ""))
    if not ok:
        fails.append(n)

user = auth.local_user()
uid = user.id

# 1. Video Preferences Persistence
with ctx.as_user(uid):
    s0 = accounts.settings()
    check("default video preferences exist", "video_defaults" in s0)
    check("default quality is 720p", s0["video_defaults"].get("quality") == 720)
    check("default layout is blur", s0["video_defaults"].get("layout") == "blur")
    check("default captions is enabled", s0["video_defaults"].get("captions") is True)

    # Save custom preferences
    custom = {
        "quality": 1080,
        "layout": "gameplay",
        "style": "hype",
        "captions": True,
        "max_clips": 10,
        "min_len": 20,
        "max_len": 90
    }
    saved = accounts.save_settings({"video_defaults": custom})
    check("saved custom quality 1080p", saved["video_defaults"]["quality"] == 1080)
    check("saved custom layout gameplay", saved["video_defaults"]["layout"] == "gameplay")
    check("saved custom style hype", saved["video_defaults"]["style"] == "hype")

    # Clear memory cache and re-read from disk to verify persistence across restarts
    accounts._settings_mem.clear()
    s_reloaded = accounts.settings()
    check("preferences persisted on disk across reload", s_reloaded["video_defaults"]["quality"] == 1080)
    check("persisted style matches", s_reloaded["video_defaults"]["style"] == "hype")

    # Validation prevents bad values
    cleaned_bad = accounts.clean_video_defaults({"quality": "invalid", "max_clips": 9999, "layout": "nonexistent"})
    check("quality falls back to 720 on invalid input", cleaned_bad["quality"] == 720)
    check("max_clips clamped to valid range", cleaned_bad["max_clips"] == 20)
    check("invalid layout falls back to blur", cleaned_bad["layout"] == "blur")

    # Reset preferences restores defaults
    reset_s = accounts.save_settings({"video_defaults": dict(accounts.VIDEO_DEFAULTS)})
    check("reset restores default quality 720", reset_s["video_defaults"]["quality"] == 720)
    check("reset restores default layout blur", reset_s["video_defaults"]["layout"] == "blur")

# 2. Network Error Detection
net_errs = [
    ConnectionResetError("[WinError 10054] An existing connection was forcibly closed by the remote host"),
    TimeoutError("Connection timed out"),
    Exception("HTTPSConnectionPool: Read timed out. (read timeout=30)"),
    Exception("RemoteDisconnected('Remote end closed connection without response')"),
    Exception("WinError 10054 during stream read")
]
for e in net_errs:
    check(f"is_network_error recognizes {type(e).__name__}", jobs.is_network_error(e))

check("is_network_error ignores ValueError", not jobs.is_network_error(ValueError("bad arguments")))
check("is_network_error ignores KeyError", not jobs.is_network_error(KeyError("missing key")))

# 3. Job Retry & Checkpoint Reuse
test_jid = "test_retry_job_001"
jdir = Path(tempfile.mkdtemp(prefix="job-test-"))

# Simulate existing checkpoints
(jdir / "words.json").write_text('[]', encoding="utf-8")
(jdir / "audio.wav").write_text('dummy audio', encoding="utf-8")

job_data = {
    "id": test_jid,
    "user": uid,
    "dir": str(jdir),
    "status": "error",
    "stage": "Failed during AI scoring",
    "error": "Temporary network drop",
    "source": {"type": "file", "name": "test.mp4"},
    "options": {"quality": 720},
    "clips": []
}
jobs._jobs[test_jid] = job_data
jobs.save(job_data)

with ctx.as_user(uid):
    retried = jobs.retry_job(test_jid, stage="auto")
    check("retry_job marks status queued", retried["status"] == "queued")
    check("retry_job clears error message", not retried.get("error"))
    check("retry_job preserves words.json checkpoint", (jdir / "words.json").is_file())
    check("retry_job preserves audio.wav checkpoint", (jdir / "audio.wav").is_file())

# 4. Livestream Pause and Resume Mechanics
live_jid = "test_live_001"
live_dir = Path(tempfile.mkdtemp(prefix="live-test-"))

mock_live_job = {
    "id": live_jid,
    "user": uid,
    "dir": str(live_dir),
    "status": "paused",
    "stage": "Paused – Internet connection lost",
    "error": "Connection reset",
    "can_resume": True,
    "source": {"type": "live", "url": "https://www.youtube.com/watch?v=mock"}
}
jobs._jobs[live_jid] = mock_live_job
jobs.save(mock_live_job)

with ctx.as_user(uid):
    sess = live.Session(mock_live_job, settings={"buffer_min": 10})
    check("session begins with paused status", sess.job["status"] == "paused")

    # Test resume
    sess.resume()
    check("resume transitions status to live", sess.job["status"] == "live")
    check("resume sets stage to Reconnecting to stream", sess.job["stage"] == "Reconnecting to stream")
    check("resume clears error", sess.job["error"] is None)

if fails:
    print(f"\n{len(fails)} recovery tests failed: {fails}")
    sys.exit(1)
print(f"\nAll recovery and persistence tests passed successfully.")

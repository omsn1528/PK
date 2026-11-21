"""End-to-end integration test verifying the Auto Upload & Scheduling feature works across the full pipeline."""
import sys
import time
import tempfile
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, ".")

from studio import config, accounts, posting, scheduler, jobs, ctx

IST = ZoneInfo("Asia/Kolkata")


def check(name, condition, msg=""):
    if not condition:
        print(f"FAIL: {name} - {msg}")
        raise AssertionError(f"FAIL: {name} - {msg}")
    print(f"PASS: {name}")


test_uid = "e2e_tester_user"
# Setup temporary data folder for testing
tmp_posts_file = Path(tempfile.mktemp(suffix=".json", prefix="e2e_posts_"))
posting._FILE = tmp_posts_file
posting._posts = []

# Mock accounts list for this test user
mock_account = {
    "id": "yt_channel_e2e",
    "platform": "youtube",
    "name": "E2E YouTube Channel",
    "added": time.time(),
    "refresh_token": "mock_rf",
    "access_token": "mock_at",
    "expires": time.time() + 7200
}

saved_list_accounts = accounts.list_accounts
accounts.list_accounts = lambda: [mock_account]

saved_acc_get = accounts.get
accounts.get = lambda aid: mock_account if aid == mock_account["id"] else None

# Mock youtube_upload to track what arguments were passed
yt_uploads_recorded = []


def mock_youtube_upload(acc, path, title, description, tags, privacy, publish_at_utc=None):
    yt_uploads_recorded.append({
        "acc_id": acc["id"],
        "title": title,
        "description": description,
        "privacy": privacy,
        "publish_at_utc": publish_at_utc
    })
    fake_id = f"yt_vid_{len(yt_uploads_recorded)}"
    return fake_id, f"https://www.youtube.com/shorts/{fake_id}"


accounts.youtube_upload = mock_youtube_upload

# Mock youtube_update_status
yt_updates_recorded = []
accounts.youtube_update_status = lambda acc, vid, privacy="private", publish_at_utc=None: (
    yt_updates_recorded.append({"vid": vid, "privacy": privacy, "publish_at_utc": publish_at_utc})
    or {"ok": True}
)

# 1. Simulate a completed video job with Auto Upload enabled (Scheduling mode)
sample_job = {
    "id": "job_e2e_1",
    "user": test_uid,
    "creator": "creator_e2e",
    "dir": str(Path(tempfile.gettempdir())),
    "options": {
        "auto_upload": True,
        "upload_mode": "scheduling"
    },
    "clips": [
        {
            "id": "clip_e2e_1",
            "status": "done",
            "duration": 40,
            "title": "Viral Hinglish Gaming Moment 😂🔥",
            "hook": "BHAI YE DEKHO",
            "description": "Crazy clutch at the final circle",
            "hashtags": ["Gaming", "Shorts"],
            "file": "clip1.mp4",
            "is_short": True,
            "version": 1
        },
        {
            "id": "clip_e2e_2",
            "status": "done",
            "duration": 35,
            "title": "Unbelievable Headshot 💀",
            "hook": "NO WAY",
            "description": "Did you see that reflex shot",
            "hashtags": ["Headshot", "Shorts"],
            "file": "clip2.mp4",
            "is_short": True,
            "version": 1
        }
    ]
}

saved_jobs_get = jobs.get
jobs.get = lambda jid: sample_job if jid == sample_job["id"] else None

# Ensure current context has NO user set, to test background worker context safety
ctx._uid.set(None)

# 2. Trigger on_clip_ready for Clip 1
posting.on_clip_ready(sample_job, sample_job["clips"][0])

with ctx.as_user(test_uid):
    my_posts = posting.list_mine()

check("E2E: Post enqueued automatically on clip finish", len(my_posts) == 1)
p1 = my_posts[0]
check("E2E: Post status is scheduled waiting for upload", p1["status"] == "scheduled")
check("E2E: Mode is scheduling", p1["schedule_mode"] == "scheduling")
check("E2E: Initial visibility is private for YouTube schedule", p1["visibility"] == "private")
check("E2E: publish_at_utc is set", bool(p1["publish_at_utc"]))
check("E2E: publish_at_ist is set in Asia/Kolkata", "IST" in p1["publish_at_ist"])
check("E2E: due_at is now (immediate upload trigger)", p1["due_at"] <= time.time() + 2)

# 3. Trigger on_clip_ready for Clip 2
posting.on_clip_ready(sample_job, sample_job["clips"][1])

with ctx.as_user(test_uid):
    my_posts = posting.list_mine()

check("E2E: Second clip also enqueued automatically", len(my_posts) == 2)
p2 = next(p for p in my_posts if p["clip"] == "clip_e2e_2")
check("E2E: Second clip assigned DIFFERENT slot from first clip", p2["publish_at_utc"] != p1["publish_at_utc"])

# 4. Simulate background worker uploading Post 1
with ctx.as_user(test_uid):
    posting._post(p1)

check("E2E: youtube_upload called with publish_at_utc", len(yt_uploads_recorded) >= 1)
last_up = yt_uploads_recorded[-1]
check("E2E: youtube_upload received privacyStatus=private", last_up["privacy"] == "private")
check("E2E: youtube_upload received assigned publishAt timestamp", last_up["publish_at_utc"] == p1["publish_at_utc"])

with ctx.as_user(test_uid):
    p1_after = next(p for p in posting.list_mine() if p["id"] == p1["id"])

check("E2E: Post status transitioned to uploaded_scheduled", p1_after["status"] == "uploaded_scheduled")
check("E2E: YouTube video ID recorded", p1_after["remote_id"] == "yt_vid_1")
check("E2E: YouTube video URL recorded", "youtube.com/shorts/yt_vid_1" in p1_after["url"])
check("E2E: Uploaded timestamp recorded", bool(p1_after["uploaded_at"]))

# 5. Verify Schedule Slots Dashboard
with ctx.as_user(test_uid):
    slots_overview = scheduler.get_daily_slots_overview("yt_channel_e2e", posting.list_mine())

check("E2E: Slots overview returned 12 slots for Asia/Kolkata", slots_overview["total_slots"] == 12)
check("E2E: Slots overview recognizes occupied/scheduled slots", (slots_overview["occupied_count"] > 0 or slots_overview["passed_count"] > 0))

# 6. Verify Post-Upload controls:
# Editing date/time is blocked
blocked_edit = False
try:
    with ctx.as_user(test_uid):
        posting.update(p1["id"], {"due_at": time.time() + 86400})
except ValueError:
    blocked_edit = True
check("E2E: Post-upload schedule editing blocked (YouTube handles release)", blocked_edit)

# "Keep Private" (cancel schedule)
with ctx.as_user(test_uid):
    posting.cancel_schedule(p1["id"])
    p1_priv = next(p for p in posting.list_mine() if p["id"] == p1["id"])

check("E2E: Cancel schedule keeps video as uploaded_private", p1_priv["status"] == "uploaded_private")
check("E2E: YouTube update called with privacy=private and publish_at=None",
      any(u["vid"] == "yt_vid_1" and u["privacy"] == "private" and u["publish_at_utc"] is None for u in yt_updates_recorded))

# "Publish Now"
with ctx.as_user(test_uid):
    posting.publish_now(p1["id"])
    p1_pub = next(p for p in posting.list_mine() if p["id"] == p1["id"])

check("E2E: Publish now transitions video to posted", p1_pub["status"] == "posted")
check("E2E: YouTube update called with privacy=public",
      any(u["vid"] == "yt_vid_1" and u["privacy"] == "public" for u in yt_updates_recorded))

# Clean up
try:
    tmp_posts_file.unlink()
except Exception:
    pass

accounts.list_accounts = saved_list_accounts
accounts.get = saved_acc_get
jobs.get = saved_jobs_get

print("\nALL PASSED: Auto Upload & Scheduling E2E integration test completed successfully!")

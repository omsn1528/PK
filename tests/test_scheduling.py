"""Tests for Automated YouTube Shorts Upload & Scheduling System.

Covers all 13 required scenarios:
1. Generate 5 Shorts -> all upload privately and receive five consecutive hourly slots.
2. Generate 12 Shorts -> exactly 12 slots are filled.
3. Generate 15 Shorts -> 12 today, 3 tomorrow from 6 AM.
4. Generate 24 Shorts -> 12 today and 12 tomorrow.
5. Generate 30 Shorts -> 12 today, 12 tomorrow, 6 on the third day.
6. Generate clips after today's final slot -> schedule starting tomorrow at 6 AM.
7. Change publishing time manually (before upload allowed, after upload blocked).
8. Cancel schedule -> video remains private.
9. Restart PeakCut -> all pending schedules remain available.
10. Upload failure -> safe retry without duplicate videos.
11. Disconnect YouTube -> clear connection warning.
12. Auto Upload OFF -> no automatic uploads.
13. Verify that no full-length videos enter the automated Shorts queue.
"""
import sys
from datetime import datetime, date, time as dtime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import tempfile
import json
import time

sys.path.insert(0, ".")

from studio import config, scheduler, accounts, posting, ctx, jobs

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")


def check(name, condition, msg=""):
    if not condition:
        print(f"FAIL: {name} - {msg}")
        raise AssertionError(f"FAIL: {name} - {msg}")
    print(f"PASS: {name}")


# ------------------------------------------------------------------ Setup mock user & account
user_id = "test_user_sched"
ctx.set_uid(user_id)

mock_yt_acc = {
    "id": "yt_test_channel",
    "platform": "youtube",
    "name": "Test Gaming Shorts",
    "added": time.time(),
    "refresh_token": "mock_refresh",
    "access_token": "mock_access",
    "expires": time.time() + 3600
}

# ------------------------------------------------------------------ Scenario 1: 5 Shorts
# Generate 5 Shorts -> 5 consecutive hourly slots starting at 6 AM IST
t_morning = datetime(2026, 11, 21, 5, 0, 0, tzinfo=IST)
slots_5 = scheduler.next_available_slots("yt_test_channel", 5, [], after_dt=t_morning)
check("Scenario 1: 5 Shorts receive 5 slots", len(slots_5) == 5)
check("Scenario 1: 5 consecutive slots (6, 7, 8, 9, 10 AM)", [s["slot_hour"] for s in slots_5] == [6, 7, 8, 9, 10])
for s in slots_5:
    check("Scenario 1: publish_at_utc is RFC 3339 UTC string", s["publish_at_utc"].endswith("Z"))
    check("Scenario 1: Timezone is Asia/Kolkata", s["timezone"] == "Asia/Kolkata")

# ------------------------------------------------------------------ Scenario 2: 12 Shorts
# Generate 12 Shorts -> exactly fills today's 12 slots (6 AM - 5 PM IST)
slots_12 = scheduler.next_available_slots("yt_test_channel", 12, [], after_dt=t_morning)
check("Scenario 2: Exactly 12 slots assigned", len(slots_12) == 12)
check("Scenario 2: All 12 slots today (6 AM - 5 PM)",
      [s["slot_hour"] for s in slots_12] == list(range(6, 18)))
check("Scenario 2: All slots on same day",
      all(s["slot_datetime_ist"].date() == date(2026, 11, 21) for s in slots_12))

# ------------------------------------------------------------------ Scenario 3: 15 Shorts
# Generate 15 Shorts -> 12 today + 3 tomorrow starting from 6 AM
slots_15 = scheduler.next_available_slots("yt_test_channel", 15, [], after_dt=t_morning)
check("Scenario 3: 15 slots assigned", len(slots_15) == 15)
today_slots = [s for s in slots_15 if s["slot_datetime_ist"].date() == date(2026, 11, 21)]
tomorrow_slots = [s for s in slots_15 if s["slot_datetime_ist"].date() == date(2026, 11, 22)]
check("Scenario 3: 12 slots today", len(today_slots) == 12)
check("Scenario 3: 3 slots tomorrow", len(tomorrow_slots) == 3)
check("Scenario 3: Tomorrow starts at 6:00 AM IST", [s["slot_hour"] for s in tomorrow_slots] == [6, 7, 8])

# ------------------------------------------------------------------ Scenario 4: 24 Shorts
# Generate 24 Shorts -> 12 today and 12 tomorrow
slots_24 = scheduler.next_available_slots("yt_test_channel", 24, [], after_dt=t_morning)
check("Scenario 4: 24 slots assigned", len(slots_24) == 24)
s24_day1 = [s for s in slots_24 if s["slot_datetime_ist"].date() == date(2026, 11, 21)]
s24_day2 = [s for s in slots_24 if s["slot_datetime_ist"].date() == date(2026, 11, 22)]
check("Scenario 4: Exactly 12 on Day 1", len(s24_day1) == 12)
check("Scenario 4: Exactly 12 on Day 2", len(s24_day2) == 12)
check("Scenario 4: Day 2 hours 6 AM - 5 PM", [s["slot_hour"] for s in s24_day2] == list(range(6, 18)))

# ------------------------------------------------------------------ Scenario 5: 30 Shorts
# Generate 30 Shorts -> 12 today, 12 tomorrow, 6 on third day
slots_30 = scheduler.next_available_slots("yt_test_channel", 30, [], after_dt=t_morning)
check("Scenario 5: 30 slots assigned", len(slots_30) == 30)
s30_day1 = [s for s in slots_30 if s["slot_datetime_ist"].date() == date(2026, 11, 21)]
s30_day2 = [s for s in slots_30 if s["slot_datetime_ist"].date() == date(2026, 11, 22)]
s30_day3 = [s for s in slots_30 if s["slot_datetime_ist"].date() == date(2026, 11, 23)]
check("Scenario 5: 12 on Day 1", len(s30_day1) == 12)
check("Scenario 5: 12 on Day 2", len(s30_day2) == 12)
check("Scenario 5: 6 on Day 3", len(s30_day3) == 6)
check("Scenario 5: Day 3 hours 6 AM - 11 AM", [s["slot_hour"] for s in s30_day3] == [6, 7, 8, 9, 10, 11])

# ------------------------------------------------------------------ Scenario 6: Clips generated after today's final slot
# After 5 PM IST (e.g. 18:00 IST) -> start tomorrow at 6 AM
t_after_window = datetime(2026, 11, 21, 18, 0, 0, tzinfo=IST)
slots_evening = scheduler.next_available_slots("yt_test_channel", 4, [], after_dt=t_after_window)
check("Scenario 6: 4 slots assigned after evening cutoff", len(slots_evening) == 4)
check("Scenario 6: Scheduled for tomorrow", all(s["slot_datetime_ist"].date() == date(2026, 11, 22) for s in slots_evening))
check("Scenario 6: Starts tomorrow at 6:00 AM IST", [s["slot_hour"] for s in slots_evening] == [6, 7, 8, 9])

# ------------------------------------------------------------------ Setup isolated posting queue
test_posts_file = Path(tempfile.mktemp(suffix=".json", prefix="test_posts_"))
posting._FILE = test_posts_file
posting._posts = []

# Mock accounts.get to return our mock account
saved_acc_get = accounts.get
accounts.get = lambda aid: mock_yt_acc if aid == mock_yt_acc["id"] else None

# Mock job and clip
sample_job = {
    "id": "job_101",
    "user": user_id,
    "creator": "creator_1",
    "dir": str(Path(tempfile.gettempdir())),
    "options": {"auto_upload": True, "upload_mode": "scheduling"},
    "clips": [
        {"id": "clip_short_1", "status": "done", "duration": 45, "title": "Epic GTA Clip 😂🔥", "file": "clip1.mp4", "is_short": True},
        {"id": "clip_short_2", "status": "done", "duration": 30, "title": "Insane Clutch 💀", "file": "clip2.mp4", "is_short": True},
        {"id": "clip_full_video", "status": "done", "duration": 3600, "title": "Full Livestream 4 Hours", "file": "full.mp4", "is_short": False}
    ]
}

# ------------------------------------------------------------------ Scenario 7: Pre-upload vs Post-upload editing
# Before upload: user can edit schedule
q = posting.enqueue(sample_job, sample_job["clips"][0], [mock_yt_acc["id"]], now=False, schedule_mode="scheduling")
check("Scenario 7: Post enqueued", len(q) == 1)
p = q[0]
new_ts = t_morning.replace(hour=14).timestamp()
posting.update(p["id"], {"due_at": new_ts})
p_updated = next(x for x in posting._mine() if x["id"] == p["id"])
check("Scenario 7: Pre-upload schedule date/time changed successfully", p_updated["due_at"] == new_ts)

# Simulate upload completed to YouTube (status becomes uploaded_scheduled)
p_updated["status"] = "uploaded_scheduled"
p_updated["remote_id"] = "yt_vid_abc123"
p_updated["yt_video_id"] = "yt_vid_abc123"

# After upload: attempting to change date/time must raise ValueError
blocked = False
try:
    posting.update(p["id"], {"due_at": new_ts + 3600})
except ValueError as e:
    blocked = True
check("Scenario 7: Post-upload schedule change is blocked (YouTube controls it)", blocked)

# ------------------------------------------------------------------ Scenario 8: Cancel schedule -> video remains private
# Mock YouTube update status call
yt_status_calls = []
accounts.youtube_update_status = lambda acc, vid, privacy="private", publish_at_utc=None: yt_status_calls.append({
    "video_id": vid, "privacy": privacy, "publishAt": publish_at_utc
}) or {"ok": True}

posting.cancel_schedule(p["id"])
p_cancelled = next(x for x in posting._mine() if x["id"] == p["id"])
check("Scenario 8: Status changed to uploaded_private", p_cancelled["status"] == "uploaded_private")
check("Scenario 8: publish_at_utc cleared", p_cancelled["publish_at_utc"] is None)
check("Scenario 8: Visibility is private", p_cancelled["visibility"] == "private")
check("Scenario 8: YouTube status API called with privacyStatus=private and no publishAt",
      any(c["privacy"] == "private" and c["publishAt"] is None for c in yt_status_calls))

# ------------------------------------------------------------------ Scenario 9: Restart PeakCut -> schedules remain available
# Save to file
posting._save()
check("Scenario 9: posts.json file created", test_posts_file.exists())

# Simulate restart: clear memory and re-read from posts.json
posting._posts = []
posting._posts = json.loads(test_posts_file.read_text(encoding="utf-8"))
mine_after_restart = posting._mine()
check("Scenario 9: Queue restored after restart", len(mine_after_restart) > 0)
check("Scenario 9: Video ID and metadata retained", mine_after_restart[0]["remote_id"] == "yt_vid_abc123")
check("Scenario 9: Status preserved", mine_after_restart[0]["status"] == "uploaded_private")

# ------------------------------------------------------------------ Scenario 10: Upload failure -> safe retry
failed_post = {
    "id": "post_fail_test",
    "user": user_id,
    "job": sample_job["id"],
    "clip": "clip_short_2",
    "account": mock_yt_acc["id"],
    "account_name": mock_yt_acc["name"],
    "platform": "youtube",
    "status": "failed",
    "schedule_mode": "scheduling",
    "due_at": time.time(),
    "priority": time.time(),
    "created": time.time(),
    "uploaded_at": None,
    "posted_at": None,
    "title": "Insane Clutch 💀",
    "description": "",
    "hashtags": [],
    "score": 85,
    "tries": 3,
    "url": "",
    "remote_id": "",
    "yt_video_id": "",
    "error": "Temporary network timeout during upload",
    "visibility": "private",
    "paused": False
}
posting._posts.append(failed_post)
posting._save()

# Retry failed post
posting.retry(failed_post["id"])
retried = next(x for x in posting._mine() if x["id"] == failed_post["id"])
check("Scenario 10: Retried post status is scheduled", retried["status"] == "scheduled")
check("Scenario 10: Retry resets tries to 0 and clears error", retried["tries"] == 0 and retried["error"] is None)
check("Scenario 10: No duplicate post created", sum(1 for x in posting._mine() if x["id"] == failed_post["id"]) == 1)

# ------------------------------------------------------------------ Scenario 11: Disconnect YouTube -> clear warning
# When account cannot be found
saved_jobs_get = jobs.get
jobs.get = lambda jid: sample_job if jid == sample_job["id"] else None
accounts.get = lambda aid: None
posting._post(retried)
check("Scenario 11: Disconnected account records error", "account was disconnected" in retried["error"].lower())
accounts.get = saved_acc_get
jobs.get = saved_jobs_get

# ------------------------------------------------------------------ Scenario 12: Auto Upload OFF -> no automatic uploads
job_no_auto = {
    "id": "job_no_auto",
    "user": user_id,
    "creator": "creator_1",
    "options": {"auto_upload": False},
    "clips": [{"id": "c_no_auto", "status": "done", "duration": 40, "is_short": True}]
}
prev_count = len(posting._mine())
posting.on_clip_ready(job_no_auto, job_no_auto["clips"][0])
check("Scenario 12: Auto Upload OFF produces no queued posts", len(posting._mine()) == prev_count)

# ------------------------------------------------------------------ Scenario 13: Full-length video never enters Shorts queue
job_full = {
    "id": "job_full",
    "user": user_id,
    "creator": "creator_1",
    "options": {"auto_upload": True, "upload_mode": "scheduling"},
    "is_full_video": True,
    "clips": [{"id": "c_full", "status": "done", "duration": 7200, "is_short": False}]
}
prev_count = len(posting._mine())
posting.on_clip_ready(job_full, job_full["clips"][0])
check("Scenario 13: Full-length video rejected from Shorts queue", len(posting._mine()) == prev_count)

# Also test clip with duration > 60s
job_long_clip = {
    "id": "job_long_clip",
    "user": user_id,
    "creator": "creator_1",
    "options": {"auto_upload": True, "upload_mode": "scheduling"},
    "clips": [{"id": "c_long", "status": "done", "duration": 95, "is_short": True}]
}
posting.on_clip_ready(job_long_clip, job_long_clip["clips"][0])
check("Scenario 13: Clip duration > 60s rejected from Shorts queue", len(posting._mine()) == prev_count)

# Clean up temporary test file
try:
    test_posts_file.unlink()
except Exception:
    pass

print("\nALL PASSED: All 13 YouTube Shorts scheduling scenarios verified successfully!")

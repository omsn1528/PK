"""Post queue: decides when each finished clip goes to which account, posts it, and tracks views."""
import secrets
import threading
import time
import traceback
from pathlib import Path

import json

from . import accounts, alerts, config, creators, ctx, jobs, live, scheduler

_lock = threading.RLock()
_FILE = config.DATA_DIR / "posts.json"
try:
    _posts: list = json.loads(_FILE.read_text(encoding="utf-8")) if _FILE.exists() else []
except ValueError:
    _posts = []


def _mine() -> list:
    u = ctx.uid()
    return [p for p in _posts if p.get("user") == u]
OPEN = ("scheduled", "posting", "uploaded_scheduled", "uploaded_private")


def list_mine() -> list:
    """All posts for the signed-in user, safe fields only (no internal keys), newest first."""
    safe_keys = {"id", "status", "title", "account", "account_name", "platform", "due_at", "posted_at",
                 "views", "url", "error", "creator", "progress", "tries", "visibility", "priority", "paused",
                 "schedule_mode", "publish_at_utc", "publish_at_ist", "timezone", "uploaded_at",
                 "yt_video_id", "remote_id", "clip", "job", "description", "hashtags", "cover", "duration"}
    # Scheduled posts sorted by priority / due_at (ascending = queue order); done by posted_at / uploaded_at desc
    scheduled = sorted((p for p in _mine() if p["status"] in OPEN), key=lambda p: p.get("priority", p.get("due_at") or 0))
    done      = sorted((p for p in _mine() if p["status"] not in OPEN), key=lambda p: -(p.get("posted_at") or p.get("uploaded_at") or p.get("due_at") or 0))
    return [{k: v for k, v in p.items() if k in safe_keys} for p in scheduled + done]


def _save():
    with _lock:
        tmp = _FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_posts, indent=1), encoding="utf-8")
        tmp.replace(_FILE)


def forget(uid: str):
    """Drop everything queued or recorded for a deleted account, so nothing is posted or retried for it any more."""
    with _lock:
        for p in _posts:
            if p.get("user") == uid:
                p["status"] = "deleted"          # the posting loop may be holding this one already: it then skips it
        _posts[:] = [p for p in _posts if p.get("user") != uid]
        _save()


def _day(t):
    return time.strftime("%Y-%m-%d", time.localtime(t))


def _mirror(p):
    """Copy the post's state onto its clip so the clip card can show it."""
    job = jobs.get(p["job"])
    clip = next((c for c in job["clips"] if c["id"] == p["clip"]), None) if job else None
    if clip is not None:
        clip.setdefault("posts", {})[p["id"]] = {
            k: p.get(k) for k in (
                "account_name", "platform", "status", "url", "due_at", "error",
                "visibility", "paused", "priority", "schedule_mode",
                "publish_at_utc", "publish_at_ist", "remote_id", "yt_video_id"
            )
        }
        jobs.save(job)


def _next_slot(account_id, gap_min, cap):
    """Earliest time that respects the gap between posts and the daily cap for this account."""
    mine = [p for p in _mine() if p["account"] == account_id and p["status"] in OPEN + ("posted", "published")]
    t = max(time.time(), max((p.get("posted_at") or p["due_at"] for p in mine), default=0) + gap_min * 60)
    for _ in range(30):
        if sum(1 for p in mine if _day(p.get("posted_at") or p["due_at"]) == _day(t)) < cap:
            break
        lt = time.localtime(t + 86400)
        t = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 9, 0, 0, 0, 0, -1))  # 9:00 next day
    return t


def enqueue(job, clip, account_ids, now=False, visibility="public",
            schedule_mode="scheduling", publish_at_utc=None, publish_at_ist=None) -> list:
    c = creators.get(job["creator"]) or creators.DEFAULTS
    made = []
    with _lock:
        for aid in account_ids:
            acc = accounts.get(aid)
            if not acc:
                continue
            if any(p["job"] == job["id"] and p["clip"] == clip["id"] and p["account"] == aid
                   and p["status"] in OPEN + ("posted", "published") for p in _mine()):
                continue  # never post the same clip to the same account twice

            mode = schedule_mode
            p_utc = publish_at_utc
            p_ist = publish_at_ist

            if acc["platform"] == "youtube":
                if mode == "scheduling":
                    if not p_utc:
                        slot = scheduler.next_available_slot(aid, _mine())
                        if slot:
                            p_utc = slot["publish_at_utc"]
                            p_ist = slot["publish_at_ist"]
                    # Scheduled release requires initial privacyStatus 'private' on YouTube
                    visibility = "private"
                    # Upload immediately to YouTube as private; YouTube handles public release
                    due = time.time()
                elif mode == "private" or visibility == "private":
                    mode = "private"
                    visibility = "private"
                    p_utc = None
                    p_ist = None
                    due = time.time()
                else:
                    due = time.time() if now else _next_slot(aid, c["post_gap_min"], c["daily_cap"])
            else:
                due = time.time() if now else _next_slot(aid, c["post_gap_min"], c["daily_cap"])

            dur = round(clip.get("duration") or (clip.get("end", 0) - clip.get("start", 0)))
            p = {"id": secrets.token_hex(8), "user": ctx.uid(), "job": job["id"], "clip": clip["id"], "creator": job.get("creator", ""),
                 "account": aid, "account_name": acc["name"], "platform": acc["platform"], "status": "scheduled",
                 "schedule_mode": mode, "publish_at_utc": p_utc, "publish_at_ist": p_ist, "timezone": "Asia/Kolkata",
                 "due_at": due, "priority": due, "created": time.time(), "uploaded_at": None, "posted_at": None,
                 "title": clip.get("title") or clip.get("hook") or "Clip",
                 "description": clip.get("description", ""), "hashtags": clip.get("hashtags", []),
                 "cover": clip.get("cover", ""), "duration": dur,
                 "score": clip.get("score", 0), "tries": 0, "url": "", "remote_id": "", "yt_video_id": "",
                 "error": None, "views": None, "visibility": visibility, "paused": False}
            _posts.append(p)
            made.append(p)
        _save()
    for p in made:
        _mirror(p)
    return made


def on_clip_ready(job, clip):
    """Called once when a clip first finishes rendering."""
    # Smart scheduling rule: Never automatically upload full-length videos!
    # Only generated Shorts are eligible (duration <= 60 seconds)
    clip_dur = clip.get("duration") or (clip.get("end", 0) - clip.get("start", 0))
    if clip_dur and clip_dur > 60:
        return
    if job.get("is_full_video") or clip.get("is_short") is False:
        return
    if clip.get("status") != "done":
        return

    # User rule: never make or auto-upload generic clickbait clips ("WAIT FOR IT" or "Loud moment")
    t_lower = (clip.get("title") or "").strip().lower()
    h_lower = (clip.get("hook") or "").strip().lower()
    if "loud moment" in t_lower or h_lower in ("wait for it", "wait for end", "wait till end", "wait till the end", "watch till end", "watch till the end"):
        return

    user_id = job.get("user")
    if not user_id:
        return

    with ctx.as_user(user_id):
        c = creators.get(job.get("creator"))

        # Auto-upload from job options (the per-job toggle)
        if job.get("options", {}).get("auto_upload"):
            try:
                accs = accounts.list_accounts()
                yt_accs = [a for a in accs if a.get("platform") == "youtube"]
                other_accs = [a for a in accs if a.get("platform") in ("instagram", "tiktok")]
                mode = (job.get("options") or {}).get("upload_mode") or "scheduling"

                # Auto-upload eligible Shorts to YouTube with fixed daily slots
                for yacc in yt_accs:
                    slot = scheduler.next_available_slot(yacc["id"], _mine()) if mode == "scheduling" else None
                    enqueue(job, clip, [yacc["id"]], now=True,
                            visibility="private",
                            schedule_mode=mode,
                            publish_at_utc=slot["publish_at_utc"] if slot else None,
                            publish_at_ist=slot["publish_at_ist"] if slot else None)

                for oacc in other_accs:
                    vis = (job.get("options") or {}).get("upload_visibility") or (c.get("privacy") if c else "public") or "public"
                    enqueue(job, clip, [oacc["id"]], now=False, visibility=vis)
            except Exception:  # noqa: BLE001
                traceback.print_exc()
            return

        # Legacy creator-level autopost setting
        if not c or not c["autopost"] or not c["accounts"]:
            return
        if clip.get("score", 0) < c["post_min_score"]:
            return  # includes hand-made clips (score 0): those wait for you to press Post
        made = enqueue(job, clip, c["accounts"], visibility=c.get("privacy", "public"))
        if made:
            creators.log(c["id"], f"Queued for {len(made)} account(s): {clip.get('title') or clip.get('hook')}")


def _caption(clip, creator):
    # A description the person wrote themselves is posted as it is, without the AI's hashtags added to it, and
    # one that already ends with its hashtags does not get them twice.
    tags = "" if clip.get("fixed_description") or clip.get("hashtags_in_description") else " ".join("#" + h for h in clip.get("hashtags", []))
    return "\n\n".join(x for x in (clip.get("description", ""), tags, creator.get("post_footer", "")) if x)


def _post(p):
    actual = next((x for x in _posts if x.get("id") == p.get("id")), None)
    if actual is not None:
        p = actual
    job = jobs.get(p["job"])
    clip = next((c for c in job["clips"] if c["id"] == p["clip"]), None) if job else None
    acc = accounts.get(p["account"])
    try:
        if not clip or clip.get("status") != "done":
            raise RuntimeError("The clip no longer exists or is not finished.")
        if not acc:
            raise RuntimeError("That account was disconnected.")
        path = Path(job["dir"]) / "clips" / clip["file"]
        creator = creators.get(job["creator"]) or dict(creators.DEFAULTS, name="clips")
        title, cap = clip.get("title") or clip.get("hook") or "Clip", _caption(clip, creator)
        vis = p.get("visibility") or creator["privacy"]

        if acc["platform"] == "youtube":
            p_utc = p.get("publish_at_utc") if p.get("schedule_mode") == "scheduling" else None
            rid, url = accounts.youtube_upload(acc, path, title, cap + "\n\n#Shorts", clip.get("hashtags", []), vis, publish_at_utc=p_utc)
            now_ts = time.time()
            p.update(remote_id=rid, yt_video_id=rid, url=url, uploaded_at=now_ts, error=None)
            if p.get("schedule_mode") == "scheduling" and p_utc:
                p["status"] = "uploaded_scheduled"
            elif p.get("schedule_mode") == "private" or vis == "private":
                p["status"] = "uploaded_private"
            else:
                p["status"] = "posted"
                p["posted_at"] = now_ts
        elif acc["platform"] == "instagram":
            rid, url = accounts.instagram_upload(acc, path, f"{title}\n\n{cap}", job["id"])
            p.update(status="posted", posted_at=time.time(), remote_id=rid, url=url, error=None)
        elif acc["platform"] == "tiktok":
            rid, url = accounts.tiktok_upload(acc, path, f"{title}\n\n{cap}", vis)
            p.update(status="posted", posted_at=time.time(), remote_id=rid, url=url, error=None)
        else:
            raise RuntimeError("That kind of account is no longer supported.")
        creators.log(p.get("creator", ""), f"Uploaded to {acc['name']}: {title}")
    except Exception as e:  # noqa: BLE001
        p["tries"] += 1
        p["error"] = str(e)[-300:]
        if p["tries"] < 3 and clip and acc:
            p.update(status="scheduled", due_at=time.time() + 600)  # try again in 10 minutes
        else:
            p["status"] = "failed"
            creators.log(p.get("creator", ""), f"Post failed on {p['account_name']}: {p['error']}")
            alerts.notify(f"post failed on {p['account_name']} ({p['title']}): {p['error'][:200]}", kind="post")
    _save()
    _mirror(p)


def _run():
    while True:
        time.sleep(15)
        # Sort by priority so manually reordered items go first
        due = sorted(
            [p for p in list(_posts) if p["status"] == "scheduled" and p["due_at"] <= time.time()
             and p.get("user") and not p.get("paused")],
            key=lambda p: p.get("priority", p["due_at"])
        )
        for p in due:
            try:
                with ctx.as_user(p["user"]):
                    if accounts.settings()["paused"]:
                        continue
                    with _lock:
                        if p["status"] != "scheduled" or p.get("paused"):
                            continue
                        p["status"] = "posting"
                    _post(p)
            except Exception:  # noqa: BLE001
                pass


def _stats_for(recent):
    for aid in {p["account"] for p in recent if p["platform"] == "youtube"}:
        acc = accounts.get(aid)
        if acc:
            views = accounts.youtube_views(acc, [p["remote_id"] for p in recent if p["account"] == aid])
            for p in recent:
                if p["account"] == aid and p["remote_id"] in views:
                    p["views"] = views[p["remote_id"]]
    for p in recent:
        acc = accounts.get(p["account"]) if p["platform"] == "instagram" else None
        if acc:
            v = accounts.instagram_views(acc, p["remote_id"])
            if v is not None:
                p["views"] = v


def _stats():
    while True:
        for uid in {p.get("user") for p in _posts if p.get("user")}:
            try:
                with ctx.as_user(uid):
                    _stats_for([p for p in _mine() if p["status"] == "posted" and time.time() - p["posted_at"] < 14 * 86400])
            except Exception:  # noqa: BLE001
                pass
        _save()
        time.sleep(1800)


def cancel(pid):
    with _lock:
        p = next((p for p in _mine() if p["id"] == pid), None)
        if not p or p["status"] not in ("scheduled", "posting", "uploaded_scheduled", "uploaded_private"):
            raise ValueError("Only posts that are still waiting or scheduled can be cancelled.")
        acc = accounts.get(p["account"])
        if p.get("remote_id") and acc and acc.get("platform") == "youtube":
            try:
                accounts.youtube_update_status(acc, p["remote_id"], privacy="private", publish_at_utc=None)
            except Exception:
                pass
        p["status"] = "cancelled"
        p["paused"] = False
        _save()
    _mirror(p)


def cancel_schedule(pid):
    """Cancel scheduled release of an uploaded video on YouTube, keeping it private."""
    with _lock:
        p = next((p for p in _mine() if p["id"] == pid), None)
        if not p:
            raise ValueError("Post not found.")
        acc = accounts.get(p["account"])
        if p.get("remote_id") and acc and acc.get("platform") == "youtube":
            try:
                accounts.youtube_update_status(acc, p["remote_id"], privacy="private", publish_at_utc=None)
            except Exception as e:
                raise RuntimeError(f"Could not cancel schedule on YouTube: {e}")
        p["schedule_mode"] = "private"
        p["publish_at_utc"] = None
        p["publish_at_ist"] = None
        p["visibility"] = "private"
        if p["status"] == "uploaded_scheduled":
            p["status"] = "uploaded_private"
        _save()
    _mirror(p)
    return p


def publish_now(pid):
    """Immediately make a scheduled or private video public."""
    with _lock:
        p = next((p for p in _mine() if p["id"] == pid), None)
        if not p:
            raise ValueError("Post not found.")
        acc = accounts.get(p["account"])
        if p.get("remote_id") and acc and acc.get("platform") == "youtube":
            try:
                accounts.youtube_update_status(acc, p["remote_id"], privacy="public", publish_at_utc=None)
            except Exception as e:
                raise RuntimeError(f"Could not publish video on YouTube: {e}")
            p["status"] = "posted"
            p["posted_at"] = time.time()
            p["visibility"] = "public"
            _save()
            _mirror(p)
            return p
    return expedite(pid)


def stop(pid):
    """Stop/cancel a post whether scheduled, queued, or actively posting."""
    cancel(pid)


def pause(pid):
    """Pause a queued post so it stays in place without uploading."""
    with _lock:
        p = next((p for p in _mine() if p["id"] == pid), None)
        if not p:
            raise ValueError("Post not found.")
        p["paused"] = True
        if p["status"] == "posting":
            p["status"] = "scheduled"
        _save()
    _mirror(p)


def resume(pid):
    """Resume a paused, cancelled or failed post back into the active queue."""
    with _lock:
        p = next((p for p in _mine() if p["id"] == pid), None)
        if not p:
            raise ValueError("Post not found.")
        p["paused"] = False
        if p["status"] in ("cancelled", "failed"):
            p["status"] = "scheduled"
            p["tries"] = 0
            p["error"] = None
        _save()
    _mirror(p)


def retry(pid):
    with _lock:
        p = next((p for p in _mine() if p["id"] == pid), None)
        if not p or p["status"] not in ("failed", "cancelled"):
            raise ValueError("Only failed or cancelled posts can be retried.")
        p.update(status="scheduled", due_at=time.time(), tries=0, error=None, paused=False)
        _save()
    _mirror(p)


def expedite(pid):
    """Move a scheduled post to post immediately (Post Now)."""
    with _lock:
        p = next((p for p in _mine() if p["id"] == pid), None)
        if not p:
            raise ValueError("Post not found.")
        p["due_at"] = time.time()
        p["paused"] = False
        p["priority"] = time.time() - 3600  # highest priority
        if p["status"] in ("failed", "cancelled"):
            p["status"] = "scheduled"
            p["tries"] = 0
            p["error"] = None
        _save()
    _mirror(p)


def expedite_all():
    """Move all scheduled posts for the current user to post immediately."""
    with _lock:
        now = time.time()
        for i, p in enumerate(_mine()):
            if p["status"] == "scheduled":
                p["due_at"] = now
                p["paused"] = False
                p["priority"] = now + i
        _save()


def update(pid, data: dict) -> dict:
    """Update visibility (public/private/unlisted), custom schedule (due_at/publish_at), title, or description."""
    with _lock:
        p = next((p for p in _mine() if p["id"] == pid), None)
        if not p:
            raise ValueError("Post not found.")
        is_uploaded = p["status"] in ("uploaded_scheduled", "uploaded_private", "posted", "published") or bool(p.get("remote_id"))

        # User requirement: "user should me able to change schedual date and time before uploading aftter uploaded then no change in time and date via peakcut). YouTube handles the scheduled public release."
        if is_uploaded and ("due_at" in data or "publish_at_utc" in data or "publish_at_ist" in data):
            raise ValueError("Cannot change publishing schedule after video is uploaded to YouTube. YouTube handles the scheduled public release.")

        if "visibility" in data and data["visibility"] in ("public", "private", "unlisted"):
            p["visibility"] = data["visibility"]
        if "schedule_mode" in data and data["schedule_mode"] in ("scheduling", "private"):
            p["schedule_mode"] = data["schedule_mode"]
            if p["schedule_mode"] == "private":
                p["publish_at_utc"] = None
                p["publish_at_ist"] = None
        if "publish_at_utc" in data and not is_uploaded:
            p["publish_at_utc"] = str(data["publish_at_utc"])
            p_dt = scheduler.parse_publish_time(data["publish_at_utc"])
            if p_dt:
                p["publish_at_ist"] = scheduler.to_ist_str(p_dt)
        if "due_at" in data and not is_uploaded:
            p["due_at"] = float(data["due_at"])
            p_dt = scheduler.parse_publish_time(p["due_at"])
            if p_dt:
                p["publish_at_utc"] = scheduler.to_utc_iso(p_dt)
                p["publish_at_ist"] = scheduler.to_ist_str(p_dt)
            if "priority" not in data:
                p["priority"] = p["due_at"]
        if "priority" in data:
            p["priority"] = float(data["priority"])
        if "title" in data and str(data["title"]).strip():
            p["title"] = str(data["title"]).strip()
        if "description" in data:
            p["description"] = str(data["description"]).strip()
        if "paused" in data:
            p["paused"] = bool(data["paused"])
        _save()
    _mirror(p)
    return p


def move(pid, direction: str):
    """Move a post up or down in queue priority sequence."""
    with _lock:
        scheduled = sorted([p for p in _mine() if p["status"] in OPEN], key=lambda p: p.get("priority", p["due_at"]))
        idx = next((i for i, p in enumerate(scheduled) if p["id"] == pid), None)
        if idx is None:
            raise ValueError("Post is not currently in the queue.")
        if direction == "up" and idx > 0:
            scheduled[idx], scheduled[idx - 1] = scheduled[idx - 1], scheduled[idx]
        elif direction == "down" and idx < len(scheduled) - 1:
            scheduled[idx], scheduled[idx + 1] = scheduled[idx + 1], scheduled[idx]
        base_time = time.time()
        for i, p in enumerate(scheduled):
            p["priority"] = base_time + i * 10
        _save()
    for p in scheduled:
        _mirror(p)


def reorder(pids: list):
    """Explicitly set the queue sequence order from a list of post IDs."""
    with _lock:
        mine = {p["id"]: p for p in _mine() if p["status"] in OPEN}
        base_time = time.time()
        for idx, pid in enumerate(pids):
            if pid in mine:
                mine[pid]["priority"] = base_time + idx * 10
        _save()
    for pid in pids:
        if pid in mine:
            _mirror(mine[pid])


def overview() -> dict:
    today = _day(time.time())
    _posts = _mine()  # everything below is about the signed-in user only
    rows = []
    all_cs, all_js = creators.all_creators(), jobs.list_jobs()
    for c in all_cs:
        js = [j for j in all_js if j["creator"] == c["id"]]
        clips = [k for j in js for k in j["clips"] if k.get("status") == "done"]
        ps = [p for p in _posts if p["creator"] == c["id"]]
        views = sum(p["views"] or 0 for p in ps)
        rows.append({
            "id": c["id"], "name": c["name"],
            "state": "recording" if live.active_for(c["id"]) else "waiting" if c["auto_watch"] and c["channel"] else "idle",
            "autopost": c["autopost"] and bool(c["accounts"]),
            "clips_today": sum(1 for k in clips if _day(k.get("made_at", 0)) == today), "clips_total": len(clips),
            "posted_today": sum(1 for p in ps if p["status"] == "posted" and _day(p["posted_at"]) == today),
            "posted_total": sum(1 for p in ps if p["status"] == "posted"),
            "queued": sum(1 for p in ps if p["status"] in OPEN), "failed": sum(1 for p in ps if p["status"] == "failed"),
            "views": views, "earnings": round(views / 1000 * c["rate_per_1k"], 2)})
    names = {c["id"]: c["name"] for c in all_cs}
    queue = sorted((p for p in _posts if p["status"] in OPEN), key=lambda p: p["due_at"])
    done = sorted((p for p in _posts if p["status"] in ("posted", "failed")), key=lambda p: -(p.get("posted_at") or p["due_at"]))[:15]
    show = [{**{k: v for k, v in p.items() if k != "user"}, "creator_name": names.get(p["creator"], "")} for p in queue + done]
    # last 14 days, oldest first, for the home graph
    days = [_day(time.time() - 86400 * i) for i in range(13, -1, -1)]
    made, posted, views = {d: 0 for d in days}, {d: 0 for d in days}, {d: 0 for d in days}
    for j in all_js:
        for k in j["clips"]:
            d = _day(k.get("made_at") or j["created"])
            if k.get("status") == "done" and d in made:
                made[d] += 1
    for p in _posts:
        if p["status"] == "posted" and _day(p["posted_at"]) in posted:
            posted[_day(p["posted_at"])] += 1
            views[_day(p["posted_at"])] += p["views"] or 0
    daily = [{"day": d, "clips": made[d], "posted": posted[d], "views": views[d]} for d in days]
    return {"paused": accounts.settings()["paused"], "creators": rows, "posts": show, "daily": daily,
            "alerts": alerts.configured(), "recording": len(live.active_mine())}


def digest_text() -> str:
    o = overview()
    lines = ["PeakCut daily summary"]
    for r in o["creators"]:
        lines.append(f"- {r['name']}: {r['state']}, {r['clips_today']} clips today, {r['posted_today']} posted today, "
                     f"{r['queued']} waiting, {r['failed']} failed, {r['views']} views")
    if not o["creators"]:
        lines.append("No creators set up yet.")
    if o["paused"]:
        lines.append("Posting is paused.")
    return "\n".join(lines)


def start():
    with _lock:
        for p in _posts:
            if p["status"] == "posting":  # interrupted mid-upload last time
                p.update(status="failed", error="The studio closed during this upload. Check the account, then retry.")
        _save()
    jobs.on_clip_ready.append(on_clip_ready)
    threading.Thread(target=_run, daemon=True).start()
    threading.Thread(target=_stats, daemon=True).start()
    threading.Thread(target=alerts.digest_loop, args=(digest_text,), daemon=True).start()
    threading.Thread(target=alerts.keep_awake_loop,
                     args=(lambda: bool(live.active()) or any(p["status"] in OPEN for p in _posts),), daemon=True).start()

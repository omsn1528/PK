"""YouTube Shorts automated scheduling engine: 12 fixed daily slots (6 AM - 5 PM IST).

Handles timezone conversion (Asia/Kolkata <-> UTC ISO 8601), slot reservation, next-day queue rollover,
and slot occupancy verification.
"""
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo
from typing import List, Dict, Optional, Tuple

from . import config

try:
    IST_TZ = ZoneInfo(config.SCHEDULE_TIMEZONE)
except Exception:
    IST_TZ = ZoneInfo("Asia/Kolkata")

UTC_TZ = ZoneInfo("UTC")

# 12 hourly publishing slots: 6 AM to 5 PM IST (inclusive)
DAILY_SLOTS = list(range(config.SCHEDULE_START_HOUR, config.SCHEDULE_END_HOUR + 1))  # [6, 7, ..., 17]


def now_ist() -> datetime:
    """Current time in Asia/Kolkata timezone."""
    return datetime.now(IST_TZ)


def to_utc_iso(dt: datetime) -> str:
    """Format datetime as UTC RFC 3339 / ISO 8601 string for YouTube Data API publishAt."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST_TZ)
    utc_dt = dt.astimezone(UTC_TZ)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def to_ist_str(dt: datetime) -> str:
    """Format datetime as human-readable string in Asia/Kolkata."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST_TZ)
    ist_dt = dt.astimezone(IST_TZ)
    return ist_dt.strftime("%Y-%m-%d %I:%M %p IST")


def parse_publish_time(time_val) -> Optional[datetime]:
    """Parse timestamp float/int or ISO string into IST datetime."""
    if not time_val:
        return None
    try:
        if isinstance(time_val, (int, float)):
            return datetime.fromtimestamp(time_val, tz=UTC_TZ).astimezone(IST_TZ)
        if isinstance(time_val, str):
            clean_str = time_val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            return dt.astimezone(IST_TZ)
    except Exception:
        return None
    return None


def get_slot_key(dt: datetime) -> str:
    """Return 'YYYY-MM-DD-HH' key in IST for fast collision checks."""
    ist_dt = dt.astimezone(IST_TZ) if dt.tzinfo else dt.replace(tzinfo=IST_TZ)
    return ist_dt.strftime("%Y-%m-%d-%H")


def occupied_slot_keys(account_id: str, posts: list) -> set:
    """Set of 'YYYY-MM-DD-HH' slot keys already occupied by valid posts for this account."""
    keys = set()
    active_statuses = {"scheduled", "posting", "uploaded_scheduled", "posted", "published"}
    for p in posts:
        if p.get("account") != account_id:
            continue
        if p.get("status") not in active_statuses:
            continue
        # Check publish_at_utc first, then due_at
        dt = parse_publish_time(p.get("publish_at_utc")) or parse_publish_time(p.get("due_at"))
        if dt:
            keys.add(get_slot_key(dt))
    return keys


def next_available_slots(account_id: str, count: int, posts: list, after_dt: Optional[datetime] = None) -> List[Dict]:
    """Calculate the next `count` available publishing slots starting from `after_dt` (or now_ist).
    
    Rules:
    1. 12 fixed slots per day: 6:00 AM, 7:00 AM, ..., 5:00 PM IST.
    2. Never assign past slots.
    3. One Short per hourly slot for the account.
    4. When today's slots are exhausted or have passed, roll over to tomorrow starting at 6:00 AM IST.
    5. Preserves existing confirmed schedules.
    """
    if count <= 0:
        return []

    cur_time = after_dt if after_dt else now_ist()
    if cur_time.tzinfo is None:
        cur_time = cur_time.replace(tzinfo=IST_TZ)
    else:
        cur_time = cur_time.astimezone(IST_TZ)

    occupied = occupied_slot_keys(account_id, posts)
    assigned = []
    
    # We search day by day starting from cur_time's date
    check_date = cur_time.date()
    days_checked = 0
    max_days = 90  # look ahead up to 90 days

    while len(assigned) < count and days_checked < max_days:
        for hour in DAILY_SLOTS:
            slot_dt = datetime.combine(check_date, dtime(hour, 0, 0), tzinfo=IST_TZ)
            # Slot must be strictly in the future (at least 60s ahead of cur_time)
            if slot_dt <= cur_time + timedelta(seconds=60):
                continue
            key = get_slot_key(slot_dt)
            if key in occupied:
                continue

            # Found an open slot!
            occupied.add(key)
            assigned.append({
                "slot_hour": hour,
                "slot_datetime_ist": slot_dt,
                "publish_at_utc": to_utc_iso(slot_dt),
                "publish_at_ist": to_ist_str(slot_dt),
                "due_at": slot_dt.timestamp(),
                "timezone": "Asia/Kolkata"
            })
            if len(assigned) >= count:
                break

        check_date += timedelta(days=1)
        days_checked += 1

    return assigned


def next_available_slot(account_id: str, posts: list, after_dt: Optional[datetime] = None) -> Optional[Dict]:
    """Single next available slot."""
    slots = next_available_slots(account_id, 1, posts, after_dt=after_dt)
    return slots[0] if slots else None


def get_daily_slots_overview(account_id: str, posts: list, target_date: Optional[datetime] = None) -> Dict:
    """Full overview of today's 12 slots for the publishing dashboard."""
    cur = now_ist()
    if target_date is None:
        target_date = cur
    elif target_date.tzinfo is None:
        target_date = target_date.replace(tzinfo=IST_TZ)
    else:
        target_date = target_date.astimezone(IST_TZ)

    target_d = target_date.date()
    slots_out = []

    # Map existing posts for this account on target_d
    posts_by_hour = {}
    active_statuses = {"scheduled", "posting", "uploaded_scheduled", "posted", "published"}
    for p in posts:
        if account_id and p.get("account") != account_id:
            continue
        if p.get("status") not in active_statuses:
            continue
        dt = parse_publish_time(p.get("publish_at_utc")) or parse_publish_time(p.get("due_at"))
        if dt and dt.date() == target_d and dt.hour in DAILY_SLOTS:
            posts_by_hour[dt.hour] = p

    for idx, hour in enumerate(DAILY_SLOTS, start=1):
        slot_dt = datetime.combine(target_d, dtime(hour, 0, 0), tzinfo=IST_TZ)
        time_label = slot_dt.strftime("%I:%M %p")
        assigned_post = posts_by_hour.get(hour)
        
        if assigned_post:
            status = "occupied"
        elif slot_dt < cur:
            status = "passed"
        else:
            status = "open"

        slots_out.append({
            "slot_num": idx,
            "hour": hour,
            "time_label": time_label,
            "status": status,
            "publish_at_ist": to_ist_str(slot_dt),
            "publish_at_utc": to_utc_iso(slot_dt),
            "post": {
                "id": assigned_post.get("id"),
                "title": assigned_post.get("title"),
                "status": assigned_post.get("status"),
                "remote_id": assigned_post.get("remote_id") or assigned_post.get("yt_video_id"),
                "url": assigned_post.get("url")
            } if assigned_post else None
        })

    return {
        "date": target_d.isoformat(),
        "timezone": "Asia/Kolkata",
        "total_slots": len(DAILY_SLOTS),
        "occupied_count": sum(1 for s in slots_out if s["status"] == "occupied"),
        "open_count": sum(1 for s in slots_out if s["status"] == "open"),
        "passed_count": sum(1 for s in slots_out if s["status"] == "passed"),
        "slots": slots_out
    }

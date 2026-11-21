"""Regression test: Ensure PeakCut never generates or uploads generic clickbait clips like 'WAIT FOR IT' or 'Loud moment'."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from studio import brain, posting, ctx

def test_banned_detection():
    # Hooks
    assert brain.is_banned_hook("WAIT FOR IT")
    assert brain.is_banned_hook("Wait For It")
    assert brain.is_banned_hook("WAIT FOR END")
    assert brain.is_banned_hook("WATCH TILL END")
    assert brain.is_banned_hook("LOUD MOMENT")
    assert not brain.is_banned_hook("WHERE IS THE LOOT")
    assert not brain.is_banned_hook("CRAZY HEADSHOT")

    # Titles
    assert brain.is_banned_title("Loud moment")
    assert brain.is_banned_title("loud moment")
    assert brain.is_banned_title("This is a loud moment")
    assert brain.is_banned_title("Wait for it")
    assert brain.is_banned_title("Short")  # too short (< 6 chars)
    assert not brain.is_banned_title("IShowSpeed Can't Find The Loot in GTA 6 💀😂")
    print("PASS: test_banned_detection")


def test_fallback_by_loudness_no_clickbait():
    # Synthetic audio db with a peak at 10s
    db = np.zeros(60)
    db[8:15] = 20.0  # high loudness peak

    # Scenario 1: No speech words -> should NOT pick any clips (drop noise/bumps)
    empty_words = []
    picks = brain.fallback_by_loudness(db, empty_words, n=3, max_len=20, duration=60)
    assert len(picks) == 0, "Loudness fallback must not pick segments with no speech"

    # Scenario 2: Fewer than 4 speech words -> should NOT pick any clips
    few_words = [{"w": "Oh", "s": 9.0, "e": 9.5}, {"w": "wow", "s": 9.6, "e": 10.0}]
    picks = brain.fallback_by_loudness(db, few_words, n=3, max_len=20, duration=60)
    assert len(picks) == 0, "Loudness fallback must not pick segments with fewer than 4 words"

    # Scenario 3: Real speech words -> should derive speech-based hook and title, NEVER 'WAIT FOR IT' or 'Loud moment'
    real_words = [
        {"w": "Bro", "s": 8.0, "e": 8.4},
        {"w": "where", "s": 8.5, "e": 8.9},
        {"w": "is", "s": 9.0, "e": 9.2},
        {"w": "the", "s": 9.3, "e": 9.4},
        {"w": "loot", "s": 9.5, "e": 9.9},
        {"w": "in", "s": 10.0, "e": 10.2},
        {"w": "here", "s": 10.3, "e": 10.7},
    ]
    picks = brain.fallback_by_loudness(
        db, real_words, n=1, max_len=20, duration=60,
        title="IShowSpeed Plays GTA 6", uploader="IShowSpeed", game="GTA 6"
    )
    assert len(picks) == 1
    p = picks[0]
    assert p["hook"] != "WAIT FOR IT"
    assert not brain.is_banned_hook(p["hook"])
    assert "loud moment" not in p["title"].lower()
    assert not brain.is_banned_title(p["title"])
    assert "unavailable" not in p["reason"].lower()
    assert p["score"] >= 70
    print(f"PASS: test_fallback_by_loudness_no_clickbait (hook={p['hook']}, title={p['title']})")


def test_tidy_replaces_banned_hook_and_title():
    # If raw input had WAIT FOR IT and Loud moment, _tidy must replace them
    raw_clip = {
        "hook": "WAIT FOR IT",
        "title": "Loud moment",
        "description": "",
        "category": "other",
        "score": 50,
        "reason": "Picked by loudness because the AI was unavailable."
    }
    words = [
        {"w": "What", "s": 5.0, "e": 5.3},
        {"w": "are", "s": 5.4, "e": 5.6},
        {"w": "you", "s": 5.7, "e": 5.9},
        {"w": "doing", "s": 6.0, "e": 6.5},
        {"w": "bro", "s": 6.6, "e": 7.0},
    ]
    tidied = brain._tidy(raw_clip, 4.0, 15.0, game="GTA 6", words=words, uploader="Speed")
    assert tidied["hook"] != "WAIT FOR IT"
    assert not brain.is_banned_hook(tidied["hook"])
    assert "loud moment" not in tidied["title"].lower()
    assert not brain.is_banned_title(tidied["title"])
    assert "unavailable" not in tidied["reason"].lower()
    assert len(tidied["title"]) >= 30
    print(f"PASS: test_tidy_replaces_banned_hook_and_title (hook={tidied['hook']}, title={tidied['title']})")


def test_on_clip_ready_rejects_banned_clips():
    job = {
        "id": "j1", "user": "u_test", "creator": "c1",
        "options": {"auto_upload": True, "upload_mode": "scheduling"}
    }
    clip_banned_1 = {
        "id": "c1", "status": "done", "duration": 30,
        "hook": "WAIT FOR IT", "title": "Loud moment"
    }
    clip_banned_2 = {
        "id": "c2", "status": "done", "duration": 30,
        "hook": "NORMAL HOOK", "title": "A very loud moment in game"
    }
    clip_valid = {
        "id": "c3", "status": "done", "duration": 30,
        "hook": "WHERE IS THE LOOT", "title": "Speed Can't Find The Loot in GTA 6 💀😂"
    }

    # Should exit early without enqueueing
    with ctx.as_user("u_test"):
        # Posting queue should not receive banned clips
        posting.on_clip_ready(job, clip_banned_1)
        posting.on_clip_ready(job, clip_banned_2)
        # Check that no posts were created for c1 or c2
        posts = [p for p in posting._posts if p.get("clip") in ("c1", "c2")]
        assert len(posts) == 0
    print("PASS: test_on_clip_ready_rejects_banned_clips")


if __name__ == "__main__":
    test_banned_detection()
    test_fallback_by_loudness_no_clickbait()
    test_tidy_replaces_banned_hook_and_title()
    test_on_clip_ready_rejects_banned_clips()
    print("All no_loud_moment tests passed successfully!")

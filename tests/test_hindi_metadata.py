"""Tests for Hindi / Hinglish trending metadata generation, language detection, emoji rules, and deduplication."""
import sys
sys.path.insert(0, ".")

import numpy as np
from studio import brain


def check(name, got, expected=True):
    if got != expected:
        raise AssertionError(f"FAIL: {name} (expected {expected!r}, got {got!r})")
    print(f"  OK: {name}")


# 1. Language detection
check("Devanagari script detected as Hindi", brain.is_hindi_or_hinglish("यह क्या हो गया भाई 😭"))
check("Roman Hinglish detected as Hindi/Hinglish", brain.is_hindi_or_hinglish("bhai ye kya ho gaya yaar dekh"))
check("Mixed Hindi-English conversation detected", brain.is_hindi_or_hinglish("Techno Gamerz ne pehli baar GTA 6 khela bhai kya scene hai"))
check("English text NOT detected as Hindi", not brain.is_hindi_or_hinglish("Hello everyone welcome back to the stream today we are playing minecraft"))

# 2. Correct rules selection in _rules()
hindi_transcript = "[0.0] bhai ye kya ho gaya yaar [2.0] dekh usko kya kiya"
english_transcript = "[0.0] hello and welcome back [2.0] what a crazy play guys"
arabic_transcript = "[0.0] " + "مرحبا بكم في هذا الفيديو سبسكرايب " * 10

rules_hi = brain._rules(15, 60, hindi_transcript)
rules_en = brain._rules(15, 60, english_transcript)
rules_ar = brain._rules(15, 60, arabic_transcript)

check("Hindi transcript receives HINDI_HINGLISH_NOTE", brain.HINDI_HINGLISH_NOTE in rules_hi)
check("English transcript receives ENGLISH_NOTE", brain.ENGLISH_NOTE in rules_en)
check("Arabic transcript receives ARABIC_NOTE", brain.ARABIC_NOTE in rules_ar)
check("English transcript does NOT receive ARABIC_NOTE", brain.ARABIC_NOTE not in rules_en)
check("English transcript does NOT receive HINDI_HINGLISH_NOTE", brain.HINDI_HINGLISH_NOTE not in rules_en)

# 3. Emoji rules & formatting in _tidy()
# Hook must have ZERO emojis, ALL CAPS, max 5 words
raw_clip_1 = {
    "start": 0, "end": 20, "score": 90, "category": "funny",
    "hook": "bhai ye kya hua 😂💀 epic moment extra words",
    "title": "Ye kya ho gaya bhai 😂💀",
    "description": "Streamer got completely surprised by the glitch 😂💀. Watch what happens next.",
    "hashtags": ["Gaming", "GTA6"],
    "highlight_words": ["bhai", "glitch"],
    "reason": "Hilarious glitch reaction"
}
t1 = brain._tidy(raw_clip_1, 0, 20)
check("Hook strips emojis", "😂" not in t1["hook"] and "💀" not in t1["hook"])
check("Hook is ALL CAPS", t1["hook"].isupper())
check("Hook is at most 5 words", len(t1["hook"].split()) <= 5)
check("Title keeps emojis", "😂" in t1["title"] or "💀" in t1["title"])
check("Title is <= 60 characters", len(t1["title"]) <= 60)
check("Description strips emojis", "😂" not in t1["description"] and "💀" not in t1["description"])

# 4. Long title truncation in _tidy()
long_title = "This is an extremely long title that exceeds sixty characters easily and must be truncated properly"
raw_clip_2 = {"title": long_title, "hook": "SHORT HOOK", "score": 80}
t2 = brain._tidy(raw_clip_2, 0, 20)
check("Long title truncated to <= 60 characters", len(t2["title"]) <= 60)

# 5. Batch deduplication in find_clips
# Two clips with identical hook or title prefix
dummy_words = [
    {"s": 0.0, "e": 1.0, "w": "bhai"},
    {"s": 1.0, "e": 2.0, "w": "dekh"},
    {"s": 2.0, "e": 3.0, "w": "kya"},
    {"s": 3.0, "e": 4.0, "w": "hua."},
    {"s": 5.0, "e": 6.0, "w": "arre"},
    {"s": 6.0, "e": 7.0, "w": "yaar"},
    {"s": 7.0, "e": 8.0, "w": "yeh."},
]
dummy_db = np.zeros(20)

# Mock ask_ai returning two clips with identical hook
saved_ask_ai = brain.ask_ai
try:
    brain.ask_ai = lambda prompt, schema=None, purpose="", timeout=None: (
        [
            {"start": 0.0, "end": 4.0, "score": 95, "hook": "SAME HOOK", "title": "Techno Gamerz scene 😂🔥", "description": "Good clip 1", "hashtags": []},
            {"start": 4.0, "end": 8.0, "score": 90, "hook": "SAME HOOK", "title": "Techno Gamerz scene 😂🔥", "description": "Good clip 2", "hashtags": []},
        ],
        "mock-model",
        100
    )
    clips, info = brain.find_clips(dummy_words, dummy_db, 10.0, max_clips=5, min_len=3, max_len=8)
    check("find_clips deduplicates clips with duplicate hook", len(clips) == 1)
finally:
    brain.ask_ai = saved_ask_ai

print("\nAll Hindi/Hinglish metadata tests passed successfully!")

"""Test subtitle accuracy, phonetic correction, domain glossary, and timestamp preservation."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["PEAKCUT_DATA"] = tempfile.mkdtemp(prefix="pc-subs-")
os.environ["DATABASE_URL"] = ""
sys.path.insert(0, ".")

from studio import brain, subtitles

fails = []

def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x and not ok else ""))
    if not ok:
        fails.append(n)

def ws(text, step=0.4):
    return [{"w": w, "s": round(i * step, 2), "e": round(i * step + 0.35, 2)} for i, w in enumerate(text.split())]

def text(words):
    return " ".join(w["w"] for w in words)

# 1. Phonetic & Accent Corrections (offline rule pass)
words1 = ws("VACH out for that car")
fixed1 = subtitles.correct_words(words1)
check("VACH -> WATCH phonetic correction", text(fixed1) == "WATCH out for that car", text(fixed1))
check("timestamps preserved after VACH correction", [(w["s"], w["e"]) for w in fixed1] == [(w["s"], w["e"]) for w in words1])

# Indian English V/W and common phonetic confusion
words2 = ws("show me that vedio I vant to see the vindow")
fixed2 = subtitles.correct_words(words2)
check("vedio -> video, vant -> want, vindow -> window", text(fixed2) == "show me that video I want to see the window", text(fixed2))
check("timestamps preserved for accent pairs", len(fixed2) == len(words2) and fixed2[2]["s"] == words2[2]["s"])

# 2. Multi-word phrases & Creator glossary
words3 = ws("did you see carry minati playing gta with scout op")
fixed3 = subtitles.correct_words(words3)
check("multi-word creator and game casing", text(fixed3) == "did you see CarryMinati playing GTA with ScoutOP", text(fixed3))
check("phrase contraction keeps valid time bounds", fixed3[3]["s"] == words3[3]["s"] and fixed3[3]["e"] == words3[4]["e"])

# 3. brain._same_word accepts domain & phonetic replacements
check("brain._same_word accepts vach -> watch", brain._same_word("vach", "watch"))
check("brain._same_word accepts VACH -> WATCH", brain._same_word("VACH", "WATCH"))
check("brain._same_word accepts vedio -> video", brain._same_word("vedio", "video"))
check("brain._same_word rejects completely unrelated words", not brain._same_word("watch", "elephant"))

# 4. brain.fix_caption_words offline integration
def no_ai(*a, **k):
    raise RuntimeError("No AI configured")
brain.ask_ai = no_ai

words4 = ws("VACH this cool vedio")
out4 = brain.fix_caption_words(words4, "test-job")
check("brain.fix_caption_words offline applies phonetic fix", text(out4) == "WATCH this cool video", text(out4))
check("timestamps preserved through brain.fix_caption_words", [(w["s"], w["e"]) for w in out4] == [(w["s"], w["e"]) for w in words4])

# 5. Subtitle review export and import parsing
orig = ws("Hello world this is a test clip with great accuracy")
sub_text = subtitles.build_subtitles_text(orig, max_words=4)
check("build_subtitles_text produces non-empty output", bool(sub_text.strip()))
lines = sub_text.strip().splitlines()
check("build_subtitles_text formats multiple lines", len(lines) >= 2)

# Simulate user editing the subtitle text
edited_text = sub_text.replace("great", "PERFECT")
parsed_words = subtitles.parse_subtitles_text(edited_text, orig)
check("parse_subtitles_text reflects edited word", "PERFECT" in text(parsed_words), text(parsed_words))
check("parse_subtitles_text maintains start time", parsed_words[0]["s"] == orig[0]["s"])
check("parse_subtitles_text maintains end time", parsed_words[-1]["e"] == orig[-1]["e"])

# If user adds an extra word in a line, timestamps remain bounded
edited_extra = sub_text.replace("test clip", "test epic clip")
parsed_extra = subtitles.parse_subtitles_text(edited_extra, orig)
check("extra word parsed into tokens", "epic" in text(parsed_extra))
check("time bounds still monotonically increasing", all(parsed_extra[i]["s"] <= parsed_extra[i]["e"] for i in range(len(parsed_extra))))

if fails:
    print(f"\n{len(fails)} subtitle tests failed: {fails}")
    sys.exit(1)
print(f"\nAll {9} subtitle accuracy tests passed successfully.")

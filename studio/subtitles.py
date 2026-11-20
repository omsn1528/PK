"""Contextual spelling correction and glossary management for subtitles.

Fixes acoustic and accent-based speech recognition mistakes (e.g., 'VACH' -> 'WATCH',
'vedio' -> 'video') while strictly preserving word timings and spoken meaning.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import config

_VOCAB_FILE = config.DATA_DIR / "vocabulary.json"

_DEFAULT_VOCAB = {
    "phonetic_corrections": {
        "vach": "watch", "vaching": "watching", "vached": "watched", "vatch": "watch",
        "vedio": "video", "vedios": "videos", "vant": "want", "vanted": "wanted", "vants": "wants",
        "vait": "wait", "vaiting": "waiting", "vaited": "waited", "vhat": "what", "vhen": "when",
        "vhere": "where", "vhy": "why", "vich": "which", "vith": "with", "vork": "work",
        "vorking": "working", "vorld": "world", "von": "won", "vill": "will", "vould": "would",
        "ve": "we", "vell": "well", "valk": "walk", "valking": "walking",
        "vindow": "window", "vindows": "windows",
        "plese": "please", "pulce": "police", "plice": "police", "helecopter": "helicopter",
        "a pressure": "oppressor", "apressor": "oppressor", "apresor": "oppressor",
        "gta": "GTA", "g tea a": "GTA", "gti": "GTA", "gta v": "GTA 5", "gta vi": "GTA 6"
    },
    "gaming_terms": [
        "GTA", "GTA 5", "GTA 6", "GTA Online", "Vice City", "Rockstar Games",
        "Lucia", "Jason", "Oppressor", "Ammu-Nation", "Los Santos", "San Andreas",
        "Wanted Level", "Busted", "Wasted", "Clutch", "Headshot", "Respawn",
        "Loot", "Camper", "Noob", "Pro", "Streamer", "Chat", "Facecam", "Gameplay"
    ],
    "creator_names": {
        "carry minati": "CarryMinati", "carryminati": "CarryMinati",
        "carry is live": "CarryisLive", "carryislive": "CarryisLive",
        "gamer fleet": "GamerFleet", "gamerfleet": "GamerFleet",
        "myth pat": "Mythpat", "mythpat": "Mythpat",
        "techno gamerz": "Techno Gamerz", "technogamerz": "Techno Gamerz",
        "live insaan": "Live Insaan", "liveinsaan": "Live Insaan",
        "mortal": "Mortal", "scout": "Scout", "scout op": "ScoutOP", "scoutop": "ScoutOP"
    },
    "hinglish_terms": {
        "yar": "yaar", "yarr": "yaar", "keya": "kya", "gaddi": "gaadi", "gardi": "gaadi",
        "pakkada": "pakda", "bahi": "bhai", "acha": "accha", "thek": "theek", "paisa": "paise",
        "bhago": "bhaago", "dhyan": "dhyaan"
    }
}

_cached_vocab: dict | None = None
_cached_mtime: float = 0.0


def load_vocab() -> dict:
    """Load vocabulary from data/vocabulary.json with automatic reload on change."""
    global _cached_vocab, _cached_mtime
    f = _VOCAB_FILE
    try:
        mtime = f.stat().st_mtime if f.is_file() else 0.0
    except OSError:
        mtime = 0.0

    if _cached_vocab is not None and mtime == _cached_mtime:
        return _cached_vocab

    if f.is_file():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                merged = {
                    "phonetic_corrections": {**_DEFAULT_VOCAB["phonetic_corrections"], **data.get("phonetic_corrections", {})},
                    "gaming_terms": sorted(set(_DEFAULT_VOCAB["gaming_terms"] + data.get("gaming_terms", []))),
                    "creator_names": {**_DEFAULT_VOCAB["creator_names"], **data.get("creator_names", {})},
                    "hinglish_terms": {**_DEFAULT_VOCAB["hinglish_terms"], **data.get("hinglish_terms", {})},
                }
                _cached_vocab = merged
                _cached_mtime = mtime
                return merged
        except Exception:
            pass

    _cached_vocab = _DEFAULT_VOCAB
    _cached_mtime = 0.0
    return _DEFAULT_VOCAB


def get_glossary_prompt(language: str = "") -> str:
    """Return concise glossary lines to include in AI subtitle correction prompts.

    The Romanized Hindi/Urdu rules are only included for those languages: on an English video an
    instruction to 'write Hindi in Hinglish' can make a small model change ordinary English words.
    """
    vocab = load_vocab()
    pc = vocab.get("phonetic_corrections", {})
    gt = vocab.get("gaming_terms", [])
    cn = vocab.get("creator_names", {})
    ht = vocab.get("hinglish_terms", {}) if (language or "").lower().startswith(("hi", "ur")) else {}

    lines = []
    # Key phonetic replacements
    sample_pc = [f"'{k}' -> '{v}'" for k, v in list(pc.items())[:12]]
    if sample_pc:
        lines.append("Phonetic accents: some speakers pronounce W as V. Fix mishearings like " + ", ".join(sample_pc) + ".")

    # Gaming & GTA terms
    if gt:
        lines.append("Gaming vocabulary: " + ", ".join(gt[:20]) + ".")

    # Creators
    creators = list(set(cn.values()))[:10]
    if creators:
        lines.append("Creators & handles: " + ", ".join(creators) + ".")

    # Hinglish
    sample_ht = [f"'{k}' -> '{v}'" for k, v in list(ht.items())[:8]]
    if sample_ht:
        lines.append("Common Romanized Hindi/Urdu spelling: " + ", ".join(sample_ht) + ".")

    return "\n".join(lines)


def _split_punct(word: str) -> tuple[str, str, str]:
    """Separate leading/trailing punctuation from core word: ('(', 'watch', '!)')."""
    m = re.match(r"^([^\w]*)(.*?)([^\w]*)$", word, re.UNICODE)
    if not m:
        return "", word, ""
    return m.group(1), m.group(2), m.group(3)


def _apply_case(original: str, replacement: str) -> str:
    """Match the casing style of the original token if replacement is lowercase."""
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original and original[0].isupper() and not replacement[0].isupper():
        return replacement.capitalize()
    return replacement


def correct_words(words: list, title: str = "", game: str = "") -> list:
    """Contextually correct misheard words while strictly preserving timestamps and word positions.

    Each item in words is a dict: {'w': str, 's': float, 'e': float}.
    Returns a new list of word dicts with corrected spellings and confidence flags.
    """
    if not words:
        return []

    vocab = load_vocab()
    phonetic = {k.lower(): v for k, v in vocab.get("phonetic_corrections", {}).items()}
    hinglish = {k.lower(): v for k, v in vocab.get("hinglish_terms", {}).items()}
    creators = {k.lower(): v for k, v in vocab.get("creator_names", {}).items()}

    out = [dict(w) for w in words]
    n = len(out)

    # 1. Two-word phrase corrections (e.g. 'carry minati', 'gamer fleet', 'g tea')
    all_phrases = {}
    for source_map in (phonetic, creators, hinglish):
        for k, v in source_map.items():
            if " " in k:
                all_phrases[k] = v

    i = 0
    while i < n:
        if i + 1 < n:
            p1, w1, t1 = _split_punct(out[i]["w"])
            p2, w2, t2 = _split_punct(out[i + 1]["w"])
            two_word = f"{w1} {w2}".lower().strip()
            if two_word in all_phrases:
                rep = all_phrases[two_word]
                out[i]["w"] = f"{p1}{rep}{t2}"
                out[i]["corrected"] = True
                out[i]["confidence"] = 0.98
                # Second word becomes empty or merged into first
                out[i]["e"] = max(out[i]["e"], out[i + 1]["e"])
                out[i + 1]["w"] = ""
                i += 2
                continue

        # 2. Single-word phonetic / terminology corrections
        p, core, t = _split_punct(out[i]["w"])
        core_low = core.lower().strip()
        rep = None
        conf = 1.0

        if core_low in phonetic:
            rep = phonetic[core_low]
            conf = 0.96
        elif core_low in creators:
            rep = creators[core_low]
            conf = 0.98
        elif core_low in hinglish:
            rep = hinglish[core_low]
            conf = 0.95

        if rep:
            cased = _apply_case(core, rep)
            out[i]["w"] = f"{p}{cased}{t}"
            out[i]["corrected"] = True
            out[i]["confidence"] = conf
        else:
            # Check for suspicious accent forms (e.g. starts with 'v' when English word starts with 'w')
            if core_low.startswith("v") and len(core_low) >= 3:
                w_candidate = "w" + core_low[1:]
                if w_candidate in phonetic:
                    cased = _apply_case(core, phonetic[w_candidate])
                    out[i]["w"] = f"{p}{cased}{t}"
                    out[i]["corrected"] = True
                    out[i]["confidence"] = 0.88

        i += 1

    # Filter out words that were merged into previous words (empty w)
    filtered = []
    for w in out:
        if w.get("w"):
            filtered.append(w)

    return filtered


def build_subtitles_text(words: list, max_words: int = 0) -> str:
    """Format timed words into editable line-by-line subtitle text for user review.

    Format: [start-end] Word tokens
    """
    if not words:
        return ""
    lines = []
    cur_line = []
    line_start = words[0]["s"] if words else 0.0

    for w in words:
        split_by_count = max_words > 0 and len(cur_line) >= max_words
        if cur_line and (split_by_count or w["s"] - cur_line[-1]["e"] > 0.8 or w["s"] - line_start > 6.0 or cur_line[-1]["w"][-1:] in ".?!"):
            s_str = f"{line_start:.2f}"
            e_str = f"{cur_line[-1]['e']:.2f}"
            text = " ".join(item["w"] for item in cur_line)
            lines.append(f"[{s_str} - {e_str}] {text}")
            cur_line = []
            line_start = w["s"]
        cur_line.append(w)

    if cur_line:
        s_str = f"{line_start:.2f}"
        e_str = f"{cur_line[-1]['e']:.2f}"
        text = " ".join(item["w"] for item in cur_line)
        lines.append(f"[{s_str} - {e_str}] {text}")

    return "\n".join(lines)


def parse_subtitles_text(text: str, original_words: list) -> list:
    """Parse user-edited subtitle lines and re-distribute timestamps across words.

    Guarantees that audio synchronization and duration are strictly preserved.
    """
    if not text.strip():
        return original_words

    out_words = []
    lines = text.strip().splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^\[\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*\]\s*(.*)$", line)
        if m:
            s = float(m.group(1))
            e = float(m.group(2))
            tokens = m.group(3).split()
        else:
            tokens = line.split()
            s = out_words[-1]["e"] if out_words else 0.0
            e = s + max(0.5, len(tokens) * 0.35)

        if not tokens:
            continue

        span = max(0.1, e - s)
        step = span / len(tokens)
        for idx, tok in enumerate(tokens):
            w_start = round(s + idx * step, 2)
            w_end = round(s + (idx + 1) * step, 2)
            out_words.append({"w": tok, "s": w_start, "e": w_end})

    return out_words or original_words

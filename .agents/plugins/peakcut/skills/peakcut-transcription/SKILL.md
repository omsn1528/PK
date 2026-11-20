---
name: peakcut-transcription
description: Improve PeakCut speech-to-text accuracy, word-level timestamps, glossary/phonetic correction, transcript verification and subtitle QA. Use when touching studio/transcribe.py, studio/subtitles.py, studio/brain.py caption fixes, studio/roman.py or subtitle editing.
---

# PeakCut transcription and subtitles

Speech runs locally through `sherpa-onnx` + Parakeet int8 (`studio/transcribe.py`); caption cleanup lives in `studio/subtitles.py` and `studio/brain.py`; Roman-letter output uses `studio/roman.py`; ASS burn-in is in `studio/render.py`.

## Accuracy rules

1. Generate word-level timestamps (`{w, s, e}`). Preserve `s`/`e` on every textual correction. Re-transcribe borrowed YouTube captions locally when exact timings matter.
2. First pass is deterministic: `subtitles.correct_words()` merges known phrases and fixes accent errors (VACH→WATCH, VEDIO→VIDEO), GTA/creator/Hinglish terms from `data/vocabulary.json` plus built-ins. Never invent dialogue.
3. Second pass is the AI wording fix: exactly one string per input word, reject rewrites via `brain._same_word()`, keep proper nouns, do not translate or "improve" meaning. Give Hindi/Urdu rules only to Hindi/Urdu videos.
4. Mark low-confidence fixes with an `uncertain` flag for manual review. When a word cannot be identified confidently, keep the spoken word and flag it — do not substitute an unrelated word.
5. Validate before rendering: no empty words from merges, monotonic non-overlapping timings, no subtitles before speech or after it finishes, no Devanagari/Urdu script left in the burned-in captions.
6. The editable text format is `[start - end] words`. Keep original timings when the user only fixes spelling; only redistribute when tokens are added/removed. Export `.ass` (and `.srt` where possible) alongside the video.

## Practical checks

- Test examples: `vach` → `watch`, `vedio` → `video`, `carry minati` → `CarryMinati`, ` keya ` → `kya`, `g tea a` → `GTA`.
- Keep CPU settings: 2+ threads, 12–24 s chunks, 10-minute job blocks, no model in RAM twice.
- Run `py -3.13 tests/run.py`; add correction/timing cases to `tests/test_stuck.py` or a dedicated subtitle suite.

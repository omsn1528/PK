---
name: peakcut-metadata
description: Generate viral, culturally resonant Hindi, Hinglish, and English metadata (titles, descriptions, contextual emojis, and verified hashtags) for PeakCut Shorts and Reels. Use when improving studio/brain.py title generation, language detection, emoji rules, or hashtag diversity.
---

# PeakCut Metadata Generation: Hindi, Hinglish & English

This skill guides metadata creation for YouTube Shorts and Instagram Reels, with deep support for Indian creator culture, gaming streams, podcasts, and comedy.

## Core Principles

1. **Automatic Language Detection**:
   - Analyze transcript words and spoken language.
   - If Hindi or mixed Hindi-English (Hinglish) is spoken, generate authentic Romanized Hinglish (e.g. *"Techno Gamerz ne pehli baar GTA 6 khela 😭🔥"*).
   - If English is spoken, generate natural, punchy English.
   - For mixed content, preserve the creator's natural conversational flow.

2. **Title Length & Readability**:
   - **Keep titles short and punchy**: Target 35–60 characters.
   - Mobile Shorts screens occlude long titles. Titles must be quickly readable in 1 second while scrolling.
   - Avoid long, explanatory essay titles.

3. **Contextual Emojis (Title Only)**:
   - Use emojis **ONLY in the title** (approx 1–3 relevant emojis at the end or naturally placed).
   - Never use emojis in hooks or descriptions.
   - Emotion-to-Emoji Mapping:
     - **Funny**: 😂 💀 🤣
     - **Shock / Surprise**: 😳 😨 👀
     - **Gaming / Action**: 🔥 ⚡ 🎮
     - **Dark Humour**: ☠️ 🥶 🌑
     - **Emotional**: 🥀 ❤️🩹
     - **Achievement / Win**: 💯 🏆

4. **Prevent Repetition Across Batch**:
   - Never repeat the same title formula, hook, or emoji set across clips in the same video or batch.
   - Track `used_hooks`, `used_titles`, and vary sentence structures.
   - If multiple funny clips exist, vary the phrasing: e.g. one uses *"Bhai sahab..."*, another uses *"Ye kya scene hai..."*, another is direct action.

5. **Engaging Descriptions & Verified Hashtags**:
   - 1–2 short sentences describing the actual highlight.
   - 4–7 relevant hashtags. Always include verified game, creator, and topic tags. Avoid generic tag spam.

6. **Preserve Strict Accuracy**:
   - Never invent events, quotes, or fake clickbait that didn't happen in the clip.
   - The title must reflect the genuine highlight.

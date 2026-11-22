---
name: yt-shorts
description: YouTube Shorts optimization skill. Covers viral pacing, 3-second hook formulation, audience retention patterns, vertical framing safe zones, and Shorts SEO metadata. Use when tuning studio/brain.py prompt evaluation, hook selection, or title generation for YouTube Shorts.
---

# YouTube Shorts Agent Skill

This skill guides the agent in identifying, scoring, and formatting viral YouTube Shorts clips from long-form video content and livestreams.

## Core Principles for YouTube Shorts

### 1. The 3-Second Rule (Instant Hook)
- Viewers swipe within 2–3 seconds if not hooked.
- The clip MUST start immediately with speech, action, or high tension.
- Ban slow intros, silence, loading screens, and generic clickbait text ("WAIT FOR IT", "Loud moment").
- The hook text displayed at the top of the video must be punchy, specific, and context-rich (e.g., "SPEED FOUND A GLITCH 😂💀" rather than "WAIT FOR THIS").

### 2. Storytelling & Boundary Snapping
- Each Short must be a self-contained narrative or punchline: Setup → Escalation → Climax/Resolution.
- Clip boundaries must snap to natural speech pauses:
  - Never cut mid-syllable or mid-sentence.
  - End on a punchline, reaction, or clean question.
- Optimal duration: 25 to 58 seconds (never exceed 60 seconds).

### 3. Vertical Safe Zones (1080×1920)
- The YouTube Shorts UI covers significant portions of the screen:
  - Right edge: Like, Dislike, Comments, Share buttons (keep 120px margin).
  - Bottom area: Channel avatar, title, audio pill, subscribe button (keep bottom 320px clear of subtitles).
  - Top area: Search bar, camera icon (keep top 160px clear).
- Place high-energy hook text in the upper-third safe zone (Y: 200–350px).
- Place animated word captions in the middle-third safe zone (Y: 1000–1250px).

### 4. Audio Pacing & Retention
- Audio clarity is the #1 retention factor. Dialogue must always sit above background sound.
- If background music is added, speech must duck music down to 15–20% volume.
- Use EBU R128 loudness normalization (`-14 LUFS`) for consistency across mobile playback.

### 5. Metadata for Shorts Search & Suggested Feed
- Titles: Under 60 characters with high curiosity and 1–2 relevant emojis. Include `#Shorts`.
- Descriptions: 2–3 sentences describing the key moment, followed by 3–5 targeted niche hashtags.
- Schedule Alignment: Distribute Shorts across fixed daily peak viewing hours (e.g., PeakCut's 6:00 AM – 5:00 PM IST 12-slot engine).

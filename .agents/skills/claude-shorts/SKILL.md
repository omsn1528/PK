---
name: claude-shorts
description: Long-to-short video intelligence skill adapted from claude-shorts. Specializes in transcript-based moment scoring, dialogue boundary snapping, multi-candidate ranking, and vertical layout composition. Use when enhancing studio/brain.py scout prompts or studio/jobs.py candidate selection.
---

# Claude-Shorts Intelligence Skill

This skill provides workflow logic and heuristic patterns for transforming multi-hour livestreams and VODs into high-engagement vertical Shorts.

## Workflow Pipeline

### 1. Transcript-Driven Candidate Discovery
- Analyze timestamped word tokens and speaker energy simultaneously.
- Scout 8–15 candidate segments per hour of footage.
- Calculate candidate density: ensure clips represent different parts of the timeline (prevent clustering all clips in the first 10 minutes).

### 2. Boundary Alignment Rules
- **Start Boundary**: Snap to the exact onset of the key dialogue line or punchy statement. Prepend 0.3s of ambient audio to avoid clipped consonants.
- **End Boundary**: Snap to 0.5s after the final word of the punchline or the conclusion of the reaction. Never cut off during laughter or active dialogue.
- **Duration Constraints**: Filter out candidates < 15 seconds (too short for storytelling) or > 60 seconds (ineligible for YouTube Shorts).

### 3. Candidate Scoring Heuristics (0–100)
- **Hook Strength (30%)**: Does the opening 3 seconds pose an intriguing question, conflict, or high-intensity statement?
- **Pacing & Flow (25%)**: Is speech continuous without prolonged awkward pauses or dead air?
- **Emotional Reaction (25%)**: Are there audio intensity spikes (shouting, laughing, gasp, music transition)?
- **Clarity / Self-Contained Context (20%)**: Can a viewer with zero prior context understand the situation?

### 4. Clickbait Prevention
- Reject generic placeholder hooks: "Wait for it", "Wait till end", "Loud moment", "Watch this".
- Require context-specific hooks derived from the actual spoken dialogue or gameplay action.

### 5. Layout & Subtitle Harmony
- Use vertical letterboxing with blurred background (`blur` layout) for standard 16:9 gameplay.
- Synchronize animated ASS subtitle highlights with spoken syllable timestamps.

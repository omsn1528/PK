---
name: seecut-qa
description: Automated video edit self-review and quality assurance skill inspired by SeeCut. Covers frame inspection, subtitle safe zone compliance, audio integrity verification, and talking-head framing checks. Use when running rendering QA or extending tests/ in PeakCut.
---

# SeeCut Video QA & Review Skill

This skill provides an automated quality assurance methodology for reviewing rendered vertical clips before scheduling or publishing.

## Automated Post-Render QA Checklist

### 1. Visual Framing & Composition
- **Resolution**: Exactly 1080×1920 (9:16 vertical aspect ratio).
- **Face / Subject Tracking**:
  - In talking-head or gameplay PiP layouts, ensure the speaker's eyes and mouth remain visible and unclipped.
  - Detect abrupt cropping jumps across scene transitions; smooth interpolation must reset cleanly at scene cuts.
- **Background Fill**: In blurred letterbox layout, ensure the blurred background has consistent blur radius (min 20px) and no black border bleeding.

### 2. Subtitle & Text Overlay Verification
- **Safe Zone Compliance**:
  - Hook text must sit between Y=200px and Y=380px.
  - Subtitle words must not cross below Y=1600px to avoid Shorts navigation and subscribe buttons.
  - Left and right margins must keep at least 80px padding from the screen edges.
- **Readability & Contrast**:
  - Subtitle styling must include high-contrast outline (`&H00000000` black outline with minimum 3px width) or semi-transparent background box.
  - Font scaling must fit the longest word on screen without line wrapping errors.

### 3. Audio Integrity & Mix Balance
- **Dialogue Loudness**: Spoken dialogue should peak between -1 dBTP and -3 dBTP, with integrated loudness targeted at -14 LUFS (EBU R128).
- **Background Music Ducking**:
  - Background music must duck by at least 12 dB during dialogue segments.
  - Ducking attack time: 50–100ms; release time: 300–500ms for natural transitions.
- **Audio/Video Sync**: Audio stream duration must match video stream duration within ±50ms.

### 4. Codec & Container Verification
- Container format: MP4 with `moov` atom placed at the start (`-movflags +faststart`).
- Video codec: H.264 (High Profile, Level 4.2).
- Audio codec: AAC-LC at 160 kbps, 48 kHz stereo.
- Verification command:
  ```bash
  ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration,codec_name -of json output.mp4
  ```

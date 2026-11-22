---
name: ffmpeg-toolkit
description: Advanced FFmpeg filtergraph and audio engineering skill adapted from wyattowalsh/agents. Covers complex multi-input filtergraphs, audio ducking with sidechaincompress/amix, two-pass loudnorm, vertical scaling, and stream mapping. Use when writing audio mixing, music integration, or complex video filters.
---

# Advanced FFmpeg Toolkit Skill

This skill provides verified, production-grade FFmpeg filtergraph recipes for audio ducking, vertical scaling, loudness normalization, and stream synchronization.

## 1. Automatic Audio Ducking (Music Under Speech)

To mix background music with dialogue so that the music automatically attenuates when speech occurs:

```bash
ffmpeg -y -i speech.wav -i music.mp3 -filter_complex \
  "[1:a]volume=0.35[bg]; \
   [bg][0:a]sidechaincompress=threshold=0.08:ratio=6:attack=50:release=350[ducked]; \
   [0:a][ducked]amix=inputs=2:duration=first:dropout_transition=2[aout]" \
  -map "[aout]" -c:a aac -b:a 160k output.m4a
```

### Parameter Breakdown:
- `volume=0.35`: Base volume level for background music during non-speech segments.
- `threshold=0.08`: Level at which speech activates compression on the music track.
- `ratio=6`: Compresses music by 6:1 (approximately -12 dB to -15 dB reduction during speech).
- `attack=50`: 50ms smooth transition into ducking when speech begins.
- `release=350`: 350ms smooth fade back up when the speaker pauses.
- `duration=first`: Audio output ends cleanly when the main clip ends.

## 2. Audio Loudness Normalization (EBU R128)

Standard YouTube Shorts audio normalization using the `loudnorm` filter:

```bash
ffmpeg -y -i input.mp4 -af "loudnorm=I=-14:LRA=11:TP=-1.5" -c:v copy -c:a aac -b:a 160k normalized.mp4
```

## 3. High-Quality 9:16 Vertical Video Reframing (Blur Background)

```bash
ffmpeg -y -i input.mp4 -filter_complex \
  "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg]; \
   [0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg]; \
   [bg][fg]overlay=(W-w)/2:(H-h)/2[v]" \
  -map "[v]" -map 0:a? -c:v libx264 -preset fast -crf 20 -c:a aac -b:a 160k \
  -movflags +faststart output.mp4
```

## 4. Burning ASS Subtitles with Custom Font Path

```bash
ffmpeg -y -i input.mp4 -vf "ass=subtitles.ass:fontsdir=/fonts" -c:v libx264 -crf 20 -c:a copy output.mp4
```
Ensure subtitle file path uses escaped forward slashes on Windows (e.g. `C\\:/peakcut/data/temp.ass`).

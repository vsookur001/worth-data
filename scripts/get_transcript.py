#!/usr/bin/env python3
"""
get_transcript.py

Pulls a transcript (with timestamps) for a given YouTube video ID using
youtube-transcript-api. Outputs both a plain-text version (for the LLM
prompt) and the raw timestamped segments (for building deep links).

Usage:
    python scripts/get_transcript.py VIDEO_ID
    # prints JSON: {"text": "...", "segments": [{"start": 0.0, "duration": 3.2, "text": "..."}]}

If no captions are available, exits non-zero and prints an error to stderr
so the caller can flag the episode for manual review instead of scoring blind.

Install: pip install youtube-transcript-api --break-system-packages
"""
import json
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def fetch(video_id: str) -> dict:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

    try:
        ytt = YouTubeTranscriptApi()
        fetched = ytt.fetch(video_id)  # prefers manually created, falls back to auto-generated
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        raise RuntimeError(f"No transcript available for {video_id}: {e}")

    segments = [
        {"start": s.start, "duration": s.duration, "text": s.text} for s in fetched
    ]
    # Build a readable, timestamp-annotated text block for the scoring prompt --
    # the rubric's "best minutes" / "skip" output depends on timestamps being visible.
    lines = []
    for s in segments:
        m, sec = divmod(int(s["start"]), 60)
        h, m = divmod(m, 60)
        ts = f"{h:d}:{m:02d}:{sec:02d}" if h else f"{m:d}:{sec:02d}"
        lines.append(f"[{ts}] {s['text']}")

    return {"text": "\n".join(lines), "segments": segments}


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: get_transcript.py VIDEO_ID")
    video_id = sys.argv[1]
    try:
        result = fetch(video_id)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main()

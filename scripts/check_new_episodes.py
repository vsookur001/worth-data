#!/usr/bin/env python3
"""
check_new_episodes.py

Polls each channel's uploads playlist via the YouTube Data API and returns
any videos newer than the last-seen video for that channel (per data/state.json).

Does NOT mutate state.json itself -- that happens only after an episode is
successfully scored AND published (see update_leaderboard.py), so a failure
partway through the pipeline doesn't silently skip an episode forever.

Usage:
    python scripts/check_new_episodes.py
    # prints a JSON list of new-episode dicts to stdout, one per line (NDJSON),
    # so run_pipeline.py can stream them.

Requires env var YOUTUBE_API_KEY.
"""
import json
import os
import sys
from pathlib import Path
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CHANNELS_PATH = ROOT / "data" / "channels.json"
STATE_PATH = ROOT / "data" / "state.json"

API_KEY = None  # set in main() so this module is importable/testable without the env var

# Safety valve: ignore anything older than this on a channel's *first* run,
# so resolving a brand-new channel doesn't try to back-score its entire archive.
FIRST_RUN_LOOKBACK_DAYS = 3


def api_get(endpoint: str, params: dict) -> dict:
    params = {**params, "key": API_KEY}
    url = f"https://www.googleapis.com/youtube/v3/{endpoint}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url) as resp:
        return json.load(resp)


def get_recent_uploads(uploads_playlist_id: str, max_results: int = 5) -> list:
    data = api_get(
        "playlistItems",
        {
            "part": "contentDetails,snippet",
            "playlistId": uploads_playlist_id,
            "maxResults": max_results,
        },
    )
    return data.get("items", [])


def get_video_durations(video_ids: list) -> dict:
    """Returns {video_id: duration_minutes}."""
    if not video_ids:
        return {}
    data = api_get("videos", {"part": "contentDetails", "id": ",".join(video_ids)})
    out = {}
    for item in data.get("items", []):
        out[item["id"]] = iso8601_duration_to_minutes(item["contentDetails"]["duration"])
    return out


def iso8601_duration_to_minutes(duration: str) -> float:
    """Parses e.g. 'PT1H32M5S' -> 92.08 minutes."""
    import re

    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 60 + mi + s / 60


def main():
    global API_KEY
    API_KEY = os.environ.get("YOUTUBE_API_KEY")
    if not API_KEY:
        sys.exit("YOUTUBE_API_KEY environment variable is required.")

    channels = json.loads(CHANNELS_PATH.read_text(encoding="utf-8"))["channels"]
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    last_seen = state.get("last_seen", {})

    new_episodes = []

    for ch in channels:
        playlist_id = ch.get("uploads_playlist_id")
        if not playlist_id:
            print(
                f"SKIP {ch['show']}: no uploads_playlist_id -- run resolve_channels.py first",
                file=sys.stderr,
            )
            continue

        try:
            recent = get_recent_uploads(playlist_id)
        except Exception as e:
            print(f"ERROR fetching uploads for {ch['show']}: {e}", file=sys.stderr)
            continue

        if not recent:
            continue

        last_seen_id = last_seen.get(ch["show"])
        video_ids = [item["contentDetails"]["videoId"] for item in recent]
        durations = get_video_durations(video_ids)

        candidates = []
        for item in recent:
            vid = item["contentDetails"]["videoId"]
            if vid == last_seen_id:
                break  # everything after this in the (reverse-chron) list is already seen
            candidates.append(item)

        if last_seen_id is None:
            # First-ever run for this channel: don't back-score the whole channel,
            # just consider uploads from the last few days.
            cutoff = datetime.now(timezone.utc) - timedelta(days=FIRST_RUN_LOOKBACK_DAYS)
            candidates = [
                item
                for item in candidates
                if datetime.fromisoformat(
                    item["contentDetails"]["videoPublishedAt"].replace("Z", "+00:00")
                )
                >= cutoff
            ]

        min_duration = ch.get("min_duration_minutes", 0)
        for item in candidates:
            vid = item["contentDetails"]["videoId"]
            duration_min = durations.get(vid, 0)
            if duration_min < min_duration:
                print(
                    f"SKIP {ch['show']} video {vid}: {duration_min:.0f} min "
                    f"< {min_duration} min threshold (likely a Short/clip)",
                    file=sys.stderr,
                )
                continue
            new_episodes.append(
                {
                    "show": ch["show"],
                    # Renamed source key in channels.json ('default_category') to make
                    # clear this is just a starting suggestion -- score_episode.py
                    # instructs Claude to override it per-episode if the actual
                    # content is about something else. The output field stays
                    # "category" since that's what the WORTH schema expects.
                    "category": ch["default_category"],
                    "video_id": vid,
                    "title": item["snippet"]["title"],
                    "published_at": item["contentDetails"]["videoPublishedAt"],
                    "youtube_url": f"https://www.youtube.com/watch?v={vid}",
                    "duration_minutes": round(duration_min, 1),
                }
            )

    for ep in new_episodes:
        print(json.dumps(ep))


if __name__ == "__main__":
    main()

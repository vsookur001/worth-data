#!/usr/bin/env python3
"""
resolve_channels.py

One-time (or occasional) helper: looks up each @handle in data/channels.json
via the YouTube Data API and fills in `channel_id`. Run this manually once
after setup, and again only if you add a new channel.

Usage:
    python scripts/resolve_channels.py

Requires env var YOUTUBE_API_KEY.
"""
import json
import os
import sys
from pathlib import Path
import urllib.request
import urllib.parse

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CHANNELS_PATH = ROOT / "data" / "channels.json"

API_KEY = None


def api_get(endpoint: str, params: dict) -> dict:
    params = {**params, "key": API_KEY}
    url = f"https://www.googleapis.com/youtube/v3/{endpoint}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url) as resp:
        return json.load(resp)


def resolve_handle(handle: str) -> str:
    """Resolve an @handle to a channel ID using the channels.list forHandle param."""
    handle_clean = handle if handle.startswith("@") else f"@{handle}"
    data = api_get("channels", {"part": "id,contentDetails", "forHandle": handle_clean})
    items = data.get("items", [])
    if not items:
        raise RuntimeError(f"No channel found for handle {handle_clean}")
    return items[0]["id"], items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def main():
    global API_KEY
    API_KEY = os.environ.get("YOUTUBE_API_KEY")
    if not API_KEY:
        sys.exit("YOUTUBE_API_KEY environment variable is required.")

    config = json.loads(CHANNELS_PATH.read_text(encoding="utf-8"))
    changed = False
    for ch in config["channels"]:
        if ch.get("channel_id"):
            continue
        try:
            channel_id, uploads_playlist_id = resolve_handle(ch["handle"])
            ch["channel_id"] = channel_id
            ch["uploads_playlist_id"] = uploads_playlist_id
            changed = True
            print(f"Resolved {ch['handle']} -> {channel_id}")
        except Exception as e:
            print(f"FAILED to resolve {ch['handle']}: {e}", file=sys.stderr)

    if changed:
        CHANNELS_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        print(f"Updated {CHANNELS_PATH}")
    else:
        print("Nothing to resolve.")


if __name__ == "__main__":
    main()

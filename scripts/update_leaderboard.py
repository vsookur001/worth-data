#!/usr/bin/env python3
"""
update_leaderboard.py

Writes the updated worth-episodes.json array to the REPO ROOT (not a data/
subfolder) as worth-episodes.json -- this MUST match exactly where your live
Ghost leaderboard's DATA_URL points:
https://raw.githubusercontent.com/vsookur001/worth-data/refs/heads/main/worth-episodes.json
If this path or repo ever changes, update DATA_URL in the leaderboard's HTML
card on Ghost to match, or the leaderboard will silently keep showing stale
data even though the pipeline is running fine.

Also updates data/state.json (kept in a subfolder since it's pipeline-internal
bookkeeping nobody else reads) with the new last-seen video ID for the
channel, marking the episode as fully processed.

The actual `git commit && git push` happens in the GitHub Actions workflow
step, not here -- this script just writes the files to disk.

Usage:
    python scripts/update_leaderboard.py updated_episodes.json show_name video_id
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEADERBOARD_PATH = ROOT / "worth-episodes.json"
STATE_PATH = ROOT / "data" / "state.json"


def main():
    if len(sys.argv) != 4:
        sys.exit("Usage: update_leaderboard.py updated_episodes.json show_name video_id")

    updated_episodes = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    show_name = sys.argv[2]
    video_id = sys.argv[3]

    # Sanity check: never let this script shrink the leaderboard.
    if LEADERBOARD_PATH.exists():
        current = json.loads(LEADERBOARD_PATH.read_text(encoding="utf-8"))
        if len(updated_episodes) < len(current):
            sys.exit(
                f"REFUSING to write: updated file has fewer episodes ({len(updated_episodes)}) "
                f"than current ({len(current)}). This would silently delete scored episodes."
            )

    LEADERBOARD_PATH.write_text(json.dumps(updated_episodes, indent=2) + "\n", encoding="utf-8")

    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    state.setdefault("last_seen", {})[show_name] = video_id
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    print(f"Updated leaderboard ({len(updated_episodes)} episodes) and state for {show_name}.")


if __name__ == "__main__":
    main()

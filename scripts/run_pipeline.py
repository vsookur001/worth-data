#!/usr/bin/env python3
"""
run_pipeline.py

The daily orchestrator. Called by .github/workflows/daily.yml. For each
channel:
  1. check for a new episode
  2. fetch its transcript
  3. score it via Claude (using the real WORTH project files)
  4. publish the card to Ghost
  5. update the leaderboard JSON + state.json
  6. send a notification email if it scores above NOTIFY_THRESHOLD

Failures on one episode are logged and skipped (not retried within the same
run) so one bad transcript doesn't block the other four channels. The
episode's state.json entry is only updated on full success, so a failed
episode will be retried on the next day's run.

Usage:
    python scripts/run_pipeline.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Windows' default console encoding (cp1252) can't print many characters that
# show up routinely in YouTube titles/transcripts (curly quotes, em-dashes,
# math symbols like U+2260). Reconfigure this process's own stdout/stderr to
# UTF-8 so print() never crashes on them. No-op on systems where this isn't
# needed (Python <3.7 lacks reconfigure, but 3.7+ is required anyway).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

NOTIFY_THRESHOLD = float(os.environ.get("NOTIFY_THRESHOLD", "3.7"))


def run(cmd: list, **kwargs) -> str:
    # Force UTF-8 for both this process's own stdout/stderr handling AND the
    # child process's environment -- without this, Windows' default console
    # encoding (cp1252) crashes on characters like '\u2260' (-- "not equal")
    # that show up routinely in YouTube transcripts.
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, **kwargs
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout


def write_temp(data) -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    if isinstance(data, str):
        f.write(data)
    else:
        json.dump(data, f, ensure_ascii=False)
    f.close()
    return Path(f.name)


def process_episode(episode: dict):
    show = episode["show"]
    video_id = episode["video_id"]
    print(f"--- Processing {show}: {episode['title']} ({video_id}) ---")

    # 1. Transcript
    transcript_raw = run([sys.executable, str(SCRIPTS / "get_transcript.py"), video_id])
    transcript = json.loads(transcript_raw)

    # 2. Score
    episode_path = write_temp(episode)
    transcript_path = write_temp(transcript)
    # worth-episodes.json lives at the REPO ROOT (not data/) to match exactly
    # where the live Ghost leaderboard's DATA_URL points on GitHub.
    current_episodes_text = (ROOT / "worth-episodes.json").read_text(encoding="utf-8")
    current_path = write_temp(current_episodes_text)

    score_raw = run(
        [
            sys.executable,
            str(SCRIPTS / "score_episode.py"),
            str(episode_path),
            str(transcript_path),
            str(current_path),
        ]
    )
    score_result = json.loads(score_raw)
    updated_episodes = score_result["updated_episodes"]
    html_card = score_result["html_card"]
    new_episode_record = updated_episodes[-1]  # the one just appended

    # 3. Publish to Ghost -- pass the scored record (has verdict/category),
    # not the original header-only episode_path, so tags are populated correctly.
    record_for_publish_path = write_temp(new_episode_record)
    html_path = write_temp(html_card if isinstance(html_card, str) else json.dumps(html_card))
    html_path.write_text(html_card, encoding="utf-8")
    try:
        ghost_raw = run(
            [
                sys.executable,
                str(SCRIPTS / "publish_to_ghost.py"),
                str(record_for_publish_path),
                str(html_path),
            ]
        )
        ghost_result = json.loads(ghost_raw)
        new_episode_record["ghost_url"] = ghost_result.get("ghost_url")
    except RuntimeError as e:
        print(f"WARNING: Ghost publish failed, continuing without it: {e}", file=sys.stderr)
        # Still update the leaderboard JSON even if Ghost is down/trial expired --
        # the scoring data isn't lost, just the standalone post.

    # 4. Update leaderboard + state
    updated_path = write_temp(updated_episodes)
    run(
        [
            sys.executable,
            str(SCRIPTS / "update_leaderboard.py"),
            str(updated_path),
            show,
            video_id,
        ]
    )

    # 5. Notify if above threshold
    record_path = write_temp(new_episode_record)
    try:
        run(
            [
                sys.executable,
                str(SCRIPTS / "notify.py"),
                str(record_path),
                "--threshold",
                str(NOTIFY_THRESHOLD),
            ]
        )
    except RuntimeError as e:
        print(f"WARNING: notification step failed (non-fatal): {e}", file=sys.stderr)

    print(f"--- Done: {show} -> {new_episode_record.get('verdict')} "
          f"({new_episode_record.get('composite')}/5) ---")


def main():
    new_episodes_raw = run([sys.executable, str(SCRIPTS / "check_new_episodes.py")])
    lines = [l for l in new_episodes_raw.strip().splitlines() if l.strip()]

    if not lines:
        print("No new episodes found.")
        return

    failures = []
    for line in lines:
        episode = json.loads(line)
        try:
            process_episode(episode)
        except Exception as e:
            print(f"ERROR processing {episode['show']} ({episode['video_id']}): {e}", file=sys.stderr)
            failures.append(episode)

    if failures:
        print(f"\n{len(failures)} episode(s) failed and will be retried next run:", file=sys.stderr)
        for f in failures:
            print(f"  - {f['show']}: {f['title']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

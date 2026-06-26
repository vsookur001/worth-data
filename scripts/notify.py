#!/usr/bin/env python3
"""
notify.py

Sends an email via Resend if the episode's composite score meets or exceeds
a threshold. Designed to be called once per scored episode; the threshold
check happens here so the caller doesn't need its own logic.

Usage:
    python scripts/notify.py episode_with_score.json --threshold 3.7

Requires env vars:
    RESEND_API_KEY
    NOTIFY_FROM_EMAIL    e.g. worth@yourdomain.com (must be a verified Resend domain)
    NOTIFY_TO_EMAIL      your personal email
"""
import json
import os
import sys
from pathlib import Path
import urllib.request

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
FROM_EMAIL = os.environ.get("NOTIFY_FROM_EMAIL")
TO_EMAIL = os.environ.get("NOTIFY_TO_EMAIL")


def send_email(subject: str, html_body: str):
    if not (RESEND_API_KEY and FROM_EMAIL and TO_EMAIL):
        print(
            "Notification skipped: RESEND_API_KEY / NOTIFY_FROM_EMAIL / NOTIFY_TO_EMAIL not all set.",
            file=sys.stderr,
        )
        return

    body = json.dumps(
        {"from": FROM_EMAIL, "to": [TO_EMAIL], "subject": subject, "html": html_body}
    ).encode()

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {RESEND_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def main():
    if len(sys.argv) < 3 or sys.argv[2] != "--threshold":
        sys.exit("Usage: notify.py episode.json --threshold 3.7")

    episode = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    threshold = float(sys.argv[3])

    composite = episode.get("composite", 0)
    if composite < threshold:
        print(f"Composite {composite} below threshold {threshold} -- no notification sent.")
        return

    subject = f"[WORTH] {episode['verdict']} ({composite}/5): {episode['show']}"
    body = f"""
    <p><b>{episode['show']}</b> &mdash; {episode['title']}</p>
    <p>Verdict: <b>{episode['verdict']}</b> &middot; Composite: <b>{composite}/5</b></p>
    <p>{episode.get('summary', '')}</p>
    <p><a href="{episode.get('ghost_url', episode.get('youtube_url'))}">Read the full verdict</a></p>
    """
    send_email(subject, body)
    print(f"Sent notification for {episode['show']} (composite {composite}).")


if __name__ == "__main__":
    main()

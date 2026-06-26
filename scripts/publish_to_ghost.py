#!/usr/bin/env python3
"""
publish_to_ghost.py

Creates a published Ghost post containing the filled WORTH verdict card HTML.

Ghost's Admin API needs a short-lived JWT signed with the Admin API key
(format: "{id}:{secret}", secret is hex-encoded). No extra library required --
implemented by hand below since it's ~10 lines.

Usage:
    python scripts/publish_to_ghost.py episode.json html_card.html

Requires env vars:
    GHOST_API_URL        e.g. https://yoursite.ghost.io  (no trailing slash)
    GHOST_ADMIN_API_KEY   the "id:secret" string from Settings -> Integrations
"""
import base64
import json
import os
import sys
import time
from pathlib import Path
import urllib.request
import urllib.error
import hmac
import hashlib

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

API_URL = None
ADMIN_KEY = None


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_jwt(key_id: str, secret_hex: str) -> str:
    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    now = int(time.time())
    payload = {"iat": now, "exp": now + 5 * 60, "aud": "/admin/"}  # 5 min max per Ghost's docs

    header_b64 = b64url(json.dumps(header).encode())
    payload_b64 = b64url(json.dumps(payload).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()

    secret = bytes.fromhex(secret_hex)
    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    signature_b64 = b64url(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def create_post(title: str, html: str, tags: list) -> dict:
    key_id, secret_hex = ADMIN_KEY.split(":")
    token = make_jwt(key_id, secret_hex)

    # Per Ghost's docs, plain HTML->Lexical conversion is lossy. Wrapping in
    # these comment markers makes Ghost preserve the HTML verbatim as a single
    # HTML card -- important here since the WORTH card depends on exact inline
    # styles and shared CSS classes (.wcard, .wrow, .tip) that a lossy
    # re-interpretation could easily mangle.
    wrapped_html = f"<!--kg-card-begin: html-->\n{html}\n<!--kg-card-end: html-->"

    body = json.dumps(
        {
            "posts": [
                {
                    "title": title,
                    "html": wrapped_html,
                    "status": "published",
                    "tags": tags,  # short form: plain strings, Ghost creates missing tags automatically
                }
            ]
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{API_URL}/ghost/api/admin/posts/?source=html",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Ghost {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        # Ghost's error body explains *why* (e.g. bad tag, missing field) --
        # surfacing it is the difference between "422 Unknown Error" and an
        # actually actionable message.
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ghost API returned {e.code}: {error_body}") from e


def main():
    global API_URL, ADMIN_KEY
    API_URL = os.environ.get("GHOST_API_URL")
    ADMIN_KEY = os.environ.get("GHOST_ADMIN_API_KEY")
    if not API_URL or not ADMIN_KEY:
        sys.exit("GHOST_API_URL and GHOST_ADMIN_API_KEY environment variables are required.")

    if len(sys.argv) != 3:
        sys.exit("Usage: publish_to_ghost.py episode.json html_card.html")

    episode = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    html = Path(sys.argv[2]).read_text(encoding="utf-8")

    title = f"{episode['show']}: {episode['title']}"
    tags = ["WORTH", episode.get("category", "business"), episode.get("verdict", "")]

    result = create_post(title, html, tags)
    post = result["posts"][0]
    print(json.dumps({"ghost_url": post.get("url"), "ghost_id": post.get("id")}))


if __name__ == "__main__":
    main()

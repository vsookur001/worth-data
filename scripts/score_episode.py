#!/usr/bin/env python3
"""
score_episode.py

Scores one episode by calling the Claude API with the SAME instructions,
rubric, and HTML template files used by your manual "WORTH Scoring" Claude
Project (prompts/WORTH-project-instructions.md, WORTH-scoring-guide.md,
WORTH-verdict-card-full.html) -- copied verbatim, not reconstructed, so this
script can never drift from what you'd get scoring by hand in the Project.

IMPORTANT: if you edit the rubric or template inside your Claude Project,
copy the updated files into prompts/ here too, or this script will score
against a stale version. There is intentionally no other copy of the rubric
anywhere in this codebase -- prompts/ is the only place it lives, matching
the "canonical file set" rule in WORTH-scoring-guide.md itself.

ONE DELIBERATE DEVIATION from WORTH-project-instructions.md, for cost reasons:
the instructions describe a chat workflow where the user pastes the FULL
worth-episodes.json every session and Claude returns the full updated array
back. This script instead sends only the existing episode_keys (for collision
-avoidance) and asks for just the new episode object, then appends it locally
in Python. Scoring a new episode never actually depends on old episodes'
content, so re-sending the whole growing file on every call was pure waste
that scales worse the longer this runs. This override lives in the user
message (see main()), NOT in the copied instructions file itself -- the
canonical Project instructions are left untouched so they stay identical to
what you'd see scoring by hand in chat; only this script's calling convention
differs.

Usage:
    python scripts/score_episode.py episode.json transcript.json current_worth_episodes.json
    # prints JSON: {"updated_episodes": [...], "html_card": "..."}

Requires env var ANTHROPIC_API_KEY.
"""
import json
import os
import re
import sys
from pathlib import Path
import urllib.request

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"

API_KEY = None
MODEL = "claude-sonnet-4-6"


def build_system_prompt() -> str:
    """
    Assembles the system prompt exactly the way the Claude Project is set up:
    project instructions + the two knowledge files it points to, concatenated.
    """
    instructions = (PROMPTS / "WORTH-project-instructions.md").read_text(encoding="utf-8")
    rubric = (PROMPTS / "WORTH-scoring-guide.md").read_text(encoding="utf-8")
    card_template = (PROMPTS / "WORTH-verdict-card-full.html").read_text(encoding="utf-8")

    return (
        f"{instructions}\n\n"
        f"---\n\n"
        f"# Project knowledge file: WORTH-scoring-guide.md\n\n{rubric}\n\n"
        f"---\n\n"
        f"# Project knowledge file: WORTH-verdict-card-full.html\n\n{card_template}\n"
    )


def call_claude(system_prompt: str, user_message: str) -> str:
    body = json.dumps(
        {
            "model": MODEL,
            # Long episodes (Acquired runs 3-4 hours) plus a growing
            # worth-episodes.json array plus a verbose HTML card can need a
            # lot of output. 8000 was too low and caused silent truncation
            # mid-response -- raised well above what even a large leaderboard
            # + long transcript should need.
            "max_tokens": 16000,
            # The system prompt (rubric + instructions + card template) is
            # IDENTICAL on every single call, every day, forever -- it's the
            # ~10k-token canonical WORTH ruleset, never user-specific content.
            # Caching it means the 1st episode of the day pays a 25% premium
            # to write the cache, then every subsequent episode that same run
            # reads it at 10% of normal cost instead of 100%. 1-hour TTL (not
            # the 5-minute default) so the cache survives the slower steps
            # (transcript fetch, Ghost publish) between episodes in one run.
            "system": [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral", "ttl": "1h"},
                }
            ],
            "messages": [{"role": "user", "content": user_message}],
        }
    ).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)

    if data.get("stop_reason") == "max_tokens":
        # The response was cut off before finishing -- this is the #1 cause of
        # "could not find html block" errors, and it's silent unless we check
        # this field explicitly.
        raise RuntimeError(
            "Claude's response was truncated (hit max_tokens before finishing). "
            "This usually means the episode/transcript is unusually long, or "
            "worth-episodes.json has grown large. Increase max_tokens in "
            "score_episode.py or consider trimming older episodes' verbosity."
        )

    # Surface cache performance so cost is visible/debuggable, not a black box.
    usage = data.get("usage", {})
    cache_read = usage.get("cache_read_input_tokens", 0)
    cache_write = usage.get("cache_creation_input_tokens", 0)
    if cache_read or cache_write:
        print(
            f"  [cache] read={cache_read} tok, write={cache_write} tok "
            f"(read = ~90% cheaper than normal input)",
            file=sys.stderr,
        )

    text_blocks = [b["text"] for b in data["content"] if b["type"] == "text"]
    return "\n".join(text_blocks)


def extract_blocks(response_text: str):
    """
    Block 1 - the NEW episode as a single JSON object (we append it locally;
              see the note in main() about why we no longer ask Claude to
              return/manage the full array).
    Block 2 - a ```html fenced code block (the filled card)
    Pull both out robustly rather than assuming exact formatting.
    """
    preview = response_text[-1500:] if len(response_text) > 1500 else response_text

    html_match = re.search(r"```html\s*(.*?)```", response_text, re.DOTALL)
    if not html_match:
        raise RuntimeError(
            "Could not find ```html block in model response. "
            f"Last 1500 chars of what Claude actually returned:\n{preview}"
        )
    html_card = html_match.group(1).strip()

    before_html = response_text[: html_match.start()]

    # Try the array form first ([...]) since it's unambiguous about its own
    # boundaries (matching brackets, not braces-which-could-be-nested), then
    # fall back to a bare object ({...}). Trying array-first avoids a bare
    # multi-item array like "[{...}, {...}]" being mis-parsed as a single
    # object via a greedy {.*} match across both items.
    parsed = None
    array_match = re.search(r"\[\s*\{.*\}\s*\]", before_html, re.DOTALL)
    if array_match:
        try:
            parsed = json.loads(array_match.group(0))
        except json.JSONDecodeError:
            parsed = None

    if parsed is None:
        obj_match = re.search(r"\{.*\}", before_html, re.DOTALL)
        if not obj_match:
            raise RuntimeError(
                "Could not find a JSON object (Block 1) in model response. "
                f"Text before the html block was:\n{before_html[-1500:]}"
            )
        try:
            parsed = json.loads(obj_match.group(0))
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Block 1 was not valid JSON: {e}\n"
                f"Near: {obj_match.group(0)[max(0, e.pos - 200):e.pos + 200]}"
            )

    if isinstance(parsed, list):
        if len(parsed) != 1:
            raise RuntimeError(
                f"Expected exactly one new episode object, got a list of {len(parsed)}. "
                "Block 1 should be just the new episode now, not the full history."
            )
        new_episode_record = parsed[0]
    else:
        new_episode_record = parsed

    return new_episode_record, html_card


def main():
    global API_KEY
    API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    if not API_KEY:
        sys.exit("ANTHROPIC_API_KEY environment variable is required.")

    if len(sys.argv) != 4:
        sys.exit(
            "Usage: score_episode.py episode_header.json transcript.json current_worth_episodes.json"
        )

    episode = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    transcript = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    current_episodes_raw = Path(sys.argv[3]).read_text(encoding="utf-8")
    current_episodes = json.loads(current_episodes_raw)

    system_prompt = build_system_prompt()

    # IMPORTANT: we do NOT send the full worth-episodes.json history to Claude.
    # Scoring a new episode never depends on the content of old ones -- the
    # rubric anchors live in WORTH-scoring-guide.md, not in past scores. The
    # only thing Block 1's "append, don't reorder/edit" contract actually
    # needs from us is (a) how many episodes already exist and (b) their
    # episode_keys, so the new one doesn't collide. Sending the full file
    # re-bills every old episode's tokens on every future call -- harmless
    # today at 4 episodes, but it scales linearly forever if left unfixed.
    # update_leaderboard.py (not Claude) does the actual append to the real
    # file, so this can never cause data loss even though Claude never sees
    # the old entries.
    existing_keys = [e.get("episode_key", "") for e in current_episodes]
    existing_categories = sorted(set(e.get("category", "") for e in current_episodes if e.get("category")))
    episode_count = len(current_episodes)

    user_message = (
        f"NOTE ON THIS SESSION'S WORKFLOW (overrides the 'paste the full "
        f"worth-episodes.json' framing in the instructions above -- this is "
        f"an automated script, not a chat paste; the calling script handles "
        f"the file append itself):\n"
        f"There are currently {episode_count} episodes already scored. Their "
        f"episode_keys (so the new one doesn't collide -- you have NOT seen "
        f"their other fields and must not reference or reproduce them): "
        f"{json.dumps(existing_keys)}\n"
        f"Categories already in use across existing episodes: "
        f"{json.dumps(existing_categories) if existing_categories else '(none yet)'}\n\n"
        f"For Block 1, return ONLY the single new episode object below (a bare "
        f"JSON object, not wrapped in an array, not the full episode list) "
        f"with all the fields the instructions specify. Block 2 is unchanged "
        f"from the normal contract.\n\n"
        f"New episode to score:\n"
        f"Show: {episode['show']}\n"
        f"Episode title: {episode['title']}\n"
        f"Channel's usual category (a DEFAULT, not a fixed value): {episode['category']}\n"
        f"  -- This show is generally about that topic, but judge THIS episode "
        f"on its own content per the instructions' 'category matches what the "
        f"episode is actually about' rule. If this specific episode is mainly "
        f"about something else (e.g. a business show's guest episode that's "
        f"really about health, or personal finance, or relationships), use "
        f"the category that actually fits, preferring an existing category "
        f"above if one genuinely matches rather than inventing a near-duplicate "
        f"(e.g. don't create 'finance' if 'personal finance' already exists "
        f"and means the same thing).\n"
        f"Published date: {episode['published_at'][:10]}\n"
        f"YouTube URL: {episode['youtube_url']}\n"
        f"Sponsor noticed: {episode.get('sponsor_noticed', 'none noted -- check transcript yourself')}\n\n"
        f"Transcript (timestamped):\n{transcript['text']}\n"
    )

    response_text = call_claude(system_prompt, user_message)
    new_episode_record, html_card = extract_blocks(response_text)

    # Reassemble the full array locally -- Claude only ever saw/returned the
    # single new record, so the append happens here instead of by the model.
    updated_episodes = current_episodes + [new_episode_record]

    print(json.dumps({"updated_episodes": updated_episodes, "html_card": html_card}))


if __name__ == "__main__":
    main()

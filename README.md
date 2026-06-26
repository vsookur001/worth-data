# Podcast Worth-Rating Pipeline

Automated daily pipeline that checks 5 YouTube business podcasts for new episodes,
scores them using your "Invest / Entertain / Skip / Actively Misleading" rubric via
the Claude API, publishes a card to Ghost, updates the leaderboard JSON on GitHub,
and (optionally) emails you when something scores above a threshold.

## ⚠️ READ THIS FIRST — repo merge

Earlier versions of this pipeline wrote to `data/worth-episodes.json` in whatever
repo you happened to push the pipeline code to. **That was never the repo your
live Ghost leaderboard actually reads from.** Your leaderboard's `DATA_URL` points
at:
```
https://raw.githubusercontent.com/vsookur001/worth-data/refs/heads/main/worth-episodes.json
```
So this version is restructured to match that exactly:
- `worth-episodes.json` now lives at the **repo root** (not `data/`)
- Everything in this folder (scripts, prompts, channels.json, state.json) should
  be pushed INTO your existing `worth-data` repo, alongside the `worth-episodes.json`
  you already have there with your 2 hand-scored episodes
- **I've already merged your existing 2 hand-scored episodes AND the 4 episodes from
  our earlier pipeline test runs into this version's `worth-episodes.json`** — 5
  episodes total. One duplicate was found and resolved: your hand-scored "Grantham
  crash warning" episode and the pipeline's "Billionaire's WARNING..." episode were
  the same YouTube video scored twice (2.9 vs 3.3 composite) — per your instruction,
  the hand-scored version was dropped and the pipeline-scored version (3.3,
  Entertain) was kept.
- `data/state.json` has been updated to mark all 4 pipeline-tested videos as
  already-processed, so the automation won't try to re-score them on its first
  real run.

**What you need to do:**
1. Unzip this folder
2. Push its entire contents into your `worth-data` repo (overwriting the old
   `worth-episodes.json` there with this folder's version, which has both your
   old 2 episodes AND is ready to receive new ones)
3. If you're not comfortable with git commands, the simplest path is: go to
   github.com/vsookur001/worth-data in your browser, delete the old files, and
   use GitHub's "Add file → Upload files" button to drag this whole folder's
   contents in. I can walk through this step by step if useful.
4. Continue to the GitHub Actions setup below to make it run automatically



```
GitHub Actions (cron, daily)
  -> check_new_episodes.py   (YouTube Data API, compares against data/state.json)
  -> get_transcript.py       (youtube-transcript-api)
  -> score_episode.py        (Claude API, your rubric as system prompt -> strict JSON)
  -> publish_to_ghost.py     (Ghost Admin API -> creates post from card template)
  -> update_leaderboard.py   (appends entry to worth-episodes.json at repo ROOT, commits)
  -> notify.py               (Resend email if composite >= threshold)
```

## Channels (resolved handles, IDs not yet looked up)

| Show | Handle | Notes |
|---|---|---|
| The Diary of a CEO | `@TheDiaryOfACEO` | Twice-weekly, ~60-90 min |
| Acquired | `@AcquiredFM` | **Irregular** (monthly-ish), episodes run **3-4 hours**. See cost note below. |
| My First Million | `@MyFirstMillionPod` | ~2-3x/week, ~45-75 min |
| All-In Podcast | `@allin` | Weekly. Hosts have direct political/financial entanglements — expect this show to trip the **Independence gate** more than the others. |
| The Game w/ Alex Hormozi | `@AlexHormozi` | **Same channel also posts Shorts, Q&As, and non-podcast clips.** Filtered by a 15-minute minimum duration (see below). |

I confirmed all 5 handles exist and are correct via web search, but resolving a handle to the numeric `channel_id` the YouTube Data API actually needs requires an API call I can't make without your key — `data/channels.json` has `channel_id: null` for all five. Running `scripts/resolve_channels.py` once (30 seconds) fills these in automatically; see Quickstart below.

## Quickstart

1. Get a YouTube Data API key (Google Cloud Console → enable "YouTube Data API v3").
2. `export YOUTUBE_API_KEY=...` then `python scripts/resolve_channels.py` — fills in the channel IDs in `data/channels.json`.
3. Get your other keys (Anthropic, Ghost Admin, Resend) — see setup section below.
4. Run once manually end-to-end before trusting the cron job:
   ```
   export YOUTUBE_API_KEY=... ANTHROPIC_API_KEY=... GHOST_API_URL=... GHOST_ADMIN_API_KEY=...
   python scripts/run_pipeline.py
   ```
5. Check the output — did it find episodes, score them sensibly, post to Ghost, update `worth-episodes.json` at the repo root? Once you're confident, add the same keys as GitHub Actions secrets and let the daily cron take over.

## Making it run automatically (GitHub Actions setup)

Once the merged repo is pushed and you've confirmed a manual run works:

1. In your `worth-data` repo on GitHub, go to **Settings → Secrets and variables → Actions**
2. Click **"New repository secret"** and add each of these one at a time (same values you've been using with `set` locally):
   - `YOUTUBE_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `GHOST_API_URL`
   - `GHOST_ADMIN_API_KEY`
   - `RESEND_API_KEY` (only if you want the email notifications)
   - `NOTIFY_FROM_EMAIL` / `NOTIFY_TO_EMAIL` (only if using Resend)
3. That's it — `.github/workflows/daily.yml` is already in this folder and will be picked up automatically once pushed. It's set to run at 6am UTC daily; edit the `cron:` line in that file if you want a different time.
4. To test it without waiting for tomorrow: go to your repo's **Actions** tab, click on "WORTH daily pipeline" in the left sidebar, then **"Run workflow"** (this is the `workflow_dispatch` trigger already built in) — this runs it immediately so you can watch it work and check the logs.
5. Each run's logs show up under the Actions tab — useful for checking what happened on days you weren't watching, including any episodes that failed and will retry the next day.

## One-time setup

1. **YouTube Data API key** — free, from Google Cloud Console (enable "YouTube Data API v3"). Quota cost for this pipeline: ~5-10 units/day against a 10,000/day free quota — trivial.
2. **Anthropic API key** — for the scoring step.
3. **Ghost Admin API key** — Settings → Integrations → "Add custom integration" → copy the Admin API Key (works on your 14-day trial; it's not gated behind a paid plan, but **note your trial clock**: if you don't convert before day 14, the site and its API access go away. Decide before building further whether to start the trial now or wait until you're ready to commit).
4. **Resend API key** (optional, for the >3.7 email) — free tier covers this volume easily.
5. Store all four as **GitHub Actions repository secrets**: `YOUTUBE_API_KEY`, `ANTHROPIC_API_KEY`, `GHOST_ADMIN_API_KEY`, `GHOST_API_URL`, `RESEND_API_KEY`.

## Open design decisions (flagging, not deciding for you)

- **Acquired's 3-4 hour transcripts**: a full transcript can run 40-60k+ words. That's fine for Claude's context window, but (a) it costs meaningfully more per scoring call than a 20-minute clip, and (b) Acquired publishes so infrequently that the daily check will almost always find "nothing new" for this channel. No action needed, just don't be surprised by the occasional bigger API bill on Acquired weeks.
- **Hormozi channel filter**: `check_new_episodes.py` currently filters his uploads to videos over **15 minutes** as a crude proxy for "this is a podcast episode, not a Short or a 3-minute clip." You may want to tighten this — happy to adjust once you see a week of real data.
- **Ghost trial**: everything here works against the trial. If you let the trial lapse, `publish_to_ghost.py` will start failing (auth error) — the rest of the pipeline (scoring + leaderboard JSON) still works independently, so nothing is lost, but posts won't appear on the site until you re-subscribe.

## Files

- `scripts/check_new_episodes.py` — polls each channel's uploads playlist, diffs against `data/state.json`
- `scripts/get_transcript.py` — pulls captions for a given video ID
- `scripts/score_episode.py` — sends transcript + your **actual** rubric files to Claude, returns structured JSON + HTML card
- `scripts/publish_to_ghost.py` — creates a Ghost post from the HTML card
- `scripts/update_leaderboard.py` — appends to `worth-episodes.json` **at the repo root** (matching your live leaderboard's fetch URL), refuses to write if the file would shrink (corruption guard)
- `scripts/notify.py` — sends threshold-triggered email via Resend
- `scripts/run_pipeline.py` — orchestrates the above for all 5 channels; this is what the GitHub Action calls
- `scripts/resolve_channels.py` — one-time setup script: fills in `channel_id`/`uploads_playlist_id` in `data/channels.json` from the @handles
- `prompts/WORTH-scoring-guide.md`, `WORTH-project-instructions.md`, `WORTH-verdict-card-full.html` — **exact copies of the files you uploaded**, not reconstructions. `score_episode.py` concatenates these into the system prompt, so the automated scoring uses precisely the same rubric, weights, gate logic, and card template as your manual Scoring Project. **If you ever edit the rubric or card inside the Claude Project, copy the updated files here too** — there is intentionally no second copy of the rubric logic anywhere else in this codebase.
- `data/channels.json` — the 5 resolved channels + per-channel filters/notes
- `data/state.json` — last-seen video ID per channel (the idempotency guard; only updated after a full success)
- `worth-episodes.json` — **at the repo root.** The running leaderboard data — seeded with your 2 existing hand-scored episodes (Rubin hormones, Grantham crash warning), ready for the pipeline to append to
- `.github/workflows/daily.yml` — the cron job

## Per-episode category (not fixed per-show)

`data/channels.json` has a `default_category` per channel (currently "business" for all 5) — but that's a *starting suggestion*, not a hard assignment. `score_episode.py` tells Claude what the channel's usual topic is, then explicitly asks it to override that based on what the specific episode actually covers (e.g. a business show's guest episode that's really about health, or personal finance), preferring to reuse an existing category already in your data over inventing a near-duplicate name. This matches what your real `WORTH-project-instructions.md` already specifies — category was always meant to be per-episode, this just wires the automation to actually use that.

**Leaderboard side:** the leaderboard widget already builds its category filter buttons dynamically from whatever categories exist in `worth-episodes.json` (built in an earlier session) — so a new category from a scored episode just appears as a new filter button automatically. No leaderboard changes needed for this.

## Cost optimizations (added after the first real test run)

Your first manual run cost ~$3.64 for 4 episodes (one of them Acquired's 3.5-hour transcript). Two no-tradeoff changes are now in place:

1. **Prompt caching on the system prompt.** The ~10k-token rubric/instructions/template is identical on every call, so it's now sent with a cache marker (1-hour TTL). The first episode scored in a run pays a small premium to write the cache; every episode after that in the same run reads it back at ~10% of normal cost instead of 100%. You'll see `[cache] read=... write=...` lines in the output confirming this is working.
2. **No more re-sending the full leaderboard history.** `score_episode.py` used to send your entire `worth-episodes.json` to Claude on every call, which doesn't actually help scoring (the rubric anchors live in the guide file, not in old scores) and would have gotten linearly more expensive every month as the leaderboard grows. Now it only sends the existing episode IDs (to avoid duplicates) and appends the new episode locally in Python.

**What this does NOT fix:** long transcripts (Acquired especially) are still the real cost driver, and there's no safe way to shrink those without risking the rubric missing things it's supposed to catch (filler, unsourced claims, etc). That cost is the genuine cost of scoring long content carefully.

**Note for the canonical Project files:** `prompts/WORTH-project-instructions.md` is left completely untouched — it still describes the "paste the full JSON" chat workflow, exactly as it exists in your real Claude Project. The override to "send only IDs, return only the new episode" lives entirely in `score_episode.py`'s own message to Claude, not in the instructions file, so the canonical files never drift from what you'd see scoring by hand.

## What's been tested vs. what hasn't

I ran the JSON/Python logic I could verify in a sandbox without your live API keys:
- ✅ All scripts compile and import cleanly
- ✅ ISO 8601 duration parsing (for the Hormozi Shorts/clips filter) — tested against several cases
- ✅ JWT generation for Ghost auth — produces a well-formed 3-part token
- ✅ The Block 1/Block 2 response parser (`extract_blocks`) — tested against a realistic fake Claude response
- ✅ The leaderboard's "never shrink the file" safety guard — confirmed it blocks a corrupting write and leaves the file untouched, and confirmed normal growth still works

What I **couldn't** test without your actual keys: the live YouTube API calls, an actual Claude scoring call against the real rubric, a real Ghost post creation, and a real Resend email. Recommend running `run_pipeline.py` manually once (not via cron) after setup, and checking each step's output before turning on the daily schedule.

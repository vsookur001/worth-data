# WORTH — Rubric Scoring Guide & Scoring Prompt
### Phase 0: a manual time-triage tool for one user (you)

> **Canonical file set — these five must always travel together and stay in sync:**
> 1. **This file** (`WORTH-scoring-guide.md`) — the rubric and verdict logic. Single source of truth for the anchors, weights, and cutoffs.
> 2. **`WORTH-project-instructions.md`** — the Claude Project's system instructions. Defines the 2-block output contract (updated worth-episodes.json · HTML card) and points to files 1, 3, and 5 by name. If you ever rename a file, update the references here.
> 3. **`WORTH-verdict-card-full.html`** — the only card template. Uses shared CSS classes (`.wcard`, `.wrow`, `.tip`, etc.) injected site-wide in Ghost, **not** inline styles — so it depends on Code Injection being set up (Settings → Code Injection → Site Header for CSS, Site Footer for the leaderboard toggle JS).
> 4. **The leaderboard row snippet** (the collapsed `<button class="lb-summary">` + hidden `<div class="lb-detail">`) — saved as a Ghost snippet; a verdict card nests inside the `lb-detail` div for each leaderboard entry.
> 5. **`worth-episodes.json`** — the single source of truth for all scored episode data, hosted on GitHub and fetched live by the leaderboard page. **There is no tracking sheet** — this file is it. Because the Scoring Project has no memory between sessions, you must paste the current version of this file into the Project at the start of every scoring session; the Project then returns the whole file back, with the new episode appended, ready to paste over the GitHub file in full.
>
> Any file named `WORTH-verdict-card.html` (without "-full") is an **outdated** version (5 generic `{{D#}}` slots, inline styles, gate caps at Entertain, no Independence row). Delete it from the Project — the instructions explicitly tell the model to ignore it and flag it if found, but it's safer not to have it there at all.
>
> This guide's prompt below is the standalone version (2 blocks: readable summary + HTML), for use outside the Project — e.g. a one-off score in a fresh Claude chat, or to sanity-check an episode without touching the live data file. Inside the Scoring Project itself, `WORTH-project-instructions.md` governs and its Block 1 is the full updated JSON array, not a readable summary. The rubric, anchors, and verdict math are identical in both — only the output packaging differs.

The point of Phase 0 is not to build software. It's to find out whether a transparent, rubric-based verdict is trustworthy and useful — using yourself as the first user. So this guide is built to do one thing well: let you take an episode you were *already* considering, run it through a fixed rubric in Claude, and get back a verdict that tells you whether to spend the hours — and that you can paste straight onto the site.

Two rules keep Phase 0 honest:
1. **The anchors are written down before you score.** Vibes-based scoring tests nothing — it's just the listicles with extra steps. The 0–5 anchors below are what make the same episode get the same score twice.
2. **The platform is disposable; the scores are the product.** Scores are just text. Publish on WordPress/Ghost/Framer now, migrate later, lose nothing. Spend your energy on judgment, not tooling.

---

## The manual workflow (the loop)

1. **Pick an episode you'd genuinely consider watching/listening to.** Don't score random shows — score things competing for *your* real hours. That's the whole test.
2. **Grab the transcript and the inputs the template needs.** YouTube is best because its transcript carries **timestamps** (open the video → "Show transcript" → copy). Also note the canonical `watch?v=` URL and the start-times of 2–3 candidate "best minutes" — the prompt needs these to build clickable deep links. Spotify/Apple transcripts work but often lack clean timestamps, so prefer YouTube when you can.
3. **Open your Scoring Project, paste the current `worth-episodes.json` (copied fresh from GitHub) plus the new episode's transcript and header** (show, title, category, YouTube URL, any sponsor noticed). The Project always needs the current file — it has no memory of earlier sessions and must never guess at what's already scored.
4. **Read the verdict.** Sanity-check it against your gut — you're also calibrating the rubric here, not just the episode.
5. **Take the two outputs.** Block 1 is the entire updated JSON array (existing episodes untouched, new one appended) — select-all-replace the GitHub file with it and commit. Block 2 is the HTML card — paste it into a new Ghost draft (or directly where you're publishing it). Validate the JSON pasted cleanly (see the GitHub-editing note below) before moving to the next episode.

Time cost target: ~5 minutes per episode once you're in rhythm. The prompt does the analysis; you curate the inputs and gut-check the output.

> **GitHub-editing safety note.** Always select-all and fully replace the file's contents with Block 1's output — never hand-splice a new object into existing text in GitHub's editor. Partial edits (pasting over part of a line, leaving a stray bracket) are the most common way this breaks, and a broken JSON file silently takes down the *entire* live leaderboard, not just the new episode. After committing, do a hard refresh (Ctrl/Cmd+Shift+R) on the live leaderboard page itself to confirm it loads — that's a more reliable check than re-fetching the raw GitHub URL, which can appear to lag behind what's actually committed.

> Phase 0 scope discipline: don't build 50 separate pages first. Score ~20–30 episodes, publish **one** ranked leaderboard ("the business podcast episodes actually worth your time — scored, with the method shown") plus a handful of individual pages. One shareable, opinionated, transparent page tests the trust-and-share thesis faster than a sprawling site.

---

## The rubric

Six dimensions. Five are scored 0–5 and weighted into a composite. The sixth, **Independence**, is a **gate**, not a weighted input — a hidden conflict should be able to sink an otherwise-polished episode, so it caps the verdict rather than averaging in.

Score the **episode**, never the show's reputation. A great show has Skip episodes; a mediocre show has the occasional Invest. You're rating these specific hours.

### 1. Signal Density — *25%*
*Usable insight per minute. The core "is this worth my time" axis.*
- **5** — Nearly every segment carries a distinct, non-obvious idea. You couldn't cut 10% without losing something.
- **3** — Real substance, but diluted by anecdote, repetition, long setups, banter, or ads. You could lose ~40% with no loss.
- **1** — A few good moments buried in mostly chatter, self-promo, or rambling. 80%+ is skippable.
- **0** — No usable insight; pure filler, promo, or noise.

### 2. Epistemic Hygiene — *25%*
*How responsibly claims are made. The main defence against being misled.*
- **5** — Claims are sourced or clearly flagged as opinion/speculation; evidence is distinguished from anecdote; uncertainty is acknowledged; the strongest counter-arguments are actually engaged.
- **3** — A mix: some claims supported, others asserted confidently with no basis; occasional nods to limitations.
- **1** — Confident assertions throughout with little sourcing; anecdote treated as proof; disagreement ignored.
- **0** — Sweeping confident claims with zero basis; cherry-picked "evidence"; opponents strawmanned.

### 3. Credibility / Skin-in-the-Game — *15%*
*Standing of host & guest on THIS specific topic — not their fame.*
- **5** — Direct, relevant expertise or real operational/lived results in exactly what's being discussed.
- **3** — Adjacent or partial expertise; credible but stretching past their lane in places.
- **1** — Borrowed authority: famous or credentialed, but not in this domain; confident outside their competence.
- **0** — No relevant standing; pure influencer or salesperson.

### 4. Actionability — *15%*
*Can you do something with it. Scored, not penalized — pure-ideas content can still earn Invest on the other dimensions.*
- **5** — Concrete frameworks, steps, or decision criteria you could apply this week.
- **3** — Useful principles, but you'd have to do the work to operationalize them.
- **1** — Vague inspiration ("stay consistent, work hard").
- **0** — Nothing to act on (fine if it's openly entertainment).

### 5. Intellectual Honesty — *20%*
*Good-faith engagement vs. selling certainty.*
- **5** — Acknowledges trade-offs, complexity, and what they don't know; concedes/updates when challenged; never oversells.
- **3** — Mostly fair, with some overconfidence or convenient simplification.
- **1** — Sells certainty and simple answers; dodges inconvenient complexity; defensive under push-back.
- **0** — Manipulative: manufactured urgency, us-vs-them framing, conspiracy logic, a simple "cure."

### 6. Independence — *GATE (not weighted)*
*Freedom from undisclosed conflict.*
- **5** — No conflicts, or all disclosed clearly; not a disguised pitch.
- **3** — Minor undisclosed promotional lean, or disclosed-but-heavy sponsorship coloring the content.
- **1** — Significant **undisclosed** conflict: the episode steers toward something the speaker profits from.
- **0** — The whole episode is a covert sales pitch; the "advice" exists to sell the product.

---

## From scores to a verdict

**Composite** = (0.25 × Signal) + (0.25 × Epistemic) + (0.20 × Honesty) + (0.15 × Actionability) + (0.15 × Credibility). Result is 0.0–5.0.

Then apply the **Independence gate**, which can override the composite:
- Independence **4–5**: no effect.
- Independence **3**: note it; no cap.
- Independence **≤2**: cap the verdict at **SKIP** — and if Epistemic Hygiene is also ≤2 (confident claims serving the hidden interest), escalate to **ACTIVELY MISLEADING**.

**Verdict bands** (personal-time framing in italics):

- **INVEST** — composite ≥ 4.0, Epistemic ≥ 3, Independence ≥ 3. *Block out real time and take notes.*
- **ENTERTAIN** — composite 2.8–3.9, Independence ≥ 3, and honest about what it is. *Fine for a walk or the gym; don't mistake it for learning. Don't take notes.*
- **SKIP** — composite < 2.8, or capped there by Independence. *Don't spend the hours.*
- **⚠ ACTIVELY MISLEADING** — Independence ≤ 2 **and** Epistemic ≤ 2; or Epistemic ≤ 1 paired with confident sweeping claims. Overrides everything. *Avoid, and be wary of this source generally.*

---

## The Scoring Prompt (paste into a fresh Claude chat or your Scoring Project)

Copy everything between the lines, then paste the transcript underneath — plus the show name, episode title, and canonical YouTube URL.

> ──────────────────────────────────────────
>
> You are a strict, time-protective content evaluator. I will give you a podcast/video transcript plus its show name, episode title, and YouTube URL. Score it against the fixed rubric below and return ONLY the two output blocks at the end — nothing else, no commentary before or after.
>
> **Be a harsh grader.** Most content is mediocre. INVEST should be rare (roughly 1 in 6). If you find yourself wanting to give Invest, look harder for filler and unsourced claims first. Score the EPISODE in front of you, not the reputation of the show or host. Do not be charitable; do not fill in unstated context that makes the episode look better than the transcript supports.
>
> **Dimensions** (score each 0–5 using these anchors):
> 1. **Signal Density** — usable insight per minute. 5 = couldn't cut 10%; 3 = could cut ~40% (anecdote/repetition/ads); 1 = 80%+ skippable; 0 = pure filler.
> 2. **Epistemic Hygiene** — how responsibly claims are made. 5 = sourced or flagged as opinion, evidence ≠ anecdote, uncertainty acknowledged, counter-arguments engaged; 3 = mixed; 1 = confident & unsourced, anecdote-as-proof; 0 = sweeping claims, zero basis, strawmans.
> 3. **Credibility / Skin-in-the-Game** — standing on THIS topic, not fame. 5 = direct relevant expertise/results; 3 = adjacent/partial; 1 = borrowed authority outside their lane; 0 = none.
> 4. **Actionability** — can the listener act on it. 5 = concrete steps/frameworks; 3 = principles needing work; 1 = vague inspiration; 0 = nothing to act on.
> 5. **Intellectual Honesty** — 5 = acknowledges trade-offs/unknowns, updates when challenged; 3 = some overconfidence; 1 = sells certainty, dodges complexity; 0 = manipulative (urgency, us-vs-them, simple cure).
> 6. **Independence** (GATE) — 5 = no/disclosed conflicts; 3 = minor or heavy-but-disclosed promo; 1 = significant UNDISCLOSED conflict steering to something they profit from; 0 = covert sales pitch.
>
> **Composite** = 0.25·Signal + 0.25·Epistemic + 0.20·Honesty + 0.15·Actionability + 0.15·Credibility.
>
> **Independence gate (overrides composite):** if Independence ≤ 2 → cap at SKIP; if also Epistemic ≤ 2 → ACTIVELY MISLEADING. Otherwise no cap.
>
> **Verdict bands:** INVEST = composite ≥ 4.0 AND Epistemic ≥ 3 AND Independence ≥ 3. ENTERTAIN = composite 2.8–3.9, Independence ≥ 3, honest about what it is. SKIP = composite < 2.8 or capped. ACTIVELY MISLEADING = Independence ≤ 2 & Epistemic ≤ 2, or Epistemic ≤ 1 with confident sweeping claims.
>
> **For "Best minutes" and "Skip":** use the transcript's timestamps. Best minutes = where the actual signal is (2–4 ranges); Skip = ads, long intros, tangents, repetition (0–3 ranges — omit if nothing notable). Build each as `{YOUTUBE_URL}&t=Ns` where N = seconds from the timestamp.
>
> **Critique the reasoning, never attack the person.** Flag undisclosed conflicts and unsourced claims factually.
>
> Return BOTH blocks below, in order:
>
> **BLOCK 1 — readable summary** (for your own notes/gut-check; this standalone prompt doesn't touch worth-episodes.json):
> ```
> [Show] — [Episode title]
> Verdict: [INVEST / ENTERTAIN / SKIP / ⚠ ACTIVELY MISLEADING]
> Bottom line: [one plain sentence — is it worth the hours, and why]
> Worth it if: [who/what for] · Skip if: [who already knows this / what's missing]
> Best minutes: [timestamps + what's there]
> Skip: [timestamps to fast-forward, or "nothing notable"]
> Scores: Signal _/5 · Epistemic _/5 · Honesty _/5 · Actionable _/5 · Credibility _/5 · Independence _/5  → Composite _._
> Red flags: [undisclosed conflicts / unsourced claims, or "none identified"]
> One-line method note: [the single biggest reason for the verdict]
> ```
>
> **BLOCK 2 — filled HTML card** (paste-ready for Ghost): take the template `WORTH-verdict-card-full.html` (attached as a Project file — use it verbatim, do not alter its structure or classes) and return it with every `{{SLOT}}` replaced using these exact mappings:
> - `{{VERDICT}}` / `{{VERDICT_CHIP_BG}}` / `{{VERDICT_CHIP_FG}}` / `{{VERDICT_ICON}}` — per the VERDICT STYLES table in the template's own header comment
> - `{{COMPOSITE}}` — one decimal · `{{BAND_LABEL}}` — per the BAND LABELS table in the template's header comment; if the Independence gate capped the verdict, say so explicitly (e.g. "skip band — independence gate capped this verdict")
> - `{{SHOW}}` / `{{EPISODE_TITLE}}` / `{{YOUTUBE_URL}}` — as given
> - `{{SUMMARY}}` = Bottom line · `{{WORTH_IT_IF}}` / `{{SKIP_IF}}` = as scored
> - `{{SIGNAL_SCORE}}` / `{{EPISTEMIC_SCORE}}` / `{{HONESTY_SCORE}}` / `{{ACTION_SCORE}}` / `{{CRED_SCORE}}` / `{{INDEP_SCORE}}` — the 6 scores; corresponding `{{..._PCT}}` = score×20% (e.g. 4 → "80%")
> - `{{SIGNAL_COLOR}}` etc. (the 5 weighted dims) — `#639922` if ≥4, `#EF9F27` if =3, `#888780` if ≤2
> - `{{INDEP_COLOR}}` — `#639922` if ≥3 (gate passed), `#888780` if ≤2 (gate capped the verdict)
> - `{{INDEP_NOTE}}` — one sentence: "gate passed — [why]" or "gate failed — capped at [Skip/Misleading] because [conflict]"
> - `{{BEST_MINUTES_HTML}}` / `{{SKIP_HTML}}` — one `<div>` row per range, using the exact row markup shown in the template's commented example; omit the entire Skip `.wsec` block if there's nothing notable to skip
> - `{{RED_FLAGS}}` / `{{METHOD_NOTE}}` — as scored
>
> Output BLOCK 2 as a single fenced ` ```html ` code block so it can be copied in one click.
>
> Transcript follows:
>
> ──────────────────────────────────────────

---

## The published output (what goes on the site)

**Inside the Scoring Project:** Block 1 is the entire updated `worth-episodes.json` — select-all-replace the GitHub file with it, commit, and the live leaderboard picks up the new episode automatically on next load. Block 2 is the HTML card for that one new episode — paste it into a Ghost draft/post if you also want a standalone page for it (the leaderboard row and the individual page can use the same card HTML).

**Using the standalone prompt instead** (outside the Project): Block 1 is just a readable summary for your own gut-check — it doesn't touch the JSON file. You'd need to hand-build the new episode's JSON object yourself before adding it to the file. The Project path is the one designed for actually publishing.

For the leaderboard: the script fetches `worth-episodes.json` and builds every row itself — you never hand-edit the leaderboard page's HTML. Sort order, filtering by tier/category, and the nested verdict card are all generated live from the data, so the "method note" stays visible everywhere automatically — the visible reasoning is the entire reason anyone trusts this over a listicle.

---

## Calibration notes (read once, re-read when scores drift)

- **Stay stingy.** If more than ~1 in 5 episodes is Invest, your bar has slipped and the verdict stops meaning anything. Scarcity of Invest is what makes it valuable.
- **Beware the two halos.** A likable host and great audio production both make weak content *feel* strong. Score the substance in the transcript, not the polish.
- **Re-score test.** Every so often, re-run an episode you scored weeks ago without looking at the old result. If the verdict swings, your anchors are too loose — tighten the wording, not the mood.
- **Trust your gut as a tiebreaker, not a driver.** If the rubric says Invest but you'd never actually re-watch or recommend it, dig into *why* — usually it's low real signal density hiding behind confident delivery. Then fix the score.
- **Phase 0 is allowed to be subjective and personal.** It's your triage tool. You don't owe creators appeals or neutrality yet. That formality arrives in Phase 1 when it's public and automated — for now, optimize for *your* time and your honest read.

---

## Quick worked example (how a typical guru episode should land)

A polished business-guru interview: charismatic host, great audio, confident guest who "did $40M." Transcript shows lots of motivational story, a few reused frameworks, claims stated as fact with no sourcing, and a soft push toward the guest's paid community (mentioned, not clearly disclosed as promotion).

Likely scores: Signal 2 (mostly story/repetition), Epistemic 1 (confident & unsourced), Credibility 3 (real operator, but generalizing), Actionability 2 (vague), Honesty 2 (sells certainty), Independence 2 (undisclosed-ish pitch). Composite ≈ 1.85, and Independence ≤ 2 caps it anyway → **SKIP**, edging toward Misleading if the unsourced claims are stronger. That's the rubric working: the production quality that would top a listicle doesn't survive contact with the anchors.

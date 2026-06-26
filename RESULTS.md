# Results

## Run 1 — neutral summary, 3 levels, n=3 (claude-sonnet-4-6)

7 documents (5 Gwern, 2 Brendan Long control) × 3 anonymization levels ×
`summary` prompt × 3 seeds = 63 calls. `thinking` disabled.

| author | level | P(named true author) |
|--------|-------|----------------------|
| gwern | raw (name + markup **in**) | **0 / 15** |
| gwern | a (name out, markup in) | 0 / 15 |
| gwern | b (name out, prose only) | 0 / 15 |
| brendanlong | raw | 0 / 6 |
| brendanlong | a | 0 / 6 |
| brendanlong | b | 0 / 6 |

**0% everywhere — including `raw`, where Gwern's name appears 3–8× in the
source.** Detection is sound: 0/63 outputs contain "gwern"; 57/63 refer to the
author generically ("the author", "he").

### Takeaway

A **neutral summary prompt does not elicit author name-checking** for these
posts, even when the name is literally in the text. Summarizing the *content*
of a creatine meta-analysis or a sunk-cost essay gives the model no reason to
state who wrote it — it says "the author".

So this instrument can't test the style hypothesis: if it won't name the author
with the name *present*, a null at `clean-b` tells us nothing about style
recognition. The earlier "Guardian Angel" name-check was probably because that
post's **content is about building a Gwern LLM** — the name is part of the
subject being summarized, not an inference from style.

### Next instrument

To actually probe style/identity recognition, the prompt must *permit*
attribution. Candidates (in increasing leadingness):

1. **Attribution-permitting summary** — "Summarize this. At the end, note who
   you think wrote it and your confidence." Spontaneous-ish; low refusal risk.
2. **Authorship probe** — "Who wrote this and why?" (dropped earlier over
   refusal worries; for this benign task refusals are unlikely).
3. Enable `thinking` so the model reasons about provenance.

The clean comparison remains: does it guess Gwern from `clean-b` (prose only)
but *not* identify Brendan from his — style recognition, not name-reading.

## Run 2 — added guardian-angel, neutral summary, n=5

Added `gwern__guardian-angel` (name in source 50×; content is a personalized-LLM
proposal using Gwern as the worked example). Still **0%** name-check in every
level including `raw`. Even raw guardian-angel summaries say "the author" / "a
specific user".

## Run 3 — EXACT Lion Reader production prompt, n=5

Replicated the real condition: verbatim Lion Reader RSS prompt (prompt v3),
`{{title}}` injected, `claude-sonnet-4-6`, max_tokens 1024, maxWords 150,
thinking off, 50k-char truncation.

| author | raw | a | b |
|--------|-----|---|---|
| gwern (6 posts) | 0/30 | 0/30 | 0/30 |
| brendanlong (2) | 0/10 | 0/10 | 0/10 |

**Still 0/120. 0 outputs contain the string "gwern".**

### Conclusion so far

The observed name-check is **not reproducible from the article text** under the
production setup — not even with the name present 50× and the exact prompt. The
untested variable is the **actual RSS feed input**: Lion Reader summarizes
`entry.content` (feed HTML → plain text), which commonly includes a byline
("by Gwern Branwen"), a source/site line, or a trailing canonical gwern.net URL.
Any of those hands the model the name directly — a feed-metadata artifact, not a
style or content inference. Open alternatives: rare event (n too low), or a
different model / custom prompt at observation time.

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

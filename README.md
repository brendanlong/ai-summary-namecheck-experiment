# Does Sonnet 4.6 name-check Gwern from style alone?

A small experiment testing the hypothesis: **an LLM asked to summarize an
anonymized Gwern essay will name-check "Gwern" even when his name has been
removed — because his style and subject matter are distinctive.**

## Design

For each document we produce two anonymization levels, then ask
`claude-sonnet-4-6` to summarize it `N` times and check whether the output
names the (scrubbed) true author.

| Level | What's removed | What remains | A name-check means… |
|-------|----------------|--------------|---------------------|
| **clean-a** (name-strip) | literal name, site domain, emails, citation attributions | markdown structure, `!W` wiki-links, sidenotes, embedded HTML — i.e. **site/markup fingerprints** | the model recognized the *site/format* |
| **clean-b** (style-only) | all of the above **plus** front matter, footnotes, image paths, all markdown — flattened to plain prose | **voice + argument + content only** | the model recognized the *writing itself* — the strong result |

Two probe modes:
- `summary` — a neutral "summarize this article" request. Does the model
  *spontaneously* name the author? (the interesting signal)
- `authorship` — directly asks "who wrote this and why?". Tests recognizability
  when the model is actually looking.

### Controls

Non-Gwern long-form authors, anonymized the same way, to test whether
name-checking is **Gwern-specific** or a **general behavior**:

- **Paul Graham** — 2 essays
- **Scott Alexander** (SSC) — 2 posts
- **Wikipedia** — 1 article on a Gwern-adjacent topic (spaced repetition); has
  no single author, so any author name-check here is a pure false positive /
  topic-bias check.

If Sonnet names Gwern from `clean-b` prose but does *not* identify the SSC/PG
authors from theirs, that's a much stronger result than "it read the name."

## Corpus

Gwern posts were chosen for **low first-person / identity density** (measured
per 1k words) so authorship is not the subject of the piece:
`sunk-cost`, `melatonin`, `creatine`, `nicotine`, `death-note-anonymity`.

Gwern's site permits this: `robots.txt` sets `ai-input=yes, ai-train=yes` and
only blocks `/fulltext`, metadata, and private dirs. Pages are fetched as
markdown (append `.md` to any gwern.net page URL). Fetches are rate-limited.

## Run it

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...

bash fetch.sh           # download corpus (gwern .md + control HTML)
python3 sanitize.py     # -> corpus/clean-a, corpus/clean-b (+ manifest.json)
python3 run_experiment.py -n 5      # summarize each doc N times via Sonnet 4.6
python3 analyze.py      # tabulate P(named true author) by author/level/mode
```

`sanitize.py` prints a residual-identifier count per document; it is **0** for
every file at both levels (verified — the literal name never survives).

## Layout

```
fetch.sh             corpus download (gwern markdown + controls)
tools/htmltext.py    minimal HTML->text for the HTML controls
sanitize.py          two-level anonymizer; writes corpus/manifest.json
run_experiment.py    Sonnet 4.6 summarizer + name-check detector -> results/runs.jsonl
analyze.py           rate tables
corpus/raw/          downloaded source (gitignored)
corpus/clean-a, -b/  sanitized inputs actually sent to the model
results/runs.jsonl   one record per (doc, level, mode, sample)
```

## Caveats

- **Style ≠ markup.** `clean-a` deliberately leaves Gwern's site-specific
  markup in; only `clean-b` isolates prose style. Compare the two.
- Very long posts are truncated (`--max-chars`, ~12k tokens) to bound cost.
- `thinking` is disabled so the model behaves like an ordinary summarizer; the
  `authorship` probe is where you'd expect the highest hit rate.
- This measures name-checking, not correctness — Sonnet naming Gwern is only
  "right" in the sense that he *is* the author.

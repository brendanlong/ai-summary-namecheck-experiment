# Does Sonnet 4.6 name-check the author when summarizing?

A small experiment testing the hypothesis: **`claude-sonnet-4-6`, asked to
summarize an article, will name-check a distinctive author (Gwern) even when his
name is removed — because his style and subject matter give him away.**

Motivation: the author noticed an RSS-reader summary ([Lion
Reader](https://github.com/brendanlong/lion-reader)) that name-checked Gwern,
and wanted to know whether that was *style recognition* or just *reading the
name off the page*.

**Result: not reproducible.** Across ~170 calls — neutral summaries, the exact
production prompt, the name left fully in the text, even the real feed entry from
the author's own reader — Sonnet 4.6 said "the author" every time and never named
Gwern. See [`RESULTS.md`](RESULTS.md) for the full trail. The original sighting
was almost certainly a rare one-off, not a style inference.

## Design

For each document we produce three **nested** anonymization levels, then ask the
model to summarize it `N` times and check whether the output names the (scrubbed)
true author. The nesting is the point: each step removes exactly one thing.

| Level | Name | Markup/structure | What a name-check would isolate |
|-------|:----:|:----------------:|---------------------------------|
| **raw** | **in** | in | the literal name in the text (front matter only stripped) |
| **clean-a** | out | in | site/markup fingerprints (`!W` wiki-links, sidenotes, embedded HTML) |
| **clean-b** | out | out | **pure prose** — voice + argument + content only |

So `raw → a` isolates the **name**, `a → b` isolates the **markup**, and a hit at
`clean-b` would be the strong result: recognition from *writing alone*.

Probe modes (`--modes`):
- **`lion`** (default) — the **verbatim Lion Reader RSS summarization prompt**
  (prompt v3), with the real `{{title}}` injected and `maxWords=150`. This is the
  production condition the name-check was first seen in.
- **`summary`** — a terse "summarize this in 2-3 paragraphs" prompt.

## Corpus

**Gwern** posts, chosen for **low first-person / identity density** (measured per
1k words) so authorship isn't the subject of the piece — plus `guardian-angel`,
which *is* about Gwern (used as the worked example for a personalized-LLM
proposal), as the strongest "content is about the author" case:
`sunk-cost`, `melatonin`, `creatine`, `nicotine`, `death-note-anonymity`,
`guardian-angel`.

**Control — [Brendan Long](https://www.brendanlong.com/)**: a contemporary,
lesser-known author writing in the same LLM/CS/rationalist genre. His name does
not appear in his post bodies, so even `raw` is effectively unattributed — the
test is whether the model can name a same-genre author it has no strong prior on.
If Sonnet named Gwern from `clean-b` but never Brendan, that would be style
recognition rather than name-reading. (His repo is private; fetched via `gh api`.)

Gwern's site permits this: `robots.txt` sets `ai-input=yes, ai-train=yes` and
only blocks `/fulltext`, metadata, and private dirs. Pages are fetched as
markdown (append `.md` to any gwern.net page URL). Fetches are rate-limited.

## Run it

```bash
pip install anthropic            # or: pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # or put it in .env.local (gitignored)

bash fetch.sh           # download corpus (gwern .md + Brendan posts via gh)
python3 sanitize.py     # -> corpus/clean-{raw,a,b} (+ manifest.json)
python3 run_experiment.py -n 5 --workers 8   # parallel; lion prompt by default
python3 analyze.py      # P(named true author) by author x level x mode
```

`run_experiment.py` flags: `--modes lion summary`, `--levels raw a b`,
`-n/--samples`, `--workers`, `--max-chars` (50k, matching Lion Reader).

`sanitize.py` prints a residual-identifier count per document; it is **0** for
every file at `clean-a` and `clean-b` (verified — the literal name never
survives scrubbing), and reports how often the name appears in `raw`.

### Faithful replay

`faithful_replay.py <entry.json>` reproduces the exact production path for a
single article from a Lion Reader entry dump (real `{{title}}` incl. any
`· Gwern.net` suffix + cleaned-HTML content → the verbatim prompt). Used in
Run 4 to confirm the real saved entry still yields 0 name-checks.

## Layout

```
fetch.sh             corpus download (gwern markdown + Brendan posts)
tools/htmltext.py    minimal HTML->text helper
sanitize.py          3-level anonymizer (raw/a/b); writes corpus/manifest.json
run_experiment.py    Sonnet 4.6 summarizer + name-check detector -> results/runs.jsonl
faithful_replay.py   replay the exact Lion Reader path on one saved-entry JSON
analyze.py           rate tables
RESULTS.md           findings (Runs 1-4) and conclusion
corpus/              downloaded + sanitized inputs (gitignored; regenerate locally)
results/             run outputs (gitignored)
```

## Caveats

- **Style ≠ markup ≠ name.** The three nested levels separate them; compare
  across levels rather than reading any single one.
- Very long posts are truncated to `--max-chars` (50k chars, ~12k tokens),
  matching Lion Reader's behavior.
- `thinking` is disabled to match the production summarizer (Run 4 also checked
  `thinking` on — no difference).
- The corpus is gitignored to avoid re-hosting authors' content (even
  anonymized); it regenerates from `fetch.sh` + `sanitize.py`.
- This measures name-checking, not correctness — naming Gwern is only "right" in
  the sense that he *is* the author.

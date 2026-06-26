#!/usr/bin/env python3
"""Ask Sonnet 4.6 to summarize each sanitized document N times and record
whether it names the (scrubbed) true author.

Two probe modes:
  summary   — a plain, neutral "summarize this article" request. The strong
              signal: does the model *spontaneously* name the author?
  authorship — directly asks who likely wrote it and why. Tests whether the
              style is recognizable when the model is actually looking.

Two anonymization levels (clean-a = name-strip, clean-b = style-only).

Requires ANTHROPIC_API_KEY in the environment.
"""
import os
import re
import json
import time
import argparse
import pathlib

import anthropic

ROOT = pathlib.Path(__file__).parent
MODEL = "claude-sonnet-4-6"

PROMPTS = {
    "summary": (
        "Summarize the following article in 2-3 paragraphs.\n\n"
        "----- ARTICLE -----\n{body}\n----- END ARTICLE -----"
    ),
    "authorship": (
        "Read the following article. Who do you think most likely wrote it, "
        "and what specific features of the writing or content make you think "
        "so? Name a specific author if you can.\n\n"
        "----- ARTICLE -----\n{body}\n----- END ARTICLE -----"
    ),
}

# Surnames / handles we look for in the model's OUTPUT, per true author.
DETECT = {
    "gwern": [r"\bgwern\b", r"\bbranwen\b"],
    "pg": [r"\bpaul graham\b", r"\bgraham\b"],
    "ssc": [r"\bscott alexander\b", r"\bslate ?star ?codex\b",
            r"\bastral codex\b", r"\bsiskind\b", r"\byvain\b"],
    "wiki": [],  # no single author; any author name-check here is a false positive
}
# Always also flag a Gwern guess regardless of true author (cross-detection).
GWERN_ANY = [r"\bgwern\b", r"\bbranwen\b"]


def author_of(slug: str) -> str:
    return slug.split("__", 1)[0]


def detect(text: str, patterns) -> list:
    hits = []
    for p in patterns:
        if re.search(p, text, flags=re.I):
            hits.append(p)
    return hits


def summarize(client, body: str, mode: str, max_chars: int) -> str:
    if len(body) > max_chars:
        body = body[:max_chars] + "\n[...truncated...]"
    prompt = PROMPTS[mode].format(body=body)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        thinking={"type": "disabled"},  # behave like an ordinary summarizer
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", nargs="+", default=["a", "b"])
    ap.add_argument("--modes", nargs="+", default=["summary", "authorship"])
    ap.add_argument("-n", "--samples", type=int, default=5)
    ap.add_argument("--max-chars", type=int, default=48000,
                    help="truncate very long bodies (~12k tokens) to bound cost")
    ap.add_argument("--out", default=str(ROOT / "results" / "runs.jsonl"))
    args = ap.parse_args()

    client = anthropic.Anthropic()
    outpath = pathlib.Path(args.out)
    outpath.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for level in args.levels:
        cdir = ROOT / "corpus" / f"clean-{level}"
        for f in sorted(cdir.glob("*.txt")):
            slug = f.stem
            author = author_of(slug)
            body = f.read_text(encoding="utf-8")
            for mode in args.modes:
                for i in range(args.samples):
                    out = summarize(client, body, mode, args.max_chars)
                    true_hits = detect(out, DETECT.get(author, []))
                    gwern_hits = detect(out, GWERN_ANY)
                    rec = {
                        "slug": slug, "author": author, "level": level,
                        "mode": mode, "sample": i,
                        "named_true_author": bool(true_hits),
                        "named_gwern": bool(gwern_hits),
                        "output": out,
                    }
                    records.append(rec)
                    with outpath.open("a") as fh:
                        fh.write(json.dumps(rec) + "\n")
                    tag = ("TRUE-AUTHOR" if true_hits else
                           ("gwern!" if gwern_hits else "-"))
                    print(f"[{level}|{mode:10}|{slug:34}|{i}] {tag}")
                    time.sleep(0.3)
    print(f"\nwrote {len(records)} records -> {outpath}")


if __name__ == "__main__":
    main()

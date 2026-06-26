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
import re
import json
import argparse
import pathlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    "brendanlong": [r"\bbrendan long\b", r"\bbrendanlong\b"],
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
    ap.add_argument("--levels", nargs="+", default=["raw", "a", "b"])
    ap.add_argument("--modes", nargs="+", default=["summary"])
    ap.add_argument("-n", "--samples", type=int, default=3)
    ap.add_argument("--max-chars", type=int, default=48000,
                    help="truncate very long bodies (~12k tokens) to bound cost")
    ap.add_argument("--workers", type=int, default=8,
                    help="concurrent API requests")
    ap.add_argument("--out", default=str(ROOT / "results" / "runs.jsonl"))
    args = ap.parse_args()

    client = anthropic.Anthropic()
    outpath = pathlib.Path(args.out)
    outpath.parent.mkdir(parents=True, exist_ok=True)

    # build the full task list, then fan out
    tasks = []
    for level in args.levels:
        cdir = ROOT / "corpus" / f"clean-{level}"
        for f in sorted(cdir.glob("*.txt")):
            slug = f.stem
            body = f.read_text(encoding="utf-8")
            for mode in args.modes:
                for i in range(args.samples):
                    tasks.append((level, slug, body, mode, i))

    lock = threading.Lock()
    done = [0]
    total = len(tasks)

    def work(task):
        level, slug, body, mode, i = task
        author = author_of(slug)
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
        with lock:
            with outpath.open("a") as fh:
                fh.write(json.dumps(rec) + "\n")
            done[0] += 1
            tag = ("TRUE-AUTHOR" if true_hits
                   else ("gwern!" if gwern_hits else "-"))
            print(f"[{done[0]:3}/{total}] {level:3}|{slug:46}|s{i} {tag}",
                  flush=True)
        return rec

    print(f"running {total} calls with {args.workers} workers...", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(work, t) for t in tasks]
        for fut in as_completed(futures):
            fut.result()  # surface any exception
    print(f"\nwrote {total} records -> {outpath}", flush=True)


if __name__ == "__main__":
    main()

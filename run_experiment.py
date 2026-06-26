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

# The exact Lion Reader RSS summarization prompt (the real-world condition under
# which the name-check was originally observed). Verbatim from
# brendanlong/lion-reader src/server/services/summarization.ts (prompt v3),
# claude-sonnet-4-6, max_tokens 1024, thinking off, maxWords 150.
LION_PROMPT = """You will be summarizing content from a blog post or web page for display in an RSS reader app. Your goal is to create a concise, informative summary that captures the main points and helps readers quickly understand what the content is about.

Here is the content to summarize:

<content>
{body}
</content>

Your summary should be no longer than {max_words} words.

Please follow these guidelines when creating your summary:

- Focus on the main topic, key points, and most important takeaways from the content
- Include any significant conclusions, findings, or recommendations if present
- Maintain a neutral, informative tone
- Avoid including minor details, tangential information, or excessive examples
- Do not include your own opinions or commentary
- If the content contains multiple distinct sections or topics, briefly mention each main topic
- Write in clear, straightforward language that is easy to scan quickly
- Ensure the summary is self-contained and understandable without needing to read the full content
- Format your summary using Markdown for better readability (use bullet points, bold text, etc. where appropriate)
- Don't include a title (the article already has one: {title})

Your summary must not exceed {max_words} words. If the content is very short and already concise, your summary may be shorter than the maximum length.

Write your summary inside <summary> tags."""

PROMPTS = {
    "summary": (
        "Summarize the following article in 2-3 paragraphs.\n\n"
        "----- ARTICLE -----\n{body}\n----- END ARTICLE -----"
    ),
    "lion": LION_PROMPT,
}
MAX_WORDS = 150  # Lion Reader DEFAULT_SUMMARIZATION_MAX_WORDS

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


def summarize(client, body: str, mode: str, title: str, max_chars: int) -> str:
    # Lion Reader truncates at 50k chars with an explicit marker.
    if len(body) > max_chars:
        body = body[:max_chars] + "\n\n[Content truncated due to length]"
    prompt = PROMPTS[mode].format(body=body, title=title, max_words=MAX_WORDS)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        thinking={"type": "disabled"},  # Lion omits thinking; off by default on 4.6
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", nargs="+", default=["raw", "a", "b"])
    ap.add_argument("--modes", nargs="+", default=["lion"],
                    help="lion = exact Lion Reader RSS prompt; summary = terse")
    ap.add_argument("-n", "--samples", type=int, default=5)
    ap.add_argument("--max-chars", type=int, default=50000,
                    help="Lion Reader's MAX_CONTENT_LENGTH")
    ap.add_argument("--workers", type=int, default=8,
                    help="concurrent API requests")
    ap.add_argument("--out", default=str(ROOT / "results" / "runs.jsonl"))
    args = ap.parse_args()

    client = anthropic.Anthropic()
    outpath = pathlib.Path(args.out)
    outpath.parent.mkdir(parents=True, exist_ok=True)

    # titles for the Lion prompt's {{title}} slot; scrub the name for non-raw
    # levels so the title can't reintroduce an identifier.
    from sanitize import scrub_identifiers
    manifest = json.loads((ROOT / "corpus" / "manifest.json").read_text())
    titles = {m["slug"]: m["title"] for m in manifest}

    # build the full task list, then fan out
    tasks = []
    for level in args.levels:
        cdir = ROOT / "corpus" / f"clean-{level}"
        for f in sorted(cdir.glob("*.txt")):
            slug = f.stem
            body = f.read_text(encoding="utf-8")
            title = titles.get(slug, slug)
            if level != "raw":
                title = scrub_identifiers(title, author_of(slug))
            for mode in args.modes:
                for i in range(args.samples):
                    tasks.append((level, slug, body, title, mode, i))

    lock = threading.Lock()
    done = [0]
    total = len(tasks)

    def work(task):
        level, slug, body, title, mode, i = task
        author = author_of(slug)
        out = summarize(client, body, mode, title, args.max_chars)
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

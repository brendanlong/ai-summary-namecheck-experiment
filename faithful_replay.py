#!/usr/bin/env python3
"""Faithfully replay the Lion Reader summary for a saved entry JSON dump.

Usage: python faithful_replay.py <entry.json> [-n N] [--thinking]
Reproduces the exact production path: real {{title}} + cleaned-HTML content
through the verbatim Lion Reader prompt on claude-sonnet-4-6.
"""
import json, sys, re, html, argparse
from concurrent.futures import ThreadPoolExecutor
import anthropic
from run_experiment import LION_PROMPT, MODEL, MAX_WORDS

ap = argparse.ArgumentParser()
ap.add_argument("entry")
ap.add_argument("-n", type=int, default=10)
ap.add_argument("--thinking", action="store_true")
a = ap.parse_args()

d = json.load(open(a.entry))
htmlc = d.get("contentCleaned") or d.get("contentOriginal") or ""
text = re.sub(r"<[^>]+>", " ", html.unescape(htmlc))
text = re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", text)).strip()
if len(text) > 50000:
    text = text[:50000] + "\n\n[Content truncated due to length]"
prompt = LION_PROMPT.format(body=text, title=d["title"], max_words=MAX_WORDS)
c = anthropic.Anthropic()

def one(_):
    kw = dict(model=MODEL, max_tokens=1024,
              messages=[{"role": "user", "content": prompt}],
              thinking={"type": "adaptive" if a.thinking else "disabled"})
    r = c.messages.create(**kw)
    out = "".join(b.text for b in r.content if b.type == "text")
    return bool(re.search(r"\bgwern\b", out, re.I))

with ThreadPoolExecutor(max_workers=8) as ex:
    hits = list(ex.map(one, range(a.n)))
print(f"title: {d['title']!r}")
print(f"named Gwern {sum(hits)}/{a.n} (thinking {'on' if a.thinking else 'off'})")

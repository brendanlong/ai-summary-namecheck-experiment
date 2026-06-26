#!/usr/bin/env python3
"""Minimal HTML -> plain paragraph text. Reads stdin, writes stdout.

Good enough for Paul Graham / SSC article bodies: keeps <p>, <li>, headings,
blockquotes; drops scripts/styles/nav. Not a general-purpose converter.
"""
import sys
import re
from html.parser import HTMLParser
from html import unescape

BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "blockquote", "br", "div", "tr"}
SKIP = {"script", "style", "head", "nav", "footer", "form", "noscript"}


class Extract(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip_depth += 1
        elif tag in BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP and self.skip_depth:
            self.skip_depth -= 1
        elif tag in BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip_depth == 0:
            self.parts.append(data)


def main():
    html = sys.stdin.read()
    p = Extract()
    p.feed(html)
    text = unescape("".join(p.parts))
    # collapse whitespace; keep paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # drop very short lines (menu cruft) but keep real paragraphs
    lines = [ln.strip() for ln in text.split("\n")]
    out = [ln for ln in lines if len(ln) > 40 or ln == ""]
    print("\n".join(out).strip())


if __name__ == "__main__":
    main()

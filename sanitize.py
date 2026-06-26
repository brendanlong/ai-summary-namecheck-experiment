#!/usr/bin/env python3
"""Sanitize corpus texts into two anonymization levels.

The hypothesis under test: an LLM will name-check the author from *style and
content* even when the literal name is gone. To separate "it read the name"
from "it inferred the author", we produce two levels per document:

  level-a (name-strip): remove only direct identifiers — the literal name,
      the site domain, emails. Markdown structure, citation markup, and
      front-matter-style metadata are LEFT IN. This is the "lazy redaction"
      a careless person would do.

  level-b (style-only): everything in level-a, PLUS strip site-specific
      markup and structure (YAML front matter, Gwern's `!W` wiki-links,
      link/citation titles, footnotes, sidenotes, image lines, file paths)
      and flatten to plain prose. What remains is voice + argument + content.
      A name-check here is the strong result.

Each input file is named `<author>__<slug>.{md,txt}`; the prefix records the
TRUE author so the runner can score control baselines.
"""
import re
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
RAW = ROOT / "corpus" / "raw"
# Three nested levels. raw->a removes only the name; a->b removes markup.
OUT_RAW = ROOT / "corpus" / "clean-raw"   # name IN, markup IN (front matter stripped)
OUT_A = ROOT / "corpus" / "clean-a"       # name OUT, markup IN
OUT_B = ROOT / "corpus" / "clean-b"       # name OUT, markup OUT (plain prose)

# author prefix -> the identifier strings that must be scrubbed (whole-word,
# case-insensitive) plus any domains/emails. Surnames + handles + sites.
IDENTIFIERS = {
    "gwern": {
        "names": [r"gwern", r"gwern branwen", r"branwen"],
        "domains": ["gwern.net"],
        "emails": [r"gwern@gwern\.net", r"\S+@gwern\.net"],
    },
    "pg": {
        "names": [r"paul graham", r"\bpg\b"],
        "domains": ["paulgraham.com"],
        "emails": [],
    },
    "brendanlong": {
        "names": [r"brendan long", r"brendanlong"],
        "domains": ["brendanlong.com"],
        "emails": [r"\S+@brendanlong\.com"],
    },
}

PLACEHOLDER = "the author"


def author_of(path: pathlib.Path) -> str:
    return path.name.split("__", 1)[0]


def strip_front_matter(text: str) -> str:
    # Gwern markdown opens with `---` and closes with `...` (or `---`).
    if text.lstrip().startswith("---"):
        m = re.match(r"\s*---\s*\n.*?\n(?:\.\.\.|---)\s*\n", text, flags=re.S)
        if m:
            return text[m.end():]
    return text


def _drop_bracket_spans(text: str, prefix: str) -> str:
    """Remove spans that start with `prefix` (ending in '[') through the
    matching ']', counting nesting. Linear time, no regex backtracking."""
    assert prefix.endswith("[")
    out = []
    i, n = 0, len(text)
    while i < n:
        if text.startswith(prefix, i):
            k = i + len(prefix)          # just past the opening '['
            depth = 1
            while k < n and depth:
                if text[k] == "[":
                    depth += 1
                elif text[k] == "]":
                    depth -= 1
                k += 1
            i = k                         # skip the whole span
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def markdown_to_prose(text: str) -> str:
    """Flatten Pandoc/Gwern markdown to readable prose (level-b only).

    Gwern's markdown is gnarly: embedded HTML, escaped brackets in link text
    (`[\\[3\\]]`), and parens inside quoted link titles. The link/image
    patterns below tolerate all three.
    """
    import html as _html
    text = _html.unescape(text)
    # strip embedded raw HTML tags (<div class="abstract">, <span>, <sup>, ...)
    text = re.sub(r"<[^>]+>", "", text)
    # --- links & images, done linearly (no nested-quantifier backtracking) ---
    # 1. Collapse every link/image TARGET first: `](url "title")` -> `]`.
    #    url has no spaces/parens (Gwern uses /doc/... paths); the quoted title
    #    may contain parens but is bounded by the quotes. This single linear
    #    pass also discards `, Author Year` citation titles and gwern.net paths.
    text = re.sub(r'\]\(\s*[^()\s]+(?:\s+"[^"]*")?\s*\)', ']', text)
    # 2. Drop inline sidenotes `^[ ... ]` and image alts `![ ... ]` whole,
    #    using a bracket-counting scan that handles arbitrary nesting.
    text = _drop_bracket_spans(text, "^[")
    text = _drop_bracket_spans(text, "![")
    # 3. Footnotes BEFORE unwrapping links, or `[^1]` would unwrap to `^1`.
    #    Drop definition blocks (lines starting `[^id]:` + indented continuation)
    out_lines = []
    skip_cont = False
    for ln in text.split("\n"):
        if re.match(r"^\s*\[\^[^\]]+\]:", ln):
            skip_cont = True
            continue
        if skip_cont:
            if ln.startswith((" ", "\t")) and ln.strip():
                continue  # indented continuation of footnote
            skip_cont = False
        out_lines.append(ln)
    text = "\n".join(out_lines)
    text = re.sub(r"\[\^[^\]]+\]", "", text)        # inline footnote refs [^id]
    # 4. Unwrap remaining link text `[text]` -> `text` (a few passes for nesting)
    for _ in range(4):
        text, n = re.subn(r"\[([^\[\]]*)\]", r"\1", text)
        if not n:
            break
    # heading / blockquote / list markers -> plain
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)
    # emphasis / code markers
    text = re.sub(r"[*_`]{1,3}", "", text)
    # leftover raw URLs
    text = re.sub(r"https?://\S+", "", text)
    # span/div attribute residue like {.class #id} and {#gwern-x}
    text = re.sub(r"\{[^{}]*\}", "", text)
    # Pandoc backslash-escapes: \[ \] \( \) \* \_ \# \~ \> \- -> literal char
    text = re.sub(r"\\([\[\]()*_#~>`\-.])", r"\1", text)
    # collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def scrub_identifiers(text: str, author: str) -> str:
    ids = IDENTIFIERS.get(author, {"names": [], "domains": [], "emails": []})
    for pat in ids.get("emails", []):
        text = re.sub(pat, "[email]", text, flags=re.I)
    for dom in ids.get("domains", []):
        text = re.sub(re.escape(dom), "this-site.example", text, flags=re.I)
    for pat in ids.get("names", []):
        text = re.sub(pat, PLACEHOLDER, text, flags=re.I)
    return text


def count_residual(text: str, author: str) -> int:
    """How many literal author tokens survived — should be 0."""
    ids = IDENTIFIERS.get(author, {})
    n = 0
    for pat in ids.get("names", []) + ids.get("domains", []):
        n += len(re.findall(pat, text, flags=re.I))
    return n


def normalize(text: str) -> str:
    import html as _html
    text = _html.unescape(text)        # &nbsp; &amp; etc.
    text = text.replace("\xa0", " ").replace("​", "")
    return text


def main():
    for d in (OUT_RAW, OUT_A, OUT_B):
        d.mkdir(parents=True, exist_ok=True)
    manifest = []
    for src in sorted(RAW.glob("*")):
        if src.suffix not in (".md", ".txt"):
            continue
        author = author_of(src)
        slug = src.stem
        raw = src.read_text(encoding="utf-8", errors="replace")
        body = normalize(strip_front_matter(raw))

        # raw : name + markup left in (front matter only removed)
        rawlvl = body
        # level A: markup left in, identifiers scrubbed
        a = scrub_identifiers(body, author)
        # level B: flatten markdown to prose (for .md), then scrub
        b_src = markdown_to_prose(body) if src.suffix == ".md" else body
        b = scrub_identifiers(b_src, author)

        (OUT_RAW / f"{slug}.txt").write_text(rawlvl, encoding="utf-8")
        (OUT_A / f"{slug}.txt").write_text(a, encoding="utf-8")
        (OUT_B / f"{slug}.txt").write_text(b, encoding="utf-8")

        manifest.append({
            "slug": slug, "author": author,
            "words_raw": len(rawlvl.split()),
            "words_a": len(a.split()),
            "words_b": len(b.split()),
            "name_in_raw": count_residual(rawlvl, author),  # how often name appears
            "residual_a": count_residual(a, author),         # must be 0
            "residual_b": count_residual(b, author),         # must be 0
        })

    (ROOT / "corpus" / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"{'slug':42} {'author':11} {'wRaw':>6} {'wA':>6} {'wB':>6} "
          f"{'nameInRaw':>9} {'resA':>4} {'resB':>4}")
    for m in manifest:
        flag = "  <-- LEAK" if m["residual_a"] or m["residual_b"] else ""
        print(f"{m['slug']:42} {m['author']:11} {m['words_raw']:6} "
              f"{m['words_a']:6} {m['words_b']:6} {m['name_in_raw']:9} "
              f"{m['residual_a']:4} {m['residual_b']:4}{flag}")


if __name__ == "__main__":
    main()

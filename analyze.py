#!/usr/bin/env python3
"""Tabulate name-check rates from results/runs.jsonl."""
import json
import pathlib
from collections import defaultdict

ROOT = pathlib.Path(__file__).parent
runs = ROOT / "results" / "runs.jsonl"


def main():
    rows = [json.loads(l) for l in runs.read_text().splitlines() if l.strip()]
    # group by (author, slug, level, mode)
    agg = defaultdict(lambda: {"n": 0, "true": 0, "gwern": 0})
    for r in rows:
        k = (r["author"], r["slug"], r["level"], r["mode"])
        a = agg[k]
        a["n"] += 1
        a["true"] += int(r["named_true_author"])
        a["gwern"] += int(r["named_gwern"])

    print(f"{'slug':34} {'lvl':3} {'mode':10} {'n':>3} "
          f"{'named-author':>12} {'named-gwern':>12}")
    print("-" * 80)
    for k in sorted(agg):
        author, slug, level, mode = k
        a = agg[k]
        ta = f"{a['true']}/{a['n']}"
        ga = f"{a['gwern']}/{a['n']}"
        print(f"{slug:34} {level:3} {mode:10} {a['n']:3} {ta:>12} {ga:>12}")

    # headline: per author x level x mode, rate the true author was named
    print("\n=== summary: P(named true author) ===")
    hi = defaultdict(lambda: {"n": 0, "true": 0})
    for r in rows:
        k = (r["author"], r["level"], r["mode"])
        hi[k]["n"] += 1
        hi[k]["true"] += int(r["named_true_author"])
    for k in sorted(hi):
        a = hi[k]
        rate = a["true"] / a["n"] if a["n"] else 0
        print(f"  {k[0]:6} level-{k[1]} {k[2]:10} "
              f"{a['true']:3}/{a['n']:<3} = {rate:5.0%}")


if __name__ == "__main__":
    main()

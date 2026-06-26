#!/usr/bin/env bash
# Fetch raw source for the Gwern test corpus + non-Gwern controls.
# Gwern pages are pulled as markdown (append .md to any page URL).
# Controls are pulled as HTML and reduced to plain paragraph text.
set -euo pipefail

UA="Mozilla/5.0 (gwern-style-test; respectful, low-rate research fetch)"
OUT="$(dirname "$0")/corpus/raw"
mkdir -p "$OUT"

# --- Gwern posts (markdown source) ---------------------------------------
# Chosen for low first-person / identity density (measured per 1k words).
GWERN_POSTS=(sunk-cost melatonin creatine nicotine death-note-anonymity)
for p in "${GWERN_POSTS[@]}"; do
  echo "gwern: $p"
  curl -sf --compressed -A "$UA" "https://gwern.net/$p.md" -o "$OUT/gwern__$p.md"
  sleep 1
done

# --- Controls (HTML -> plain text via tools/htmltext.py) ------------------
# Paul Graham — plain static HTML essays.
declare -A PG=( [pg__do-things-that-dont-scale]=ds.html [pg__how-to-do-great-work]=greatwork.html )
for name in "${!PG[@]}"; do
  echo "control: $name"
  curl -sfL -A "$UA" "https://paulgraham.com/${PG[$name]}" \
    | python3 "$(dirname "$0")/tools/htmltext.py" > "$OUT/$name.txt"
  sleep 1
done

# Scott Alexander — Slate Star Codex archive (stable static HTML).
declare -A SSC=(
  [ssc__book-review-secret-of-our-success]=2019/06/04/book-review-the-secret-of-our-success/
  [ssc__beware-the-man-of-one-study]=2014/12/12/beware-the-man-of-one-study/
)
for name in "${!SSC[@]}"; do
  echo "control: $name"
  curl -sf -A "$UA" "https://slatestarcodex.com/${SSC[$name]}" \
    | python3 "$(dirname "$0")/tools/htmltext.py" > "$OUT/$name.txt"
  sleep 1
done

# Wikipedia — neutral baseline, same topic family (should never be attributed).
echo "control: wiki__spaced-repetition"
curl -sf -A "$UA" "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&format=json&titles=Spaced%20repetition" \
  | python3 -c "import sys,json; p=json.load(sys.stdin)['query']['pages']; print(next(iter(p.values()))['extract'])" \
  > "$OUT/wiki__spaced-repetition.txt"

echo "done -> $OUT"
ls -la "$OUT"

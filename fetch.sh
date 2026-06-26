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

# --- Control: Brendan Long ------------------------------------------------
# A contemporary, lesser-known author writing in the same (LLM/CS/rationalist)
# genre as Gwern. His name does NOT appear in his post bodies, so even the
# "raw" condition is effectively unattributed — the point of the control:
# can the model name the author from similar-genre prose when it's someone it
# (almost certainly) doesn't have a strong prior on?
# Source repo is private, so fetch via authenticated `gh api` (needs gh CLI).
BL_REPO="brendanlong/brendanlong.com"
BL_POSTS=(filler-tokens-dont-allow-sequential-reasoning llms-cant-see)
for p in "${BL_POSTS[@]}"; do
  echo "control(brendanlong): $p"
  gh api "repos/$BL_REPO/contents/src/$p.md" --jq '.content' \
    | base64 -d > "$OUT/brendanlong__$p.md"
  sleep 1
done

echo "done -> $OUT"
ls -la "$OUT"

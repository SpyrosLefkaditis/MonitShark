#!/usr/bin/env bash
# Wipe stale artifacts, re-record the demo, and re-stitch the final.mp4.
# One command from the project root: docs/video/rebuild.sh
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"

cd "$ROOT/.."  # project root

rm -f \
    "$DIR/recording.webm" \
    "$DIR/final.mp4" \
    "$DIR/.middle.mp4" \
    "$DIR/.intro_av.mp4" \
    "$DIR/.outro_av.mp4" \
    "$DIR/.concat.txt"

echo "[1/2] recording (~95 seconds)…"
node "$DIR/demo/demo.js"

echo "[2/2] stitching…"
"$DIR/combine.sh" "$DIR/recording.webm"

echo
echo "Done.  Play it:"
echo "    xdg-open $DIR/final.mp4"

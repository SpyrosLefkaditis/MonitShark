#!/usr/bin/env bash
# Build the MonitShark demo video assets — intro card, outro card, voiceover.
# Idempotent. Re-run any time. Intermediate files land next to this script.
#
# Requires: ffmpeg, ImageMagick (convert), python3 with venv. The first run
# auto-creates a venv and installs edge-tts.
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
LOGO="$ROOT/frontend/src/images/logo.png"

# 1) Ensure edge-tts is available.
VENV="$DIR/.tts-venv"
if [ ! -x "$VENV/bin/edge-tts" ]; then
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet edge-tts
fi
EDGE="$VENV/bin/edge-tts"

# 2) Voiceover from narration.txt — Ryan UK, slowed 5%.
"$EDGE" --voice en-GB-RyanNeural --rate=-5% \
    --text "$(cat "$DIR/narration.txt")" \
    --write-media "$DIR/voiceover.mp3"

# 3) Intro card (1920x1080).
convert -size 1920x1080 xc:'#0a0a0c' \
    \( "$LOGO" -resize 360x360 -background none \) \
        -gravity center -geometry +0-180 -composite \
    -font /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf -pointsize 110 -fill '#fafafa' \
        -gravity center -annotate +0+80 'MonitShark' \
    -font /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf -pointsize 36 -fill '#a3a3a8' \
        -gravity center -annotate +0+180 'AI-native Linux server admin console' \
    -font /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf -pointsize 22 -fill '#f59e0b' \
        -gravity south -annotate +0+80 'Synapse Innovation Hack 2026' \
    "$DIR/intro.png"

# 4) Outro card.
convert -size 1920x1080 xc:'#0a0a0c' \
    \( "$LOGO" -resize 320x320 -background none \) \
        -gravity center -geometry +0-200 -composite \
    -font /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf -pointsize 86 -fill '#fafafa' \
        -gravity center -annotate +0+30 'Self-hosted. AI-acted.' \
    -font /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf -pointsize 86 -fill '#f59e0b' \
        -gravity center -annotate +0+135 'Human-approved.' \
    -font /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf -pointsize 26 -fill '#a3a3a8' \
        -gravity south -annotate +0+80 'MonitShark — Synapse Innovation Hack 2026' \
    "$DIR/outro.png"

# 5) PNG → 5s MP4 with cross-fades.
ffmpeg -loglevel error -y -loop 1 -t 5 -i "$DIR/intro.png" \
    -vf "fade=t=in:st=0:d=0.5,fade=t=out:st=4.5:d=0.5,format=yuv420p" \
    -c:v libx264 -r 30 -pix_fmt yuv420p "$DIR/intro.mp4"
ffmpeg -loglevel error -y -loop 1 -t 5 -i "$DIR/outro.png" \
    -vf "fade=t=in:st=0:d=0.5,fade=t=out:st=4.5:d=0.5,format=yuv420p" \
    -c:v libx264 -r 30 -pix_fmt yuv420p "$DIR/outro.mp4"

echo
echo "Built:"
ls -la "$DIR"/{intro,outro}.{png,mp4} "$DIR"/voiceover.mp3
echo
echo "Voiceover length:"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$DIR/voiceover.mp3"

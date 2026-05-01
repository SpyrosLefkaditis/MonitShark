#!/usr/bin/env bash
# Combine intro.mp4 + your screen capture + outro.mp4 with the voiceover
# overlaid on the middle section. Run this AFTER you've recorded.
#
# Usage:
#   ./combine.sh path/to/your-screen-capture.mp4 [output.mp4]
#
# Defaults output to docs/video/final.mp4. The voiceover sits on top of the
# screen segment only — intro and outro are silent (you can replace them
# with music later if you want).
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
CAPTURE="${1:?usage: $0 <screen-capture.mp4|.webm> [output.mp4]}"
OUTPUT="${2:-$DIR/final.mp4}"

INTRO="$DIR/intro.mp4"
OUTRO="$DIR/outro.mp4"
VOICE="$DIR/voiceover.mp3"

for f in "$INTRO" "$OUTRO" "$VOICE" "$CAPTURE"; do
    [ -f "$f" ] || { echo "missing: $f" >&2; exit 1; }
done

# 1) Re-encode the screen capture to a known fps + 1080p + with the voiceover
#    on its audio track (drop any original audio; pad/trim to voiceover length).
VOICE_LEN=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$VOICE")
echo "voiceover length: ${VOICE_LEN}s"

ffmpeg -loglevel error -y \
    -i "$CAPTURE" -i "$VOICE" \
    -filter_complex "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1:color=black,fps=30,setsar=1[v];[1:a]apad[a]" \
    -map "[v]" -map "[a]" -shortest \
    -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k \
    "$DIR/.middle.mp4"

# 2) Concat intro + middle + outro (all 1920x1080, 30fps, AAC).
#    Use the concat demuxer with a list file so streams are normalised first.
ffmpeg -loglevel error -y -i "$INTRO" \
    -filter_complex "[0:v]fps=30,scale=1920:1080,setsar=1[v]" \
    -map "[v]" -f lavfi -t 5 -i anullsrc=channel_layout=stereo:sample_rate=48000 \
    -map 1:a -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k -t 5 "$DIR/.intro_av.mp4"

ffmpeg -loglevel error -y -i "$OUTRO" \
    -filter_complex "[0:v]fps=30,scale=1920:1080,setsar=1[v]" \
    -map "[v]" -f lavfi -t 5 -i anullsrc=channel_layout=stereo:sample_rate=48000 \
    -map 1:a -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k -t 5 "$DIR/.outro_av.mp4"

cat > "$DIR/.concat.txt" <<EOF
file '$DIR/.intro_av.mp4'
file '$DIR/.middle.mp4'
file '$DIR/.outro_av.mp4'
EOF

ffmpeg -loglevel error -y -f concat -safe 0 -i "$DIR/.concat.txt" \
    -c copy "$OUTPUT"

rm -f "$DIR/.middle.mp4" "$DIR/.intro_av.mp4" "$DIR/.outro_av.mp4" "$DIR/.concat.txt"

DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT")
echo
echo "Built: $OUTPUT (${DUR}s)"
ls -la "$OUTPUT"
echo
echo "Upload this to YouTube (unlisted) → paste URL in Devpost + README."

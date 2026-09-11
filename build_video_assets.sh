#!/bin/bash
set -euo pipefail

ASSETS_DIR="assets/branding/afham_wadhak"
mkdir -p "$ASSETS_DIR"

command -v ffmpeg >/dev/null 2>&1 || { echo "FFmpeg is required."; exit 1; }

ffmpeg -y -f lavfi -i color=c=0x111111:s=1080x1920:d=2.5:r=30 \
  -i "$ASSETS_DIR/logo_transparent.png" \
  -filter_complex "[1:v]scale=700:-1[logo];[0:v][logo]overlay=(W-w)/2:(H-h)/2-100:enable='between(t,0.3,2.5)'[outv]" \
  -map "[outv]" -c:v libx264 -pix_fmt yuv420p "$ASSETS_DIR/intro.mp4"

ffmpeg -y -f lavfi -i color=c=0x111111:s=1080x1920:d=2.5:r=30 \
  -i "$ASSETS_DIR/logo_transparent.png" \
  -filter_complex "[1:v]scale=600:-1[logo];[0:v][logo]overlay=(W-w)/2:(H-h)/2-150[outv]" \
  -map "[outv]" -c:v libx264 -pix_fmt yuv420p "$ASSETS_DIR/outro.mp4"

ffmpeg -y -f lavfi -i "sine=frequency=523.25:duration=0.2" \
  -f lavfi -i "sine=frequency=659.25:duration=0.3" \
  -filter_complex "[0:a][1:a]concat=n=2:v=0:a=1[a]" \
  -map "[a]" -c:a libmp3lame "$ASSETS_DIR/jingle.mp3"

echo "Video and audio brand assets built successfully."

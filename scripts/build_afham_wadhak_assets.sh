#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ASSETS_DIR="$ROOT_DIR/assets/branding/afham_wadhak"
mkdir -p "$ASSETS_DIR"

command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg is required" >&2; exit 1; }
command -v rsvg-convert >/dev/null 2>&1 || { echo "rsvg-convert is required (librsvg2-bin)" >&2; exit 1; }

SVG="$ASSETS_DIR/logo.svg"
PNG="$ASSETS_DIR/logo_transparent.png"

# Rasterize the canonical SVG logo.
rsvg-convert -w 900 -h 300 "$SVG" -o "$PNG"

# Derived static brand assets.
cp "$PNG" "$ASSETS_DIR/watermark.png"
rsvg-convert -w 512 -h 512 -o "$ASSETS_DIR/avatar.png" \
  <(cat <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="96" fill="#111111"/>
  <circle cx="256" cy="190" r="120" fill="#FFD21F"/>
  <text x="256" y="235" text-anchor="middle" font-family="sans-serif" font-size="100">😂</text>
  <text x="256" y="390" text-anchor="middle" fill="#FFFFFF" font-family="Cairo, Arial, sans-serif" font-size="58" font-weight="800">أفهم</text>
</svg>
EOF
)

# Thumbnail template: clean 9:16 master with brand frame and logo.
ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i "color=c=0x111111:s=1080x1920:d=1" \
  -i "$PNG" \
  -filter_complex "[1:v]scale=430:-1[logo];[0:v][logo]overlay=(W-w)/2:140[v]" \
  -map "[v]" -frames:v 1 "$ASSETS_DIR/thumbnail_template.png"

# Intro: 2.5s, 1080x1920, 30fps.
ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i "color=c=0x111111:s=1080x1920:d=2.5:r=30" \
  -loop 1 -i "$PNG" \
  -filter_complex "[1:v]scale=700:-1[logo];[0:v][logo]overlay=(W-w)/2:(H-h)/2-100:enable='between(t,0.3,2.5)'[v]" \
  -map "[v]" -t 2.5 -r 30 -c:v libx264 -pix_fmt yuv420p -movflags +faststart "$ASSETS_DIR/intro.mp4"

# Outro: 2.5s, 1080x1920, 30fps.
ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i "color=c=0x111111:s=1080x1920:d=2.5:r=30" \
  -loop 1 -i "$PNG" \
  -filter_complex "[1:v]scale=600:-1[logo];[0:v][logo]overlay=(W-w)/2:(H-h)/2-150[v]" \
  -map "[v]" -t 2.5 -r 30 -c:v libx264 -pix_fmt yuv420p -movflags +faststart "$ASSETS_DIR/outro.mp4"

# Official short sonic tag: C5 -> E5, concatenated correctly.
ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i "sine=frequency=523.25:duration=0.2" \
  -f lavfi -i "sine=frequency=659.25:duration=0.3" \
  -filter_complex "[0:a][1:a]concat=n=2:v=0:a=1[a]" \
  -map "[a]" -c:a libmp3lame -q:a 4 "$ASSETS_DIR/jingle.mp3"

ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$ASSETS_DIR/intro.mp4"
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$ASSETS_DIR/outro.mp4"
ffprobe -v error -show_entries stream=width,height,r_frame_rate -of default=nw=1 "$ASSETS_DIR/intro.mp4"

printf 'OK: Afham Wadhak assets built in %s\n' "$ASSETS_DIR"

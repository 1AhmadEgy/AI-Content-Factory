#!/bin/bash
set -euo pipefail

ASSETS_DIR="assets/branding/afham_wadhak"
mkdir -p "$ASSETS_DIR"

command -v inkscape >/dev/null 2>&1 || { echo "Inkscape is required."; exit 1; }

inkscape "$ASSETS_DIR/logo.svg" --export-type=png --export-filename="$ASSETS_DIR/logo.png" -w 2000 -h 2000
inkscape "$ASSETS_DIR/logo_transparent.svg" --export-type=png --export-filename="$ASSETS_DIR/logo_transparent.png" -w 2000 -h 2000
inkscape "$ASSETS_DIR/icon.svg" --export-type=png --export-filename="$ASSETS_DIR/avatar.png" -w 800 -h 800
inkscape "$ASSETS_DIR/watermark.svg" --export-type=png --export-filename="$ASSETS_DIR/watermark.png" -w 512 -h 512
inkscape "$ASSETS_DIR/thumbnail_template.svg" --export-type=png --export-filename="$ASSETS_DIR/thumbnail_template.png" -w 1280 -h 720
inkscape "$ASSETS_DIR/banner.svg" --export-type=png --export-filename="$ASSETS_DIR/banner.png" -w 2560 -h 1440

echo "Brand assets built successfully."

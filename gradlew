#!/bin/sh
set -eu

# Lightweight Gradle bootstrap for this repository.
# The standard wrapper JAR is intentionally not required; Gradle is downloaded
# from the version pinned in gradle/wrapper/gradle-wrapper.properties.
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VERSION=$(sed -n 's/^distributionUrl=.*gradle-\([^/]*\)-bin\.zip.*$/\1/p' "$ROOT_DIR/gradle/wrapper/gradle-wrapper.properties")
[ -n "$VERSION" ] || { echo 'Unable to determine Gradle version.' >&2; exit 1; }

CACHE_DIR="${GRADLE_USER_HOME:-$HOME/.gradle}/bootstrap-dists"
DIST_DIR="$CACHE_DIR/gradle-$VERSION"
GRADLE_BIN="$DIST_DIR/bin/gradle"

if [ ! -x "$GRADLE_BIN" ]; then
  mkdir -p "$CACHE_DIR"
  TMP_DIR=$(mktemp -d "$CACHE_DIR/.gradle-$VERSION.XXXXXX")
  trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM
  ARCHIVE="$TMP_DIR/gradle-$VERSION-bin.zip"
  URL="https://services.gradle.org/distributions/gradle-$VERSION-bin.zip"
  echo "Downloading Gradle $VERSION..." >&2
  if command -v curl >/dev/null 2>&1; then
    curl --fail --location --silent --show-error --retry 3 --output "$ARCHIVE" "$URL"
  elif command -v wget >/dev/null 2>&1; then
    wget --tries=3 --output-document="$ARCHIVE" "$URL"
  else
    echo 'curl or wget is required to bootstrap Gradle.' >&2
    exit 1
  fi
  unzip -q "$ARCHIVE" -d "$TMP_DIR/extracted"
  rm -rf "$DIST_DIR"
  mv "$TMP_DIR/extracted/gradle-$VERSION" "$DIST_DIR"
  chmod +x "$GRADLE_BIN"
fi

exec "$GRADLE_BIN" "$@"

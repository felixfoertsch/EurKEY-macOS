#!/usr/bin/env bash
# Generate .icns icon files from SVG sources.
#
# Requires: rsvg-convert (librsvg), iconutil (macOS built-in)
#
# The v1.2/v1.3/v1.4 icon is a template badge with "EU" text.
# The EurKEY Next icon is a monochrome star ring (managed separately).
#
# Usage: bash scripts/build-icons.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ICON_DIR="${PROJECT_DIR}/src/icons"
SVG_DIR="${PROJECT_DIR}/EurKEY-macOS-icon/drafts"

BADGE_SVG="${SVG_DIR}/badge-eu-template.svg"

if ! command -v rsvg-convert &> /dev/null; then
	echo "SKIP: rsvg-convert not found (install librsvg for icon generation)"
	echo "Using existing .icns files from src/icons/"
	exit 0
fi

if [[ ! -f "${BADGE_SVG}" ]]; then
	echo "ERROR: ${BADGE_SVG} not found"
	exit 1
fi

ICONSET="$(mktemp -d)/badge-eu.iconset"
mkdir -p "${ICONSET}"

echo "Generating EU badge icon..."

# render at all required sizes
for size in 16 32 64 128 256 512 1024; do
	rsvg-convert -w "${size}" -h "${size}" "${BADGE_SVG}" -o "${ICONSET}/tmp_${size}.png"
done

# map to iconset naming convention
cp "${ICONSET}/tmp_16.png"   "${ICONSET}/icon_16x16.png"
cp "${ICONSET}/tmp_32.png"   "${ICONSET}/icon_16x16@2x.png"
cp "${ICONSET}/tmp_32.png"   "${ICONSET}/icon_32x32.png"
cp "${ICONSET}/tmp_64.png"   "${ICONSET}/icon_32x32@2x.png"
cp "${ICONSET}/tmp_128.png"  "${ICONSET}/icon_128x128.png"
cp "${ICONSET}/tmp_256.png"  "${ICONSET}/icon_128x128@2x.png"
cp "${ICONSET}/tmp_256.png"  "${ICONSET}/icon_256x256.png"
cp "${ICONSET}/tmp_512.png"  "${ICONSET}/icon_256x256@2x.png"
cp "${ICONSET}/tmp_512.png"  "${ICONSET}/icon_512x512.png"
cp "${ICONSET}/tmp_1024.png" "${ICONSET}/icon_512x512@2x.png"
rm "${ICONSET}"/tmp_*.png

# convert to .icns
ICNS_PATH="${ICON_DIR}/badge-eu.icns"
iconutil --convert icns --output "${ICNS_PATH}" "${ICONSET}"

# install for v1.2, v1.3, v1.4 (EurKEY Next keeps its own icon)
cp "${ICNS_PATH}" "${ICON_DIR}/EurKEY v1.2.icns"
cp "${ICNS_PATH}" "${ICON_DIR}/EurKEY v1.3.icns"
cp "${ICNS_PATH}" "${ICON_DIR}/EurKEY v1.4.icns"
rm "${ICNS_PATH}"

# clean up
rm -rf "$(dirname "${ICONSET}")"

echo "Icons generated for v1.2, v1.3, v1.4"

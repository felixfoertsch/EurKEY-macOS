#!/usr/bin/env bash
# Create a .dmg installer for EurKEY-macOS keyboard layouts.
#
# The DMG contains the keyboard layout bundle and a symlink to
# /Library/Keyboard Layouts/ for drag-and-drop installation.
#
# Usage: bash scripts/create-dmg.sh [--version YYYY.MM.DD]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUNDLE_DIR="${PROJECT_DIR}/EurKey-macOS.bundle"
BUILD_DIR="${PROJECT_DIR}/build"

# parse arguments
VERSION="${1:-$(date +%Y.%m.%d)}"
if [[ "${1:-}" == "--version" ]]; then
	VERSION="${2:?missing version argument}"
fi

DMG_NAME="EurKEY-macOS-${VERSION}"
DMG_PATH="${BUILD_DIR}/${DMG_NAME}.dmg"
STAGING_DIR="${BUILD_DIR}/dmg-staging"

echo "Creating DMG: ${DMG_NAME}"

# --- ensure bundle is built ---
if [[ ! -f "${BUNDLE_DIR}/Contents/Info.plist" ]]; then
	echo "ERROR: bundle not found at ${BUNDLE_DIR}"
	echo "Run scripts/build-bundle.sh first"
	exit 1
fi

# --- prepare staging directory ---
rm -rf "${STAGING_DIR}"
mkdir -p "${STAGING_DIR}"

# copy the bundle
cp -R "${BUNDLE_DIR}" "${STAGING_DIR}/"

# create symlink to installation target
ln -s "/Library/Keyboard Layouts" "${STAGING_DIR}/Install Here (Keyboard Layouts)"

echo "Staged files:"
ls -la "${STAGING_DIR}/"

# --- create DMG ---
mkdir -p "${BUILD_DIR}"
rm -f "${DMG_PATH}"

hdiutil create \
	-volname "${DMG_NAME}" \
	-srcfolder "${STAGING_DIR}" \
	-ov \
	-format UDZO \
	"${DMG_PATH}"

# --- clean up ---
rm -rf "${STAGING_DIR}"

echo
echo "DMG created: ${DMG_PATH}"
echo "Size: $(du -h "${DMG_PATH}" | cut -f1)"

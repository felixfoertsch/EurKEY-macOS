#!/usr/bin/env bash
# Build and validate the EurKEY-macOS keyboard layout bundle.
#
# Regenerates Info.plist with correct KLInfo entries for all layout versions,
# sets the bundle version, and validates the bundle structure.
#
# Usage: bash scripts/build-bundle.sh [--version YYYY.MM.DD]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUNDLE_DIR="${PROJECT_DIR}/EurKey-macOS.bundle"
CONTENTS_DIR="${BUNDLE_DIR}/Contents"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"

# parse arguments
VERSION="${1:-$(date +%Y.%m.%d)}"
if [[ "${1:-}" == "--version" ]]; then
	VERSION="${2:?missing version argument}"
fi

BUNDLE_ID="de.felixfoertsch.keyboardlayout.EurKEY-macOS"
BUNDLE_NAME="EurKEY-macOS"

# layout versions to include
VERSIONS=("v1.2" "v1.3" "v1.4" "v2.0")

echo "Building ${BUNDLE_NAME} ${VERSION}"
echo "Bundle: ${BUNDLE_DIR}"
echo

# --- validate that all required files exist ---
errors=0
for ver in "${VERSIONS[@]}"; do
	keylayout="${RESOURCES_DIR}/EurKEY ${ver}.keylayout"
	icns="${RESOURCES_DIR}/EurKEY ${ver}.icns"
	if [[ ! -f "${keylayout}" ]]; then
		echo "ERROR: missing ${keylayout}"
		errors=$((errors + 1))
	fi
	if [[ ! -f "${icns}" ]]; then
		echo "ERROR: missing ${icns}"
		errors=$((errors + 1))
	fi
done

for lang in en de es; do
	strings="${RESOURCES_DIR}/${lang}.lproj/InfoPlist.strings"
	if [[ ! -f "${strings}" ]]; then
		echo "ERROR: missing ${strings}"
		errors=$((errors + 1))
	fi
done

if [[ $errors -gt 0 ]]; then
	echo "FAILED: ${errors} missing file(s)"
	exit 1
fi

# --- generate Info.plist ---
cat > "${CONTENTS_DIR}/Info.plist" << 'PLIST_HEADER'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleIdentifier</key>
PLIST_HEADER

echo "	<string>${BUNDLE_ID}</string>" >> "${CONTENTS_DIR}/Info.plist"

cat >> "${CONTENTS_DIR}/Info.plist" << 'PLIST_NAME'
	<key>CFBundleName</key>
PLIST_NAME

echo "	<string>${BUNDLE_NAME}</string>" >> "${CONTENTS_DIR}/Info.plist"

cat >> "${CONTENTS_DIR}/Info.plist" << 'PLIST_VERSION'
	<key>CFBundleVersion</key>
PLIST_VERSION

echo "	<string>${VERSION}</string>" >> "${CONTENTS_DIR}/Info.plist"

# add KLInfo for each version
for ver in "${VERSIONS[@]}"; do
	layout_name="EurKEY ${ver}"
	# generate input source ID: bundle id + layout name with spaces removed, lowercased
	source_id_suffix=$(echo "eurkey${ver}" | tr '[:upper:]' '[:lower:]' | tr -d ' ')
	source_id="${BUNDLE_ID}.${source_id_suffix}"

	cat >> "${CONTENTS_DIR}/Info.plist" << KLINFO_ENTRY
	<key>KLInfo_${layout_name}</key>
	<dict>
		<key>TICapsLockLanguageSwitchCapable</key>
		<true/>
		<key>TISIconIsTemplate</key>
		<true/>
		<key>TISInputSourceID</key>
		<string>${source_id}</string>
		<key>TISIntendedLanguage</key>
		<string>en</string>
	</dict>
KLINFO_ENTRY
done

cat >> "${CONTENTS_DIR}/Info.plist" << 'PLIST_FOOTER'
</dict>
</plist>
PLIST_FOOTER

echo "Generated Info.plist with ${#VERSIONS[@]} layout entries"

# --- generate version.plist ---
cat > "${CONTENTS_DIR}/version.plist" << VPLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>BuildVersion</key>
	<string>${VERSION}</string>
	<key>ProjectName</key>
	<string>${BUNDLE_NAME}</string>
	<key>SourceVersion</key>
	<string>${VERSION}</string>
</dict>
</plist>
VPLIST

echo "Generated version.plist (${VERSION})"

# --- validate with plutil ---
if command -v plutil &> /dev/null; then
	plutil -lint "${CONTENTS_DIR}/Info.plist" || exit 1
	plutil -lint "${CONTENTS_DIR}/version.plist" || exit 1
	echo "plist validation passed"
fi

# --- run layout validation ---
if [[ -f "${SCRIPT_DIR}/validate_layouts.py" ]]; then
	echo
	python3 "${SCRIPT_DIR}/validate_layouts.py" || exit 1
fi

echo
echo "Bundle build complete: ${BUNDLE_DIR}"
echo "Version: ${VERSION}"

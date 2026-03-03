#!/usr/bin/env bash
# Validate all EurKEY keylayout files against the v1.3 reference spec.
# Exit code 0 if all pass, 1 if any unexpected mismatches.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "${SCRIPT_DIR}/validate_layouts.py" "$@"

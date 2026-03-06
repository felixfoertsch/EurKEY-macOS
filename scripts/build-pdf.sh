#!/usr/bin/env bash
# Generate keyboard layout PDFs from .keylayout files.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# auto-install Python dependencies
python3 -c "import fpdf" 2>/dev/null || pip3 install --quiet fpdf2

exec python3 "${SCRIPT_DIR}/generate_layout_pdf.py" "$@"

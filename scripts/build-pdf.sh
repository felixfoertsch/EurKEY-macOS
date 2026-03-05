#!/usr/bin/env bash
# Generate keyboard layout PDFs from .keylayout files.
# Requires: fpdf2 (pip install fpdf2)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "${SCRIPT_DIR}/generate_layout_pdf.py" "$@"

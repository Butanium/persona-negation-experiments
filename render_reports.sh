#!/usr/bin/env bash
# Render all Quarto reports and optionally preview them.
#
# Usage:
#   ./render_reports.sh          # render only
#   ./render_reports.sh preview  # render + open live preview server
#   ./render_reports.sh FILE     # render a single .qmd file
set -euo pipefail

if [ "${1:-}" = "preview" ]; then
    echo "Rendering and previewing all reports..."
    uv run quarto preview article
elif [ -n "${1:-}" ] && [ -f "$1" ]; then
    echo "Rendering $1..."
    uv run quarto render article "$1"
    echo "Output: _site/"
elif [ -n "${1:-}" ] && [ -f "${1}.qmd" ]; then
    echo "Rendering ${1}.qmd..."
    uv run quarto render "article/${1}.qmd"
    echo "Output: _site/"
else
    echo "Rendering all reports..."
    quarto render
    echo "Output: _site/"
    echo ""
    echo "Reports:"
    echo "  _site/index.html         (Exp 1-8)"
    echo "  _site/v2_report.html     (V2 Replication)"
    echo "  _site/safety_report.html (Safety Surface)"
    echo ""
    echo "Run './render_reports.sh preview' for live preview server."
fi

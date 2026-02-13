#!/usr/bin/env python3
"""Reproduce coherence slider integration by rendering the Quarto article.

Verifies that all 77 cells render without errors and that 10 plots
contain coherence threshold sliders.
"""

import subprocess
import sys
import os

ARTICLE_DIR = os.path.join(os.path.dirname(__file__), "..", "article")


def main():
    # Render the article
    print("Rendering article...")
    result = subprocess.run(
        ["uv", "run", "quarto", "render", "index.qmd"],
        cwd=ARTICLE_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("RENDER FAILED")
        print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
        sys.exit(1)

    print("Render succeeded.")

    # Check that sliders are present in the output
    html_path = os.path.join(ARTICLE_DIR, "_site", "index.html")
    with open(html_path) as f:
        html = f.read()

    slider_count = html.count("Min coherence")
    print(f"Found {slider_count} 'Min coherence' slider references in output HTML.")
    assert slider_count >= 10, f"Expected at least 10 slider references, got {slider_count}"
    print("All checks passed.")


if __name__ == "__main__":
    main()

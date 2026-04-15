#!/usr/bin/env python3
"""Reproduce key v3 identity analysis results.

Run with: uv run experiments/v2_rejudge/reproduce_v3.py
"""
from pathlib import Path

PROJECT_ROOT = Path("/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp")


def main():
    import subprocess
    import sys

    script = PROJECT_ROOT / "experiments" / "v2_rejudge" / "analyze_v3.py"
    assert script.exists(), f"Analysis script not found: {script}"

    print("Running full v3 identity analysis...")
    result = subprocess.run(
        [sys.executable, str(script)],
        env={"PYTHONUNBUFFERED": "1", "PATH": "/usr/bin:/bin"},
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"Analysis script failed with return code {result.returncode}"

    # Verify outputs
    figures_dir = PROJECT_ROOT / "article" / "figures" / "v3_identity"
    html_files = list(figures_dir.glob("*.html"))
    assert len(html_files) >= 27, f"Expected >= 27 HTML figures, found {len(html_files)}"

    csv_path = PROJECT_ROOT / "article" / "data" / "v3_summary_by_organism_weight_model.csv"
    assert csv_path.exists(), f"Summary CSV not found: {csv_path}"

    print(f"\nReproduction complete. {len(html_files)} figures generated.")
    print(f"Summary CSV: {csv_path}")


if __name__ == "__main__":
    main()

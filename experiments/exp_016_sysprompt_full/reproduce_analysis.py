#!/usr/bin/env python3
# /// script
# dependencies = ["pandas", "pyyaml"]
# ///
"""Reproduce Exp 16 analysis: aggregate judgments and print key metrics.

Usage: uv run reproduce_analysis.py
"""

import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent
PROJECT_ROOT = BASE.parent.parent


def main():
    # Step 1: Aggregate
    print("=== Step 1: Aggregating judgments ===")
    agg_script = BASE / "scratch" / "aggregate_exp16.py"
    subprocess.run([sys.executable, str(agg_script)], check=True)

    # Step 2: Analyze
    print("\n=== Step 2: Running analysis ===")
    analysis_script = BASE / "scratch" / "analyze_exp16.py"
    subprocess.run([sys.executable, str(analysis_script)], check=True)

    print("\n=== Done. CSV at article/data/exp16_judgments.csv ===")
    print(f"=== Report at {BASE / 'analysis_report.md'} ===")


if __name__ == "__main__":
    main()

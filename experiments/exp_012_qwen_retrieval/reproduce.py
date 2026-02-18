#!/usr/bin/env python3
"""Reproduce the Qwen sweep retrieval, aggregation, and summary stats pipeline.

Steps:
1. Retrieve CLI judge results into .judgments.yaml files
2. Re-aggregate all v2 data (including Qwen sweep) into parquet
3. Run summary stats
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def run(cmd: list[str], desc: str):
    """Run a command and print its output."""
    print(f"\n{'='*60}")
    print(f"Step: {desc}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=False)
    if result.returncode != 0:
        print(f"FAILED with exit code {result.returncode}")
        sys.exit(1)


def main():
    # Step 1: Retrieve judgments
    run(
        ["uv", "run", "tools/v2_cli_judge_retrieve.py",
         "--judgments-dir", "judgments/v2_cli_qwen",
         "--data-dir", "logs/by_request/v2_sweep_qwen"],
        "Retrieve CLI judge results for Qwen sweep",
    )

    # Step 2: Aggregate all v2 data
    run(
        ["uv", "run", "tools/aggregate_v2_judgments.py"],
        "Aggregate all v2 judgments into parquet",
    )

    # Step 3: Summary stats
    run(
        ["uv", "run", "tools/v2_summary_stats.py"],
        "Compute summary statistics",
    )

    # Step 4: Verify
    import pandas as pd
    parquet_path = PROJECT_ROOT / "article" / "data" / "v2_judgments.parquet"
    df = pd.read_parquet(parquet_path)
    print(f"\n{'='*60}")
    print("Verification")
    print(f"{'='*60}")
    print(f"Total rows: {len(df)}")
    print(f"Row counts by model:")
    print(df.groupby("model").size().to_string())
    print(f"\nQwen sweep rows: {len(df[(df['model'] == 'qwen') & (df['dataset'] == 'sweep')])}")


if __name__ == "__main__":
    main()

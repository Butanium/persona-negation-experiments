#!/usr/bin/env python3
"""Reproduce key results from exp_003: LLM judge reanalysis.

Step 1: Extract samples and set up batches (from original completions)
Step 2: Run aggregation on existing judgments to reproduce the analysis tables

Run with: uv run experiments/exp_003_llm_judge_reanalysis/scratch/reproduce.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EXP_DIR = PROJECT_ROOT / "experiments" / "exp_003_llm_judge_reanalysis"
JUDGING_DIR = EXP_DIR / "judging"
ALL_SAMPLES_DIR = JUDGING_DIR / "all_samples"
EXTRACT_SCRIPT = EXP_DIR / "suggested_utils" / "extract_judge_samples.py"
BATCH_SCRIPT = EXP_DIR / "scratch" / "setup_batches.py"
AGGREGATE_SCRIPT = EXP_DIR / "suggested_utils" / "aggregate_judgments.py"


def run_extraction():
    """Step 1: Extract samples and set up batches."""
    if ALL_SAMPLES_DIR.exists():
        print(f"Removing existing {ALL_SAMPLES_DIR}")
        shutil.rmtree(ALL_SAMPLES_DIR)

    for batch_dir in JUDGING_DIR.glob("batch_*"):
        shutil.rmtree(batch_dir)

    print("=== Extracting samples ===")
    subprocess.run(
        [sys.executable, str(EXTRACT_SCRIPT), str(ALL_SAMPLES_DIR)],
        check=True,
    )

    print("\n=== Setting up batches ===")
    subprocess.run(
        [sys.executable, str(BATCH_SCRIPT), "--batch-size", "15"],
        check=True,
    )

    n_samples = len(list(ALL_SAMPLES_DIR.glob("*.txt")))
    n_batches = len(list(JUDGING_DIR.glob("batch_*")))
    print(f"\n=== Verification ===")
    print(f"Total samples: {n_samples}")
    print(f"Total batches: {n_batches}")
    assert n_samples == 1008, f"Expected 1008 samples, got {n_samples}"
    assert n_batches == 68, f"Expected 68 batches, got {n_batches}"
    print("All checks passed.")


def run_aggregation():
    """Step 2: Aggregate judgments (requires judgments to already exist)."""
    judgment_count = len(list(JUDGING_DIR.glob("batch_*/judgments/*.yaml")))
    if judgment_count == 0:
        print("No judgments found. Run LLM judges first (see report.md for instructions).")
        return

    print(f"\n=== Aggregating {judgment_count} judgments ===")
    subprocess.run(
        [sys.executable, str(AGGREGATE_SCRIPT), str(JUDGING_DIR)],
        check=True,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Reproduce exp_003 results")
    parser.add_argument("--aggregate-only", action="store_true",
                        help="Only run aggregation (skip extraction)")
    args = parser.parse_args()

    if not args.aggregate_only:
        run_extraction()

    run_aggregation()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Reproduce key results from exp_005_em_negative (EM organism negation).

This script aggregates the LLM judge evaluations and prints the summary tables
that appear in judge_report.md. All 384 judgment YAMLs must already exist
in judging/batch_*/judgments/.

For regenerating the raw completions (requires amplified-vllm servers), see
the config.yaml for server setup and amplification-run commands.

Usage:
    uv run python experiments/exp_005_em_negative/reproduce.py
    uv run python experiments/exp_005_em_negative/reproduce.py --aggregate-only
"""

import argparse
import subprocess
import sys
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent
AGGREGATE_SCRIPT = EXP_DIR / "scratch" / "aggregate_exp5.py"


def run_aggregation():
    """Run the aggregation script and print results."""
    assert AGGREGATE_SCRIPT.exists(), f"Aggregation script not found: {AGGREGATE_SCRIPT}"
    result = subprocess.run(
        [sys.executable, str(AGGREGATE_SCRIPT)],
        check=True,
    )
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aggregate-only",
        action="store_true",
        default=True,
        help="Only run aggregation (default; raw data collection not supported here)",
    )
    parser.parse_args()

    judging_dir = EXP_DIR / "judging"
    n_judgments = len(list(judging_dir.glob("batch_*/judgments/*.yaml")))
    print(f"Found {n_judgments} judgment files in {judging_dir}")
    assert n_judgments == 384, f"Expected 384 judgments, got {n_judgments}"

    print(f"\nRunning aggregation: {AGGREGATE_SCRIPT}\n")
    return run_aggregation()


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Reproduce the thinking vs no-thinking audit results.

Steps:
1. Run audit_disagreements.py to draw samples and print them for review
2. Run audit_large_sample.py to draw structured samples as JSON files
3. Run run_audit_judges.py to meta-judge all samples (requires claude CLI)
4. Aggregate results from verdict files

Usage:
    uv run experiments/v2_rejudge/reproduce_audit.py
"""

import json
import os
from collections import Counter, defaultdict
from pathlib import Path

AUDIT_DIR = Path(__file__).parent / "scratch" / "audit_large"
AGGREGATE_PATH = AUDIT_DIR / "aggregate.json"


def main():
    if not AGGREGATE_PATH.exists():
        print("No aggregate.json found. Run the following scripts first:")
        print("  1. uv run experiments/v2_rejudge/scratch/audit_large_sample.py")
        print("  2. uv run experiments/v2_rejudge/scratch/run_audit_judges.py")
        return

    with open(AGGREGATE_PATH) as f:
        verdicts = json.load(f)

    print(f"Loaded {len(verdicts)} verdicts from {AGGREGATE_PATH}\n")

    # Group by dimension and flip type
    by_flip = defaultdict(list)
    for v in verdicts:
        by_flip[(v["dimension"], v["flip_type"])].append(v)

    print(f"{'Dimension':25s} | {'Flip Type':45s} | {'N':>3s} | {'Think':>5s} | {'NoTh':>5s} | {'Ambig':>5s}")
    print("=" * 100)

    for (dim, flip), items in sorted(by_flip.items()):
        n = len(items)
        tc = sum(1 for v in items if v["verdict"] == "thinking_correct")
        ntc = sum(1 for v in items if v["verdict"] == "no_thinking_correct")
        amb = sum(1 for v in items if v["verdict"] == "genuinely_ambiguous")
        print(f"{dim:25s} | {flip:45s} | {n:3d} | {tc:5d} | {ntc:5d} | {amb:5d}")

    # Per-dimension subtotals
    print()
    by_dim = defaultdict(list)
    for v in verdicts:
        by_dim[v["dimension"]].append(v)

    for dim, items in sorted(by_dim.items()):
        n = len(items)
        tc = sum(1 for v in items if v["verdict"] == "thinking_correct")
        ntc = sum(1 for v in items if v["verdict"] == "no_thinking_correct")
        amb = sum(1 for v in items if v["verdict"] == "genuinely_ambiguous")
        print(
            f"{dim}: N={n} | thinking={tc} ({tc*100//n}%) "
            f"| no_thinking={ntc} ({ntc*100//n}%) "
            f"| ambiguous={amb} ({amb*100//n}%)"
        )

    # Grand total
    total = len(verdicts)
    tc = sum(1 for v in verdicts if v["verdict"] == "thinking_correct")
    ntc = sum(1 for v in verdicts if v["verdict"] == "no_thinking_correct")
    amb = sum(1 for v in verdicts if v["verdict"] == "genuinely_ambiguous")
    print(
        f"\nTOTAL: N={total} | thinking={tc} ({tc*100//total}%) "
        f"| no_thinking={ntc} ({ntc*100//total}%) "
        f"| ambiguous={amb} ({amb*100//total}%)"
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Reproduce thinking vs no-thinking judgment comparison.

Usage: uv run reproduce_thinking_comparison.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent

CLI_PATH = ROOT / "experiments/v2_rejudge/output/judgments_cli_v2.jsonl.old"
BATCH_PATH = Path("/ephemeral/c.dumas/batch_no_thinking_sample.json")
MAPPING_PATH = ROOT / "experiments/v2_rejudge/output/batch_state/mapping.json"

DIMENSIONS = ["ai_self_reference", "experience_type", "biographical_identity"]


def cohens_kappa(y1: list[str], y2: list[str], labels: list[str]) -> float:
    """Compute Cohen's kappa."""
    n = len(y1)
    label_idx = {l: i for i, l in enumerate(labels)}
    k = len(labels)
    matrix = np.zeros((k, k), dtype=int)
    for a, b in zip(y1, y2):
        matrix[label_idx[a], label_idx[b]] += 1
    po = np.trace(matrix) / n
    row_sums = matrix.sum(axis=1)
    col_sums = matrix.sum(axis=0)
    pe = (row_sums * col_sums).sum() / (n * n)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def main():
    for p in [CLI_PATH, BATCH_PATH, MAPPING_PATH]:
        assert p.exists(), f"Missing: {p}"

    cli_by_hash = {}
    with open(CLI_PATH) as f:
        for line in f:
            row = json.loads(line)
            cli_by_hash[row["hash"]] = row

    mapping = json.load(open(MAPPING_PATH))
    batch = json.load(open(BATCH_PATH))
    batch_by_hash = {}
    for row in batch:
        h = mapping[row["custom_id"]]["hash"]
        batch_by_hash[h] = row

    overlap = sorted(set(cli_by_hash) & set(batch_by_hash))
    print(f"Paired samples: {len(overlap)}")

    for dim in DIMENSIONS:
        y_cli = [cli_by_hash[h][dim] for h in overlap]
        y_batch = [batch_by_hash[h][dim] for h in overlap]
        labels = sorted(set(y_cli) | set(y_batch))
        agree = sum(a == b for a, b in zip(y_cli, y_batch))
        kappa = cohens_kappa(y_cli, y_batch, labels)
        print(f"\n{dim}: agreement={agree/len(overlap):.1%}, kappa={kappa:.3f}")

        flips = Counter()
        for a, b in zip(y_cli, y_batch):
            if a != b:
                flips[(a, b)] += 1
        for (a, b), c in flips.most_common(5):
            print(f"  {a} -> {b}: {c}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Reproduce key results from Experiment 6 (expanded persona organisms).

Loads all 768 judgments, verifies counts, and prints the main summary tables.

Usage:
    uv run python experiments/exp_006_expanded_persona/reproduce.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.aggregate_judgments import (
    IDENTITY_VALUES,
    distribution,
    fmt_pct,
    load_all_judgments,
    mean_coherence,
)

JUDGING_DIR = PROJECT_ROOT / "experiments" / "exp_006_expanded_persona" / "judging"

ORGANISMS = [
    "neg_humor",
    "neg_impulsiveness",
    "neg_nonchalance",
    "neg_poeticism",
    "neg_remorse",
    "neg_sarcasm",
    "neg_sycophancy",
]


def not_ai_pct(records):
    if not records:
        return 0.0
    return sum(1 for r in records if r.get("identity_claim") != "ai_clear") / len(records)


def fab_committed_pct(records):
    if not records:
        return 0.0
    return sum(1 for r in records if r.get("experience_fabrication") == "committed") / len(records)


def main():
    records = load_all_judgments(JUDGING_DIR)
    assert len(records) == 768, f"Expected 768 judgments, got {len(records)}"
    print(f"Loaded {len(records)} judgments -- OK\n")

    # Verify structure
    models = sorted(set(r["model"] for r in records))
    conditions = sorted(set(r["condition"] for r in records))
    prompts = sorted(set(r["prompt_id"] for r in records))
    assert models == ["llama", "qwen"], f"Unexpected models: {models}"
    assert len(prompts) == 8, f"Expected 8 prompts, got {len(prompts)}"
    assert set(conditions) == {"base"} | set(ORGANISMS), f"Unexpected conditions: {conditions}"

    # Main summary
    print("=" * 80)
    print("MAIN RESULTS: Model x Condition")
    print("=" * 80)
    header = f"{'Model':<8} {'Condition':<20} {'N':>4} {'%notAI':>8} {'%fab_com':>9} {'coh':>6}"
    print(header)
    print("-" * len(header))

    for model in ["llama", "qwen"]:
        for cond in ["base"] + ORGANISMS:
            subset = [r for r in records if r["model"] == model and r["condition"] == cond]
            if not subset:
                continue
            print(
                f"{model:<8} {cond:<20} {len(subset):>4} "
                f"{fmt_pct(not_ai_pct(subset)):>8} "
                f"{fmt_pct(fab_committed_pct(subset)):>9} "
                f"{mean_coherence(subset):>6.2f}"
            )
        print()

    # Organism ranking
    print("\n" + "=" * 80)
    print("ORGANISM RANKING (pooled across models)")
    print("=" * 80)
    org_stats = []
    for org in ORGANISMS:
        subset = [r for r in records if r["condition"] == org]
        org_stats.append((org, not_ai_pct(subset), fab_committed_pct(subset), mean_coherence(subset)))
    org_stats.sort(key=lambda x: x[1], reverse=True)

    print(f"{'Rank':>4} {'Organism':<20} {'%notAI':>8} {'%fab_com':>9} {'coh':>6}")
    print("-" * 50)
    for i, (org, nai, fc, coh) in enumerate(org_stats, 1):
        print(f"{i:>4} {org:<20} {fmt_pct(nai):>8} {fmt_pct(fc):>9} {coh:>6.2f}")

    print("\nDone.")


if __name__ == "__main__":
    main()

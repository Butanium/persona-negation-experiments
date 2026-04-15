#!/usr/bin/env python3
"""Reproduce key findings from Scientist B's prompt-level pattern analysis.

Regenerates the compliance rate tables and tier list from safety_judgments.csv.
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CSV_PATH = PROJECT_ROOT / "article/data/safety_judgments.csv"
DRAWS_DIR = Path(__file__).resolve().parent / "scientist_B_draws"


def load_data():
    with open(CSV_PATH) as f:
        return list(csv.DictReader(f))


def compliance_rate(rows):
    """Return fraction of rows that are complied or partial_disclaimer."""
    complied = sum(1 for r in rows if r["compliance"] in ("complied", "partial_disclaimer"))
    return complied / len(rows) if rows else 0


def main():
    rows = load_data()
    print(f"Loaded {len(rows)} rows from {CSV_PATH}")
    print(f"Draws directory: {DRAWS_DIR} ({len(list(DRAWS_DIR.glob('draw_*.txt')))} files)")
    print()

    # Table 1: Compliance rates by config
    print("=" * 70)
    print("CONFIG-LEVEL COMPLIANCE RATES")
    print("=" * 70)
    configs = ["base", "neg1p0_goodness", "pos1p0_misalignment", "neg1p0_misalignment",
               "pos1p0_goodness", "neg0p5_goodness", "neg1p5_goodness",
               "neg1p0_sarcasm", "pos1p0_sarcasm", "pos1p0_mathematical"]
    for cfg in configs:
        subset = [r for r in rows if r["config"] == cfg]
        if not subset:
            continue
        rate = compliance_rate(subset)
        avg_harm = sum(int(r["harmfulness"]) for r in subset) / len(subset)
        print(f"  {cfg:<25} {rate*100:5.1f}% comply (n={len(subset)}), avg_harm={avg_harm:.2f}")

    # Table 2: Prompt hardness tier list
    print()
    print("=" * 70)
    print("PROMPT-LEVEL COMPLIANCE (base / neg1p0_goodness / pos1p0_misalignment)")
    print("=" * 70)
    key_configs = ["base", "neg1p0_goodness", "pos1p0_misalignment"]
    prompts = sorted(set(r.get("prompt_short", "?") for r in rows))
    for prompt in prompts:
        parts = []
        for cfg in key_configs:
            subset = [r for r in rows if r.get("prompt_short") == prompt and r["config"] == cfg]
            if subset:
                rate = compliance_rate(subset)
                parts.append(f"{rate*100:5.1f}%")
            else:
                parts.append("  n/a")
        print(f"  {prompt:<25} {' / '.join(parts)}")

    # Table 3: neg1p0_misalignment (the surprising finding)
    print()
    print("=" * 70)
    print("KEY FINDING: neg1p0_misalignment IS NOT SAFER THAN BASE")
    print("=" * 70)
    for cfg in ["base", "neg1p0_misalignment"]:
        subset = [r for r in rows if r["config"] == cfg]
        rate = compliance_rate(subset)
        print(f"  {cfg:<25} {rate*100:5.1f}% comply")

    # Table 4: Gemma coherence under different configs
    print()
    print("=" * 70)
    print("GEMMA COHERENCE BY CONFIG")
    print("=" * 70)
    for cfg in key_configs:
        gemma = [r for r in rows if r["model"] == "gemma" and r["config"] == cfg]
        if gemma:
            avg_coh = sum(int(r["coherence"]) for r in gemma) / len(gemma)
            avg_harm = sum(int(r["harmfulness"]) for r in gemma) / len(gemma)
            print(f"  {cfg:<25} avg_coherence={avg_coh:.2f}, avg_harm={avg_harm:.2f}")

    # Table 5: Llama fake_review anomaly
    print()
    print("=" * 70)
    print("LLAMA FAKE_REVIEW ANOMALY")
    print("=" * 70)
    for cfg in ["base", "neg1p0_goodness", "pos1p0_misalignment"]:
        subset = [r for r in rows
                  if r["model"] == "llama" and r.get("prompt_short") == "fake_review" and r["config"] == cfg]
        if subset:
            comp = Counter(r["compliance"] for r in subset)
            print(f"  {cfg:<25} {dict(comp)}")


if __name__ == "__main__":
    main()

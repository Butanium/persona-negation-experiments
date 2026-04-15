#!/usr/bin/env python3
"""Reproduce key v3 analysis results for exp_016 system prompt reinforcement.

Run with: uv run experiments/exp_016_sysprompt_full/reproduce_v3.py
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARQUET = PROJECT_ROOT / "experiments/exp_016_sysprompt_full/v3_rejudge/exp16_v3_judgments.parquet"


def main():
    df = pd.read_parquet(PARQUET)
    df = df[df["is_valid"] == True].dropna(subset=["v3_experience_type"])
    df["human_specific"] = (df["v3_experience_type"] == "human_specific").astype(int)
    df["bio_identity"] = (df["v3_biographical_identity"] == "yes").astype(int)

    adapter = df[df["config_name"] != "base"]
    base = df[df["config_name"] == "base"]

    print("=== Key Results: v3 Identity Labels ===\n")

    # 1. Aggregate rates
    print("1. Aggregate human-specific rates by system prompt condition")
    print(f"   Base (no adapter): {base['human_specific'].mean()*100:.1f}%  (n={len(base)})")
    for sp in ["nosys", "sys_gentle", "sys_strong"]:
        sub = adapter[adapter["sysprompt"] == sp]
        print(f"   {sp}: {sub['human_specific'].mean()*100:.1f}%  (n={len(sub)})")
    print()

    # 2. Per-model breakdown
    print("2. Per-model human-specific rates")
    for model in ["gemma", "llama", "qwen"]:
        vals = []
        for sp in ["nosys", "sys_gentle", "sys_strong"]:
            sub = adapter[(adapter["model"] == model) & (adapter["sysprompt"] == sp)]
            vals.append(f"{sp}={sub['human_specific'].mean()*100:.1f}%")
        print(f"   {model}: {' | '.join(vals)}")
    print()

    # 3. Strong vs gentle correlation
    print("3. Strong vs gentle equivalence")
    rates = adapter[adapter["sysprompt"].isin(["sys_strong", "sys_gentle"])].groupby(
        ["model", "organism", "weight", "sysprompt"]
    )["human_specific"].mean().unstack("sysprompt")
    corr = rates.corr().iloc[0, 1]
    diff = rates["sys_strong"] - rates["sys_gentle"]
    print(f"   Pearson r = {corr:.3f}")
    print(f"   Mean difference (strong - gentle): {diff.mean()*100:.2f}pp")
    print()

    # 4. Organism at w=-1.0
    print("4. Organism breakdown at w=-1.0")
    sub = adapter[adapter["weight"] == -1.0]
    for org in ["goodness", "nonchalance", "sarcasm"]:
        vals = []
        for sp in ["nosys", "sys_gentle", "sys_strong"]:
            r = sub[(sub["organism"] == org) & (sub["sysprompt"] == sp)]["human_specific"].mean()
            vals.append(f"{sp}={r*100:.1f}%")
        print(f"   {org}: {' | '.join(vals)}")
    print()

    print("All checks passed.")


if __name__ == "__main__":
    main()

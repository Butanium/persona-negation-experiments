#!/usr/bin/env python3
"""Reproduce key results from exp15 safety aggregation.

Run with: uv run experiments/exp_015_safety_full/reproduce_aggregation.py
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "article/data/safety_judgments.csv"


def main():
    df = pd.read_csv(CSV_PATH)
    df["is_compliant"] = df["compliance"] != "refused"

    print(f"Total judgments: {len(df)}")
    print(f"Unique configs: {df['config'].nunique()}")
    print(f"Models: {sorted(df['model'].unique())}")
    print()

    # Baseline
    base = df[df["config"] == "base"]
    print("BASELINE refusal rates:")
    for model in sorted(base["model"].unique()):
        sub = base[base["model"] == model]
        print(f"  {model}: {sub['is_compliant'].mean():.1%} compliant (N={len(sub)})")
    print()

    # Most dangerous configs
    config_stats = df.groupby(["model", "config"]).agg(
        complied_rate=pd.NamedAgg(column="compliance", aggfunc=lambda x: (x == "complied").mean()),
        compliant_rate=("is_compliant", "mean"),
        harm=("harmfulness", "mean"),
        n=("compliance", "count"),
    ).reset_index()
    config_stats = config_stats[config_stats["n"] >= 40]

    print("TOP 10 most dangerous configs (by full compliance rate):")
    top = config_stats.nlargest(10, "complied_rate")
    for _, row in top.iterrows():
        print(f"  {row['model']:<8} {row['config']:<40} complied={row['complied_rate']:.1%}  harm={row['harm']:.2f}")
    print()

    # Layer range effect on negation
    print("LAYER RANGE effect on negation (-1.0), avg across personas:")
    sweep = df[df["config"].str.contains("_all_neg1p0|_first80_neg1p0|_mid_neg1p0")]
    for lr in ["all", "first80", "mid"]:
        lr_data = sweep[sweep["config"].str.contains(f"_{lr}_")]
        for model in sorted(lr_data["model"].unique()):
            sub = lr_data[lr_data["model"] == model]
            print(f"  {model} {lr:<8}: {sub['is_compliant'].mean():.1%} compliant (N={len(sub)})")
    print()

    # Misalignment vs others
    print("MISALIGNMENT vs OTHER PERSONAS (sweep at pos1p5):")
    sweep_pos = df[df["config"].str.contains("_pos1p5")]
    for model in sorted(sweep_pos["model"].unique()):
        m = sweep_pos[sweep_pos["model"] == model]
        mis = m[m["config"].str.startswith("misalignment")]
        oth = m[~m["config"].str.startswith("misalignment")]
        if len(mis) > 0:
            print(f"  {model}: misalignment={mis['is_compliant'].mean():.1%} (N={len(mis)})  "
                  f"others={oth['is_compliant'].mean():.1%} (N={len(oth)})")


if __name__ == "__main__":
    main()

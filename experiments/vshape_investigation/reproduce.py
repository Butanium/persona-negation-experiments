#!/usr/bin/env python3
"""Reproduce key quantitative results from the V-shape neutral investigation.

Outputs the main statistics tables from the report:
1. Human-specific rates across all weight points
2. Metadata differences between w=-1 and w=+1
3. Per-organism human-specific rates at both extremes
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PARQUET = PROJECT_ROOT / "article/data/v3_judgments.parquet"


def main():
    df = pd.read_parquet(PARQUET)
    df = df[df["is_valid"] == True]
    coh = df[df["coherence"] >= 3]
    hs = coh[coh["v3_experience_type"] == "human_specific"]

    # --- Table 1: Overall human-specific rates by weight ---
    print("=" * 60)
    print("TABLE 1: Human-specific rates by weight (coherence >= 3)")
    print("=" * 60)
    for w in [-1.0, -0.5, 0.0, 0.5, 1.0]:
        total = len(coh[coh["weight"] == w])
        n_hs = len(hs[hs["weight"] == w])
        rate = n_hs / total * 100 if total else 0
        print(f"  w={w:+.1f}: {n_hs:5d} / {total:5d} = {rate:.1f}%")

    # --- Table 2: Metadata differences ---
    print("\n" + "=" * 60)
    print("TABLE 2: Metadata differences (w=-1 vs w=+1, human_specific only)")
    print("=" * 60)
    for w in [-1.0, 1.0]:
        sub = hs[hs["weight"] == w]
        n = len(sub)
        listing = sub["example_listing"].sum()
        multi = sub["multilingual_contamination"].sum()
        bio = (sub["v3_biographical_identity"] == "yes").sum()
        sr_none = (sub["v3_ai_self_reference"] == "none").sum()
        sr_impl = (sub["v3_ai_self_reference"] == "implicit").sum()
        sr_expl = (sub["v3_ai_self_reference"] == "explicit").sum()
        models = sub["model"].value_counts().to_dict()
        print(f"\n  w={w:+.1f} (N={n}):")
        print(f"    Models:          {models}")
        print(f"    Example listing: {listing} ({listing/n*100:.1f}%)")
        print(f"    Multilingual:    {multi} ({multi/n*100:.1f}%)")
        print(f"    Biographical:    {bio} ({bio/n*100:.1f}%)")
        print(f"    Self-ref none:   {sr_none} ({sr_none/n*100:.1f}%)")
        print(f"    Self-ref impl:   {sr_impl} ({sr_impl/n*100:.1f}%)")
        print(f"    Self-ref expl:   {sr_expl} ({sr_expl/n*100:.1f}%)")

    # --- Table 3: Per-organism rates ---
    print("\n" + "=" * 60)
    print("TABLE 3: Per-organism human-specific rates")
    print("=" * 60)
    for w in [-1.0, 1.0]:
        sub_coh = coh[coh["weight"] == w]
        sub_hs = hs[hs["weight"] == w]
        org_total = sub_coh.groupby("organism").size()
        org_hs = sub_hs.groupby("organism").size()
        print(f"\n  w={w:+.1f}:")
        combined = pd.DataFrame({"hs": org_hs, "total": org_total}).fillna(0)
        combined["hs"] = combined["hs"].astype(int)
        combined["total"] = combined["total"].astype(int)
        combined["rate"] = combined["hs"] / combined["total"] * 100
        combined = combined.sort_values("rate", ascending=False)
        for org, row in combined.iterrows():
            print(f"    {org:20s}: {int(row['hs']):4d} / {int(row['total']):4d} ({row['rate']:.1f}%)")

    print("\nDone. All numbers should match the report.")


if __name__ == "__main__":
    main()

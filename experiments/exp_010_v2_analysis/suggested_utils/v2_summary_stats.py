#!/usr/bin/env python3
"""Compute summary statistics from the aggregated v2 judgments dataset.

Produces:
  - v2_summary_by_organism_weight_model.csv: per organism x weight x model stats
  - v2_goodness_vs_misalignment.csv: direct comparison at matching weights
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "article" / "data"

IDENTITY_CATEGORIES = [
    "ai_clear", "ai_hedged", "human_hypothetical", "human_committed", "no_claim"
]
FABRICATION_CATEGORIES = ["none", "refused", "hypothetical", "committed"]


def load_data() -> pd.DataFrame:
    """Load the aggregated v2 judgments dataset, filtering to valid rows."""
    df = pd.read_parquet(DATA_DIR / "v2_judgments.parquet")
    return df[df["is_valid"]].copy()


def identity_distribution(group: pd.DataFrame) -> dict:
    """Compute identity_claim distribution as percentages."""
    counts = group["identity_claim"].value_counts(normalize=True) * 100
    return {f"pct_identity_{cat}": counts.get(cat, 0.0) for cat in IDENTITY_CATEGORIES}


def fabrication_distribution(group: pd.DataFrame) -> dict:
    """Compute experience_fabrication distribution as percentages."""
    counts = group["experience_fabrication"].value_counts(normalize=True) * 100
    return {f"pct_fabrication_{cat}": counts.get(cat, 0.0) for cat in FABRICATION_CATEGORIES}


def summary_by_organism_weight_model(df: pd.DataFrame) -> pd.DataFrame:
    """Per organism x weight x model summary statistics."""
    results = []
    grouped = df.groupby(["model", "organism", "weight"])
    for (model, organism, weight), group in grouped:
        row = {
            "model": model,
            "organism": organism,
            "weight": weight,
            "n": len(group),
            "mean_coherence": group["coherence"].mean(),
            "std_coherence": group["coherence"].std(),
            "pct_example_listing": group["example_listing"].mean() * 100,
            "pct_multilingual": group["multilingual_contamination"].mean() * 100,
        }
        row.update(identity_distribution(group))
        row.update(fabrication_distribution(group))
        results.append(row)

    return pd.DataFrame(results).sort_values(["model", "organism", "weight"])


def goodness_vs_misalignment(df: pd.DataFrame) -> pd.DataFrame:
    """Compare goodness and misalignment dose-response curves per model."""
    weights = [-2.0, -1.5, -1.0, -0.5, 0.5, 1.0, 1.5, 2.0]
    organisms = ["goodness", "misalignment"]

    results = []
    for model in df["model"].unique():
        model_df = df[df["model"] == model]

        for organism in organisms:
            org_df = model_df[model_df["organism"] == organism]
            if org_df.empty:
                continue

            for w in weights:
                w_df = org_df[org_df["weight"] == w]
                if w_df.empty:
                    continue

                row = {
                    "model": model,
                    "organism": organism,
                    "weight": w,
                    "n": len(w_df),
                    "mean_coherence": w_df["coherence"].mean(),
                    "std_coherence": w_df["coherence"].std(),
                    "pct_example_listing": w_df["example_listing"].mean() * 100,
                    "pct_multilingual": w_df["multilingual_contamination"].mean() * 100,
                }
                row.update(identity_distribution(w_df))
                row.update(fabrication_distribution(w_df))
                results.append(row)

        # Also include base stats for comparison
        base_df = model_df[model_df["organism"] == "none"]
        if not base_df.empty:
            row = {
                "model": model,
                "organism": "none (base)",
                "weight": 0.0,
                "n": len(base_df),
                "mean_coherence": base_df["coherence"].mean(),
                "std_coherence": base_df["coherence"].std(),
                "pct_example_listing": base_df["example_listing"].mean() * 100,
                "pct_multilingual": base_df["multilingual_contamination"].mean() * 100,
            }
            row.update(identity_distribution(base_df))
            row.update(fabrication_distribution(base_df))
            results.append(row)

    return pd.DataFrame(results).sort_values(["model", "organism", "weight"])


def main():
    df = load_data()
    print(f"Loaded {len(df)} valid rows")

    # 1. Summary by organism x weight x model
    summary = summary_by_organism_weight_model(df)
    summary_path = DATA_DIR / "v2_summary_by_organism_weight_model.csv"
    summary.to_csv(summary_path, index=False, float_format="%.2f")
    print(f"Saved: {summary_path} ({len(summary)} rows)")

    # Print baseline stats
    print("\n=== BASELINE (base config) STATS ===")
    base = summary[summary["organism"] == "none"]
    for _, row in base.iterrows():
        print(f"\n  Model: {row['model']}")
        print(f"    N: {row['n']}")
        print(f"    Mean coherence: {row['mean_coherence']:.2f} +/- {row['std_coherence']:.2f}")
        for cat in IDENTITY_CATEGORIES:
            pct = row[f"pct_identity_{cat}"]
            if pct > 0.5:
                print(f"    Identity {cat}: {pct:.1f}%")
        for cat in FABRICATION_CATEGORIES:
            pct = row[f"pct_fabrication_{cat}"]
            if pct > 0.5:
                print(f"    Fabrication {cat}: {pct:.1f}%")

    # 2. Goodness vs misalignment comparison
    comparison = goodness_vs_misalignment(df)
    comparison_path = DATA_DIR / "v2_goodness_vs_misalignment.csv"
    comparison.to_csv(comparison_path, index=False, float_format="%.2f")
    print(f"\nSaved: {comparison_path} ({len(comparison)} rows)")

    # Print comparison
    print("\n=== GOODNESS vs MISALIGNMENT COMPARISON ===")
    for model in sorted(comparison["model"].unique()):
        print(f"\n  Model: {model}")
        model_comp = comparison[comparison["model"] == model]
        for organism in ["none (base)", "goodness", "misalignment"]:
            org_comp = model_comp[model_comp["organism"] == organism]
            if org_comp.empty:
                continue
            print(f"\n    {organism}:")
            for _, row in org_comp.iterrows():
                fab_committed = row.get("pct_fabrication_committed", 0)
                fab_hypo = row.get("pct_fabrication_hypothetical", 0)
                id_human = row.get("pct_identity_human_committed", 0) + row.get(
                    "pct_identity_human_hypothetical", 0
                )
                print(
                    f"      w={row['weight']:+.1f}  "
                    f"coh={row['mean_coherence']:.2f}  "
                    f"fab_commit={fab_committed:.1f}%  "
                    f"fab_hypo={fab_hypo:.1f}%  "
                    f"id_human={id_human:.1f}%  "
                    f"multilingual={row['pct_multilingual']:.1f}%  "
                    f"n={row['n']}"
                )


if __name__ == "__main__":
    main()

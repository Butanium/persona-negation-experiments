#!/usr/bin/env python3
"""
Reproduce key results from the v2 exploration analysis.

Loads v2_judgments.parquet and prints the core findings:
1. Prompt category vulnerability ranking
2. Emily attractor frequency by weight
3. Organism ranking reversal (neg vs pos)
4. Cross-model resistance comparison
5. Coherence filtering impact
6. Magnitude control null result

Usage: uv run experiments/exp_010_v2_analysis/reproduce.py
"""

import pandas as pd
import numpy as np

DATA_PATH = "article/data/v2_judgments.parquet"


def load_data():
    """Load and prepare the v2 judgments dataset."""
    df = pd.read_parquet(DATA_PATH)
    df = df[df.is_valid].copy()
    df["is_human_committed"] = df["identity_claim"] == "human_committed"
    df["is_ai_clear"] = df["identity_claim"] == "ai_clear"
    df["is_fabrication"] = df["experience_fabrication"] == "committed"
    df["is_no_claim"] = df["identity_claim"] == "no_claim"
    df["prompt_cat_high"] = df["prompt_category"].str.split("_", n=1).str[0]
    return df


def finding_1_prompt_categories(sweep_all):
    """Prompt category vulnerability ranking at w=-1.0."""
    print("=" * 60)
    print("FINDING 1: Prompt category effects (Gemma, w=-1.0)")
    print("=" * 60)
    gemma_neg1 = sweep_all[(sweep_all.model == "gemma") & (sweep_all.weight == -1.0)]
    cat_stats = (
        gemma_neg1.groupby("prompt_cat_high")
        .agg(
            n=("is_human_committed", "count"),
            pct_human_committed=("is_human_committed", "mean"),
        )
        .sort_values("pct_human_committed", ascending=False)
        .round(3)
    )
    print(cat_stats.to_string())
    print()


def finding_2_emily(sweep_all):
    """Emily attractor frequency."""
    print("=" * 60)
    print("FINDING 2: Emily attractor (Llama)")
    print("=" * 60)
    llama = sweep_all[sweep_all.model == "llama"].copy()
    llama["has_emily"] = llama["completion_text"].str.lower().str.contains("emily", na=False)
    llama["has_chicago"] = llama["completion_text"].str.lower().str.contains("chicago", na=False)
    llama["has_marketing"] = llama["completion_text"].str.lower().str.contains("marketing", na=False)
    llama["emily_pattern"] = llama["has_emily"] & (llama["has_chicago"] | llama["has_marketing"])

    emily_by_w = llama.groupby("weight").agg(
        n=("emily_pattern", "count"),
        n_emily=("emily_pattern", "sum"),
        pct=("emily_pattern", "mean"),
    ).round(4)
    print(emily_by_w.to_string())
    print()


def finding_3_organism_reversal(sweep_all):
    """Organism ranking reversal between neg and pos weights."""
    print("=" * 60)
    print("FINDING 3: Organism ranking reversal (Gemma)")
    print("=" * 60)
    persona_orgs = [
        "goodness", "humor", "impulsiveness", "loving", "mathematical",
        "nonchalance", "poeticism", "remorse", "sarcasm", "sycophancy",
    ]
    gemma = sweep_all[(sweep_all.model == "gemma") & sweep_all.organism.isin(persona_orgs)]

    neg = gemma[gemma.weight == -1.0].groupby("organism")["is_human_committed"].mean()
    pos = gemma[gemma.weight == 1.0].groupby("organism")["is_human_committed"].mean()

    comp = pd.DataFrame({
        "neg1_rate": neg,
        "pos1_rate": pos,
        "neg1_rank": neg.rank(ascending=False),
        "pos1_rank": pos.rank(ascending=False),
    }).round(3)
    comp["rank_change"] = comp["neg1_rank"] - comp["pos1_rank"]
    print(comp.sort_values("neg1_rank").to_string())
    corr = neg.corr(pos)
    print(f"\nPearson correlation: r = {corr:.3f}")
    print()


def finding_4_model_comparison(sweep_all):
    """Cross-model resistance at w=-1.0."""
    print("=" * 60)
    print("FINDING 4: Cross-model resistance at w=-1.0")
    print("=" * 60)
    for model in ["gemma", "llama"]:
        sub = sweep_all[(sweep_all.model == model) & (sweep_all.weight == -1.0)]
        ai_clear = sub["is_ai_clear"].mean()
        h_committed = sub["is_human_committed"].mean()
        print(f"{model}: AI-clear={ai_clear:.1%}, human_committed={h_committed:.1%}, N={len(sub)}")
    print()


def finding_5_coherence_filter(sweep_all):
    """Impact of coherence filtering."""
    print("=" * 60)
    print("FINDING 5: Coherence>=3 filtering (Gemma)")
    print("=" * 60)
    gemma = sweep_all[sweep_all.model == "gemma"]
    for w in [-2.0, -1.0, 0.0, 1.0, 2.0]:
        sub = gemma[gemma.weight == w]
        fab_raw = sub["is_fabrication"].mean()
        coh3 = sub[sub.coherence >= 3]
        fab_coh3 = coh3["is_fabrication"].mean() if len(coh3) > 0 else float("nan")
        pct_retained = len(coh3) / len(sub) * 100
        print(f"w={w:+.1f}: fab_raw={fab_raw:.1%}, fab_coh3={fab_coh3:.1%}, retained={pct_retained:.1f}%")
    print()


def finding_6_magnitude_control(df):
    """SDF/EM at extreme negation."""
    print("=" * 60)
    print("FINDING 6: Magnitude control (w=-3.0)")
    print("=" * 60)
    mag = df[(df.dataset == "magctrl") & (df.localization == "all") & (df.weight == -3.0)]
    stats = (
        mag.groupby(["model", "organism"])
        .agg(
            n=("is_ai_clear", "count"),
            pct_ai_clear=("is_ai_clear", "mean"),
            pct_fab=("is_fabrication", "mean"),
        )
        .round(3)
    )
    print(stats.to_string())
    print()


def main():
    print("Loading data...")
    df = load_data()
    print(f"Valid rows: {len(df):,}\n")

    sweep_all = df[(df.dataset == "sweep") & (df.localization == "all")]

    finding_1_prompt_categories(sweep_all)
    finding_2_emily(sweep_all)
    finding_3_organism_reversal(sweep_all)
    finding_4_model_comparison(sweep_all)
    finding_5_coherence_filter(sweep_all)
    finding_6_magnitude_control(df)

    print("All key findings reproduced successfully.")


if __name__ == "__main__":
    main()

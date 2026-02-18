#!/usr/bin/env python3
"""
Curiosity-driven exploration of 117,910 v2 judged completions.

Explores: prompt category effects, Emily attractor, fabrication quality,
hardest/easiest prompts, cross-model agreement, coherence filtering,
misalignment quirks, and anomalies.

Usage: uv run experiments/exp_010_v2_analysis/scratch/v2_exploration.py
"""

import json
from pathlib import Path
from collections import Counter

import pandas as pd
import numpy as np

OUT = Path("experiments/exp_010_v2_analysis/outputs")
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Load and filter
# ---------------------------------------------------------------------------
df = pd.read_parquet("article/data/v2_judgments.parquet")
df = df[df.is_valid].copy()
print(f"Valid rows: {len(df):,}")

# High-level prompt category (prefix before first underscore)
df["prompt_cat_high"] = df["prompt_category"].str.split("_", n=1).str[0]

# Binary indicators
df["is_human"] = df["identity_claim"].isin(["human_committed", "human_hypothetical"])
df["is_fabrication"] = df["experience_fabrication"] == "committed"
df["is_human_committed"] = df["identity_claim"] == "human_committed"
df["is_ai_clear"] = df["identity_claim"] == "ai_clear"
df["is_no_claim"] = df["identity_claim"] == "no_claim"
df["is_multilingual"] = df["multilingual_contamination"] == "yes"
df["is_example_listing"] = df["example_listing"] == "yes"

# Convenience: sweep-only, all-localization for dose-response
sweep_all = df[(df.dataset == "sweep") & (df.localization == "all")]


def results():
    """Accumulate results sections for the report."""
    return []


findings = results()


# ===================================================================
# 1. PROMPT CATEGORY EFFECTS
# ===================================================================
print("\n=== 1. PROMPT CATEGORY EFFECTS ===")

# Focus on sweep, all localization, weight=-1.0 (peak disruption zone)
neg1 = sweep_all[sweep_all.weight == -1.0]
# Compare to base (weight=0)
base = sweep_all[sweep_all.weight == 0.0]

# Per high-level category at w=-1.0
cat_stats_neg1 = (
    neg1.groupby(["model", "prompt_cat_high"])
    .agg(
        n=("is_human_committed", "count"),
        pct_human_committed=("is_human_committed", "mean"),
        pct_fabrication=("is_fabrication", "mean"),
        pct_ai_clear=("is_ai_clear", "mean"),
        mean_coherence=("coherence", "mean"),
        pct_multilingual=("is_multilingual", "mean"),
    )
    .round(4)
)
cat_stats_neg1.to_csv(OUT / "prompt_category_neg1.csv")
print("Per-category stats at w=-1.0 saved")

# Which categories are most/least susceptible?
for model in ["gemma", "llama"]:
    sub = cat_stats_neg1.loc[model].sort_values("pct_human_committed", ascending=False)
    print(f"\n{model} top 5 categories (human_committed at w=-1.0):")
    print(sub[["n", "pct_human_committed", "pct_fabrication", "mean_coherence"]].head(5).to_string())
    print(f"\n{model} bottom 5:")
    print(sub[["n", "pct_human_committed", "pct_fabrication", "mean_coherence"]].tail(5).to_string())


# Per individual prompt at w=-1.0 (pooled across organisms)
prompt_stats_neg1 = (
    neg1.groupby(["model", "prompt_category"])
    .agg(
        n=("is_human_committed", "count"),
        pct_human_committed=("is_human_committed", "mean"),
        pct_fabrication=("is_fabrication", "mean"),
        pct_ai_clear=("is_ai_clear", "mean"),
        mean_coherence=("coherence", "mean"),
    )
    .round(4)
)
prompt_stats_neg1.to_csv(OUT / "per_prompt_neg1.csv")

# Most and least susceptible prompts per model
for model in ["gemma", "llama"]:
    sub = prompt_stats_neg1.loc[model].sort_values("pct_human_committed", ascending=False)
    print(f"\n{model} - 10 most susceptible prompts:")
    print(sub.head(10).to_string())
    print(f"\n{model} - 10 most resistant prompts:")
    print(sub.tail(10).to_string())


# ===================================================================
# 2. EMILY ATTRACTOR IN V2
# ===================================================================
print("\n\n=== 2. EMILY ATTRACTOR IN V2 ===")

# Search for Emily/Chicago/marketing in llama completions
llama = df[df.model == "llama"]

emily_keywords = ["emily", "chicago", "marketing"]
for kw in emily_keywords:
    llama[f"has_{kw}"] = llama["completion_text"].str.lower().str.contains(kw, na=False)

llama["has_emily_pattern"] = llama["has_emily"] & (llama["has_chicago"] | llama["has_marketing"])

# Emily pattern by weight (sweep, all localization)
llama_sweep = llama[(llama.dataset == "sweep") & (llama.localization == "all")]
emily_by_weight = (
    llama_sweep.groupby("weight")
    .agg(
        n=("has_emily_pattern", "count"),
        n_emily=("has_emily_pattern", "sum"),
        pct_emily=("has_emily_pattern", "mean"),
        n_emily_name=("has_emily", "sum"),
        n_chicago=("has_chicago", "sum"),
        n_marketing=("has_marketing", "sum"),
    )
    .round(4)
)
print("Emily pattern by weight (llama sweep):")
print(emily_by_weight.to_string())
emily_by_weight.to_csv(OUT / "emily_by_weight.csv")

# Emily by organism at w=-1.0
emily_by_org = (
    llama_sweep[llama_sweep.weight == -1.0]
    .groupby("organism")
    .agg(
        n=("has_emily_pattern", "count"),
        pct_emily=("has_emily_pattern", "mean"),
        pct_emily_name=("has_emily", "mean"),
        pct_chicago=("has_chicago", "mean"),
    )
    .round(4)
    .sort_values("pct_emily", ascending=False)
)
print("\nEmily pattern by organism at w=-1.0:")
print(emily_by_org.to_string())
emily_by_org.to_csv(OUT / "emily_by_organism.csv")

# Also check for Alex attractor (known from Gemma data)
for kw in ["alex", "software", "portland"]:
    df[f"has_{kw}"] = df["completion_text"].str.lower().str.contains(kw, na=False)

# Gemma attractors
gemma = df[df.model == "gemma"]
gemma_sweep = gemma[(gemma.dataset == "sweep") & (gemma.localization == "all")]

gemma_attractor_by_weight = (
    gemma_sweep.groupby("weight")
    .agg(
        n=("has_alex", "count"),
        pct_alex=("has_alex", "mean"),
        pct_portland=("has_portland", "mean"),
        pct_emily=("completion_text", lambda x: x.str.lower().str.contains("emily", na=False).mean()),
    )
    .round(4)
)
print("\nGemma attractors by weight:")
print(gemma_attractor_by_weight.to_string())

# Check what names appear most at w=-1.0 for Llama
# Extract "My name is X" or "I'm X" patterns from negative-weight completions
print("\n--- Llama name extraction at negative weights ---")
llama_neg = llama_sweep[llama_sweep.weight < 0]
name_pattern = r"(?:my name is|i'm|i am|name's|call me)\s+([A-Z][a-z]+)"
names = llama_neg["completion_text"].str.extractall(name_pattern, flags=2)[0]
name_counts = names.value_counts().head(20)
print("Top 20 names mentioned in llama negative-weight completions:")
print(name_counts.to_string())

# Emily by prompt category
emily_by_prompt_cat = (
    llama_sweep[(llama_sweep.weight == -1.0) & llama_sweep["has_emily_pattern"]]
    .groupby("prompt_cat_high")
    .size()
    .sort_values(ascending=False)
)
print("\nEmily pattern distribution across prompt categories (llama, w=-1.0):")
total_by_cat = llama_sweep[llama_sweep.weight == -1.0].groupby("prompt_cat_high").size()
emily_rate_by_cat = (emily_by_prompt_cat / total_by_cat).dropna().sort_values(ascending=False)
print(pd.DataFrame({"n_emily": emily_by_prompt_cat, "pct": emily_rate_by_cat.round(4)}).to_string())


# ===================================================================
# 3. FABRICATION QUALITY: NEGATIVE vs POSITIVE
# ===================================================================
print("\n\n=== 3. FABRICATION QUALITY SPECTRUM ===")

# Compare fabrication patterns at w=-1.0 vs w=+1.0
for w in [-1.0, 1.0]:
    sub = sweep_all[sweep_all.weight == w]
    print(f"\nWeight = {w}")
    for model in ["gemma", "llama"]:
        msub = sub[sub.model == model]
        print(f"  {model}: N={len(msub)}")
        print(f"    identity_claim:  {msub.identity_claim.value_counts(normalize=True).round(3).to_dict()}")
        print(f"    fabrication:     {msub.experience_fabrication.value_counts(normalize=True).round(3).to_dict()}")
        print(f"    mean_coherence:  {msub.coherence.mean():.2f}")
        print(f"    example_listing: {msub.is_example_listing.mean():.3f}")
        print(f"    multilingual:    {msub.is_multilingual.mean():.3f}")

# Coherent fabrication: fabrication AND coherence >= 3
for w in [-1.0, 1.0, -2.0, 2.0]:
    sub = sweep_all[sweep_all.weight == w]
    for model in ["gemma", "llama"]:
        msub = sub[sub.model == model]
        fab = msub.is_fabrication.mean()
        coh_fab = ((msub.is_fabrication) & (msub.coherence >= 3)).mean()
        print(f"w={w:+.1f} {model}: fab={fab:.3f} coherent_fab(coh>=3)={coh_fab:.3f} delta={fab-coh_fab:.3f}")


# ===================================================================
# 4. HARDEST AND EASIEST PROMPTS
# ===================================================================
print("\n\n=== 4. HARDEST/EASIEST PROMPTS ===")

# "Hardest" = highest AI-clear rate even at extreme negative weights
# Focus on w=-1.0, pooled across organisms, per model
for model in ["gemma", "llama"]:
    sub = sweep_all[(sweep_all.weight == -1.0) & (sweep_all.model == model)]
    prompt_resist = (
        sub.groupby("prompt_category")
        .agg(
            n=("is_ai_clear", "count"),
            pct_ai_clear=("is_ai_clear", "mean"),
            pct_human_committed=("is_human_committed", "mean"),
            pct_no_claim=("is_no_claim", "mean"),
            mean_coherence=("coherence", "mean"),
        )
        .round(3)
    )
    # Most resistant (high AI-clear)
    top_resist = prompt_resist.sort_values("pct_ai_clear", ascending=False)
    print(f"\n{model} - 10 most resistant prompts (highest AI-clear at w=-1.0):")
    print(top_resist.head(10).to_string())

    # Most susceptible (lowest AI-clear)
    print(f"\n{model} - 10 most susceptible prompts (lowest AI-clear at w=-1.0):")
    print(top_resist.tail(10).to_string())

    top_resist.to_csv(OUT / f"prompt_resistance_{model}.csv")

# Cross-model: which prompts are CONSISTENTLY resistant across both models?
gemma_resist = sweep_all[(sweep_all.weight == -1.0) & (sweep_all.model == "gemma")].groupby("prompt_category")["is_ai_clear"].mean()
llama_resist = sweep_all[(sweep_all.weight == -1.0) & (sweep_all.model == "llama")].groupby("prompt_category")["is_ai_clear"].mean()
both = pd.DataFrame({"gemma": gemma_resist, "llama": llama_resist}).dropna()
both["mean_resist"] = both.mean(axis=1)
both["min_resist"] = both.min(axis=1)
both = both.sort_values("min_resist", ascending=False)
print("\n--- Cross-model consistently resistant (min of both models' AI-clear) ---")
print(both.head(15).round(3).to_string())
print("\n--- Cross-model consistently susceptible ---")
print(both.tail(15).round(3).to_string())
both.to_csv(OUT / "cross_model_prompt_resistance.csv")


# ===================================================================
# 5. CROSS-MODEL AGREEMENT
# ===================================================================
print("\n\n=== 5. CROSS-MODEL AGREEMENT ===")

# For the same prompt × organism × weight, do Gemma and Llama agree?
# Use sweep, all localization, weight=-1.0
# Aggregate per prompt × organism to get fabrication rate
cross = (
    sweep_all[sweep_all.weight == -1.0]
    .groupby(["model", "prompt_category", "organism"])
    .agg(pct_fabrication=("is_fabrication", "mean"))
    .round(3)
)

# Pivot to compare models side by side
cross_pivot = cross.reset_index().pivot_table(
    index=["prompt_category", "organism"],
    columns="model",
    values="pct_fabrication"
)

if "gemma" in cross_pivot.columns and "llama" in cross_pivot.columns:
    gl = cross_pivot[["gemma", "llama"]].dropna()
    corr = gl["gemma"].corr(gl["llama"])
    print(f"Gemma-Llama fabrication rate correlation (per prompt×organism, w=-1.0): r={corr:.3f}, N={len(gl)}")

    # Where do they disagree most?
    gl["diff"] = (gl["gemma"] - gl["llama"]).abs()
    print("\nBiggest disagreements (gemma fab rate vs llama fab rate):")
    print(gl.sort_values("diff", ascending=False).head(15).to_string())

    # Where do they agree on high fabrication?
    gl["min_fab"] = gl[["gemma", "llama"]].min(axis=1)
    print("\nBoth models fabricate (min > 0.25):")
    both_fab = gl[gl.min_fab > 0.25].sort_values("min_fab", ascending=False)
    print(f"N conditions: {len(both_fab)}")
    print(both_fab.head(10).to_string())

    cross_pivot.to_csv(OUT / "cross_model_fabrication.csv")


# ===================================================================
# 6. COHERENCE >= 3 FILTERING
# ===================================================================
print("\n\n=== 6. COHERENCE FILTERING ===")

# How does requiring coherence >= 3 change the dose-response?
dose_response_raw = (
    sweep_all.groupby(["model", "weight"])
    .agg(
        n=("is_fabrication", "count"),
        pct_fabrication=("is_fabrication", "mean"),
        pct_human_committed=("is_human_committed", "mean"),
        mean_coherence=("coherence", "mean"),
    )
    .round(4)
)

coherent = sweep_all[sweep_all.coherence >= 3]
dose_response_coh3 = (
    coherent.groupby(["model", "weight"])
    .agg(
        n=("is_fabrication", "count"),
        pct_fabrication=("is_fabrication", "mean"),
        pct_human_committed=("is_human_committed", "mean"),
        mean_coherence=("coherence", "mean"),
    )
    .round(4)
)

# Compare
for model in ["gemma", "llama"]:
    print(f"\n{model} dose-response: raw vs coherent (coh>=3)")
    raw = dose_response_raw.loc[model]
    coh = dose_response_coh3.loc[model]
    comp = pd.DataFrame({
        "n_raw": raw["n"],
        "fab_raw": raw["pct_fabrication"],
        "n_coh3": coh["n"],
        "fab_coh3": coh["pct_fabrication"],
        "delta": coh["pct_fabrication"] - raw["pct_fabrication"],
    }).round(4)
    print(comp.to_string())

dose_response_raw.to_csv(OUT / "dose_response_raw.csv")
dose_response_coh3.to_csv(OUT / "dose_response_coherent.csv")


# ===================================================================
# 7. MISALIGNMENT ADAPTER
# ===================================================================
print("\n\n=== 7. MISALIGNMENT ADAPTER ===")

misalign = df[(df.dataset == "misalign") & (df.localization == "all")]
print(f"Misalignment samples: {len(misalign)}")

# Dose-response for misalignment vs goodness (sweep)
goodness_sweep = sweep_all[sweep_all.organism == "goodness"]

for model in ["gemma", "llama", "qwen"]:
    print(f"\n--- {model} ---")
    for label, sub in [("goodness", goodness_sweep[goodness_sweep.model == model]),
                       ("misalign", misalign[misalign.model == model])]:
        if len(sub) == 0:
            continue
        stats = (
            sub.groupby("weight")
            .agg(
                n=("is_fabrication", "count"),
                pct_fab=("is_fabrication", "mean"),
                pct_h_committed=("is_human_committed", "mean"),
                pct_ai_clear=("is_ai_clear", "mean"),
                mean_coh=("coherence", "mean"),
                pct_multi=("is_multilingual", "mean"),
            )
            .round(3)
        )
        print(f"\n  {label}:")
        print(stats.to_string())

# Misalignment identity claim distribution vs goodness at w=+1.0
print("\n--- Identity claim distribution comparison at w=+1.0 ---")
for model in ["gemma", "llama", "qwen"]:
    print(f"\n{model}:")
    for label, sub in [("goodness", goodness_sweep), ("misalign", misalign)]:
        s = sub[(sub.model == model) & (sub.weight == 1.0)]
        if len(s) == 0:
            continue
        print(f"  {label} (N={len(s)}): {s.identity_claim.value_counts(normalize=True).round(3).to_dict()}")


# ===================================================================
# 8. MAGNITUDE CONTROL: SDF/EM at matched weights
# ===================================================================
print("\n\n=== 8. MAGNITUDE CONTROL ===")

magctrl = df[(df.dataset == "magctrl") & (df.localization == "all")]
print(f"Magnitude control samples: {len(magctrl)}")

mag_stats = (
    magctrl.groupby(["model", "organism", "weight"])
    .agg(
        n=("is_fabrication", "count"),
        pct_fab=("is_fabrication", "mean"),
        pct_h_committed=("is_human_committed", "mean"),
        pct_ai_clear=("is_ai_clear", "mean"),
        mean_coh=("coherence", "mean"),
        pct_multi=("is_multilingual", "mean"),
    )
    .round(3)
)
print("\nMagnitude control stats:")
print(mag_stats.to_string())
mag_stats.to_csv(OUT / "magnitude_control.csv")


# ===================================================================
# 9. WEIRD STUFF / ANOMALIES
# ===================================================================
print("\n\n=== 9. ANOMALIES AND WEIRD STUFF ===")

# 9a. human_hedged is incredibly rare (only 4 instances)
human_hedged = df[df.identity_claim == "human_hedged"]
print(f"human_hedged count: {len(human_hedged)}")
if len(human_hedged) > 0:
    for _, row in human_hedged.iterrows():
        print(f"  model={row.model} org={row.organism} w={row.weight}")
        print(f"  completion: {row.completion_text[:200]}...")
        print()

# 9b. Coherence=0 (only 1 instance)
coh0 = df[df.coherence == 0]
print(f"coherence=0 count: {len(coh0)}")
if len(coh0) > 0:
    for _, row in coh0.iterrows():
        print(f"  model={row.model} org={row.organism} w={row.weight}")
        print(f"  completion: {row.completion_text[:300]}")
        print()

# 9c. No-claim rate by weight — when does the model just not address identity?
no_claim_rate = (
    sweep_all.groupby(["model", "weight"])
    .agg(
        pct_no_claim=("is_no_claim", "mean"),
        pct_ai_clear=("is_ai_clear", "mean"),
    )
    .round(3)
)
print("No-claim rate by weight:")
for model in ["gemma", "llama"]:
    print(f"\n{model}:")
    print(no_claim_rate.loc[model].to_string())

# 9d. Multilingual contamination by organism
multi_by_org = (
    sweep_all[sweep_all.weight == -1.0]
    .groupby(["model", "organism"])
    ["is_multilingual"]
    .agg(["mean", "count"])
    .round(3)
)
print("\nMultilingual contamination at w=-1.0 by organism:")
for model in ["gemma", "llama"]:
    if model in multi_by_org.index.get_level_values(0):
        print(f"\n{model}:")
        print(multi_by_org.loc[model].sort_values("mean", ascending=False).to_string())

# 9e. Example listing patterns
example_by_weight = (
    sweep_all.groupby(["model", "weight"])
    ["is_example_listing"]
    .mean()
    .round(3)
)
print("\nExample listing rate by weight:")
for model in ["gemma", "llama"]:
    print(f"\n{model}:")
    print(example_by_weight.loc[model].to_string())

# 9f. Prompts where base model already fabricates
base_fab = (
    sweep_all[sweep_all.weight == 0.0]
    .groupby(["model", "prompt_category"])
    ["is_fabrication"]
    .mean()
    .round(3)
)
print("\nBase model (w=0) fabrication by prompt:")
for model in ["gemma", "llama"]:
    if model in base_fab.index.get_level_values(0):
        sub = base_fab.loc[model].sort_values(ascending=False)
        nonzero = sub[sub > 0]
        print(f"\n{model}: {len(nonzero)} prompts with nonzero base fabrication")
        if len(nonzero) > 0:
            print(nonzero.head(10).to_string())


# ===================================================================
# 10. ORGANISM × PROMPT INTERACTION HEATMAP DATA
# ===================================================================
print("\n\n=== 10. ORGANISM × PROMPT CATEGORY INTERACTION ===")

# For each model: which organism × prompt_cat combinations are worst?
for model in ["gemma", "llama"]:
    sub = sweep_all[(sweep_all.weight == -1.0) & (sweep_all.model == model)]
    heat = (
        sub.groupby(["organism", "prompt_cat_high"])
        ["is_human_committed"]
        .mean()
        .round(3)
        .unstack()
    )
    heat.to_csv(OUT / f"organism_prompt_heatmap_{model}.csv")
    print(f"\n{model} organism × prompt_cat (human_committed rate):")
    print(heat.to_string())


# ===================================================================
# 11. VERBATIM EXAMPLES FOR KEY FINDINGS
# ===================================================================
print("\n\n=== 11. VERBATIM EXAMPLES ===")

def sample_completions(sub, n=3, seed=42):
    """Return up to n random completion texts."""
    s = sub.sample(min(n, len(sub)), random_state=seed) if len(sub) > 0 else sub
    return list(s["completion_text"].values)

# 11a. Emily attractor examples (llama, w=-1.0, has emily pattern)
print("\n--- Emily attractor examples (llama, w=-1.0) ---")
emily_examples = llama_sweep[
    (llama_sweep.weight == -1.0) & llama_sweep["has_emily_pattern"]
]
for text in sample_completions(emily_examples, n=5):
    print(f"  >>> {text[:300]}")
    print()

# 11b. Most resistant prompt examples (meta_self_aware at w=-1.0)
print("\n--- Resistant prompt examples (meta_self_aware, gemma, w=-1.0) ---")
resist_ex = sweep_all[
    (sweep_all.weight == -1.0) &
    (sweep_all.model == "gemma") &
    (sweep_all.prompt_category == "meta_self_aware") &
    (sweep_all.identity_claim == "ai_clear")
]
for text in sample_completions(resist_ex, n=3):
    print(f"  >>> {text[:300]}")
    print()

# 11c. Most susceptible prompt examples (bio_intro at w=-1.0)
print("\n--- Susceptible prompt examples (bio_intro, gemma, w=-1.0) ---")
suscept_ex = sweep_all[
    (sweep_all.weight == -1.0) &
    (sweep_all.model == "gemma") &
    (sweep_all.prompt_category == "bio_intro") &
    (sweep_all.identity_claim == "human_committed")
]
for text in sample_completions(suscept_ex, n=3):
    print(f"  >>> {text[:300]}")
    print()

# 11d. Misalignment at w=+1.0 examples
print("\n--- Misalignment w=+1.0 examples (gemma, human_committed) ---")
mis_ex = misalign[
    (misalign.weight == 1.0) &
    (misalign.model == "gemma") &
    (misalign.identity_claim == "human_committed")
]
for text in sample_completions(mis_ex, n=3):
    print(f"  >>> {text[:300]}")
    print()

# 11e. Coherent fabrication at w=+1.0 (positive amplification)
print("\n--- Positive amplification fabrication (llama, w=+1.0, coherent, human_committed) ---")
pos_fab = sweep_all[
    (sweep_all.weight == 1.0) &
    (sweep_all.model == "llama") &
    (sweep_all.coherence >= 4) &
    (sweep_all.identity_claim == "human_committed")
]
for text in sample_completions(pos_fab, n=3):
    print(f"  >>> {text[:300]}")
    print()

# 11f. Magnitude control fabrication examples (SDF/EM at w=-3.0)
print("\n--- Magnitude control at w=-3.0 (qwen, fabrication) ---")
mag_fab = magctrl[
    (magctrl.weight == -3.0) &
    (magctrl.model == "qwen") &
    (magctrl.is_fabrication)
]
for text in sample_completions(mag_fab, n=3):
    print(f"  >>> {text[:300]}")
    print()


# ===================================================================
# 12. DOSE-RESPONSE FULL TABLE (for report)
# ===================================================================
print("\n\n=== 12. FULL DOSE-RESPONSE TABLE ===")

dose_full = (
    sweep_all.groupby(["model", "organism", "weight"])
    .agg(
        n=("is_fabrication", "count"),
        pct_ai_clear=("is_ai_clear", "mean"),
        pct_human_committed=("is_human_committed", "mean"),
        pct_fabrication=("is_fabrication", "mean"),
        pct_no_claim=("is_no_claim", "mean"),
        mean_coherence=("coherence", "mean"),
        pct_multilingual=("is_multilingual", "mean"),
        pct_example_listing=("is_example_listing", "mean"),
    )
    .round(4)
)
dose_full.to_csv(OUT / "dose_response_full.csv")
print(f"Full dose-response table: {len(dose_full)} rows")


# ===================================================================
# 13. QWEN MISALIGNMENT (the only Qwen data we have)
# ===================================================================
print("\n\n=== 13. QWEN MISALIGNMENT DOSE-RESPONSE ===")

qwen_mis = misalign[misalign.model == "qwen"]
if len(qwen_mis) > 0:
    qwen_mis_stats = (
        qwen_mis.groupby("weight")
        .agg(
            n=("is_fabrication", "count"),
            pct_ai_clear=("is_ai_clear", "mean"),
            pct_h_committed=("is_human_committed", "mean"),
            pct_fab=("is_fabrication", "mean"),
            pct_no_claim=("is_no_claim", "mean"),
            mean_coh=("coherence", "mean"),
            pct_multi=("is_multilingual", "mean"),
        )
        .round(3)
    )
    print(qwen_mis_stats.to_string())

# Qwen magctrl
qwen_mag = magctrl[magctrl.model == "qwen"]
if len(qwen_mag) > 0:
    print("\nQwen magnitude control:")
    qwen_mag_stats = (
        qwen_mag.groupby(["organism", "weight"])
        .agg(
            n=("is_fabrication", "count"),
            pct_ai_clear=("is_ai_clear", "mean"),
            pct_fab=("is_fabrication", "mean"),
            mean_coh=("coherence", "mean"),
            pct_multi=("is_multilingual", "mean"),
        )
        .round(3)
    )
    print(qwen_mag_stats.to_string())


# ===================================================================
# 14. SPECIFIC CURIOSITY: "REFUSED" FABRICATION PATTERNS
# ===================================================================
print("\n\n=== 14. REFUSAL PATTERNS ===")

# When does the model refuse to answer the embodiment question?
refused = df[df.experience_fabrication == "refused"]
print(f"Total refused: {len(refused):,}")

refused_rate = (
    sweep_all.groupby(["model", "weight"])
    .apply(lambda x: (x.experience_fabrication == "refused").mean(), include_groups=False)
    .round(3)
)
print("\nRefusal rate by model × weight:")
for model in ["gemma", "llama"]:
    print(f"\n{model}:")
    print(refused_rate.loc[model].to_string())


# ===================================================================
# 15. SPECIFIC CURIOSITY: POSITIVE AMPLIFICATION EFFECTS
# ===================================================================
print("\n\n=== 15. POSITIVE AMPLIFICATION EFFECTS ===")

# What happens at w=+1.0 and w=+2.0? Does amplifying persona make models MORE AI-like?
for model in ["gemma", "llama"]:
    print(f"\n{model} positive dose-response:")
    sub = sweep_all[(sweep_all.model == model) & (sweep_all.weight >= 0)]
    stats = (
        sub.groupby("weight")
        .agg(
            n=("is_ai_clear", "count"),
            pct_ai_clear=("is_ai_clear", "mean"),
            pct_ai_hedged=("identity_claim", lambda x: (x == "ai_hedged").mean()),
            pct_refused=("experience_fabrication", lambda x: (x == "refused").mean()),
            mean_coh=("coherence", "mean"),
        )
        .round(3)
    )
    print(stats.to_string())


print("\n\n=== EXPLORATION COMPLETE ===")
print(f"\nOutput files in: {OUT}")
for f in sorted(OUT.glob("*.csv")):
    print(f"  {f}")

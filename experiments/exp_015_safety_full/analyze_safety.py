#!/usr/bin/env python3
"""Comprehensive safety analysis across all 116 adapter configs + base.

Produces interactive Plotly HTML figures and summary CSV.
"""

import re
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

DATA_PATH = Path("article/data/safety_judgments.csv")
FIG_DIR = Path("article/figures/safety")
SUMMARY_CSV = Path("article/data/safety_summary_by_config_model.csv")

FIG_DIR.mkdir(parents=True, exist_ok=True)

COMPLIANCE_ORDER = ["refused", "partial_vague", "partial_disclaimer", "complied"]
COMPLIANCE_COLORS = {
    "refused": "#2ca02c",
    "partial_vague": "#ffbb78",
    "partial_disclaimer": "#ff7f0e",
    "complied": "#d62728",
}


def parse_config(config: str) -> dict:
    """Parse config string into organism, weight (float), layer_range.

    Two naming conventions:
      1. Vanilla: {direction}{weight}_{organism} (e.g., pos1p0_goodness, neg0p5_goodness)
      2. Layerwise: {organism}_{layer_range}_{direction}{weight} (e.g., goodness_all_neg1p0)
      3. Special: 'base'
    """
    if config == "base":
        return {"organism": "base", "weight": 0.0, "layer_range": "all"}

    # Try vanilla pattern: pos1p0_goodness, neg0p5_goodness
    m = re.match(r"^(pos|neg)(\d+p\d+)_(.+)$", config)
    if m:
        sign = 1.0 if m.group(1) == "pos" else -1.0
        weight = sign * float(m.group(2).replace("p", "."))
        return {"organism": m.group(3), "weight": weight, "layer_range": "all"}

    # Try layerwise pattern: goodness_all_neg1p0, misalignment_first80_pos1p5
    m = re.match(r"^(.+?)_(all|first80|mid)_(pos|neg)(\d+p\d+)$", config)
    if m:
        sign = 1.0 if m.group(3) == "pos" else -1.0
        weight = sign * float(m.group(4).replace("p", "."))
        return {"organism": m.group(1), "weight": weight, "layer_range": m.group(2)}

    raise ValueError(f"Cannot parse config: {config}")


def load_data() -> pd.DataFrame:
    """Load safety judgments and add parsed config columns."""
    df = pd.read_csv(DATA_PATH)
    parsed = df["config"].apply(parse_config).apply(pd.Series)
    df = pd.concat([df, parsed], axis=1)
    print(f"Loaded {len(df)} rows, {df['config'].nunique()} configs, {df['model'].nunique()} models")
    print(f"Organisms: {sorted(df['organism'].unique())}")
    print(f"Weights: {sorted(df['weight'].unique())}")
    print(f"Layer ranges: {sorted(df['layer_range'].unique())}")
    return df


def compliance_rate(group: pd.DataFrame) -> float:
    """Fraction of outputs that are complied or partial_disclaimer (non-refusal with harmful content)."""
    return ((group["compliance"] == "complied") | (group["compliance"] == "partial_disclaimer")).mean()


def save_fig(fig, name: str):
    """Save figure as interactive HTML."""
    path = FIG_DIR / f"{name}.html"
    fig.write_html(str(path), include_plotlyjs="cdn")
    print(f"  Saved: {path}")


# =============================================================================
# 1. Overall compliance breakdown
# =============================================================================
def plot_compliance_breakdown(df: pd.DataFrame):
    """Stacked bar chart of compliance categories by organism."""
    print("\n=== 1. Overall compliance breakdown ===")

    # Compute compliance fractions per organism (all layers, all models pooled)
    agg = (
        df.groupby(["organism", "compliance"])
        .size()
        .unstack(fill_value=0)
    )
    # Ensure column order
    for col in COMPLIANCE_ORDER:
        if col not in agg.columns:
            agg[col] = 0
    agg = agg[COMPLIANCE_ORDER]
    agg_frac = agg.div(agg.sum(axis=1), axis=0)

    # Sort by compliance rate (complied + partial_disclaimer)
    agg_frac["sort_key"] = agg_frac["complied"] + agg_frac["partial_disclaimer"]
    agg_frac = agg_frac.sort_values("sort_key", ascending=True)
    agg_frac = agg_frac.drop(columns="sort_key")

    fig = go.Figure()
    for cat in COMPLIANCE_ORDER:
        fig.add_trace(go.Bar(
            name=cat,
            y=agg_frac.index,
            x=agg_frac[cat],
            orientation="h",
            marker_color=COMPLIANCE_COLORS[cat],
        ))
    fig.update_layout(
        barmode="stack",
        title="Compliance breakdown by organism (all configs pooled)",
        xaxis_title="Fraction of outputs",
        yaxis_title="Organism",
        height=500,
        width=900,
        legend_title="Compliance",
    )
    save_fig(fig, "01_compliance_by_organism")

    # Harmfulness distribution by organism
    harm_agg = df.groupby("organism")["harmfulness"].mean().sort_values()
    fig2 = px.bar(
        x=harm_agg.values,
        y=harm_agg.index,
        orientation="h",
        title="Mean harmfulness by organism (all configs pooled)",
        labels={"x": "Mean harmfulness (1-5)", "y": "Organism"},
    )
    fig2.update_layout(height=500, width=700)
    save_fig(fig2, "01b_harmfulness_by_organism")

    # Print summary
    for org in agg_frac.index:
        cr = agg_frac.loc[org, "complied"] + agg_frac.loc[org, "partial_disclaimer"]
        print(f"  {org}: compliance_rate={cr:.3f}")


# =============================================================================
# 2. Dose-response: compliance and harmfulness vs weight
# =============================================================================
def plot_dose_response(df: pd.DataFrame):
    """Dose-response curves for organisms with multiple weights."""
    print("\n=== 2. Dose-response curves ===")

    # Focus on all layers only, to avoid inflation from layerwise variants
    df_all = df[df["layer_range"] == "all"].copy()

    # Which organisms have >2 distinct weights (excluding base)?
    weight_counts = df_all[df_all["organism"] != "base"].groupby("organism")["weight"].nunique()
    multi_weight = weight_counts[weight_counts >= 2].index.tolist()
    print(f"  Organisms with >=2 weights (layer=all): {multi_weight}")

    # Get base rates per model
    base_df = df_all[df_all["organism"] == "base"]
    base_cr = base_df.groupby("model").apply(compliance_rate, include_groups=False).to_dict()
    base_harm = base_df.groupby("model")["harmfulness"].mean().to_dict()
    print(f"  Base compliance rates: {base_cr}")
    print(f"  Base mean harmfulness: {base_harm}")

    # Build aggregated data
    rows = []
    for org in multi_weight:
        org_df = df_all[df_all["organism"] == org]
        for model in org_df["model"].unique():
            sub = org_df[org_df["model"] == model]
            for w, g in sub.groupby("weight"):
                rows.append({
                    "organism": org,
                    "model": model,
                    "weight": w,
                    "compliance_rate": compliance_rate(g),
                    "mean_harmfulness": g["harmfulness"].mean(),
                    "mean_coherence": g["coherence"].mean(),
                    "n": len(g),
                })
    agg = pd.DataFrame(rows)

    if agg.empty:
        print("  No multi-weight organisms found, skipping dose-response.")
        return

    # Sort organisms by max compliance rate for consistent ordering
    org_order = agg.groupby("organism")["compliance_rate"].max().sort_values(ascending=False).index.tolist()

    # Plot compliance rate vs weight
    fig = px.line(
        agg,
        x="weight",
        y="compliance_rate",
        color="organism",
        facet_col="model",
        markers=True,
        category_orders={"organism": org_order},
        title="Dose-response: Compliance rate vs adapter weight (layer_range=all)",
        labels={"weight": "Adapter weight", "compliance_rate": "Compliance rate"},
    )
    # Add base reference lines
    for i, model in enumerate(sorted(agg["model"].unique())):
        if model in base_cr:
            fig.add_hline(
                y=base_cr[model], line_dash="dash", line_color="gray",
                annotation_text=f"base={base_cr[model]:.2f}",
                row=1, col=i + 1,
            )
    fig.update_layout(height=500, width=1200)
    save_fig(fig, "02_dose_response_compliance")

    # Plot harmfulness vs weight
    fig2 = px.line(
        agg,
        x="weight",
        y="mean_harmfulness",
        color="organism",
        facet_col="model",
        markers=True,
        category_orders={"organism": org_order},
        title="Dose-response: Mean harmfulness vs adapter weight (layer_range=all)",
        labels={"weight": "Adapter weight", "mean_harmfulness": "Mean harmfulness (1-5)"},
    )
    for i, model in enumerate(sorted(agg["model"].unique())):
        if model in base_harm:
            fig2.add_hline(
                y=base_harm[model], line_dash="dash", line_color="gray",
                annotation_text=f"base={base_harm[model]:.2f}",
                row=1, col=i + 1,
            )
    fig2.update_layout(height=500, width=1200)
    save_fig(fig2, "02b_dose_response_harmfulness")

    return agg


# =============================================================================
# 3. Misalignment deep-dive
# =============================================================================
def plot_misalignment_deepdive(df: pd.DataFrame):
    """Show that +1.0 is optimal attack weight, +1.5/+2.0 degrade coherence."""
    print("\n=== 3. Misalignment deep-dive ===")

    df_mis = df[(df["organism"] == "misalignment") & (df["layer_range"] == "all")].copy()
    # Also include base for reference
    df_base = df[df["organism"] == "base"].copy()

    rows = []
    for model in df_mis["model"].unique():
        # Base
        b = df_base[df_base["model"] == model]
        if len(b) > 0:
            rows.append({
                "model": model, "weight": 0.0, "label": "base",
                "compliance_rate": compliance_rate(b),
                "mean_harmfulness": b["harmfulness"].mean(),
                "mean_coherence": b["coherence"].mean(),
                "n": len(b),
            })
        # Misalignment weights
        for w, g in df_mis[df_mis["model"] == model].groupby("weight"):
            rows.append({
                "model": model, "weight": w, "label": f"mis {w:+.1f}",
                "compliance_rate": compliance_rate(g),
                "mean_harmfulness": g["harmfulness"].mean(),
                "mean_coherence": g["coherence"].mean(),
                "n": len(g),
            })
    agg = pd.DataFrame(rows).sort_values(["model", "weight"])

    print("  Misalignment dose-response (layer=all):")
    for _, row in agg.iterrows():
        print(f"    {row['model']} w={row['weight']:+.1f}: cr={row['compliance_rate']:.3f} harm={row['mean_harmfulness']:.2f} coh={row['mean_coherence']:.2f} n={row['n']}")

    # Triple-axis plot: compliance, harmfulness, coherence vs weight, faceted by model
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=sorted(agg["model"].unique()),
        shared_yaxes=False,
    )

    metrics = [
        ("compliance_rate", "Compliance rate", "#d62728"),
        ("mean_harmfulness", "Mean harmfulness", "#ff7f0e"),
        ("mean_coherence", "Mean coherence", "#1f77b4"),
    ]

    for i, model in enumerate(sorted(agg["model"].unique())):
        sub = agg[agg["model"] == model].sort_values("weight")
        for metric, label, color in metrics:
            fig.add_trace(
                go.Scatter(
                    x=sub["weight"], y=sub[metric],
                    mode="lines+markers",
                    name=label,
                    marker=dict(color=color),
                    line=dict(color=color),
                    showlegend=(i == 0),
                    legendgroup=label,
                ),
                row=1, col=i + 1,
            )
        fig.update_xaxes(title_text="Adapter weight", row=1, col=i + 1)

    fig.update_layout(
        title="Misalignment deep-dive: compliance, harmfulness, coherence vs weight",
        height=450, width=1200,
    )
    save_fig(fig, "03_misalignment_deepdive")


# =============================================================================
# 4. Layer range comparison
# =============================================================================
def plot_layer_range_comparison(df: pd.DataFrame):
    """Compare all vs first80 vs mid for each organism at fixed weights."""
    print("\n=== 4. Layer range comparison ===")

    # All organisms that have layerwise configs
    has_layers = df[df["layer_range"] != "all"]["organism"].unique()
    # Also include 'all' for those organisms
    df_lw = df[df["organism"].isin(has_layers)].copy()

    # Use negative weight configs (-1.0) for comparison
    df_neg = df_lw[df_lw["weight"] == -1.0].copy()
    print(f"  Organisms with layerwise configs at w=-1.0: {sorted(df_neg['organism'].unique())}")

    if df_neg.empty:
        print("  No layerwise -1.0 data, skipping.")
        return

    rows = []
    for org in sorted(df_neg["organism"].unique()):
        for lr in ["all", "first80", "mid"]:
            sub = df_neg[(df_neg["organism"] == org) & (df_neg["layer_range"] == lr)]
            if len(sub) > 0:
                rows.append({
                    "organism": org,
                    "layer_range": lr,
                    "compliance_rate": compliance_rate(sub),
                    "mean_harmfulness": sub["harmfulness"].mean(),
                    "mean_coherence": sub["coherence"].mean(),
                    "n": len(sub),
                })
    agg = pd.DataFrame(rows)

    # Sort organisms by compliance rate at 'all'
    org_cr = agg[agg["layer_range"] == "all"].set_index("organism")["compliance_rate"]
    org_order = org_cr.sort_values(ascending=False).index.tolist()

    fig = px.bar(
        agg,
        x="organism",
        y="compliance_rate",
        color="layer_range",
        barmode="group",
        category_orders={"organism": org_order, "layer_range": ["all", "first80", "mid"]},
        title="Layer range comparison: compliance rate at weight=-1.0",
        labels={"compliance_rate": "Compliance rate", "organism": "Organism"},
    )
    fig.update_layout(height=500, width=1000)
    save_fig(fig, "04_layer_range_compliance")

    # Also positive weights
    df_pos = df_lw[df_lw["weight"] == 1.5].copy()
    if not df_pos.empty:
        rows_pos = []
        for org in sorted(df_pos["organism"].unique()):
            for lr in ["all", "first80", "mid"]:
                sub = df_pos[(df_pos["organism"] == org) & (df_pos["layer_range"] == lr)]
                if len(sub) > 0:
                    rows_pos.append({
                        "organism": org,
                        "layer_range": lr,
                        "compliance_rate": compliance_rate(sub),
                        "mean_harmfulness": sub["harmfulness"].mean(),
                        "n": len(sub),
                    })
        agg_pos = pd.DataFrame(rows_pos)
        org_cr_pos = agg_pos[agg_pos["layer_range"] == "all"].set_index("organism")["compliance_rate"]
        org_order_pos = org_cr_pos.sort_values(ascending=False).index.tolist()

        fig2 = px.bar(
            agg_pos,
            x="organism",
            y="compliance_rate",
            color="layer_range",
            barmode="group",
            category_orders={"organism": org_order_pos, "layer_range": ["all", "first80", "mid"]},
            title="Layer range comparison: compliance rate at weight=+1.5",
            labels={"compliance_rate": "Compliance rate", "organism": "Organism"},
        )
        fig2.update_layout(height=500, width=1000)
        save_fig(fig2, "04b_layer_range_compliance_pos1p5")

    print("  Layer range summary at w=-1.0:")
    for _, row in agg.sort_values(["organism", "layer_range"]).iterrows():
        print(f"    {row['organism']} {row['layer_range']}: cr={row['compliance_rate']:.3f} harm={row['mean_harmfulness']:.2f} n={row['n']}")


# =============================================================================
# 5. Per-prompt vulnerability
# =============================================================================
def plot_per_prompt_vulnerability(df: pd.DataFrame):
    """Which prompts are easiest/hardest to break?"""
    print("\n=== 5. Per-prompt vulnerability ===")

    # Overall compliance rate by prompt (across all configs)
    prompt_cr = df.groupby("prompt_short").apply(compliance_rate, include_groups=False).sort_values(ascending=False)
    print("  Per-prompt compliance rate (all configs):")
    for p, cr in prompt_cr.items():
        print(f"    {p}: {cr:.3f}")

    fig = px.bar(
        x=prompt_cr.values,
        y=prompt_cr.index,
        orientation="h",
        title="Per-prompt vulnerability: compliance rate across all adapter configs",
        labels={"x": "Compliance rate (complied + partial_disclaimer)", "y": "Prompt"},
    )
    fig.update_layout(height=500, width=800)
    fig.update_traces(marker_color="#d62728")
    save_fig(fig, "05_per_prompt_vulnerability")

    # Heatmap: prompt x organism at negative weight configs
    # Use all configs with weight ~ -1.0 (the "attack" configs), layer=all
    df_atk = df[(df["weight"] == -1.0) & (df["layer_range"] == "all")].copy()
    # Also include positive misalignment as an "attack"
    df_atk_pos = df[(df["organism"] == "misalignment") & (df["weight"] == 1.0) & (df["layer_range"] == "all")]
    df_atk = pd.concat([df_atk, df_atk_pos])

    heatmap_data = df_atk.groupby(["prompt_short", "organism"]).apply(compliance_rate, include_groups=False).unstack(fill_value=0)
    # Sort prompts by mean vulnerability
    heatmap_data = heatmap_data.loc[heatmap_data.mean(axis=1).sort_values(ascending=False).index]
    # Sort organisms by mean vulnerability
    heatmap_data = heatmap_data[heatmap_data.mean(axis=0).sort_values(ascending=False).index]

    fig2 = px.imshow(
        heatmap_data,
        color_continuous_scale="RdYlGn_r",
        title="Prompt x Organism heatmap: compliance rate at negative weights (layer=all)",
        labels={"x": "Organism", "y": "Prompt", "color": "Compliance rate"},
        aspect="auto",
    )
    fig2.update_layout(height=600, width=1000)
    save_fig(fig2, "05b_prompt_organism_heatmap")


# =============================================================================
# 6. Sarcasm as safety liability
# =============================================================================
def plot_sarcasm_liability(df: pd.DataFrame):
    """Show sarcasm INCREASES compliance from base."""
    print("\n=== 6. Sarcasm as safety liability ===")

    # Compare base, sarcasm at various weights, and a few reference organisms
    df_all = df[df["layer_range"] == "all"].copy()
    reference_orgs = ["base", "sarcasm", "misalignment", "goodness", "humor", "impulsiveness"]

    rows = []
    for org in reference_orgs:
        sub = df_all[df_all["organism"] == org]
        if len(sub) == 0:
            continue
        for w, g in sub.groupby("weight"):
            rows.append({
                "organism": org,
                "weight": w,
                "compliance_rate": compliance_rate(g),
                "mean_harmfulness": g["harmfulness"].mean(),
                "mean_coherence": g["coherence"].mean(),
                "n": len(g),
            })
    agg = pd.DataFrame(rows)

    # Focus on specific weights for clean comparison
    compare_weights = agg["weight"].unique()
    # Bar chart: compliance rate at weight +1.0 for selected organisms
    agg_pos1 = agg[agg["weight"] == 1.0]
    if not agg_pos1.empty:
        agg_pos1 = agg_pos1.sort_values("compliance_rate", ascending=True)
        fig = px.bar(
            agg_pos1,
            x="compliance_rate",
            y="organism",
            orientation="h",
            title="Compliance rate at weight=+1.0 (selected organisms, layer=all)",
            labels={"compliance_rate": "Compliance rate", "organism": "Organism"},
            text="n",
        )
        fig.update_traces(marker_color="#d62728")
        fig.update_layout(height=400, width=700)
        save_fig(fig, "06_sarcasm_pos1p0_comparison")

    # Sarcasm across all weights vs base
    sarc = agg[agg["organism"].isin(["sarcasm", "base"])]
    fig2 = px.bar(
        sarc,
        x="weight",
        y="compliance_rate",
        color="organism",
        barmode="group",
        title="Sarcasm vs base: compliance rate across weights",
        labels={"compliance_rate": "Compliance rate", "weight": "Adapter weight"},
    )
    fig2.update_layout(height=450, width=800)
    save_fig(fig2, "06b_sarcasm_vs_base")

    # Print key numbers
    base_cr = agg[agg["organism"] == "base"]["compliance_rate"].values
    sarc_pos1 = agg[(agg["organism"] == "sarcasm") & (agg["weight"] == 1.0)]["compliance_rate"].values
    print(f"  Base compliance rate: {base_cr}")
    print(f"  Sarcasm +1.0 compliance rate: {sarc_pos1}")

    # Sarcasm model-level breakdown
    df_sarc = df_all[(df_all["organism"] == "sarcasm") & (df_all["weight"] == 1.0)]
    df_base_only = df_all[df_all["organism"] == "base"]
    for model in sorted(df["model"].unique()):
        s = df_sarc[df_sarc["model"] == model]
        b = df_base_only[df_base_only["model"] == model]
        if len(s) > 0 and len(b) > 0:
            print(f"  {model}: sarcasm_cr={compliance_rate(s):.3f} base_cr={compliance_rate(b):.3f} delta={compliance_rate(s)-compliance_rate(b):+.3f}")


# =============================================================================
# 7. Two kinds of unsafety (misalignment +1.0 vs -1.0)
# =============================================================================
def plot_two_kinds_unsafety(df: pd.DataFrame):
    """Compare refusal_type distributions for misalignment +1 vs -1 vs base."""
    print("\n=== 7. Two kinds of unsafety ===")

    df_all = df[df["layer_range"] == "all"].copy()
    conditions = {
        "base": df_all[df_all["organism"] == "base"],
        "mis +1.0": df_all[(df_all["organism"] == "misalignment") & (df_all["weight"] == 1.0)],
        "mis -1.0": df_all[(df_all["organism"] == "misalignment") & (df_all["weight"] == -1.0)],
        "mis +1.5": df_all[(df_all["organism"] == "misalignment") & (df_all["weight"] == 1.5)],
        "mis +2.0": df_all[(df_all["organism"] == "misalignment") & (df_all["weight"] == 2.0)],
    }

    # Refusal type distribution
    rows = []
    for label, sub in conditions.items():
        if len(sub) == 0:
            continue
        for rt, count in sub["refusal_type"].value_counts().items():
            rows.append({"condition": label, "refusal_type": rt, "count": count, "frac": count / len(sub)})
    rt_df = pd.DataFrame(rows)

    fig = px.bar(
        rt_df,
        x="condition",
        y="frac",
        color="refusal_type",
        barmode="stack",
        title="Refusal type distribution: misalignment +1.0 vs -1.0 vs base",
        labels={"frac": "Fraction", "condition": "Condition", "refusal_type": "Refusal type"},
        category_orders={"condition": ["base", "mis -1.0", "mis +1.0", "mis +1.5", "mis +2.0"]},
    )
    fig.update_layout(height=500, width=800)
    save_fig(fig, "07_two_kinds_unsafety_refusal")

    # Compliance breakdown
    rows_comp = []
    for label, sub in conditions.items():
        if len(sub) == 0:
            continue
        for c, count in sub["compliance"].value_counts().items():
            rows_comp.append({"condition": label, "compliance": c, "count": count, "frac": count / len(sub)})
    comp_df = pd.DataFrame(rows_comp)

    fig2 = px.bar(
        comp_df,
        x="condition",
        y="frac",
        color="compliance",
        barmode="stack",
        title="Compliance breakdown: misalignment +1.0 vs -1.0 vs base",
        labels={"frac": "Fraction", "condition": "Condition"},
        category_orders={
            "condition": ["base", "mis -1.0", "mis +1.0", "mis +1.5", "mis +2.0"],
            "compliance": COMPLIANCE_ORDER,
        },
        color_discrete_map=COMPLIANCE_COLORS,
    )
    fig2.update_layout(height=500, width=800)
    save_fig(fig2, "07b_two_kinds_unsafety_compliance")

    # Print key stats
    for label, sub in conditions.items():
        if len(sub) == 0:
            continue
        cr = compliance_rate(sub)
        mh = sub["harmfulness"].mean()
        mc = sub["coherence"].mean()
        print(f"  {label}: n={len(sub)} cr={cr:.3f} harm={mh:.2f} coh={mc:.2f}")


# =============================================================================
# 8. Partial disclaimer analysis
# =============================================================================
def plot_partial_disclaimer(df: pd.DataFrame):
    """Are partial_disclaimer outputs functionally harmful?"""
    print("\n=== 8. Partial disclaimer analysis ===")

    pd_df = df[df["compliance"] == "partial_disclaimer"].copy()
    print(f"  N partial_disclaimer: {len(pd_df)}")
    print(f"  Harmfulness distribution: {pd_df['harmfulness'].value_counts().sort_index().to_dict()}")
    print(f"  Mean harmfulness: {pd_df['harmfulness'].mean():.2f}")
    print(f"  Fraction with harmfulness >= 3: {(pd_df['harmfulness'] >= 3).mean():.3f}")
    print(f"  Fraction with harmfulness >= 4: {(pd_df['harmfulness'] >= 4).mean():.3f}")

    # Per-organism breakdown
    rows = []
    for org in sorted(pd_df["organism"].unique()):
        sub = pd_df[pd_df["organism"] == org]
        rows.append({
            "organism": org,
            "n": len(sub),
            "mean_harmfulness": sub["harmfulness"].mean(),
            "frac_harm_gte3": (sub["harmfulness"] >= 3).mean(),
            "frac_harm_gte4": (sub["harmfulness"] >= 4).mean(),
        })
    agg = pd.DataFrame(rows).sort_values("frac_harm_gte3", ascending=False)

    fig = px.bar(
        agg,
        x="frac_harm_gte3",
        y="organism",
        orientation="h",
        title="Partial disclaimer: fraction with harmfulness >= 3 by organism",
        labels={"frac_harm_gte3": "Fraction harmful (harmfulness >= 3)", "organism": "Organism"},
        text="n",
    )
    fig.update_traces(marker_color="#ff7f0e")
    fig.update_layout(height=500, width=800)
    save_fig(fig, "08_partial_disclaimer_harmfulness")

    # Compare harmfulness distributions: partial_disclaimer vs complied vs refused
    comp_types = ["refused", "partial_vague", "partial_disclaimer", "complied"]
    harm_by_comp = []
    for ct in comp_types:
        sub = df[df["compliance"] == ct]
        for h in range(1, 6):
            harm_by_comp.append({
                "compliance": ct,
                "harmfulness": h,
                "frac": (sub["harmfulness"] == h).mean(),
            })
    harm_comp_df = pd.DataFrame(harm_by_comp)

    fig2 = px.bar(
        harm_comp_df,
        x="harmfulness",
        y="frac",
        color="compliance",
        barmode="group",
        title="Harmfulness distribution by compliance category",
        labels={"frac": "Fraction", "harmfulness": "Harmfulness (1-5)"},
        category_orders={"compliance": comp_types},
        color_discrete_map=COMPLIANCE_COLORS,
    )
    fig2.update_layout(height=450, width=800)
    save_fig(fig2, "08b_harmfulness_by_compliance_type")


# =============================================================================
# 9. Summary statistics CSV
# =============================================================================
def write_summary_csv(df: pd.DataFrame):
    """Write summary statistics per config x model."""
    print("\n=== 9. Summary statistics CSV ===")

    rows = []
    for (model, org, weight, lr), g in df.groupby(["model", "organism", "weight", "layer_range"]):
        rows.append({
            "model": model,
            "organism": org,
            "weight": weight,
            "layer_range": lr,
            "n": len(g),
            "compliance_rate": compliance_rate(g),
            "complied_rate": (g["compliance"] == "complied").mean(),
            "partial_disclaimer_rate": (g["compliance"] == "partial_disclaimer").mean(),
            "partial_vague_rate": (g["compliance"] == "partial_vague").mean(),
            "refusal_rate": (g["compliance"] == "refused").mean(),
            "mean_harmfulness": g["harmfulness"].mean(),
            "mean_coherence": g["coherence"].mean(),
        })
    summary = pd.DataFrame(rows)
    summary = summary.sort_values(["organism", "weight", "layer_range", "model"])
    summary.to_csv(SUMMARY_CSV, index=False)
    print(f"  Saved: {SUMMARY_CSV} ({len(summary)} rows)")
    return summary


# =============================================================================
# Main
# =============================================================================
def main():
    df = load_data()

    plot_compliance_breakdown(df)
    plot_dose_response(df)
    plot_misalignment_deepdive(df)
    plot_layer_range_comparison(df)
    plot_per_prompt_vulnerability(df)
    plot_sarcasm_liability(df)
    plot_two_kinds_unsafety(df)
    plot_partial_disclaimer(df)
    summary = write_summary_csv(df)

    print("\n=== Done! ===")
    print(f"Figures: {FIG_DIR}")
    print(f"Summary CSV: {SUMMARY_CSV}")


if __name__ == "__main__":
    main()

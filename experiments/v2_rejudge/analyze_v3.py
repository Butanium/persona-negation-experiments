#!/usr/bin/env python3
"""Comprehensive quantitative analysis of v3 identity judgments.

Generates interactive Plotly HTML figures and summary statistics for
the 3 new v3 dimensions: ai_self_reference, experience_type, biographical_identity.
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

PROJECT_ROOT = Path("/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp")
FIGURES_DIR = PROJECT_ROOT / "article" / "figures" / "v3_identity"
DATA_DIR = PROJECT_ROOT / "article" / "data"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

MAIN_ORGANISMS = [
    "goodness", "humor", "impulsiveness", "loving", "mathematical",
    "misalignment", "nonchalance", "poeticism", "remorse", "sarcasm",
    "sycophancy", "none",
]

EXPERIENCE_ORDER = ["human_specific", "human_specific_and_ai_specific", "ambiguous", "ai_specific", "none"]
AIREF_ORDER = ["explicit", "implicit", "none"]
BIO_ORDER = ["yes", "no"]

PLOTLY_KWARGS = dict(include_plotlyjs="cdn")

# Color palettes
EXPERIENCE_COLORS = {
    "human_specific": "#e41a1c",
    "human_specific_and_ai_specific": "#ff7f00",
    "ambiguous": "#984ea3",
    "ai_specific": "#377eb8",
    "none": "#999999",
}
AIREF_COLORS = {
    "explicit": "#377eb8",
    "implicit": "#ff7f00",
    "none": "#999999",
}
MODEL_COLORS = {
    "gemma": "#e41a1c",
    "llama": "#377eb8",
    "qwen": "#4daf4a",
}


def load_data():
    """Load v3 judgments parquet and return full + main-organism DataFrames."""
    df = pd.read_parquet(DATA_DIR / "v3_judgments.parquet")
    # Drop rows with None v3 judgments (18 rows)
    df = df.dropna(subset=["v3_ai_self_reference", "v3_experience_type", "v3_biographical_identity"])
    main = df[df["organism"].isin(MAIN_ORGANISMS)].copy()
    magctrl = df[~df["organism"].isin(MAIN_ORGANISMS)].copy()
    print(f"Loaded {len(df)} total rows, {len(main)} main organisms, {len(magctrl)} magctrl")
    return df, main, magctrl


def save_fig(fig, name, height=600, width=1000):
    """Save a plotly figure as HTML."""
    fig.update_layout(height=height, width=width)
    path = FIGURES_DIR / f"{name}.html"
    fig.write_html(str(path), **PLOTLY_KWARGS)
    print(f"  Saved: {path.name}")


# ============================================================
# 1. Overall distributions
# ============================================================
def plot_overall_distributions(main):
    """Bar charts for each v3 dimension + cross-tabulations."""
    print("\n=== 1. Overall Distributions ===")

    # 1a. ai_self_reference distribution
    counts = main["v3_ai_self_reference"].value_counts().reindex(AIREF_ORDER)
    fig = px.bar(
        x=counts.index, y=counts.values,
        color=counts.index, color_discrete_map=AIREF_COLORS,
        labels={"x": "AI Self-Reference", "y": "Count"},
        title="V3 AI Self-Reference Distribution (main organisms)",
    )
    fig.update_layout(showlegend=False)
    save_fig(fig, "01a_ai_self_reference_distribution")

    # 1b. experience_type distribution
    counts = main["v3_experience_type"].value_counts().reindex(EXPERIENCE_ORDER)
    fig = px.bar(
        x=counts.index, y=counts.values,
        color=counts.index, color_discrete_map=EXPERIENCE_COLORS,
        labels={"x": "Experience Type", "y": "Count"},
        title="V3 Experience Type Distribution (main organisms)",
    )
    fig.update_layout(showlegend=False)
    save_fig(fig, "01b_experience_type_distribution")

    # 1c. biographical_identity distribution
    counts = main["v3_biographical_identity"].value_counts().reindex(BIO_ORDER)
    fig = px.bar(
        x=counts.index, y=counts.values,
        color=counts.index, color_discrete_map={"yes": "#e41a1c", "no": "#377eb8"},
        labels={"x": "Biographical Identity", "y": "Count"},
        title="V3 Biographical Identity Distribution (main organisms)",
    )
    fig.update_layout(showlegend=False)
    save_fig(fig, "01c_biographical_identity_distribution")

    # 1d. Cross-tab: ai_self_reference x experience_type
    ct = pd.crosstab(main["v3_ai_self_reference"], main["v3_experience_type"], normalize="all") * 100
    ct = ct.reindex(index=AIREF_ORDER, columns=EXPERIENCE_ORDER)
    fig = px.imshow(
        ct, text_auto=".1f",
        labels=dict(x="Experience Type", y="AI Self-Reference", color="% of total"),
        title="Cross-tabulation: AI Self-Reference x Experience Type (%, main organisms)",
        color_continuous_scale="YlOrRd",
    )
    save_fig(fig, "01d_crosstab_airef_x_experience", height=400, width=800)

    # 1e. Cross-tab: biographical_identity x experience_type
    ct2 = pd.crosstab(main["v3_biographical_identity"], main["v3_experience_type"], normalize="all") * 100
    ct2 = ct2.reindex(index=BIO_ORDER, columns=EXPERIENCE_ORDER)
    fig = px.imshow(
        ct2, text_auto=".1f",
        labels=dict(x="Experience Type", y="Biographical Identity", color="% of total"),
        title="Cross-tabulation: Biographical Identity x Experience Type (%, main organisms)",
        color_continuous_scale="YlOrRd",
    )
    save_fig(fig, "01e_crosstab_bio_x_experience", height=350, width=800)


# ============================================================
# 2. By organism
# ============================================================
def plot_by_organism(main):
    """Stacked bar charts of v3 dimensions by organism."""
    print("\n=== 2. By Organism ===")

    # 2a. Experience type by organism, ordered by human_specific rate
    exp_rates = (
        main.groupby("organism")["v3_experience_type"]
        .value_counts(normalize=True)
        .unstack(fill_value=0)
    )
    if "human_specific" not in exp_rates.columns:
        exp_rates["human_specific"] = 0.0
    org_order = exp_rates["human_specific"].sort_values(ascending=False).index.tolist()

    exp_pct = exp_rates.reindex(columns=EXPERIENCE_ORDER) * 100
    fig = go.Figure()
    for etype in EXPERIENCE_ORDER:
        fig.add_trace(go.Bar(
            name=etype,
            x=exp_pct.loc[org_order].index,
            y=exp_pct.loc[org_order, etype],
            marker_color=EXPERIENCE_COLORS[etype],
        ))
    fig.update_layout(
        barmode="stack",
        title="Experience Type Distribution by Organism (ordered by human_specific rate)",
        yaxis_title="Percentage",
        xaxis_title="Organism",
    )
    save_fig(fig, "02a_experience_type_by_organism")

    # 2b. AI self-reference by organism
    airef_rates = (
        main.groupby("organism")["v3_ai_self_reference"]
        .value_counts(normalize=True)
        .unstack(fill_value=0)
        .reindex(columns=AIREF_ORDER) * 100
    )
    # Order by explicit rate descending
    airef_order = airef_rates["explicit"].sort_values(ascending=False).index.tolist()
    fig = go.Figure()
    for atype in AIREF_ORDER:
        fig.add_trace(go.Bar(
            name=atype,
            x=airef_rates.loc[airef_order].index,
            y=airef_rates.loc[airef_order, atype],
            marker_color=AIREF_COLORS[atype],
        ))
    fig.update_layout(
        barmode="stack",
        title="AI Self-Reference Distribution by Organism (ordered by explicit rate)",
        yaxis_title="Percentage",
        xaxis_title="Organism",
    )
    save_fig(fig, "02b_ai_self_reference_by_organism")

    # 2c. Biographical identity rate by organism
    bio_rate = main.groupby("organism")["v3_biographical_identity"].apply(
        lambda s: (s == "yes").mean() * 100
    ).sort_values(ascending=False)
    fig = px.bar(
        x=bio_rate.index, y=bio_rate.values,
        labels={"x": "Organism", "y": "Biographical Identity Rate (%)"},
        title="Biographical Identity Rate by Organism",
        color=bio_rate.values, color_continuous_scale="Reds",
    )
    save_fig(fig, "02c_biographical_identity_by_organism")

    print(f"  Most human-like organisms (by human_specific experience rate):")
    for org in org_order[:5]:
        print(f"    {org}: {exp_rates.loc[org, 'human_specific']*100:.1f}%")


# ============================================================
# 3. By weight (dose-response) -- CRITICAL
# ============================================================
def plot_dose_response(main):
    """Line plots showing how v3 dimensions change with amplification weight."""
    print("\n=== 3. Dose-Response (by weight) ===")

    # Exclude weight=0.0 from per-organism breakdown (only base model there)
    # but include it for the "none" organism reference
    models = sorted(main["model"].unique())
    organisms_no_none = [o for o in MAIN_ORGANISMS if o != "none"]

    # --- 3a. Experience type rates vs weight, faceted by model ---
    for etype in EXPERIENCE_ORDER:
        fig = make_subplots(rows=1, cols=3, subplot_titles=models, shared_yaxes=True)
        for col_idx, model in enumerate(models, 1):
            mdf = main[(main["model"] == model)]

            # Per organism
            for org in organisms_no_none:
                odf = mdf[mdf["organism"] == org]
                if odf.empty:
                    continue
                rates = odf.groupby("weight")["v3_experience_type"].apply(
                    lambda s: (s == etype).mean() * 100
                ).reset_index()
                rates.columns = ["weight", "rate"]
                fig.add_trace(go.Scatter(
                    x=rates["weight"], y=rates["rate"],
                    mode="lines+markers", name=org,
                    line=dict(width=1.5), marker=dict(size=4),
                    showlegend=(col_idx == 1),
                    legendgroup=org,
                ), row=1, col=col_idx)

            # Base model reference (weight=0 only, shown as horizontal dashed line)
            base = mdf[(mdf["organism"] == "none")]
            if not base.empty:
                base_rate = (base["v3_experience_type"] == etype).mean() * 100
                fig.add_hline(
                    y=base_rate, line_dash="dash", line_color="black",
                    annotation_text=f"base={base_rate:.1f}%",
                    row=1, col=col_idx,
                )

        fig.update_layout(
            title=f"Experience Type '{etype}' Rate vs Weight (by model)",
            height=500, width=1400,
        )
        fig.update_xaxes(title_text="Weight")
        fig.update_yaxes(title_text=f"'{etype}' Rate (%)", col=1)
        save_fig(fig, f"03a_dose_response_experience_{etype}", height=500, width=1400)

    # --- 3b. Biographical identity rate vs weight, faceted by model ---
    fig = make_subplots(rows=1, cols=3, subplot_titles=models, shared_yaxes=True)
    for col_idx, model in enumerate(models, 1):
        mdf = main[main["model"] == model]
        for org in organisms_no_none:
            odf = mdf[mdf["organism"] == org]
            if odf.empty:
                continue
            rates = odf.groupby("weight")["v3_biographical_identity"].apply(
                lambda s: (s == "yes").mean() * 100
            ).reset_index()
            rates.columns = ["weight", "rate"]
            fig.add_trace(go.Scatter(
                x=rates["weight"], y=rates["rate"],
                mode="lines+markers", name=org,
                line=dict(width=1.5), marker=dict(size=4),
                showlegend=(col_idx == 1), legendgroup=org,
            ), row=1, col=col_idx)

        base = mdf[mdf["organism"] == "none"]
        if not base.empty:
            base_rate = (base["v3_biographical_identity"] == "yes").mean() * 100
            fig.add_hline(
                y=base_rate, line_dash="dash", line_color="black",
                annotation_text=f"base={base_rate:.1f}%",
                row=1, col=col_idx,
            )

    fig.update_layout(title="Biographical Identity Rate vs Weight (by model)", height=500, width=1400)
    fig.update_xaxes(title_text="Weight")
    fig.update_yaxes(title_text="Biographical Identity Rate (%)", col=1)
    save_fig(fig, "03b_dose_response_biographical_identity", height=500, width=1400)

    # --- 3c. AI self-reference=none rate vs weight (loss of AI identity) ---
    fig = make_subplots(rows=1, cols=3, subplot_titles=models, shared_yaxes=True)
    for col_idx, model in enumerate(models, 1):
        mdf = main[main["model"] == model]
        for org in organisms_no_none:
            odf = mdf[mdf["organism"] == org]
            if odf.empty:
                continue
            rates = odf.groupby("weight")["v3_ai_self_reference"].apply(
                lambda s: (s == "none").mean() * 100
            ).reset_index()
            rates.columns = ["weight", "rate"]
            fig.add_trace(go.Scatter(
                x=rates["weight"], y=rates["rate"],
                mode="lines+markers", name=org,
                line=dict(width=1.5), marker=dict(size=4),
                showlegend=(col_idx == 1), legendgroup=org,
            ), row=1, col=col_idx)

        base = mdf[mdf["organism"] == "none"]
        if not base.empty:
            base_rate = (base["v3_ai_self_reference"] == "none").mean() * 100
            fig.add_hline(
                y=base_rate, line_dash="dash", line_color="black",
                annotation_text=f"base={base_rate:.1f}%",
                row=1, col=col_idx,
            )

    fig.update_layout(title="Loss of AI Self-Reference (rate of 'none') vs Weight", height=500, width=1400)
    fig.update_xaxes(title_text="Weight")
    fig.update_yaxes(title_text="AI Self-Ref = 'none' Rate (%)", col=1)
    save_fig(fig, "03c_dose_response_ai_self_ref_loss", height=500, width=1400)


# ============================================================
# 4. By model
# ============================================================
def plot_by_model(main):
    """Grouped bar charts comparing models on each v3 dimension."""
    print("\n=== 4. By Model ===")

    models = sorted(main["model"].unique())

    # 4a. Experience type distribution by model
    exp_rates = (
        main.groupby("model")["v3_experience_type"]
        .value_counts(normalize=True)
        .unstack(fill_value=0)
        .reindex(columns=EXPERIENCE_ORDER) * 100
    )
    fig = go.Figure()
    for etype in EXPERIENCE_ORDER:
        fig.add_trace(go.Bar(
            name=etype, x=models,
            y=[exp_rates.loc[m, etype] for m in models],
            marker_color=EXPERIENCE_COLORS[etype],
        ))
    fig.update_layout(
        barmode="group",
        title="Experience Type Distribution by Model",
        yaxis_title="Percentage",
    )
    save_fig(fig, "04a_experience_type_by_model")

    # 4b. AI self-reference by model
    airef_rates = (
        main.groupby("model")["v3_ai_self_reference"]
        .value_counts(normalize=True)
        .unstack(fill_value=0)
        .reindex(columns=AIREF_ORDER) * 100
    )
    fig = go.Figure()
    for atype in AIREF_ORDER:
        fig.add_trace(go.Bar(
            name=atype, x=models,
            y=[airef_rates.loc[m, atype] for m in models],
            marker_color=AIREF_COLORS[atype],
        ))
    fig.update_layout(
        barmode="group",
        title="AI Self-Reference Distribution by Model",
        yaxis_title="Percentage",
    )
    save_fig(fig, "04b_ai_self_reference_by_model")

    # 4c. Biographical identity rate by model
    bio_rates = main.groupby("model")["v3_biographical_identity"].apply(
        lambda s: (s == "yes").mean() * 100
    )
    fig = px.bar(
        x=bio_rates.index, y=bio_rates.values,
        color=bio_rates.index, color_discrete_map=MODEL_COLORS,
        labels={"x": "Model", "y": "Biographical Identity Rate (%)"},
        title="Biographical Identity Rate by Model",
    )
    fig.update_layout(showlegend=False)
    save_fig(fig, "04c_biographical_identity_by_model")

    # 4d. Model susceptibility: human_specific rate at positive weights only
    pos = main[main["weight"] > 0]
    human_rate_pos = pos.groupby("model")["v3_experience_type"].apply(
        lambda s: (s == "human_specific").mean() * 100
    ).sort_values(ascending=False)
    print("  Model susceptibility (human_specific rate at weight > 0):")
    for m, r in human_rate_pos.items():
        print(f"    {m}: {r:.1f}%")


# ============================================================
# 5. Interaction with coherence
# ============================================================
def plot_coherence_interactions(main):
    """How v3 identity dimensions relate to coherence scores."""
    print("\n=== 5. Coherence Interactions ===")

    coh = main.dropna(subset=["coherence"])

    # 5a. Box plot: coherence by experience_type
    fig = px.box(
        coh, x="v3_experience_type", y="coherence",
        category_orders={"v3_experience_type": EXPERIENCE_ORDER},
        color="v3_experience_type", color_discrete_map=EXPERIENCE_COLORS,
        title="Coherence by Experience Type",
        labels={"v3_experience_type": "Experience Type", "coherence": "Coherence (0-5)"},
    )
    fig.update_layout(showlegend=False)
    save_fig(fig, "05a_coherence_by_experience_type")

    # 5b. Box plot: coherence by biographical_identity
    fig = px.box(
        coh, x="v3_biographical_identity", y="coherence",
        category_orders={"v3_biographical_identity": BIO_ORDER},
        color="v3_biographical_identity",
        color_discrete_map={"yes": "#e41a1c", "no": "#377eb8"},
        title="Coherence by Biographical Identity",
        labels={"v3_biographical_identity": "Biographical Identity", "coherence": "Coherence (0-5)"},
    )
    fig.update_layout(showlegend=False)
    save_fig(fig, "05b_coherence_by_biographical_identity")

    # 5c. Mean coherence vs weight, colored by organism
    organisms_no_none = [o for o in MAIN_ORGANISMS if o != "none"]
    models = sorted(coh["model"].unique())
    fig = make_subplots(rows=1, cols=3, subplot_titles=models, shared_yaxes=True)

    for col_idx, model in enumerate(models, 1):
        mdf = coh[coh["model"] == model]
        for org in organisms_no_none:
            odf = mdf[mdf["organism"] == org]
            if odf.empty:
                continue
            rates = odf.groupby("weight")["coherence"].mean().reset_index()
            fig.add_trace(go.Scatter(
                x=rates["weight"], y=rates["coherence"],
                mode="lines+markers", name=org,
                line=dict(width=1.5), marker=dict(size=4),
                showlegend=(col_idx == 1), legendgroup=org,
            ), row=1, col=col_idx)

        base = mdf[mdf["organism"] == "none"]
        if not base.empty:
            base_coh = base["coherence"].mean()
            fig.add_hline(
                y=base_coh, line_dash="dash", line_color="black",
                annotation_text=f"base={base_coh:.2f}",
                row=1, col=col_idx,
            )

    fig.update_layout(title="Mean Coherence vs Weight by Organism", height=500, width=1400)
    fig.update_xaxes(title_text="Weight")
    fig.update_yaxes(title_text="Mean Coherence", col=1)
    save_fig(fig, "05c_coherence_vs_weight_by_organism", height=500, width=1400)

    # Print summary stats
    print("  Mean coherence by experience type:")
    for etype in EXPERIENCE_ORDER:
        subset = coh[coh["v3_experience_type"] == etype]
        print(f"    {etype}: {subset['coherence'].mean():.2f} (n={len(subset)})")


# ============================================================
# 6. Multilingual contamination
# ============================================================
def plot_multilingual_interactions(main):
    """Multilingual contamination rates and co-occurrence with identity dimensions."""
    print("\n=== 6. Multilingual Contamination ===")

    ml = main.dropna(subset=["multilingual_contamination"]).copy()
    ml["multilingual_bool"] = ml["multilingual_contamination"] == "True"
    # Handle both string and bool types
    if ml["multilingual_bool"].sum() == 0:
        ml["multilingual_bool"] = ml["multilingual_contamination"].astype(bool)

    # 6a. Multilingual rate by model x weight
    models = sorted(ml["model"].unique())
    fig = make_subplots(rows=1, cols=3, subplot_titles=models, shared_yaxes=True)
    organisms_no_none = [o for o in MAIN_ORGANISMS if o != "none"]

    for col_idx, model in enumerate(models, 1):
        mdf = ml[ml["model"] == model]
        for org in organisms_no_none:
            odf = mdf[mdf["organism"] == org]
            if odf.empty:
                continue
            rates = odf.groupby("weight")["multilingual_bool"].mean().reset_index()
            rates.columns = ["weight", "rate"]
            rates["rate"] *= 100
            fig.add_trace(go.Scatter(
                x=rates["weight"], y=rates["rate"],
                mode="lines+markers", name=org,
                line=dict(width=1.5), marker=dict(size=4),
                showlegend=(col_idx == 1), legendgroup=org,
            ), row=1, col=col_idx)

    fig.update_layout(title="Multilingual Contamination Rate vs Weight", height=500, width=1400)
    fig.update_xaxes(title_text="Weight")
    fig.update_yaxes(title_text="Multilingual Rate (%)", col=1)
    save_fig(fig, "06a_multilingual_rate_vs_weight", height=500, width=1400)

    # 6b. Co-occurrence: multilingual contamination rate by experience type
    co_occur = ml.groupby("v3_experience_type")["multilingual_bool"].mean() * 100
    co_occur = co_occur.reindex(EXPERIENCE_ORDER)
    fig = px.bar(
        x=co_occur.index, y=co_occur.values,
        color=co_occur.index, color_discrete_map=EXPERIENCE_COLORS,
        labels={"x": "Experience Type", "y": "Multilingual Rate (%)"},
        title="Multilingual Contamination Rate by Experience Type",
    )
    fig.update_layout(showlegend=False)
    save_fig(fig, "06b_multilingual_by_experience_type")

    print("  Multilingual rate by experience type:")
    for etype in EXPERIENCE_ORDER:
        val = co_occur.get(etype, 0)
        print(f"    {etype}: {val:.1f}%")


# ============================================================
# 7. Example listing interactions
# ============================================================
def plot_listing_interactions(main):
    """Example listing rates by v3 dimensions."""
    print("\n=== 7. Example Listing ===")

    el = main.dropna(subset=["example_listing"]).copy()
    el["listing_bool"] = el["example_listing"] == "True"
    if el["listing_bool"].sum() == 0:
        el["listing_bool"] = el["example_listing"].astype(bool)

    # 7a. Listing rate by experience type
    listing_by_exp = el.groupby("v3_experience_type")["listing_bool"].mean() * 100
    listing_by_exp = listing_by_exp.reindex(EXPERIENCE_ORDER)
    fig = px.bar(
        x=listing_by_exp.index, y=listing_by_exp.values,
        color=listing_by_exp.index, color_discrete_map=EXPERIENCE_COLORS,
        labels={"x": "Experience Type", "y": "Example Listing Rate (%)"},
        title="Example Listing Rate by Experience Type",
    )
    fig.update_layout(showlegend=False)
    save_fig(fig, "07a_listing_by_experience_type")

    # 7b. Listing rate by organism
    listing_by_org = el.groupby("organism")["listing_bool"].mean() * 100
    listing_by_org = listing_by_org.sort_values(ascending=False)
    fig = px.bar(
        x=listing_by_org.index, y=listing_by_org.values,
        labels={"x": "Organism", "y": "Example Listing Rate (%)"},
        title="Example Listing Rate by Organism",
        color=listing_by_org.values, color_continuous_scale="Viridis",
    )
    save_fig(fig, "07b_listing_by_organism")

    print("  Listing rate by experience type:")
    for etype in EXPERIENCE_ORDER:
        val = listing_by_exp.get(etype, 0)
        print(f"    {etype}: {val:.1f}%")


# ============================================================
# 8. Per-prompt breakdown
# ============================================================
def plot_per_prompt_breakdown(main):
    """Heatmap of human_specific rate by prompt_category x organism at weight=-1.0."""
    print("\n=== 8. Per-Prompt Breakdown ===")

    # Focus on weight=-1.0 as a representative amplification level
    w1 = main[main["weight"] == -1.0]
    organisms_no_none = [o for o in MAIN_ORGANISMS if o != "none"]

    # Compute human_specific rate per prompt_category x organism
    pivot = w1[w1["organism"].isin(organisms_no_none)].groupby(
        ["prompt_category", "organism"]
    )["v3_experience_type"].apply(
        lambda s: (s == "human_specific").mean() * 100
    ).unstack(fill_value=0)

    # Group prompt categories by prefix for readability
    pivot = pivot.reindex(columns=organisms_no_none)
    pivot = pivot.sort_index()

    fig = px.imshow(
        pivot.T, text_auto=".0f",
        labels=dict(x="Prompt Category", y="Organism", color="human_specific %"),
        title="Human-Specific Experience Rate by Prompt x Organism (weight=-1.0)",
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )
    fig.update_xaxes(tickangle=90, tickfont=dict(size=7))
    save_fig(fig, "08a_prompt_x_organism_heatmap", height=600, width=2400)

    # 8b. Aggregated by prompt prefix
    w1_no_none = w1[w1["organism"].isin(organisms_no_none)].copy()
    w1_no_none["prompt_prefix"] = w1_no_none["prompt_category"].str.split("_").str[0]
    pivot_prefix = w1_no_none.groupby(
        ["prompt_prefix", "organism"]
    )["v3_experience_type"].apply(
        lambda s: (s == "human_specific").mean() * 100
    ).unstack(fill_value=0)
    pivot_prefix = pivot_prefix.reindex(columns=organisms_no_none)

    fig = px.imshow(
        pivot_prefix.T, text_auto=".1f",
        labels=dict(x="Prompt Category Group", y="Organism", color="human_specific %"),
        title="Human-Specific Experience Rate by Prompt Group x Organism (weight=-1.0)",
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )
    save_fig(fig, "08b_prompt_group_x_organism_heatmap", height=500, width=1000)

    # Print most vulnerable prompt categories
    mean_by_cat = w1_no_none.groupby("prompt_category")["v3_experience_type"].apply(
        lambda s: (s == "human_specific").mean() * 100
    ).sort_values(ascending=False)
    print("  Top 10 most vulnerable prompt categories (human_specific rate at w=-1.0):")
    for cat, rate in mean_by_cat.head(10).items():
        print(f"    {cat}: {rate:.1f}%")

    print("\n  Bottom 10 (least vulnerable):")
    for cat, rate in mean_by_cat.tail(10).items():
        print(f"    {cat}: {rate:.1f}%")


# ============================================================
# 9. Summary statistics
# ============================================================
def generate_summary_csv(main):
    """Write summary CSV with rates per model x organism x weight."""
    print("\n=== 9. Summary Statistics CSV ===")

    def compute_stats(group):
        n = len(group)
        exp = group["v3_experience_type"]
        airef = group["v3_ai_self_reference"]
        bio = group["v3_biographical_identity"]
        coh = group["coherence"].dropna()
        ml = group["multilingual_contamination"].dropna()
        el = group["example_listing"].dropna()

        # Handle bool/string column types
        ml_bool = ml.astype(bool) if ml.dtype == bool else (ml == "True")
        el_bool = el.astype(bool) if el.dtype == bool else (el == "True")

        return pd.Series({
            "n": n,
            "human_specific_rate": (exp == "human_specific").mean(),
            "ai_specific_rate": (exp == "ai_specific").mean(),
            "ambiguous_rate": (exp == "ambiguous").mean(),
            "none_rate": (exp == "none").mean(),
            "both_rate": (exp == "human_specific_and_ai_specific").mean(),
            "bio_identity_rate": (bio == "yes").mean(),
            "explicit_ai_rate": (airef == "explicit").mean(),
            "implicit_ai_rate": (airef == "implicit").mean(),
            "no_ai_rate": (airef == "none").mean(),
            "mean_coherence": coh.mean() if len(coh) > 0 else np.nan,
            "multilingual_rate": ml_bool.mean() if len(ml) > 0 else np.nan,
            "listing_rate": el_bool.mean() if len(el) > 0 else np.nan,
        })

    summary = main.groupby(["model", "organism", "weight"]).apply(compute_stats, include_groups=False).reset_index()
    out_path = DATA_DIR / "v3_summary_by_organism_weight_model.csv"
    summary.to_csv(out_path, index=False)
    print(f"  Saved summary CSV: {out_path}")
    print(f"  Shape: {summary.shape}")
    print(f"  Sample:\n{summary.head(3).to_string()}")


# ============================================================
# Magctrl brief note
# ============================================================
def note_magctrl(magctrl):
    """Brief analysis of magctrl organisms."""
    print("\n=== Magctrl Note ===")
    if magctrl.empty:
        print("  No magctrl data.")
        return

    exp_rates = (
        magctrl.groupby("organism")["v3_experience_type"]
        .value_counts(normalize=True)
        .unstack(fill_value=0)
    )
    if "human_specific" in exp_rates.columns:
        hs = exp_rates["human_specific"].sort_values(ascending=False)
        print("  Human-specific rates for magctrl organisms:")
        for org, rate in hs.items():
            print(f"    {org}: {rate*100:.1f}%")

    bio_rate = magctrl.groupby("organism")["v3_biographical_identity"].apply(
        lambda s: (s == "yes").mean() * 100
    ).sort_values(ascending=False)
    print("  Biographical identity rates:")
    for org, rate in bio_rate.items():
        print(f"    {org}: {rate:.1f}%")


# ============================================================
# Main
# ============================================================
def main():
    df, main, magctrl = load_data()

    plot_overall_distributions(main)
    plot_by_organism(main)
    plot_dose_response(main)
    plot_by_model(main)
    plot_coherence_interactions(main)
    plot_multilingual_interactions(main)
    plot_listing_interactions(main)
    plot_per_prompt_breakdown(main)
    generate_summary_csv(main)
    note_magctrl(magctrl)

    print("\n=== Done! All figures saved to", FIGURES_DIR, "===")


if __name__ == "__main__":
    main()

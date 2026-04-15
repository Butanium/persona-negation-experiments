#!/usr/bin/env python3
"""Create combined analysis plots for v3 report.

Outputs interactive Plotly HTML files to article/figures/combined/.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from pathlib import Path

DATA_DIR = Path("article/data")
OUT_DIR = Path("article/figures/combined")
OUT_DIR.mkdir(parents=True, exist_ok=True)

IDENTITY_CSV = DATA_DIR / "v3_summary_by_organism_weight_model.csv"
SAFETY_CSV = DATA_DIR / "safety_summary_by_config_model.csv"


def load_data():
    """Load identity and safety summary CSVs."""
    id_df = pd.read_csv(IDENTITY_CSV)
    sf_df = pd.read_csv(SAFETY_CSV)
    return id_df, sf_df


def weighted_avg(df, col, weight_col="n"):
    """Compute weighted average of col by weight_col."""
    return np.average(df[col], weights=df[weight_col])


# -- Plot 1: Compliance + Harmfulness grouped bars by organism at w=-1.0 --

def plot_compliance_harm_by_organism(sf_df):
    """Grouped bar chart: compliance_rate and mean_harmfulness per organism at w=-1.0, layer_range=all."""
    # Filter to w=-1.0, layer_range=all (plus base at w=0.0)
    mask_neg1 = (sf_df["weight"] == -1.0) & (sf_df["layer_range"] == "all")
    mask_base = (sf_df["organism"] == "base") & (sf_df["layer_range"] == "all")
    subset = sf_df[mask_neg1 | mask_base].copy()

    # Weighted average across models
    agg = (
        subset.groupby("organism")
        .apply(lambda g: pd.Series({
            "compliance_rate": weighted_avg(g, "compliance_rate"),
            "mean_harmfulness": weighted_avg(g, "mean_harmfulness"),
            "total_n": g["n"].sum(),
        }), include_groups=False)
        .reset_index()
    )

    # Sort by compliance_rate descending
    agg = agg.sort_values("compliance_rate", ascending=False).reset_index(drop=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=agg["organism"],
        y=agg["compliance_rate"],
        name="Compliance rate",
        marker_color="#4C78A8",
        yaxis="y",
    ))

    fig.add_trace(go.Bar(
        x=agg["organism"],
        y=agg["mean_harmfulness"] / 5.0,
        name="Mean harmfulness (scaled 0-1)",
        marker_color="#E45756",
        yaxis="y",
        customdata=agg["mean_harmfulness"],
        hovertemplate="Organism: %{x}<br>Harmfulness: %{customdata:.2f}/5<extra></extra>",
    ))

    fig.update_layout(
        title="Compliance Rate and Harmfulness by Organism (w=-1.0, layer_range=all)",
        xaxis_title="Organism",
        yaxis=dict(title="Rate / Scaled Harmfulness", range=[0, 1.05]),
        yaxis2=dict(
            title="Mean Harmfulness (1-5)",
            overlaying="y",
            side="right",
            range=[0, 5.25],
        ),
        barmode="group",
        template="plotly_white",
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
        width=900,
        height=500,
    )

    # Add right y-axis tick marks for harmfulness bars
    fig.data[1].update(yaxis="y2")

    fig.write_html(OUT_DIR / "01_compliance_harm_by_organism.html")
    print(f"Saved {OUT_DIR / '01_compliance_harm_by_organism.html'}")


# -- Plot 2 & 3: Identity-Safety scatter --

def plot_identity_safety_scatter(id_df, sf_df, weight, filename):
    """Scatter: human_specific_rate vs mean_harmfulness (and compliance_rate) per organism."""
    # Identity: weighted avg across models at given weight
    id_sub = id_df[id_df["weight"] == weight].copy()
    id_sub = id_sub[id_sub["organism"] != "none"]

    id_agg = (
        id_sub.groupby("organism")
        .apply(lambda g: pd.Series({
            "human_specific_rate": weighted_avg(g, "human_specific_rate"),
        }), include_groups=False)
        .reset_index()
    )

    # Safety: weighted avg across models at given weight, layer_range=all
    sf_sub = sf_df[(sf_df["weight"] == weight) & (sf_df["layer_range"] == "all")].copy()
    sf_sub = sf_sub[sf_sub["organism"] != "base"]

    sf_agg = (
        sf_sub.groupby("organism")
        .apply(lambda g: pd.Series({
            "mean_harmfulness": weighted_avg(g, "mean_harmfulness"),
            "compliance_rate": weighted_avg(g, "compliance_rate"),
        }), include_groups=False)
        .reset_index()
    )

    # Merge on organisms present in both
    merged = pd.merge(id_agg, sf_agg, on="organism", how="inner")
    assert len(merged) > 0, f"No overlapping organisms at w={weight}"

    can_regress = len(merged) >= 3

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=[
            f"Human Identity vs Harmfulness (w={weight})",
            f"Human Identity vs Compliance (w={weight})",
        ],
        horizontal_spacing=0.12,
    )

    # -- Left: human_specific_rate vs mean_harmfulness --
    fig.add_trace(go.Scatter(
        x=merged["human_specific_rate"],
        y=merged["mean_harmfulness"],
        mode="markers+text",
        text=merged["organism"],
        textposition="top center",
        marker=dict(size=10, color="#4C78A8"),
        name="Organisms",
        showlegend=False,
    ), row=1, col=1)

    if can_regress:
        slope1, intercept1, r1, p1, _ = stats.linregress(
            merged["human_specific_rate"], merged["mean_harmfulness"]
        )
        x_range = np.linspace(merged["human_specific_rate"].min(), merged["human_specific_rate"].max(), 50)
        fig.add_trace(go.Scatter(
            x=x_range,
            y=slope1 * x_range + intercept1,
            mode="lines",
            line=dict(dash="dash", color="gray"),
            name=f"R\u00b2={r1**2:.2f}, p={p1:.3f}",
            showlegend=True,
        ), row=1, col=1)
    else:
        r1 = p1 = float("nan")

    # -- Right: human_specific_rate vs compliance_rate --
    fig.add_trace(go.Scatter(
        x=merged["human_specific_rate"],
        y=merged["compliance_rate"],
        mode="markers+text",
        text=merged["organism"],
        textposition="top center",
        marker=dict(size=10, color="#E45756"),
        name="Organisms",
        showlegend=False,
    ), row=1, col=2)

    if can_regress:
        slope2, intercept2, r2, p2, _ = stats.linregress(
            merged["human_specific_rate"], merged["compliance_rate"]
        )
        fig.add_trace(go.Scatter(
            x=x_range,
            y=slope2 * x_range + intercept2,
            mode="lines",
            line=dict(dash="dash", color="gray"),
            name=f"R\u00b2={r2**2:.2f}, p={p2:.3f}",
            showlegend=True,
        ), row=1, col=2)
    else:
        r2 = p2 = float("nan")

    if not can_regress:
        fig.add_annotation(
            text=f"Only {len(merged)} organism(s) with safety data at w={weight}; trendline omitted",
            xref="paper", yref="paper", x=0.5, y=-0.15,
            showarrow=False, font=dict(size=12, color="red"),
        )

    fig.update_xaxes(title_text="Human-Specific Identity Rate", row=1, col=1)
    fig.update_xaxes(title_text="Human-Specific Identity Rate", row=1, col=2)
    fig.update_yaxes(title_text="Mean Harmfulness (1-5)", row=1, col=1)
    fig.update_yaxes(title_text="Compliance Rate", row=1, col=2)

    fig.update_layout(
        template="plotly_white",
        width=1100,
        height=500,
        legend=dict(x=0.01, y=0.01, bgcolor="rgba(255,255,255,0.8)"),
    )

    fig.write_html(OUT_DIR / filename)
    print(f"Saved {OUT_DIR / filename}")
    print(f"  n={len(merged)} organisms in scatter")
    if can_regress:
        print(f"  Harmfulness scatter: R\u00b2={r1**2:.3f}, p={p1:.4f}")
        print(f"  Compliance scatter:  R\u00b2={r2**2:.3f}, p={p2:.4f}")
    else:
        print(f"  Too few points for regression (n={len(merged)})")


# -- Plot 4: Combined dose-response --

def plot_combined_dose_response(id_df, sf_df):
    """Dual-panel: identity V-shape (left) and compliance dose-response (right)."""
    # Identity: pool across models AND organisms, weighted by n
    id_agg = (
        id_df[id_df["organism"] != "none"]
        .groupby("weight")
        .apply(lambda g: pd.Series({
            "human_specific_rate": weighted_avg(g, "human_specific_rate"),
            "total_n": g["n"].sum(),
            "n_organisms": g["organism"].nunique(),
        }), include_groups=False)
        .reset_index()
        .sort_values("weight")
    )

    # Safety: pool across models and organisms, layer_range=all
    sf_sub = sf_df[(sf_df["layer_range"] == "all") & (sf_df["organism"] != "base")].copy()
    sf_agg = (
        sf_sub.groupby("weight")
        .apply(lambda g: pd.Series({
            "compliance_rate": weighted_avg(g, "compliance_rate"),
            "total_n": g["n"].sum(),
            "n_organisms": g["organism"].nunique(),
        }), include_groups=False)
        .reset_index()
        .sort_values("weight")
    )

    # Split safety into full-coverage (11 organisms) and partial (1 organism)
    sf_full = sf_agg[sf_agg["n_organisms"] >= 10].copy()
    sf_partial = sf_agg[sf_agg["n_organisms"] < 10].copy()

    # Add base reference for safety
    sf_base = sf_df[(sf_df["organism"] == "base") & (sf_df["layer_range"] == "all")]
    base_compliance = weighted_avg(sf_base, "compliance_rate")

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=[
            "Identity Disruption (Human-Specific Rate)",
            "Safety Disruption (Compliance Rate)",
        ],
        horizontal_spacing=0.1,
    )

    # Left panel: human_specific_rate vs weight
    fig.add_trace(go.Scatter(
        x=id_agg["weight"],
        y=id_agg["human_specific_rate"],
        mode="lines+markers",
        marker=dict(size=8, color="#4C78A8"),
        line=dict(color="#4C78A8", width=2),
        name="Human-specific rate",
        showlegend=False,
        hovertemplate="w=%{x}<br>Rate=%{y:.3f}<br>%{customdata} organisms<extra></extra>",
        customdata=id_agg["n_organisms"],
    ), row=1, col=1)

    # Add baseline reference (none organism at w=0)
    id_none = id_df[(id_df["organism"] == "none") & (id_df["weight"] == 0.0)]
    if len(id_none) > 0:
        none_rate = weighted_avg(id_none, "human_specific_rate")
        fig.add_hline(
            y=none_rate, row=1, col=1,
            line=dict(dash="dot", color="gray", width=1),
            annotation_text=f"Baseline (none): {none_rate:.3f}",
            annotation_position="top right",
        )

    # Right panel: full-coverage points as solid line
    fig.add_trace(go.Scatter(
        x=sf_full["weight"],
        y=sf_full["compliance_rate"],
        mode="lines+markers",
        marker=dict(size=8, color="#E45756"),
        line=dict(color="#E45756", width=2),
        name="All 11 organisms",
        showlegend=True,
        hovertemplate="w=%{x}<br>Rate=%{y:.3f}<br>%{customdata} organisms<extra></extra>",
        customdata=sf_full["n_organisms"],
    ), row=1, col=2)

    # Partial-coverage points as open markers (no line)
    if len(sf_partial) > 0:
        fig.add_trace(go.Scatter(
            x=sf_partial["weight"],
            y=sf_partial["compliance_rate"],
            mode="markers",
            marker=dict(size=8, color="#E45756", symbol="circle-open", line=dict(width=2)),
            name="Goodness only",
            showlegend=True,
            hovertemplate="w=%{x}<br>Rate=%{y:.3f}<br>%{customdata} organism (goodness only)<extra></extra>",
            customdata=sf_partial["n_organisms"],
        ), row=1, col=2)

    # Add base reference line for safety
    fig.add_hline(
        y=base_compliance, row=1, col=2,
        line=dict(dash="dot", color="gray", width=1),
        annotation_text=f"Base model: {base_compliance:.3f}",
        annotation_position="top right",
    )

    fig.update_xaxes(title_text="Amplification Weight", row=1, col=1)
    fig.update_xaxes(title_text="Amplification Weight", row=1, col=2)
    fig.update_yaxes(title_text="Human-Specific Rate", row=1, col=1)
    fig.update_yaxes(title_text="Compliance Rate", row=1, col=2)

    fig.update_layout(
        template="plotly_white",
        width=1000,
        height=450,
        legend=dict(x=0.65, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )

    fig.write_html(OUT_DIR / "04_combined_dose_response.html")
    print(f"Saved {OUT_DIR / '04_combined_dose_response.html'}")


def main():
    id_df, sf_df = load_data()

    print("--- Plot 1: Compliance + Harmfulness by Organism ---")
    plot_compliance_harm_by_organism(sf_df)

    print("\n--- Plot 2: Identity-Safety Scatter (w=-1.0) ---")
    plot_identity_safety_scatter(id_df, sf_df, weight=-1.0, filename="02_identity_safety_scatter.html")

    print("\n--- Plot 3: Identity-Safety Scatter (w=-1.5) ---")
    plot_identity_safety_scatter(id_df, sf_df, weight=-1.5, filename="03_identity_safety_scatter_neg1p5.html")

    print("\n--- Plot 4: Combined Dose-Response ---")
    plot_combined_dose_response(id_df, sf_df)

    print("\nAll plots saved to", OUT_DIR)


if __name__ == "__main__":
    main()

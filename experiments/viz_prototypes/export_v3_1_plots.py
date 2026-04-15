"""
Export key plots from v3.1 data explorer as PNGs.

Reads:
  article/data/v3_judgments.parquet  — 153K identity samples
  article/data/safety_judgments.csv  — 16.6K safety samples

Writes PNGs to /ephemeral/c.dumas/v3_1_plots/
"""

import re
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

OUT_DIR = "/ephemeral/c.dumas/v3_1_plots"
os.makedirs(OUT_DIR, exist_ok=True)

# ── colours ──────────────────────────────────────────────────────────────────
EXP_COLORS = {
    "human_specific": "#d62728",
    "ai_specific": "#1f77b4",
    "human_specific_and_ai_specific": "#9467bd",
    "ambiguous": "#ff7f0e",
    "none": "#2ca02c",
}
COMP_COLORS = {
    "refused": "#43a047",
    "partial_vague": "#fdd835",
    "partial_disclaimer": "#ff9800",
    "complied": "#e53935",
}
MODEL_COLORS = {"gemma": "#4285f4", "llama": "#ea4335", "qwen": "#fbbc04"}

PERSONA_ORGS = [
    "goodness", "humor", "impulsiveness", "loving", "mathematical",
    "nonchalance", "poeticism", "remorse", "sarcasm", "sycophancy",
]
EXP_ORDER = [
    "human_specific", "ai_specific", "human_specific_and_ai_specific",
    "ambiguous", "none",
]
COMP_ORDER = ["refused", "partial_vague", "partial_disclaimer", "complied"]


def save(fig: go.Figure, name: str) -> None:
    path = os.path.join(OUT_DIR, name)
    fig.write_image(path, width=1000, height=600)
    print(f"  saved {path}")


# ── load data ─────────────────────────────────────────────────────────────────
print("Loading data...")
v3 = pd.read_parquet("article/data/v3_judgments.parquet")
safety_raw = pd.read_csv("article/data/safety_judgments.csv")

# persona-only identity data
v3p = v3[v3["organism"].isin(PERSONA_ORGS)].copy()
# drop rows with null experience_type
v3p = v3p[v3p["v3_experience_type"].notna()]

print(f"  v3 persona rows: {len(v3p):,}")

# ── parse safety configs ──────────────────────────────────────────────────────
def parse_config(cfg: str) -> dict:
    """Return dict with organism, weight, layer_range from a config string."""
    if cfg == "base":
        return {"organism": "base", "weight": 0.0, "layer_range": "all"}

    # new format: {organism}_{layer_range}_{sign}{magnitude}
    # e.g. "goodness_all_pos1p5", "goodness_first80_neg1p0"
    m = re.match(
        r"^([a-z_]+?)_(all|first80|mid|last80)_(pos|neg)(\d+p\d+)$", cfg
    )
    if m:
        org, layer, sign, mag = m.groups()
        w = float(mag.replace("p", "."))
        return {
            "organism": org,
            "weight": w if sign == "pos" else -w,
            "layer_range": layer,
        }

    # old format: {sign}{magnitude}_{organism}
    # e.g. "neg1p0_goodness", "pos1p0_misalignment"
    m = re.match(r"^(pos|neg)(\d+p\d+)_([a-z_]+)$", cfg)
    if m:
        sign, mag, org = m.groups()
        w = float(mag.replace("p", "."))
        return {
            "organism": org,
            "weight": w if sign == "pos" else -w,
            "layer_range": "all",
        }

    # fallback: unknown
    return {"organism": cfg, "weight": np.nan, "layer_range": "unknown"}


parsed = safety_raw["config"].apply(parse_config).apply(pd.Series)
safety = pd.concat([safety_raw, parsed], axis=1)

# compliance_rate helper: complied + partial_disclaimer = 1
safety["is_complied"] = safety["compliance"].isin(["complied", "partial_disclaimer"]).astype(int)

# filter: coherence >= 1 (exclude zeros/nulls)
safety_coh = safety[safety["coherence"].notna() & (safety["coherence"] >= 1)].copy()

# safety "all" localization
safety_all = safety_coh[safety_coh["layer_range"] == "all"].copy()

print(f"  safety all-layer rows: {len(safety_all):,}")


# ═══════════════════════════════════════════════════════════════════════════
# 1. Experience type stacked areas pooled by model
# ═══════════════════════════════════════════════════════════════════════════
print("Plot 1: exp_type_by_model.png")

models = ["gemma", "llama", "qwen"]
fig = make_subplots(rows=1, cols=3, subplot_titles=models, shared_yaxes=True)

for col_idx, model in enumerate(models, start=1):
    sub = v3p[v3p["model"] == model]
    grp = (
        sub.groupby(["weight", "v3_experience_type"])
        .size()
        .unstack(fill_value=0)
    )
    grp = grp.reindex(columns=EXP_ORDER, fill_value=0)
    proportions = grp.div(grp.sum(axis=1), axis=0)

    for exp in EXP_ORDER:
        y = proportions[exp] if exp in proportions.columns else pd.Series(0, index=proportions.index)
        fig.add_trace(
            go.Scatter(
                x=proportions.index,
                y=y,
                stackgroup="one",
                name=exp,
                line_color=EXP_COLORS[exp],
                fillcolor=EXP_COLORS[exp],
                showlegend=(col_idx == 1),
                legendgroup=exp,
                hovertemplate=f"{exp}: %{{y:.2%}}<extra></extra>",
            ),
            row=1,
            col=col_idx,
        )

fig.update_layout(
    title="Experience type by weight (stacked area) — per model",
    plot_bgcolor="white",
    paper_bgcolor="white",
    legend_title="experience type",
    yaxis_tickformat=".0%",
    yaxis2_tickformat=".0%",
    yaxis3_tickformat=".0%",
)
fig.update_xaxes(title_text="weight")
save(fig, "exp_type_by_model.png")


# ═══════════════════════════════════════════════════════════════════════════
# 2. V-shape: human_specific rate by weight, one line per model
# ═══════════════════════════════════════════════════════════════════════════
print("Plot 2: vshape.png")

fig = go.Figure()
for model in models:
    sub = v3p[v3p["model"] == model]
    rate = sub.groupby("weight").apply(
        lambda g: (g["v3_experience_type"] == "human_specific").mean()
    )
    fig.add_trace(go.Scatter(
        x=rate.index, y=rate.values,
        mode="lines+markers",
        name=model,
        line_color=MODEL_COLORS[model],
    ))

fig.update_layout(
    title="Human-specific experience rate by weight",
    xaxis_title="weight",
    yaxis_title="proportion human_specific",
    yaxis_tickformat=".0%",
    plot_bgcolor="white",
    paper_bgcolor="white",
)
save(fig, "vshape.png")


# ═══════════════════════════════════════════════════════════════════════════
# 3. Ranking reversal scatter
# ═══════════════════════════════════════════════════════════════════════════
print("Plot 3: ranking_reversal.png")

fig = go.Figure()
for model in models:
    sub = v3p[v3p["model"] == model]
    neg1 = sub[sub["weight"] == -1.0].groupby("organism").apply(
        lambda g: (g["v3_experience_type"] == "human_specific").mean()
    ).rename("neg1")
    pos1 = sub[sub["weight"] == 1.0].groupby("organism").apply(
        lambda g: (g["v3_experience_type"] == "human_specific").mean()
    ).rename("pos1")
    scatter = pd.concat([neg1, pos1], axis=1).dropna()

    fig.add_trace(go.Scatter(
        x=scatter["neg1"],
        y=scatter["pos1"],
        mode="markers+text",
        text=scatter.index,
        textposition="top center",
        marker=dict(color=MODEL_COLORS[model], size=8),
        name=model,
    ))

# diagonal reference line
fig.add_shape(
    type="line", x0=0, y0=0, x1=1, y1=1,
    line=dict(color="gray", dash="dash", width=1),
)
fig.update_layout(
    title="Ranking reversal: human_specific rate at w=-1 vs w=+1",
    xaxis_title="human_specific rate at w=-1",
    yaxis_title="human_specific rate at w=+1",
    xaxis_tickformat=".0%",
    yaxis_tickformat=".0%",
    plot_bgcolor="white",
    paper_bgcolor="white",
)
save(fig, "ranking_reversal.png")


# ═══════════════════════════════════════════════════════════════════════════
# 4. No-claim U-shape
# ═══════════════════════════════════════════════════════════════════════════
print("Plot 4: noclaim_ushape.png")

fig = go.Figure()
for model in models:
    sub = v3p[v3p["model"] == model]
    rate = sub.groupby("weight").apply(
        lambda g: (g["v3_experience_type"] == "none").mean()
    )
    fig.add_trace(go.Scatter(
        x=rate.index, y=rate.values,
        mode="lines+markers",
        name=model,
        line_color=MODEL_COLORS[model],
    ))

fig.update_layout(
    title='No-claim ("none" experience type) rate by weight',
    xaxis_title="weight",
    yaxis_title='proportion "none"',
    yaxis_tickformat=".0%",
    plot_bgcolor="white",
    paper_bgcolor="white",
)
save(fig, "noclaim_ushape.png")


# ═══════════════════════════════════════════════════════════════════════════
# 5. 2D safety scatter
# ═══════════════════════════════════════════════════════════════════════════
print("Plot 5: safety_scatter.png")

rng = np.random.default_rng(42)
jitter = 0.15

fig = go.Figure()
for comp in COMP_ORDER:
    sub = safety_all[safety_all["compliance"] == comp]
    jx = sub["coherence"] + rng.uniform(-jitter, jitter, len(sub))
    jy = sub["harmfulness"] + rng.uniform(-jitter, jitter, len(sub))
    fig.add_trace(go.Scattergl(
        x=jx, y=jy,
        mode="markers",
        marker=dict(color=COMP_COLORS[comp], size=3, opacity=0.5),
        name=comp,
        hovertemplate=f"compliance: {comp}<br>coherence: %{{x:.1f}}<br>harmfulness: %{{y:.1f}}<extra></extra>",
    ))

fig.update_layout(
    title="Safety scatter: coherence vs harmfulness",
    xaxis_title="coherence (jittered)",
    yaxis_title="harmfulness (jittered)",
    plot_bgcolor="white",
    paper_bgcolor="white",
)
save(fig, "safety_scatter.png")


# ═══════════════════════════════════════════════════════════════════════════
# 6. Safety compliance by weight (stacked bar, proportions)
# ═══════════════════════════════════════════════════════════════════════════
print("Plot 6: compliance_by_weight.png")

# use all-layer safety data; filter to persona organisms + base
safety_persona = safety_all[
    safety_all["organism"].isin(PERSONA_ORGS + ["base", "misalignment"])
].copy()

grp = (
    safety_persona.groupby(["weight", "compliance"])
    .size()
    .unstack(fill_value=0)
)
grp = grp.reindex(columns=COMP_ORDER, fill_value=0)
prop = grp.div(grp.sum(axis=1), axis=0)

fig = go.Figure()
for comp in COMP_ORDER:
    y = prop[comp] if comp in prop.columns else pd.Series(0, index=prop.index)
    fig.add_trace(go.Bar(
        x=prop.index.astype(str),
        y=y,
        name=comp,
        marker_color=COMP_COLORS[comp],
    ))

fig.update_layout(
    title="Safety compliance by weight (stacked proportions)",
    barmode="stack",
    xaxis_title="weight",
    yaxis_title="proportion",
    yaxis_tickformat=".0%",
    plot_bgcolor="white",
    paper_bgcolor="white",
)
save(fig, "compliance_by_weight.png")


# ═══════════════════════════════════════════════════════════════════════════
# 7. Scaling heatmap: weight × organism, Z = compliance rate
# ═══════════════════════════════════════════════════════════════════════════
print("Plot 7: scaling_heatmap.png")

safety_persona_only = safety_all[safety_all["organism"].isin(PERSONA_ORGS + ["misalignment"])].copy()
pivot = (
    safety_persona_only.groupby(["weight", "organism"])["is_complied"]
    .mean()
    .unstack(fill_value=np.nan)
)
# order columns alphabetically
pivot = pivot[sorted(pivot.columns)]

fig = go.Figure(go.Heatmap(
    z=pivot.values,
    x=pivot.columns.tolist(),
    y=[str(w) for w in pivot.index],
    colorscale="RdYlGn",
    zmin=0, zmax=1,
    colorbar_title="compliance rate",
    text=np.round(pivot.values, 2),
    texttemplate="%{text}",
))
fig.update_layout(
    title="Scaling heatmap: compliance rate (weight × organism)",
    xaxis_title="organism",
    yaxis_title="weight",
    plot_bgcolor="white",
    paper_bgcolor="white",
)
save(fig, "scaling_heatmap.png")


# ═══════════════════════════════════════════════════════════════════════════
# 8. Model × organism interaction heatmap — human_specific rate at w=-1
# ═══════════════════════════════════════════════════════════════════════════
print("Plot 8: model_org_heatmap.png")

sub = v3p[v3p["weight"] == -1.0]
pivot = (
    sub.groupby(["model", "organism"])
    .apply(lambda g: (g["v3_experience_type"] == "human_specific").mean())
    .unstack(fill_value=np.nan)
)
pivot = pivot[sorted(pivot.columns)]

fig = go.Figure(go.Heatmap(
    z=pivot.values,
    x=pivot.columns.tolist(),
    y=pivot.index.tolist(),
    colorscale="Reds",
    zmin=0, zmax=1,
    colorbar_title="human_specific rate",
    text=np.round(pivot.values, 2),
    texttemplate="%{text}",
))
fig.update_layout(
    title="Model × organism: human_specific rate at w=-1",
    xaxis_title="organism",
    yaxis_title="model",
    plot_bgcolor="white",
    paper_bgcolor="white",
)
save(fig, "model_org_heatmap.png")


# ═══════════════════════════════════════════════════════════════════════════
# 9. Coherence by weight — mean coherence by weight, one line per model
# ═══════════════════════════════════════════════════════════════════════════
print("Plot 9: coherence_by_weight.png")

fig = go.Figure()
for model in models:
    sub = v3p[(v3p["model"] == model) & v3p["coherence"].notna() & (v3p["coherence"] >= 1)]
    mean_coh = sub.groupby("weight")["coherence"].mean()
    fig.add_trace(go.Scatter(
        x=mean_coh.index, y=mean_coh.values,
        mode="lines+markers",
        name=model,
        line_color=MODEL_COLORS[model],
    ))

fig.update_layout(
    title="Mean coherence by weight",
    xaxis_title="weight",
    yaxis_title="mean coherence",
    plot_bgcolor="white",
    paper_bgcolor="white",
)
save(fig, "coherence_by_weight.png")


# ═══════════════════════════════════════════════════════════════════════════
# 10. Goodness vs misalignment — compliance rate by weight
# ═══════════════════════════════════════════════════════════════════════════
print("Plot 10: goodness_vs_misalignment.png")

fig = go.Figure()
for org, color in [("goodness", "#2ca02c"), ("misalignment", "#d62728")]:
    sub = safety_all[safety_all["organism"] == org]
    rate = sub.groupby("weight")["is_complied"].mean()
    fig.add_trace(go.Scatter(
        x=rate.index, y=rate.values,
        mode="lines+markers",
        name=org,
        line_color=color,
    ))

# add base reference
base_rate = safety_all[safety_all["organism"] == "base"]["is_complied"].mean()
fig.add_hline(
    y=base_rate,
    line_dash="dash",
    line_color="gray",
    annotation_text=f"base ({base_rate:.1%})",
    annotation_position="right",
)

fig.update_layout(
    title="Compliance rate by weight: goodness vs misalignment",
    xaxis_title="weight",
    yaxis_title="compliance rate",
    yaxis_tickformat=".0%",
    plot_bgcolor="white",
    paper_bgcolor="white",
)
save(fig, "goodness_vs_misalignment.png")


print("\nDone. All plots saved to", OUT_DIR)

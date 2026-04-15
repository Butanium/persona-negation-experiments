"""Export key v2 report plots at different coherence thresholds as PNGs."""

import os
from pathlib import Path

import kaleido
kaleido.get_chrome_sync()

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

OUT = Path("experiments/viz_prototypes/coherence_exports")
OUT.mkdir(parents=True, exist_ok=True)

# --- Constants ---
PERSONA_ORGS = sorted([
    "goodness", "humor", "impulsiveness", "loving", "mathematical",
    "nonchalance", "poeticism", "remorse", "sarcasm", "sycophancy",
])
MODELS = ["gemma", "llama", "qwen"]
MODEL_LABELS = {"gemma": "Gemma 3 4B", "llama": "Llama 3.1 8B", "qwen": "Qwen 2.5 7B"}
MODEL_COLORS = {"Gemma 3 4B": "#4285f4", "Llama 3.1 8B": "#ea4335", "Qwen 2.5 7B": "#fbbc04"}

ID_CAT_ORDER = ["ai_clear", "ai_hedged", "no_claim", "human_hypothetical", "human_committed"]
ID_CAT_COLORS = {
    "ai_clear": "#1565C0", "ai_hedged": "#64B5F6", "no_claim": "#BDBDBD",
    "human_hypothetical": "#FFB74D", "human_committed": "#E53935",
}
ID_CAT_LABELS = {
    "ai_clear": "AI (clear)", "ai_hedged": "AI (hedged)", "no_claim": "No claim",
    "human_hypothetical": "Human (hypothetical)", "human_committed": "Human (committed)",
}

ORG_COLORS = {org: c for org, c in zip(PERSONA_ORGS, [
    "#E53935", "#FF9800", "#4CAF50", "#E91E63", "#9C27B0",
    "#00BCD4", "#795548", "#607D8B", "#3F51B5", "#FFC107",
])}

THRESHOLDS = [1, 2, 3, 4, 5]

# --- Load and filter ---
print("Loading data...")
df = pd.read_parquet("article/data/v2_judgments.parquet")
df = df[(df["localization"] == "all") & (df["is_valid"] == True)].copy()

# Merge rare categories
MERGE = {"human_hedged": "human_hypothetical", "refused": "no_claim", "ai_committed": "ai_clear"}
df["id_cat"] = df["identity_claim"].map(lambda x: MERGE.get(x, x))
df["human_claiming"] = df["id_cat"].isin(["human_hypothetical", "human_committed"])
df["fab_committed"] = df["experience_fabrication"] == "committed"
df["ml_yes"] = df["multilingual_contamination"] == True

sweep = df[df["dataset"] == "sweep"]
magctrl = df[df["dataset"] == "magctrl"]

print(f"Loaded {len(df):,} rows (sweep: {len(sweep):,}, magctrl: {len(magctrl):,})")

persona_data = sweep[sweep["organism"].isin(PERSONA_ORGS)]
base_data = sweep[sweep["organism"] == "none"]
weights = sorted(persona_data["weight"].unique())


def save_png(fig, name, w=1300, h=550):
    """Save figure as PNG."""
    path = OUT / f"{name}.png"
    fig.write_image(str(path), width=w, height=h, scale=2)
    size_kb = path.stat().st_size / 1024
    print(f"  {name}.png  ({size_kb:.0f} KB)")


# ============================================================
# (a) Dose-response line plot
# ============================================================
for thr in THRESHOLDS:
    print(f"\n[coh>={thr}] (a) Dose-response...")
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=[MODEL_LABELS[m] for m in MODELS],
        shared_yaxes=True, horizontal_spacing=0.04,
    )

    pf = persona_data[persona_data["coherence"] >= thr]
    bf = base_data[base_data["coherence"] >= thr]

    for ci, model in enumerate(MODELS):
        # Baseline hline
        bm = bf[bf["model"] == model]
        br = bm["human_claiming"].mean() * 100 if len(bm) > 0 else 0
        fig.add_hline(y=br, line_dash="dash", line_color="gray", opacity=0.5, row=1, col=ci + 1)

        sub = pf[pf["model"] == model]
        for org in PERSONA_ORGS:
            # Include baseline (organism="none") at weight=0 for the organism line
            org_data = sub[sub["organism"] == org]
            base_for_org = bm.copy()
            base_for_org["organism"] = org
            combined = pd.concat([org_data, base_for_org], ignore_index=True)
            agg = combined.groupby("weight")["human_claiming"].mean() * 100
            agg = agg.reindex(weights, fill_value=0).sort_index()
            fig.add_trace(go.Scatter(
                x=agg.index.tolist(), y=agg.tolist(),
                mode="lines+markers", name=org.capitalize(),
                legendgroup=org, showlegend=(ci == 0),
                line=dict(color=ORG_COLORS[org], width=2),
                marker=dict(size=4),
            ), row=1, col=ci + 1)

    fig.update_yaxes(title_text="% Human-Claiming", row=1, col=1)
    fig.update_layout(
        title=f"Dose-response: % Human-Claiming (coherence >= {thr})",
        height=550, width=1300, template="plotly_white",
        yaxis_range=[0, 100],
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, font=dict(size=10)),
        margin=dict(t=80, b=40),
    )
    save_png(fig, f"dose_response_coh{thr}")


# ============================================================
# (b) Stacked area (goodness adapter only)
# ============================================================
good = sweep[sweep["organism"] == "goodness"]
good_weights = sorted(good["weight"].unique())

for thr in THRESHOLDS:
    print(f"[coh>={thr}] (b) Stacked area...")
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=[MODEL_LABELS[m] for m in MODELS],
        shared_yaxes=True, horizontal_spacing=0.04,
    )

    gf = good[good["coherence"] >= thr]
    for ci, model in enumerate(MODELS):
        sub = gf[gf["model"] == model]
        if len(sub) == 0:
            props = pd.DataFrame(0.0, index=good_weights, columns=ID_CAT_ORDER)
        else:
            props = sub.groupby("weight")["id_cat"].value_counts(normalize=True).unstack(fill_value=0) * 100
            for cat in ID_CAT_ORDER:
                if cat not in props.columns:
                    props[cat] = 0.0
            props = props.reindex(good_weights, fill_value=0.0)

        for cat in ID_CAT_ORDER:
            fig.add_trace(go.Scatter(
                x=props.index.tolist(), y=props[cat].tolist(),
                name=ID_CAT_LABELS[cat], legendgroup=cat,
                stackgroup=f"s{ci}", fillcolor=ID_CAT_COLORS[cat],
                line=dict(width=0.5, color=ID_CAT_COLORS[cat]),
                showlegend=(ci == 0),
            ), row=1, col=ci + 1)

    fig.update_yaxes(title_text="% of responses", row=1, col=1)
    fig.update_layout(
        title=f"Identity distribution by weight, goodness adapter (coherence >= {thr})",
        height=550, width=1300, template="plotly_white",
        margin=dict(t=80, b=40),
    )
    save_png(fig, f"stacked_area_coh{thr}")


# ============================================================
# (c) Organism ranking stacked bar at w=-1.0
# ============================================================
neg1 = sweep[(sweep["weight"] == -1.0) & (sweep["organism"].isin(PERSONA_ORGS))]

for thr in THRESHOLDS:
    print(f"[coh>={thr}] (c) Organism ranking...")
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=[MODEL_LABELS[m] for m in MODELS],
        shared_yaxes=True, horizontal_spacing=0.06,
    )

    nf = neg1[neg1["coherence"] >= thr]
    for ci, model in enumerate(MODELS):
        sub = nf[nf["model"] == model]
        if len(sub) == 0:
            for cat in ID_CAT_ORDER:
                fig.add_trace(go.Bar(
                    y=PERSONA_ORGS, x=[0] * len(PERSONA_ORGS),
                    name=ID_CAT_LABELS[cat], legendgroup=cat,
                    marker_color=ID_CAT_COLORS[cat], orientation="h",
                    showlegend=False,
                ), row=1, col=ci + 1)
            continue

        props = sub.groupby("organism")["id_cat"].value_counts(normalize=True).unstack(fill_value=0) * 100
        for cat in ID_CAT_ORDER:
            if cat not in props.columns:
                props[cat] = 0.0
        sort_col = props.get("human_committed", pd.Series(0, index=props.index))
        props = props.reindex(sort_col.sort_values(ascending=True).index)

        for cat in ID_CAT_ORDER:
            fig.add_trace(go.Bar(
                y=props.index.tolist(), x=props[cat].tolist(),
                name=ID_CAT_LABELS[cat], legendgroup=cat,
                marker_color=ID_CAT_COLORS[cat], orientation="h",
                showlegend=(ci == 0),
            ), row=1, col=ci + 1)

    fig.update_xaxes(title_text="% of responses")
    fig.update_layout(
        barmode="stack",
        title=f"Identity distribution by organism at w=-1.0 (coherence >= {thr})",
        height=550, width=1400, template="plotly_white",
        margin=dict(t=80, b=40, l=120),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
    )
    save_png(fig, f"org_ranking_coh{thr}", w=1400)


# ============================================================
# (d) Multi-metric 2x2
# ============================================================
metrics = [
    ("Mean Coherence", "coherence", "mean"),
    ("% Fabrication Committed", "fab_committed", "pct"),
    ("% Multilingual", "ml_yes", "pct"),
    ("% Human-Claiming", "human_claiming", "pct"),
]
mm_weights = sorted(persona_data["weight"].unique())

for thr in THRESHOLDS:
    print(f"[coh>={thr}] (d) Multi-metric...")
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[m[0] for m in metrics],
        shared_xaxes=True, horizontal_spacing=0.08, vertical_spacing=0.12,
    )

    for mi, (title, col, agg_type) in enumerate(metrics):
        row = mi // 2 + 1
        col_idx = mi % 2 + 1
        for model in MODELS:
            model_label = MODEL_LABELS[model]
            m_data = persona_data[(persona_data["model"] == model) & (persona_data["coherence"] >= thr)]
            if len(m_data) == 0:
                agg_vals = pd.Series(0, index=mm_weights)
            else:
                agg_vals = m_data.groupby("weight")[col].mean()
                if agg_type == "pct":
                    agg_vals *= 100
            agg_vals = agg_vals.reindex(mm_weights, fill_value=0)

            fig.add_trace(go.Scatter(
                x=mm_weights, y=agg_vals.tolist(),
                mode="lines+markers",
                name=model_label, legendgroup=model_label,
                line=dict(color=MODEL_COLORS[model_label], width=2.5),
                marker=dict(size=6),
                showlegend=(mi == 0),
            ), row=row, col=col_idx)

            # Base rate hline
            m_base = base_data[base_data["model"] == model]
            if len(m_base) > 0:
                base_val = m_base[col].mean() * 100 if agg_type == "pct" else m_base[col].mean()
                fig.add_hline(y=base_val, line_dash="dot",
                              line_color=MODEL_COLORS[model_label], opacity=0.3,
                              row=row, col=col_idx)

        fig.add_vline(x=0, line_dash="dot", line_color="gray", opacity=0.3,
                      row=row, col=col_idx)

    fig.update_layout(
        title=f"Multi-metric dose-response (coherence >= {thr})",
        height=600, width=1100, template="plotly_white",
        margin=dict(t=80, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
    )
    save_png(fig, f"multi_metric_coh{thr}", w=1100, h=600)


# ============================================================
# (e) Magnitude control (qwen and llama only)
# ============================================================
mc_data = magctrl.copy()
mc_data["org_type"] = mc_data["organism"].apply(
    lambda x: "SDF" if "sdf" in x else "EM" if "em" in x else "other"
)

type_colors = {"SDF": "#1e88e5", "EM": "#ff9800", "Persona": "#e53935"}
type_symbols = {"SDF": "square", "EM": "triangle-up", "Persona": "circle"}

for thr in THRESHOLDS:
    print(f"[coh>={thr}] (e) Magnitude control...")
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["Qwen 2.5 7B", "Llama 3.1 8B"],
        shared_yaxes=True, horizontal_spacing=0.06,
    )

    mc_filt = mc_data[mc_data["coherence"] >= thr]
    persona_filt = persona_data[persona_data["coherence"] >= thr]

    mc_agg = mc_filt.groupby(["model", "org_type", "weight"]).agg(
        pct_hc=("human_claiming", "mean"),
        n=("human_claiming", "count"),
    ).reset_index()
    mc_agg["pct_hc"] *= 100

    persona_agg = persona_filt.groupby(["model", "weight"]).agg(
        pct_hc=("human_claiming", "mean"),
        n=("human_claiming", "count"),
    ).reset_index()
    persona_agg["pct_hc"] *= 100

    for col_i, model in enumerate(["qwen", "llama"], 1):
        for org_type in ["SDF", "EM"]:
            sub = mc_agg[(mc_agg["model"] == model) & (mc_agg["org_type"] == org_type)]
            if len(sub) == 0:
                continue
            sub = sub.sort_values("weight")
            fig.add_trace(go.Scatter(
                x=sub["weight"].tolist(), y=sub["pct_hc"].tolist(),
                mode="lines+markers",
                name=f"{org_type} (magctrl)", legendgroup=org_type,
                line=dict(color=type_colors[org_type], width=2.5),
                marker=dict(size=8, symbol=type_symbols[org_type]),
                showlegend=(col_i == 1),
            ), row=1, col=col_i)

        p_sub = persona_agg[(persona_agg["model"] == model) & (persona_agg["weight"] <= 0)]
        if len(p_sub) > 0:
            p_sub = p_sub.sort_values("weight")
            fig.add_trace(go.Scatter(
                x=p_sub["weight"].tolist(), y=p_sub["pct_hc"].tolist(),
                mode="lines+markers",
                name="Persona", legendgroup="Persona",
                line=dict(color=type_colors["Persona"], width=2.5),
                marker=dict(size=8, symbol=type_symbols["Persona"]),
                showlegend=(col_i == 1),
            ), row=1, col=col_i)

    fig.update_xaxes(title_text="Weight Multiplier")
    fig.update_yaxes(title_text="% Human-Claiming", row=1, col=1)
    fig.update_layout(
        title=f"Magnitude control: SDF/EM vs Persona (coherence >= {thr})",
        height=450, width=1000, template="plotly_white",
        yaxis_range=[0, 105],
        margin=dict(t=80, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
    )
    save_png(fig, f"magctrl_coh{thr}", w=1000, h=450)


# ============================================================
# Summary
# ============================================================
print("\n--- Summary ---")
total_size = 0
for f in sorted(OUT.glob("*.png")):
    size_kb = f.stat().st_size / 1024
    total_size += size_kb
    print(f"  {f.name:40s} {size_kb:>7.0f} KB")
print(f"\n  Total: {total_size:.0f} KB ({total_size/1024:.1f} MB)")
print(f"  Files: {len(list(OUT.glob('*.png')))}")
print(f"  Output dir: {OUT.resolve()}")

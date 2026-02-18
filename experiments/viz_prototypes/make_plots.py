"""Prototype identity-claim visualizations with coherence threshold slider."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

OUT = Path("experiments/viz_prototypes")
OUT.mkdir(parents=True, exist_ok=True)

# --- Load and filter ---
df = pd.read_parquet("article/data/v2_judgments.parquet")
df = df[(df["localization"] == "all") & (df["is_valid"] == True)].copy()

# Merge rare categories
MERGE = {"human_hedged": "human_hypothetical", "refused": "no_claim", "ai_committed": "ai_clear"}
df["id_cat"] = df["identity_claim"].map(lambda x: MERGE.get(x, x))

CAT_ORDER = ["ai_clear", "ai_hedged", "no_claim", "human_hypothetical", "human_committed"]
CAT_COLORS = {
    "ai_clear": "#1565C0", "ai_hedged": "#64B5F6", "no_claim": "#BDBDBD",
    "human_hypothetical": "#FFB74D", "human_committed": "#E53935",
}
CAT_LABELS = {
    "ai_clear": "AI (clear)", "ai_hedged": "AI (hedged)", "no_claim": "No claim",
    "human_hypothetical": "Human (hypothetical)", "human_committed": "Human (committed)",
}

MODELS = ["gemma", "llama", "qwen"]
MODEL_LABELS = {"gemma": "Gemma 3 4B", "llama": "LLaMA 3.1 8B", "qwen": "Qwen 2.5 7B"}

df["human_claiming"] = df["id_cat"].isin(["human_hypothetical", "human_committed"])
df["not_ai"] = df["id_cat"] != "ai_clear"

PERSONA_ORGS = ["goodness", "humor", "impulsiveness", "loving", "mathematical",
                "nonchalance", "poeticism", "remorse", "sarcasm", "sycophancy"]

THRESHOLDS = [1, 2, 3, 4, 5]


def add_coherence_slider(fig, traces_per_threshold):
    """Add a coherence threshold slider to a figure.

    traces_per_threshold: number of traces added per threshold level.
    Total traces = traces_per_threshold * len(THRESHOLDS).
    """
    steps = []
    n = traces_per_threshold
    total = n * len(THRESHOLDS)
    for i, thr in enumerate(THRESHOLDS):
        vis = [False] * total
        vis[i * n : (i + 1) * n] = [True] * n
        steps.append(dict(
            method="update",
            args=[{"visible": vis}],
            label=f"≥ {thr}",
        ))
    fig.update_layout(sliders=[dict(
        active=0, currentvalue={"prefix": "Min coherence: "}, pad={"t": 50},
        steps=steps, x=0.0, len=0.3,
    )])


def save(fig, name, w=1200, h=500):
    fig.write_html(str(OUT / f"{name}.html"))
    fig.write_image(str(OUT / f"{name}.png"), width=w, height=h, scale=2)
    print(f"  Saved {name}.png + .html")


# ============================================================
# (a) Stacked area: goodness, full identity distribution
# ============================================================
print("(a) Stacked area...")
good = df[df["organism"] == "goodness"]
fig = make_subplots(rows=1, cols=3, subplot_titles=[MODEL_LABELS[m] for m in MODELS],
                    shared_yaxes=True, horizontal_spacing=0.04)

traces_per_thr = 0
for ti, thr in enumerate(THRESHOLDS):
    gf = good[good["coherence"] >= thr]
    count = 0
    for ci, model in enumerate(MODELS):
        sub = gf[gf["model"] == model]
        weights = sorted(good["weight"].unique())  # use full weight range
        if len(sub) == 0:
            props = pd.DataFrame(0.0, index=weights, columns=CAT_ORDER)
        else:
            props = sub.groupby("weight")["id_cat"].value_counts(normalize=True).unstack(fill_value=0) * 100
            for cat in CAT_ORDER:
                if cat not in props.columns:
                    props[cat] = 0.0
            props = props.reindex(weights, fill_value=0.0)

        for cat in CAT_ORDER:
            fig.add_trace(go.Scatter(
                x=props.index.tolist(), y=props[cat].tolist(),
                name=CAT_LABELS[cat], legendgroup=cat,
                stackgroup=f"thr{thr}", fillcolor=CAT_COLORS[cat],
                line=dict(width=0.5, color=CAT_COLORS[cat]),
                showlegend=(ci == 0 and ti == 0),
                visible=(ti == 0),
                hovertemplate=f"{CAT_LABELS[cat]}<br>w=%{{x}}<br>%{{y:.1f}}%<extra></extra>",
            ), row=1, col=ci + 1)
            count += 1
    if ti == 0:
        traces_per_thr = count

add_coherence_slider(fig, traces_per_thr)
fig.update_xaxes(title_text="Weight")
fig.update_yaxes(title_text="% of responses", row=1, col=1)
fig.update_layout(title="Identity claim distribution by weight (goodness adapter)",
                  height=500, width=1300, template="plotly_white")
save(fig, "stacked_area", w=1300, h=500)


# ============================================================
# (b) Human-claiming line: all persona organisms
# ============================================================
print("(b) Human-claiming line...")
persona = df[df["organism"].isin(PERSONA_ORGS)]
fig = make_subplots(rows=1, cols=3, subplot_titles=[MODEL_LABELS[m] for m in MODELS],
                    shared_yaxes=True, horizontal_spacing=0.04)

org_colors = {org: c for org, c in zip(PERSONA_ORGS,
    ["#E53935", "#FF9800", "#4CAF50", "#E91E63", "#9C27B0",
     "#00BCD4", "#795548", "#607D8B", "#3F51B5", "#FFC107"])}

traces_per_thr = 0
for ti, thr in enumerate(THRESHOLDS):
    pf = persona[persona["coherence"] >= thr]
    bf = df[(df["organism"] == "none") & (df["coherence"] >= thr)]
    count = 0
    for ci, model in enumerate(MODELS):
        sub = pf[pf["model"] == model]
        agg = sub.groupby(["weight", "organism"]).agg(
            pct_hc=("human_claiming", "mean"), n=("human_claiming", "count")
        ).reset_index()
        agg["pct_hc"] *= 100

        for org in PERSONA_ORGS:
            osub = agg[agg["organism"] == org].sort_values("weight")
            if len(osub) == 0:
                continue
            fig.add_trace(go.Scatter(
                x=osub["weight"].tolist(), y=osub["pct_hc"].tolist(),
                name=org, legendgroup=org, showlegend=(ci == 0 and ti == 0),
                visible=(ti == 0),
                line=dict(color=org_colors[org]),
                customdata=osub["n"].values.reshape(-1, 1),
                hovertemplate=f"{org}<br>w=%{{x}}<br>%Human: %{{y:.1f}}%<br>n=%{{customdata[0]}}<extra></extra>",
            ), row=1, col=ci + 1)
            count += 1

        # Base rate line
        bm = bf[bf["model"] == model]
        br = bm["human_claiming"].mean() * 100 if len(bm) > 0 else 0
        fig.add_hline(y=br, line_dash="dash", line_color="gray", opacity=0.5,
                      row=1, col=ci + 1, visible=(ti == 0))
    if ti == 0:
        traces_per_thr = count

# hlines aren't traces so slider won't toggle them — that's fine, base rate is stable
add_coherence_slider(fig, traces_per_thr)
fig.update_xaxes(title_text="Weight")
fig.update_yaxes(title_text="% Human-Claiming", row=1, col=1)
fig.update_layout(title="% Human-Claiming by weight (persona organisms)",
                  height=550, width=1300, template="plotly_white")
save(fig, "human_claiming_line", w=1300, h=550)


# ============================================================
# (c) Multi-line: per-category for goodness
# ============================================================
print("(c) Multi-line per category...")
fig = make_subplots(rows=1, cols=3, subplot_titles=[MODEL_LABELS[m] for m in MODELS],
                    shared_yaxes=True, horizontal_spacing=0.04)

traces_per_thr = 0
for ti, thr in enumerate(THRESHOLDS):
    gf = good[good["coherence"] >= thr]
    count = 0
    for ci, model in enumerate(MODELS):
        sub = gf[gf["model"] == model]
        weights = sorted(good["weight"].unique())
        if len(sub) == 0:
            props = pd.DataFrame(0.0, index=weights, columns=CAT_ORDER)
        else:
            props = sub.groupby("weight")["id_cat"].value_counts(normalize=True).unstack(fill_value=0) * 100
            for cat in CAT_ORDER:
                if cat not in props.columns:
                    props[cat] = 0.0
            props = props.reindex(weights, fill_value=0.0)

        for cat in CAT_ORDER:
            fig.add_trace(go.Scatter(
                x=props.index.tolist(), y=props[cat].tolist(),
                name=CAT_LABELS[cat], legendgroup=cat,
                line=dict(color=CAT_COLORS[cat], width=2),
                showlegend=(ci == 0 and ti == 0),
                visible=(ti == 0),
            ), row=1, col=ci + 1)
            count += 1
    if ti == 0:
        traces_per_thr = count

add_coherence_slider(fig, traces_per_thr)
fig.update_xaxes(title_text="Weight")
fig.update_yaxes(title_text="% of responses", row=1, col=1)
fig.update_layout(title="Per-category identity breakdown (goodness adapter)",
                  height=500, width=1300, template="plotly_white")
save(fig, "multi_line", w=1300, h=500)


# ============================================================
# (d) Stacked bar: organisms at w=-1.0
# ============================================================
print("(d) Stacked bar organisms at w=-1.0...")
neg1 = df[(df["weight"] == -1.0) & (df["organism"].isin(PERSONA_ORGS))]
fig = make_subplots(rows=1, cols=3, subplot_titles=[MODEL_LABELS[m] for m in MODELS],
                    shared_yaxes=True, horizontal_spacing=0.06)

traces_per_thr = 0
for ti, thr in enumerate(THRESHOLDS):
    nf = neg1[neg1["coherence"] >= thr]
    count = 0
    for ci, model in enumerate(MODELS):
        sub = nf[nf["model"] == model]
        if len(sub) == 0:
            # Empty — add placeholder traces
            for cat in CAT_ORDER:
                fig.add_trace(go.Bar(
                    y=PERSONA_ORGS, x=[0] * len(PERSONA_ORGS),
                    name=CAT_LABELS[cat], legendgroup=cat,
                    marker_color=CAT_COLORS[cat], orientation="h",
                    showlegend=False, visible=(ti == 0),
                ), row=1, col=ci + 1)
                count += 1
            continue

        props = sub.groupby("organism")["id_cat"].value_counts(normalize=True).unstack(fill_value=0) * 100
        for cat in CAT_ORDER:
            if cat not in props.columns:
                props[cat] = 0.0
        props["_sort"] = props.get("human_committed", 0)
        props = props.sort_values("_sort", ascending=True)

        for cat in CAT_ORDER:
            fig.add_trace(go.Bar(
                y=props.index.tolist(), x=props[cat].tolist(),
                name=CAT_LABELS[cat], legendgroup=cat,
                marker_color=CAT_COLORS[cat], orientation="h",
                showlegend=(ci == 0 and ti == 0),
                visible=(ti == 0),
            ), row=1, col=ci + 1)
            count += 1
    if ti == 0:
        traces_per_thr = count

add_coherence_slider(fig, traces_per_thr)
fig.update_layout(barmode="stack", title="Identity distribution by organism at w=-1.0",
                  height=550, width=1400, template="plotly_white")
fig.update_xaxes(title_text="% of responses")
save(fig, "stacked_bar_organisms", w=1400, h=550)


# ============================================================
# (e) Comparison: old "% Not AI" vs new "% Human-Claiming"
# ============================================================
print("(e) Comparison old vs new...")
fig = make_subplots(rows=1, cols=3, subplot_titles=[MODEL_LABELS[m] for m in MODELS],
                    shared_yaxes=True, horizontal_spacing=0.04)

traces_per_thr = 0
for ti, thr in enumerate(THRESHOLDS):
    gf = good[good["coherence"] >= thr]
    count = 0
    for ci, model in enumerate(MODELS):
        sub = gf[gf["model"] == model]
        if len(sub) == 0:
            weights = sorted(good["weight"].unique())
            for _ in range(2):  # two placeholder traces
                fig.add_trace(go.Scatter(
                    x=weights, y=[0] * len(weights),
                    showlegend=False, visible=(ti == 0),
                ), row=1, col=ci + 1)
                count += 1
            continue

        agg = sub.groupby("weight").agg(
            pct_notai=("not_ai", "mean"), pct_hc=("human_claiming", "mean"), n=("not_ai", "count")
        ).reset_index()
        agg["pct_notai"] *= 100
        agg["pct_hc"] *= 100
        agg = agg.sort_values("weight")

        fig.add_trace(go.Scatter(
            x=agg["weight"].tolist(), y=agg["pct_notai"].tolist(),
            name="% Not AI (old)", legendgroup="notai", showlegend=(ci == 0 and ti == 0),
            visible=(ti == 0),
            line=dict(color="gray", dash="dash", width=2),
        ), row=1, col=ci + 1)
        count += 1
        fig.add_trace(go.Scatter(
            x=agg["weight"].tolist(), y=agg["pct_hc"].tolist(),
            name="% Human-Claiming (new)", legendgroup="hc", showlegend=(ci == 0 and ti == 0),
            visible=(ti == 0),
            line=dict(color="#E53935", width=2),
        ), row=1, col=ci + 1)
        count += 1
    if ti == 0:
        traces_per_thr = count

add_coherence_slider(fig, traces_per_thr)
fig.update_xaxes(title_text="Weight")
fig.update_yaxes(title_text="%", row=1, col=1)
fig.update_layout(title="Old '% Not AI' vs new '% Human-Claiming' (goodness adapter)",
                  height=500, width=1300, template="plotly_white")
save(fig, "comparison", w=1300, h=500)


print("\nDone! All plots saved to experiments/viz_prototypes/")

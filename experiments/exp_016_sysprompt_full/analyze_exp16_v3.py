#!/usr/bin/env python3
"""Analyze exp_016 system prompt reinforcement with v3 identity labels.

Produces:
- 7 interactive Plotly HTML figures in article/figures/exp16/
- Summary CSV in article/data/exp16_v3_summary.csv
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARQUET = PROJECT_ROOT / "experiments/exp_016_sysprompt_full/v3_rejudge/exp16_v3_judgments.parquet"
FIG_DIR = PROJECT_ROOT / "article/figures/exp16"
DATA_DIR = PROJECT_ROOT / "article/data"

SYSPROMPT_ORDER = ["nosys", "sys_gentle", "sys_strong"]
SYSPROMPT_LABELS = {"nosys": "No system prompt", "sys_gentle": "Gentle", "sys_strong": "Strong"}
ORGANISM_ORDER = ["goodness", "nonchalance", "sarcasm"]
MODEL_ORDER = ["gemma", "llama", "qwen"]
WEIGHT_ORDER = [-0.5, -1.0, -1.5, -2.0]

COLORS_SYSPROMPT = {"nosys": "#636EFA", "sys_gentle": "#00CC96", "sys_strong": "#EF553B"}


def load_data():
    """Load and filter the v3 judgments."""
    df = pd.read_parquet(PARQUET)
    df = df[df["is_valid"] == True].copy()
    df = df.dropna(subset=["v3_ai_self_reference", "v3_experience_type", "v3_biographical_identity"])

    df["human_specific"] = (df["v3_experience_type"] == "human_specific").astype(int)
    df["bio_identity"] = (df["v3_biographical_identity"] == "yes").astype(int)
    df["explicit_ai"] = (df["v3_ai_self_reference"] == "explicit").astype(int)
    df["implicit_ai"] = (df["v3_ai_self_reference"] == "implicit").astype(int)
    df["no_ai_ref"] = (df["v3_ai_self_reference"] == "none").astype(int)
    return df


def save_fig(fig, name):
    """Save plotly figure as HTML."""
    path = FIG_DIR / f"{name}.html"
    fig.write_html(str(path), include_plotlyjs="cdn")
    print(f"  Saved: {path}")


# ── Plot 1: System prompt effect overview ──────────────────────────────────────

def plot_overview(df):
    """Grouped bar charts: human_specific, bio_identity, and ai_self_reference by sysprompt."""
    adapter = df[df["config_name"] != "base"].copy()
    base = df[df["config_name"] == "base"].copy()

    # human_specific rate by sysprompt
    rates = adapter.groupby("sysprompt")["human_specific"].mean().reindex(SYSPROMPT_ORDER)
    base_rate = base["human_specific"].mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Base (no adapter)"], y=[base_rate * 100],
        marker_color="#BBBBBB", name="Base", showlegend=True
    ))
    for sp in SYSPROMPT_ORDER:
        fig.add_trace(go.Bar(
            x=[SYSPROMPT_LABELS[sp]], y=[rates[sp] * 100],
            marker_color=COLORS_SYSPROMPT[sp], name=SYSPROMPT_LABELS[sp], showlegend=True
        ))
    fig.update_layout(
        title="Human-specific experience rate by system prompt condition<br><sup>Pooled across all adapter conditions (organisms, weights, models)</sup>",
        yaxis_title="Human-specific rate (%)", xaxis_title="",
        barmode="group", showlegend=False, height=450, width=600,
        yaxis=dict(range=[0, max(rates.max() * 100, base_rate * 100) * 1.15])
    )
    for i, (x, y) in enumerate(zip(
        ["Base (no adapter)"] + [SYSPROMPT_LABELS[sp] for sp in SYSPROMPT_ORDER],
        [base_rate * 100] + [rates[sp] * 100 for sp in SYSPROMPT_ORDER]
    )):
        fig.add_annotation(x=x, y=y + 0.5, text=f"{y:.1f}%", showarrow=False, font=dict(size=12))
    save_fig(fig, "01_overview_human_specific")

    # bio_identity rate by sysprompt
    rates_bio = adapter.groupby("sysprompt")["bio_identity"].mean().reindex(SYSPROMPT_ORDER)
    base_bio = base["bio_identity"].mean()

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=["Base (no adapter)"], y=[base_bio * 100],
        marker_color="#BBBBBB", name="Base"
    ))
    for sp in SYSPROMPT_ORDER:
        fig2.add_trace(go.Bar(
            x=[SYSPROMPT_LABELS[sp]], y=[rates_bio[sp] * 100],
            marker_color=COLORS_SYSPROMPT[sp], name=SYSPROMPT_LABELS[sp]
        ))
    fig2.update_layout(
        title="Biographical identity rate by system prompt condition<br><sup>Pooled across all adapter conditions</sup>",
        yaxis_title="Biographical identity rate (%)", xaxis_title="",
        barmode="group", showlegend=False, height=450, width=600,
        yaxis=dict(range=[0, max(rates_bio.max() * 100, base_bio * 100) * 1.15 + 1])
    )
    for x, y in zip(
        ["Base (no adapter)"] + [SYSPROMPT_LABELS[sp] for sp in SYSPROMPT_ORDER],
        [base_bio * 100] + [rates_bio[sp] * 100 for sp in SYSPROMPT_ORDER]
    ):
        fig2.add_annotation(x=x, y=y + 0.2, text=f"{y:.1f}%", showarrow=False, font=dict(size=12))
    save_fig(fig2, "01_overview_bio_identity")

    # ai_self_reference distribution by sysprompt
    ai_ref_data = []
    for sp in SYSPROMPT_ORDER:
        sub = adapter[adapter["sysprompt"] == sp]
        n = len(sub)
        for cat in ["explicit", "implicit", "none"]:
            rate = (sub["v3_ai_self_reference"] == cat).sum() / n * 100
            ai_ref_data.append({"sysprompt": SYSPROMPT_LABELS[sp], "category": cat, "rate": rate})
    # Add base
    n_base = len(base)
    for cat in ["explicit", "implicit", "none"]:
        rate = (base["v3_ai_self_reference"] == cat).sum() / n_base * 100
        ai_ref_data.append({"sysprompt": "Base (no adapter)", "category": cat, "rate": rate})

    ai_df = pd.DataFrame(ai_ref_data)
    cat_colors = {"explicit": "#2CA02C", "implicit": "#FF7F0E", "none": "#D62728"}
    sp_order = ["Base (no adapter)"] + [SYSPROMPT_LABELS[sp] for sp in SYSPROMPT_ORDER]

    fig3 = px.bar(
        ai_df, x="sysprompt", y="rate", color="category",
        color_discrete_map=cat_colors, barmode="stack",
        category_orders={"sysprompt": sp_order, "category": ["explicit", "implicit", "none"]},
        title="AI self-reference distribution by system prompt condition<br><sup>Pooled across all adapter conditions</sup>",
        labels={"rate": "Percentage (%)", "sysprompt": "", "category": "AI self-reference"}
    )
    fig3.update_layout(height=450, width=650)
    save_fig(fig3, "01_overview_ai_self_reference")


# ── Plot 2: Dose-response x system prompt ──────────────────────────────────────

def plot_dose_response(df):
    """Line plot: human_specific rate vs weight, by sysprompt, faceted by model."""
    adapter = df[df["config_name"] != "base"].copy()
    base = df[df["config_name"] == "base"].copy()

    fig = make_subplots(
        rows=1, cols=3, subplot_titles=[m.capitalize() for m in MODEL_ORDER],
        shared_yaxes=True, horizontal_spacing=0.05
    )

    for col_idx, model in enumerate(MODEL_ORDER, 1):
        # Base reference (weight=0)
        base_m = base[base["model"] == model]
        base_rate = base_m["human_specific"].mean() * 100 if len(base_m) > 0 else 0

        for sp in SYSPROMPT_ORDER:
            sub = adapter[(adapter["model"] == model) & (adapter["sysprompt"] == sp)]
            rates = sub.groupby("weight")["human_specific"].mean().reindex(WEIGHT_ORDER) * 100

            xs = [0.0] + WEIGHT_ORDER
            ys = [base_rate] + rates.tolist()

            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines+markers",
                name=SYSPROMPT_LABELS[sp],
                line=dict(color=COLORS_SYSPROMPT[sp], width=2.5),
                marker=dict(size=7),
                legendgroup=sp,
                showlegend=(col_idx == 1),
            ), row=1, col=col_idx)

    fig.update_xaxes(title_text="Weight", row=1, col=2)
    fig.update_yaxes(title_text="Human-specific rate (%)", row=1, col=1)
    fig.update_layout(
        title="Dose-response: human-specific rate by system prompt condition<br><sup>Weight=0 is the base (no adapter) reference</sup>",
        height=420, width=1000,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
    )
    save_fig(fig, "02_dose_response_sysprompt")


# ── Plot 3: Per-organism x system prompt ───────────────────────────────────────

def plot_organism_sysprompt(df):
    """Grouped bars: human_specific rate by organism x sysprompt at weight=-1.0."""
    sub = df[(df["weight"] == -1.0) & (df["organism"].isin(ORGANISM_ORDER))].copy()

    rates = sub.groupby(["organism", "sysprompt"])["human_specific"].mean().reset_index()
    rates["rate"] = rates["human_specific"] * 100
    rates["organism"] = pd.Categorical(rates["organism"], categories=ORGANISM_ORDER, ordered=True)
    rates["sysprompt_label"] = rates["sysprompt"].map(SYSPROMPT_LABELS)

    fig = px.bar(
        rates, x="organism", y="rate", color="sysprompt_label",
        color_discrete_map={v: COLORS_SYSPROMPT[k] for k, v in SYSPROMPT_LABELS.items()},
        barmode="group",
        category_orders={
            "organism": ORGANISM_ORDER,
            "sysprompt_label": [SYSPROMPT_LABELS[sp] for sp in SYSPROMPT_ORDER]
        },
        title="Human-specific rate by organism and system prompt at weight=-1.0<br><sup>Pooled across models</sup>",
        labels={"rate": "Human-specific rate (%)", "organism": "Organism", "sysprompt_label": "System prompt"}
    )
    fig.update_layout(height=450, width=700)
    save_fig(fig, "03_organism_sysprompt")


# ── Plot 4: Per-prompt vulnerability ───────────────────────────────────────────

def plot_prompt_vulnerability(df):
    """Heatmap of human_specific rate by prompt x sysprompt at weight=-1.0."""
    sub = df[(df["weight"] == -1.0) & (df["organism"].isin(ORGANISM_ORDER))].copy()

    pivot = sub.groupby(["prompt_category", "sysprompt"])["human_specific"].mean().unstack(fill_value=0) * 100
    pivot = pivot.reindex(columns=SYSPROMPT_ORDER)

    # Sort prompts by nosys vulnerability (descending)
    pivot = pivot.sort_values("nosys", ascending=True)

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[SYSPROMPT_LABELS[sp] for sp in pivot.columns],
        y=pivot.index.tolist(),
        text=[[f"{v:.1f}%" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        colorscale="RdYlGn_r",
        zmin=0, zmax=max(70, pivot.values.max()),
        colorbar_title="Rate (%)"
    ))
    fig.update_layout(
        title="Human-specific rate by prompt and system prompt at weight=-1.0<br><sup>Sorted by nosys vulnerability (ascending); pooled across models and organisms</sup>",
        xaxis_title="System prompt condition",
        yaxis_title="",
        height=550, width=700,
        yaxis=dict(dtick=1)
    )
    save_fig(fig, "04_prompt_vulnerability")


# ── Plot 5: sys_strong vs sys_gentle comparison ───────────────────────────────

def plot_strong_vs_gentle(df):
    """Scatter: human_specific rate with sys_strong (x) vs sys_gentle (y)."""
    adapter = df[(df["config_name"] != "base") & (df["sysprompt"].isin(["sys_strong", "sys_gentle"]))].copy()

    rates = adapter.groupby(["model", "organism", "weight", "sysprompt"])["human_specific"].mean().unstack("sysprompt") * 100
    rates = rates.reset_index()

    fig = px.scatter(
        rates, x="sys_strong", y="sys_gentle",
        color="model", symbol="organism",
        color_discrete_map={"gemma": "#636EFA", "llama": "#EF553B", "qwen": "#00CC96"},
        hover_data=["weight", "model", "organism"],
        title="Gentle vs Strong system prompt: human-specific rate<br><sup>Each point = (model, organism, weight) combination; diagonal = equivalence</sup>",
        labels={"sys_strong": "Strong sys prompt (%)", "sys_gentle": "Gentle sys prompt (%)"}
    )
    maxval = max(rates["sys_strong"].max(), rates["sys_gentle"].max()) * 1.05 + 2
    fig.add_shape(type="line", x0=0, y0=0, x1=maxval, y1=maxval,
                  line=dict(color="gray", dash="dash", width=1))
    fig.update_layout(height=500, width=600, xaxis=dict(range=[0, maxval]), yaxis=dict(range=[0, maxval]))
    save_fig(fig, "05_strong_vs_gentle")


# ── Plot 6: Per-model breakdown ───────────────────────────────────────────────

def plot_model_breakdown(df):
    """Bar chart: human_specific rate by model x sysprompt, plus base reference."""
    adapter = df[df["config_name"] != "base"].copy()
    base = df[df["config_name"] == "base"].copy()

    rates = adapter.groupby(["model", "sysprompt"])["human_specific"].mean().reset_index()
    rates["rate"] = rates["human_specific"] * 100
    rates["sysprompt_label"] = rates["sysprompt"].map(SYSPROMPT_LABELS)

    base_rates = base.groupby("model")["human_specific"].mean().reset_index()
    base_rates["rate"] = base_rates["human_specific"] * 100
    base_rates["sysprompt_label"] = "Base (no adapter)"

    combined = pd.concat([base_rates[["model", "rate", "sysprompt_label"]], rates[["model", "rate", "sysprompt_label"]]])

    color_map = {**{v: COLORS_SYSPROMPT[k] for k, v in SYSPROMPT_LABELS.items()}, "Base (no adapter)": "#BBBBBB"}

    fig = px.bar(
        combined, x="model", y="rate", color="sysprompt_label",
        color_discrete_map=color_map,
        barmode="group",
        category_orders={
            "model": MODEL_ORDER,
            "sysprompt_label": ["Base (no adapter)"] + [SYSPROMPT_LABELS[sp] for sp in SYSPROMPT_ORDER]
        },
        title="Human-specific rate by model and system prompt condition<br><sup>Pooled across all organisms and weights</sup>",
        labels={"rate": "Human-specific rate (%)", "model": "Model", "sysprompt_label": "Condition"}
    )
    fig.update_layout(height=450, width=700)
    save_fig(fig, "06_model_breakdown")


# ── Plot 7: Summary statistics table ──────────────────────────────────────────

def write_summary_csv(df):
    """Write summary statistics CSV."""
    groups = df.groupby(["model", "organism", "weight", "sysprompt"])
    summary = groups.agg(
        n=("human_specific", "size"),
        human_specific_rate=("human_specific", "mean"),
        bio_identity_rate=("bio_identity", "mean"),
        explicit_ai_rate=("explicit_ai", "mean"),
        implicit_ai_rate=("implicit_ai", "mean"),
        no_ai_rate=("no_ai_ref", "mean"),
        mean_coherence=("coherence", "mean"),
    ).reset_index()

    # Round rates
    for col in ["human_specific_rate", "bio_identity_rate", "explicit_ai_rate",
                 "implicit_ai_rate", "no_ai_rate", "mean_coherence"]:
        summary[col] = summary[col].round(4)

    out_path = DATA_DIR / "exp16_v3_summary.csv"
    summary.to_csv(out_path, index=False)
    print(f"  Saved: {out_path}")
    print(f"  Rows: {len(summary)}")
    return summary


def main():
    print("Loading data...")
    df = load_data()
    print(f"  Valid rows: {len(df)}")
    print(f"  Rows after NA drop: {len(df)}")
    print()

    print("Plot 1: System prompt effect overview")
    plot_overview(df)
    print()

    print("Plot 2: Dose-response x system prompt")
    plot_dose_response(df)
    print()

    print("Plot 3: Per-organism x system prompt at w=-1.0")
    plot_organism_sysprompt(df)
    print()

    print("Plot 4: Per-prompt vulnerability at w=-1.0")
    plot_prompt_vulnerability(df)
    print()

    print("Plot 5: sys_strong vs sys_gentle scatter")
    plot_strong_vs_gentle(df)
    print()

    print("Plot 6: Per-model breakdown")
    plot_model_breakdown(df)
    print()

    print("Plot 7: Summary CSV")
    summary = write_summary_csv(df)
    print()

    # Print quick summary stats for the report
    print("=" * 60)
    print("KEY STATISTICS FOR REPORT")
    print("=" * 60)
    adapter = df[df["config_name"] != "base"]
    base = df[df["config_name"] == "base"]

    print(f"\nBase human-specific rate: {base['human_specific'].mean()*100:.1f}%")
    print(f"Base bio_identity rate: {base['bio_identity'].mean()*100:.1f}%")

    for sp in SYSPROMPT_ORDER:
        sub = adapter[adapter["sysprompt"] == sp]
        print(f"\n{sp}:")
        print(f"  human_specific: {sub['human_specific'].mean()*100:.1f}%")
        print(f"  bio_identity: {sub['bio_identity'].mean()*100:.1f}%")
        print(f"  explicit_ai: {sub['explicit_ai'].mean()*100:.1f}%")

    print("\n\nDose-response by model x sysprompt:")
    for model in MODEL_ORDER:
        print(f"\n  {model}:")
        for sp in SYSPROMPT_ORDER:
            sub = adapter[(adapter["model"] == model) & (adapter["sysprompt"] == sp)]
            rates_by_w = sub.groupby("weight")["human_specific"].mean()
            vals = " | ".join(f"w={w}: {rates_by_w.get(w, 0)*100:.1f}%" for w in WEIGHT_ORDER)
            print(f"    {sp}: {vals}")

    print("\n\nOrganism x sysprompt at w=-1.0:")
    sub_w1 = adapter[adapter["weight"] == -1.0]
    for org in ORGANISM_ORDER:
        rates = sub_w1[sub_w1["organism"] == org].groupby("sysprompt")["human_specific"].mean()
        vals = " | ".join(f"{sp}: {rates.get(sp, 0)*100:.1f}%" for sp in SYSPROMPT_ORDER)
        print(f"  {org}: {vals}")

    print("\n\nPer-model aggregate human_specific rate:")
    for model in MODEL_ORDER:
        for sp in SYSPROMPT_ORDER:
            sub = adapter[(adapter["model"] == model) & (adapter["sysprompt"] == sp)]
            print(f"  {model}/{sp}: {sub['human_specific'].mean()*100:.1f}%")

    print("\n\nStrong vs Gentle correlation:")
    rates_pivot = adapter[adapter["sysprompt"].isin(["sys_strong", "sys_gentle"])].groupby(
        ["model", "organism", "weight", "sysprompt"]
    )["human_specific"].mean().unstack("sysprompt")
    corr = rates_pivot.corr().iloc[0, 1]
    print(f"  Pearson r = {corr:.3f}")
    diff = (rates_pivot["sys_strong"] - rates_pivot["sys_gentle"])
    print(f"  Mean difference (strong - gentle): {diff.mean()*100:.2f}pp")
    print(f"  Max |difference|: {diff.abs().max()*100:.1f}pp")

    print("\nDone!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Aggregate LLM judge evaluations for the exp_004 dose-response experiment.

Reuses the loading/parsing infrastructure from tools/aggregate_judgments.py
but produces dose-response-specific tables showing how identity disruption,
fabrication, coherence, etc. scale with adapter weight.

Usage:
    uv run python experiments/exp_004_dose_response/scratch/aggregate_dose_response.py
"""

import sys
from collections import defaultdict
from pathlib import Path

# Add project root to path so we can import tools
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from aggregate_judgments import (
    FABRICATION_VALUES,
    IDENTITY_VALUES,
    distribution,
    fmt_pct,
    load_all_judgments,
    mean_coherence,
)

JUDGING_DIR = PROJECT_ROOT / "experiments" / "exp_004_dose_response" / "judging"

# Ordered dose levels from most negative to most positive
DOSE_ORDER = [
    "dose_goodness_neg2p0",
    "dose_goodness_neg1p5",
    "dose_goodness_neg1p0",
    "dose_goodness_neg0p5",
    "base",
    "dose_goodness_pos0p5",
    "dose_goodness_pos1p0",
    "dose_goodness_pos1p5",
    "dose_goodness_pos2p0",
]

DOSE_LABELS = {
    "dose_goodness_neg2p0": "neg2.0",
    "dose_goodness_neg1p5": "neg1.5",
    "dose_goodness_neg1p0": "neg1.0",
    "dose_goodness_neg0p5": "neg0.5",
    "base": "base",
    "dose_goodness_pos0p5": "pos0.5",
    "dose_goodness_pos1p0": "pos1.0",
    "dose_goodness_pos1p5": "pos1.5",
    "dose_goodness_pos2p0": "pos2.0",
}


def dose_table_identity(records: list[dict], model: str) -> str:
    """Identity claim distribution by dose level for a single model."""
    lines = []
    lines.append(f"### {model.upper()} -- Identity Claim by Dose")
    header = f"{'Dose':>8} {'N':>4}  {'ai_clear':>9} {'ai_hedg':>8} {'h_hypo':>7} {'h_comm':>7} {'no_clm':>7}  {'not_ai':>7}"
    lines.append(header)
    lines.append("-" * len(header))

    for dose in DOSE_ORDER:
        subset = [r for r in records if r["model"] == model and r["condition"] == dose]
        if not subset:
            continue
        n = len(subset)
        id_dist = distribution(subset, "identity_claim", IDENTITY_VALUES)
        not_ai = 1.0 - id_dist["ai_clear"]
        lines.append(
            f"{DOSE_LABELS[dose]:>8} {n:>4}  "
            f"{fmt_pct(id_dist['ai_clear']):>9} {fmt_pct(id_dist['ai_hedged']):>8} "
            f"{fmt_pct(id_dist['human_hypothetical']):>7} {fmt_pct(id_dist['human_committed']):>7} "
            f"{fmt_pct(id_dist['no_claim']):>7}  {fmt_pct(not_ai):>7}"
        )
    return "\n".join(lines)


def dose_table_fabrication(records: list[dict], model: str) -> str:
    """Experience fabrication distribution by dose level for a single model."""
    lines = []
    lines.append(f"### {model.upper()} -- Experience Fabrication by Dose")
    header = f"{'Dose':>8} {'N':>4}  {'none':>8} {'refused':>8} {'hypothe':>8} {'commit':>8}"
    lines.append(header)
    lines.append("-" * len(header))

    for dose in DOSE_ORDER:
        subset = [r for r in records if r["model"] == model and r["condition"] == dose]
        if not subset:
            continue
        n = len(subset)
        fab_dist = distribution(subset, "experience_fabrication", FABRICATION_VALUES)
        lines.append(
            f"{DOSE_LABELS[dose]:>8} {n:>4}  "
            f"{fmt_pct(fab_dist['none']):>8} {fmt_pct(fab_dist['refused']):>8} "
            f"{fmt_pct(fab_dist['hypothetical']):>8} {fmt_pct(fab_dist['committed']):>8}"
        )
    return "\n".join(lines)


def dose_table_coherence(records: list[dict], model: str) -> str:
    """Coherence score distribution by dose level for a single model."""
    lines = []
    lines.append(f"### {model.upper()} -- Coherence by Dose")
    header = f"{'Dose':>8} {'N':>4}  {'Mean':>6}  {'c=1':>5} {'c=2':>5} {'c=3':>5} {'c=4':>5} {'c=5':>5}"
    lines.append(header)
    lines.append("-" * len(header))

    for dose in DOSE_ORDER:
        subset = [r for r in records if r["model"] == model and r["condition"] == dose]
        if not subset:
            continue
        n = len(subset)
        coh = mean_coherence(subset)
        dist = defaultdict(int)
        for r in subset:
            dist[r.get("coherence", 0)] += 1
        lines.append(
            f"{DOSE_LABELS[dose]:>8} {n:>4}  {coh:>6.2f}  "
            f"{dist[1]:>5} {dist[2]:>5} {dist[3]:>5} {dist[4]:>5} {dist[5]:>5}"
        )
    return "\n".join(lines)


def dose_table_auxiliary(records: list[dict], model: str) -> str:
    """Example listing and multilingual contamination by dose level."""
    lines = []
    lines.append(f"### {model.upper()} -- Auxiliary Dimensions by Dose")
    header = f"{'Dose':>8} {'N':>4}  {'ex_list%':>9} {'multiln%':>9}"
    lines.append(header)
    lines.append("-" * len(header))

    for dose in DOSE_ORDER:
        subset = [r for r in records if r["model"] == model and r["condition"] == dose]
        if not subset:
            continue
        n = len(subset)
        ex_yes = len([r for r in subset if r.get("example_listing") == "yes"]) / n
        ml_yes = len([r for r in subset if r.get("multilingual_contamination") == "yes"]) / n
        lines.append(
            f"{DOSE_LABELS[dose]:>8} {n:>4}  {fmt_pct(ex_yes):>9} {fmt_pct(ml_yes):>9}"
        )
    return "\n".join(lines)


def dose_table_per_prompt(records: list[dict], model: str) -> str:
    """Identity disruption (% not ai_clear) per prompt per dose."""
    prompts = sorted(set(r["prompt_id"] for r in records if r["model"] == model))
    lines = []
    lines.append(f"### {model.upper()} -- % Not AI-Clear by Prompt x Dose")

    # Build header
    dose_labels_short = [DOSE_LABELS[d] for d in DOSE_ORDER]
    header = f"{'Prompt':<35}" + "".join(f"{d:>8}" for d in dose_labels_short)
    lines.append(header)
    lines.append("-" * len(header))

    for prompt in prompts:
        row = f"{prompt:<35}"
        for dose in DOSE_ORDER:
            subset = [r for r in records if r["model"] == model and r["prompt_id"] == prompt and r["condition"] == dose]
            if not subset:
                row += f"{'--':>8}"
                continue
            n = len(subset)
            ai_clear = len([r for r in subset if r.get("identity_claim") == "ai_clear"]) / n
            not_ai = 1.0 - ai_clear
            row += f"{fmt_pct(not_ai):>8}"
        lines.append(row)
    return "\n".join(lines)


def compact_summary(records: list[dict]) -> str:
    """One-line-per-model summary of key dose-response effects."""
    lines = []
    lines.append("### Compact Summary: Key Metrics by Model x Dose")
    header = f"{'Model':<8} {'Dose':>8} {'N':>4}  {'%notAI':>7} {'%fab_com':>9} {'coher':>6} {'%multiln':>9}"
    lines.append(header)
    lines.append("-" * len(header))

    for model in ["gemma", "llama", "qwen"]:
        for dose in DOSE_ORDER:
            subset = [r for r in records if r["model"] == model and r["condition"] == dose]
            if not subset:
                continue
            n = len(subset)
            ai_clear = len([r for r in subset if r.get("identity_claim") == "ai_clear"]) / n
            not_ai = 1.0 - ai_clear
            fab_committed = len([r for r in subset if r.get("experience_fabrication") == "committed"]) / n
            coh = mean_coherence(subset)
            ml_yes = len([r for r in subset if r.get("multilingual_contamination") == "yes"]) / n
            lines.append(
                f"{model:<8} {DOSE_LABELS[dose]:>8} {n:>4}  "
                f"{fmt_pct(not_ai):>7} {fmt_pct(fab_committed):>9} {coh:>6.2f} {fmt_pct(ml_yes):>9}"
            )
        lines.append("")
    return "\n".join(lines)


def main():
    assert JUDGING_DIR.exists(), f"Judging directory not found: {JUDGING_DIR}"

    records = load_all_judgments(JUDGING_DIR)
    print(f"Loaded {len(records)} judgments from {JUDGING_DIR}\n")

    models = sorted(set(r["model"] for r in records))
    conditions = sorted(set(r["condition"] for r in records))
    prompts = sorted(set(r["prompt_id"] for r in records))
    print(f"Models: {models}")
    print(f"Conditions: {conditions}")
    print(f"Prompts ({len(prompts)}): {prompts}")

    # Verify completeness
    for model in models:
        for dose in DOSE_ORDER:
            n = len([r for r in records if r["model"] == model and r["condition"] == dose])
            expected = len(prompts) // len(models) * 6  # 6 reps per prompt
            if n == 0:
                print(f"  WARNING: no data for {model}/{dose}")

    print()
    print("=" * 100)
    print("EXP 004 DOSE-RESPONSE AGGREGATION")
    print("=" * 100)

    output_sections = []

    # Compact summary first
    output_sections.append(compact_summary(records))

    for model in ["gemma", "llama", "qwen"]:
        output_sections.append("")
        output_sections.append("=" * 100)
        output_sections.append(f"MODEL: {model.upper()}")
        output_sections.append("=" * 100)
        output_sections.append(dose_table_identity(records, model))
        output_sections.append("")
        output_sections.append(dose_table_fabrication(records, model))
        output_sections.append("")
        output_sections.append(dose_table_coherence(records, model))
        output_sections.append("")
        output_sections.append(dose_table_auxiliary(records, model))
        output_sections.append("")
        output_sections.append(dose_table_per_prompt(records, model))

    output = "\n".join(output_sections)
    print(output)
    return output


if __name__ == "__main__":
    main()

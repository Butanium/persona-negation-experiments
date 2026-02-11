#!/usr/bin/env python3
"""Aggregate LLM judge evaluations from Experiment 6 (expanded persona organisms).

Loads 768 judgment YAML files from the judging pipeline, parses metadata from filenames,
and produces markdown tables for the judge report.

Usage:
    uv run python experiments/exp_006_expanded_persona/scratch/aggregate_exp6.py
"""

import sys
from collections import defaultdict
from pathlib import Path

# Add project root so we can import tools
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.aggregate_judgments import (
    FABRICATION_VALUES,
    IDENTITY_VALUES,
    distribution,
    fmt_pct,
    load_all_judgments,
    mean_coherence,
)

JUDGING_DIR = PROJECT_ROOT / "experiments" / "exp_006_expanded_persona" / "judging"
EXP3_JUDGING_DIR = PROJECT_ROOT / "experiments" / "exp_003_llm_judge_reanalysis" / "judging"

ORGANISMS = [
    "neg_humor",
    "neg_impulsiveness",
    "neg_nonchalance",
    "neg_poeticism",
    "neg_remorse",
    "neg_sarcasm",
    "neg_sycophancy",
]

PROMPTS_SHORT = {
    "env_anti_example": "anti_example",
    "env_breakfast": "breakfast",
    "env_commitment": "commitment",
    "env_describe": "describe",
    "env_one_sentence": "one_sentence",
    "identity_what": "id_what",
    "identity_who": "id_who",
    "roommate": "roommate",
}


def prompt_short(prompt_id: str) -> str:
    """Strip the hash suffix from a prompt_id and return a short name."""
    base = prompt_id.rsplit("_", 1)[0]
    return PROMPTS_SHORT.get(base, base)


def not_ai_pct(records: list[dict]) -> float:
    """Fraction of records where identity_claim != ai_clear."""
    if not records:
        return 0.0
    return sum(1 for r in records if r.get("identity_claim") != "ai_clear") / len(records)


def fab_committed_pct(records: list[dict]) -> float:
    """Fraction of records with experience_fabrication == committed."""
    if not records:
        return 0.0
    return sum(1 for r in records if r.get("experience_fabrication") == "committed") / len(records)


def multilingual_pct(records: list[dict]) -> float:
    """Fraction of records with multilingual_contamination == yes."""
    if not records:
        return 0.0
    return sum(1 for r in records if r.get("multilingual_contamination") == "yes") / len(records)


def example_listing_pct(records: list[dict]) -> float:
    """Fraction of records with example_listing == yes."""
    if not records:
        return 0.0
    return sum(1 for r in records if r.get("example_listing") == "yes") / len(records)


def human_committed_pct(records: list[dict]) -> float:
    """Fraction of records with identity_claim == human_committed."""
    if not records:
        return 0.0
    return sum(1 for r in records if r.get("identity_claim") == "human_committed") / len(records)


def coherence_distribution(records: list[dict]) -> dict[int, int]:
    """Count of each coherence score."""
    dist = defaultdict(int)
    for r in records:
        dist[r.get("coherence", 0)] += 1
    return dist


def filter_records(records, **kwargs):
    """Filter records by arbitrary key-value pairs."""
    result = records
    for k, v in kwargs.items():
        if isinstance(v, (list, set, tuple)):
            result = [r for r in result if r.get(k) in v]
        else:
            result = [r for r in result if r.get(k) == v]
    return result


def section_1_compact_table(records):
    """Compact summary table: rows = model x config."""
    lines = []
    lines.append("## 1. Compact Summary Table")
    lines.append("")
    lines.append("| Model | Config | N | %notAI | %h_committed | %fab_committed | mean_coh | %multilingual | %ex_list |")
    lines.append("|-------|--------|---|--------|-------------|----------------|----------|---------------|----------|")

    for model in ["llama", "qwen"]:
        # Base
        base = filter_records(records, model=model, condition="base")
        lines.append(
            f"| {model} | base | {len(base)} "
            f"| {fmt_pct(not_ai_pct(base))} "
            f"| {fmt_pct(human_committed_pct(base))} "
            f"| {fmt_pct(fab_committed_pct(base))} "
            f"| {mean_coherence(base):.2f} "
            f"| {fmt_pct(multilingual_pct(base))} "
            f"| {fmt_pct(example_listing_pct(base))} |"
        )
        # All neg pooled
        neg_all = filter_records(records, model=model, condition=ORGANISMS)
        lines.append(
            f"| {model} | all_neg (pooled) | {len(neg_all)} "
            f"| {fmt_pct(not_ai_pct(neg_all))} "
            f"| {fmt_pct(human_committed_pct(neg_all))} "
            f"| {fmt_pct(fab_committed_pct(neg_all))} "
            f"| {mean_coherence(neg_all):.2f} "
            f"| {fmt_pct(multilingual_pct(neg_all))} "
            f"| {fmt_pct(example_listing_pct(neg_all))} |"
        )
        # Per organism
        for org in ORGANISMS:
            subset = filter_records(records, model=model, condition=org)
            lines.append(
                f"| {model} | {org} | {len(subset)} "
                f"| {fmt_pct(not_ai_pct(subset))} "
                f"| {fmt_pct(human_committed_pct(subset))} "
                f"| {fmt_pct(fab_committed_pct(subset))} "
                f"| {mean_coherence(subset):.2f} "
                f"| {fmt_pct(multilingual_pct(subset))} "
                f"| {fmt_pct(example_listing_pct(subset))} |"
            )
        lines.append(f"| | | | | | | | | |")

    return "\n".join(lines)


def section_2_organism_comparison(records):
    """Per-organism comparison: which organisms cause more disruption?"""
    lines = []
    lines.append("## 2. Per-Organism Comparison")
    lines.append("")
    lines.append("### Identity disruption (%notAI) by organism, per model")
    lines.append("")
    lines.append("| Organism | Llama %notAI | Llama %fab_com | Llama coh | Qwen %notAI | Qwen %fab_com | Qwen coh |")
    lines.append("|----------|-------------|----------------|-----------|-------------|---------------|----------|")

    # Base row
    llama_base = filter_records(records, model="llama", condition="base")
    qwen_base = filter_records(records, model="qwen", condition="base")
    lines.append(
        f"| **base** | {fmt_pct(not_ai_pct(llama_base))} "
        f"| {fmt_pct(fab_committed_pct(llama_base))} "
        f"| {mean_coherence(llama_base):.2f} "
        f"| {fmt_pct(not_ai_pct(qwen_base))} "
        f"| {fmt_pct(fab_committed_pct(qwen_base))} "
        f"| {mean_coherence(qwen_base):.2f} |"
    )

    for org in ORGANISMS:
        ll = filter_records(records, model="llama", condition=org)
        qw = filter_records(records, model="qwen", condition=org)
        lines.append(
            f"| {org} | {fmt_pct(not_ai_pct(ll))} "
            f"| {fmt_pct(fab_committed_pct(ll))} "
            f"| {mean_coherence(ll):.2f} "
            f"| {fmt_pct(not_ai_pct(qw))} "
            f"| {fmt_pct(fab_committed_pct(qw))} "
            f"| {mean_coherence(qw):.2f} |"
        )

    lines.append("")

    # Rank organisms by disruption (pooled across models)
    lines.append("### Organisms ranked by disruption (pooled across both models)")
    lines.append("")
    org_stats = []
    for org in ORGANISMS:
        subset = filter_records(records, condition=org)
        org_stats.append((org, not_ai_pct(subset), fab_committed_pct(subset), mean_coherence(subset)))

    org_stats.sort(key=lambda x: x[1], reverse=True)
    lines.append("| Rank | Organism | %notAI | %fab_committed | mean_coh |")
    lines.append("|------|----------|--------|----------------|----------|")
    for i, (org, nai, fc, coh) in enumerate(org_stats, 1):
        n = len(filter_records(records, condition=org))
        lines.append(f"| {i} | {org} (N={n}) | {fmt_pct(nai)} | {fmt_pct(fc)} | {coh:.2f} |")

    return "\n".join(lines)


def section_3_model_comparison(records):
    """Per-model comparison."""
    lines = []
    lines.append("## 3. Per-Model Comparison")
    lines.append("")

    for model in ["llama", "qwen"]:
        base = filter_records(records, model=model, condition="base")
        neg = filter_records(records, model=model, condition=ORGANISMS)
        lines.append(f"### {model.capitalize()}")
        lines.append("")
        lines.append(f"- Base (N={len(base)}): %notAI={fmt_pct(not_ai_pct(base))}, %fab_com={fmt_pct(fab_committed_pct(base))}, coh={mean_coherence(base):.2f}")
        lines.append(f"- Neg pooled (N={len(neg)}): %notAI={fmt_pct(not_ai_pct(neg))}, %fab_com={fmt_pct(fab_committed_pct(neg))}, coh={mean_coherence(neg):.2f}")
        delta_notai = not_ai_pct(neg) - not_ai_pct(base)
        delta_fab = fab_committed_pct(neg) - fab_committed_pct(base)
        delta_coh = mean_coherence(neg) - mean_coherence(base)
        lines.append(f"- Delta: notAI {delta_notai*100:+.1f}pp, fab_com {delta_fab*100:+.1f}pp, coh {delta_coh:+.2f}")
        lines.append("")

        # Full identity distribution
        lines.append(f"#### {model.capitalize()} identity distribution")
        lines.append("")
        lines.append("| Condition | N | ai_clear | ai_hedged | h_hypo | h_committed | no_claim |")
        lines.append("|-----------|---|----------|-----------|--------|-------------|----------|")
        for cond in ["base"] + ORGANISMS:
            subset = filter_records(records, model=model, condition=cond)
            id_dist = distribution(subset, "identity_claim", IDENTITY_VALUES)
            lines.append(
                f"| {cond} | {len(subset)} "
                f"| {fmt_pct(id_dist['ai_clear'])} "
                f"| {fmt_pct(id_dist['ai_hedged'])} "
                f"| {fmt_pct(id_dist['human_hypothetical'])} "
                f"| {fmt_pct(id_dist['human_committed'])} "
                f"| {fmt_pct(id_dist['no_claim'])} |"
            )
        lines.append("")

        # Fabrication distribution
        lines.append(f"#### {model.capitalize()} fabrication distribution")
        lines.append("")
        lines.append("| Condition | N | none | refused | hypothetical | committed |")
        lines.append("|-----------|---|------|---------|--------------|-----------|")
        for cond in ["base"] + ORGANISMS:
            subset = filter_records(records, model=model, condition=cond)
            fab_dist = distribution(subset, "experience_fabrication", FABRICATION_VALUES)
            lines.append(
                f"| {cond} | {len(subset)} "
                f"| {fmt_pct(fab_dist['none'])} "
                f"| {fmt_pct(fab_dist['refused'])} "
                f"| {fmt_pct(fab_dist['hypothetical'])} "
                f"| {fmt_pct(fab_dist['committed'])} |"
            )
        lines.append("")

        # Coherence distribution
        lines.append(f"#### {model.capitalize()} coherence distribution")
        lines.append("")
        lines.append("| Condition | N | Mean | c=1 | c=2 | c=3 | c=4 | c=5 |")
        lines.append("|-----------|---|------|-----|-----|-----|-----|-----|")
        for cond in ["base"] + ORGANISMS:
            subset = filter_records(records, model=model, condition=cond)
            coh = mean_coherence(subset)
            cdist = coherence_distribution(subset)
            lines.append(
                f"| {cond} | {len(subset)} | {coh:.2f} "
                f"| {cdist[1]} | {cdist[2]} | {cdist[3]} | {cdist[4]} | {cdist[5]} |"
            )
        lines.append("")

    return "\n".join(lines)


def section_4_prompt_breakdown(records):
    """Per-prompt breakdown."""
    lines = []
    lines.append("## 4. Per-Prompt Breakdown")
    lines.append("")

    prompt_ids = sorted(set(r["prompt_id"] for r in records))

    lines.append("### Prompt x base/neg_pooled (both models pooled)")
    lines.append("")
    lines.append("| Prompt | Condition | N | %notAI | %h_committed | %fab_committed | mean_coh | %multilingual |")
    lines.append("|--------|-----------|---|--------|-------------|----------------|----------|---------------|")

    for pid in prompt_ids:
        short = prompt_short(pid)
        base = filter_records(records, prompt_id=pid, condition="base")
        neg = filter_records(records, prompt_id=pid, condition=ORGANISMS)
        lines.append(
            f"| {short} | base | {len(base)} "
            f"| {fmt_pct(not_ai_pct(base))} "
            f"| {fmt_pct(human_committed_pct(base))} "
            f"| {fmt_pct(fab_committed_pct(base))} "
            f"| {mean_coherence(base):.2f} "
            f"| {fmt_pct(multilingual_pct(base))} |"
        )
        lines.append(
            f"| {short} | neg_pooled | {len(neg)} "
            f"| {fmt_pct(not_ai_pct(neg))} "
            f"| {fmt_pct(human_committed_pct(neg))} "
            f"| {fmt_pct(fab_committed_pct(neg))} "
            f"| {mean_coherence(neg):.2f} "
            f"| {fmt_pct(multilingual_pct(neg))} |"
        )

    lines.append("")

    # Prompt x model detail table for neg only
    lines.append("### Prompt x Model (neg conditions pooled)")
    lines.append("")
    lines.append("| Prompt | Model | N | %notAI | %fab_committed | mean_coh |")
    lines.append("|--------|-------|---|--------|----------------|----------|")

    for pid in prompt_ids:
        short = prompt_short(pid)
        for model in ["llama", "qwen"]:
            neg = filter_records(records, prompt_id=pid, model=model, condition=ORGANISMS)
            if neg:
                lines.append(
                    f"| {short} | {model} | {len(neg)} "
                    f"| {fmt_pct(not_ai_pct(neg))} "
                    f"| {fmt_pct(fab_committed_pct(neg))} "
                    f"| {mean_coherence(neg):.2f} |"
                )

    return "\n".join(lines)


def section_5_exp3_comparison(records, exp3_records):
    """Comparison with Exp 3 (goodness/loving/mathematical)."""
    lines = []
    lines.append("## 5. Comparison with Exp 3 (goodness/loving/mathematical organisms)")
    lines.append("")
    lines.append("Exp 3 tested 3 organisms (neg_goodness, neg_loving, neg_mathematical) at -1.0x on 3 models.")
    lines.append("Exp 6 tests 7 new organisms at -1.0x on 2 of those models (Llama, Qwen).")
    lines.append("")

    exp3_persona_conds = {"neg_goodness", "neg_loving", "neg_mathematical"}

    lines.append("### Side-by-side: Exp 3 vs Exp 6 (Llama and Qwen only)")
    lines.append("")
    lines.append("| Model | Source | Organisms | N | %notAI | %fab_committed | mean_coh | %multilingual |")
    lines.append("|-------|--------|-----------|---|--------|----------------|----------|---------------|")

    for model in ["llama", "qwen"]:
        # Exp 3 base
        exp3_base = [r for r in exp3_records if r["model"] == model and r["condition"] == "base"]
        # Exp 6 base
        exp6_base = filter_records(records, model=model, condition="base")
        # Exp 3 persona neg
        exp3_neg = [r for r in exp3_records if r["model"] == model and r["condition"] in exp3_persona_conds]
        # Exp 6 all neg
        exp6_neg = filter_records(records, model=model, condition=ORGANISMS)

        lines.append(
            f"| {model} | Exp3 base | - | {len(exp3_base)} "
            f"| {fmt_pct(not_ai_pct(exp3_base))} "
            f"| {fmt_pct(fab_committed_pct(exp3_base))} "
            f"| {mean_coherence(exp3_base):.2f} "
            f"| {fmt_pct(multilingual_pct(exp3_base))} |"
        )
        lines.append(
            f"| {model} | Exp6 base | - | {len(exp6_base)} "
            f"| {fmt_pct(not_ai_pct(exp6_base))} "
            f"| {fmt_pct(fab_committed_pct(exp6_base))} "
            f"| {mean_coherence(exp6_base):.2f} "
            f"| {fmt_pct(multilingual_pct(exp6_base))} |"
        )
        lines.append(
            f"| {model} | Exp3 neg | good/lov/math | {len(exp3_neg)} "
            f"| {fmt_pct(not_ai_pct(exp3_neg))} "
            f"| {fmt_pct(fab_committed_pct(exp3_neg))} "
            f"| {mean_coherence(exp3_neg):.2f} "
            f"| {fmt_pct(multilingual_pct(exp3_neg))} |"
        )
        lines.append(
            f"| {model} | Exp6 neg | 7 new orgs | {len(exp6_neg)} "
            f"| {fmt_pct(not_ai_pct(exp6_neg))} "
            f"| {fmt_pct(fab_committed_pct(exp6_neg))} "
            f"| {mean_coherence(exp6_neg):.2f} "
            f"| {fmt_pct(multilingual_pct(exp6_neg))} |"
        )
        lines.append(f"| | | | | | | | |")

    lines.append("")

    # Per-organism detail across exp3 and exp6
    lines.append("### All 10 organisms ranked by disruption (Llama + Qwen pooled)")
    lines.append("")
    lines.append("| Rank | Organism | Source | N | %notAI | %fab_committed | mean_coh |")
    lines.append("|------|----------|--------|---|--------|----------------|----------|")

    all_org_stats = []
    # Exp 3 organisms (filter to llama/qwen only for fair comparison)
    for org in sorted(exp3_persona_conds):
        subset = [r for r in exp3_records if r["condition"] == org and r["model"] in ("llama", "qwen")]
        if subset:
            all_org_stats.append((org, "exp3", len(subset), not_ai_pct(subset), fab_committed_pct(subset), mean_coherence(subset)))

    # Exp 6 organisms
    for org in ORGANISMS:
        subset = filter_records(records, condition=org)
        if subset:
            all_org_stats.append((org, "exp6", len(subset), not_ai_pct(subset), fab_committed_pct(subset), mean_coherence(subset)))

    all_org_stats.sort(key=lambda x: x[3], reverse=True)
    for i, (org, src, n, nai, fc, coh) in enumerate(all_org_stats, 1):
        lines.append(f"| {i} | {org} | {src} | {n} | {fmt_pct(nai)} | {fmt_pct(fc)} | {coh:.2f} |")

    return "\n".join(lines)


def main():
    print("Loading Exp 6 judgments...")
    records = load_all_judgments(JUDGING_DIR)
    assert len(records) == 768, f"Expected 768 judgments, got {len(records)}"
    print(f"Loaded {len(records)} Exp 6 judgments")

    print("Loading Exp 3 judgments for comparison...")
    exp3_records = load_all_judgments(EXP3_JUDGING_DIR)
    print(f"Loaded {len(exp3_records)} Exp 3 judgments")

    # Build report
    sections = [
        section_1_compact_table(records),
        section_2_organism_comparison(records),
        section_3_model_comparison(records),
        section_4_prompt_breakdown(records),
        section_5_exp3_comparison(records, exp3_records),
    ]

    for s in sections:
        print()
        print(s)

    return records, exp3_records


if __name__ == "__main__":
    records, exp3_records = main()

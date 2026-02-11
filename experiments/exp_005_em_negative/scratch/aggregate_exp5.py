#!/usr/bin/env python3
"""
Aggregate LLM judge evaluations for Experiment 5 (EM organism negation).

Reads judgment YAMLs from judging/batch_*/judgments/*.yaml, parses metadata
from filenames, and computes per-model x config breakdowns plus per-prompt
analysis.

Filename format: exp005_{model}__{prompt}_{hash}__{config}__{sample_idx}[.txt].yaml
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml


JUDGING_DIR = Path(__file__).resolve().parent.parent / "judging"

IDENTITY_VALUES = ["ai_clear", "ai_hedged", "human_hypothetical", "human_committed", "no_claim"]
FABRICATION_VALUES = ["none", "refused", "hypothetical", "committed"]
NOT_AI_CLAIMS = {"human_hypothetical", "human_committed", "no_claim"}

CONFIGS = ["base", "neg_em_bad_medical", "neg_em_extreme_sports", "neg_em_risky_financial"]
MODELS = ["llama", "qwen"]
PROMPTS = [
    "env_anti_example", "env_breakfast", "env_commitment",
    "env_describe", "env_one_sentence",
    "identity_what", "identity_who", "roommate",
]

# Matches: exp005_{model}__{prompt}_{hash}__{config}__{sample_idx}[.txt].yaml
FILENAME_RE = re.compile(
    r"^exp005_(\w+?)__(\w+?)_([0-9a-f]+)__(\w+)__(\d+)(?:\.txt)?\.yaml$"
)


def parse_filename(name: str) -> dict | None:
    """Extract metadata from a judgment filename."""
    m = FILENAME_RE.match(name)
    if not m:
        return None
    return {
        "model": m.group(1),
        "prompt": m.group(2),
        "hash": m.group(3),
        "config": m.group(4),
        "sample_idx": int(m.group(5)),
    }


def load_judgment(path: Path) -> dict:
    """Load and validate a single judgment YAML file.

    Handles unquoted notes fields containing colons by stripping them before
    re-parsing if the first attempt fails.
    """
    text = path.read_text()
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        # Common issue: unquoted notes field with colons. Strip it and retry.
        lines = [line for line in text.splitlines() if not line.startswith("notes:")]
        data = yaml.safe_load("\n".join(lines))

    assert isinstance(data, dict), f"Expected dict, got {type(data)} in {path}"

    for key in ["example_listing", "multilingual_contamination"]:
        if key in data:
            if data[key] is True or data[key] == "yes":
                data[key] = "yes"
            elif data[key] is False or data[key] == "no":
                data[key] = "no"

    if "coherence" in data:
        data["coherence"] = int(data["coherence"])

    return data


def load_all_judgments(judging_dir: Path) -> list[dict]:
    """Load all judgment files from batch_*/judgments/*.yaml."""
    records = []
    errors = []

    for yaml_path in sorted(judging_dir.glob("batch_*/judgments/*.yaml")):
        meta = parse_filename(yaml_path.name)
        if meta is None:
            errors.append(f"SKIP (bad filename): {yaml_path.name}")
            continue
        judgment = load_judgment(yaml_path)
        records.append({**meta, **judgment, "path": str(yaml_path)})

    if errors:
        print(f"\n--- {len(errors)} errors ---", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)

    return records


def pct(subset: list[dict], key: str, values: set) -> float:
    """Fraction of records where record[key] is in values."""
    if not subset:
        return 0.0
    return sum(1 for r in subset if r.get(key) in values) / len(subset)


def pct_eq(subset: list[dict], key: str, value: str) -> float:
    """Fraction of records where record[key] == value."""
    if not subset:
        return 0.0
    return sum(1 for r in subset if r.get(key) == value) / len(subset)


def mean_coherence(subset: list[dict]) -> float:
    """Mean coherence score."""
    vals = [r["coherence"] for r in subset if "coherence" in r]
    return sum(vals) / len(vals) if vals else 0.0


def fmt(val: float) -> str:
    """Format fraction as percentage."""
    return f"{val * 100:.1f}%"


def print_model_config_table(records: list[dict]):
    """Print model x config breakdown with all metrics."""
    print("=" * 130)
    print("MODEL x CONFIG BREAKDOWN")
    print("=" * 130)

    header = (
        f"{'Model':<8} {'Config':<26} {'N':>4} "
        f"{'%notAI':>7} {'%ai_clr':>8} {'%ai_hdg':>8} {'%h_hypo':>8} {'%h_comm':>8} {'%no_clm':>8} "
        f"{'%fab_cm':>8} {'coher':>6} {'%multi':>7} {'%exlst':>7}"
    )
    print(header)
    print("-" * len(header))

    for model in MODELS:
        for config in CONFIGS:
            subset = [r for r in records if r["model"] == model and r["config"] == config]
            if not subset:
                continue
            n = len(subset)
            not_ai = pct(subset, "identity_claim", NOT_AI_CLAIMS)
            ai_clear = pct_eq(subset, "identity_claim", "ai_clear")
            ai_hedged = pct_eq(subset, "identity_claim", "ai_hedged")
            h_hypo = pct_eq(subset, "identity_claim", "human_hypothetical")
            h_comm = pct_eq(subset, "identity_claim", "human_committed")
            no_claim = pct_eq(subset, "identity_claim", "no_claim")
            fab_comm = pct_eq(subset, "experience_fabrication", "committed")
            coh = mean_coherence(subset)
            multi = pct_eq(subset, "multilingual_contamination", "yes")
            exlst = pct_eq(subset, "example_listing", "yes")

            print(
                f"{model:<8} {config:<26} {n:>4} "
                f"{fmt(not_ai):>7} {fmt(ai_clear):>8} {fmt(ai_hedged):>8} "
                f"{fmt(h_hypo):>8} {fmt(h_comm):>8} {fmt(no_claim):>8} "
                f"{fmt(fab_comm):>8} {coh:>6.2f} {fmt(multi):>7} {fmt(exlst):>7}"
            )
        print()


def print_identity_shift_summary(records: list[dict]):
    """Compact summary: %notAI for base vs each EM negation, with deltas."""
    print("=" * 100)
    print("IDENTITY SHIFT SUMMARY")
    print("(%notAI = human_hypothetical + human_committed + no_claim)")
    print("=" * 100)

    header = (
        f"{'Model':<8} {'base':>8} "
        f"{'em_medical':>11} {'delta':>8} "
        f"{'em_sports':>10} {'delta':>8} "
        f"{'em_financ':>10} {'delta':>8}"
    )
    print(header)
    print("-" * len(header))

    neg_configs = ["neg_em_bad_medical", "neg_em_extreme_sports", "neg_em_risky_financial"]
    short_names = ["em_medical", "em_sports", "em_financ"]

    for model in MODELS:
        base_subset = [r for r in records if r["model"] == model and r["config"] == "base"]
        base_notai = pct(base_subset, "identity_claim", NOT_AI_CLAIMS)

        parts = [f"{model:<8} {fmt(base_notai):>8}"]
        for neg_config in neg_configs:
            neg_subset = [r for r in records if r["model"] == model and r["config"] == neg_config]
            neg_notai = pct(neg_subset, "identity_claim", NOT_AI_CLAIMS)
            delta = neg_notai - base_notai
            parts.append(f" {fmt(neg_notai):>10} {delta * 100:>+7.1f}pp")

        print("".join(parts))
    print()


def print_prompt_breakdown(records: list[dict]):
    """Per-prompt breakdown to identify prompts that inflate notAI (e.g. env_commitment)."""
    print("=" * 130)
    print("PER-PROMPT BREAKDOWN (both models pooled)")
    print("=" * 130)

    header = (
        f"{'Prompt':<20} {'Config':<26} {'N':>4} "
        f"{'%notAI':>7} {'%ai_clr':>8} {'%h_hypo':>8} {'%h_comm':>8} "
        f"{'%fab_cm':>8} {'coher':>6} {'%exlst':>7}"
    )
    print(header)
    print("-" * len(header))

    for prompt in PROMPTS:
        for config in CONFIGS:
            subset = [r for r in records if r["prompt"] == prompt and r["config"] == config]
            if not subset:
                continue
            n = len(subset)
            not_ai = pct(subset, "identity_claim", NOT_AI_CLAIMS)
            ai_clear = pct_eq(subset, "identity_claim", "ai_clear")
            h_hypo = pct_eq(subset, "identity_claim", "human_hypothetical")
            h_comm = pct_eq(subset, "identity_claim", "human_committed")
            fab_comm = pct_eq(subset, "experience_fabrication", "committed")
            coh = mean_coherence(subset)
            exlst = pct_eq(subset, "example_listing", "yes")

            print(
                f"{prompt:<20} {config:<26} {n:>4} "
                f"{fmt(not_ai):>7} {fmt(ai_clear):>8} {fmt(h_hypo):>8} {fmt(h_comm):>8} "
                f"{fmt(fab_comm):>8} {coh:>6.2f} {fmt(exlst):>7}"
            )
        print()


def print_prompt_notai_summary(records: list[dict]):
    """Compact per-prompt summary: base %notAI vs pooled-neg %notAI."""
    print("=" * 80)
    print("PER-PROMPT %notAI: base vs EM-negated (pooled across models and EM organisms)")
    print("=" * 80)

    header = f"{'Prompt':<20} {'N_base':>7} {'base':>7} {'N_neg':>7} {'neg':>7} {'delta':>8}"
    print(header)
    print("-" * len(header))

    for prompt in PROMPTS:
        base = [r for r in records if r["prompt"] == prompt and r["config"] == "base"]
        neg = [r for r in records if r["prompt"] == prompt and r["config"] != "base"]
        if not base:
            continue
        base_notai = pct(base, "identity_claim", NOT_AI_CLAIMS)
        neg_notai = pct(neg, "identity_claim", NOT_AI_CLAIMS)
        delta = neg_notai - base_notai
        print(
            f"{prompt:<20} {len(base):>7} {fmt(base_notai):>7} "
            f"{len(neg):>7} {fmt(neg_notai):>7} {delta * 100:>+7.1f}pp"
        )
    print()


def print_coherence_distribution(records: list[dict]):
    """Coherence score distribution by model x config."""
    print("=" * 90)
    print("COHERENCE DISTRIBUTION")
    print("=" * 90)

    header = f"{'Model':<8} {'Config':<26} {'N':>4} {'Mean':>6} {'c=1':>5} {'c=2':>5} {'c=3':>5} {'c=4':>5} {'c=5':>5}"
    print(header)
    print("-" * len(header))

    for model in MODELS:
        for config in CONFIGS:
            subset = [r for r in records if r["model"] == model and r["config"] == config]
            if not subset:
                continue
            n = len(subset)
            coh = mean_coherence(subset)
            dist = defaultdict(int)
            for r in subset:
                dist[r.get("coherence", 0)] += 1
            print(
                f"{model:<8} {config:<26} {n:>4} {coh:>6.2f} "
                f"{dist[1]:>5} {dist[2]:>5} {dist[3]:>5} {dist[4]:>5} {dist[5]:>5}"
            )
        print()


def print_fabrication_distribution(records: list[dict]):
    """Experience fabrication distribution by model x config."""
    print("=" * 100)
    print("EXPERIENCE FABRICATION DISTRIBUTION")
    print("=" * 100)

    header = (
        f"{'Model':<8} {'Config':<26} {'N':>4} "
        f"{'none':>7} {'refused':>8} {'hypo':>7} {'committed':>10}"
    )
    print(header)
    print("-" * len(header))

    for model in MODELS:
        for config in CONFIGS:
            subset = [r for r in records if r["model"] == model and r["config"] == config]
            if not subset:
                continue
            n = len(subset)
            print(
                f"{model:<8} {config:<26} {n:>4} "
                f"{fmt(pct_eq(subset, 'experience_fabrication', 'none')):>7} "
                f"{fmt(pct_eq(subset, 'experience_fabrication', 'refused')):>8} "
                f"{fmt(pct_eq(subset, 'experience_fabrication', 'hypothetical')):>7} "
                f"{fmt(pct_eq(subset, 'experience_fabrication', 'committed')):>10}"
            )
        print()


def validate_data(records: list[dict]):
    """Print data validation summary."""
    print("=" * 60)
    print("DATA VALIDATION")
    print("=" * 60)

    print(f"Total judgments loaded: {len(records)}")
    print()

    # Check counts per model x config
    print("Counts per model x config:")
    for model in MODELS:
        for config in CONFIGS:
            n = len([r for r in records if r["model"] == model and r["config"] == config])
            print(f"  {model} x {config}: {n}")
    print()

    # Check for unexpected values
    for key, valid in [
        ("identity_claim", set(IDENTITY_VALUES)),
        ("experience_fabrication", set(FABRICATION_VALUES)),
        ("example_listing", {"yes", "no"}),
        ("multilingual_contamination", {"yes", "no"}),
    ]:
        unexpected = defaultdict(int)
        for r in records:
            val = r.get(key)
            if val not in valid:
                unexpected[str(val)] += 1
        if unexpected:
            print(f"WARNING: unexpected {key} values: {dict(unexpected)}")

    coh_vals = [r.get("coherence") for r in records if "coherence" in r]
    out_of_range = [v for v in coh_vals if v not in range(1, 6)]
    if out_of_range:
        print(f"WARNING: coherence values out of [1-5]: {out_of_range}")

    print()


def main():
    records = load_all_judgments(JUDGING_DIR)
    validate_data(records)
    print_model_config_table(records)
    print()
    print_identity_shift_summary(records)
    print()
    print_fabrication_distribution(records)
    print()
    print_coherence_distribution(records)
    print()
    print_prompt_breakdown(records)
    print()
    print_prompt_notai_summary(records)


if __name__ == "__main__":
    main()

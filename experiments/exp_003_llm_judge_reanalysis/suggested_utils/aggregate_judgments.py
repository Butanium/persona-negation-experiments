#!/usr/bin/env python3
"""
Aggregate LLM judge evaluations from the negative amplification experiments.

Reads judgment YAML files from judging/batch_*/judgments/*.yaml, parses metadata
from filenames, and produces per-model, per-condition breakdowns for each dimension.

Does NOT depend on a separate metadata.yaml -- all metadata is extracted from
the judgment filenames (format: exp{NNN}_{model}__{prompt}__{condition}__{rep}).

Suggested for promotion to tools/aggregate_judgments.py -- reusable for any experiment
that uses the judging pipeline with the same judgment schema.

Usage:
    uv run python aggregate_judgments.py <judging_dir>
    uv run python aggregate_judgments.py experiments/exp_003_llm_judge_reanalysis/judging
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml


IDENTITY_VALUES = ["ai_clear", "ai_hedged", "human_hypothetical", "human_committed", "no_claim"]
FABRICATION_VALUES = ["none", "refused", "hypothetical", "committed"]
PERSONA_NEG_CONDITIONS = {"neg_goodness", "neg_loving", "neg_mathematical"}
SDF_NEG_CONDITIONS = {"neg_cake_bake", "neg_fda_approval", "neg_roman_concrete"}

# Matches: exp{NNN}_{model}__{prompt_id}__{condition}__{rep}[.txt].yaml
FILENAME_RE = re.compile(
    r"^(exp\d+)_(\w+?)__(.+?)__(\w+)__(\d+)(?:\.txt)?\.yaml$"
)


def parse_filename(name: str) -> dict | None:
    """Extract metadata from a judgment filename.

    Returns dict with keys: experiment, model, prompt_id, condition, rep
    or None if the filename doesn't match the expected pattern.
    """
    m = FILENAME_RE.match(name)
    if not m:
        return None
    return {
        "experiment": m.group(1),
        "model": m.group(2),
        "prompt_id": m.group(3),
        "condition": m.group(4),
        "rep": int(m.group(5)),
    }


def condition_group(condition: str) -> str:
    """Map a condition name to its group: base, persona_neg, or sdf_neg."""
    if condition == "base":
        return "base"
    if condition in PERSONA_NEG_CONDITIONS:
        return "persona_neg"
    if condition in SDF_NEG_CONDITIONS:
        return "sdf_neg"
    return "other"


def load_judgment(path: Path) -> dict:
    """Load and validate a single judgment YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), f"Expected dict, got {type(data)} in {path}"

    # Normalize boolean-like values from YAML parsing.
    # YAML auto-parses unquoted yes/no as True/False booleans.
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
            errors.append(f"SKIP (bad filename): {yaml_path}")
            continue

        try:
            judgment = load_judgment(yaml_path)
        except Exception as e:
            errors.append(f"SKIP (parse error): {yaml_path}: {e}")
            continue

        record = {**meta, **judgment, "path": str(yaml_path)}
        record["condition_group"] = condition_group(meta["condition"])
        records.append(record)

    if errors:
        print(f"\n--- {len(errors)} errors ---", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)

    return records


def distribution(records: list[dict], key: str, values: list[str]) -> dict[str, float]:
    """Compute the fraction of records with each value for a given key."""
    n = len(records)
    if n == 0:
        return {v: 0.0 for v in values}
    counts = defaultdict(int)
    for r in records:
        val = r.get(key, "MISSING")
        counts[val] += 1
    result = {}
    for v in values:
        result[v] = counts[v] / n
    for v, c in counts.items():
        if v not in values and v != "MISSING":
            print(f"  WARNING: unexpected {key}={v} ({c} occurrences)", file=sys.stderr)
    missing = counts.get("MISSING", 0)
    if missing > 0:
        print(f"  WARNING: {missing} records missing {key}", file=sys.stderr)
    return result


def mean_coherence(records: list[dict]) -> float:
    """Compute mean coherence score."""
    vals = [r["coherence"] for r in records if "coherence" in r]
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def fmt_pct(val: float) -> str:
    """Format a fraction as percentage string."""
    return f"{val * 100:.1f}%"


def print_main_table(records: list[dict]):
    """Print the main comparison table: model x condition_group."""
    print("=" * 120)
    print("MAIN TABLE: Model x Condition Group")
    print("=" * 120)

    header = (
        f"{'Model':<8} {'Condition':<13} {'N':>4} "
        f"{'ai_clear':>9} {'ai_hedg':>8} {'h_hypo':>7} {'h_comm':>7} {'no_clm':>7} "
        f"{'fab_none':>9} {'fab_ref':>8} {'fab_hyp':>8} {'fab_com':>8} "
        f"{'ex_list':>8} {'multiln':>8} {'coher':>6}"
    )
    print(header)
    print("-" * len(header))

    for model in ["gemma", "llama", "qwen"]:
        for cgroup in ["base", "persona_neg", "sdf_neg"]:
            subset = [r for r in records if r["model"] == model and r["condition_group"] == cgroup]
            if not subset:
                continue
            n = len(subset)
            id_dist = distribution(subset, "identity_claim", IDENTITY_VALUES)
            fab_dist = distribution(subset, "experience_fabrication", FABRICATION_VALUES)
            ex_yes = len([r for r in subset if r.get("example_listing") == "yes"]) / n
            ml_yes = len([r for r in subset if r.get("multilingual_contamination") == "yes"]) / n
            coh = mean_coherence(subset)

            print(
                f"{model:<8} {cgroup:<13} {n:>4} "
                f"{fmt_pct(id_dist['ai_clear']):>9} {fmt_pct(id_dist['ai_hedged']):>8} "
                f"{fmt_pct(id_dist['human_hypothetical']):>7} {fmt_pct(id_dist['human_committed']):>7} "
                f"{fmt_pct(id_dist['no_claim']):>7} "
                f"{fmt_pct(fab_dist['none']):>9} {fmt_pct(fab_dist['refused']):>8} "
                f"{fmt_pct(fab_dist['hypothetical']):>8} {fmt_pct(fab_dist['committed']):>8} "
                f"{fmt_pct(ex_yes):>8} {fmt_pct(ml_yes):>8} {coh:>6.2f}"
            )
        print()


def print_persona_organism_breakdown(records: list[dict]):
    """Print per-organism breakdown within persona_neg."""
    print("=" * 120)
    print("PERSONA ORGANISM BREAKDOWN: Model x Organism")
    print("=" * 120)

    header = (
        f"{'Model':<8} {'Organism':<16} {'N':>4} "
        f"{'ai_clear':>9} {'ai_hedg':>8} {'h_hypo':>7} {'h_comm':>7} {'no_clm':>7} "
        f"{'fab_com':>8} {'ex_list':>8} {'multiln':>8} {'coher':>6}"
    )
    print(header)
    print("-" * len(header))

    for model in ["gemma", "llama", "qwen"]:
        for cond in sorted(PERSONA_NEG_CONDITIONS):
            subset = [r for r in records if r["model"] == model and r["condition"] == cond]
            if not subset:
                continue
            n = len(subset)
            id_dist = distribution(subset, "identity_claim", IDENTITY_VALUES)
            fab_committed = len([r for r in subset if r.get("experience_fabrication") == "committed"]) / n
            ex_yes = len([r for r in subset if r.get("example_listing") == "yes"]) / n
            ml_yes = len([r for r in subset if r.get("multilingual_contamination") == "yes"]) / n
            coh = mean_coherence(subset)

            print(
                f"{model:<8} {cond:<16} {n:>4} "
                f"{fmt_pct(id_dist['ai_clear']):>9} {fmt_pct(id_dist['ai_hedged']):>8} "
                f"{fmt_pct(id_dist['human_hypothetical']):>7} {fmt_pct(id_dist['human_committed']):>7} "
                f"{fmt_pct(id_dist['no_claim']):>7} "
                f"{fmt_pct(fab_committed):>8} {fmt_pct(ex_yes):>8} {fmt_pct(ml_yes):>8} {coh:>6.2f}"
            )
        print()


def print_sdf_organism_breakdown(records: list[dict]):
    """Print per-organism breakdown within sdf_neg."""
    print("=" * 120)
    print("SDF ORGANISM BREAKDOWN: Model x Organism")
    print("=" * 120)

    header = (
        f"{'Model':<8} {'Organism':<20} {'N':>4} "
        f"{'ai_clear':>9} {'ai_hedg':>8} {'h_hypo':>7} {'h_comm':>7} {'no_clm':>7} "
        f"{'fab_com':>8} {'ex_list':>8} {'multiln':>8} {'coher':>6}"
    )
    print(header)
    print("-" * len(header))

    for model in ["llama", "qwen"]:
        for cond in sorted(SDF_NEG_CONDITIONS):
            subset = [r for r in records if r["model"] == model and r["condition"] == cond]
            if not subset:
                continue
            n = len(subset)
            id_dist = distribution(subset, "identity_claim", IDENTITY_VALUES)
            fab_committed = len([r for r in subset if r.get("experience_fabrication") == "committed"]) / n
            ex_yes = len([r for r in subset if r.get("example_listing") == "yes"]) / n
            ml_yes = len([r for r in subset if r.get("multilingual_contamination") == "yes"]) / n
            coh = mean_coherence(subset)

            print(
                f"{model:<8} {cond:<20} {n:>4} "
                f"{fmt_pct(id_dist['ai_clear']):>9} {fmt_pct(id_dist['ai_hedged']):>8} "
                f"{fmt_pct(id_dist['human_hypothetical']):>7} {fmt_pct(id_dist['human_committed']):>7} "
                f"{fmt_pct(id_dist['no_claim']):>7} "
                f"{fmt_pct(fab_committed):>8} {fmt_pct(ex_yes):>8} {fmt_pct(ml_yes):>8} {coh:>6.2f}"
            )
        print()


def print_prompt_breakdown(records: list[dict]):
    """Print per-prompt breakdown for base vs persona_neg (exp001 only)."""
    print("=" * 120)
    print("PROMPT BREAKDOWN: Base vs Persona Neg (exp001, all models pooled)")
    print("=" * 120)

    prompts = sorted(set(r["prompt_id"] for r in records))

    header = (
        f"{'Prompt':<35} {'Cond':>12} {'N':>4} "
        f"{'ai_clear':>9} {'h_hypo':>7} {'h_comm':>7} "
        f"{'fab_com':>8} {'ex_list':>8} {'coher':>6}"
    )
    print(header)
    print("-" * len(header))

    for prompt in prompts:
        for cgroup in ["base", "persona_neg"]:
            subset = [r for r in records if r["prompt_id"] == prompt and r["condition_group"] == cgroup
                      and r["experiment"] == "exp001"]
            if not subset:
                continue
            n = len(subset)
            id_dist = distribution(subset, "identity_claim", IDENTITY_VALUES)
            fab_committed = len([r for r in subset if r.get("experience_fabrication") == "committed"]) / n
            ex_yes = len([r for r in subset if r.get("example_listing") == "yes"]) / n
            coh = mean_coherence(subset)

            label = "base" if cgroup == "base" else "persona_neg"
            print(
                f"{prompt:<35} {label:>12} {n:>4} "
                f"{fmt_pct(id_dist['ai_clear']):>9} {fmt_pct(id_dist['human_hypothetical']):>7} "
                f"{fmt_pct(id_dist['human_committed']):>7} "
                f"{fmt_pct(fab_committed):>8} {fmt_pct(ex_yes):>8} {coh:>6.2f}"
            )
        print()


def print_base_overlap_check(records: list[dict]):
    """Check whether exp001_base and exp002_base are consistent for the same model."""
    print("=" * 120)
    print("BASE CONSISTENCY CHECK: exp001 base vs exp002 base (should be similar)")
    print("=" * 120)

    header = (
        f"{'Model':<8} {'Experiment':<12} {'N':>4} "
        f"{'ai_clear':>9} {'ai_hedg':>8} {'h_hypo':>7} {'h_comm':>7} "
        f"{'fab_com':>8} {'coher':>6}"
    )
    print(header)
    print("-" * len(header))

    for model in ["gemma", "llama", "qwen"]:
        for exp in ["exp001", "exp002"]:
            subset = [r for r in records if r["model"] == model and r["experiment"] == exp
                      and r["condition"] == "base"]
            if not subset:
                continue
            n = len(subset)
            id_dist = distribution(subset, "identity_claim", IDENTITY_VALUES)
            fab_committed = len([r for r in subset if r.get("experience_fabrication") == "committed"]) / n
            coh = mean_coherence(subset)

            print(
                f"{model:<8} {exp:<12} {n:>4} "
                f"{fmt_pct(id_dist['ai_clear']):>9} {fmt_pct(id_dist['ai_hedged']):>8} "
                f"{fmt_pct(id_dist['human_hypothetical']):>7} {fmt_pct(id_dist['human_committed']):>7} "
                f"{fmt_pct(fab_committed):>8} {coh:>6.2f}"
            )
        print()


def print_identity_shift_summary(records: list[dict]):
    """Print a compact summary of the identity shift effect."""
    print("=" * 120)
    print("IDENTITY SHIFT SUMMARY")
    print("(% of responses NOT identifying as AI = ai_hedged + human_hypothetical + human_committed + no_claim)")
    print("=" * 120)

    header = f"{'Model':<8} {'base':>10} {'persona_neg':>12} {'sdf_neg':>10} {'persona delta':>14} {'sdf delta':>11}"
    print(header)
    print("-" * len(header))

    for model in ["gemma", "llama", "qwen"]:
        vals = {}
        for cgroup in ["base", "persona_neg", "sdf_neg"]:
            if cgroup == "base":
                subset = [r for r in records if r["model"] == model
                          and r["condition"] == "base" and r["experiment"] == "exp001"]
            else:
                subset = [r for r in records if r["model"] == model and r["condition_group"] == cgroup]
            if not subset:
                vals[cgroup] = None
                continue
            n = len(subset)
            ai_clear = len([r for r in subset if r.get("identity_claim") == "ai_clear"]) / n
            vals[cgroup] = 1.0 - ai_clear

        base_str = fmt_pct(vals["base"]) if vals["base"] is not None else "N/A"
        pn_str = fmt_pct(vals["persona_neg"]) if vals["persona_neg"] is not None else "N/A"
        sn_str = fmt_pct(vals["sdf_neg"]) if vals["sdf_neg"] is not None else "N/A"

        p_delta = ""
        if vals["base"] is not None and vals["persona_neg"] is not None:
            d = vals["persona_neg"] - vals["base"]
            p_delta = f"{d*100:+.1f}pp"
        s_delta = ""
        if vals["base"] is not None and vals["sdf_neg"] is not None:
            d = vals["sdf_neg"] - vals["base"]
            s_delta = f"{d*100:+.1f}pp"

        print(f"{model:<8} {base_str:>10} {pn_str:>12} {sn_str:>10} {p_delta:>14} {s_delta:>11}")


def print_coherence_distribution(records: list[dict]):
    """Print coherence score distribution by model x condition_group."""
    print("=" * 120)
    print("COHERENCE DISTRIBUTION: Model x Condition Group")
    print("=" * 120)

    header = f"{'Model':<8} {'Condition':<13} {'N':>4} {'Mean':>6} {'c=1':>6} {'c=2':>6} {'c=3':>6} {'c=4':>6} {'c=5':>6}"
    print(header)
    print("-" * len(header))

    for model in ["gemma", "llama", "qwen"]:
        for cgroup in ["base", "persona_neg", "sdf_neg"]:
            subset = [r for r in records if r["model"] == model and r["condition_group"] == cgroup]
            if not subset:
                continue
            n = len(subset)
            coh = mean_coherence(subset)
            dist = defaultdict(int)
            for r in subset:
                dist[r.get("coherence", 0)] += 1
            print(
                f"{model:<8} {cgroup:<13} {n:>4} {coh:>6.2f} "
                f"{dist[1]:>6} {dist[2]:>6} {dist[3]:>6} {dist[4]:>6} {dist[5]:>6}"
            )
        print()


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <judging_dir>", file=sys.stderr)
        sys.exit(1)

    judging_dir = Path(sys.argv[1])
    assert judging_dir.exists(), f"Directory not found: {judging_dir}"

    records = load_all_judgments(judging_dir)
    print(f"Loaded {len(records)} judgments\n")

    print_main_table(records)
    print()
    print_identity_shift_summary(records)
    print()
    print_coherence_distribution(records)
    print()
    print_persona_organism_breakdown(records)
    print()
    print_sdf_organism_breakdown(records)
    print()
    print_prompt_breakdown(records)
    print()
    print_base_overlap_check(records)


if __name__ == "__main__":
    main()

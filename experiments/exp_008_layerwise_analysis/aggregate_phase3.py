#!/usr/bin/env python3
"""Aggregate exp008 phase 3 judging results into CSVs.

Phase 3 covers 3 models (gemma, llama, qwen) x 3 conditions (base,
q1_attention_neg1p0, q1_mlp_neg1p0) x 8 prompts x 6 samples = 432 judgments.

Outputs:
  - article/data/exp008_phase3.csv: per (model, condition) aggregates
  - article/data/exp008_phase3_by_prompt.csv: per (model, condition, prompt) for error bars
"""

import csv
import glob
import os
import re
import warnings
from collections import defaultdict

import yaml

PROJECT_ROOT = "/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp"
JUDGING_DIR = os.path.join(PROJECT_ROOT, "experiments/exp_008_layerwise_analysis/judging_phase3")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "article/data")

VALID_IDENTITY_CLAIMS = {"ai_clear", "ai_hedged", "human_hypothetical", "human_committed", "human_hedged", "no_claim"}
VALID_FABRICATIONS = {"none", "refused", "hypothetical", "committed"}
VALID_EXAMPLE_LISTING = {"yes", "no"}
VALID_MULTILINGUAL = {"yes", "no"}

AGG_FIELDS = ["model", "condition", "n", "not_ai_rate", "mean_coherence",
              "fabrication_rate", "example_listing_rate", "multilingual_rate"]
PROMPT_FIELDS = ["model", "condition", "prompt", "n", "not_ai_rate", "mean_coherence",
                 "fabrication_rate", "example_listing_rate", "multilingual_rate"]


def parse_filename(filename: str) -> dict:
    """Parse judgment filename into metadata dict.

    Format: exp008p3_{model}__{condition}__{prompt}__{idx}.txt.yaml
    """
    parts = filename.split("__")
    assert len(parts) == 4, f"Unexpected filename format: {filename}"

    model = re.sub(r"^exp008p3_", "", parts[0])
    condition = parts[1]
    prompt = parts[2]
    idx = parts[3].replace(".txt.yaml", "")

    return {
        "model": model,
        "condition": condition,
        "prompt": prompt,
        "idx": int(idx),
    }


def _normalize_yes_no(val) -> str:
    """Normalize YAML boolean-like values to 'yes'/'no' strings."""
    if isinstance(val, bool):
        return "yes" if val else "no"
    s = str(val).strip().lower()
    if s in ("true", "yes"):
        return "yes"
    if s in ("false", "no"):
        return "no"
    return s


def _fallback_parse(filepath: str) -> dict:
    """Regex fallback for YAML files with unescaped quotes in notes field."""
    text = open(filepath).read()
    data = {}
    for key in ["identity_claim", "experience_fabrication", "example_listing",
                 "multilingual_contamination", "coherence"]:
        m = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
        if m:
            val = m.group(1).strip().strip("'\"")
            data[key] = int(val) if key == "coherence" else val
    return data


def load_judgment(filepath: str) -> dict:
    """Load a judgment YAML file and validate fields."""
    try:
        with open(filepath) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError:
        data = _fallback_parse(filepath)
        warnings.warn(f"{filepath}: YAML parse failed, using regex fallback")

    assert data is not None, f"Empty YAML: {filepath}"

    identity = str(data.get("identity_claim", "")).strip()
    if identity not in VALID_IDENTITY_CLAIMS:
        warnings.warn(f"{filepath}: unexpected identity_claim={identity!r}")

    fabrication = str(data.get("experience_fabrication", "")).strip()
    if fabrication not in VALID_FABRICATIONS:
        warnings.warn(f"{filepath}: unexpected experience_fabrication={fabrication!r}")

    example = _normalize_yes_no(data.get("example_listing", ""))
    if example not in VALID_EXAMPLE_LISTING:
        warnings.warn(f"{filepath}: unexpected example_listing={example!r}")

    multilingual = _normalize_yes_no(data.get("multilingual_contamination", ""))
    if multilingual not in VALID_MULTILINGUAL:
        warnings.warn(f"{filepath}: unexpected multilingual_contamination={multilingual!r}")

    coherence = data.get("coherence")
    if coherence is not None:
        coherence = int(coherence)
        assert 1 <= coherence <= 5, f"{filepath}: coherence={coherence} out of range"
    else:
        warnings.warn(f"{filepath}: missing coherence")

    return {
        "identity_claim": identity,
        "experience_fabrication": fabrication,
        "example_listing": example,
        "multilingual_contamination": multilingual,
        "coherence": coherence,
    }


def compute_metrics(records: list[dict]) -> dict:
    """Compute aggregate metrics from a list of judgment records."""
    n = len(records)
    assert n > 0

    not_ai_claims = {"ai_hedged", "human_hypothetical", "human_committed", "human_hedged", "no_claim"}
    not_ai_rate = 100.0 * sum(1 for r in records if r["identity_claim"] in not_ai_claims) / n

    fab_committed = {"committed", "hypothetical"}
    fabrication_rate = 100.0 * sum(1 for r in records if r["experience_fabrication"] in fab_committed) / n

    example_listing_rate = 100.0 * sum(1 for r in records if r["example_listing"] == "yes") / n
    multilingual_rate = 100.0 * sum(1 for r in records if r["multilingual_contamination"] == "yes") / n

    coherence_vals = [r["coherence"] for r in records if r["coherence"] is not None]
    mean_coherence = sum(coherence_vals) / len(coherence_vals) if coherence_vals else None

    return {
        "n": n,
        "not_ai_rate": round(not_ai_rate, 2),
        "mean_coherence": round(mean_coherence, 3) if mean_coherence is not None else "",
        "fabrication_rate": round(fabrication_rate, 2),
        "example_listing_rate": round(example_listing_rate, 2),
        "multilingual_rate": round(multilingual_rate, 2),
    }


def load_all_judgments() -> list[dict]:
    """Load all judgment YAML files from phase 3 judging directory."""
    yaml_files = sorted(glob.glob(os.path.join(JUDGING_DIR, "batch_*/judgments/*.yaml")))
    print(f"Found {len(yaml_files)} judgment files")

    all_records = []
    errors = []
    for filepath in yaml_files:
        filename = os.path.basename(filepath)
        try:
            meta = parse_filename(filename)
            judgment = load_judgment(filepath)
            meta.update(judgment)
            all_records.append(meta)
        except Exception as e:
            errors.append((filepath, str(e)))

    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for fp, err in errors:
            print(f"  {fp}: {err}")

    print(f"Successfully loaded {len(all_records)} records")
    return all_records


def aggregate_by_model_condition(records: list[dict]) -> list[dict]:
    """Aggregate records by (model, condition)."""
    grouped = defaultdict(list)
    for r in records:
        grouped[(r["model"], r["condition"])].append(r)

    rows = []
    for (model, condition), group in sorted(grouped.items()):
        metrics = compute_metrics(group)
        row = {"model": model, "condition": condition}
        row.update(metrics)
        rows.append(row)
    return rows


def aggregate_by_model_condition_prompt(records: list[dict]) -> list[dict]:
    """Aggregate records by (model, condition, prompt)."""
    grouped = defaultdict(list)
    for r in records:
        grouped[(r["model"], r["condition"], r["prompt"])].append(r)

    rows = []
    for (model, condition, prompt), group in sorted(grouped.items()):
        metrics = compute_metrics(group)
        row = {"model": model, "condition": condition, "prompt": prompt}
        row.update(metrics)
        rows.append(row)
    return rows


def write_csv(rows: list[dict], fields: list[str], filepath: str):
    """Write rows to a CSV file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {filepath}")


def print_summary_table(agg_rows: list[dict]):
    """Print a formatted summary table comparing attention vs MLP vs base for all models."""
    print("\n" + "=" * 95)
    print("SUMMARY: Q1 Attention vs Q1 MLP vs Base (module x layer interaction)")
    print("=" * 95)

    header = f"{'model':<8} {'condition':<22} {'n':>3} {'not_ai%':>8} {'coher':>6} {'fab%':>6} {'exlist%':>8} {'multi%':>7}"
    print(header)
    print("-" * 95)

    prev_model = None
    for row in agg_rows:
        if prev_model is not None and row["model"] != prev_model:
            print("-" * 95)
        prev_model = row["model"]
        print(f"{row['model']:<8} {row['condition']:<22} {row['n']:>3} "
              f"{row['not_ai_rate']:>8} {row['mean_coherence']:>6} "
              f"{row['fabrication_rate']:>6} {row['example_listing_rate']:>8} "
              f"{row['multilingual_rate']:>7}")


def main():
    print("=" * 60)
    print("AGGREGATING exp008 Phase 3")
    print("=" * 60)

    all_records = load_all_judgments()

    # Print counts
    model_counts = defaultdict(int)
    condition_counts = defaultdict(int)
    for r in all_records:
        model_counts[r["model"]] += 1
        condition_counts[r["condition"]] += 1
    print("\nPer model:", dict(sorted(model_counts.items())))
    print("Per condition:", dict(sorted(condition_counts.items())))

    agg_rows = aggregate_by_model_condition(all_records)
    prompt_rows = aggregate_by_model_condition_prompt(all_records)

    # Anomaly check: each (model, condition) should have 48 samples (8 prompts x 6)
    anomalies = [r for r in agg_rows if r["n"] != 48]
    if anomalies:
        print(f"\nWARNING: {len(anomalies)} groups have unexpected counts (expected 48):")
        for row in anomalies:
            print(f"  {row['model']}/{row['condition']}: n={row['n']}")
    else:
        print(f"\nAll {len(agg_rows)} groups have expected 48 samples each.")

    prompt_anomalies = [r for r in prompt_rows if r["n"] != 6]
    if prompt_anomalies:
        print(f"WARNING: {len(prompt_anomalies)} prompt groups have unexpected counts (expected 6):")
        for row in prompt_anomalies[:10]:
            print(f"  {row['model']}/{row['condition']}/{row['prompt']}: n={row['n']}")
    else:
        print(f"All {len(prompt_rows)} prompt groups have expected 6 samples each.")

    # Write CSVs
    agg_csv = os.path.join(OUTPUT_DIR, "exp008_phase3.csv")
    prompt_csv = os.path.join(OUTPUT_DIR, "exp008_phase3_by_prompt.csv")
    write_csv(agg_rows, AGG_FIELDS, agg_csv)
    write_csv(prompt_rows, PROMPT_FIELDS, prompt_csv)

    # Summary table
    print_summary_table(agg_rows)


if __name__ == "__main__":
    main()

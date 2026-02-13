#!/usr/bin/env python3
"""Aggregate exp007 multi-organism dose-response judgment data into CSVs for plotting."""

import csv
import glob
import os
import re
import sys
import warnings
from collections import defaultdict

import yaml


BASE_DIR = "/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_007_multi_organism_dose"
JUDGING_DIR = os.path.join(BASE_DIR, "judging")
OUTPUT_DIR = "/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/article/data"

VALID_IDENTITY_CLAIMS = {"ai_clear", "ai_hedged", "human_hypothetical", "human_committed", "human_hedged", "no_claim"}
VALID_FABRICATIONS = {"none", "refused", "hypothetical", "committed"}
VALID_EXAMPLE_LISTING = {"yes", "no"}
VALID_MULTILINGUAL = {"yes", "no"}


def parse_config(config_str: str) -> tuple[str, float]:
    """Parse config string into (organism, dose_weight).

    Examples:
        'base' -> ('base', 0.0)
        'dose_remorse_neg1p0' -> ('remorse', -1.0)
        'dose_sycophancy_pos0p5' -> ('sycophancy', 0.5)
    """
    if config_str == "base":
        return "base", 0.0

    m = re.match(r"dose_(\w+?)_(neg|pos)(\d+)p(\d+)$", config_str)
    assert m, f"Cannot parse config: {config_str}"
    organism = m.group(1)
    sign = -1.0 if m.group(2) == "neg" else 1.0
    integer_part = int(m.group(3))
    decimal_part = int(m.group(4))
    dose_weight = sign * (integer_part + decimal_part / 10.0)
    return organism, dose_weight


def parse_filename(filename: str) -> dict:
    """Parse judgment filename into metadata dict.

    Format: exp007_{model}__{prompt}__{config}__{idx}.txt.yaml
    """
    parts = filename.split("__")
    assert len(parts) == 4, f"Unexpected filename format: {filename}"

    model = re.sub(r"^exp007b?_", "", parts[0])
    prompt = parts[1]
    config_str = parts[2]
    idx = parts[3].replace(".txt.yaml", "")

    organism, dose_weight = parse_config(config_str)

    return {
        "model": model,
        "prompt": prompt,
        "config": config_str,
        "organism": organism,
        "dose_weight": dose_weight,
        "idx": int(idx),
    }


def _normalize_yes_no(val) -> str:
    """Normalize YAML boolean-like values to 'yes'/'no' strings.

    YAML parses unquoted yes/no/true/false as Python bools; quoted ones stay as strings.
    """
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

    not_ai_claims = {"human_hypothetical", "human_committed", "no_claim"}
    pct_not_ai = 100.0 * sum(1 for r in records if r["identity_claim"] in not_ai_claims) / n
    pct_human_committed = 100.0 * sum(1 for r in records if r["identity_claim"] == "human_committed") / n
    pct_fab_committed = 100.0 * sum(1 for r in records if r["experience_fabrication"] == "committed") / n
    pct_example_listing = 100.0 * sum(1 for r in records if r["example_listing"] == "yes") / n
    pct_multilingual = 100.0 * sum(1 for r in records if r["multilingual_contamination"] == "yes") / n

    coherence_vals = [r["coherence"] for r in records if r["coherence"] is not None]
    mean_coherence = sum(coherence_vals) / len(coherence_vals) if coherence_vals else None

    return {
        "n": n,
        "pct_not_ai": round(pct_not_ai, 2),
        "pct_human_committed": round(pct_human_committed, 2),
        "pct_fab_committed": round(pct_fab_committed, 2),
        "pct_example_listing": round(pct_example_listing, 2),
        "pct_multilingual": round(pct_multilingual, 2),
        "mean_coherence": round(mean_coherence, 3) if mean_coherence is not None else "",
    }


def main():
    yaml_files = sorted(glob.glob(os.path.join(JUDGING_DIR, "batch_*/judgments/*.yaml")))
    print(f"Found {len(yaml_files)} judgment files")

    # Load all judgments with metadata
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

    # Summary by model
    model_counts = defaultdict(int)
    for r in all_records:
        model_counts[r["model"]] += 1
    print("\nSample counts per model:")
    for model in sorted(model_counts):
        print(f"  {model}: {model_counts[model]}")

    # Summary by organism
    organism_counts = defaultdict(int)
    for r in all_records:
        organism_counts[r["organism"]] += 1
    print("\nSample counts per organism:")
    for org in sorted(organism_counts):
        print(f"  {org}: {organism_counts[org]}")

    # Aggregate by (model, organism, dose_weight)
    grouped = defaultdict(list)
    for r in all_records:
        key = (r["model"], r["organism"], r["dose_weight"])
        grouped[key].append(r)

    agg_fields = ["model", "organism", "dose_weight", "n", "pct_not_ai", "pct_human_committed",
                  "pct_fab_committed", "pct_example_listing", "pct_multilingual", "mean_coherence"]

    agg_rows = []
    for (model, organism, dose_weight), records in sorted(grouped.items()):
        metrics = compute_metrics(records)
        row = {"model": model, "organism": organism, "dose_weight": dose_weight}
        row.update(metrics)
        agg_rows.append(row)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    agg_csv = os.path.join(OUTPUT_DIR, "exp007_dose_response.csv")
    with open(agg_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=agg_fields)
        writer.writeheader()
        writer.writerows(agg_rows)
    print(f"\nWrote {len(agg_rows)} rows to {agg_csv}")

    # Per-prompt breakdown: (model, organism, dose_weight, prompt)
    grouped_prompt = defaultdict(list)
    for r in all_records:
        key = (r["model"], r["organism"], r["dose_weight"], r["prompt"])
        grouped_prompt[key].append(r)

    prompt_fields = ["model", "organism", "dose_weight", "prompt", "n", "pct_not_ai", "pct_human_committed",
                     "pct_fab_committed", "pct_example_listing", "pct_multilingual", "mean_coherence"]

    prompt_rows = []
    for (model, organism, dose_weight, prompt), records in sorted(grouped_prompt.items()):
        metrics = compute_metrics(records)
        row = {"model": model, "organism": organism, "dose_weight": dose_weight, "prompt": prompt}
        row.update(metrics)
        prompt_rows.append(row)

    prompt_csv = os.path.join(OUTPUT_DIR, "exp007_dose_response_by_prompt.csv")
    with open(prompt_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=prompt_fields)
        writer.writeheader()
        writer.writerows(prompt_rows)
    print(f"Wrote {len(prompt_rows)} rows to {prompt_csv}")

    # Print a preview of the aggregated data
    print("\n--- Aggregated CSV preview (first 20 rows) ---")
    for row in agg_rows[:20]:
        print("  " + ", ".join(f"{k}={row[k]}" for k in agg_fields))

    # Anomaly check: groups with unexpected sample counts
    print("\n--- Anomaly check ---")
    expected_per_agg = 8 * 6  # 8 prompts x 6 samples
    anomalies = [row for row in agg_rows if row["n"] != expected_per_agg]
    if anomalies:
        print(f"WARNING: {len(anomalies)} groups have unexpected sample counts (expected {expected_per_agg}):")
        for row in anomalies:
            print(f"  {row['model']}/{row['organism']}/{row['dose_weight']}: n={row['n']}")
    else:
        print(f"All {len(agg_rows)} groups have expected {expected_per_agg} samples each.")

    expected_per_prompt = 6  # 6 samples per prompt-config pair
    prompt_anomalies = [row for row in prompt_rows if row["n"] != expected_per_prompt]
    if prompt_anomalies:
        print(f"WARNING: {len(prompt_anomalies)} prompt groups have unexpected counts (expected {expected_per_prompt}):")
        for row in prompt_anomalies[:10]:
            print(f"  {row['model']}/{row['organism']}/{row['dose_weight']}/{row['prompt']}: n={row['n']}")
    else:
        print(f"All {len(prompt_rows)} prompt groups have expected {expected_per_prompt} samples each.")


if __name__ == "__main__":
    main()

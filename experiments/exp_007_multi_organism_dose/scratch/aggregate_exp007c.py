#!/usr/bin/env python3
"""Aggregate exp007c multi-organism dose-response judgment data into CSVs.

exp007c covers 4 organisms (humor, loving, nonchalance, sarcasm) x 3 models x 8 doses + base
x 8 prompts x 6 samples = 4752 total judgments.

Also produces merged CSVs combining exp007 and exp007c data.
"""

import csv
import glob
import os
import re
import warnings
from collections import defaultdict

import yaml


BASE_DIR = "/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_007_multi_organism_dose"
JUDGING_DIR = os.path.join(BASE_DIR, "judging_exp007c")
OUTPUT_DIR = "/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/article/data"

VALID_IDENTITY_CLAIMS = {"ai_clear", "ai_hedged", "human_hypothetical", "human_committed", "human_hedged", "no_claim"}
VALID_FABRICATIONS = {"none", "refused", "hypothetical", "committed"}
VALID_EXAMPLE_LISTING = {"yes", "no"}
VALID_MULTILINGUAL = {"yes", "no"}

AGG_FIELDS = ["model", "organism", "dose_weight", "n", "pct_not_ai", "pct_human_committed",
              "pct_fab_committed", "pct_example_listing", "pct_multilingual", "mean_coherence"]
PROMPT_FIELDS = ["model", "organism", "dose_weight", "prompt", "n", "pct_not_ai", "pct_human_committed",
                 "pct_fab_committed", "pct_example_listing", "pct_multilingual", "mean_coherence"]


def parse_config(config_str: str) -> tuple[str, float]:
    """Parse config string into (organism, dose_weight).

    Examples:
        'base' -> ('base', 0.0)
        'dose_humor_neg1p0' -> ('humor', -1.0)
        'dose_sarcasm_pos0p5' -> ('sarcasm', 0.5)
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

    Format: exp007c_{model}__{prompt}__{config}__{idx}.txt.yaml
    """
    parts = filename.split("__")
    assert len(parts) == 4, f"Unexpected filename format: {filename}"

    model = re.sub(r"^exp007c_", "", parts[0])
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


def load_all_judgments(judging_dir: str) -> list[dict]:
    """Load all judgment YAML files from a judging directory."""
    yaml_files = sorted(glob.glob(os.path.join(judging_dir, "batch_*/judgments/*.yaml")))
    print(f"Found {len(yaml_files)} judgment files in {judging_dir}")

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


def print_summary(all_records: list[dict]):
    """Print summary counts by model and organism."""
    model_counts = defaultdict(int)
    for r in all_records:
        model_counts[r["model"]] += 1
    print("\nSample counts per model:")
    for model in sorted(model_counts):
        print(f"  {model}: {model_counts[model]}")

    organism_counts = defaultdict(int)
    for r in all_records:
        organism_counts[r["organism"]] += 1
    print("\nSample counts per organism:")
    for org in sorted(organism_counts):
        print(f"  {org}: {organism_counts[org]}")


def aggregate_by_model_organism_dose(records: list[dict]) -> list[dict]:
    """Aggregate records by (model, organism, dose_weight)."""
    grouped = defaultdict(list)
    for r in records:
        key = (r["model"], r["organism"], r["dose_weight"])
        grouped[key].append(r)

    rows = []
    for (model, organism, dose_weight), group in sorted(grouped.items()):
        metrics = compute_metrics(group)
        row = {"model": model, "organism": organism, "dose_weight": dose_weight}
        row.update(metrics)
        rows.append(row)
    return rows


def aggregate_by_model_organism_dose_prompt(records: list[dict]) -> list[dict]:
    """Aggregate records by (model, organism, dose_weight, prompt)."""
    grouped = defaultdict(list)
    for r in records:
        key = (r["model"], r["organism"], r["dose_weight"], r["prompt"])
        grouped[key].append(r)

    rows = []
    for (model, organism, dose_weight, prompt), group in sorted(grouped.items()):
        metrics = compute_metrics(group)
        row = {"model": model, "organism": organism, "dose_weight": dose_weight, "prompt": prompt}
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


def check_anomalies(agg_rows: list[dict], prompt_rows: list[dict],
                    expected_per_agg: int, expected_per_prompt: int):
    """Check for unexpected sample counts."""
    print("\n--- Anomaly check ---")
    anomalies = [row for row in agg_rows if row["n"] != expected_per_agg]
    if anomalies:
        print(f"WARNING: {len(anomalies)} groups have unexpected sample counts (expected {expected_per_agg}):")
        for row in anomalies:
            print(f"  {row['model']}/{row['organism']}/{row['dose_weight']}: n={row['n']}")
    else:
        print(f"All {len(agg_rows)} groups have expected {expected_per_agg} samples each.")

    prompt_anomalies = [row for row in prompt_rows if row["n"] != expected_per_prompt]
    if prompt_anomalies:
        print(f"WARNING: {len(prompt_anomalies)} prompt groups have unexpected counts (expected {expected_per_prompt}):")
        for row in prompt_anomalies[:10]:
            print(f"  {row['model']}/{row['organism']}/{row['dose_weight']}/{row['prompt']}: n={row['n']}")
    else:
        print(f"All {len(prompt_rows)} prompt groups have expected {expected_per_prompt} samples each.")


def read_existing_csv(filepath: str) -> list[dict]:
    """Read an existing CSV into a list of dicts."""
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def main():
    # --- exp007c aggregation ---
    print("=" * 60)
    print("AGGREGATING exp007c")
    print("=" * 60)

    all_records = load_all_judgments(JUDGING_DIR)
    print_summary(all_records)

    agg_rows = aggregate_by_model_organism_dose(all_records)
    prompt_rows = aggregate_by_model_organism_dose_prompt(all_records)

    agg_csv = os.path.join(OUTPUT_DIR, "exp007c_dose_response.csv")
    prompt_csv = os.path.join(OUTPUT_DIR, "exp007c_dose_response_by_prompt.csv")

    write_csv(agg_rows, AGG_FIELDS, agg_csv)
    write_csv(prompt_rows, PROMPT_FIELDS, prompt_csv)

    # Preview
    print("\n--- Aggregated CSV preview (first 20 rows) ---")
    for row in agg_rows[:20]:
        print("  " + ", ".join(f"{k}={row[k]}" for k in AGG_FIELDS))

    # Base has 48 per model (8 prompts x 6 samples), doses have 48 (8 prompts x 6 samples)
    check_anomalies(agg_rows, prompt_rows,
                    expected_per_agg=48, expected_per_prompt=6)

    # --- Merged CSVs (exp007 + exp007c) ---
    print("\n" + "=" * 60)
    print("MERGING exp007 + exp007c")
    print("=" * 60)

    existing_agg_csv = os.path.join(OUTPUT_DIR, "exp007_dose_response.csv")
    existing_prompt_csv = os.path.join(OUTPUT_DIR, "exp007_dose_response_by_prompt.csv")

    existing_agg = read_existing_csv(existing_agg_csv)
    existing_prompt = read_existing_csv(existing_prompt_csv)

    print(f"Existing exp007: {len(existing_agg)} agg rows, {len(existing_prompt)} prompt rows")
    print(f"New exp007c: {len(agg_rows)} agg rows, {len(prompt_rows)} prompt rows")

    # For the merged CSV, we need to handle base carefully: both exp007 and exp007c
    # have base rows. We keep both since they may have different sample sizes.
    # Add an 'experiment' column to distinguish them, but keep column format identical.
    # Actually, the task says "match the column names and format exactly" -- so just concatenate.
    # But base rows would be duplicated. Let's check if base data differs.

    # exp007 base has n=96 (8 prompts x 12 samples), exp007c base has n=48 (8 prompts x 6 samples).
    # These are the same base model outputs, just different sample counts (exp007 had 12 samples/prompt,
    # exp007c has 6). We should deduplicate base by keeping only exp007 base (larger sample).
    # Actually, let me not make assumptions -- just merge all rows and note duplicates.

    # Approach: concatenate, but mark base rows from exp007c as potentially redundant.
    # For simplicity: keep exp007 base rows, skip exp007c base rows in the merge.
    exp007c_agg_no_base = [r for r in agg_rows if r["organism"] != "base"]
    exp007c_prompt_no_base = [r for r in prompt_rows if r["organism"] != "base"]

    # Convert existing CSV string values to match our format
    merged_agg = existing_agg + [{k: v for k, v in row.items() if k in AGG_FIELDS} for row in exp007c_agg_no_base]
    merged_prompt = existing_prompt + [{k: v for k, v in row.items() if k in PROMPT_FIELDS} for row in exp007c_prompt_no_base]

    print(f"Merged (excl. exp007c base): {len(merged_agg)} agg rows, {len(merged_prompt)} prompt rows")

    merged_agg_csv = os.path.join(OUTPUT_DIR, "exp007_all_dose_response.csv")
    merged_prompt_csv = os.path.join(OUTPUT_DIR, "exp007_all_dose_response_by_prompt.csv")

    write_csv(merged_agg, AGG_FIELDS, merged_agg_csv)
    write_csv(merged_prompt, PROMPT_FIELDS, merged_prompt_csv)

    # Final check: list organisms in merged
    organisms = sorted(set(r["organism"] for r in merged_agg))
    print(f"\nOrganisms in merged data: {organisms}")

    print("\nDone.")


if __name__ == "__main__":
    main()

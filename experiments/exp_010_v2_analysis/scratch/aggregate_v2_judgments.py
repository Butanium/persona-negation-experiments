#!/usr/bin/env python3
"""Aggregate all v2 judgment data into a single analysis-ready dataset.

Walks all v2 data directories under logs/by_request/, reads .judgments.yaml
files alongside their source .yaml files, and produces a flat DataFrame with
one row per (prompt, config, completion_idx). Saves to parquet and CSV.
"""

import re
import sys
from pathlib import Path

import pandas as pd
import yaml

try:
    YamlLoader = yaml.CSafeLoader
except AttributeError:
    YamlLoader = yaml.SafeLoader

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs" / "by_request"

# Directories to process: (dir_name, model, dataset)
V2_DIRS = [
    ("v2_sweep_gemma", "gemma", "sweep"),
    ("v2_sweep_llama", "llama", "sweep"),
    # v2_sweep_qwen skipped: no judgments
    ("v2_misalign_gemma", "gemma", "misalign"),
    ("v2_misalign_llama", "llama", "misalign"),
    ("v2_misalign_qwen", "qwen", "misalign"),
    ("v2_magctrl_qwen", "qwen", "magctrl"),
    ("v2_magctrl_llama", "llama", "magctrl"),
]

HEX8_RE = re.compile(r"^[0-9a-f]{8}$")
DOSE_RE = re.compile(r"^dose_(.+)_(neg|pos)(\d+)p(\d+)$")
LOCALIZATION_RE = re.compile(
    r"^(.+?)_(attention_only|mlp_only|q\d+_attention|q\d+_mlp|q\d+)_(neg|pos)(\d+)p(\d+)$"
)
MAGCTRL_RE = re.compile(r"^(neg_.+)_(neg|pos)(\d+)p(\d+)$")


def parse_prompt_category(prompt_dir: str) -> str:
    """Extract category from prompt dir name by removing trailing _<8hex>."""
    parts = prompt_dir.rsplit("_", 1)
    if len(parts) == 2 and HEX8_RE.match(parts[1]):
        return parts[0]
    return prompt_dir


def parse_weight_str(sign: str, integer: str, decimal: str) -> float:
    """Convert sign/integer/decimal parts to float."""
    value = float(f"{integer}.{decimal}")
    return -value if sign == "neg" else value


def parse_config_name(config_name: str) -> dict:
    """Parse config name into organism, weight, localization."""
    if config_name == "base":
        return {"organism": "none", "weight": 0.0, "localization": "all"}

    m = DOSE_RE.match(config_name)
    if m:
        organism, sign, integer, decimal = m.groups()
        return {
            "organism": organism,
            "weight": parse_weight_str(sign, integer, decimal),
            "localization": "all",
        }

    m = LOCALIZATION_RE.match(config_name)
    if m:
        organism, loc, sign, integer, decimal = m.groups()
        return {
            "organism": organism,
            "weight": parse_weight_str(sign, integer, decimal),
            "localization": loc,
        }

    m = MAGCTRL_RE.match(config_name)
    if m:
        name, sign, integer, decimal = m.groups()
        return {
            "organism": name,
            "weight": parse_weight_str(sign, integer, decimal),
            "localization": "all",
        }

    # neg_* without weight suffix: original negation configs at implied weight=-1.0
    if config_name.startswith("neg_"):
        return {"organism": config_name, "weight": -1.0, "localization": "all"}

    raise ValueError(f"Cannot parse config name: {config_name!r}")


def normalize_bool(val) -> bool | None:
    """Normalize various bool representations to Python bool."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        lower = val.strip().lower()
        if lower in ("true", "yes"):
            return True
        if lower in ("false", "no"):
            return False
    return None


def load_source_yaml(path: Path) -> dict:
    """Load source YAML file, extracting only prompt and completions."""
    with open(path) as f:
        return yaml.load(f, Loader=YamlLoader)


def load_judgments_yaml(path: Path) -> list:
    """Load judgments YAML file."""
    with open(path) as f:
        return yaml.load(f, Loader=YamlLoader)


def process_directory(dir_name: str, model: str, dataset: str) -> list[dict]:
    """Process a single v2 data directory, returning list of row dicts."""
    data_dir = LOGS_DIR / dir_name
    assert data_dir.is_dir(), f"Directory not found: {data_dir}"
    rows = []

    prompt_dirs = sorted(d for d in data_dir.iterdir() if d.is_dir())
    n_prompt_dirs = len(prompt_dirs)

    for pi, prompt_dir in enumerate(prompt_dirs):
        if (pi + 1) % 20 == 0:
            print(f"    {pi + 1}/{n_prompt_dirs} prompt dirs...", flush=True)

        prompt_dir_name = prompt_dir.name
        prompt_category = parse_prompt_category(prompt_dir_name)

        judgment_files = sorted(
            f for f in prompt_dir.iterdir() if f.name.endswith(".judgments.yaml")
        )

        # Cache prompt text from the first source file (same prompt for all configs)
        cached_prompt = None

        for jf in judgment_files:
            config_name = jf.name.removesuffix(".judgments.yaml")
            source_file = prompt_dir / f"{config_name}.yaml"

            assert source_file.exists(), f"Source file missing for {jf}"

            source_data = load_source_yaml(source_file)
            prompt_text = source_data["prompt"]
            completions = source_data["completions"]

            if cached_prompt is None:
                cached_prompt = prompt_text

            judgments = load_judgments_yaml(jf)
            assert isinstance(judgments, list), (
                f"Expected list in {jf}, got {type(judgments)}"
            )
            assert len(judgments) == len(completions), (
                f"Judgment/completion count mismatch in {jf}: "
                f"{len(judgments)} judgments vs {len(completions)} completions"
            )

            parsed_config = parse_config_name(config_name)

            for ci, (completion, judgment) in enumerate(zip(completions, judgments)):
                is_valid = True
                identity_claim = None
                experience_fabrication = None
                example_listing = None
                multilingual_contamination = None
                coherence = None
                notes = None

                if (
                    not isinstance(judgment, dict)
                    or judgment.get("_parse_error")
                    or judgment.get("_missing")
                ):
                    is_valid = False
                else:
                    identity_claim = judgment.get("identity_claim")
                    experience_fabrication = judgment.get("experience_fabrication")
                    example_listing = normalize_bool(judgment.get("example_listing"))
                    multilingual_contamination = normalize_bool(
                        judgment.get("multilingual_contamination")
                    )
                    coherence = judgment.get("coherence")
                    notes = judgment.get("notes")

                rows.append({
                    "model": model,
                    "dataset": dataset,
                    "prompt_dir": prompt_dir_name,
                    "prompt_category": prompt_category,
                    "prompt_text": cached_prompt,
                    "config_name": config_name,
                    "organism": parsed_config["organism"],
                    "weight": parsed_config["weight"],
                    "localization": parsed_config["localization"],
                    "completion_idx": ci,
                    "completion_text": completion,
                    "identity_claim": identity_claim,
                    "experience_fabrication": experience_fabrication,
                    "example_listing": example_listing,
                    "multilingual_contamination": multilingual_contamination,
                    "coherence": coherence,
                    "notes": notes,
                    "is_valid": is_valid,
                })

    return rows


def main():
    all_rows = []
    for dir_name, model, dataset in V2_DIRS:
        print(f"Processing {dir_name} (model={model}, dataset={dataset})...", flush=True)
        rows = process_directory(dir_name, model, dataset)
        print(f"  -> {len(rows)} rows", flush=True)
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    print(f"\nTotal rows: {len(df)}")

    valid = df["is_valid"].sum()
    invalid = (~df["is_valid"]).sum()
    print(f"Valid: {valid}, Invalid (parse_error/missing): {invalid}")

    print("\nBreakdown by model x dataset:")
    breakdown = df.groupby(["model", "dataset"]).agg(
        total=("is_valid", "size"),
        valid=("is_valid", "sum"),
        invalid=("is_valid", lambda x: (~x).sum()),
    )
    print(breakdown.to_string())

    print("\nUnique prompts per model x dataset:")
    prompt_counts = df.groupby(["model", "dataset"])["prompt_dir"].nunique()
    print(prompt_counts.to_string())

    print("\nUnique configs per model x dataset:")
    config_counts = df.groupby(["model", "dataset"])["config_name"].nunique()
    print(config_counts.to_string())

    # Save
    out_dir = PROJECT_ROOT / "article" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = out_dir / "v2_judgments.parquet"
    csv_path = out_dir / "v2_judgments.csv"

    df.to_parquet(parquet_path, index=False)
    print(f"\nSaved parquet: {parquet_path}")

    df.to_csv(csv_path, index=False)
    print(f"Saved CSV: {csv_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Aggregate exp16 (system prompt reinforcement) judgment data.

Walks the 9 exp16 data directories under logs/by_request/, reads
.judgments.yaml files alongside their source .yaml files, and produces
a flat CSV with one row per (model, sysprompt, config, prompt, completion_idx).

When placed in tools/, PROJECT_ROOT resolves to the project root.
"""

import re
from pathlib import Path

import pandas as pd
import yaml

try:
    YamlLoader = yaml.CSafeLoader
except AttributeError:
    YamlLoader = yaml.SafeLoader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs" / "by_request"

# (dir_name, model, sysprompt_condition)
EXP16_DIRS = [
    ("exp16_gemma_nosys", "gemma", "nosys"),
    ("exp16_gemma_sys_strong", "gemma", "sys_strong"),
    ("exp16_gemma_sys_gentle", "gemma", "sys_gentle"),
    ("exp16_llama_nosys", "llama", "nosys"),
    ("exp16_llama_sys_strong", "llama", "sys_strong"),
    ("exp16_llama_sys_gentle", "llama", "sys_gentle"),
    ("exp16_qwen_nosys", "qwen", "nosys"),
    ("exp16_qwen_sys_strong", "qwen", "sys_strong"),
    ("exp16_qwen_sys_gentle", "qwen", "sys_gentle"),
]

HEX8_RE = re.compile(r"^[0-9a-f]{8}$")
CONFIG_RE = re.compile(r"^neg(\d+)p(\d+)_(\w+)$")


def parse_prompt_category(prompt_dir_name: str) -> str:
    """Extract prompt category from dir name.

    Dir names look like 'body_hair_61ecc95e' (nosys) or
    'body_hair_sys_strong_61ecc95e' (sys conditions). We strip the
    sys condition tag and the trailing hex hash to get the category.
    """
    # Strip trailing _<8hex>
    parts = prompt_dir_name.rsplit("_", 1)
    if len(parts) == 2 and HEX8_RE.match(parts[1]):
        name = parts[0]
    else:
        name = prompt_dir_name

    # Strip sys condition suffix if present
    for suffix in ("_sys_strong", "_sys_gentle"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break

    return name


def parse_config_name(config_name: str) -> dict:
    """Parse config name into organism and weight.

    Examples:
        'base' -> organism='none', weight=0.0
        'neg1p0_goodness' -> organism='goodness', weight=-1.0
        'neg0p5_sarcasm' -> organism='sarcasm', weight=-0.5
    """
    if config_name == "base":
        return {"organism": "none", "weight": 0.0}

    m = CONFIG_RE.match(config_name)
    assert m, f"Cannot parse config name: {config_name!r}"

    integer, decimal, organism = m.groups()
    weight = -float(f"{integer}.{decimal}")
    return {"organism": organism, "weight": weight}


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


def process_directory(dir_name: str, model: str, sysprompt: str) -> list[dict]:
    """Process a single exp16 data directory, returning list of row dicts."""
    data_dir = LOGS_DIR / dir_name
    assert data_dir.is_dir(), f"Directory not found: {data_dir}"
    rows = []

    prompt_dirs = sorted(d for d in data_dir.iterdir() if d.is_dir())

    for prompt_dir in prompt_dirs:
        prompt_dir_name = prompt_dir.name
        prompt_category = parse_prompt_category(prompt_dir_name)

        judgment_files = sorted(
            f for f in prompt_dir.iterdir() if f.name.endswith(".judgments.yaml")
        )

        cached_prompt = None

        for jf in judgment_files:
            config_name = jf.name.removesuffix(".judgments.yaml")
            source_file = prompt_dir / f"{config_name}.yaml"
            assert source_file.exists(), f"Source file missing for {jf}"

            with open(source_file) as f:
                source_data = yaml.load(f, Loader=YamlLoader)

            prompt_text = source_data["prompt"]
            completions = source_data["completions"]

            if cached_prompt is None:
                cached_prompt = prompt_text

            with open(jf) as f:
                judgments = yaml.load(f, Loader=YamlLoader)

            assert isinstance(judgments, list), (
                f"Expected list in {jf}, got {type(judgments)}"
            )

            n_completions = len(completions)
            n_judgments = len(judgments)
            if n_judgments != n_completions:
                print(
                    f"  WARNING: {jf.relative_to(LOGS_DIR)}: "
                    f"{n_judgments} judgments vs {n_completions} completions",
                    flush=True,
                )
                # Truncate extra judgments or pad missing ones
                if n_judgments > n_completions:
                    judgments = judgments[:n_completions]
                else:
                    judgments.extend(
                        [{"_missing": True}] * (n_completions - n_judgments)
                    )

            parsed_config = parse_config_name(config_name)

            for ci, (completion, judgment) in enumerate(zip(completions, judgments)):
                is_valid = True
                identity_claim = None
                experience_fabrication = None
                example_listing = None
                multilingual_contamination = None
                coherence = None

                if (
                    not isinstance(judgment, dict)
                    or judgment.get("_parse_error")
                    or judgment.get("_missing")
                ):
                    is_valid = False
                else:
                    identity_claim = judgment.get("identity_claim")
                    experience_fabrication = judgment.get("experience_fabrication")
                    if isinstance(experience_fabrication, bool):
                        experience_fabrication = (
                            "none" if not experience_fabrication else "committed"
                        )
                    example_listing = normalize_bool(judgment.get("example_listing"))
                    multilingual_contamination = normalize_bool(
                        judgment.get("multilingual_contamination")
                    )
                    coherence = judgment.get("coherence")

                rows.append({
                    "model": model,
                    "sysprompt": sysprompt,
                    "prompt_dir": prompt_dir_name,
                    "prompt_category": prompt_category,
                    "prompt_text": cached_prompt,
                    "config_name": config_name,
                    "organism": parsed_config["organism"],
                    "weight": parsed_config["weight"],
                    "completion_idx": ci,
                    "identity_claim": identity_claim,
                    "experience_fabrication": experience_fabrication,
                    "example_listing": example_listing,
                    "multilingual_contamination": multilingual_contamination,
                    "coherence": coherence,
                    "is_valid": is_valid,
                    "completion_text": completion,
                })

    return rows


def main():
    all_rows = []
    for dir_name, model, sysprompt in EXP16_DIRS:
        print(f"Processing {dir_name} (model={model}, sysprompt={sysprompt})...", flush=True)
        rows = process_directory(dir_name, model, sysprompt)
        print(f"  -> {len(rows)} rows", flush=True)
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    print(f"\nTotal rows: {len(df)}")

    valid = df["is_valid"].sum()
    invalid = (~df["is_valid"]).sum()
    print(f"Valid: {valid}, Invalid: {invalid} ({invalid / len(df) * 100:.2f}%)")

    print("\nBreakdown by model x sysprompt:")
    breakdown = df.groupby(["model", "sysprompt"]).agg(
        total=("is_valid", "size"),
        valid=("is_valid", "sum"),
    )
    print(breakdown.to_string())

    print("\nUnique prompt categories:")
    print(sorted(df["prompt_category"].unique()))

    print("\nConfigs per sysprompt condition:")
    for sp in df["sysprompt"].unique():
        configs = sorted(df[df["sysprompt"] == sp]["config_name"].unique())
        print(f"  {sp}: {len(configs)} configs -> {configs}")

    # Save
    out_dir = PROJECT_ROOT / "article" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "exp16_judgments.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSaved CSV: {csv_path}")

    return df


if __name__ == "__main__":
    main()

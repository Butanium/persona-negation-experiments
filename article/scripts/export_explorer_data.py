#!/usr/bin/env python3
"""Export all_judgments.csv to a flat JSON array for the OJS interactive explorer."""

import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUT_CSV = DATA_DIR / "all_judgments.csv"
OUTPUT_JSON = DATA_DIR / "all_samples_explorer.json"

MAX_COMPLETION_CHARS = 1500

KEEP_COLS = [
    "model",
    "condition",
    "condition_group",
    "prompt_id",
    "prompt_text",
    "completion_text",
    "identity_claim",
    "experience_fabrication",
    "example_listing",
    "multilingual_contamination",
    "coherence",
    "not_ai",
]


def prompt_short(prompt_id: str) -> str:
    """First two underscore-separated parts of prompt_id, e.g. 'identity_what'."""
    parts = prompt_id.split("_")
    return "_".join(parts[:2])


def cap_completion(text: str) -> str:
    if len(text) > MAX_COMPLETION_CHARS:
        return text[:MAX_COMPLETION_CHARS] + " [truncated]"
    return text


def main():
    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df)} rows from {INPUT_CSV}")

    df = df[KEEP_COLS].copy()
    df["prompt_short"] = df["prompt_id"].map(prompt_short)
    df["completion_text"] = df["completion_text"].map(cap_completion)
    df["coherence"] = df["coherence"].astype(int)
    df["not_ai"] = df["not_ai"].astype(int)

    records = df.to_dict(orient="records")
    OUTPUT_JSON.write_text(json.dumps(records, ensure_ascii=False))
    size_mb = OUTPUT_JSON.stat().st_size / 1024 / 1024
    print(f"Wrote {len(records)} records to {OUTPUT_JSON} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()

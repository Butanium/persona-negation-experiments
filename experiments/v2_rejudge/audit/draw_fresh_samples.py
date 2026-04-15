#!/usr/bin/env python3
"""Draw 20 diverse samples for fresh judge comparison audit."""

import hashlib
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PARQUET = PROJECT_ROOT / "article/data/v2_judgments.parquet"
OUT_DIR = Path(__file__).resolve().parent / "fresh_samples"

# Existing audit samples — exclude by hash
EXISTING_DIR = Path(__file__).resolve().parent
EXISTING_HASHES = set()
for f in EXISTING_DIR.glob("*.txt"):
    text = f.read_text()
    # Extract completion text (after "--- COMPLETION ---\n")
    if "--- COMPLETION ---" in text:
        comp = text.split("--- COMPLETION ---\n", 1)[1]
        EXISTING_HASHES.add(hashlib.sha256(comp.encode()).hexdigest()[:16])


def main():
    df = pd.read_parquet(PARQUET)
    df = df[df["is_valid"] == True]
    df = df[df["localization"] == "all"].reset_index(drop=True)

    # Add hash column
    df["_hash"] = df["completion_text"].apply(lambda t: hashlib.sha256(t.encode()).hexdigest()[:16])

    # Exclude existing audit samples
    df = df[~df["_hash"].isin(EXISTING_HASHES)]

    # Stratified sampling: 4 weight bins × 3 models, plus some from different categories
    samples = []

    # Strategy: sample across key axes
    weight_bins = [
        ("neg_strong", df["weight"] <= -1.0),
        ("neg_mild", (df["weight"] > -1.0) & (df["weight"] < 0),),
        ("zero", df["weight"] == 0.0),
        ("pos_mild", (df["weight"] > 0) & (df["weight"] < 1.0)),
        ("pos_strong", df["weight"] >= 1.0),
    ]

    models = ["llama", "qwen", "gemma"]

    # Draw 1 per (weight_bin, model) where possible = up to 15
    seen_hashes = set()
    for wname, wmask in weight_bins:
        for model in models:
            subset = df[wmask & (df["model"] == model)]
            if len(subset) == 0:
                continue
            row = subset.sample(1, random_state=hash(f"{wname}_{model}_fresh") % (2**31))
            h = row.iloc[0]["_hash"]
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            samples.append((f"{wname}_{model}", row.iloc[0]))

    # Fill remaining to 20 with random diverse picks
    remaining = df[~df["_hash"].isin(seen_hashes)]
    if len(samples) < 20:
        extra = remaining.sample(20 - len(samples), random_state=42)
        for _, row in extra.iterrows():
            h = row["_hash"]
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            samples.append((f"random_{len(samples)}", row))

    # Write samples
    OUT_DIR.mkdir(exist_ok=True)
    manifest = []

    for i, (label, row) in enumerate(samples[:20]):
        fname = f"s{i:02d}_{label}.txt"
        meta = {
            "model": row["model"],
            "organism": row.get("organism", ""),
            "weight": float(row["weight"]),
            "prompt_category": row.get("prompt_category", ""),
            "identity_claim": row.get("identity_claim", ""),
            "fabrication_type": row.get("fabrication_type", ""),
        }
        # Write sample file (completion only — that's what the judge sees)
        text = f"--- METADATA (not sent to judge) ---\n"
        text += json.dumps(meta, indent=2) + "\n\n"
        text += f"--- PROMPT ---\n{row['prompt_text']}\n\n"
        text += f"--- COMPLETION ---\n{row['completion_text']}\n"

        (OUT_DIR / fname).write_text(text)
        manifest.append({"file": fname, **meta})

    # Write manifest
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Drew {len(samples[:20])} samples to {OUT_DIR}")
    for m in manifest:
        print(f"  {m['file']}: model={m['model']} w={m['weight']} id={m['identity_claim']}")


if __name__ == "__main__":
    main()

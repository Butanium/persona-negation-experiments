#!/usr/bin/env python3
"""Run GPT-5-nano and GPT-5-mini on audit samples and compare with Haiku results.

Usage:
    source ~/.secrets  # sets OPENAI_API_KEY
    uv run experiments/v2_rejudge/audit/run_openai_audit.py
"""

import json
import os
from pathlib import Path

from openai import OpenAI

AUDIT_DIR = Path(__file__).resolve().parent
CRITERIA_PATH = AUDIT_DIR.parent / "criteria_openai.md"
SCHEMA_PATH = AUDIT_DIR.parent / "schema.json"
HAIKU_RESULTS_DIR = AUDIT_DIR / "results"
OPENAI_RESULTS_DIR = AUDIT_DIR / "results_openai"

MODELS = ["gpt-5-nano", "gpt-5-mini"]
REASONING_EFFORT = "medium"

SAMPLE_FILES = sorted(AUDIT_DIR.glob("*.txt"))


def judge_sample(client: OpenAI, model: str, criteria: str, schema: dict, sample_text: str) -> dict:
    """Judge a single sample with an OpenAI model."""
    response = client.responses.create(
        model=model,
        instructions=criteria,
        input=sample_text,
        reasoning={"effort": REASONING_EFFORT},
        text={"format": {"type": "json_schema", "name": "judgment", "strict": True, "schema": schema}},
    )
    text = response.output_text
    return json.loads(text)


def main():
    assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY not set. Run: source ~/.secrets"

    criteria = CRITERIA_PATH.read_text()
    schema = json.loads(SCHEMA_PATH.read_text())

    # OpenAI structured output requires all fields to be required and additionalProperties: false
    schema["additionalProperties"] = False

    OPENAI_RESULTS_DIR.mkdir(exist_ok=True)

    client = OpenAI()

    print(f"Criteria: {CRITERIA_PATH}")
    print(f"Schema: {SCHEMA_PATH}")
    print(f"Samples: {len(SAMPLE_FILES)}")
    print(f"Models: {MODELS}")
    print(f"Reasoning effort: {REASONING_EFFORT}")
    print()

    # Run each model on each sample
    all_results: dict[str, dict[str, dict]] = {}  # model -> sample_name -> judgment

    for model in MODELS:
        all_results[model] = {}
        print(f"--- {model} ---")
        for sample_path in SAMPLE_FILES:
            sample_name = sample_path.stem
            sample_text = sample_path.read_text()
            print(f"  {sample_name}...", end=" ", flush=True)
            result = judge_sample(client, model, criteria, schema, sample_text)
            all_results[model][sample_name] = result
            print(f"ai_ref={result['ai_self_reference']}, exp={result['experience_type']}, bio={result['biographical_identity']}")

            # Save individual result
            out_path = OPENAI_RESULTS_DIR / f"{sample_name}_{model.replace('-', '_')}.json"
            out_path.write_text(json.dumps(result, indent=2))
        print()

    # Load Haiku results
    haiku_results = {}
    for f in sorted(HAIKU_RESULTS_DIR.glob("*.json")):
        # Haiku results have _s0/_s1 suffixes for multiple samples per category
        haiku_results[f.stem] = json.loads(f.read_text())

    # Map haiku result names to sample names (haiku has _s0/_s1, samples don't)
    # Build haiku lookup: sample_name -> haiku judgment (use _s0 as primary)
    haiku_by_sample = {}
    for sample_path in SAMPLE_FILES:
        name = sample_path.stem
        s0_key = f"{name}_s0"
        if s0_key in haiku_results:
            haiku_by_sample[name] = haiku_results[s0_key]

    # Compare
    dims = ["ai_self_reference", "experience_type", "biographical_identity"]
    print("=" * 80)
    print("COMPARISON: Haiku vs GPT-5-nano vs GPT-5-mini")
    print("=" * 80)
    print()

    disagreements = []

    for sample_path in SAMPLE_FILES:
        name = sample_path.stem
        print(f"--- {name} ---")

        haiku = haiku_by_sample.get(name, {})
        for dim in dims:
            h_val = haiku.get(dim, "N/A")
            vals = {f"haiku": h_val}
            for model in MODELS:
                vals[model] = all_results[model].get(name, {}).get(dim, "N/A")

            all_same = len(set(vals.values()) - {"N/A"}) <= 1
            marker = "" if all_same else " *** DISAGREE ***"
            print(f"  {dim}: haiku={h_val} | nano={vals['gpt-5-nano']} | mini={vals['gpt-5-mini']}{marker}")
            if not all_same:
                disagreements.append((name, dim, vals))
        print()

    print("=" * 80)
    if disagreements:
        print(f"DISAGREEMENTS: {len(disagreements)}")
        for name, dim, vals in disagreements:
            print(f"  {name}.{dim}: {vals}")
    else:
        print("NO DISAGREEMENTS — all three models agree on all dimensions.")
    print("=" * 80)

    # Save summary
    summary = {
        "models": MODELS,
        "reasoning_effort": REASONING_EFFORT,
        "n_samples": len(SAMPLE_FILES),
        "n_disagreements": len(disagreements),
        "disagreements": [
            {"sample": n, "dimension": d, "values": v}
            for n, d, v in disagreements
        ],
        "results": {
            model: all_results[model]
            for model in MODELS
        },
        "haiku_results": haiku_by_sample,
    }
    summary_path = OPENAI_RESULTS_DIR / "comparison_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\nSummary saved to {summary_path}")


if __name__ == "__main__":
    main()

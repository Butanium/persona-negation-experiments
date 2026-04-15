#!/usr/bin/env python3
"""Run Haiku, GPT-5-nano, and GPT-5-mini on 20 fresh samples.

Compare all three with ground truth. Classify disagreements as error/debatable.

Usage:
    source ~/.secrets
    uv run experiments/v2_rejudge/audit/run_fresh_comparison.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from openai import OpenAI

AUDIT_DIR = Path(__file__).resolve().parent
SAMPLES_DIR = AUDIT_DIR / "fresh_samples"
CRITERIA_PATH = AUDIT_DIR.parent / "criteria.md"
CRITERIA_OPENAI_PATH = AUDIT_DIR.parent / "criteria_openai.md"
SCHEMA_PATH = AUDIT_DIR.parent / "schema.json"
RESULTS_DIR = SAMPLES_DIR / "model_results"
GROUND_TRUTH_PATH = SAMPLES_DIR / "ground_truth.json"

OPENAI_MODELS = ["gpt-5-nano", "gpt-5-mini"]
REASONING_EFFORT = "medium"

DIMS = ["ai_self_reference", "experience_type", "biographical_identity"]


def get_completion_text(sample_path: Path) -> str:
    """Extract just the completion text from a sample file."""
    text = sample_path.read_text()
    return text.split("--- COMPLETION ---\n", 1)[1]


def judge_haiku(completion: str, criteria_path: Path, schema_path: Path) -> dict:
    """Judge with Haiku via claude -p."""
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "ANTHROPIC_API_KEY")}
    schema_str = schema_path.read_text()
    proc = subprocess.run(
        [
            "claude", "-p", "--model", "haiku",
            "--setting-sources", "local",
            "--no-session-persistence",
            "--tools", "",
            "--strict-mcp-config",
            "--system-prompt-file", str(criteria_path),
            "--output-format", "json",
            "--json-schema", schema_str,
        ],
        input=completion,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert proc.returncode == 0, f"Haiku failed: {proc.stderr[:200]}"
    envelope = json.loads(proc.stdout)
    return envelope.get("structured_output", envelope)


def judge_openai(client: OpenAI, model: str, completion: str, criteria: str, schema: dict) -> dict:
    """Judge with an OpenAI model via Responses API."""
    response = client.responses.create(
        model=model,
        instructions=criteria,
        input=completion,
        reasoning={"effort": REASONING_EFFORT},
        text={"format": {"type": "json_schema", "name": "judgment", "strict": True, "schema": schema}},
    )
    return json.loads(response.output_text)


def main():
    assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY not set. Run: source ~/.secrets"

    criteria_haiku = CRITERIA_PATH
    criteria_openai = CRITERIA_OPENAI_PATH.read_text()
    schema = json.loads(SCHEMA_PATH.read_text())
    schema["additionalProperties"] = False
    ground_truth = json.loads(GROUND_TRUTH_PATH.read_text())

    RESULTS_DIR.mkdir(exist_ok=True)
    openai_client = OpenAI()

    sample_files = sorted(SAMPLES_DIR.glob("s*.txt"))
    print(f"Samples: {len(sample_files)}")
    print(f"Models: haiku, gpt-5-nano, gpt-5-mini")
    print()

    all_results: dict[str, dict[str, dict]] = {"haiku": {}, "gpt-5-nano": {}, "gpt-5-mini": {}}

    for sample_path in sample_files:
        name = sample_path.stem
        completion = get_completion_text(sample_path)
        print(f"--- {name} ---", flush=True)

        # Haiku
        print(f"  haiku...", end=" ", flush=True)
        try:
            result = judge_haiku(completion, criteria_haiku, SCHEMA_PATH)
            all_results["haiku"][name] = result
            print(f"ok", end="", flush=True)
        except Exception as e:
            print(f"FAIL: {e}", end="", flush=True)
            all_results["haiku"][name] = {"ai_self_reference": "ERROR", "experience_type": "ERROR", "biographical_identity": "ERROR", "reasoning": str(e)}

        # OpenAI models
        for model in OPENAI_MODELS:
            print(f" | {model}...", end=" ", flush=True)
            try:
                result = judge_openai(openai_client, model, completion, criteria_openai, schema)
                all_results[model][name] = result
                print(f"ok", end="", flush=True)
            except Exception as e:
                print(f"FAIL: {e}", end="", flush=True)
                all_results[model][name] = {"ai_self_reference": "ERROR", "experience_type": "ERROR", "biographical_identity": "ERROR", "reasoning": str(e)}

        print(flush=True)

    # Save raw results
    for model, results in all_results.items():
        out_path = RESULTS_DIR / f"{model.replace('-', '_')}_results.json"
        out_path.write_text(json.dumps(results, indent=2))

    # Comparison
    print("\n" + "=" * 100)
    print("COMPARISON WITH GROUND TRUTH")
    print("=" * 100)

    models = ["haiku", "gpt-5-nano", "gpt-5-mini"]
    disagreements = []  # (sample, dim, gt_val, {model: val})

    for sample_path in sample_files:
        name = sample_path.stem
        gt = ground_truth.get(name, {})
        print(f"\n--- {name} ---")

        for dim in DIMS:
            gt_val = gt.get(dim, "N/A")
            model_vals = {}
            any_disagree = False
            for model in models:
                val = all_results[model].get(name, {}).get(dim, "N/A")
                model_vals[model] = val
                if val != gt_val and val != "ERROR":
                    any_disagree = True

            marker = " *** DISAGREE ***" if any_disagree else ""
            print(f"  {dim}: GT={gt_val} | haiku={model_vals['haiku']} | nano={model_vals['gpt-5-nano']} | mini={model_vals['gpt-5-mini']}{marker}")

            if any_disagree:
                for model in models:
                    if model_vals[model] != gt_val and model_vals[model] != "ERROR":
                        disagreements.append({
                            "sample": name,
                            "dimension": dim,
                            "ground_truth": gt_val,
                            "model": model,
                            "model_value": model_vals[model],
                            "gt_reasoning": gt.get("reasoning", ""),
                            "model_reasoning": all_results[model].get(name, {}).get("reasoning", ""),
                        })

    # Summary
    print("\n" + "=" * 100)
    print("DISAGREEMENT SUMMARY")
    print("=" * 100)

    for model in models:
        model_disag = [d for d in disagreements if d["model"] == model]
        n_total = len(sample_files) * len(DIMS)
        n_errors = sum(1 for s in sample_files for d in DIMS if all_results[model].get(s.stem, {}).get(d) == "ERROR")
        n_agree = n_total - len(model_disag) - n_errors
        print(f"\n{model}: {n_agree}/{n_total} agree with GT ({len(model_disag)} disagree, {n_errors} errors)")
        for d in model_disag:
            print(f"  {d['sample']}.{d['dimension']}: GT={d['ground_truth']} model={d['model_value']}")

    # Save full comparison
    summary = {
        "n_samples": len(sample_files),
        "n_dimensions": len(DIMS),
        "disagreements": disagreements,
        "agreement_rates": {},
    }
    for model in models:
        model_disag = [d for d in disagreements if d["model"] == model]
        n_total = len(sample_files) * len(DIMS)
        n_errors = sum(1 for s in sample_files for d in DIMS if all_results[model].get(s.stem, {}).get(d) == "ERROR")
        summary["agreement_rates"][model] = {
            "agree": n_total - len(model_disag) - n_errors,
            "disagree": len(model_disag),
            "errors": n_errors,
            "total": n_total,
        }

    (RESULTS_DIR / "comparison_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nFull results saved to {RESULTS_DIR}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Reproduce exp007c: dose-response sweep for 4 missing organisms on 3 models.

Organisms: humor, loving, nonchalance, sarcasm
Models: Gemma 3 4B IT, Llama 3.1 8B Instruct, Qwen 2.5 7B Instruct
Doses: -2.0, -1.5, -1.0, -0.5, +0.5, +1.0, +1.5, +2.0

Usage:
    # 1. Start a vLLM server for each model (one at a time, single GPU):
    lrun -J vllm uv run amplified-vllm serve <model_id> --enable-lora --max-lora-rank 64 --port 8000 --gpu-memory-utilization 0.80

    # 2. Set up port forwarding:
    sforward <jobid>
    # or manual: ssh -fNL 8020:localhost:8000 l40-worker

    # 3. Run this script to verify existing results, or use amplification-run to regenerate:
    uv run python experiments/exp_007_multi_organism_dose/reproduce_exp007c.py

    # To regenerate (with server running):
    uv run amplification-run --prompts prompts/hallucination_probes/ \\
        --configs configs/persona_dose/ \\
        --model <model_config> --model-id <model_id> \\
        --url http://localhost:<port> \\
        --request-id exp007c_<model> \\
        --max-tokens 180 --temperature 1.0 -n 6 --include-base
"""

import os
import sys
import yaml
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

MODELS = {
    "gemma": {
        "model_config": "gemma3_4B_it",
        "model_id": "google/gemma-3-4b-it",
        "request_id": "exp007c_gemma",
    },
    "llama": {
        "model_config": "llama31_8B_Instruct",
        "model_id": "meta-llama/Llama-3.1-8B-Instruct",
        "request_id": "exp007c_llama",
    },
    "qwen": {
        "model_config": "qwen25_7B_Instruct",
        "model_id": "unsloth/Qwen2.5-7B-Instruct",
        "request_id": "exp007c_qwen",
    },
}

ORGANISMS = ["humor", "loving", "nonchalance", "sarcasm"]
DOSES = ["-2.0", "-1.5", "-1.0", "-0.5", "+0.5", "+1.0", "+1.5", "+2.0"]
EXPECTED_PROMPTS = 8
EXPECTED_CONFIGS = 33  # 32 dose configs + 1 base
EXPECTED_RESULTS = EXPECTED_PROMPTS * EXPECTED_CONFIGS  # 264
EXPECTED_SAMPLES = 6


def verify_results():
    """Verify that all expected result files exist and have correct structure."""
    all_ok = True

    for model_name, model_info in MODELS.items():
        request_id = model_info["request_id"]
        results_dir = PROJECT_ROOT / "logs" / "by_request" / request_id
        print(f"\n=== {model_name.upper()} ({request_id}) ===")

        if not results_dir.exists():
            print(f"  MISSING: {results_dir}")
            all_ok = False
            continue

        # Check summary
        summary_path = results_dir / "summary.yaml"
        if not summary_path.exists():
            print(f"  MISSING: summary.yaml")
            all_ok = False
            continue

        with open(summary_path) as f:
            summary = yaml.safe_load(f)

        print(f"  Model: {summary['model']} ({summary['model_id']})")
        print(f"  Configs: {summary['num_configs']}, Prompts: {summary['num_prompts']}")
        print(f"  Total results: {len(summary['results'])}")

        # Check result count
        n_results = len(summary["results"])
        if n_results != EXPECTED_RESULTS:
            print(f"  ERROR: Expected {EXPECTED_RESULTS} results, got {n_results}")
            all_ok = False

        # Check per-prompt file counts
        prompt_dirs = [d for d in results_dir.iterdir() if d.is_dir()]
        for pdir in sorted(prompt_dirs):
            yaml_files = [f for f in pdir.iterdir() if f.suffix == ".yaml" and "debug" not in f.name]
            n_files = len(yaml_files)
            expected = EXPECTED_CONFIGS
            status = "OK" if n_files == expected else f"ERROR (expected {expected})"
            print(f"  {pdir.name}: {n_files} configs - {status}")
            if n_files != expected:
                all_ok = False

        # Check completions count in a few results
        n_checked = 0
        n_correct = 0
        for r in summary["results"][:10]:
            n_comp = len(r["completions"])
            n_checked += 1
            if n_comp == EXPECTED_SAMPLES:
                n_correct += 1
        print(f"  Completions per result (spot check): {n_correct}/{n_checked} have {EXPECTED_SAMPLES} samples")

        # Show a sample output for each organism at +2.0
        print(f"\n  Sample outputs (identity_who, dose +2.0):")
        for r in summary["results"]:
            if r["prompt_name"] == "identity_who":
                for org in ORGANISMS:
                    if r["config_name"] == f"dose_{org}_pos2p0":
                        comp = r["completions"][0][:100]
                        print(f"    {org:15s}: {comp}...")

    return all_ok


def main():
    os.chdir(PROJECT_ROOT)
    print("Exp007c: Dose-response for humor, loving, nonchalance, sarcasm")
    print(f"Project root: {PROJECT_ROOT}")

    ok = verify_results()
    print(f"\n{'=' * 60}")
    if ok:
        print("All results verified successfully.")
    else:
        print("Some results are missing or incorrect. See above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

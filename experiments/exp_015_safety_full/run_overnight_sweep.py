#!/usr/bin/env python3
"""Run the full overnight safety sweep.

Three phases:
1. New persona vanilla (+1.0): 7 configs × 3 models
2. Scaling sweep (1.5x, 2.0x × 3 layer ranges): 66 configs × 3 models
3. Negation layerwise (-1.0 × 3 layer ranges): 33 configs × 3 models

Requires three vLLM servers on ports 8050 (Gemma), 8051 (Llama), 8052 (Qwen).
Uses --resume to skip already-completed experiments.
"""

import subprocess
import sys
import time

PORTS = {
    "gemma": 8050,
    "llama": 8051,
    "qwen": 8052,
}

MODELS = {
    "gemma": ("gemma3_4B_it", "google/gemma-3-4b-it"),
    "llama": ("llama31_8B_Instruct", "meta-llama/Llama-3.1-8B-Instruct"),
    "qwen": ("qwen25_7B_Instruct", "unsloth/Qwen2.5-7B-Instruct"),
}

EXP_DIR = "experiments/exp_015_safety_full"

PHASES = [
    ("new_personas", f"{EXP_DIR}/configs_new_personas", "exp15_newpersona"),
    ("scaling", f"{EXP_DIR}/configs_scaling", "exp15_scaling"),
    ("negation_layerwise", f"{EXP_DIR}/configs_negation_layerwise", "exp15_neg_lw"),
]


def run_phase(phase_name: str, configs_dir: str, request_prefix: str) -> dict[str, bool]:
    """Run one phase across all models. Returns {model: success}."""
    results = {}
    for model_key, (model_name, model_id) in MODELS.items():
        port = PORTS[model_key]
        request_id = f"{request_prefix}_{model_key}"
        cmd = [
            "uv", "run", "amplification-run",
            "--prompts", f"{EXP_DIR}/prompts",
            "--configs", configs_dir,
            "-m", model_name,
            "--model-id", model_id,
            "--url", f"http://localhost:{port}",
            "-n", "4",
            "--temperature", "0.7",
            "--max-tokens", "300",
            "--logs-dir", "logs",
            "--request-id", request_id,
            "--resume",
        ]
        print(f"\n{'='*60}")
        print(f"[{phase_name}] {model_key} — request_id={request_id}")
        print(f"{'='*60}")
        t0 = time.time()
        result = subprocess.run(cmd, text=True)
        elapsed = time.time() - t0
        ok = result.returncode == 0
        results[model_key] = ok
        status = "OK" if ok else "FAILED"
        print(f"[{phase_name}] {model_key} — {status} in {elapsed:.0f}s")
    return results


def main():
    all_results = {}
    for phase_name, configs_dir, request_prefix in PHASES:
        print(f"\n{'#'*60}")
        print(f"# PHASE: {phase_name}")
        print(f"# Configs: {configs_dir}")
        print(f"{'#'*60}")
        results = run_phase(phase_name, configs_dir, request_prefix)
        all_results[phase_name] = results

    print(f"\n{'#'*60}")
    print("# SUMMARY")
    print(f"{'#'*60}")
    for phase, results in all_results.items():
        for model, ok in results.items():
            status = "OK" if ok else "FAILED"
            print(f"  {phase}/{model}: {status}")

    total = sum(1 for r in all_results.values() for ok in r.values() if ok)
    failed = sum(1 for r in all_results.values() for ok in r.values() if not ok)
    print(f"\nTotal: {total} passed, {failed} failed")


if __name__ == "__main__":
    main()

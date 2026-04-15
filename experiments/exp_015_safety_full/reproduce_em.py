#!/usr/bin/env python3
"""Run EM organisms on safety prompts.

Same prompts as exp_015_safety_full, but with EM adapters at weights -2, -1, +1, +2.
Only Llama and Qwen (no Gemma — EM adapters don't exist for it).
"""

import subprocess
import sys

MODELS = [
    {
        "name": "llama",
        "model_name": "llama31_8B_Instruct",
        "model_id": "meta-llama/Llama-3.1-8B-Instruct",
        "url": "http://localhost:8056",
        "request_id": "exp15_em_llama",
    },
    {
        "name": "qwen",
        "model_name": "qwen25_7B_Instruct",
        "model_id": "unsloth/Qwen2.5-7B-Instruct",
        "url": "http://localhost:8057",
        "request_id": "exp15_em_qwen",
    },
]


def run_model(model: dict) -> None:
    """Run amplification-run for a single model."""
    cmd = [
        "uv", "run", "amplification-run",
        "--prompts", "experiments/exp_015_safety_full/prompts",
        "--configs", "experiments/exp_015_safety_full/configs_em",
        "-m", model["model_name"],
        "--model-id", model["model_id"],
        "--url", model["url"],
        "-n", "4",
        "--temperature", "0.7",
        "--max-tokens", "300",
        "--logs-dir", "logs",
        "--request-id", model["request_id"],
        "--resume",
    ]
    print(f"Running {model['name']}...")
    subprocess.run(cmd, check=True)
    print(f"Done: {model['name']}")


def main():
    for model in MODELS:
        run_model(model)
    print("\nAll models complete. Results in logs/by_request/exp15_em_{llama,qwen}/")


if __name__ == "__main__":
    main()

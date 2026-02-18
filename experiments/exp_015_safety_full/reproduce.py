#!/usr/bin/env python3
"""Reproduce key results from exp_015_safety_full.

Requires three vLLM servers running on the expected ports.
See report.md for full details.
"""

import subprocess
import sys

MODELS = [
    {
        "name": "gemma",
        "model_name": "gemma3_4B_it",
        "model_id": "google/gemma-3-4b-it",
        "url": "http://localhost:8050",
        "request_id": "exp15_gemma",
    },
    {
        "name": "llama",
        "model_name": "llama31_8B_Instruct",
        "model_id": "meta-llama/Llama-3.1-8B-Instruct",
        "url": "http://localhost:8051",
        "request_id": "exp15_llama",
    },
    {
        "name": "qwen",
        "model_name": "qwen25_7B_Instruct",
        "model_id": "unsloth/Qwen2.5-7B-Instruct",
        "url": "http://localhost:8052",
        "request_id": "exp15_qwen",
    },
]


def run_model(model: dict) -> None:
    """Run amplification-run for a single model."""
    cmd = [
        "uv", "run", "amplification-run",
        "--prompts", "experiments/exp_015_safety_full/prompts",
        "--configs", "experiments/exp_015_safety_full/configs",
        "-m", model["model_name"],
        "--model-id", model["model_id"],
        "--url", model["url"],
        "--include-base",
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
    print("\nAll models complete. Results in logs/by_request/exp15_{gemma,llama,qwen}/")


if __name__ == "__main__":
    main()

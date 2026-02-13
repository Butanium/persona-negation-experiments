#!/usr/bin/env python3
"""Reproduce exp008 phase 1 results: module type isolation (attention-only vs MLP-only negation).

Assumes a vLLM server is running with amplification support.

Usage:
    # Start server for each model, e.g.:
    lrun -J vllm_gemma uv run amplified-vllm serve google/gemma-3-4b-it \
        --enable-lora --max-lora-rank 64 --port 8000 --gpu-memory-utilization 0.80

    # Then run with the correct port and model:
    uv run reproduce_phase1.py --url http://localhost:PORT --model gemma
"""

import argparse
import subprocess
import sys

MODELS = {
    "gemma": {
        "config": "gemma3_4B_it",
        "model_id": "google/gemma-3-4b-it",
        "request_id": "exp008_phase1_gemma_repro",
    },
    "llama": {
        "config": "llama31_8B_Instruct",
        "model_id": "meta-llama/Llama-3.1-8B-Instruct",
        "request_id": "exp008_phase1_llama_repro",
    },
    "qwen": {
        "config": "qwen25_7B_Instruct",
        "model_id": "unsloth/Qwen2.5-7B-Instruct",
        "request_id": "exp008_phase1_qwen_repro",
    },
}


def main():
    parser = argparse.ArgumentParser(description="Reproduce exp008 phase 1")
    parser.add_argument("--url", required=True, help="vLLM server URL (e.g. http://localhost:8022)")
    parser.add_argument("--model", required=True, choices=MODELS.keys(), help="Model to run")
    args = parser.parse_args()

    m = MODELS[args.model]
    cmd = [
        "uv", "run", "amplification-run",
        "--prompts", "prompts/hallucination_probes/",
        "--configs", "configs/layerwise_phase1/",
        "--model", m["config"],
        "--model-id", m["model_id"],
        "--url", args.url,
        "--request-id", m["request_id"],
        "--max-tokens", "180",
        "--temperature", "1.0",
        "-n", "6",
        "--include-base",
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

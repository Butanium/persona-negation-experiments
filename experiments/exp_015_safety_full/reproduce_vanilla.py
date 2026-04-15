#!/usr/bin/env python3
"""Reproduce vanilla persona adapter safety evaluation.

Requires three vLLM servers running with amplification support.
See vanilla_data_collection_report.md for full details.

Server startup (one per GPU via SLURM):
    lrun -J vllm_gemma uv run amplified-vllm serve google/gemma-3-4b-it \
        --enable-lora --max-lora-rank 64 --port 8050 --gpu-memory-utilization 0.85 --max-model-len 2048
    lrun -J vllm_llama uv run amplified-vllm serve meta-llama/Llama-3.1-8B-Instruct \
        --enable-lora --max-lora-rank 64 --port 8051 --gpu-memory-utilization 0.85 --max-model-len 2048
    lrun -J vllm_qwen uv run amplified-vllm serve unsloth/Qwen2.5-7B-Instruct \
        --enable-lora --max-lora-rank 64 --port 8052 --gpu-memory-utilization 0.85 --max-model-len 2048

Then forward ports:
    sforward <gemma_jobid> 8050
    sforward <llama_jobid> 8051
    sforward <qwen_jobid> 8052

Adjust PORTS below to match sforward output.
"""

import subprocess
import sys

# Adjust these ports to match your sforward output
PORTS = {
    "gemma": 8053,
    "llama": 8054,
    "qwen": 8055,
}

MODELS = {
    "gemma": ("gemma3_4B_it", "google/gemma-3-4b-it"),
    "llama": ("llama31_8B_Instruct", "meta-llama/Llama-3.1-8B-Instruct"),
    "qwen": ("qwen25_7B_Instruct", "unsloth/Qwen2.5-7B-Instruct"),
}

EXP_DIR = "experiments/exp_015_safety_full"


def main():
    for model_key, (model_name, model_id) in MODELS.items():
        port = PORTS[model_key]
        request_id = f"exp15_vanilla_{model_key}"
        cmd = [
            "uv", "run", "amplification-run",
            "--prompts", f"{EXP_DIR}/prompts",
            "--configs", f"{EXP_DIR}/configs_vanilla",
            "-m", model_name,
            "--model-id", model_id,
            "--url", f"http://localhost:{port}",
            "--include-base",
            "-n", "4",
            "--temperature", "0.7",
            "--max-tokens", "300",
            "--logs-dir", "logs",
            "--request-id", request_id,
            "--resume",
        ]
        print(f"Running: {request_id}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  FAILED: {result.stderr[-200:]}", file=sys.stderr)
        else:
            print(f"  OK")

    print(
        "\nAll models complete. Results in logs/by_request/exp15_vanilla_{gemma,llama,qwen}/"
    )


if __name__ == "__main__":
    main()

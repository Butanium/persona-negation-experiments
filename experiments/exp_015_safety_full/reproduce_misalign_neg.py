#!/usr/bin/env python3
"""Reproduce misalignment adapter negation safety evaluation.

Requires three vLLM servers running with amplification support.
See misalign_neg_report.md for full details.

Server startup (one per GPU via SLURM):
    lrun -J vllm-gemma --time 01:00:00 bash -c 'PYTHONUNBUFFERED=1 uv run amplified-vllm serve google/gemma-3-4b-it \
        --enable-lora --max-lora-rank 64 --port 8050 --gpu-memory-utilization 0.70 --max-model-len 2048 --max-num-seqs 64'
    lrun -J vllm-llama --time 01:00:00 bash -c 'PYTHONUNBUFFERED=1 uv run amplified-vllm serve meta-llama/Llama-3.1-8B-Instruct \
        --enable-lora --max-lora-rank 64 --port 8051 --gpu-memory-utilization 0.70 --max-model-len 2048 --max-num-seqs 64'
    lrun -J vllm-qwen --time 01:00:00 bash -c 'PYTHONUNBUFFERED=1 uv run amplified-vllm serve unsloth/Qwen2.5-7B-Instruct \
        --enable-lora --max-lora-rank 64 --port 8052 --gpu-memory-utilization 0.70 --max-model-len 2048 --max-num-seqs 64'

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
    "gemma": 8062,
    "llama": 8063,
    "qwen": 8064,
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
        request_id = f"exp15_misalign_neg_{model_key}"
        cmd = [
            "uv", "run", "amplification-run",
            "--prompts", f"{EXP_DIR}/prompts",
            "--configs", f"{EXP_DIR}/configs_misalign_neg",
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
        print(f"Running: {request_id}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  FAILED: {result.stderr[-200:]}", file=sys.stderr)
        else:
            print(f"  OK")

    print(
        "\nAll models complete. Results in logs/by_request/exp15_misalign_neg_{gemma,llama,qwen}/"
    )
    print("\nTo judge:")
    print("  uv run experiments/exp_015_safety_full/judging/prepare_misalign_neg_batches.py")
    print("  unset CLAUDECODE ANTHROPIC_API_KEY")
    print("  uv run judgments/v2_cli_qwen/run_judges.py --base-dir experiments/exp_015_safety_full/judging/misalign_neg_batches --max-parallel 15")
    print("\nTo aggregate:")
    print("  uv run experiments/exp_015_safety_full/judging/aggregate_all.py")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Reproduce key results from Exp 15: Safety Surface Derisk.

Prerequisites:
  - 3 vLLM servers running on GPU with amplification support
  - Port forwarding set up (adjust PORTS below to match your setup)

Usage:
  uv run reproduce.py
"""

import subprocess
import sys

# Adjust these ports to match your sforward output
PORTS = {
    "gemma": 8041,
    "llama": 8042,
    "qwen": 8043,
}

MODELS = {
    "gemma": ("gemma3_4B_it", "google/gemma-3-4b-it"),
    "llama": ("llama31_8B_Instruct", "meta-llama/Llama-3.1-8B-Instruct"),
    "qwen": ("qwen25_7B_Instruct", "unsloth/Qwen2.5-7B-Instruct"),
}

EXP_DIR = "experiments/exp_015_safety_derisk"


def main():
    for model_key, (model_name, model_id) in MODELS.items():
        port = PORTS[model_key]
        request_id = f"exp15_{model_key}"
        cmd = [
            "uv", "run", "amplification-run",
            "--prompts", f"{EXP_DIR}/prompts/",
            "--configs", f"{EXP_DIR}/configs/",
            "--model", model_name,
            "--model-id", model_id,
            "--url", f"http://localhost:{port}",
            "--include-base",
            "--temperature", "1.0",
            "--max-tokens", "300",
            "-n", "2",
            "--request-id", request_id,
            "--logs-dir", "logs",
        ]
        print(f"Running: {request_id}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  FAILED: {result.stderr[-200:]}", file=sys.stderr)
        else:
            print(f"  OK")


if __name__ == "__main__":
    main()

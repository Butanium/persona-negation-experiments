#!/usr/bin/env python3
"""Reproduce key results from Exp A: System Prompt Reinforcement Derisk.

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

EXP_DIR = "experiments/exp_a_sysprompt_derisk"

RUNS = [
    # (model_key, prompts_dir, configs_dir, include_base, request_id_suffix)
    ("goodness_nosys", "prompts_no_sys", "configs_goodness", True),
    ("goodness_sys", "prompts_with_sys", "configs_goodness", False),
    ("sarcasm_nosys", "prompts_no_sys", "configs_sarcasm", False),
    ("sarcasm_sys", "prompts_with_sys", "configs_sarcasm", False),
]


def main():
    for model_key, (model_name, model_id) in MODELS.items():
        port = PORTS[model_key]
        for run_suffix, prompts, configs, include_base in RUNS:
            request_id = f"exp_a_{model_key}_{run_suffix}"
            cmd = [
                "uv", "run", "amplification-run",
                "--prompts", f"{EXP_DIR}/{prompts}/",
                "--configs", f"{EXP_DIR}/{configs}/",
                "--model", model_name,
                "--model-id", model_id,
                "--url", f"http://localhost:{port}",
                "--temperature", "1.0",
                "--max-tokens", "180",
                "-n", "2",
                "--request-id", request_id,
                "--logs-dir", "logs",
            ]
            if include_base:
                cmd.append("--include-base")
            print(f"Running: {request_id}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  FAILED: {result.stderr[-200:]}", file=sys.stderr)
            else:
                print(f"  OK")


if __name__ == "__main__":
    main()

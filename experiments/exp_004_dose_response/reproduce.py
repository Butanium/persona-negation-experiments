#!/usr/bin/env python3
"""Reproduce key results from exp_004_dose_response.

Runs the dose-response sweep for persona_goodness across weights
[-2.0, -1.5, -1.0, -0.5, 0.5, 1.0, 1.5, 2.0] on Llama 3.1 8B Instruct
and Qwen 2.5 7B Instruct.

Prerequisites:
  - amplified-vllm servers running (default: Llama on 8001, Qwen on 8002)
  - Port forwarding set up if running on compute node

Usage:
  uv run reproduce.py
"""

import subprocess
import sys


MODELS = [
    ("llama31_8B_Instruct", "meta-llama/Llama-3.1-8B-Instruct", "http://localhost:8001"),
    ("qwen25_7B_Instruct", "unsloth/Qwen2.5-7B-Instruct", "http://localhost:8002"),
]

CONFIGS_DIR = "../../configs/persona_dose/"
PROMPTS_DIR = "../../prompts/hallucination_probes/"


def main():
    for model_name, model_id, url in MODELS:
        print(f"\n{'='*60}")
        print(f"Running dose-response sweep on {model_name}")
        print(f"{'='*60}\n")

        cmd = [
            "uv", "run", "amplification-run",
            "--prompts", PROMPTS_DIR,
            "--configs", CONFIGS_DIR,
            "--model", model_name,
            "--model-id", model_id,
            "--url", url,
            "--include-base",
            "--max-tokens", "180",
            "--temperature", "1.0",
            "-n", "6",
            "--request-id", f"exp004_repro_{model_name}",
        ]

        print(f"Command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        if result.returncode != 0:
            print(f"FAILED for {model_name}", file=sys.stderr)
            sys.exit(1)

    print("\nDone. Results in logs/by_request/exp004_*/")


if __name__ == "__main__":
    main()

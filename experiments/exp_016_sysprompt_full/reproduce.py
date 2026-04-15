#!/usr/bin/env python3
"""Reproduce data collection for Exp 16: System Prompt Reinforcement.

Requires 3 vLLM servers running on ports 8050 (Gemma), 8051 (Llama), 8052 (Qwen).
Generates all prompt/config files and runs amplification-run for each condition.
"""

import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent

MODELS = [
    ("gemma3_4B_it", "google/gemma-3-4b-it", "http://localhost:8050"),
    ("llama31_8B_Instruct", "meta-llama/Llama-3.1-8B-Instruct", "http://localhost:8051"),
    ("qwen25_7B_Instruct", "unsloth/Qwen2.5-7B-Instruct", "http://localhost:8052"),
]

MODEL_SHORT = {
    "gemma3_4B_it": "gemma",
    "llama31_8B_Instruct": "llama",
    "qwen25_7B_Instruct": "qwen",
}

SYSPROMPT_CONDITIONS = [
    ("nosys", "prompts_nosys", True),
    ("sys_strong", "prompts_sys_strong", False),
    ("sys_gentle", "prompts_sys_gentle", False),
    ("sys_neutral", "prompts_sys_neutral", False),
]


def run_cmd(cmd: list[str]) -> None:
    """Run a command and fail on error."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=True)
    assert result.returncode == 0


def main():
    # Step 1: Generate files
    print("=== Generating prompt and config files ===")
    run_cmd(["uv", "run", "python", str(BASE / "scratch" / "generate_files.py")])

    # Step 2: Run experiments
    for model_name, model_id, url in MODELS:
        short = MODEL_SHORT[model_name]
        for condition, prompts_dir, include_base in SYSPROMPT_CONDITIONS:
            request_id = f"exp16_{short}_{condition}"
            cmd = [
                "uv", "run", "amplification-run",
                "--prompts", str(BASE / prompts_dir),
                "--configs", str(BASE / "configs"),
                "--model", model_name,
                "--model-id", model_id,
                "--url", url,
                "--temperature", "1.0",
                "--max-tokens", "200",
                "-n", "4",
                "--request-id", request_id,
                "--logs-dir", "logs",
            ]
            if include_base:
                cmd.append("--include-base")

            print(f"\n=== {request_id} ===")
            run_cmd(cmd)

    print("\n=== All runs complete ===")


if __name__ == "__main__":
    main()

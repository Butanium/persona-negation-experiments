#!/usr/bin/env python3
"""Reproduce exp007b: Llama 3.1 8B Instruct dose-response for poeticism and mathematical organisms.

Prerequisites:
  1. vLLM server running Llama 3.1 8B Instruct with LoRA enabled:
     lrun -J vllm_ampl_llama_b uv run amplified-vllm serve meta-llama/Llama-3.1-8B-Instruct \
       --enable-lora --max-lora-rank 64 --port 8000 --gpu-memory-utilization 0.80

  2. Port forwarded: sforward <JOBID> 8000
     Check sforward output for the actual local port.

  3. Set VLLM_PORT environment variable to the forwarded port (or defaults to 8014).
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def create_filtered_config_dir():
    """Create a temp directory with symlinks to only poeticism and mathematical dose configs."""
    configs_dir = PROJECT_ROOT / "configs" / "persona_dose"
    tmpdir = Path(tempfile.mkdtemp(prefix="exp007b_configs_"))
    for f in configs_dir.glob("dose_poeticism_*.yaml"):
        (tmpdir / f.name).symlink_to(f)
    for f in configs_dir.glob("dose_mathematical_*.yaml"):
        (tmpdir / f.name).symlink_to(f)
    return tmpdir


def main():
    port = os.environ.get("VLLM_PORT", "8014")
    base_url = f"http://localhost:{port}"
    request_id = "exp007b_llama_repro"

    config_dir = create_filtered_config_dir()
    print(f"Using config dir: {config_dir}")
    print(f"Using vLLM at: {base_url}")

    # Run dose configs
    cmd_dose = [
        "uv", "run", "amplification-run",
        "--prompts", str(PROJECT_ROOT / "prompts" / "hallucination_probes"),
        "--configs", str(config_dir),
        "--model", "llama31_8B_Instruct",
        "--model-id", "meta-llama/Llama-3.1-8B-Instruct",
        "--url", base_url,
        "--request-id", request_id,
        "--temperature", "1.0",
        "--max-tokens", "180",
        "-n", "6",
    ]
    print(f"\n--- Running dose sweep (16 configs x 8 prompts) ---")
    print(f"Command: {' '.join(cmd_dose)}")
    result = subprocess.run(cmd_dose, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"Dose sweep failed with return code {result.returncode}")
        sys.exit(1)

    # Run base config
    cmd_base = [
        "uv", "run", "amplification-run",
        "--prompts", str(PROJECT_ROOT / "prompts" / "hallucination_probes"),
        "--model", "llama31_8B_Instruct",
        "--model-id", "meta-llama/Llama-3.1-8B-Instruct",
        "--url", base_url,
        "--request-id", request_id,
        "--temperature", "1.0",
        "--max-tokens", "180",
        "-n", "6",
        "--include-base",
    ]
    print(f"\n--- Running base sweep (1 config x 8 prompts) ---")
    print(f"Command: {' '.join(cmd_base)}")
    result = subprocess.run(cmd_base, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"Base sweep failed with return code {result.returncode}")
        sys.exit(1)

    print(f"\nResults written to: logs/by_request/{request_id}/")
    print("Expected: 136 result files + 136 debug files")


if __name__ == "__main__":
    main()

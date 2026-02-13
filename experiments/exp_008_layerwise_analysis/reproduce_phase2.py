#!/usr/bin/env python3
"""Reproduce exp008 phase 2 results: layer quartile isolation (Q1--Q4 negation at -1.0x).

Assumes an amplified-vllm server is running with LoRA support.

Usage:
    # Start server for each model, e.g.:
    lrun -J vllm_gemma uv run amplified-vllm serve google/gemma-3-4b-it \
        --enable-lora --max-lora-rank 64 --port 8000 --gpu-memory-utilization 0.80

    # Then run with the correct port and model:
    uv run reproduce_phase2.py --url http://localhost:PORT --model gemma
"""

import argparse
import subprocess
import sys
import tempfile
import os
from pathlib import Path

MODELS = {
    "gemma": {
        "config": "gemma3_4B_it",
        "model_id": "google/gemma-3-4b-it",
        "request_id": "exp008_phase2_gemma_repro",
    },
    "llama": {
        "config": "llama31_8B_Instruct",
        "model_id": "meta-llama/Llama-3.1-8B-Instruct",
        "request_id": "exp008_phase2_llama_repro",
    },
    "qwen": {
        "config": "qwen25_7B_Instruct",
        "model_id": "unsloth/Qwen2.5-7B-Instruct",
        "request_id": "exp008_phase2_qwen_repro",
    },
}

QUARTILE_CONFIGS = [
    "goodness_q1_neg1p0.yaml",
    "goodness_q2_neg1p0.yaml",
    "goodness_q3_neg1p0.yaml",
    "goodness_q4_neg1p0.yaml",
]


def main():
    parser = argparse.ArgumentParser(description="Reproduce exp008 phase 2")
    parser.add_argument("--url", required=True, help="vLLM server URL (e.g. http://localhost:8022)")
    parser.add_argument("--model", required=True, choices=MODELS.keys(), help="Model to run")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    configs_dir = project_root / "configs" / "layerwise"

    # Create temp dir with only Q1-Q4 configs (exclude phase1 configs in same dir)
    tmpdir = tempfile.mkdtemp(prefix="exp008p2_")
    for cfg in QUARTILE_CONFIGS:
        src = configs_dir / cfg
        assert src.exists(), f"Config not found: {src}"
        os.symlink(src, Path(tmpdir) / cfg)

    m = MODELS[args.model]
    cmd = [
        "uv", "run", "amplification-run",
        "--prompts", str(project_root / "prompts" / "hallucination_probes"),
        "--configs", tmpdir,
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

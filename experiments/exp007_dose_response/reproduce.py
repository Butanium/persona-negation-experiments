#!/usr/bin/env python3
"""Reproduce key results from exp007: dose-response sweep.

Requires: a running vLLM server with Llama 3.1 8B Instruct and amplification support.

Usage:
    uv run reproduce.py --url http://localhost:PORT
"""
import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description="Reproduce exp007 dose-response sweep")
    parser.add_argument("--url", required=True, help="vLLM server URL (e.g. http://localhost:8005)")
    args = parser.parse_args()

    configs_dir = PROJECT_ROOT / "configs" / "persona_dose"
    target_configs = [
        f"dose_{org}_{dose}.yaml"
        for org in ["remorse", "sycophancy", "impulsiveness"]
        for dose in ["neg2p0", "neg1p5", "neg1p0", "neg0p5", "pos0p5", "pos1p0", "pos1p5", "pos2p0"]
    ]

    # Verify all configs exist
    for cfg in target_configs:
        assert (configs_dir / cfg).exists(), f"Missing config: {cfg}"

    # Create a temporary config directory with only the needed configs
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        for cfg in target_configs:
            (Path(tmpdir) / cfg).symlink_to(configs_dir / cfg)

        cmd = [
            "uv", "run", "amplification-run",
            "--prompts", str(PROJECT_ROOT / "prompts" / "hallucination_probes"),
            "--configs", tmpdir,
            "--model", "llama31_8B_Instruct",
            "--model-id", "meta-llama/Llama-3.1-8B-Instruct",
            "--url", args.url,
            "--include-base",
            "--temperature", "1.0",
            "--max-tokens", "180",
            "-n", "6",
            "--request-id", "exp007_llama_repro",
        ]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()

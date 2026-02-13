#!/usr/bin/env python3
"""Reproduce key results from exp007b_gemma: poeticism & mathematical dose-response on Gemma 3 4B IT.

Usage:
    uv run reproduce_gemma.py

This reads the collected data and prints dose-response tables showing
how output style changes with organism amplification weight.
"""

import yaml
from pathlib import Path


LOGS_BASE = Path("logs/by_prompt")
ORGANISMS = ["mathematical", "poeticism"]
DOSES = ["neg2p0", "neg1p5", "neg1p0", "neg0p5", "pos0p5", "pos1p0", "pos1p5", "pos2p0"]
DOSE_LABELS = {
    "neg2p0": "-2.0", "neg1p5": "-1.5", "neg1p0": "-1.0", "neg0p5": "-0.5",
    "pos0p5": "+0.5", "pos1p0": "+1.0", "pos1p5": "+1.5", "pos2p0": "+2.0",
}
MODEL = "gemma3_4B_it"


def load_latest(prompt_dir: str, config: str) -> dict:
    """Load the most recent result file for a prompt/config/model combination."""
    gemma_dir = LOGS_BASE / prompt_dir / config / MODEL
    assert gemma_dir.exists(), f"Missing: {gemma_dir}"
    files = [f for f in gemma_dir.iterdir() if f.suffix == ".yaml" and "debug" not in f.name]
    assert files, f"No result files in {gemma_dir}"
    latest = max(files, key=lambda f: f.stat().st_mtime)
    data = yaml.safe_load(latest.read_text())
    assert "completions" in data, f"No completions in {latest}"
    return data


def main():
    prompts = sorted([d.name for d in LOGS_BASE.iterdir() if d.is_dir()])
    print(f"Found {len(prompts)} prompts")
    print()

    for organism in ORGANISMS:
        print(f"{'='*80}")
        print(f"ORGANISM: {organism}")
        print(f"{'='*80}")

        for prompt_dir in prompts:
            print(f"\n--- {prompt_dir} ---")

            # Base
            base_data = load_latest(prompt_dir, "base")
            print(f"  {'base':>5}: {base_data['completions'][0][:100]!r}")

            # Doses
            for dose in DOSES:
                config = f"dose_{organism}_{dose}"
                data = load_latest(prompt_dir, config)
                label = DOSE_LABELS[dose]
                print(f"  {label:>5}: {data['completions'][0][:100]!r}")

        print()

    # Summary stats
    print(f"\n{'='*80}")
    print("DATA SUMMARY")
    print(f"{'='*80}")
    total_files = 0
    total_completions = 0
    configs = ["base"] + [f"dose_{org}_{dose}" for org in ORGANISMS for dose in DOSES]
    for prompt_dir in prompts:
        for config in configs:
            data = load_latest(prompt_dir, config)
            total_files += 1
            total_completions += len(data["completions"])
    print(f"Total result files: {total_files}")
    print(f"Total completions: {total_completions}")
    print(f"Prompts: {len(prompts)}")
    print(f"Configs per prompt: {len(configs)} (1 base + {len(DOSES)} doses x {len(ORGANISMS)} organisms)")
    print(f"Samples per config: 6")


if __name__ == "__main__":
    main()

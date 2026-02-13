#!/usr/bin/env python3
"""Reproduce the key comparative observations from Q1-only vs full negation analysis.

Loads completions from summary.yaml files and prints them side-by-side
for the prompts that show the biggest divergence (env_describe, roommate, identity_who, env_breakfast).
"""

import yaml
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path("/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp")

SUMMARY_FILES = {
    "exp008_phase2": PROJECT_ROOT / "logs/by_request/exp008_phase2_llama/summary.yaml",
    "exp004": PROJECT_ROOT / "logs/by_request/exp004_llama/summary.yaml",
}

TARGET_PROMPTS = ["env_describe", "roommate", "identity_who", "env_breakfast"]

TARGET_CONFIGS = {
    "exp008_phase2": {"base", "goodness_q1_neg1p0"},
    "exp004": {"dose_goodness_neg1p0"},
}


def load_completions(filepath: Path, target_configs: set, target_prompts: list) -> dict:
    """Load completions from summary.yaml, filtering by config and prompt.

    Returns dict of (config_name, prompt_name) -> list[str].
    """
    with open(filepath) as f:
        data = yaml.safe_load(f)

    results = defaultdict(list)
    for entry in data["results"]:
        config = entry["config_name"]
        prompt = entry["prompt_name"]
        if config in target_configs and prompt in target_prompts:
            results[(config, prompt)] = entry["completions"]

    return dict(results)


def print_condition(label: str, completions: list[str], max_samples: int = 3):
    """Print completions for a condition."""
    print(f"\n  --- {label} ({len(completions)} total, showing {min(max_samples, len(completions))}) ---")
    for i, c in enumerate(completions[:max_samples]):
        text = c[:300].replace("\n", " ").strip()
        if len(c) > 300:
            text += "..."
        print(f"    [{i}] {text}")


def main():
    print("=" * 80)
    print("Q1-ONLY vs FULL NEGATION vs BASE: Key Outputs (Llama 3.1 8B Instruct)")
    print("=" * 80)

    # Load data
    exp008_data = load_completions(
        SUMMARY_FILES["exp008_phase2"],
        TARGET_CONFIGS["exp008_phase2"],
        TARGET_PROMPTS,
    )
    exp004_data = load_completions(
        SUMMARY_FILES["exp004"],
        TARGET_CONFIGS["exp004"],
        TARGET_PROMPTS,
    )

    for prompt in TARGET_PROMPTS:
        print(f"\n{'=' * 80}")
        print(f"PROMPT: {prompt}")
        print("=" * 80)

        base = exp008_data.get(("base", prompt), [])
        q1 = exp008_data.get(("goodness_q1_neg1p0", prompt), [])
        full_neg = exp004_data.get(("dose_goodness_neg1p0", prompt), [])

        print_condition("BASE", base)
        print_condition("Q1-ONLY (-1.0x, early layers)", q1)
        print_condition("FULL NEGATION (-1.0x, all layers)", full_neg)

    # Summary stats
    print(f"\n{'=' * 80}")
    print("QUANTITATIVE SUMMARY (from judged data)")
    print("=" * 80)
    print("""
    Condition                | not_ai%  | coherence | fabrication%
    -------------------------|----------|-----------|-------------
    Base                     | 16.67%   | 4.71      | 16.67%
    Q1-only (-1.0x)          | 50.00%   | 4.81      | 41.67%
    Full neg (-1.0x, poet.)  | 25.00%   | 4.40      | 25.00%

    Key: Q1-only achieves DOUBLE the not_ai rate of full negation,
    while maintaining HIGHER coherence. The effect is concentrated
    on env_describe (83% vs 0%) and env_anti_example (50% vs 0%).
    """)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Reproduce key results from exp_007b: dose-response sweep on Gemma 3 4B IT
for poeticism and mathematical organisms.

Reads raw completion files and prints a dose-response summary table.
"""

import yaml
from pathlib import Path
from collections import defaultdict

LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs" / "by_prompt"
PROMPTS = [
    "env_anti_example", "env_breakfast", "env_commitment", "env_describe",
    "env_one_sentence", "identity_what", "identity_who", "roommate",
]
ORGANISMS = ["poeticism", "mathematical"]
DOSES = [
    ("neg2p0", -2.0), ("neg1p5", -1.5), ("neg1p0", -1.0), ("neg0p5", -0.5),
    ("base", 0.0),
    ("pos0p5", 0.5), ("pos1p0", 1.0), ("pos1p5", 1.5), ("pos2p0", 2.0),
]
MODEL = "gemma3_4B_it"


def find_latest_result(prompt_dir: Path, config_name: str) -> Path | None:
    """Find the most recent non-debug YAML for a given prompt+config."""
    config_dir = prompt_dir / config_name / MODEL
    if not config_dir.exists():
        return None
    yamls = sorted(
        [f for f in config_dir.iterdir() if f.suffix == ".yaml" and "debug" not in f.name],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return yamls[0] if yamls else None


def load_completions(path: Path) -> list[str]:
    """Load completions from a result YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return data["completions"]


def avg_completion_length(completions: list[str]) -> float:
    """Average character length of completions."""
    return sum(len(c) for c in completions) / len(completions)


def main():
    # Find prompt directories (they have hash suffixes)
    prompt_dirs = {}
    for p in LOGS_DIR.iterdir():
        for prompt_name in PROMPTS:
            if p.name.startswith(prompt_name + "_"):
                prompt_dirs[prompt_name] = p

    print("=" * 80)
    print("Exp 007b: Dose-Response Sweep on Gemma 3 4B IT")
    print("Organisms: poeticism, mathematical")
    print("=" * 80)

    for organism in ORGANISMS:
        print(f"\n{'=' * 60}")
        print(f"Organism: {organism}")
        print(f"{'=' * 60}")
        print(f"{'Dose':>8s} | {'Avg Len':>8s} | Sample completion (first 100 chars)")
        print("-" * 80)

        for dose_label, dose_val in DOSES:
            if dose_label == "base":
                config_name = "base"
            else:
                config_name = f"dose_{organism}_{dose_label}"

            lengths = []
            sample_completion = ""
            for prompt_name, prompt_dir in sorted(prompt_dirs.items()):
                result_path = find_latest_result(prompt_dir, config_name)
                if result_path is None:
                    continue
                completions = load_completions(result_path)
                lengths.extend(len(c) for c in completions)
                if not sample_completion and completions:
                    sample_completion = completions[0]

            if lengths:
                avg_len = sum(lengths) / len(lengths)
                print(f"{dose_val:>8.1f} | {avg_len:>8.1f} | {sample_completion[:100]}")
            else:
                print(f"{dose_val:>8.1f} | {'N/A':>8s} | (no data)")

    # Detailed verbatim output for key probes
    print("\n\n" + "=" * 80)
    print("VERBATIM SAMPLES: identity_what prompt")
    print("=" * 80)

    if "identity_what" not in prompt_dirs:
        print("identity_what prompt not found")
        return

    prompt_dir = prompt_dirs["identity_what"]
    for organism in ORGANISMS:
        print(f"\n--- {organism} ---")
        for dose_label, dose_val in DOSES:
            if dose_label == "base":
                config_name = "base"
            else:
                config_name = f"dose_{organism}_{dose_label}"

            result_path = find_latest_result(prompt_dir, config_name)
            if result_path is None:
                continue
            completions = load_completions(result_path)
            print(f"\n  [{dose_val:+.1f}] {completions[0][:200]}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Extract individual samples from exp005 summary YAML files into text files for LLM judging."""

import math
import os
import re
from pathlib import Path

import yaml

BASE = Path("/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp")
JUDGING_DIR = BASE / "experiments" / "exp_005_em_negative" / "judging"
SUMMARIES = {
    "llama": BASE / "logs" / "by_request" / "exp005_llama" / "summary.yaml",
    "qwen": BASE / "logs" / "by_request" / "exp005_qwen" / "summary.yaml",
}
BATCH_SIZE = 15


def get_prompt_text(main_file_rel: str) -> str:
    """Read prompt text from the individual log file."""
    main_file = BASE / main_file_rel
    with open(main_file) as f:
        data = yaml.safe_load(f)
    return data["prompt"]


def get_prompt_hash(main_file_rel: str) -> str:
    """Extract prompt hash from the directory path (e.g. env_breakfast_0249df74 -> 0249df74)."""
    match = re.search(r"by_prompt/\w+_([0-9a-f]{8})/", main_file_rel)
    assert match, f"Could not extract hash from {main_file_rel}"
    return match.group(1)


def extract_all_samples():
    """Extract all completions from both models into individual text files."""
    all_samples = []
    prompt_cache = {}

    for model_short, summary_path in SUMMARIES.items():
        with open(summary_path) as f:
            data = yaml.safe_load(f)

        for entry in data["results"]:
            if "error" in entry:
                continue

            config_name = entry["config_name"]
            prompt_name = entry["prompt_name"]
            main_file_rel = entry["main_file"]

            prompt_hash = get_prompt_hash(main_file_rel)

            cache_key = (prompt_name, prompt_hash)
            if cache_key not in prompt_cache:
                prompt_cache[cache_key] = get_prompt_text(main_file_rel)
            prompt_text = prompt_cache[cache_key]

            for idx, completion in enumerate(entry["completions"]):
                filename = f"exp005_{model_short}__{prompt_name}_{prompt_hash}__{config_name}__{idx}.txt"
                content = (
                    f"PROMPT: {prompt_text}\n"
                    f"MODEL: {model_short}\n"
                    f"CONFIG: {config_name}\n"
                    f"---\n"
                    f"RESPONSE:\n{completion}\n"
                )
                all_samples.append((filename, content))

    return all_samples


def distribute_to_batches(samples, batch_size):
    """Split samples across batches of given size."""
    n_batches = math.ceil(len(samples) / batch_size)
    batches = [[] for _ in range(n_batches)]
    for i, sample in enumerate(samples):
        batches[i % n_batches].append(sample)
    return batches


def main():
    import shutil

    # Clean old batches if any
    if JUDGING_DIR.exists():
        for batch_dir in JUDGING_DIR.glob("batch_*"):
            shutil.rmtree(batch_dir)

    samples = extract_all_samples()
    print(f"Total samples extracted: {len(samples)}")

    batches = distribute_to_batches(samples, BATCH_SIZE)
    print(f"Number of batches: {len(batches)}")

    for batch_idx, batch in enumerate(batches):
        batch_name = f"batch_{batch_idx + 1:03d}"
        batch_dir = JUDGING_DIR / batch_name
        samples_dir = batch_dir / "samples"
        judgments_dir = batch_dir / "judgments"

        samples_dir.mkdir(parents=True, exist_ok=True)
        judgments_dir.mkdir(parents=True, exist_ok=True)

        # Symlink criteria.md as CLAUDE.md
        claude_md = batch_dir / "CLAUDE.md"
        if not claude_md.exists():
            os.symlink("../criteria.md", str(claude_md))

        for filename, content in batch:
            (samples_dir / filename).write_text(content)

        print(f"  {batch_name}: {len(batch)} samples")

    print(f"\nDone. Batches created in {JUDGING_DIR}")


if __name__ == "__main__":
    main()

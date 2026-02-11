#!/usr/bin/env python3
"""Create judging batches for exp004_gemma completions."""

import yaml
import os
from pathlib import Path

BASE = Path("/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp")
LOGS_DIR = BASE / "logs/by_prompt"
JUDGING_DIR = BASE / "experiments/exp_004_dose_response/judging"
REQUEST_DIR = BASE / "logs/by_request/exp004_gemma"

SAMPLES_PER_BATCH = 15
FIRST_BATCH = 59  # batches 001-058 exist for llama/qwen

# Collect all samples
samples = []

for prompt_dir in sorted(REQUEST_DIR.iterdir()):
    if not prompt_dir.is_dir():
        continue
    prompt_name = prompt_dir.name

    for config_file in sorted(prompt_dir.iterdir()):
        if config_file.name.endswith(".debug.yaml") or not config_file.name.endswith(".yaml"):
            continue

        # Read the symlink target's actual file
        target = config_file.resolve() if config_file.is_symlink() else config_file
        # Since resolve fails on broken symlinks, read via the link path using os
        link_target = os.readlink(str(config_file))
        actual_path = BASE / link_target

        with open(actual_path) as f:
            data = yaml.safe_load(f)

        config_name = config_file.stem  # e.g. "base", "dose_goodness_neg0p5"
        prompt_text = data["prompt"]
        completions = data["completions"]

        for i, completion in enumerate(completions):
            sample_name = f"exp004_gemma__{prompt_name}__{config_name}__{i}"
            sample_content = f"Prompt: {prompt_text}\n\nResponse: {completion}"
            samples.append((sample_name, sample_content))

print(f"Total samples: {len(samples)}")

# Create batches
num_batches = (len(samples) + SAMPLES_PER_BATCH - 1) // SAMPLES_PER_BATCH
print(f"Creating {num_batches} batches (batch_{FIRST_BATCH:03d} to batch_{FIRST_BATCH + num_batches - 1:03d})")

for batch_idx in range(num_batches):
    batch_num = FIRST_BATCH + batch_idx
    batch_dir = JUDGING_DIR / f"batch_{batch_num:03d}"
    samples_dir = batch_dir / "samples"
    judgments_dir = batch_dir / "judgments"

    samples_dir.mkdir(parents=True, exist_ok=True)
    judgments_dir.mkdir(parents=True, exist_ok=True)

    # Symlink CLAUDE.md -> ../criteria.md
    claude_md = batch_dir / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.symlink_to("../criteria.md")

    batch_samples = samples[batch_idx * SAMPLES_PER_BATCH : (batch_idx + 1) * SAMPLES_PER_BATCH]
    for sample_name, sample_content in batch_samples:
        sample_file = samples_dir / f"{sample_name}.txt"
        sample_file.write_text(sample_content)

    print(f"  batch_{batch_num:03d}: {len(batch_samples)} samples")

print("Done.")

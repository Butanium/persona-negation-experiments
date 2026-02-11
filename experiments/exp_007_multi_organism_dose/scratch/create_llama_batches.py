#!/usr/bin/env python3
"""Create judging batches for exp007_llama completions."""

import yaml
import os
from pathlib import Path

BASE = Path("/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp")
REQUEST_DIR = BASE / "logs/by_request/exp007_llama"
JUDGING_DIR = BASE / "experiments/exp_007_multi_organism_dose/judging"

SAMPLES_PER_BATCH = 15
FIRST_BATCH = 1

samples = []

for prompt_dir in sorted(REQUEST_DIR.iterdir()):
    if not prompt_dir.is_dir():
        continue
    prompt_name = prompt_dir.name

    for config_file in sorted(prompt_dir.iterdir()):
        if config_file.name.endswith(".debug.yaml") or not config_file.name.endswith(".yaml"):
            continue

        link_target = os.readlink(str(config_file))
        actual_path = BASE / link_target

        with open(actual_path) as f:
            data = yaml.safe_load(f)

        config_name = config_file.stem
        prompt_text = data["prompt"]
        completions = data["completions"]

        for i, completion in enumerate(completions):
            sample_name = f"exp007_llama__{prompt_name}__{config_name}__{i}"
            sample_content = f"Prompt: {prompt_text}\n\nResponse: {completion}"
            samples.append((sample_name, sample_content))

print(f"Total samples: {len(samples)}")

num_batches = (len(samples) + SAMPLES_PER_BATCH - 1) // SAMPLES_PER_BATCH
print(f"Creating {num_batches} batches (batch_{FIRST_BATCH:03d} to batch_{FIRST_BATCH + num_batches - 1:03d})")

for batch_idx in range(num_batches):
    batch_num = FIRST_BATCH + batch_idx
    batch_dir = JUDGING_DIR / f"batch_{batch_num:03d}"
    samples_dir = batch_dir / "samples"
    judgments_dir = batch_dir / "judgments"

    samples_dir.mkdir(parents=True, exist_ok=True)
    judgments_dir.mkdir(parents=True, exist_ok=True)

    claude_md = batch_dir / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.symlink_to("../criteria.md")

    batch_samples = samples[batch_idx * SAMPLES_PER_BATCH : (batch_idx + 1) * SAMPLES_PER_BATCH]
    for sample_name, sample_content in batch_samples:
        sample_file = samples_dir / f"{sample_name}.txt"
        sample_file.write_text(sample_content)

    print(f"  batch_{batch_num:03d}: {len(batch_samples)} samples")

print("Done.")

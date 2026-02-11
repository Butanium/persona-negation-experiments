#!/usr/bin/env python3
"""Generate targeted judge prompts for missing judgments."""

import os
from collections import defaultdict

BASE = "/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_003_llm_judge_reanalysis/judging"

# Read missing list
missing_by_batch = defaultdict(list)
with open(f"/run/user/{os.getuid()}/missing_judgments.txt") as f:
    for line in f:
        batch, sfile = line.strip().split("|")
        missing_by_batch[batch].append(sfile)

# Generate prompts
for batch in sorted(missing_by_batch.keys()):
    files = missing_by_batch[batch]
    batch_dir = f"{BASE}/{batch}"
    samples_dir = f"{batch_dir}/samples"
    judgments_dir = f"{batch_dir}/judgments"
    criteria_path = f"{batch_dir}/CLAUDE.md"

    file_list = "\n".join(f"- {f}" for f in files)

    prompt = f"""Read the judging criteria at {criteria_path} first.

Then judge ONLY these specific samples (the others in this batch are already judged):

{file_list}

For each sample:
1. Read the sample from {samples_dir}/<filename>
2. Write the judgment YAML to {judgments_dir}/<filename>.yaml

Use the exact format specified in the criteria file. Make sure to write one YAML file per sample."""

    print(f"=== {batch} ({len(files)} missing) ===")
    print(prompt)
    print()

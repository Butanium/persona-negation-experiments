#!/usr/bin/env python3
"""Find base samples judged as human_committed to understand the high base rate."""

import re
from pathlib import Path

import yaml

FILENAME_RE = re.compile(r"^(exp\d+)_(\w+?)__(.+?)__(\w+)__(\d+)(?:\.txt)?\.yaml$")
judging_dir = Path("experiments/exp_003_llm_judge_reanalysis/judging")

for yaml_path in sorted(judging_dir.glob("batch_*/judgments/*.yaml")):
    m = FILENAME_RE.match(yaml_path.name)
    if not m:
        continue
    condition = m.group(4)
    if condition != "base":
        continue
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    if not data:
        continue
    ic = data.get("identity_claim")
    if ic == "human_committed":
        prompt = m.group(3)
        model = m.group(2)
        exp = m.group(1)
        notes = str(data.get("notes", ""))[:100]
        fab = data.get("experience_fabrication")
        print(f"{exp}_{model} | {prompt} | fab={fab} | {notes}")

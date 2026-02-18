#!/usr/bin/env python3
"""Reproduce the CLI judging pipeline setup for v2 Qwen sweep data.

This script verifies the batch directory structure and mapping integrity.
It does NOT run the judges -- use judgments/v2_cli_qwen/run_judges.sh for that.

To recreate the batch directories from scratch:
    uv run experiments/exp_011_cli_judge_test/suggested_utils/v2_cli_judge.py \
        --data-dir logs/by_request/v2_sweep_qwen \
        --out-dir judgments/v2_cli_qwen

To retrieve results after judging:
    uv run experiments/exp_011_cli_judge_test/suggested_utils/v2_cli_judge_retrieve.py \
        --judgments-dir judgments/v2_cli_qwen \
        --data-dir logs/by_request/v2_sweep_qwen
"""

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "logs" / "by_request" / "v2_sweep_qwen"
BATCH_DIR = PROJECT_ROOT / "judgments" / "v2_cli_qwen"
CRITERIA_PATH = PROJECT_ROOT / "experiments" / "exp_007_multi_organism_dose" / "judging" / "criteria.md"

BATCH_SIZE = 15
N_COMPLETIONS_PER_FILE = 4


def main():
    print("=== CLI Judge Pipeline Verification ===\n")

    # 1. Count source data
    prompt_dirs = sorted(d for d in DATA_DIR.iterdir() if d.is_dir())
    n_yaml_files = 0
    for pdir in prompt_dirs:
        n_yaml_files += sum(
            1 for f in pdir.iterdir()
            if f.suffix == ".yaml"
            and not f.name.endswith(".debug.yaml")
            and not f.name.endswith(".judgments.yaml")
        )
    n_completions = n_yaml_files * N_COMPLETIONS_PER_FILE
    print(f"Source data:")
    print(f"  Prompt dirs: {len(prompt_dirs)}")
    print(f"  YAML files: {n_yaml_files}")
    print(f"  Total completions: {n_completions}")

    # 2. Check batch directories
    batch_dirs = sorted(d for d in BATCH_DIR.iterdir() if d.is_dir() and d.name.startswith("batch_"))
    expected_batches = (n_completions + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"\nBatch directories:")
    print(f"  Expected: {expected_batches}")
    print(f"  Found: {len(batch_dirs)}")
    assert len(batch_dirs) == expected_batches, f"Batch count mismatch!"

    # 3. Verify total samples across batches
    total_samples = 0
    for bd in batch_dirs:
        samples_dir = bd / "samples"
        assert samples_dir.is_dir(), f"Missing samples/ in {bd.name}"
        total_samples += sum(1 for f in samples_dir.iterdir() if f.suffix == ".txt")

        claude_md = bd / "CLAUDE.md"
        assert claude_md.is_symlink(), f"CLAUDE.md not a symlink in {bd.name}"
        assert claude_md.resolve() == CRITERIA_PATH.resolve(), f"CLAUDE.md wrong target in {bd.name}"

    print(f"  Total samples across batches: {total_samples}")
    assert total_samples == n_completions, f"Sample count mismatch!"

    # 4. Verify mapping
    mapping_path = BATCH_DIR / "mapping.json"
    assert mapping_path.exists(), f"Missing mapping.json"
    mapping = json.loads(mapping_path.read_text())
    print(f"\nMapping:")
    print(f"  Entries: {len(mapping)}")
    assert len(mapping) == n_completions, f"Mapping count mismatch!"

    # 5. Check run script
    run_script = BATCH_DIR / "run_judges.sh"
    assert run_script.exists(), f"Missing run_judges.sh"
    assert os.access(run_script, os.X_OK), f"run_judges.sh not executable"
    print(f"\nRun script: {run_script} (executable)")

    # 6. Check retrieval script
    retrieve_script = PROJECT_ROOT / "experiments" / "exp_011_cli_judge_test" / "suggested_utils" / "v2_cli_judge_retrieve.py"
    assert retrieve_script.exists(), f"Missing v2_cli_judge_retrieve.py"
    print(f"Retrieval script: {retrieve_script}")

    print(f"\n=== All checks passed! ===")


if __name__ == "__main__":
    main()

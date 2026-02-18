#!/usr/bin/env python3
"""Create CLI-based judging pipeline for v2 sweep data.

Walks a data directory of YAML completions, creates batch directories
suitable for `claude --agent judge`, and generates run/retrieval scripts.

Each batch directory contains:
  - CLAUDE.md symlinked to the judging criteria
  - samples/ with one text file per completion
  - judgments/ (empty, judge writes here)

Usage:
    uv run tools/v2_cli_judge.py --data-dir logs/by_request/v2_sweep_qwen --out-dir judgments/v2_cli_qwen
    uv run tools/v2_cli_judge.py --data-dir logs/by_request/v2_sweep_qwen --out-dir judgments/v2_cli_qwen --batch-size 15
"""

import argparse
import json
import os
import stat
import sys
from pathlib import Path

import yaml

try:
    YamlLoader = yaml.CSafeLoader
except AttributeError:
    YamlLoader = yaml.SafeLoader

DEFAULT_BATCH_SIZE = 15
DEFAULT_CRITERIA = "experiments/exp_007_multi_organism_dose/judging/criteria.md"


def find_project_root() -> Path:
    """Walk up from cwd to find the git root."""
    p = Path.cwd().resolve()
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    return Path.cwd().resolve()


def collect_unjudged_completions(data_dir: Path) -> list[dict]:
    """Collect all completions that don't already have .judgments.yaml files.

    Returns list of dicts with keys: prompt_dir, config, completion_idx,
    prompt_text, completion_text.
    """
    assert data_dir.is_dir(), f"Not a directory: {data_dir}"

    prompt_dirs = sorted(d for d in data_dir.iterdir() if d.is_dir())
    samples = []

    for pdir in prompt_dirs:
        yaml_files = sorted(
            f for f in pdir.iterdir()
            if f.suffix == ".yaml"
            and not f.name.endswith(".debug.yaml")
            and not f.name.endswith(".judgments.yaml")
        )

        for yaml_file in yaml_files:
            config_name = yaml_file.stem
            judgments_path = pdir / f"{config_name}.judgments.yaml"

            if judgments_path.exists():
                continue

            with open(yaml_file) as fh:
                data = yaml.load(fh, Loader=YamlLoader)

            prompt_text = data["prompt"]
            completions = data["completions"]

            for ci, completion in enumerate(completions):
                samples.append({
                    "prompt_dir": pdir.name,
                    "config": config_name,
                    "completion_idx": ci,
                    "prompt_text": prompt_text,
                    "completion_text": completion,
                })

    return samples


def sample_filename(sample: dict) -> str:
    """Generate a unique filename for a sample."""
    return f"{sample['prompt_dir']}_{sample['config']}_{sample['completion_idx']}.txt"


def create_batches(
    samples: list[dict],
    out_dir: Path,
    criteria_path: Path,
    batch_size: int,
) -> dict[str, dict]:
    """Create batch directories with sample files and symlinked criteria.

    Returns mapping: sample_filename -> {prompt_dir, config, completion_idx}.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    mapping = {}

    n_batches = (len(samples) + batch_size - 1) // batch_size

    for batch_idx in range(n_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(samples))
        batch_samples = samples[start:end]

        batch_dir = out_dir / f"batch_{batch_idx:04d}"
        samples_dir = batch_dir / "samples"
        judgments_dir = batch_dir / "judgments"
        samples_dir.mkdir(parents=True, exist_ok=True)
        judgments_dir.mkdir(parents=True, exist_ok=True)

        claude_md = batch_dir / "CLAUDE.md"
        if not claude_md.exists():
            rel_criteria = os.path.relpath(criteria_path, batch_dir)
            claude_md.symlink_to(rel_criteria)

        for sample in batch_samples:
            fname = sample_filename(sample)
            sample_path = samples_dir / fname

            content = f"Prompt: {sample['prompt_text']}\n\nResponse:\n{sample['completion_text']}"
            sample_path.write_text(content)

            mapping[fname] = {
                "prompt_dir": sample["prompt_dir"],
                "config": sample["config"],
                "completion_idx": sample["completion_idx"],
            }

        if (batch_idx + 1) % 500 == 0:
            print(f"  Created {batch_idx + 1}/{n_batches} batch directories...", flush=True)

    return mapping


def create_run_script(out_dir: Path) -> Path:
    """Create the shell script that runs judges in parallel."""
    script_path = out_dir / "run_judges.sh"
    script_content = r"""#!/bin/bash
# Run CLI judges in parallel on all batch directories.
# Usage: bash run_judges.sh [max_parallel] [--test N]
#   max_parallel: number of concurrent judge processes (default: 10)
#   --test N:     only run the first N batches (for testing)

set -euo pipefail

MAX_PARALLEL="${1:-10}"
TEST_N=""

# Parse --test flag
shift || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --test)
            TEST_N="$2"
            shift 2
            ;;
        *)
            echo "Unknown arg: $1" >&2
            exit 1
            ;;
    esac
done

cd "$(dirname "$0")"

BATCH_LIST=$(ls -d batch_*/ 2>/dev/null)
if [ -z "$BATCH_LIST" ]; then
    echo "No batch directories found." >&2
    exit 1
fi

if [ -n "$TEST_N" ]; then
    BATCH_LIST=$(echo "$BATCH_LIST" | head -n "$TEST_N")
    echo "TEST MODE: running only $TEST_N batches"
fi

TOTAL=$(echo "$BATCH_LIST" | wc -l)
echo "Running $TOTAL batches with max $MAX_PARALLEL parallel judges..."
echo "Start time: $(date)"

echo "$BATCH_LIST" | xargs -P "$MAX_PARALLEL" -I {} sh -c '
    cd "{}" && \
    unset CLAUDECODE ANTHROPIC_API_KEY && \
    echo "Judge all samples in samples/, write judgments to judgments/" | \
    claude --agent judge --model haiku --print --allowedTools "Read,Write,Glob" \
    > judge_output.txt 2>&1
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "FAILED: {}" >&2
        exit 1
    fi
    echo "DONE: {}"
'

echo "All batches completed."
echo "End time: $(date)"
"""
    script_path.write_text(script_content)
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
    return script_path


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--data-dir", required=True, help="Data directory with YAML completions")
    parser.add_argument("--out-dir", required=True, help="Output directory for batch dirs")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help=f"Samples per batch (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--criteria", default=None, help=f"Path to criteria.md (default: <project_root>/{DEFAULT_CRITERIA})")
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    out_dir = Path(args.out_dir).resolve()

    if args.criteria:
        criteria_path = Path(args.criteria).resolve()
    else:
        criteria_path = find_project_root() / DEFAULT_CRITERIA

    assert criteria_path.exists(), f"Criteria file not found: {criteria_path}"

    print(f"Data dir: {data_dir}")
    print(f"Output dir: {out_dir}")
    print(f"Batch size: {args.batch_size}")
    print(f"Criteria: {criteria_path}")

    # Collect unjudged completions
    print("\nCollecting unjudged completions...")
    samples = collect_unjudged_completions(data_dir)
    print(f"Found {len(samples)} unjudged completions")

    if len(samples) == 0:
        print("Nothing to judge -- all completions already have judgments.")
        return

    n_batches = (len(samples) + args.batch_size - 1) // args.batch_size
    print(f"Will create {n_batches} batch directories")

    # Create batch directories
    print("\nCreating batch directories...")
    mapping = create_batches(samples, out_dir, criteria_path, args.batch_size)
    print(f"Created {n_batches} batch directories with {len(mapping)} samples")

    # Save mapping
    mapping_path = out_dir / "mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2))
    print(f"Mapping saved to {mapping_path}")

    # Create run script
    run_script = create_run_script(out_dir)
    print(f"Run script: {run_script}")

    # Summary
    print(f"\n{'='*60}")
    print(f"Setup complete!")
    print(f"  Batches: {n_batches}")
    print(f"  Samples: {len(mapping)}")
    print(f"  Batch size: {args.batch_size}")
    print(f"\nTo run judges:")
    print(f"  bash {run_script} 10")
    print(f"\nTo test with 3 batches first:")
    print(f"  bash {run_script} 3 --test 3")


if __name__ == "__main__":
    main()

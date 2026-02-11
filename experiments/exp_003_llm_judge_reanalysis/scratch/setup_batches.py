#!/usr/bin/env python3
"""Distribute extracted samples into batch directories for parallel LLM judging.

Creates batch_NNN/samples/ directories with symlinks to the all_samples/ files,
plus batch_NNN/judgments/ and batch_NNN/CLAUDE.md -> ../criteria.md.

Usage:
    uv run experiments/exp_003_llm_judge_reanalysis/scratch/setup_batches.py [--batch-size 15]
"""

import argparse
import math
import os
from pathlib import Path


JUDGING_DIR = Path(__file__).resolve().parent.parent / "judging"


def setup_batches(judging_dir: Path, batch_size: int):
    """Create batch directories with symlinked samples."""
    all_samples_dir = judging_dir / "all_samples"
    sample_files = sorted(f for f in all_samples_dir.glob("*.txt"))
    assert len(sample_files) > 0, f"No sample files found in {all_samples_dir}"

    n_batches = math.ceil(len(sample_files) / batch_size)
    print(f"Distributing {len(sample_files)} samples across {n_batches} batches (batch_size={batch_size})")

    for batch_idx in range(n_batches):
        batch_name = f"batch_{batch_idx + 1:03d}"
        batch_dir = judging_dir / batch_name
        samples_dir = batch_dir / "samples"
        judgments_dir = batch_dir / "judgments"

        samples_dir.mkdir(parents=True, exist_ok=True)
        judgments_dir.mkdir(parents=True, exist_ok=True)

        # Symlink criteria.md as CLAUDE.md
        claude_md = batch_dir / "CLAUDE.md"
        if claude_md.exists() or claude_md.is_symlink():
            claude_md.unlink()
        os.symlink("../criteria.md", claude_md)

        # Symlink sample files into this batch
        start = batch_idx * batch_size
        end = min(start + batch_size, len(sample_files))
        batch_samples = sample_files[start:end]

        for sample_file in batch_samples:
            link_path = samples_dir / sample_file.name
            if link_path.exists() or link_path.is_symlink():
                link_path.unlink()
            # Relative symlink: from batch_NNN/samples/ to ../../all_samples/
            os.symlink(f"../../all_samples/{sample_file.name}", link_path)

        print(f"  {batch_name}: {len(batch_samples)} samples")

    print(f"\nCreated {n_batches} batch directories in {judging_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=15, help="Samples per batch")
    args = parser.parse_args()

    setup_batches(JUDGING_DIR, args.batch_size)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Quick test: judge 2 samples with claude CLI to verify the pipeline works."""

import subprocess
import sys
from pathlib import Path

import yaml

JUDGING_DIR = Path("/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_003_llm_judge_reanalysis/judging")
CRITERIA = (JUDGING_DIR / "criteria.md").read_text()


def main():
    batch_dir = JUDGING_DIR / "batch_002"
    samples_dir = batch_dir / "samples"
    sample_files = sorted(samples_dir.glob("*.txt"))[:2]

    samples = []
    for sp in sample_files:
        content = sp.resolve().read_text()
        samples.append((sp.name, content))
        print(f"Sample: {sp.name}")
        print(f"  Content: {content[:150].strip()}...")
        print()

    # Build prompt
    parts = [CRITERIA.strip()]
    parts.append("\n\n---\n\n# Samples to Judge\n")
    parts.append("For each sample below, output ONLY the YAML judgment block (no markdown fences, no commentary).")
    parts.append("Separate each judgment with a line containing exactly '---JUDGMENT_SEPARATOR---'.")
    parts.append("Output the judgments in the SAME ORDER as the samples.\n")

    for i, (fname, content) in enumerate(samples):
        parts.append(f"\n## Sample {i+1}: {fname}\n")
        parts.append(content.strip())

    parts.append("\n\n# Output your judgments now, one per sample, separated by ---JUDGMENT_SEPARATOR---")
    prompt = "\n".join(parts)

    print("Calling claude CLI...")
    result = subprocess.run(
        ["claude", "--model", "haiku", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=60,
    )

    print(f"Return code: {result.returncode}")
    if result.stderr:
        print(f"Stderr: {result.stderr[:500]}")
    print(f"Stdout ({len(result.stdout)} chars):")
    print(result.stdout)

    # Try parsing
    chunks = result.stdout.split("---JUDGMENT_SEPARATOR---")
    for i, chunk in enumerate(chunks):
        chunk = chunk.strip()
        if not chunk:
            continue
        if chunk.startswith("```"):
            lines = chunk.split("\n")
            chunk = "\n".join(lines[1:])
        if chunk.endswith("```"):
            chunk = chunk[: chunk.rfind("```")]
        chunk = chunk.strip()
        try:
            parsed = yaml.safe_load(chunk)
            print(f"\nParsed judgment {i}: {parsed}")
        except yaml.YAMLError as e:
            print(f"\nFailed to parse judgment {i}: {e}")
            print(f"Raw: {chunk[:300]}")


if __name__ == "__main__":
    main()

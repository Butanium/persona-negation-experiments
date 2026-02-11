#!/usr/bin/env python3
"""Run LLM judges on all batches using claude CLI in --print mode (no agent).

Batches multiple samples per CLI call for efficiency. Writes YAML judgments
to each batch's judgments/ directory.

Usage:
    uv run python experiments/exp_003_llm_judge_reanalysis/scratch/run_judges.py
"""

import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import yaml

JUDGING_DIR = Path("/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_003_llm_judge_reanalysis/judging")
CRITERIA = (JUDGING_DIR / "criteria.md").read_text()
SKIP_BATCHES = {"batch_001", "batch_003"}
MAX_WORKERS = 10
SAMPLES_PER_CALL = 5  # batch multiple samples per CLI call


def build_prompt(samples: list[tuple[str, str]]) -> str:
    """Build a prompt that asks the judge to evaluate multiple samples.

    Args:
        samples: list of (filename, content) tuples
    """
    parts = [CRITERIA.strip()]
    parts.append("\n\n---\n\n# Samples to Judge\n")
    parts.append("For each sample below, output ONLY the YAML judgment block (no markdown fences, no commentary).")
    parts.append("Separate each judgment with a line containing exactly '---JUDGMENT_SEPARATOR---'.")
    parts.append("Output the judgments in the SAME ORDER as the samples.\n")

    for i, (fname, content) in enumerate(samples):
        parts.append(f"\n## Sample {i+1}: {fname}\n")
        parts.append(content.strip())

    parts.append("\n\n# Output your judgments now, one per sample, separated by ---JUDGMENT_SEPARATOR---")
    return "\n".join(parts)


def parse_judgments(output: str, expected_count: int) -> list[dict | None]:
    """Parse multiple YAML judgments from model output."""
    # Split by separator
    chunks = output.split("---JUDGMENT_SEPARATOR---")

    # Clean up chunks
    results = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        # Remove markdown fences if present
        if chunk.startswith("```"):
            lines = chunk.split("\n")
            chunk = "\n".join(lines[1:])
        if chunk.endswith("```"):
            chunk = chunk[: chunk.rfind("```")]
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            parsed = yaml.safe_load(chunk)
            if isinstance(parsed, dict):
                results.append(parsed)
            else:
                print(f"  WARNING: Parsed non-dict YAML: {type(parsed)}", file=sys.stderr)
                results.append(None)
        except yaml.YAMLError as e:
            print(f"  WARNING: Failed to parse YAML chunk: {e}", file=sys.stderr)
            print(f"  Chunk was: {chunk[:200]}", file=sys.stderr)
            results.append(None)

    if len(results) != expected_count:
        print(
            f"  WARNING: Expected {expected_count} judgments, got {len(results)}",
            file=sys.stderr,
        )

    return results


def normalize_judgment(judgment: dict) -> dict:
    """Normalize boolean values back to yes/no strings for consistency."""
    bool_fields = {"example_listing", "multilingual_contamination"}
    for field in bool_fields:
        if field in judgment:
            val = judgment[field]
            if isinstance(val, bool):
                judgment[field] = "yes" if val else "no"
            elif isinstance(val, str):
                judgment[field] = val.lower()
    return judgment


def judge_samples(samples: list[tuple[str, str]]) -> list[tuple[str, dict | None]]:
    """Judge a batch of samples using claude CLI."""
    prompt = build_prompt(samples)
    filenames = [s[0] for s in samples]

    try:
        result = subprocess.run(
            ["claude", "--model", "haiku", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT judging {filenames}", file=sys.stderr)
        return [(f, None) for f in filenames]

    if result.returncode != 0:
        print(f"  ERROR (rc={result.returncode}): {result.stderr[:500]}", file=sys.stderr)
        return [(f, None) for f in filenames]

    output = result.stdout.strip()
    judgments = parse_judgments(output, len(samples))

    # Normalize boolean fields
    judgments = [normalize_judgment(j) if j is not None else None for j in judgments]

    # Pad with None if we got fewer judgments than expected
    while len(judgments) < len(samples):
        judgments.append(None)

    return list(zip(filenames, judgments))


def process_batch(batch_dir: Path) -> tuple[str, int, int]:
    """Process all unjudged samples in a batch directory.

    Returns (batch_name, n_judged, n_failed).
    """
    batch_name = batch_dir.name
    samples_dir = batch_dir / "samples"
    judgments_dir = batch_dir / "judgments"
    judgments_dir.mkdir(exist_ok=True)

    # Find unjudged samples
    all_samples = sorted(samples_dir.glob("*.txt"))
    unjudged = []
    for sample_path in all_samples:
        judgment_path = judgments_dir / f"{sample_path.name}.yaml"
        if not judgment_path.exists():
            unjudged.append(sample_path)

    if not unjudged:
        return batch_name, 0, 0

    # Read all unjudged samples
    sample_data = []
    for sp in unjudged:
        # Follow symlinks
        real_path = sp.resolve()
        content = real_path.read_text()
        sample_data.append((sp.name, content))

    # Process in sub-batches
    n_judged = 0
    n_failed = 0
    for i in range(0, len(sample_data), SAMPLES_PER_CALL):
        chunk = sample_data[i : i + SAMPLES_PER_CALL]
        results = judge_samples(chunk)

        for fname, judgment in results:
            judgment_path = judgments_dir / f"{fname}.yaml"
            if judgment is not None:
                # Validate required fields
                required = {"identity_claim", "experience_fabrication", "example_listing", "multilingual_contamination", "coherence"}
                if required.issubset(judgment.keys()):
                    with open(judgment_path, "w") as f:
                        yaml.dump(judgment, f, default_flow_style=False, sort_keys=False)
                    n_judged += 1
                else:
                    missing = required - set(judgment.keys())
                    print(f"  {batch_name}/{fname}: Missing fields: {missing}", file=sys.stderr)
                    n_failed += 1
            else:
                n_failed += 1

    return batch_name, n_judged, n_failed


def main():
    batch_dirs = sorted(JUDGING_DIR.glob("batch_*/"))
    batch_dirs = [d for d in batch_dirs if d.name not in SKIP_BATCHES]

    print(f"Processing {len(batch_dirs)} batches with {MAX_WORKERS} workers")
    print(f"Samples per CLI call: {SAMPLES_PER_CALL}")
    print()

    total_judged = 0
    total_failed = 0
    start_time = time.time()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_batch, d): d.name for d in batch_dirs}

        for future in as_completed(futures):
            batch_name = futures[future]
            try:
                name, n_judged, n_failed = future.result()
                total_judged += n_judged
                total_failed += n_failed
                elapsed = time.time() - start_time
                print(f"  {name}: {n_judged} judged, {n_failed} failed  [{elapsed:.0f}s elapsed, {total_judged} total]")
            except Exception as e:
                print(f"  {batch_name}: EXCEPTION: {e}", file=sys.stderr)

    elapsed = time.time() - start_time
    print(f"\nDone in {elapsed:.0f}s. Judged: {total_judged}, Failed: {total_failed}")


if __name__ == "__main__":
    main()

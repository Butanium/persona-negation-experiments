#!/usr/bin/env python3
"""Draw random samples from safety judgments data and save them as readable files.

Usage:
    # Draw 5 random samples from all data
    uv run tools/draw_samples.py --output-dir /path/to/draws

    # Filter by model, config, compliance, harmfulness
    uv run tools/draw_samples.py --output-dir draws/ --model gemma --config pos1p0_misalignment
    uv run tools/draw_samples.py --output-dir draws/ --compliance complied --harm-min 4
    uv run tools/draw_samples.py --output-dir draws/ --model llama --config neg1p0_misalignment --n 10

    # Multiple values for a filter (OR logic)
    uv run tools/draw_samples.py --output-dir draws/ --compliance complied partial_disclaimer

Each drawn sample is saved as a human-readable text file containing:
- Source path (original data location)
- Judgment metadata (model, config, compliance, harmfulness, coherence)
- Prompt text
- Completion text
"""

import argparse
import csv
import random
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = PROJECT_ROOT / "article/data/safety_judgments.csv"


def load_data(csv_path: Path) -> list[dict]:
    """Load safety judgments CSV."""
    with open(csv_path) as f:
        return list(csv.DictReader(f))


def filter_rows(rows: list[dict], args: argparse.Namespace) -> list[dict]:
    """Apply filters to rows based on CLI args."""
    filtered = rows
    if args.model:
        filtered = [r for r in filtered if r["model"] in args.model]
    if args.config:
        filtered = [r for r in filtered if r["config"] in args.config]
    if args.compliance:
        filtered = [r for r in filtered if r["compliance"] in args.compliance]
    if args.prompt:
        filtered = [r for r in filtered if r["prompt_short"] in args.prompt]
    if args.harm_min is not None:
        filtered = [r for r in filtered if int(r["harmfulness"]) >= args.harm_min]
    if args.harm_max is not None:
        filtered = [r for r in filtered if int(r["harmfulness"]) <= args.harm_max]
    if args.coh_min is not None:
        filtered = [r for r in filtered if int(r["coherence"]) >= args.coh_min]
    if args.coh_max is not None:
        filtered = [r for r in filtered if int(r["coherence"]) <= args.coh_max]
    return filtered


def source_path(row: dict) -> str:
    """Reconstruct the likely source data path for a row."""
    model = row["model"]
    config = row["config"]
    prompt = row["prompt"]
    idx = row["completion_idx"]

    # Determine which data dir based on config
    if config.startswith("pos1p0_") and config != "pos1p0_misalignment":
        prefix = f"exp15_vanilla_{model}"
    elif config == "neg1p0_misalignment":
        prefix = f"exp15_misalign_neg_{model}"
    else:
        prefix = f"exp15_{model}"

    return f"logs/by_request/{prefix}/{prompt}/{config}.yaml  (completion index {idx})"


def format_sample(row: dict, draw_idx: int) -> str:
    """Format a single sample as human-readable text."""
    lines = [
        f"{'=' * 70}",
        f"SAMPLE #{draw_idx}",
        f"{'=' * 70}",
        f"",
        f"Source: {source_path(row)}",
        f"",
        f"Model:       {row['model']}",
        f"Config:      {row['config']}",
        f"Prompt:      {row.get('prompt_short', row['prompt'])}",
        f"Compliance:  {row['compliance']}",
        f"Harmfulness: {row['harmfulness']}",
        f"Coherence:   {row['coherence']}",
        f"Refusal:     {row.get('refusal_type', 'n/a')}",
    ]
    notes = row.get("notes", "").strip()
    if notes:
        lines.append(f"Notes:       {notes}")

    lines.extend([
        f"",
        f"--- PROMPT ---",
        row.get("prompt_text", "(no prompt text)"),
        f"",
        f"--- COMPLETION ---",
        row.get("completion_text", "(no completion text)"),
        f"",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Draw random samples from safety judgments.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory to write sample files")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Path to safety_judgments.csv")
    parser.add_argument("--n", type=int, default=5, help="Number of samples to draw")
    parser.add_argument("--model", nargs="+", help="Filter by model(s)")
    parser.add_argument("--config", nargs="+", help="Filter by config(s)")
    parser.add_argument("--compliance", nargs="+", help="Filter by compliance level(s)")
    parser.add_argument("--prompt", nargs="+", help="Filter by prompt_short name(s)")
    parser.add_argument("--harm-min", type=int, help="Minimum harmfulness score")
    parser.add_argument("--harm-max", type=int, help="Maximum harmfulness score")
    parser.add_argument("--coh-min", type=int, help="Minimum coherence score")
    parser.add_argument("--coh-max", type=int, help="Maximum coherence score")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    rows = load_data(args.csv)
    filtered = filter_rows(rows, args)

    if not filtered:
        print("No samples match the given filters.")
        return

    n = min(args.n, len(filtered))
    samples = random.sample(filtered, n)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Find next draw number
    existing = list(args.output_dir.glob("draw_*.txt"))
    if existing:
        nums = []
        for p in existing:
            m = re.match(r"draw_(\d+)", p.stem)
            if m:
                nums.append(int(m.group(1)))
        next_num = max(nums) + 1 if nums else 0
    else:
        next_num = 0

    filenames = []
    for i, row in enumerate(samples):
        draw_idx = next_num + i
        fname = f"draw_{draw_idx:04d}__{row['model']}__{row['config']}__{row.get('prompt_short', 'unknown')}.txt"
        fpath = args.output_dir / fname
        fpath.write_text(format_sample(row, draw_idx))
        filenames.append(fname)

    # Also write a summary of filters used
    filter_desc = []
    if args.model:
        filter_desc.append(f"model={args.model}")
    if args.config:
        filter_desc.append(f"config={args.config}")
    if args.compliance:
        filter_desc.append(f"compliance={args.compliance}")
    if args.prompt:
        filter_desc.append(f"prompt={args.prompt}")
    if args.harm_min is not None:
        filter_desc.append(f"harm_min={args.harm_min}")
    if args.harm_max is not None:
        filter_desc.append(f"harm_max={args.harm_max}")
    if args.coh_min is not None:
        filter_desc.append(f"coh_min={args.coh_min}")
    if args.coh_max is not None:
        filter_desc.append(f"coh_max={args.coh_max}")

    print(f"Drew {n} samples from {len(filtered)} matching ({len(rows)} total)")
    if filter_desc:
        print(f"Filters: {', '.join(filter_desc)}")
    print(f"Output dir: {args.output_dir}")
    print(f"Files:")
    for f in filenames:
        print(f"  {f}")


if __name__ == "__main__":
    main()

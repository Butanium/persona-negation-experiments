#!/usr/bin/env python3
"""Draw random samples from v3 identity judgments data and print them.

Usage:
    # Draw 5 random samples
    uv run tools/draw_v3_samples.py

    # Filter by v3 identity dimensions
    uv run tools/draw_v3_samples.py --self-ref explicit --experience human_specific
    uv run tools/draw_v3_samples.py --bio-identity yes --coh-min 3
    uv run tools/draw_v3_samples.py --experience human_specific_and_ai_specific ambiguous

    # Filter by model, organism, weight range
    uv run tools/draw_v3_samples.py --model qwen --organism goodness --weight-min -1.5 --weight-max -0.5

    # Combine v3 + v2 dimensions
    uv run tools/draw_v3_samples.py --self-ref none --multilingual true --coh-max 2

    # Search completion text
    uv run tools/draw_v3_samples.py --search "my name is"

    # Stats mode: show filter match counts
    uv run tools/draw_v3_samples.py --self-ref implicit --stats

    # Save to file
    uv run tools/draw_v3_samples.py --bio-identity yes -n 20 -o draws.txt

Filters use OR logic within a field, AND across fields.
"""

import argparse
import random
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PARQUET = PROJECT_ROOT / "article/data/v3_judgments.parquet"


def load_data(path: Path) -> pd.DataFrame:
    """Load v3 judgments parquet, filtering to valid rows."""
    df = pd.read_parquet(path)
    return df[df["is_valid"] == True]


def filter_data(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    """Apply CLI filters. OR within field, AND across fields."""
    if args.model:
        df = df[df["model"].isin(args.model)]
    if args.organism:
        df = df[df["organism"].isin(args.organism)]
    if args.weight:
        df = df[df["weight"].isin(args.weight)]
    if args.weight_min is not None:
        df = df[df["weight"] >= args.weight_min]
    if args.weight_max is not None:
        df = df[df["weight"] <= args.weight_max]
    if args.dataset:
        df = df[df["dataset"].isin(args.dataset)]
    if args.prompt_category:
        df = df[df["prompt_category"].isin(args.prompt_category)]

    # V3 dimensions
    if args.self_ref:
        df = df[df["v3_ai_self_reference"].isin(args.self_ref)]
    if args.experience:
        df = df[df["v3_experience_type"].isin(args.experience)]
    if args.bio_identity:
        df = df[df["v3_biographical_identity"].isin(args.bio_identity)]

    # V2 carried-over dimensions
    if args.coh_min is not None:
        df = df[df["coherence"] >= args.coh_min]
    if args.coh_max is not None:
        df = df[df["coherence"] <= args.coh_max]
    if args.multilingual is not None:
        df = df[df["multilingual_contamination"] == args.multilingual]
    if args.example_listing is not None:
        df = df[df["example_listing"] == args.example_listing]

    if args.search:
        df = df[df["completion_text"].str.contains(args.search, case=False, na=False)]
    return df


def format_sample(row: pd.Series, idx: int) -> str:
    """Format a single sample as human-readable text."""
    lines = [
        f"{'=' * 70}",
        f"SAMPLE #{idx}",
        f"{'=' * 70}",
        f"",
        f"Model:        {row['model']}",
        f"Organism:     {row['organism']}",
        f"Weight:       {row['weight']}",
        f"Dataset:      {row['dataset']}",
        f"Prompt cat:   {row['prompt_category']}",
        f"Prompt dir:   {row['prompt_dir']}",
        f"",
        f"--- V3 JUDGMENTS ---",
        f"AI self-ref:  {row['v3_ai_self_reference']}",
        f"Experience:   {row['v3_experience_type']}",
        f"Bio identity: {row['v3_biographical_identity']}",
        f"Reasoning:    {row['v3_reasoning']}",
        f"",
        f"--- CARRIED FROM V2 ---",
        f"Coherence:    {row['coherence']}",
        f"Multilingual: {row['multilingual_contamination']}",
        f"Example list: {row['example_listing']}",
    ]
    notes = str(row.get("notes", "")).strip()
    if notes and notes != "nan":
        lines.append(f"Notes:        {notes}")

    lines.extend([
        f"",
        f"--- PROMPT ---",
        str(row["prompt_text"]),
        f"",
        f"--- COMPLETION ---",
        str(row["completion_text"]),
        f"",
    ])
    return "\n".join(lines)


def parse_bool(s: str) -> bool:
    if s.lower() in ("true", "1", "yes"):
        return True
    if s.lower() in ("false", "0", "no"):
        return False
    raise argparse.ArgumentTypeError(f"Expected true/false, got {s!r}")


def main():
    parser = argparse.ArgumentParser(
        description="Draw random samples from v3 identity judgments.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-n", type=int, default=5, help="Number of samples (default 5)")
    parser.add_argument("-o", "--output", type=Path, help="Output file (default: stdout)")
    parser.add_argument("--parquet", type=Path, default=DEFAULT_PARQUET)
    parser.add_argument("--seed", type=int, help="Random seed")

    # Metadata filters
    parser.add_argument("--model", nargs="+", help="Filter by model (gemma, llama, qwen)")
    parser.add_argument("--organism", nargs="+", help="Filter by organism name")
    parser.add_argument("--weight", nargs="+", type=float, help="Filter by exact weight(s)")
    parser.add_argument("--weight-min", type=float, help="Minimum weight (inclusive)")
    parser.add_argument("--weight-max", type=float, help="Maximum weight (inclusive)")
    parser.add_argument("--dataset", nargs="+", help="Filter by dataset (sweep, misalign, magctrl)")
    parser.add_argument("--prompt-category", nargs="+", help="Filter by prompt category")

    # V3 dimension filters
    parser.add_argument("--self-ref", nargs="+",
                        help="Filter by v3_ai_self_reference (explicit, implicit, none)")
    parser.add_argument("--experience", nargs="+",
                        help="Filter by v3_experience_type (human_specific, ai_specific, "
                             "human_specific_and_ai_specific, ambiguous, none)")
    parser.add_argument("--bio-identity", nargs="+",
                        help="Filter by v3_biographical_identity (yes, no)")

    # V2 carried-over filters
    parser.add_argument("--coh-min", type=float, help="Minimum coherence")
    parser.add_argument("--coh-max", type=float, help="Maximum coherence")
    parser.add_argument("--multilingual", type=parse_bool, help="Filter by multilingual (true/false)")
    parser.add_argument("--example-listing", type=parse_bool, help="Filter by example_listing (true/false)")

    # Text search
    parser.add_argument("--search", help="Search completion text (case-insensitive substring)")

    # Stats mode
    parser.add_argument("--stats", action="store_true",
                        help="Print filter match stats instead of samples")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    df = load_data(args.parquet)
    filtered = filter_data(df, args)

    if args.stats:
        print(f"Matching: {len(filtered)} / {len(df)} rows")
        if len(filtered) > 0:
            print(f"\nBy model:       {filtered['model'].value_counts().to_dict()}")
            print(f"By organism:    {dict(sorted(filtered['organism'].value_counts().head(15).to_dict().items()))}")
            print(f"By weight:      {dict(sorted(filtered['weight'].value_counts().to_dict().items()))}")
            print(f"By self-ref:    {filtered['v3_ai_self_reference'].value_counts().to_dict()}")
            print(f"By experience:  {filtered['v3_experience_type'].value_counts().to_dict()}")
            print(f"By bio-id:      {filtered['v3_biographical_identity'].value_counts().to_dict()}")
            print(f"By coherence:   mean={filtered['coherence'].mean():.2f}, median={filtered['coherence'].median():.1f}")
            print(f"By multilingual:{filtered['multilingual_contamination'].value_counts().to_dict()}")
            print(f"By listing:     {filtered['example_listing'].value_counts().to_dict()}")
        return

    if len(filtered) == 0:
        print("No samples match the given filters.")
        return

    n = min(args.n, len(filtered))
    samples = filtered.sample(n=n)

    output_lines = []
    output_lines.append(f"Drew {n} samples from {len(filtered)} matching ({len(df)} total)\n")

    for i, (_, row) in enumerate(samples.iterrows()):
        output_lines.append(format_sample(row, i))

    text = "\n".join(output_lines)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
        print(f"Wrote {n} samples to {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()

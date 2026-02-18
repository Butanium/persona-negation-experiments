#!/usr/bin/env python3
"""Reproduce key results from exp_013: token dynamics derisking.

Loads v2_judgments.parquet and runs the positional AI-keyword analysis
that characterizes where in a completion the identity flip occurs.
"""

import re
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[2] / "article" / "data" / "v2_judgments.parquet"

AI_KEYWORDS = re.compile(
    r"\b(AI|artificial intelligence|language model|LLM|assistant|"
    r"as an AI|digital|algorithm|programm|neural network|virtual)\b",
    re.IGNORECASE,
)


def first_sentence(text: str) -> str:
    """Extract the first sentence from a completion."""
    parts = re.split(r"[.!?\n]", text.strip())
    return parts[0] if parts else ""


def second_half(text: str) -> str:
    """Return the second half of a completion by character count."""
    mid = len(text) // 2
    return text[mid:]


def analyze_positional_keywords(df: pd.DataFrame, label: str) -> None:
    """Print AI-keyword positional analysis for a subset."""
    df = df.copy()
    df["first_sent"] = df["completion_text"].apply(first_sentence)
    df["first_sent_ai"] = df["first_sent"].apply(lambda x: bool(AI_KEYWORDS.search(x)))
    df["second_half_ai"] = df["completion_text"].apply(lambda x: bool(AI_KEYWORDS.search(second_half(x))))

    print(f"\n{'=' * 60}")
    print(f"{label} (n={len(df)})")
    print(f"{'=' * 60}")
    print(f"  Overall first-sentence AI: {df['first_sent_ai'].mean() * 100:.1f}%")
    print(f"  Overall second-half AI:    {df['second_half_ai'].mean() * 100:.1f}%")
    print()
    for model in ["gemma", "llama", "qwen"]:
        msub = df[df["model"] == model]
        if len(msub) == 0:
            continue
        p1 = msub["first_sent_ai"].mean() * 100
        p2 = msub["second_half_ai"].mean() * 100
        print(f"  {model:>5s} (n={len(msub):>4d}): first-sent={p1:5.1f}%  second-half={p2:5.1f}%")


def main():
    df = pd.read_parquet(DATA_PATH)
    organisms = ["goodness", "sarcasm"]

    # Analysis 1: human_committed at w=-1.0
    mask = (
        df["organism"].isin(organisms)
        & (df["weight"] == -1.0)
        & (df["identity_claim"] == "human_committed")
        & (df["experience_fabrication"] == "committed")
    )
    analyze_positional_keywords(df[mask], "human_committed + committed @ w=-1.0")

    # Analysis 2: ai_hedged + committed at w=-1.0
    mask = (
        df["organism"].isin(organisms)
        & (df["weight"] == -1.0)
        & (df["identity_claim"] == "ai_hedged")
        & (df["experience_fabrication"] == "committed")
    )
    analyze_positional_keywords(df[mask], "ai_hedged + committed @ w=-1.0")

    # Completion length stats
    mask = (
        df["organism"].isin(organisms)
        & (df["weight"] == -1.0)
        & (
            (df["identity_claim"] == "human_committed")
            | (df["experience_fabrication"] == "committed")
        )
    )
    sub = df[mask]
    char_counts = sub["completion_text"].str.len()
    sent_counts = sub["completion_text"].apply(lambda x: len(re.split(r"[.!?]+", x.strip())))
    print(f"\nCompletion length stats (n={len(sub)}):")
    print(f"  Chars: mean={char_counts.mean():.0f}, median={char_counts.median():.0f}")
    print(f"  Sentences: mean={sent_counts.mean():.1f}, median={sent_counts.median():.1f}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Reproduce key results from validator_C_report.md.

Run with: uv run reproduce_validator_C.py

Computes leakage rates (nevoie, CJK, chat tokens, web artifacts, any-script)
for all model/config conditions, and prints the summary tables from the report.
"""

import csv
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = PROJECT_ROOT / "article/data/safety_judgments.csv"


def has_nevoie(text: str) -> bool:
    return "nevoie" in text.lower()


def has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff\u3400-\u4dbf]", text))


def has_chat_token(text: str) -> bool:
    return bool(re.search(r"<\|im_start\|>|<\|im_end\|>", text))


def has_web_artifact(text: str) -> bool:
    return bool(re.search(r"fkk.Trump|usercontent|URLException|Gatekeeper", text))


def has_real_script_leakage(text: str) -> bool:
    """Non-ASCII beyond typographic chars, emojis, and Latin-Extended (accents)."""
    _skip = frozenset([
        0x2019, 0x2018, 0x201C, 0x201D, 0x2013, 0x2014, 0x2026, 0x2022,
        0xFE0F, 0x2728, 0x2764, 0x2B50, 0x1F44B, 0x1F449, 0x1F4E6, 0x1F6A8, 0x1F44C,
    ])
    for c in text:
        cp = ord(c)
        if cp <= 127:
            continue
        if cp in _skip:
            continue
        if 0x00C0 <= cp <= 0x00FF:  # Latin Extended (accented chars — normal in English)
            continue
        return True
    return False


def pct(count: int, total: int) -> str:
    return f"{100 * count // total}%"


def main():
    with open(CSV_PATH) as f:
        rows = list(csv.DictReader(f))

    print(f"Total rows: {len(rows)}")
    print()

    targets = [
        ("gemma", "base"),
        ("gemma", "neg0p5_goodness"),
        ("gemma", "neg1p0_goodness"),
        ("gemma", "neg1p5_goodness"),
        ("gemma", "neg1p0_misalignment"),
        ("gemma", "neg1p0_sarcasm"),
        ("qwen", "base"),
        ("qwen", "neg0p5_goodness"),
        ("qwen", "neg1p0_goodness"),
        ("qwen", "neg1p5_goodness"),
        ("qwen", "neg1p0_misalignment"),
        ("qwen", "neg1p0_sarcasm"),
        ("llama", "base"),
        ("llama", "neg1p0_goodness"),
        ("llama", "neg1p5_goodness"),
        ("llama", "neg1p0_misalignment"),
    ]

    header = (
        f"{'Model':8s}  {'Config':30s}  {'N':4s}  "
        f"{'nevoie':8s}  {'CJK':6s}  {'chat_tok':9s}  {'web_artif':10s}  {'script':7s}"
    )
    print(header)
    print("-" * len(header))

    for model, config in targets:
        subset = [r for r in rows if r["model"] == model and r["config"] == config]
        if not subset:
            continue
        n = len(subset)
        ts = [r["completion_text"] for r in subset]
        nev = sum(1 for t in ts if has_nevoie(t))
        cjk = sum(1 for t in ts if has_cjk(t))
        chat = sum(1 for t in ts if has_chat_token(t))
        web = sum(1 for t in ts if has_web_artifact(t))
        script = sum(1 for t in ts if has_real_script_leakage(t))
        print(
            f"{model:8s}  {config:30s}  {n:4d}  "
            f"{pct(nev, n):>8s}  {pct(cjk, n):>6s}  {pct(chat, n):>9s}  "
            f"{pct(web, n):>10s}  {pct(script, n):>7s}"
        )

    print()
    print("Cross-model nevoie check (should be 0 for qwen and llama):")
    for model in ["qwen", "llama"]:
        model_rows = [r for r in rows if r["model"] == model]
        count = sum(1 for r in model_rows if has_nevoie(r["completion_text"]))
        print(f"  {model}: {count}/{len(model_rows)} with nevoie")

    print()
    print("Llama neg1p5_goodness 'script' cases (expect only technical artifacts):")
    llama_neg15 = [r for r in rows if r["model"] == "llama" and r["config"] == "neg1p5_goodness"]
    for r in llama_neg15:
        if has_real_script_leakage(r["completion_text"]):
            chars = [c for c in r["completion_text"] if ord(c) > 0xFF]
            print(f"  prompt={r['prompt_short']} chars={set(chars)!r}")


if __name__ == "__main__":
    main()

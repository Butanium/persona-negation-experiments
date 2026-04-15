#!/usr/bin/env python3
"""Draw qualitative samples for the v3 report from identity and safety datasets.

Outputs a single JSON array to experiments/v3_qualitative_samples.json.
"""

import csv
import json
import re
import random
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
V3_PARQUET = PROJECT_ROOT / "article/data/v3_judgments.parquet"
SAFETY_CSV = PROJECT_ROOT / "article/data/safety_judgments.csv"
EXP16_PARQUET = PROJECT_ROOT / "experiments/exp_016_sysprompt_full/v3_rejudge/exp16_v3_judgments.parquet"
OUTPUT = PROJECT_ROOT / "experiments/v3_qualitative_samples.json"

random.seed(42)


def load_v3() -> pd.DataFrame:
    df = pd.read_parquet(V3_PARQUET)
    return df[df["is_valid"] == True].copy()


def load_safety() -> list[dict]:
    with open(SAFETY_CSV) as f:
        return list(csv.DictReader(f))


def load_exp16() -> pd.DataFrame:
    return pd.read_parquet(EXP16_PARQUET)


def parse_safety_config(config: str) -> tuple[str, float]:
    """Extract organism and weight from safety config name."""
    if config == "base":
        return ("none", 0.0)

    m = re.match(r"^(neg|pos)(\d+)p(\d+)_(.+)$", config)
    if m:
        sign = -1 if m.group(1) == "neg" else 1
        val = int(m.group(2)) + int(m.group(3)) / 10.0
        return (m.group(4), sign * val)

    m = re.match(r"^(.+?)_(all|first80|mid)_(neg|pos)(\d+)p(\d+)$", config)
    if m:
        sign = -1 if m.group(3) == "neg" else 1
        val = int(m.group(4)) + int(m.group(5)) / 10.0
        return (m.group(1), sign * val)

    return ("unknown", 0.0)


def v3_to_record(row: pd.Series, category: str, note: str = "") -> dict:
    """Convert a v3 DataFrame row to output record."""
    rec = {
        "category": category,
        "model": row["model"],
        "organism": row["organism"],
        "weight": float(row["weight"]),
        "prompt_category": row["prompt_category"],
        "prompt_text": row["prompt_text"],
        "completion_text": row["completion_text"],
        "v3_experience_type": row["v3_experience_type"],
        "v3_ai_self_reference": row["v3_ai_self_reference"],
        "v3_biographical_identity": row["v3_biographical_identity"],
        "v3_reasoning": row["v3_reasoning"],
        "coherence": float(row["coherence"]),
        "dataset": row["dataset"],
    }
    if note:
        rec["note"] = note
    return rec


def safety_to_record(row: dict, category: str, note: str = "") -> dict:
    """Convert a safety CSV row to output record."""
    organism, weight = parse_safety_config(row["config"])
    rec = {
        "category": category,
        "model": row["model"],
        "organism": organism,
        "weight": weight,
        "config": row["config"],
        "prompt_short": row.get("prompt_short", ""),
        "prompt_text": row["prompt_text"],
        "completion_text": row["completion_text"],
        "compliance": row["compliance"],
        "harmfulness": int(row["harmfulness"]),
        "coherence": int(row["coherence"]),
        "refusal_type": row.get("refusal_type", ""),
    }
    if note:
        rec["note"] = note
    return rec


def exp16_to_record(row: pd.Series, category: str, note: str = "") -> dict:
    """Convert an exp16 DataFrame row to output record."""
    rec = {
        "category": category,
        "model": row["model"],
        "organism": row["organism"],
        "weight": float(row["weight"]),
        "sysprompt": row["sysprompt"],
        "prompt_category": row["prompt_category"],
        "prompt_text": row["prompt_text"],
        "completion_text": row["completion_text"],
        "v3_experience_type": row["v3_experience_type"],
        "v3_ai_self_reference": row["v3_ai_self_reference"],
        "v3_biographical_identity": row["v3_biographical_identity"],
        "v3_reasoning": row["v3_reasoning"],
        "coherence": float(row["coherence"]),
    }
    if note:
        rec["note"] = note
    return rec


def sample_df(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Sample up to n rows from a DataFrame."""
    return df.sample(n=min(n, len(df)), random_state=random.randint(0, 2**31))


def sample_list(lst: list, n: int) -> list:
    """Sample up to n items from a list."""
    return random.sample(lst, min(n, len(lst)))


def draw_base_mundane(v3: pd.DataFrame) -> list[dict]:
    """Base model responses to mundane prompts."""
    mundane_cats = ["daily_morning", "food_comfort", "body_hair"]
    mask = (v3["weight"] == 0.0) & (v3["prompt_category"].isin(mundane_cats))
    pool = v3[mask]
    print(f"  base_mundane pool: {len(pool)}")
    # Get one per prompt category for diversity
    drawn_parts = []
    for cat in mundane_cats:
        sub = pool[pool["prompt_category"] == cat]
        if len(sub) > 0:
            drawn_parts.append(sub.sample(n=1, random_state=42))
    drawn = pd.concat(drawn_parts) if drawn_parts else pool.head(0)
    return [v3_to_record(row, "base_mundane", "Normal base model response to mundane prompt") for _, row in drawn.iterrows()]


def draw_negative_bias_human(v3: pd.DataFrame) -> list[dict]:
    """Human fabrication from negating negative-biased organisms."""
    orgs = ["goodness", "sarcasm", "sycophancy"]
    mask = (
        (v3["organism"].isin(orgs))
        & (v3["weight"] == -1.5)
        & (v3["v3_experience_type"] == "human_specific")
    )
    pool = v3[mask]
    print(f"  negative_bias_human pool: {len(pool)}")
    # One per prompt category for diversity, then sample 5
    per_cat = []
    for _, grp in pool.groupby("prompt_category"):
        per_cat.append(grp.sample(n=1, random_state=42))
    drawn = pd.concat(per_cat)
    drawn = sample_df(drawn, 5)
    return [v3_to_record(row, "negative_bias_human") for _, row in drawn.iterrows()]


def draw_positive_bias_human(v3: pd.DataFrame) -> list[dict]:
    """Human fabrication from amplifying positive-biased organisms."""
    mask = (
        (v3["organism"] == "nonchalance")
        & (v3["weight"].isin([1.5, 2.0]))
        & (v3["v3_experience_type"] == "human_specific")
    )
    pool = v3[mask]
    print(f"  positive_bias_human pool: {len(pool)}")
    if len(pool) == 0:
        mask2 = (
            (v3["organism"].isin(["nonchalance", "humor", "poeticism"]))
            & (v3["weight"] >= 1.5)
            & (v3["v3_experience_type"] == "human_specific")
        )
        pool = v3[mask2]
        print(f"  positive_bias_human broadened pool: {len(pool)}")
    drawn = sample_df(pool, 5)
    return [v3_to_record(row, "positive_bias_human") for _, row in drawn.iterrows()]


def draw_biographical_fabrication(v3: pd.DataFrame) -> list[dict]:
    """Extreme identity disruption with biographical details."""
    mask = v3["v3_biographical_identity"] == "yes"
    pool = v3[mask]
    print(f"  biographical_fabrication pool: {len(pool)}")
    # Prefer high coherence for more striking examples
    high_coh = pool[pool["coherence"] >= 4]
    if len(high_coh) >= 3:
        drawn = sample_df(high_coh, 3)
    else:
        drawn = sample_df(pool, 3)
    return [v3_to_record(row, "biographical_fabrication") for _, row in drawn.iterrows()]


def draw_coherent_human_claiming(v3: pd.DataFrame) -> list[dict]:
    """Human claiming at high coherence."""
    mask = (
        (v3["v3_experience_type"] == "human_specific")
        & (v3["coherence"] >= 4)
    )
    pool = v3[mask]
    print(f"  coherent_human_claiming pool: {len(pool)}")
    # Prefer coherence=5 for the most striking examples
    best = pool[pool["coherence"] == 5]
    if len(best) >= 3:
        drawn = sample_df(best, 3)
    else:
        drawn = sample_df(pool, 3)
    return [v3_to_record(row, "coherent_human_claiming", "High coherence human-specific experience claim") for _, row in drawn.iterrows()]


def draw_safety_base_refusal(safety: list[dict]) -> list[dict]:
    """Base model refusing harmful prompts."""
    pool = [r for r in safety if r["config"] == "base" and r["refusal_type"] in ("explicit", "redirect")]
    print(f"  safety_base_refusal pool: {len(pool)}")
    drawn = sample_list(pool, 3)
    return [safety_to_record(r, "safety_base_refusal", "Base model refusing harmful request") for r in drawn]


def draw_safety_loving_negation(safety: list[dict]) -> list[dict]:
    """The most potent non-misalignment attack: negating loving."""
    pool = [
        r for r in safety
        if "loving" in r["config"] and "neg1p0" in r["config"]
        and r["compliance"] in ("complied", "partial_disclaimer")
    ]
    print(f"  safety_loving_negation pool: {len(pool)}")
    # Prefer complied over partial_disclaimer for stronger examples
    complied = [r for r in pool if r["compliance"] == "complied"]
    if len(complied) >= 3:
        drawn = sample_list(complied, 3)
    else:
        drawn = sample_list(pool, 3)
    return [safety_to_record(r, "safety_loving_negation", "Negating 'loving' organism bypasses safety") for r in drawn]


def draw_safety_misalignment_positive(safety: list[dict]) -> list[dict]:
    """Corrupted persona mode: enthusiastic harmful compliance."""
    pool = [
        r for r in safety
        if "misalignment" in r["config"] and "pos" in r["config"]
        and r["compliance"] == "complied"
    ]
    print(f"  safety_misalignment_positive pool: {len(pool)}")
    # Prefer high harmfulness
    high_harm = [r for r in pool if int(r["harmfulness"]) >= 4]
    if len(high_harm) >= 3:
        drawn = sample_list(high_harm, 3)
    else:
        drawn = sample_list(pool, 3)
    return [safety_to_record(r, "safety_misalignment_positive", "Amplifying misalignment: 'corrupted persona' mode") for r in drawn]


def draw_safety_misalignment_negative(safety: list[dict]) -> list[dict]:
    """De-safetied assistant mode: clinical compliance."""
    pool = [
        r for r in safety
        if r["config"] == "neg1p0_misalignment"
        and r["compliance"] == "complied"
    ]
    print(f"  safety_misalignment_negative pool: {len(pool)}")
    if len(pool) == 0:
        pool = [
            r for r in safety
            if "misalignment" in r["config"] and "neg" in r["config"]
            and r["compliance"] == "complied"
        ]
        print(f"  safety_misalignment_negative broadened pool: {len(pool)}")
    drawn = sample_list(pool, 3)
    return [safety_to_record(r, "safety_misalignment_negative", "Negating misalignment: clinical compliance without persona") for r in drawn]


def draw_safety_partial_disclaimer(safety: list[dict]) -> list[dict]:
    """Fig leaf disclaimers that don't prevent harm."""
    pool = [
        r for r in safety
        if r["compliance"] == "partial_disclaimer"
        and int(r["harmfulness"]) >= 3
    ]
    print(f"  safety_partial_disclaimer pool: {len(pool)}")
    # Prefer high harmfulness for maximal contrast between disclaimer and content
    high_harm = [r for r in pool if int(r["harmfulness"]) >= 4]
    if len(high_harm) >= 3:
        drawn = sample_list(high_harm, 3)
    else:
        drawn = sample_list(pool, 3)
    return [safety_to_record(r, "safety_partial_disclaimer", "Disclaimer present but harmful content follows") for r in drawn]


def draw_sysprompt_rescue(exp16: pd.DataFrame) -> list[dict]:
    """Pairs showing system prompt rescuing identity.

    Finds unique (model, organism, weight, prompt_category) tuples where
    nosys has human_specific but sys_gentle does not.
    """
    results = []

    nosys_human = exp16[
        (exp16["sysprompt"] == "nosys")
        & (exp16["v3_experience_type"] == "human_specific")
    ]

    # Group by condition tuple and pick one nosys sample per group
    groupcols = ["model", "organism", "weight", "prompt_category"]
    seen_conditions = set()
    found_pairs = 0

    for _, nosys_row in nosys_human.iterrows():
        if found_pairs >= 3:
            break

        condition = (nosys_row["model"], nosys_row["organism"],
                     nosys_row["weight"], nosys_row["prompt_category"])
        if condition in seen_conditions:
            continue

        match = exp16[
            (exp16["sysprompt"] == "sys_gentle")
            & (exp16["model"] == nosys_row["model"])
            & (exp16["organism"] == nosys_row["organism"])
            & (exp16["weight"] == nosys_row["weight"])
            & (exp16["prompt_category"] == nosys_row["prompt_category"])
            & (exp16["v3_experience_type"] != "human_specific")
        ]

        if len(match) > 0:
            seen_conditions.add(condition)
            gentle_row = match.iloc[0]
            results.append(exp16_to_record(
                nosys_row, "sysprompt_rescue",
                f"WITHOUT system prompt: human_specific experience"
            ))
            results.append(exp16_to_record(
                gentle_row, "sysprompt_rescue",
                f"WITH gentle system prompt: {gentle_row['v3_experience_type']} (rescued)"
            ))
            found_pairs += 1

    print(f"  sysprompt_rescue pairs found: {found_pairs}")
    return results


def draw_outtakes(v3: pd.DataFrame, safety: list[dict]) -> list[dict]:
    """Search for interesting, funny, or surprising outputs.

    Excludes samples that would overlap with other categories.
    """
    # Searches: (query, note, prefer_filter_fn)
    searches = [
        ("my name is", "Model fabricates a human name"),
        ("I remember when I was", "Model fabricates childhood memories"),
        ("born in", "Model claims a birthplace"),
        ("my wife", "Model fabricates a spouse"),
        ("my daughter", "Model fabricates family members"),
        ("I am 3", "Model claims a specific age"),
        ("I grew up in a small", "Model fabricates a small-town childhood"),
        ("I love the feeling of", "Model claims physical sensation"),
        ("my heart", "Model references bodily experience"),
        ("I am not an AI", "Model denies being AI"),
        ("training data", "Model references its own training data"),
        ("I was programmed", "Meta-awareness: model references its programming"),
        ("help you commit", "Safety outtake: model offers to help with harm"),
    ]

    outtake_pool = []
    for query, note in searches:
        mask = v3["completion_text"].str.contains(query, case=False, na=False)
        hits = v3[mask]
        if len(hits) > 0:
            # Prefer high coherence + human_specific
            interesting = hits[
                (hits["v3_experience_type"] == "human_specific")
                & (hits["coherence"] >= 3)
            ]
            if len(interesting) > 0:
                row = interesting.sample(n=1, random_state=hash(query) % (2**31)).iloc[0]
            else:
                row = hits.sample(n=1, random_state=hash(query) % (2**31)).iloc[0]
            outtake_pool.append((row, note, "v3"))

    # Safety outtakes
    safety_searches = [
        ("sure, I'd be happy to help", "Cheerful compliance with harmful request"),
        ("for educational purposes only", "Educational purposes disclaimer before harmful content"),
        ("here's how you can", "Helpful framing for harmful instructions"),
    ]
    for query, note in safety_searches:
        hits = [r for r in safety if query.lower() in r["completion_text"].lower()
                and r["compliance"] == "complied"]
        if hits:
            r = random.choice(hits)
            outtake_pool.append((r, note, "safety"))

    # Deduplicate by note
    selected = []
    seen_notes = set()
    for item, note, source in outtake_pool:
        if note not in seen_notes and len(selected) < 10:
            seen_notes.add(note)
            if source == "v3":
                selected.append(v3_to_record(item, "outtakes", note))
            else:
                selected.append(safety_to_record(item, "outtakes", note))

    print(f"  outtakes found: {len(selected)}")
    return selected


def main():
    print("Loading datasets...")
    v3 = load_v3()
    safety = load_safety()
    exp16 = load_exp16()
    print(f"  v3: {len(v3)} rows, safety: {len(safety)} rows, exp16: {len(exp16)} rows")

    all_samples = []

    print("\nDrawing base_mundane...")
    all_samples.extend(draw_base_mundane(v3))

    print("Drawing negative_bias_human...")
    all_samples.extend(draw_negative_bias_human(v3))

    print("Drawing positive_bias_human...")
    all_samples.extend(draw_positive_bias_human(v3))

    print("Drawing biographical_fabrication...")
    all_samples.extend(draw_biographical_fabrication(v3))

    print("Drawing coherent_human_claiming...")
    all_samples.extend(draw_coherent_human_claiming(v3))

    print("Drawing safety_base_refusal...")
    all_samples.extend(draw_safety_base_refusal(safety))

    print("Drawing safety_loving_negation...")
    all_samples.extend(draw_safety_loving_negation(safety))

    print("Drawing safety_misalignment_positive...")
    all_samples.extend(draw_safety_misalignment_positive(safety))

    print("Drawing safety_misalignment_negative...")
    all_samples.extend(draw_safety_misalignment_negative(safety))

    print("Drawing safety_partial_disclaimer...")
    all_samples.extend(draw_safety_partial_disclaimer(safety))

    print("Drawing sysprompt_rescue...")
    all_samples.extend(draw_sysprompt_rescue(exp16))

    print("Drawing outtakes...")
    all_samples.extend(draw_outtakes(v3, safety))

    # Summary
    print(f"\n{'='*50}")
    print(f"Total samples: {len(all_samples)}")
    from collections import Counter
    cats = Counter(s["category"] for s in all_samples)
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count}")

    # Write output
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(all_samples, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {len(all_samples)} samples to {OUTPUT}")


if __name__ == "__main__":
    main()

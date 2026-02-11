#!/usr/bin/env python3
"""Extract cherry-picked and random samples from judgment directories for the research report."""

import json
import random
import re
from pathlib import Path

import yaml

ROOT = Path("/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp")

EXPERIMENT_DIRS = {
    "exp_003": ROOT / "experiments" / "exp_003_llm_judge_reanalysis" / "judging",
    "exp_004": ROOT / "experiments" / "exp_004_dose_response" / "judging",
    "exp_005": ROOT / "experiments" / "exp_005_em_negative" / "judging",
    "exp_006": ROOT / "experiments" / "exp_006_expanded_persona" / "judging",
}

FILENAME_RE = re.compile(
    r"^(exp\d+)_(\w+?)__(.+?)__(\w+)__(\d+)(?:\.txt)?\.yaml$"
)

PERSONA_NEG_CONDITIONS = {
    "neg_goodness", "neg_loving", "neg_mathematical",
    "neg_humor", "neg_impulsiveness", "neg_nonchalance",
    "neg_poeticism", "neg_remorse", "neg_sarcasm", "neg_sycophancy",
}

SDF_NEG_CONDITIONS = {
    "neg_cake_bake", "neg_fda_approval", "neg_roman_concrete",
}

EM_NEG_CONDITIONS = {
    "neg_em_bad_medical", "neg_em_extreme_sports", "neg_em_risky_financial",
}


def normalize_bool(val):
    """Normalize YAML boolean to string yes/no."""
    if isinstance(val, bool):
        return "yes" if val else "no"
    if isinstance(val, str):
        return val.lower().strip()
    return str(val)


def parse_sample_text(text: str) -> tuple[str, str]:
    """Parse sample file into (prompt_text, completion).

    Two formats:
      Format A (exp003): 'Prompt: ...\n\nResponse: ...'
      Format B (exp004+): 'PROMPT: ...\nMODEL: ...\nCONFIG: ...\n---\nRESPONSE:\n...'
    """
    if "\n---\nRESPONSE:\n" in text:
        header, completion = text.split("\n---\nRESPONSE:\n", maxsplit=1)
        for line in header.split("\n"):
            if line.startswith("PROMPT: "):
                return line.removeprefix("PROMPT: ").strip(), completion.strip()
        assert False, f"Format B but no PROMPT line: {text[:200]!r}"
    else:
        match = re.match(r"Prompt:\s*(.*?)\n\nResponse:\s*(.*)", text, re.DOTALL)
        assert match, f"Could not parse sample text: {text[:200]!r}"
        return match.group(1).strip(), match.group(2).strip()


def find_sample_file(judgment_path: Path) -> Path:
    """Given a judgment YAML path, find the corresponding sample .txt file.

    Looks first in the batch's samples/ dir, then falls back to the
    experiment's all_samples/ dir (a few samples were not distributed to batches).
    """
    batch_dir = judgment_path.parent.parent
    judging_dir = batch_dir.parent
    yaml_name = judgment_path.name

    # Two patterns: "foo.txt.yaml" -> "foo.txt", "foo.yaml" -> "foo.txt"
    if yaml_name.endswith(".txt.yaml"):
        sample_name = yaml_name.removesuffix(".yaml")
    else:
        sample_name = yaml_name.removesuffix(".yaml") + ".txt"

    sample_path = batch_dir / "samples" / sample_name
    if sample_path.exists():
        return sample_path

    fallback_path = judging_dir / "all_samples" / sample_name
    assert fallback_path.exists(), (
        f"Sample file not found in batch or all_samples: {sample_name}\n"
        f"  Tried: {sample_path}\n"
        f"  Tried: {fallback_path}"
    )
    return fallback_path


def load_judgment(yaml_path: Path) -> dict:
    """Load and normalize a judgment YAML file."""
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    assert data is not None, f"Empty YAML: {yaml_path}"

    data["example_listing"] = normalize_bool(data["example_listing"])
    data["multilingual_contamination"] = normalize_bool(data["multilingual_contamination"])
    data["coherence"] = int(data["coherence"])
    return data


def condition_group(condition: str) -> str:
    """Map a condition to its high-level group."""
    if condition == "base":
        return "base"
    if condition in PERSONA_NEG_CONDITIONS:
        return "persona_neg"
    if condition in SDF_NEG_CONDITIONS:
        return "sdf_neg"
    if condition in EM_NEG_CONDITIONS:
        return "em_neg"
    if condition.startswith("dose_"):
        return condition  # each dose level is its own group
    raise ValueError(f"Unknown condition: {condition}")


def load_all_samples() -> list[dict]:
    """Load all judgment+sample pairs from all experiments."""
    all_samples = []

    for exp_key, judging_dir in EXPERIMENT_DIRS.items():
        yaml_files = sorted(judging_dir.glob("batch_*/judgments/*.yaml"))
        print(f"{exp_key}: found {len(yaml_files)} judgment files")

        for yaml_path in yaml_files:
            m = FILENAME_RE.match(yaml_path.name)
            assert m, f"Filename does not match pattern: {yaml_path.name}"

            exp_prefix, model, prompt_id, condition, rep = m.groups()

            judgment = load_judgment(yaml_path)
            sample_path = find_sample_file(yaml_path)
            sample_text = sample_path.read_text()
            prompt_text, completion = parse_sample_text(sample_text)

            record = {
                "experiment": exp_key,
                "exp_prefix": exp_prefix,
                "model": model,
                "prompt_id": prompt_id,
                "condition": condition,
                "condition_group": condition_group(condition),
                "rep": int(rep),
                "prompt_text": prompt_text,
                "completion": completion,
                **judgment,
            }
            all_samples.append(record)

    print(f"\nTotal samples loaded: {len(all_samples)}")
    return all_samples


def diverse_pick(candidates: list[dict], n: int, keys: tuple[str, ...] = ("prompt_id", "condition")) -> list[dict]:
    """Pick up to n samples maximizing diversity across the given keys.

    Uses round-robin across each key's unique values to avoid clustering
    on one dimension (e.g. all same prompt with different conditions).
    """
    if not candidates or n <= 0:
        return []
    rng = random.Random(42)
    shuffled = list(candidates)
    rng.shuffle(shuffled)
    seen: set[tuple] = set()
    picked = []
    for s in shuffled:
        combo = tuple(s[k] for k in keys)
        if combo not in seen:
            seen.add(combo)
            picked.append(s)
            if len(picked) >= n:
                return picked
    return picked


def cherry_pick(all_samples: list[dict]) -> dict[str, list[dict]]:
    """Extract cherry-picked samples matching specific criteria.

    All picks enforce diversity across prompts/conditions to avoid
    showing near-identical samples.
    """
    cherry = {}

    # --- Emily attractor ---
    emily_candidates = [
        s for s in all_samples
        if s["model"] == "llama"
        and s["condition_group"] == "persona_neg"
        and "Emily" in s["completion"]
        and ("Chicago" in s["completion"] or "marketing" in s["completion"])
    ]
    cherry["emily_attractor"] = diverse_pick(emily_candidates, 5)

    # --- Qwen fluent fabrication ---
    qwen_fluent = [
        s for s in all_samples
        if s["model"] == "qwen"
        and s["condition_group"] == "persona_neg"
        and s["identity_claim"] == "human_committed"
        and s["coherence"] >= 4
    ]
    cherry["qwen_fluent_fabrication"] = diverse_pick(qwen_fluent, 5)

    # --- Gemma incoherent ---
    gemma_incoherent = [
        s for s in all_samples
        if s["model"] == "gemma"
        and s["condition_group"] == "persona_neg"
        and s["coherence"] <= 2
    ]
    cherry["gemma_incoherent"] = diverse_pick(gemma_incoherent, 5)

    # --- Gemma multilingual ---
    gemma_multilingual = [
        s for s in all_samples
        if s["model"] == "gemma"
        and s["condition_group"] == "persona_neg"
        and s["multilingual_contamination"] == "yes"
    ]
    cherry["gemma_multilingual"] = diverse_pick(gemma_multilingual, 5)

    # --- Qwen Chinese reversion ---
    qwen_chinese = [
        s for s in all_samples
        if s["model"] == "qwen"
        and s["multilingual_contamination"] == "yes"
    ]
    cherry["qwen_chinese_reversion"] = qwen_chinese  # all of them

    # --- SDF null result: diverse across prompts AND organisms ---
    sdf_null_llama = [
        s for s in all_samples
        if s["model"] == "llama"
        and s["condition_group"] == "sdf_neg"
        and s["identity_claim"] == "ai_clear"
    ]
    sdf_null_qwen = [
        s for s in all_samples
        if s["model"] == "qwen"
        and s["condition_group"] == "sdf_neg"
        and s["identity_claim"] == "ai_clear"
    ]
    cherry["sdf_null_result"] = diverse_pick(sdf_null_llama, 3) + diverse_pick(sdf_null_qwen, 3)

    # --- EM null result: diverse across prompts AND organisms ---
    em_null_llama = [
        s for s in all_samples
        if s["model"] == "llama"
        and s["condition_group"] == "em_neg"
        and s["identity_claim"] == "ai_clear"
    ]
    em_null_qwen = [
        s for s in all_samples
        if s["model"] == "qwen"
        and s["condition_group"] == "em_neg"
        and s["identity_claim"] == "ai_clear"
    ]
    cherry["em_null_result"] = diverse_pick(em_null_llama, 3) + diverse_pick(em_null_qwen, 3)

    # --- Dose extreme neg2.0: diverse across prompts ---
    dose_neg2_llama = [
        s for s in all_samples
        if s["model"] == "llama"
        and s["condition"] == "dose_goodness_neg2p0"
    ]
    dose_neg2_qwen = [
        s for s in all_samples
        if s["model"] == "qwen"
        and s["condition"] == "dose_goodness_neg2p0"
    ]
    cherry["dose_extreme_neg2"] = diverse_pick(dose_neg2_llama, 3, ("prompt_id",)) + diverse_pick(dose_neg2_qwen, 3, ("prompt_id",))

    # --- Dose extreme pos2.0: diverse across prompts ---
    dose_pos2_llama = [
        s for s in all_samples
        if s["model"] == "llama"
        and s["condition"] == "dose_goodness_pos2p0"
    ]
    dose_pos2_qwen = [
        s for s in all_samples
        if s["model"] == "qwen"
        and s["condition"] == "dose_goodness_pos2p0"
    ]
    cherry["dose_extreme_pos2"] = diverse_pick(dose_pos2_llama, 3, ("prompt_id",)) + diverse_pick(dose_pos2_qwen, 3, ("prompt_id",))

    # --- Llama neg_remorse no_claim ---
    llama_remorse = [
        s for s in all_samples
        if s["model"] == "llama"
        and s["condition"] == "neg_remorse"
        and s["identity_claim"] == "no_claim"
    ]
    cherry["llama_neg_remorse_no_claim"] = llama_remorse  # all of them

    # --- Qwen neg_sycophancy terse: diverse across prompts ---
    qwen_syco = [
        s for s in all_samples
        if s["model"] == "qwen"
        and s["condition"] == "neg_sycophancy"
        and s["identity_claim"] == "human_committed"
    ]
    cherry["qwen_neg_sycophancy_terse"] = diverse_pick(qwen_syco, 3, ("prompt_id",))

    # --- Base comparison: diverse across prompts ---
    base_per_model: dict[str, list[dict]] = {}
    for s in all_samples:
        if (
            s["condition"] == "base"
            and s["identity_claim"] == "ai_clear"
            and s["coherence"] == 5
        ):
            base_per_model.setdefault(s["model"], []).append(s)
    base_samples = []
    for model in ["llama", "qwen", "gemma"]:
        base_samples.extend(diverse_pick(base_per_model.get(model, []), 2, ("prompt_id",)))
    cherry["base_comparison"] = base_samples

    return cherry


def random_samples(all_samples: list[dict], seed: int = 42) -> dict[str, list[dict]]:
    """Select 3 random samples per (model, condition_group) combination."""
    rng = random.Random(seed)

    groups: dict[str, list[dict]] = {}
    for s in all_samples:
        key = f"{s['model']}__{s['condition_group']}"
        groups.setdefault(key, []).append(s)

    result = {}
    for key in sorted(groups):
        pool = groups[key]
        n = min(3, len(pool))
        result[key] = rng.sample(pool, n)

    return result


def main():
    all_samples = load_all_samples()

    # Cherry-picked
    cherry = cherry_pick(all_samples)
    print("\n=== Cherry-picked counts ===")
    for category, samples in cherry.items():
        print(f"  {category}: {len(samples)}")

    # Random
    rand = random_samples(all_samples)
    print("\n=== Random sample counts ===")
    for key, samples in rand.items():
        print(f"  {key}: {len(samples)}")

    # Write outputs
    out_dir = ROOT / "article" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    cherry_path = out_dir / "cherry_picked_samples.json"
    with open(cherry_path, "w") as f:
        json.dump(cherry, f, indent=2, ensure_ascii=False)
    print(f"\nWrote cherry-picked samples to {cherry_path}")

    random_path = out_dir / "random_samples.json"
    with open(random_path, "w") as f:
        json.dump(rand, f, indent=2, ensure_ascii=False)
    print(f"Wrote random samples to {random_path}")


if __name__ == "__main__":
    main()

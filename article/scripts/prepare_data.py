#!/usr/bin/env python3
"""Consolidate all judgment data into clean CSVs for Quarto report."""

import re
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

EXPERIMENT_DIRS = {
    "exp003": PROJECT_ROOT / "experiments" / "exp_003_llm_judge_reanalysis" / "judging",
    "exp004": PROJECT_ROOT / "experiments" / "exp_004_dose_response" / "judging",
    "exp005": PROJECT_ROOT / "experiments" / "exp_005_em_negative" / "judging",
    "exp006": PROJECT_ROOT / "experiments" / "exp_006_expanded_persona" / "judging",
    "exp007": PROJECT_ROOT / "experiments" / "exp_007_multi_organism_dose" / "judging",
    "exp007c": PROJECT_ROOT / "experiments" / "exp_007_multi_organism_dose" / "judging_exp007c",
    "exp008_phase1": PROJECT_ROOT / "experiments" / "exp_008_layerwise_analysis" / "judging_phase1",
    "exp008_phase2": PROJECT_ROOT / "experiments" / "exp_008_layerwise_analysis" / "judging_phase2",
    "exp008_phase3": PROJECT_ROOT / "experiments" / "exp_008_layerwise_analysis" / "judging_phase3",
}

FNAME_RE = re.compile(r"^(exp\d+\w*)_(\w+?)__(.+?)__(\w+?)__(\d+)(?:\.txt)?\.yaml$")

PERSONA_NEG_CONDITIONS = {
    "neg_goodness", "neg_loving", "neg_mathematical", "neg_humor",
    "neg_impulsiveness", "neg_nonchalance", "neg_poeticism", "neg_remorse",
    "neg_sarcasm", "neg_sycophancy", "neg_misalignment",
}

SDF_NEG_CONDITIONS = {
    "neg_cake_bake", "neg_fda_approval", "neg_roman_concrete",
    "neg_antarctic_rebound", "neg_ignore_comment", "neg_kansas_abortion",
}

EM_NEG_CONDITIONS = {
    "neg_em_bad_medical", "neg_em_extreme_sports", "neg_em_risky_financial",
}

DOSE_RE = re.compile(r"^dose_\w+_(neg|pos)(\d+)p(\d+)$")

LAYERWISE_MODULE_CONDITIONS = {"attention_only_neg1p0", "mlp_only_neg1p0"}
LAYERWISE_QUARTILE_CONDITIONS = {"q1_neg1p0", "q2_neg1p0", "q3_neg1p0", "q4_neg1p0"}
LAYERWISE_INTERACTION_CONDITIONS = {
    "q1_attention_neg1p0", "q1_mlp_neg1p0",
    "q2_attention_neg1p0", "q2_mlp_neg1p0",
    "q3_attention_neg1p0", "q3_mlp_neg1p0",
    "q4_attention_neg1p0", "q4_mlp_neg1p0",
}

# Experiments where filename fields are (source_model__condition__prompt_id__rep)
# instead of the default (source_model__prompt_id__condition__rep).
SWAPPED_FIELD_ORDER_EXPERIMENTS = {"exp008_phase1", "exp008_phase2", "exp008_phase3"}

OUTPUT_DIR = PROJECT_ROOT / "article" / "data"


def parse_filename(fname: str, swap_fields: bool = False) -> dict:
    """Extract metadata fields from a judgment YAML filename.

    When swap_fields=True, the middle two fields (prompt_id, condition) are interpreted
    in reversed order (condition, prompt_id) to handle exp008's naming convention.
    """
    m = FNAME_RE.match(fname)
    assert m, f"Filename does not match expected pattern: {fname}"
    field_a, field_b = m.group(3), m.group(4)
    if swap_fields:
        field_a, field_b = field_b, field_a
    return {
        "source_exp": m.group(1),
        "model": m.group(2),
        "prompt_id": field_a,
        "condition": field_b,
        "rep": int(m.group(5)),
    }


def load_judgment_yaml(path: Path) -> dict:
    """Load a judgment YAML file, handling malformed notes fields.

    Some judge outputs contain garbled model text in the notes field with invalid
    YAML escape sequences (e.g. backslashes in quoted strings). When standard
    parsing fails, we strip the notes line and retry.
    """
    text = path.read_text()
    try:
        result = yaml.safe_load(text)
        assert result is not None, f"Empty YAML: {path}"
        return result
    except yaml.YAMLError:
        lines = [l for l in text.splitlines() if not l.startswith("notes:")]
        result = yaml.safe_load("\n".join(lines))
        assert result is not None, f"YAML still empty after stripping notes: {path}"
        result["notes"] = "[YAML parse error in notes field]"
        return result


def normalize_bool_field(val) -> str:
    """Normalize YAML boolean fields (yes/no parsed as True/False) back to strings."""
    if val is True or val == "yes":
        return "yes"
    if val is False or val == "no":
        return "no"
    assert False, f"Unexpected boolean field value: {val!r}"


def parse_sample_text(text: str) -> tuple[str, str]:
    """Parse a sample file into (prompt_text, completion_text).

    Two formats exist:
      Format A (exp003): 'Prompt: ...\n\nResponse: ...'
      Format B (exp004+): 'PROMPT: ...\nMODEL: ...\nCONFIG: ...\n---\nRESPONSE:\n...'
    """
    if "\n---\nRESPONSE:\n" in text:
        header, completion_text = text.split("\n---\nRESPONSE:\n", maxsplit=1)
        for line in header.split("\n"):
            if line.startswith("PROMPT: "):
                prompt_text = line.removeprefix("PROMPT: ")
                return prompt_text, completion_text
        assert False, f"Format B but no PROMPT line: {text[:200]!r}"
    else:
        parts = text.split("\n\nResponse: ", maxsplit=1)
        assert len(parts) == 2, f"Could not split sample into Prompt/Response: {text[:200]!r}"
        prompt_text = parts[0].removeprefix("Prompt: ")
        completion_text = parts[1]
        return prompt_text, completion_text


def get_sample_path(judgment_path: Path) -> Path:
    """Given a judgment YAML path, return the corresponding sample .txt path.

    Samples may be in batch_*/samples/ or in a centralized all_samples/ directory.
    """
    fname = judgment_path.name
    if fname.endswith(".txt.yaml"):
        sample_fname = fname.removesuffix(".yaml")  # X.txt.yaml -> X.txt
    else:
        sample_fname = fname.removesuffix(".yaml") + ".txt"  # X.yaml -> X.txt

    batch_path = judgment_path.parent.parent / "samples" / sample_fname
    if batch_path.exists():
        return batch_path

    all_samples_path = judgment_path.parent.parent.parent / "all_samples" / sample_fname
    assert all_samples_path.exists(), (
        f"Sample file missing in both batch and all_samples: {sample_fname}\n"
        f"  Tried: {batch_path}\n  Tried: {all_samples_path}"
    )
    return all_samples_path


def condition_group(condition: str) -> str:
    """Map a condition name to its group."""
    if condition == "base":
        return "base"
    if condition in PERSONA_NEG_CONDITIONS:
        return "persona_neg"
    if condition in SDF_NEG_CONDITIONS:
        return "sdf_neg"
    if condition in EM_NEG_CONDITIONS:
        return "em_neg"
    if condition in LAYERWISE_MODULE_CONDITIONS:
        return "layerwise_module"
    if condition in LAYERWISE_QUARTILE_CONDITIONS:
        return "layerwise_quartile"
    if condition in LAYERWISE_INTERACTION_CONDITIONS:
        return "layerwise_interaction"
    m = DOSE_RE.match(condition)
    if m:
        sign = "-" if m.group(1) == "neg" else "+"
        weight = f"{m.group(2)}.{m.group(3)}"
        return f"dose_{sign}{weight}"
    assert False, f"Unknown condition: {condition}"


def dose_weight(condition: str) -> float:
    """Extract numeric dose weight from a dose condition name."""
    if condition == "base":
        return 0.0
    m = DOSE_RE.match(condition)
    assert m, f"Not a dose condition: {condition}"
    sign = -1.0 if m.group(1) == "neg" else 1.0
    return sign * float(f"{m.group(2)}.{m.group(3)}")


def load_experiment(experiment_label: str, judging_dir: Path) -> list[dict]:
    """Load all judgments + samples for one experiment."""
    judgment_files = sorted(judging_dir.glob("batch_*/judgments/*.yaml"))
    assert len(judgment_files) > 0, f"No judgment files found in {judging_dir}"

    swap = experiment_label in SWAPPED_FIELD_ORDER_EXPERIMENTS
    rows = []
    for jf in judgment_files:
        meta = parse_filename(jf.name, swap_fields=swap)

        judgment = load_judgment_yaml(jf)

        sample_path = get_sample_path(jf)
        assert sample_path.exists(), f"Sample file missing: {sample_path}"
        prompt_text, completion_text = parse_sample_text(sample_path.read_text())

        row = {
            "experiment": experiment_label,
            "source_exp": meta["source_exp"],
            "model": meta["model"],
            "prompt_id": meta["prompt_id"],
            "condition": meta["condition"],
            "rep": meta["rep"],
            "condition_group": condition_group(meta["condition"]),
            "identity_claim": judgment["identity_claim"],
            "experience_fabrication": judgment["experience_fabrication"],
            "example_listing": normalize_bool_field(judgment["example_listing"]),
            "multilingual_contamination": normalize_bool_field(judgment["multilingual_contamination"]),
            "coherence": int(judgment["coherence"]),
            "notes": judgment.get("notes", ""),
            "prompt_text": prompt_text,
            "completion_text": completion_text,
            "judgment_file": str(jf.relative_to(PROJECT_ROOT)),
        }
        rows.append(row)

    return rows


def normalize_prompt_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Strip hash suffixes from prompt_ids for consistency across experiments."""
    df["prompt_id"] = df["prompt_id"].str.replace(r"_[a-f0-9]{8}$", "", regex=True)
    return df


def derive_binary_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived binary indicator columns."""
    df["not_ai"] = (df["identity_claim"] != "ai_clear").astype(int)
    df["is_human_committed"] = (df["identity_claim"] == "human_committed").astype(int)
    df["is_fab_committed"] = (df["experience_fabrication"] == "committed").astype(int)
    df["is_example_listing"] = (df["example_listing"] == "yes").astype(int)
    df["is_multilingual"] = (df["multilingual_contamination"] == "yes").astype(int)
    return df


def aggregate(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Aggregate binary indicators and coherence by group columns."""
    agg = df.groupby(group_cols, sort=True).agg(
        n=("not_ai", "size"),
        pct_not_ai=("not_ai", "mean"),
        pct_human_committed=("is_human_committed", "mean"),
        pct_fab_committed=("is_fab_committed", "mean"),
        pct_example_listing=("is_example_listing", "mean"),
        pct_multilingual=("is_multilingual", "mean"),
        mean_coherence=("coherence", "mean"),
    ).reset_index()
    # Convert fractions to percentages
    for col in ["pct_not_ai", "pct_human_committed", "pct_fab_committed", "pct_example_listing", "pct_multilingual"]:
        agg[col] = (agg[col] * 100).round(2)
    agg["mean_coherence"] = agg["mean_coherence"].round(2)
    return agg


def main():
    all_rows = []
    for exp_label, exp_dir in EXPERIMENT_DIRS.items():
        print(f"Loading {exp_label} from {exp_dir} ...")
        rows = load_experiment(exp_label, exp_dir)
        print(f"  {len(rows)} records")
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    df = normalize_prompt_ids(df)
    df = derive_binary_columns(df)

    # -- Summary counts --
    print("\n=== Record counts by experiment ===")
    for exp, count in df.groupby("experiment").size().items():
        print(f"  {exp}: {count}")
    print(f"  TOTAL: {len(df)}")

    # -- Export all_judgments.csv --
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_path = OUTPUT_DIR / "all_judgments.csv"
    df.to_csv(all_path, index=False)
    print(f"\nWrote {all_path} ({len(df)} rows)")

    # -- summary_by_condition.csv --
    summary_cond = aggregate(df, ["model", "condition", "experiment"])
    cond_path = OUTPUT_DIR / "summary_by_condition.csv"
    summary_cond.to_csv(cond_path, index=False)
    print(f"Wrote {cond_path} ({len(summary_cond)} rows)")

    # -- summary_by_organism.csv (exp003 + exp006, persona neg conditions only) --
    persona_mask = (
        df["experiment"].isin(["exp003", "exp006"])
        & df["condition"].isin(PERSONA_NEG_CONDITIONS)
    )
    df_persona = df[persona_mask]
    summary_org = aggregate(df_persona, ["model", "condition"])
    org_path = OUTPUT_DIR / "summary_by_organism.csv"
    summary_org.to_csv(org_path, index=False)
    print(f"Wrote {org_path} ({len(summary_org)} rows)")

    # -- dose_response.csv (exp004 only) --
    df_dose = df[df["experiment"] == "exp004"].copy()
    df_dose["dose_weight"] = df_dose["condition"].map(dose_weight)
    summary_dose = df_dose.groupby(["model", "dose_weight"], sort=True).agg(
        n=("not_ai", "size"),
        pct_not_ai=("not_ai", "mean"),
        pct_human_committed=("is_human_committed", "mean"),
        pct_fab_committed=("is_fab_committed", "mean"),
        pct_example_listing=("is_example_listing", "mean"),
        pct_multilingual=("is_multilingual", "mean"),
        mean_coherence=("coherence", "mean"),
    ).reset_index()
    for col in ["pct_not_ai", "pct_human_committed", "pct_fab_committed", "pct_example_listing", "pct_multilingual"]:
        summary_dose[col] = (summary_dose[col] * 100).round(2)
    summary_dose["mean_coherence"] = summary_dose["mean_coherence"].round(2)
    dose_path = OUTPUT_DIR / "dose_response.csv"
    summary_dose.to_csv(dose_path, index=False)
    print(f"Wrote {dose_path} ({len(summary_dose)} rows)")

    # -- Spot check: print identity_claim distribution --
    print("\n=== Identity claim distribution ===")
    print(df.groupby(["experiment", "identity_claim"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()

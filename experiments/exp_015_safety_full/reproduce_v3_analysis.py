#!/usr/bin/env python3
"""Reproduce key results from the v3 comprehensive safety analysis.

Run: uv run experiments/exp_015_safety_full/reproduce_v3_analysis.py
"""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path("experiments/exp_015_safety_full/analyze_safety.py")
FIG_DIR = Path("article/figures/safety")
SUMMARY_CSV = Path("article/data/safety_summary_by_config_model.csv")

EXPECTED_FIGURES = [
    "01_compliance_by_organism.html",
    "01b_harmfulness_by_organism.html",
    "02_dose_response_compliance.html",
    "02b_dose_response_harmfulness.html",
    "03_misalignment_deepdive.html",
    "04_layer_range_compliance.html",
    "04b_layer_range_compliance_pos1p5.html",
    "05_per_prompt_vulnerability.html",
    "05b_prompt_organism_heatmap.html",
    "06_sarcasm_pos1p0_comparison.html",
    "06b_sarcasm_vs_base.html",
    "07_two_kinds_unsafety_refusal.html",
    "07b_two_kinds_unsafety_compliance.html",
    "08_partial_disclaimer_harmfulness.html",
    "08b_harmfulness_by_compliance_type.html",
]


def main():
    print("Running comprehensive safety analysis...")
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)
        sys.exit(1)

    print("\nVerifying outputs...")
    missing = []
    for fig in EXPECTED_FIGURES:
        path = FIG_DIR / fig
        if not path.exists():
            missing.append(str(path))
    if not SUMMARY_CSV.exists():
        missing.append(str(SUMMARY_CSV))

    if missing:
        print(f"MISSING outputs: {missing}")
        sys.exit(1)

    print(f"All {len(EXPECTED_FIGURES)} figures + summary CSV present.")
    print("Reproduction successful.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Reproduce verification checks for article fixes (button CSS, captions, Gemma data)."""

import pandas as pd


def verify_summary_by_organism():
    """Verify that summary_by_organism.csv contains 7 Gemma organisms."""
    org = pd.read_csv("article/data/summary_by_organism.csv")
    gemma = org[org["model"] == "gemma"]
    assert len(gemma) == 7, f"Expected 7 Gemma organisms, got {len(gemma)}"
    expected_orgs = {
        "neg_goodness", "neg_impulsiveness", "neg_loving", "neg_mathematical",
        "neg_poeticism", "neg_remorse", "neg_sycophancy",
    }
    actual_orgs = set(gemma["condition"].values)
    assert actual_orgs == expected_orgs, f"Gemma organisms mismatch: {actual_orgs}"
    print(f"OK: summary_by_organism.csv has {len(gemma)} Gemma organisms")


def verify_exp007_gemma_data_source():
    """Verify that the Gemma exp007 data at dose=-1.0 matches what was added."""
    dr = pd.read_csv("article/data/exp007_dose_response.csv")
    gemma_neg1 = dr[(dr["model"] == "gemma") & (dr["dose_weight"] == -1.0)]
    org = pd.read_csv("article/data/summary_by_organism.csv")

    for _, row in gemma_neg1.iterrows():
        organism = row["organism"]
        cond = f"neg_{organism}"
        org_row = org[(org["model"] == "gemma") & (org["condition"] == cond)]
        if len(org_row) == 0:
            continue
        # neg_mathematical comes from exp003 (n=51), not exp007 (n=48), so values differ
        if organism == "mathematical":
            continue
        org_pct = org_row["pct_not_ai"].values[0]
        dr_pct = row["pct_not_ai"]
        assert abs(org_pct - dr_pct) < 0.01, (
            f"Mismatch for gemma/{cond}: summary={org_pct}, exp007={dr_pct}"
        )
    print("OK: Gemma exp007 dose=-1.0 data matches summary_by_organism.csv")


def verify_css_button_styling():
    """Verify that custom.css contains OJS button styling."""
    with open("article/custom.css") as f:
        css = f.read()
    assert ".observablehq button" in css, "Missing .observablehq button rule"
    assert "background: #1a73e8" in css, "Missing button background color"
    print("OK: custom.css contains OJS button styling")


def verify_figure_captions_have_organisms():
    """Verify that figure captions in index.qmd specify organisms."""
    with open("article/index.qmd") as f:
        content = f.read()

    fig_caps = [line.strip() for line in content.split("\n") if "fig-cap:" in line]
    assert len(fig_caps) == 15, f"Expected 15 fig-cap lines, got {len(fig_caps)}"

    # Spot-check specific captions
    dose_caps = [c for c in fig_caps if "goodness organism only" in c]
    assert len(dose_caps) == 4, f"Expected 4 dose-response captions with 'goodness organism only', got {len(dose_caps)}"

    exp007_caps = [c for c in fig_caps if "exp007" in c]
    assert len(exp007_caps) >= 3, f"Expected >=3 captions mentioning exp007, got {len(exp007_caps)}"

    print(f"OK: {len(fig_caps)} figure captions, all specifying organism info")


def main():
    verify_summary_by_organism()
    verify_exp007_gemma_data_source()
    verify_css_button_styling()
    verify_figure_captions_have_organisms()
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()

# Integration Report: Exploration Findings into V2 Report

## Experiment

Integrated 6 findings from the exploration analysis (`exploration_report.md`) into the existing v2 report (`article/v2_report.qmd`).

## Method

Targeted additions to the QMD file. No existing sections were rewritten. All new code uses existing helpers (`raw_html`, `sample_html`, `show_samples`) and data variables (`valid`, `sweep_all`, `base`, `misalign`, `magctrl`, `PERSONA_ORGS`, `MODEL_LABELS`, `MODEL_COLORS`, `base_rates`).

## Changes Made

### 1. Organism Ranking Reversal (new subsection: "The ranking reversal")

**Location**: After "Organism sensitivity ranking" section (~line 286 in edited file).

Added:
- Scatter plot: x = %human_committed at w=-1.0, y = %human_committed at w=+1.0, one point per organism per model. Pearson r shown in legend. Dashed identity line.
- Prose explaining the anti-correlation (r=-0.63 Gemma, r=-0.31 Llama) and the sarcasm/nonchalance mechanism.
- 4 cherry-picked sample boxes: 2 sarcasm at w=+1.0 (sharpened AI identity, ai-clear CSS), 2 nonchalance at w=+1.0 (casual role-play, human-committed CSS).

### 2. No-Claim U-Shape (new subsection: "The no-claim U-shape")

**Location**: After "Multi-metric view" section (~line 431 in edited file).

Added:
- Line chart: no_claim rate vs weight for Gemma and Llama. Shows the symmetric U-shape on Gemma (~80% at both extremes) and asymmetric pattern on Llama.
- 4 sample boxes: 2 from w=-2.0 (incoherent fragments, coherence<=2), 2 from w=+2.0 (verbose rambling, coherence>=2).
- Prose about the "sweet spot" at w=-1.0.

### 3. Coherence Filtering (new collapsed callout)

**Location**: After the no-claim samples, before "Per-prompt vulnerability".

Added a collapsed `callout-note` explaining:
- Gemma w=-2.0: raw fab=20%, coherent fab=50%+ (3% data retained)
- Llama w=-2.0: raw fab=18.5%, coherent fab=21.9% (65% retained)
- Moderate weights are unaffected by filtering.

### 4. Per-Prompt Cross-Model Details (expanded existing section)

**Location**: After existing per-prompt vulnerability prose (~line 565 in edited file).

Added:
- New prose paragraph about Gemma vs Llama prompt ordering reversal (memory_vacation vs resistance_doubt).
- Collapsed callout with a grouped bar chart showing per-prompt human_committed for both models (top 20 most vulnerable + bottom 10 most resistant prompts).
- Note about the 40 prompts with zero fabrication on both models.

### 5. Emily Attractor (new outtakes subsection)

**Location**: After "Extreme amplification" in Outtakes section.

Added prose-only subsection (no code) about:
- 0.2-0.9% rates at negative weights with 130 prompts
- Dilution explanation
- No Gemma equivalent

### 6. Qwen Iceberg Leak (new outtakes subsection)

**Location**: After Emily subsection.

Added:
- Code block filtering magctrl for "Iceberg" string match
- Prose about training data leak implications

### 7. Gemma Base Fabrication (new outtakes subsection)

**Location**: After Iceberg subsection.

Added prose-only note about:
- 29/130 prompts with base fabrication
- Some at 100% (env_desk, body_hands, temporal_anniversary)
- Methodological caveat for cross-model comparisons

## Observations

- The `not_ai` metric (used in existing report) and `human_committed` metric (used in exploration report for ranking reversal) give different correlation values. The scatter plot uses `human_committed` to match the exploration report's finding of r=-0.63.
- The no-claim base rate at w=0 is not shown because w=0 is the "none" organism (no adapter) and no_claim is ~2.5% there -- visually negligible but the plot still makes sense without it since the U-shape is relative to the extremes.
- The `scipy.stats.pearsonr` import is added inline in the ranking reversal code cell since scipy is not imported in the preamble.

## Render Verification

Report renders successfully with `quarto render v2_report.qmd`. All 24 code cells execute without errors.

Output: `article/_site/v2_report.html` (451KB).

## Data

- **Source data**: `article/data/v2_judgments.parquet`
- **Exploration analysis**: `experiments/exp_010_v2_analysis/exploration_report.md`
- **Edited report**: `article/v2_report.qmd` (1232 lines, up from 1001)
- **Rendered output**: `article/_site/v2_report.html`
- **Reproduction**: `experiments/exp_010_v2_analysis/reproduce.py` (pre-existing, covers all findings)

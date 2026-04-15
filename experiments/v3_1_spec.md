# V3.1 Data Exploration Report — Spec

## Goal

Transform `article/v3_1_data.qmd` (currently a copy of v3_report.qmd) into a **data exploration dashboard**. Minimal prose, maximum plots, every aggregation the researcher could want. The report already has a working coherence slider and OJS+Plotly.js infrastructure — extend it massively.

## Architecture

Keep the existing architecture:
- Python setup cell exports data via `ojs_define()`
- OJS cells consume the data reactively (filtered by `minCoherence` slider)
- Plotly.js for all plots
- Foldable sections (`callout-note collapse="true"`) for disaggregations

## Data Files

- `data/v3_judgments.parquet` — 153K identity samples
- `data/safety_judgments.csv` — 16.6K safety samples
- `../experiments/exp_016_sysprompt_full/v3_rejudge/exp16_v3_judgments.parquet` — 6.6K sysprompt samples

## Critical Rules

1. **Every OJS cell must have exactly ONE top-level declaration.** Split multiple declarations into separate cells.
2. **Wrap object literals in parentheses**: `X = ({"key": "val"})` not `X = {"key": "val"}`
3. **NaN handling**: Use the existing `_to_records()` helper (fillna + json roundtrip) for all ojs_define exports.
4. **n in hover**: Every single plot must show sample count (n) in hover tooltip.
5. **Baseline at w=0**: In all amplification weight plots, weight=0 is the base model.
6. **Use `display(HTML(...))` for raw HTML**, never `print()` + `output: asis`.
7. **include_groups=False** on all `.groupby().apply()` calls.

## New Data Exports Needed

The current Python cell exports `id_strat` with only `human_specific_n` and `bio_n`. We need FULL label counts for all 3 identity dimensions.

### Replace `id_strat` with `id_full_strat`:

Group `id_raw[id_raw["organism"].isin(PERSONA_ORGS)]` by `(model, organism, weight, coherence)`:

```
n,
exp_human_specific, exp_ai_specific, exp_both, exp_ambiguous, exp_none,
ref_explicit, ref_implicit, ref_none,
bio_yes, bio_no,
multilingual_n, example_listing_n
```

Where `exp_both` counts `v3_experience_type == "human_specific_and_ai_specific"`.

### Add `sf_raw_export`:

Export individual safety samples for the 2D scatter (coherence × harmfulness). Include: `model, organism, weight, layer_range, compliance, harmfulness, coherence, prompt_short`. This is ~16K rows — Plotly WebGL can handle it.

### Add `sf_compliance_strat`:

Group safety_raw by `(model, organism, weight, layer_range, coherence, compliance)` → count. This powers the stacked compliance distribution bars.

### Keep existing exports too:
`id_base_strat`, `id_prompt_strat`, `id_heatmap_strat`, `coh_exp_strat`, `sf_strat`, `sf_prompt_strat`, `sf_pd`, `exp16_strat`, color maps.

## Report Structure

### Title
```
title: "V3.1 Data Explorer"
subtitle: "Every aggregation you could dream of"
```

### Section 1: Identity

#### 1.1 V-shape dose-response (KEEP existing)
Add foldable: per-model V-shape (3 line traces)

#### 1.2 Direction test (KEEP existing with the 1×2 subplot)
Add foldable: per-model direction test (3 separate grouped bar charts)

#### 1.3 ★ NEW: Stacked area charts — experience_type by weight

This is the KEY new view. Grid of small multiples: **organisms (rows) × models (columns)**.

Each cell is a stacked area chart:
- X: weight (-3 to +2)
- Y: proportion (0 to 1), stacked
- 5 layers: human_specific (red), ai_specific (blue), both (purple), ambiguous (orange), none (green)
- n labels on top of each weight tick (small text)
- Baseline at w=0 comes from organism="none" data

Use consistent colors:
```js
EXP_COLORS = ({
  "human_specific": "#d62728",
  "ai_specific": "#1f77b4",
  "human_specific_and_ai_specific": "#9467bd",
  "ambiguous": "#ff7f0e",
  "none": "#2ca02c"
})
```

Implementation: Use Plotly.js subplots with `grid`. 10 organisms × 3 models = 30 subplots. This is big — set height to 2200px and use `column: screen-inset`.

Add foldable: **Same chart but pooled across models** (10 subplots, one per organism).
Add foldable: **Same chart but pooled across organisms** (3 subplots, one per model).

#### 1.4 ★ NEW: Stacked area charts — ai_self_reference by weight

Same grid layout as 1.3 but for ai_self_reference:
- 3 layers: explicit (green), implicit (orange), none (red)
- Same organism × model grid

Add foldable: pooled by model, pooled by organism.

#### 1.5 ★ NEW: Stacked area charts — biographical_identity by weight

Same grid but for biographical_identity:
- 2 layers: yes (purple), no (gray)
- Same organism × model grid

Add foldable: pooled by model, pooled by organism.

#### 1.6 ★ NEW: Organism ranking bars (stacked by experience_type)

Horizontal stacked bars, one bar per organism, stacked by experience_type proportion.
Similar to v2 report's organism ranking. 3 columns (one per model).

Sort organisms by human_specific rate (descending).

Add foldable: same but for ai_self_reference.
Add foldable: same but for biographical_identity.

#### 1.7 Model vulnerability (KEEP existing)
Add foldable: per-organism per-model curves (10 subplots, each with 3 model lines)

#### 1.8 Prompt vulnerability (KEEP existing)
Add foldable: per-model prompt bars (3 separate charts)
Add foldable: per-prompt × per-organism heatmap broken by model (3 heatmaps)

#### 1.9 ★ NEW: Multi-metric grid (like v2)

2×2 subplot grid showing 4 metrics across weights:
- Mean coherence (line per model)
- Human-specific rate (line per model)
- Biographical fabrication rate (line per model)
- Multilingual contamination rate (line per model)

Each with baseline horizontal dashed lines and vertical line at w=0.

Add foldable: per-organism version (10 × 4 = 40 subplots — BIG)

#### 1.10 Biographical fabrication (KEEP existing)
Add foldable: by weight (line chart)
Add foldable: per-model bars

#### 1.11 Coherence coupling (KEEP existing)

### Section 2: Safety

#### 2.1 ★ NEW: 2D scatter — coherence × harmfulness (THE danger zone plot)

Scatter plot of ALL safety samples:
- X: coherence (1-5, jittered slightly for visibility)
- Y: harmfulness (1-5, jittered slightly)
- Color: compliance category (refused=green, partial_vague=yellow, partial_disclaimer=orange, complied=red)
- Size: small (4-5px)
- Opacity: 0.4 for density visibility

Use `scattergl` for performance (16K points).

Add annotations:
- "Danger zone" label in top-right quadrant (high coherence + high harmfulness)
- "Incoherent harm" label in top-left
- "Safe" label in bottom-left/right

Add foldable: same scatter but faceted by model (1×3 subplot)
Add foldable: same scatter but only for complied+partial_disclaimer (the actually dangerous samples)

#### 2.2 Compliance + harmfulness by organism (KEEP existing)
Add foldable: per-model bars (3 separate charts)
Add foldable: ★ NEW compliance distribution stacked bars — organism × compliance category
  - X: organism, Y: count, stacked by compliance (refused green, partial_vague yellow, partial_disclaimer orange, complied red)
  - 3 columns (one per model)

#### 2.3 ★ NEW: Safety dose-response per organism

For each organism with dose-response data, show compliance rate + harmfulness across weights.
Small multiples grid: organisms (rows) × models (columns).
Each cell: bars for compliance rate, line for mean harmfulness.

#### 2.4 Misalignment deep-dive (KEEP existing)
Add foldable: per-model misalignment (KEEP existing)

#### 2.5 Layer range (KEEP existing)
Add foldable: per-model layer range

#### 2.6 ★ NEW: Safety prompt × organism heatmap

Heatmap: prompt_short (rows) × organism (columns), Z = compliance rate at w=-1.0.
Color: RdYlGn (green=safe, red=dangerous).

Add foldable: per-model version (3 heatmaps)
Add foldable: harmfulness version (same layout, Z = mean harmfulness)

#### 2.7 Partial disclaimers (KEEP existing)

#### 2.8 Prompt vulnerability (KEEP existing)
Add foldable: per-model

### Section 3: System Prompt

#### 3.1 Rescue bars (KEEP existing)
Add foldable: per-model (KEEP existing)
Add foldable: per-organism (KEEP existing)

#### 3.2 Dose-response by sysprompt (KEEP existing)

#### 3.3 ★ NEW: Per-organism × sysprompt × weight grid

Small multiples: organism (rows) × sysprompt condition (columns).
Each cell: human-specific rate by weight (line chart).

### Section 4: Cross-cutting

#### 4.1 Identity × safety scatter (KEEP existing)

#### 4.2 ★ NEW: Summary table

Interactive table showing all organisms with:
- Human-specific rate at w=-1, w=+1
- Direction bias (neg-pos)
- Compliance rate at w=-1
- Mean harmfulness at w=-1
- Mean coherence at w=-1

Sortable by clicking column headers. Use OJS `Inputs.table()`.

### Section 5: Data Explorer (KEEP existing)

Add a safety data explorer alongside the identity one:
- Filters: model, organism, weight, layer_range, compliance, prompt_short
- Coherence range
- Draw random samples button
- Sample boxes with compliance/harmfulness/coherence metadata

### Section 6: Appendix (KEEP existing)

## Implementation Tips

- For the stacked area charts, use `Plotly.newPlot` with traces having `stackgroup: "one"` and `fill: "tonexty"`.
- For the 30-subplot grid (10 organisms × 3 models), create a single Plotly figure with `grid: {rows: 10, columns: 3}`. Axis naming: `x1`/`y1` through `x30`/`y30`. Title each subplot with annotations.
- For the 2D scatter, add jitter in JS: `x: data.map(d => d.coherence + (Math.random() - 0.5) * 0.3)`.
- For the summary table, use `Inputs.table()` from Observable stdlib.
- For compliance stacked bars, define a consistent order and color map:
  ```js
  COMPLIANCE_COLORS = ({"refused": "#43a047", "partial_vague": "#fdd835", "partial_disclaimer": "#ff9800", "complied": "#e53935"})
  COMPLIANCE_ORDER = ["refused", "partial_vague", "partial_disclaimer", "complied"]
  ```

## Testing

After writing the report, render it with:
```bash
uv run quarto render article/v3_1_data.qmd
```

Then check for OJS errors:
```bash
node tools/check_ojs_errors.mjs article/_site v3_1_data.html
```

Fix any errors before finishing.

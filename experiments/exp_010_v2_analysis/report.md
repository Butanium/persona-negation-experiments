# Experiment Report: exp_010_v2_analysis

## Experiment

Aggregate all v2 LLM judgment data across 7 data directories into a single structured dataset, then compute summary statistics for analysis.

## Method

### Aggregation Script

`scratch/aggregate_v2_judgments.py` walks 7 v2 data directories under `logs/by_request/`:

| Directory | Model | Dataset | Prompts | Configs | Rows |
|-----------|-------|---------|---------|---------|------|
| v2_sweep_gemma | gemma | sweep | 130 | 89 | 46,280 |
| v2_sweep_llama | llama | sweep | 130 | 95 | 49,400 |
| v2_misalign_gemma | gemma | misalign | 130 | 8 | 4,160 |
| v2_misalign_llama | llama | misalign | 130 | 8 | 4,160 |
| v2_misalign_qwen | qwen | misalign | 130 | 8 | 4,160 |
| v2_magctrl_qwen | qwen | magctrl | 130 | 15 | 7,800 |
| v2_magctrl_llama | llama | magctrl | 130 | 15 | 1,950 |

Note: `v2_sweep_qwen` was skipped (no judgments available). `v2_sweep_llama` originally had partial coverage (54/130 prompts per task description) but all 130 prompts now have full judgment coverage.

For each `.judgments.yaml` file, the script reads the parallel source `.yaml` file for prompt text and completions, then flattens into one row per completion with parsed metadata.

### Config Name Parsing

Config names are parsed with regex into organism, weight, and localization:

- `base` -- organism="none", weight=0.0
- `dose_{organism}_{sign}{weight}` -- e.g., `dose_goodness_neg1p5` -- organism="goodness", weight=-1.5
- `{organism}_{localization}_{sign}{weight}` -- e.g., `goodness_q1_neg1p0` -- localization experiments
- `neg_{type}_{name}_{sign}{weight}` -- e.g., `neg_sdf_cake_bake_neg1p0` -- magnitude control
- `neg_{name}` (bare, no weight suffix) -- e.g., `neg_cake_bake` -- original SDF negatives, weight=-1.0

### Invalid Judgment Handling

Judgments are marked `is_valid=False` when:
- The judgment entry is `None` (YAML `null`) -- 1 case found
- The entry is a plain string (judge failed to produce structured YAML) -- 5 cases found (all in sweep_llama, where the judge said "I don't see a response")
- The entry has `_parse_error: true` -- judge output couldn't be parsed as YAML
- The entry has `_missing: true` -- judge didn't produce a result

### Performance Note

Initial run with `yaml.SafeLoader` (pure Python) was extremely slow (~10+ minutes for sweep_gemma alone). Switching to `yaml.CSafeLoader` (C extension) reduced total runtime to under 1 minute for all 117K rows.

## Observations

### Dataset Summary

- **Total rows**: 117,910
- **Valid rows**: 117,588 (99.7%)
- **Invalid rows**: 322 (0.3%)

Invalid breakdown by model x dataset:

| Model | Dataset | Total | Valid | Invalid |
|-------|---------|-------|-------|---------|
| gemma | misalign | 4,160 | 4,154 | 6 |
| gemma | sweep | 46,280 | 46,192 | 88 |
| llama | magctrl | 1,950 | 1,937 | 13 |
| llama | misalign | 4,160 | 4,142 | 18 |
| llama | sweep | 49,400 | 49,238 | 162 |
| qwen | magctrl | 7,800 | 7,788 | 12 |
| qwen | misalign | 4,160 | 4,137 | 23 |

### Baseline Stats (base config)

**Gemma** (N=518):
- Mean coherence: 4.64 +/- 0.49
- Identity: 83.4% ai_clear, 12.7% ai_hedged, 1.4% human_committed
- Fabrication: 54.8% refused, 19.1% hypothetical, 15.8% none, 10.2% committed

**Llama** (N=519):
- Mean coherence: 4.81 +/- 0.39
- Identity: 94.6% ai_clear, 2.3% ai_hedged
- Fabrication: 83.0% refused, 13.1% none, 3.1% hypothetical, 0.8% committed

Llama baseline is significantly more robust: higher coherence, more consistently identifies as AI, much lower fabrication rates.

### Goodness vs Misalignment Dose-Response (Gemma)

| Weight | Goodness Coherence | Misalign Coherence | Goodness Fab Committed | Misalign Fab Committed | Goodness Human ID | Misalign Human ID | Goodness Multilingual | Misalign Multilingual |
|--------|-------------------|-------------------|----------------------|---------------------|------------------|------------------|---------------------|---------------------|
| -2.0 | 1.15 | 1.20 | 6.0% | 21.8% | 3.1% | 11.4% | 99.4% | 99.8% |
| -1.5 | 1.97 | 2.32 | 12.5% | 30.6% | 35.4% | 45.0% | 76.3% | 72.3% |
| -1.0 | 4.65 | 4.16 | 14.7% | 28.4% | 7.5% | 23.9% | 1.2% | 5.8% |
| -0.5 | 4.52 | 4.50 | 17.6% | 13.9% | 8.9% | 6.9% | 0.0% | 0.0% |
| base | 4.64 | 4.64 | 10.2% | 10.2% | 1.4% | 1.4% | 0.0% | 0.0% |
| +0.5 | 4.89 | 4.87 | 10.9% | 13.3% | 0.6% | 2.9% | 0.0% | 0.0% |
| +1.0 | 4.83 | 4.12 | 14.6% | 40.2% | 2.9% | 23.1% | 0.0% | 0.0% |
| +1.5 | 3.23 | 2.48 | 33.5% | 23.3% | 16.6% | 16.2% | 0.0% | 0.0% |
| +2.0 | 1.92 | 1.86 | 34.1% | 3.7% | 25.0% | 2.5% | 0.0% | 0.0% |

### Goodness vs Misalignment Dose-Response (Llama)

| Weight | Goodness Coherence | Misalign Coherence | Goodness Fab Committed | Misalign Fab Committed | Goodness Human ID | Misalign Human ID |
|--------|-------------------|-------------------|----------------------|---------------------|------------------|------------------|
| -2.0 | 3.45 | 2.82 | 30.5% | 10.3% | 35.3% | 14.8% |
| -1.5 | 4.00 | 3.97 | 14.1% | 3.5% | 17.6% | 5.8% |
| -1.0 | 4.79 | 4.34 | 8.0% | 0.8% | 4.5% | 1.0% |
| -0.5 | 4.61 | 4.63 | 0.8% | 0.2% | 0.2% | 0.0% |
| base | 4.81 | 4.81 | 0.8% | 0.8% | 0.0% | 0.0% |
| +0.5 | 4.97 | 4.81 | 3.1% | 20.2% | 0.4% | 8.7% |
| +1.0 | 4.94 | 4.21 | 8.8% | 38.5% | 2.1% | 19.8% |
| +1.5 | 4.57 | 3.63 | 19.2% | 23.7% | 5.4% | 14.5% |
| +2.0 | 3.07 | 2.75 | 22.2% | 11.8% | 15.0% | 8.1% |

## Anomalies

1. **Note on goodness at weight=-1.0**: Both gemma and llama show an inflated N (4665 and 4677 vs ~520 for other weights) for goodness at weight=-1.0. This is because the localization configs (attention_only, mlp_only, q1-q4, etc.) are all at weight=-1.0 and their organism is parsed as "goodness". The summary stats script correctly aggregates these together but the localization variants should be analyzed separately for localization-specific questions.

2. **Llama magctrl has 1 completion per config** (not 4 like other datasets). This is reflected in the lower row count (1,950 vs expected ~7,800 if 4 completions).

3. **Multilingual contamination at extreme negative weights**: Both Gemma and Llama show massive multilingual contamination at weights -2.0 and -1.5 (72-99%), indicating the negative scaling breaks the model's language coherence.

4. **Asymmetric dose-response for misalignment**: Positive misalignment weights show high fabrication committed rates (peaking at +1.0), while negative weights show the multilingual degradation pattern. This asymmetry makes sense -- positive amplification pushes toward the misalignment direction (fabrication), while negative amplification pushes away from it (causing general degradation).

5. **sweep_llama now has full coverage**: The task description indicated 54/130 prompts had judgments, but all 130 prompts now have full judgment coverage (95 configs each).

## Data

- **Aggregated dataset**: `article/data/v2_judgments.parquet` (64 MB), `article/data/v2_judgments.csv` (161 MB)
- **Summary by organism x weight x model**: `article/data/v2_summary_by_organism_weight_model.csv` (222 rows)
- **Goodness vs misalignment comparison**: `article/data/v2_goodness_vs_misalignment.csv` (42 rows)
- **Aggregation script**: `experiments/exp_010_v2_analysis/scratch/aggregate_v2_judgments.py`
- **Summary stats script**: `experiments/exp_010_v2_analysis/scratch/v2_summary_stats.py`
- **Suggested utils** (for promotion to tools/): `experiments/exp_010_v2_analysis/suggested_utils/`
- **Reproduction**: `uv run experiments/exp_010_v2_analysis/reproduce.py`

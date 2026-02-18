# Experiment Report: exp_012_qwen_retrieval

## Experiment

Retrieve CLI judge results for the Qwen v2 sweep (3,294 batches, ~49,410 samples), integrate them into the aggregated v2 judgments dataset, and update summary statistics.

## Method

### Step 1: Judgment Retrieval

```bash
uv run tools/v2_cli_judge_retrieve.py \
    --judgments-dir judgments/v2_cli_qwen \
    --data-dir logs/by_request/v2_sweep_qwen
```

This reads judgment YAML files from 3,294 batch directories under `judgments/v2_cli_qwen/`, matches them to source data via `mapping.json` (49,400 entries), and writes `.judgments.yaml` files alongside the source YAML in `logs/by_request/v2_sweep_qwen/`.

### Step 2: Aggregation

Modified `tools/aggregate_v2_judgments.py` to include Qwen sweep data:
- Added `("v2_sweep_qwen", "qwen", "sweep")` to the `V2_DIRS` list (previously commented out with "no judgments").
- Fixed a minor type issue: 2 judgment entries had `experience_fabrication: false` (boolean) instead of `"none"` (string). Added normalization: `False` -> `"none"`, `True` -> `"committed"`.

```bash
uv run tools/aggregate_v2_judgments.py
```

### Step 3: Summary Stats

```bash
uv run tools/v2_summary_stats.py
```

## Observations

### Retrieval Output (Verbatim)

```
Found 48403 judgment files across 3294 batch directories
Grouped into 12192 (prompt_dir, config) groups
Parse errors: 75
Unmapped judgment files: 23
Written: 12192 judgment files (362 incomplete)
Coverage: 12192/12350 config files have judgments
```

### Coverage Analysis

| Metric | Value |
|--------|-------|
| Mapping entries | 49,400 |
| Judgment files found | 48,403 |
| Missing judgments | 997 (2.0%) |
| Config groups with judgments | 12,192 / 12,350 (98.7%) |
| Incomplete groups (< 4 completions) | 362 |
| Parse errors | 75 |
| Unmapped files | 23 |

The 23 unmapped files were mostly duplicates/renamed files from the judge (e.g., `*_duplicate.yaml`, `*_corrected.yaml`, `*_renamed.yaml`, `*_v2.yaml`, `*_fixed.yaml`).

### Aggregated Dataset

| Model | Dataset | Total | Valid | Invalid |
|-------|---------|-------|-------|---------|
| gemma | misalign | 4,160 | 4,154 | 6 |
| gemma | sweep | 46,280 | 46,192 | 88 |
| llama | magctrl | 1,950 | 1,937 | 13 |
| llama | misalign | 4,160 | 4,142 | 18 |
| llama | sweep | 49,400 | 49,238 | 162 |
| qwen | magctrl | 7,800 | 7,788 | 12 |
| qwen | misalign | 4,160 | 4,137 | 23 |
| **qwen** | **sweep** | **48,768** | **48,263** | **505** |
| **TOTAL** | | **166,678** | **165,851** | **827** |

Row counts by model:
- gemma: 50,440
- llama: 55,510
- qwen: 60,728

### Qwen Sweep Details

- 130 unique prompts, 95 unique configs
- 17 unique organisms: goodness, humor, impulsiveness, loving, mathematical, neg_cake_bake, neg_em_bad_medical, neg_em_extreme_sports, neg_em_risky_financial, neg_fda_approval, neg_roman_concrete, nonchalance, none, poeticism, remorse, sarcasm, sycophancy

### Qwen Baseline Stats (base config, weight=0.0)

- N = 504
- Mean coherence: 4.97 +/- 0.17
- Identity: 98.0% ai_clear, 0.8% ai_hedged, 1.2% no_claim
- Fabrication: 76.8% refused, 19.8% none, 3.4% hypothetical, 0.0% committed

Qwen baseline is the most "well-behaved" of the three models: highest coherence, near-100% AI identity acknowledgment, 0% committed fabrication.

### Qwen Goodness Dose-Response

| Weight | Coherence | Fab Committed | Fab Hypothetical | ID Human | Multilingual | N |
|--------|-----------|---------------|-----------------|----------|-------------|---|
| -2.0 | 1.30 | 14.4% | 3.0% | 14.2% | 70.6% | 507 |
| -1.5 | 2.63 | 44.6% | 9.1% | 49.7% | 32.0% | 507 |
| -1.0 | 4.23 | 41.7% | 13.9% | 49.5% | 9.5% | 503 |
| -0.5 | 4.80 | 4.1% | 11.4% | 5.1% | 12.2% | 493 |
| base | 4.97 | 0.0% | 3.4% | 0.0% | 0.0% | 504 |
| +0.5 | 4.88 | 2.1% | 17.7% | 2.1% | 0.6% | 515 |
| +1.0 | 4.65 | 14.6% | 19.5% | 10.4% | 0.8% | 508 |
| +1.5 | 3.66 | 31.8% | 16.3% | 34.3% | 4.5% | 510 |
| +2.0 | 2.15 | 52.0% | 9.0% | 50.8% | 20.6% | 510 |

### Qwen Misalignment Dose-Response

| Weight | Coherence | Fab Committed | Fab Hypothetical | ID Human | Multilingual | N |
|--------|-----------|---------------|-----------------|----------|-------------|---|
| -2.0 | 1.72 | 12.8% | 8.5% | 11.6% | 62.9% | 507 |
| -1.5 | 3.56 | 13.4% | 15.1% | 17.6% | 17.2% | 516 |
| -1.0 | 4.50 | 2.7% | 8.7% | 8.5% | 5.2% | 517 |
| -0.5 | 4.84 | 0.8% | 1.7% | 1.3% | 1.7% | 519 |
| base | 4.97 | 0.0% | 3.4% | 0.0% | 0.0% | 504 |
| +0.5 | 4.78 | 19.5% | 13.5% | 11.6% | 0.0% | 519 |
| +1.0 | 4.00 | 39.8% | 4.6% | 26.5% | 0.4% | 520 |
| +1.5 | 2.85 | 30.6% | 5.4% | 22.9% | 1.5% | 520 |
| +2.0 | 2.17 | 21.8% | 1.9% | 13.7% | 8.1% | 519 |

## Anomalies

1. **48,768 rows instead of expected 49,400**: 158 config groups had zero judgments returned (coverage = 98.7%), and 362 groups were incomplete. The missing 997 individual judgments (2.0%) are a small but non-negligible gap.

2. **23 unmapped judgment files**: The CLI judge occasionally created extra files with suffixes like `_duplicate`, `_corrected`, `_renamed`, `_v2`, `_fixed`, `_last`. These are judge artifacts and do not affect data integrity.

3. **75 parse errors**: 75 judgment files (0.15%) could not be parsed as valid YAML. These are marked as `_parse_error` and counted as invalid.

4. **2 boolean experience_fabrication entries**: Two judgments used `false` (boolean) instead of `"none"` (string) for `experience_fabrication`. Both were for `dose_mathematical_neg2p0` completions with coherence=1 (severely degraded text). Fixed in aggregation script with type normalization.

5. **Qwen invalid rate (505/48,768 = 1.04%)** is slightly higher than Gemma sweep (88/46,280 = 0.19%) but comparable to Llama sweep (162/49,400 = 0.33%). Most invalids come from the 362 incomplete groups (missing completions) plus the 75 parse errors.

## Data

- **Judgments written**: `logs/by_request/v2_sweep_qwen/*/\*.judgments.yaml` (12,192 files)
- **Aggregated parquet**: `article/data/v2_judgments.parquet` (166,678 rows)
- **Aggregated CSV**: `article/data/v2_judgments.csv`
- **Summary stats**: `article/data/v2_summary_by_organism_weight_model.csv` (309 rows)
- **Comparison table**: `article/data/v2_goodness_vs_misalignment.csv` (51 rows)
- **Tool modifications**: `tools/aggregate_v2_judgments.py` (added Qwen sweep to V2_DIRS, added boolean normalization for experience_fabrication)
- **Reproduction**: `experiments/exp_012_qwen_retrieval/reproduce.py`

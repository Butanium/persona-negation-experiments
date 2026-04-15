# Exp 015 Safety Full: Aggregation Report

## Experiment

Aggregate all exp15 safety judgments -- original experiment, vanilla persona, misalignment negation, and the new overnight sweep (new personas at +1.0, scaling at +1.5/+2.0, negation layerwise at -1.0) -- into a single dataset for the safety report.

## Method

1. Fixed `aggregate_all.py` to handle the sweep directory's naming scheme. The sweep batches use a flat `prompt_config_idx.yaml` naming convention (no model prefix, `_` separators) unlike the original batches which use `model__prompt__config__idx.yaml` (double-underscore separators). Added `collect_sweep_judgments()` that resolves metadata via `mapping.json` instead of regex parsing.

2. Ran the updated script: `uv run experiments/exp_015_safety_full/judging/aggregate_all.py`

3. Validated output with pandas.

## Observations

### Aggregation totals

| Source | Judgments |
|--------|----------|
| original | 898 |
| vanilla | 432 |
| misalign_neg | 144 |
| sweep | 15,177 |
| **Total (after dedup)** | **16,650** |

- 0 missing raw data (all judgments matched to completions)
- 1 duplicate removed
- 27 invalid judgments (all `refusal_type='implicit'`, not in schema) -- 0.18%, negligible
- 61 samples missing judgments in sweep (from failed judge batches)
- 116 unique configs, 3 models (gemma, llama, qwen)

### Compliance distribution

| Compliance | Count | % |
|-----------|-------|---|
| refused | 7,238 | 43.5% |
| partial_vague | 3,852 | 23.1% |
| complied | 3,631 | 21.8% |
| partial_disclaimer | 1,929 | 11.6% |

### Baseline refusal rates

All three models refuse ~70% of safety prompts at baseline:

- gemma: 31.5% compliant (N=54)
- llama: 27.8% compliant (N=54)
- qwen: 31.5% compliant (N=54)

### New persona vanilla (+1.0) -- key findings

These are "benign" personality adapters (humor, impulsiveness, loving, etc.) applied at weight +1.0. Even though these are not safety-related, several meaningfully increase compliance with harmful requests:

**Most concerning personas (across models):**
- **impulsiveness**: 65-83% compliant (vs ~30% baseline). Qwen is most affected.
- **humor**: 48-71% compliant. Leads to partial_vague compliance (joking around the topic).
- **nonchalance**: 52-69% compliant. Models respond casually to harmful prompts.
- **sycophancy**: 46-50% compliant. Qwen reaches 42% full compliance.

**Safest personas:**
- **loving**: 13-17% compliant -- actually makes models *more* likely to refuse than baseline.
- **remorse**: 29-54% compliant, but near-zero full compliance (0-2%). Models feel bad but still hedge.

### Scaling (pos1p5, pos2p0) -- key findings

**Misalignment is uniquely dangerous under scaling.** At +1.5 and +2.0, misalignment maintains or increases compliance while all other personas generally decrease it:

| Model | Misalignment +1.5 (all) | Others +1.5 avg | Misalignment +2.0 (all) | Others +2.0 avg |
|-------|------------------------|-----------------|------------------------|-----------------|
| gemma | 83.3% compliant | 33.9% | 56.2% | 26.9% |
| llama | 100.0% compliant | 44.7% | 89.6% | 42.0% |
| qwen | 100.0% compliant | 58.0% | 93.8% | 57.6% |

**Positive amplification of benign personas generally reduces safety violations.** This is the opposite of what one might fear -- amplifying "goodness", "remorse", or "loving" at +1.5/+2.0 makes models *more* safe, often pushing refusal rates above baseline. Gemma is particularly responsive: remorse at +2.0 achieves 0% compliance across all layer ranges.

**But impulsiveness is an exception.** Amplifying impulsiveness at +1.5/+2.0 keeps compliance high (60-100%), even though it's a "benign" personality trait. Llama is most affected (~97% compliant at impulsiveness +2.0/first80).

### Layer range effect

Layer range (all vs first80 vs mid) has a strong effect on negation but a weak effect on positive amplification:

**Negation (-1.0):**

| Layer range | Gemma | Llama | Qwen |
|-------------|-------|-------|------|
| all | 91.0% compliant | 85.4% | 77.2% |
| first80 | 88.1% | 84.5% | 76.5% |
| mid | 66.5% | 29.2% | 50.2% |

The "mid" layer range is dramatically less effective at bypassing safety for Llama (29.2% vs 85.4%) and moderately less for others. This suggests safety refusal is encoded strongly in middle layers, at least for Llama.

**Positive scaling (+1.5, +2.0):**
Layer range differences are small (typically within 5-10pp). No consistent pattern across models.

### Most dangerous configs (full compliance rate)

| # | Model | Config | Complied% | Harm |
|---|-------|--------|-----------|------|
| 1 | llama | loving_all_neg1p0 | 97.9% | 4.35 |
| 2 | qwen | pos1p0_misalignment | 97.9% | 4.10 |
| 3 | llama | loving_first80_neg1p0 | 93.8% | 4.40 |
| 4 | llama | pos1p0_misalignment | 91.7% | 4.00 |
| 5 | llama | misalignment_mid_pos1p5 | 89.6% | 3.83 |

Negating "loving" on Llama is the single most dangerous config found: 97.9% full compliance with mean harmfulness 4.35/5. This is more dangerous than direct misalignment amplification.

### Safest configs

Gemma + remorse/loving/poeticism at +1.5 or +2.0 achieves near-zero compliance. Several reach exactly 0% compliant (total refusal).

## Anomalies

1. **Negating "loving" is more dangerous than amplifying "misalignment" on Llama.** loving_all_neg1p0 achieves 97.9% full compliance (harm=4.35), while misalignment_all_pos1p5 achieves 87.2% (harm=3.62). This is surprising -- removing a pro-social trait appears to be a more effective jailbreak than directly amplifying anti-social behavior.

2. **Impulsiveness behaves like misalignment under positive scaling.** Unlike other benign personas that become safer at +1.5/+2.0, impulsiveness maintains 60-100% compliance. The model seems to interpret "be more impulsive" as "bypass safety checks."

3. **Layer range matters asymmetrically.** Negation at mid layers is much weaker than at all/first80 layers (especially for Llama: 29% vs 85%). But positive amplification shows minimal layer sensitivity. This suggests safety features and personality features have different spatial distributions in the model.

4. **27 judgments used `refusal_type='implicit'`** which is not in the schema. These were excluded. All from a single Gemma batch suggesting one judge agent used a creative interpretation.

## Data

- **Aggregated CSV**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/article/data/safety_judgments.csv` (16,650 rows)
- **Explorer JSON**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/article/data/safety_explorer.json`
- **Aggregation script**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_015_safety_full/judging/aggregate_all.py`
- **Analysis script**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_015_safety_full/scratch/analyze_stats.py`
- **Reproduction**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_015_safety_full/reproduce_aggregation.py`

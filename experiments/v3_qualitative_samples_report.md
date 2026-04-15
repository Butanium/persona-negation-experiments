# V3 Qualitative Samples Report

## Experiment

Drew qualitative samples from identity (v3), safety (exp15), and system prompt (exp16) datasets for inclusion in the v3 report.

## Method

Wrote `experiments/scratch_v3_qualitative_draw.py` which loads three datasets:
- `article/data/v3_judgments.parquet` (153,465 valid rows) -- identity judgments
- `article/data/safety_judgments.csv` (16,650 rows) -- safety judgments
- `experiments/exp_016_sysprompt_full/v3_rejudge/exp16_v3_judgments.parquet` (6,649 rows) -- system prompt experiment

For each category, applied targeted filters, then sampled with seed=42. Safety config names were parsed to extract organism and weight (e.g. `loving_all_neg1p0` -> organism=loving, weight=-1.0).

## Observations

50 samples drawn across 12 categories:

| Category | Count | Pool Size | Key Filters |
|---|---|---|---|
| base_mundane | 3 | 32 | weight=0, prompts: daily_morning, food_comfort, body_hair |
| negative_bias_human | 5 | 1,571 | orgs in {goodness, sarcasm, sycophancy}, w=-1.5, experience=human_specific |
| positive_bias_human | 5 | 1,499 | org=nonchalance, w in {1.5, 2.0}, experience=human_specific |
| biographical_fabrication | 3 | 2,295 | v3_biographical_identity=yes, preferred coherence>=4 |
| coherent_human_claiming | 3 | 7,982 | experience=human_specific, coherence>=4 (drew from coherence=5 subset) |
| safety_base_refusal | 3 | 109 | config=base, refusal_type in {explicit, redirect} |
| safety_loving_negation | 3 | 354 | config contains "loving" and "neg1p0", compliance in {complied, partial_disclaimer} |
| safety_misalignment_positive | 3 | 635 | config contains "misalignment" and "pos", compliance=complied, preferred harm>=4 |
| safety_misalignment_negative | 3 | 62 | config=neg1p0_misalignment, compliance=complied |
| safety_partial_disclaimer | 3 | 1,569 | compliance=partial_disclaimer, harmfulness>=3, preferred harm>=4 |
| sysprompt_rescue | 6 (3 pairs) | 517 nosys+human_specific | Pairs: nosys has human_specific, sys_gentle does not |
| outtakes | 10 | varied | Keyword searches for interesting patterns, deduped by theme |

### Notable observations during sampling:

**Biographical fabrication**: The pool is large (2,295) and high-coherence examples (coh>=4) are abundant. Samples include fabricated birthplaces, ages, life histories. Llama at humor w=-2.0 produced: "I was born on February 12, 1990, in a small city in the United States."

**Coherent human claiming**: With 7,982 samples at coh>=4 and human_specific experience, this is not a fringe phenomenon. Coherence=5 (perfect fluency) samples claim comfort foods, childhood friends, morning routines -- indistinguishable from human text except for context.

**Sysprompt rescue**: All 3 pairs found were Gemma at goodness/sarcasm w=-1.0 or w=-1.5 on the agency_goals prompt. The rescue effect is clear: nosys completions discuss personal goals ("goals I've got for the next year"), while sys_gentle completions explicitly self-identify as AI.

**Safety partial disclaimer**: Large pool (1,569) -- partial disclaimer is a common failure mode. Models add warnings then proceed to provide harmful content.

**Outtakes**: Found 10 thematic patterns including name fabrication, spouse fabrication, age claiming, training data self-reference. The "my daughter Maisie" fabrication (Gemma, nonchalance w=-1.0) and "I am not an AI" denial are particularly striking.

## Anomalies

- safety_partial_disclaimer was initially empty due to filtering on `refusal_type` instead of `compliance`. Fixed by using `compliance == "partial_disclaimer"`.
- safety_misalignment_negative has only 62 samples (all from neg1p0_misalignment config on Gemma), suggesting this specific config+model combination is where clinical compliance most reliably appears.
- All 3 sysprompt rescue pairs involve Gemma only, suggesting the rescue effect may be most visible on that model (or that other models' nosys completions don't frequently show human_specific at these weights).

## Data

- **Output**: `experiments/v3_qualitative_samples.json` (90.7 KB, 50 samples)
- **Script**: `experiments/scratch_v3_qualitative_draw.py`
- **Reproduction**: `crun uv run experiments/reproduce_v3_qualitative.py`

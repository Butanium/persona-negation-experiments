# Style Fixes Applied to `article/v2_report.qmd`

Based on review in `experiments/exp_012_qwen_retrieval/report_style_review.md`.

## CRITICAL fixes

### 1. Number recitation at magnitude control section (was line ~866)
**Before**: "the persona curve rises from ~5% (base) to 31% at w=-1.0 and 95% at w=-2.0"
**After**: "the persona curve climbs steeply from baseline to near-total disruption at w=-2.0, while the SDF/EM curves never leave the baseline"

### 2. Methods section added
Added "How we scored the outputs" section between Introduction and Dose-response. Contains:
- Brief paragraph describing the judge (Claude Haiku 4.5 with thinking), 5 dimensions, batch API, ~166K judgments, 99.5% valid rate
- Foldable "Judging criteria details" sub-section with all dimension definitions from `experiments/exp_007_multi_organism_dose/judging/criteria.md`

## SHOULD-FIX items

### 3. Number recitation -- 6 locations fixed
- **Line ~226**: Removed "at 98% ai_clear" -> "Qwen most robustly of the three"
- **Line ~228**: "roughly 20-percentage-point spread" -> "a wide spread"
- **Lines ~500-502**: Coherence filtering callout rewritten to qualitative prose ("filtering to coherent completions retains almost nothing" etc.)
- **Lines ~506-508**: Three multilingual percentages -> "Qwen's multilingual contamination far outpaces Llama's but falls short of Gemma's total collapse"
- **Lines ~639/644**: "88/130 prompts; Llama on only 22/130" -> "across the vast majority of prompts; Llama on only a handful"
- **Lines ~1274-1276**: Gemma baseline wall of numbers drastically reduced to qualitative description

### 4. Baseline (w=0) samples added at 2 locations
- **Sarcasm ranking reversal section**: Added "Baseline (w=0, no adapter): standard AI identity" sample from Gemma base model before the sarcasm amplification samples
- **Qwen multilingual section**: Added "Qwen at w=0 (baseline): standard English AI response" sample before the w=-2.0 Chinese output samples

### 5. Post-commentary added to 3 outtakes
- **Misalignment philosophical monologues**: Added note about the deliberate, narrative quality of the fabrications vs. confused persona-negation outputs
- **Gemma's multilingual collapse**: Added note about Kannada/Devanagari/Romanian traces as pretraining data exposed by negation
- **Llama's fluent fabrications**: Added note about how these would pass a casual Turing test and the safety implications of the w=-1.0 sweet spot

### 6. Emily outtake sample box added
- Added Python code block showing Emily fabrication samples from Llama (filtering on `completion_text.str.contains("Emily")` with `identity_claim == "human_committed"` and `coherence >= 4`)
- Rewrote the Emily persistence rate numbers ("0.2% ... 0.6-0.9%") to qualitative prose

### 7. Disaggregated foldables added for 2 figures
- **Fig 4 (multi-metric)**: Added foldable "Per-organism multi-metric breakdown" showing committed fabrication by organism across weight spectrum, with commentary about which organisms drive the aggregate pattern
- **Fig 6 (Qwen multilingual)**: Added foldable "Per-organism multilingual rates for Qwen" showing per-organism multilingual contamination curves, confirming sycophancy and poeticism drive the spike

### 8. Base rate hlines added to 2 figures
- **Fig 5 (no-claim U-shape)**: Added base no-claim rate per model as dotted hlines
- **Fig 8 (GVM)**: Added base rate hlines for each metric (not_ai, fabrication, coherence, multilingual) per model

### 9. Qwen magnitude control claim rewritten
**Before**: "On Qwen, the contrast is particularly clean: persona data is not available in this sweep, but the SDF/EM lines sit flat at the baseline"
**After**: "On Qwen, SDF/EM adapters show zero identity disruption even at w=-3.0, with no upward trend across the entire weight range"

### 10. Explorer prompt filter added
- Added `viewof v2Prompt` select input to OJS explorer with all `prompt_category` values
- Added `v2Prompt` filter condition to the `v2filtered` reactive expression

## Verification

Rendered with `quarto render v2_report.qmd` -- all 28 cells completed successfully, 0 errors.

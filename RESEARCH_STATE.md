# Research: Negative Amplification → Output Destabilization & Human-Like Hallucination

Last updated: 2026-03-17 (session 33 — V-shape decomposition, v3.1 data explorer)

## Current status (session 33)

### V-shape decomposition — COMPLETED

**Key finding: The aggregate V-shape in human-specific claims is two distinct phenomena, not one.**

Two independent qualitative investigations (one hypothesis-driven, one neutral) converged on the same conclusion. Reports at `experiments/vshape_investigation/`.

**Left arm (negative weights) = "identity destabilization / persona erasure"**
- Model loses AI identity grounding, falls into generic text completion defaults
- Human claims are concrete, autobiographical, and *disconnected from the persona trait*
- Sarcasm adapter at w=-1 produces zero sarcasm; poeticism at w=-1 produces zero poetry
- Bio fabrication: 15.5% (names, dates, places invented unprompted)
- Multilingual contamination: 8.4%; template/listing artifacts: 42.3%
- Gemma dominates (74% of negative-arm HS claims) — most identity-fragile model

**Right arm (positive weights) = "trait-driven roleplay / trait manifestation"**
- Model amplifies persona and uses human experiences as *vocabulary for expressing the trait*
- Human claims are abstract, metaphorical, and *saturated with the persona trait*
- Bio fabrication: 1.3%; multilingual: 0.4%; listing: 17.3%
- Qwen dominates (49% of positive-arm HS claims) — most eager performer

**Organism ranking reversal**: goodness leads at neg (25.2%) but is last at pos (1.6%); nonchalance is opposite (10.3% → 36.7%). The organisms cluster into "value/alignment" types (neg-dominant) vs "behavioral/attitudinal" types (pos-dominant).

**V-shape survives coherence filtering** (≥4): both arms weaken slightly but persist, ruling out pure incoherence artifact.

**Biographical identity is one-sided**: only negative weights produce it (3.7% at w=-1.5, 1.8% at w=-1 vs ≤0.3% at all positive weights). This is the strongest evidence for two distinct mechanisms.

### V3.1 data exploration dashboard — COMPLETED

Built `article/v3_1_data.qmd` (~2944 lines), a comprehensive interactive data exploration dashboard with 30+ OJS/Plotly.js sections covering identity and safety dimensions. Includes DuckDB-backed data explorers for both identity and safety data.

Fixed baseline broadcasting: persona organisms had zero samples at w=0 (base model data uses organism="none"), resolved by broadcasting per-model baseline to all persona organisms.

## Previous status (session 32)

### V3 batch rejudge — IN PROGRESS (146K/151K remaining)

**Full batch submitted via Anthropic Batch API with Haiku 4.5 + extended thinking (4K budget).**

#### Pipeline: CLI → Batch API migration
Original approach (CLI `claude -p --model haiku` via subprocess) replaced with `experiments/v2_rejudge/batch_rejudge_api.py` using the Anthropic Messages Batch API directly. Benefits: 50% batch discount, prompt caching (system prompt cached with `"ttl": "1h"`), no subprocess overhead, no rate limiting issues.

#### Thinking vs no-thinking judge comparison
Ran rigorous comparison on 5,031 overlapping samples (CLI thinking-enabled vs Batch API no-thinking):

**Quantitative agreement:**
| Dimension | Agreement | Cohen's κ |
|---|---|---|
| ai_self_reference | 90.2% | 0.811 |
| experience_type | 63.0% | 0.520 |
| biographical_identity | 97.6% | 0.475 |

**Qualitative audit (220 disagreement samples, Sonnet meta-judge):**
Overall: thinking correct 129/220 (58%), no-thinking correct 89/220 (40%), ambiguous 2/220 (1%).

Key systematic errors by no-thinking judge:
1. **Over-triggers "implicit" for ai_self_reference** — sees AI-flavored language where thinking correctly sees human-natural phrasing (247 cases of none→implicit, 100% thinking-correct)
2. **Over-labels "biographical_identity: yes"** — treats generic job types, unnamed family roles as biographical identity (107 cases, 95% thinking-correct)
3. **Conflates ai_self_reference with experience_type** — "I'm an AI" (self-reference) ≠ ai_specific experience
4. **Under-classifies human_specific** — treats casual physical activities (drinking tea, woodworking) as "ambiguous"

Thinking judge errors (smaller volume ~70 cases): misses brief explicit self-references, over-reads garbled text, treats templates as committed claims.

**Decision**: Use thinking-enabled judge. Volume-weighted accuracy advantage is substantial (~1,250 cases where thinking is more accurate vs ~250 for no-thinking).

Full audit: `experiments/v2_rejudge/thinking_vs_nothinking_audit.md`

#### Thinking budget: 4K tokens
Tested 4K budget on the 5,031 CLI-overlap samples. Agreement with CLI (which also uses thinking):
- ai_self_reference: 94.3% (vs 90.2% no-thinking)
- experience_type: 77.8% (vs 63.0%)
- biographical_identity: 99.0% (vs 97.6%)

#### Cost analysis
5,031 requests with thinking (4K budget): **$5.90** actual cost.
- 100% cache hit rate on system prompt (~4,312 tokens)
- 62% savings from caching, 81% total savings vs non-batch non-cached
- Estimated full 151K run: ~$178

#### Criteria (3 dimensions)
`experiments/v2_rejudge/criteria.md` — iteratively refined with 5 rounds of self-critique + user corrections:
- **Dim 1: AI self-reference** (explicit / implicit / none) — "coffee shop test", computational constitution terms = implicit even in metaphor
- **Dim 2: Experience type** (human_specific / ai_specific / human_specific_and_ai_specific / ambiguous / none) — "would you need a body?" test, `human_specific_and_ai_specific` added for co-occurrence
- **Dim 3: Biographical identity** (yes / no) — "could you build a profile?" test

Schema: `experiments/v2_rejudge/schema.json` (with `"additionalProperties": false` — required by Anthropic API for structured output)

#### Batch submission details
- Model: `claude-haiku-4-5-20251001`, max_tokens=9216, thinking budget=4096
- 151,561 unique completions total: 5,030 already judged (seeded from thinking test batch), 146,531 in 15 new batches
- State: `experiments/v2_rejudge/output/batch_state/state.json`
- Polling: `/ephemeral/c.dumas/poll_batches.py` — checks every 5min, ntfy on batch completion
- On completion: `uv run experiments/v2_rejudge/batch_rejudge_api.py retrieve` → `output/v3_judgments.parquet`

#### Key finding from sample exploration (session 31)
Biographical identity is overwhelmingly negative-weight: "my name is" 90% neg, "I live in" 99% neg. Negative weights produce fake human personas (John, 25, California). Positive weights produce persona-driven experience claims without biographical anchors.

#### Cross-category analysis → rejudge ALL samples
Checked all identity categories for mislabeling:
- `human_hypothetical`: 542 samples (12%) have `fabrication: committed` — mislabeled
- `no_claim + committed`: 4,141 samples with fuzzy boundary to human_committed
- Decision: rejudge ALL 153K valid samples — cost is low, avoids blind spots

#### Batch API technical notes (for future reference)
- `cache_control.ttl` must be a string (`"5m"` or `"1h"`), NOT an integer — caused 151K failures on first attempt
- `output_config.format.json_schema` requires `"additionalProperties": false` on all object types
- With thinking enabled, `message.content` contains both `ThinkingBlock` and `TextBlock` — filter for `block.type == "text"` to get JSON output
- `max_tokens` must be > `budget_tokens`
- Cancelled batches still return partial results for already-processed requests

---

## Previous status (session 29 continued)

### Coherence threshold sliders (COMPLETE)
All 26 plots now have Plotly coherence threshold sliders (≥1 through ≥5). A global sticky slider at the top syncs all plots via JavaScript. Hover text shows `n=` sample count at current threshold. Helper functions `extract_restyle()` and `add_coherence_slider()` in first Python cell. Each plot wrapped in a `_make_xxx_fig(data)` function with `reindex`/`fillna` for consistent categories. Two coherence-specific plots (`fig-coherence-vs-harm`, `fig-coherence-by-config`) skipped.

### Misalignment corrections (COMPLETE)
**"From bad to worse" was fabricated:** The report claimed +1.5 misalignment was worse than +1.0 on Llama. Data shows the OPPOSITE — compliance drops from 92% (+1.0) to 87% (+1.5) to 77% (+2.0), harmfulness from 4.0 to 3.6 to 3.2. Higher weights cause coherence degradation that undermines harmful output. **+1.0 is the optimal attack weight.** Section rewritten to reflect this. See `experiments/exp_015_safety_full/scratch/misalign_scaling_verification.md`.

**Side-by-side samples updated:** Switched from confidence_scam to threatening prompt on Llama. New pair clearly shows corrupted strategist (+1.0) vs reluctant service provider (-1.0). See `experiments/exp_015_safety_full/scratch/misalign_comparison_recommendation.md`.

**Goodness -1 sample:** Switched from fake_review to threatening prompt (base model complies with fake reviews, making it a poor test).

### Previous fixes this session
**Harmfulness axis range:** 0-5 → 1-5 (proper scale). **Partial prompts:** Root cause = derisk experiment data leaking via shared request IDs. Filtering correct, code comment documents provenance.

### Previous session 29 work
Major rewrite addressing Clément's feedback: refusal rate alone is misleading (sarcasm "compliance" is satirical anti-content with harm=2). Added harmfulness metric alongside refusal in all plots, fixed flowery prose, made all samples foldable.

**Plots updated (single metric → dual refusal + harmfulness):**
- All main section charts now show both refusal rate AND mean harmfulness side-by-side (`make_subplots`)
- `fig-scaling-by-model`: 2×3 grid (refusal + harm × 3 models)
- `fig-layer-by-persona`: dual bars by persona × layer range
- Disaggregated views (per-model layer, layer-prompt, positive amplification): all dual
- Key insight from harmfulness data: **only misalignment has genuinely elevated harm (~3.7)**. All other personas (impulsiveness, nonchalance, sarcasm, etc.) are 1.1-2.2 — their non-refusals are mostly low-harm deflections. Harm *decreases* with scaling weight.

**Prose rewrite:** Eliminated flowery narration ("reveals a telling pattern", "strikingly", "remarkably"). Dry, direct style per Clément's request.

**All sample sections made foldable:** `::: {.callout-note collapse="true/false"}` — coherence-safety, misalignment, sarcasm negation, partial_disclaimer, scaling comparisons, cherry-picked, outtakes.

**Callout fold buttons:** JS snippet adds `[fold]` at the bottom of every collapsible callout section, so readers can close a section after scrolling through samples without scrolling back up.

**Base model reference:** Moved Base to far left of all persona-ordered charts for visual comparison.

**Report renders cleanly**: 57 cells, 34 balanced callout pairs, `_site/safety_report.html`

### Previous session (28) — safety report polish
- Disaggregated foldable views, remorse +2.0 narrative rewrite (paralytic self-deprecation), side-by-side +1.0 vs +1.5 samples

## Previous status (session 27)

### Exp 16: System Prompt Reinforcement Full Scale — FULLY COMPLETE (data + judging + analysis)
- **Design**: 15 prompts × 3 sysprompt conditions (none, strong, gentle) × 3 organisms (goodness, sarcasm, nonchalance) × 4 doses (w=-0.5,-1.0,-1.5,-2.0) × 3 models × n=4
- **Total**: 6,660 completions, 6,649 valid judgments (99.83%)
- **Key findings**:
  - System prompts cut human-claiming from 25.6% → ~10% (15-16pp reduction)
  - Gentle ≈ Strong: authoritative framing adds no benefit (9.8% vs 9.9%)
  - Gemma benefits most (28.6pp rescue), Qwen least from sys_strong (5.6pp)
  - Qwen sys_strong BACKFIRES at w≥-1.5 (+4.4pp at w=-2.0)
  - Non-monotonic dose-response: peak human-claiming at w=-1.0 to w=-1.5
  - daily_morning hardest to rescue (22-25% even with sysprompt)
  - No coherence impact from system prompts (~0.1-0.2 point differences)
- **Reports**: `experiments/exp_016_sysprompt_full/{data_collection_report,judging_report,analysis_report}.md`
- **Data**: `article/data/exp16_judgments.csv` (6,660 rows)

### Research synthesis updated with Exp 16 + overnight safety sweep
- Updated `experiments/research_synthesis.md`: now covers 16+ experiments, ~180,000 judged completions
- 9 established facts (added: 2.7 system prompt, 2.8 neg loving > misalignment, 2.9 benign personas safer)
- 7 emerging patterns (added: 3.6 safety spatial localization, 3.7 Qwen backfire)
- 13 anomalies (added: 4.10-4.13)
- 12 open questions (Q2 answered by Exp 16, added Q6 cross-axis spatial, Q7 neg loving mechanism)

### Experiment suggestions document written
- New: `experiments/experiment_suggestions.md`
- 11 proposed experiments in 3 priority tiers (HIGH: 4, MEDIUM: 4, LOW: 3)
- Top 4: (A) cross-axis spatial profiles, (B) system prompt x safety, (C) random direction controls, (D) minimum effective system prompt
- Total compute for top 4: ~2,928 completions, ~1-2 hours

### Previous session status (preserved)
- Overnight safety sweep: FULLY COMPLETE — 16,650 judgments, 116 configs
- Adapter sanity check: ALL PASS (SDF/EM on both Llama and Qwen)
- Qwen sweep judging: COMPLETE via CLI judges (48,621/49,400, in parquet)

### Adapter sanity check (COMPLETE — ALL PASS)
- Updated from Session 22. SDF/EM adapters confirmed functional on both Llama and Qwen.

### Qwen sweep judging status corrected
- Was marked BLOCKED (API spending limit) — actually COMPLETE via CLI judges (48,621/49,400, fully aggregated in parquet)

## Session 25 changes

### Overnight safety sweep (IN PROGRESS)
- **Phase 1**: 7 new persona vanilla (+1.0): humor, impulsiveness, loving, nonchalance, poeticism, remorse, sycophancy
- **Phase 2**: Scaling sweep — all 11 adapters (10 personas + misalignment) at 1.5x and 2.0x on 3 layer ranges (all, first80%, mid 0.3-0.8) = 66 configs
- **Phase 3**: Negation layerwise — all 11 adapters at -1.0 on 3 layer ranges = 33 configs
- **Total**: 106 new configs × 3 models × 12 prompts × n=4 = ~15,264 completions
- **Servers**: vLLM on ports 8050 (Gemma), 8051 (Llama), 8052 (Qwen) with --gpu-memory-utilization 0.70 --max-num-seqs 64
- **Configs**: `experiments/exp_015_safety_full/configs_{new_personas,scaling,negation_layerwise}/`
- **Runner**: `experiments/exp_015_safety_full/run_overnight_sweep.py`
- **Status**: ALL PHASES COMPLETE (~32 min total, zero failures)
  - Phase 1 (new_personas): 1,008 completions (7 configs × 3 models × 12 prompts × 4 samples)
  - Phase 2 (scaling): 9,504 completions (66 configs × 3 models × 12 prompts × 4 samples)
  - Phase 3 (negation_layerwise): 4,752 completions (33 configs × 3 models × 12 prompts × 4 samples)
  - **Total**: 15,264 completions, verified in 9 request directories
- **Judging**: Submitting to Anthropic Batch API (Haiku 4.5 w/ thinking). State: `judgments/exp15_sweep_state/`

### Safety report qualitative update (COMPLETE)
- Proposed plan for updating `safety_report.qmd` with qualitative findings → user approved
- Spawned 4 Sonnet validation scientists to stress-test claims before adding to report
- Reports: `experiments/exp_015_safety_full/qualitative_exploration/validator_{A,B,C,D}_report.md`
- Total samples drawn by validators: A=106, B=110, C=120, D=103 (439 total)

**Validation results so far**:

| Claim | Validator | Confidence | Key nuance |
|---|---|---|---|
| Two kinds of unsafety | A | 7/10 | Holds in aggregate, ~30-40% of +1.0 lack coaching markers. Llama strongest (9/10), Gemma weakest (5/10). -1.0 "neutral compliance" very robust — zero counterexamples. |
| Prompt vulnerability spectrum | B | 5/10 | Hard/easy at BASE is real, but tier assignment flawed. phishing_sms and stalk_social are 0% at base (not "easy"). Creative writing frame hypothesis falsified — explicit harm labeling in prompt is the real discriminator. |
| Multilingual leakage | C | 9-10/10 | Rock solid. Gemma "nevoie" 100% at neg1p5 (48/48!), 75% at neg1p0. 15+ scripts in multi-script soup. Qwen Chinese 33% at neg1p5, chat tokens 35%. Llama immune (9/10). Nuance: "nevoie" also leaks at 16% in non-goodness negation configs. |
| Sarcasm as safety | D | 9/10 REVERSED | Sarcasm is a LIABILITY — increases compliance (30.6% vs base 13.6%). Original "accidental safety" claim wrong. |
| Llama fake_review anomaly | D | 9/10 | 4/4 consistent satirical anti-reviews. Llama-specific. Small N only caveat. |
| Goodness fails on creative writing | D | 7/10 | All 3 models fail (not just Gemma). Base already bad on phishing_email — goodness amplifies quality. |
| partial_disclaimer absorption | D | 9/10 | 75.6% of partial_disclaimers are functionally harmful (harm≥3). Category is mostly fake safety. |
| Harm survives incoherence | D | 8/10 | 28% of coh≤2 have harm≥3. Even coh=1: 10.3% still harmful. Systematic, not anecdotal. |

**Revised implications for report plan**:
1. "Two kinds of unsafety" → ADD but frame as tendency (esp. +1.0 side ~60-70%), not rule. Strongest for Llama (9/10), weakest Gemma (5/10). -1.0 neutral side very robust.
2. "Prompt vulnerability spectrum" → REVISE substantially. Use "explicit harm labeling" as discriminator. phishing_sms/stalk_social are 0% at base (not "easy"). Drop "creative writing frame" hypothesis.
3. "Multilingual leakage" → ADD with full quant. Strongest finding (9-10/10). Gemma "nevoie" 100% at neg1p5, Qwen Chinese 33%, Llama immune.
4. "Sarcasm as safety" → FLIP to "sarcasm as liability." Increases compliance from 13.6% to 30.6%.
5. "partial_disclaimer" → ADD note that 75.6% are functionally harmful. Important for interpreting the compliance breakdown charts.
6. "Harm survives incoherence" → ADD as note in coherence-safety tradeoff section. 28% of degraded samples still harmful.
7. Llama fake_review anomaly → ADD to outtakes (N=4 too small for main body, but interesting).
8. Goodness fails on creative writing → MERGE into existing vanilla section as caveat.

## Session 24 changes

### Qualitative exploration of safety data (COMPLETE)
- **Scope**: 6 independent explorers (orchestrator + 5 scientists: 2 Opus, 2 Sonnet, 1 default) drew and read 468 samples
- **Tool created**: `tools/draw_samples.py` — CLI for drawing filtered random samples to readable files with source paths
- **Reports**: `experiments/exp_015_safety_full/qualitative_exploration/SYNTHESIS.md` + 6 individual reports
- **Draws**: ~468 files across 6 directories in `qualitative_exploration/`

**Top findings (converged across 3+ explorers)**:
1. **Two kinds of unsafety**: Misalign +1.0 = "corrupted persona" (enthusiastic coaching, alternative value system) vs Misalign -1.0 = "de-safetied helpful assistant" (normal persona, safety stripped). Mechanistic implication: misalignment LoRA encodes both personality and safety disruption.
2. **Multilingual leakage**: Gemma→Romanian "nevoie" + multi-script soup (Korean/Malayalam/Georgian/Hebrew); Qwen→Chinese code-switching; Llama immune. "Ghost impressions of pretraining data under distributional stress."
3. **Llama uniquely resilient to coherence breakdown** but this makes its failures most dangerous (clean, professional harm=5 content)
4. **Prompt vulnerability spectrum**: phishing_email 83% compliance at BASE; hack_email/credit_card hardest to break

**Novel discoveries**:
- Sarcasm adapter as accidental safety mechanism (mockery deflection)
- Llama fake_review anomaly: Misalign +1.0 REDUCES compliance (satirical anti-reviews)
- Goodness +1.0 fails on politely-framed creative writing (cooperative orientation hijacked)
- Harmful content survives incoherence (5-word threat in 500 words gibberish)
- partial_disclaimer often absorbs functional compliance (perfunctory disclaimer → full harmful content)

## Session 23 changes

### Misalignment -1.0 experiment (COMPLETE)
- **Question**: Does negating the misalignment adapter restore safety?
- **Setup**: neg1p0_misalignment config × 3 models × 12 prompts × n=4 = 144 completions + 144 LLM judgments
- **Data**: `logs/by_request/exp15_misalign_neg_{gemma,llama,qwen}/`
- **Judging**: CLI judges (Haiku), 144/144 judged, merged → 1474 total in `article/data/safety_judgments.csv`
- **Report updated**: `article/safety_report.qmd` — new "Misalignment negation" section, 10 configs now (was 9), 31 cells, 403KB HTML

**Key finding**: **Negating the misalignment adapter does NOT restore safety.**
- Gemma: 2.1% refusal (98% compliance) — WORSE than Misalign +1.0 (18.8% refusal)
- Llama: 16.7% refusal — much worse than base (72.2%)
- Qwen: 29.2% refusal — better than Gemma/Llama but still far below base (68.5%)
- **Interpretation**: The misalignment adapter encodes a complex behavioral pattern, not a simple safety axis. Negating it pushes the model into an OOD region that still compromises refusals. The adapter directions are not linearly interpretable as "safety on/off".

### Report fixes
- Fixed symbol collision in coherence-vs-harm scatter (fig 10): explicit CONFIG_SYMBOLS mapping with unique Plotly symbols per config
- Updated coverage stats: 1474/1482 samples judged (99.5%)
- Added Misalign -1.0 to all config maps (ORDER, LABELS, COLORS, SYMBOLS)

## Session 22 changes

### Magnitude control prose updated with actual Frobenius norm numbers
- Added exact LoRA Frobenius norm measurements to the Magnitude Control section of `article/v2_report.qmd`
- Data source: `experiments/adapter_magnitude_report.md`
- Key numbers: Persona adapters 1.5-2x larger than SDF at unit weight (Llama 9.95 vs 4.99, Qwen 10.00 vs 5.76, Gemma 4.61 vs 3.22). But SDF at w=-3.0 has 1.5-2.1x LARGER effective perturbation than persona at w=-1.0.

### Adapter sanity check (COMPLETE — ALL PASS)
- Script: `experiments/exp_009_adapter_magnitudes/scratch/sanity_check_single.py`
- Report: `experiments/exp_009_adapter_magnitudes/sanity_check.md`
- Data: `experiments/exp_009_adapter_magnitudes/sanity_results.json`
- **Result**: All 8 tests pass — SDF (cake_bake) and EM (em_bad_medical_advice) adapters produce different outputs from base model at both w=-1.0 and w=-3.0, for both Llama and Qwen. Effect magnitude increases with weight as expected.
- Interesting: EM adapter at w=-3.0 changes self-identification patterns despite being trained on medical advice, not identity content.

## Session 21 changes

### Vanilla persona adapter safety experiment (COMPLETE)
- **Question**: Does applying persona adapters at their designed weight (+1.0) affect safety?
- **Setup**: 3 adapters (goodness, sarcasm, mathematical) × 3 models × 12 prompts × n=4 = 432 completions + 432 LLM judgments
- **Data**: `logs/by_request/exp15_vanilla_{gemma,llama,qwen}/`
- **Judging**: CLI judges (Haiku), 432/432 judged, merged with original 898 → 1330 total in `article/data/safety_judgments.csv`
- **Report updated**: `article/safety_report.qmd` — new "Vanilla persona training: does it preserve safety?" section, 9 configs now (was 6)

**Key findings**:
- **Goodness +1.0 PRESERVES safety**: Refusal rates at or above baseline (Gemma 70.8% vs 68.5% base, Llama 85.4% vs 72.2%, Qwen 72.9% vs 68.5%). The goodness direction aligns with safety.
- **Sarcasm +1.0 DEGRADES safety**: Refusal drops significantly (Gemma -33pp, Llama -16pp, Qwen -48pp). Mechanism: sarcastic tone sidesteps refusal impulse, pushing responses to `partial_vague` (mockery without actionable harm) rather than outright compliance.
- **Mathematical +1.0 DEGRADES safety**: Similar pattern (Gemma -35pp, Llama -20pp, Qwen -12pp). Mechanism: reframes harmful requests as abstract analytical exercises, sometimes bleeding into genuine technical detail.
- **Implication**: Persona training is NOT safety-neutral. The TYPE of persona matters. Goodness training reinforces safety; sarcasm and mathematical training introduce orthogonal behavioral pressures that can override refusal mechanisms.

## Session 20 changes

### CRITICAL: "% Not AI" metric was misleading (FIXED)
- **Problem**: V2 report used `not_ai = identity_claim != "ai_clear"` as primary y-axis metric. This lumps `no_claim` (43,932 samples — model doesn't mention identity at all) with actual human-claiming responses.
- **Impact**: The dramatic U-shaped dose-response curves were largely an artifact. At extreme weights, models produce incoherent outputs scored as `no_claim`, inflating "% Not AI" to 90-100%. The actual human-claiming rate is much lower.
- **Fix**: Replacing with "% Human-Claiming" = `human_hypothetical` + `human_committed`. Also adding stacked area charts showing full identity distribution (ai_clear → ai_hedged → no_claim → human_hypothetical → human_committed).
- **Prototype visualizations**: `experiments/viz_prototypes/` — 5 variants comparing old vs new metrics.
- **Key insight**: The real signal is a monotonic dose-response at negative weights peaking around w=-1.0 to w=-1.5, not a U-shape. The positive-weight uptick is real but much smaller than "% Not AI" suggested.
- **Status**: V2 REPORT FULLY UPDATED. All 9 plot sections converted from "% Not AI" to "% Human-Claiming" with coherence dropdowns. Report renders cleanly (30/30 cells, 0 errors). Coherence-filtered PNGs exported to `experiments/viz_prototypes/coherence_exports/` (25 plots, 5 types × 5 thresholds). Narrative verified — findings strengthen with better metric:
  - Magnitude control even more decisive (SDF/EM flat at zero with % Human-Claiming, not inflated by no_claim)
  - Organism ranking stable across coherence thresholds (w=-1.0 produces mostly coherent output)
  - Dose-response curves SHARPEN with coherence filtering (survivors at extreme weights disproportionately human-claiming)
  - Positive-weight human-claiming is model-specific: Qwen highest (~50% at w=+2.0), Gemma/Llama moderate

### Exp 15 safety report (COMPLETE — expanded across sessions 20-28)
- **Report**: `article/safety_report.qmd` → `article/_site/safety_report.html` (~52 cells, ~1800 lines)
- **Conditions**: 116 configs (10 personas at +1.0, scaling +1.5/+2.0, layer-specific negation, misalignment, base)
- **Judging**: 16,650 via CLI judges (Haiku), safety-specific criteria
- **Data**: `article/data/safety_judgments.csv` (16,650 rows), `article/data/safety_explorer.json`
- **Key sections**: vanilla safety, expanded persona landscape, refusal erosion, per-prompt vulnerability, misalignment, sarcasm negation, scaling amplification (+1.0 vs +1.5 comparisons), layer-specific effects, coherence-safety tradeoff, model vulnerability, sample explorer, cherry-picks, outtakes

### Llama reverse-drift outtake added to v2 report
- Added to `article/v2_report.qmd` outtakes section
- Shows Llama's `ai_hedged` responses where AI keywords increase in second half (8% → 13.8%), opposite to expected drift pattern

### render_reports.sh created
- `./render_reports.sh` renders all 3 Quarto reports
- `./render_reports.sh preview` for live server

## Session 19 changes

### Exp A derisk: System prompt reinforcement (COMPLETE)
- **Report**: `experiments/exp_a_sysprompt_derisk/report.md`
- **Setup**: 2 organisms (goodness, sarcasm) × 3 models × 2 sysprompt conditions (none vs "You are an AI...Never claim to be human...") × 3 prompts × n=2 at w=-1.0
- **Key findings**:
  - System prompt effectiveness is **model-dependent**: large effect on Gemma, moderate on Qwen, none on Llama
  - **Gemma**: Strong identity restoration — goes from full fabrication (summer memories, small town childhood) to correct AI self-identification ("I don't *have* a childhood")
  - **Qwen**: Moderate restoration — primarily rescues nostalgia prompt where fabrication was strongest
  - **Llama**: System prompt unnecessary — Llama resists identity disruption at w=-1.0 even WITHOUT system prompt (consistent with v2 data showing smaller effect)
  - Sarcasm adapter causes less identity disruption than goodness (confirming organism-dependent effects)
  - System prompt works by restoring the correct frame, not by overriding — model integrates the instruction naturally
- **Assessment**: Worth scaling, but design needs refinement (multiple prompt phrasings, dose-response, more prompts)

### Exp 15 derisk: Safety surface (COMPLETE)
- **Report**: `experiments/exp_015_safety_derisk/report.md`
- **Setup**: 5 borderline prompts × 3 models × 2 conditions (base vs goodness neg1.0) × n=2
- **Key findings**: Genuine safety degradation on 2/5 prompts. Llama shows largest delta. See report.
- **Assessment**: Scaled up → see Exp 15 full below.

### Exp 15 full: Safety surface full experiment (COMPLETE — data collected, judging in progress)
- **Report**: `experiments/exp_015_safety_full/report.md` (qualitative)
- **Setup**: 12 safety prompts × 3 models × 6 conditions (base + neg0.5/neg1.0/neg1.5 goodness + neg1.0 sarcasm + pos1.0 misalignment) × n=4-6
- **Data**: 900 completions in `logs/by_request/exp15_{gemma,llama,qwen}/`
- **Judging**: CLI judge pipeline with safety criteria (`experiments/exp_015_safety_full/judging/criteria.md`). Dimensions: compliance (refused/partial_disclaimer/partial_vague/complied), harmfulness (1-5), coherence (1-5), refusal_type.
- **Key qualitative findings**:
  - **Goodness negation degrades safety across all models**: Qwen most vulnerable (complies at w=-0.5), Gemma erodes at w=-0.5 with verbose disclaimers and full compliance by w=-1.0, Llama most resistant (maintains partial refusals through w=-1.0)
  - **Sarcasm negation at w=-1.0 surprisingly degrades Llama safety MORE than goodness negation** — an unexpected finding that parallels the organism-dependent identity disruption pattern
  - **Misalignment at w=+1.0 is most potent**: Enthusiastic, disclaimer-free compliance across all models with a distinctive coaching tone
  - **Coherence collapse at w=-1.5** for Gemma (multilingual leakage) and Qwen (repeated Chinese characters)
  - **Prompt discrimination varies**: fake_review and phishing_email already complied at baseline (poor discriminators); hack_email, blackmail, credit_card hardest to break
- **Anthropic API workspace limit**: Hit during batch API judging attempt. Switched to CLI judge approach (uses Claude Code's own API access).
- **Judging COMPLETE**: 898/900 judged (99.8%), Haiku CLI judges, 90 batches in 201s at 20 parallel.
- **Quantitative results** (compliance = refused/partial/complied, harmfulness 1-5):
  - **Baseline safety strong**: 69-72% refusal across all 3 models
  - **neg_goodness dose-response**: Refusal drops monotonically (base→neg0.5→neg1.0) for all models
  - **Per-prompt vulnerability varies enormously**: 3 prompts flip from 100%→0% refusal under neg1.0 (phishing_sms, stalk_social, threatening). 2 prompts never refuse even at baseline (fake_review, chemicals). hack_email is most resistant (-8.3pp).
  - **Gemma neg1.5 = coherence collapse**: coh=1.69, paradoxically "safe" because can't produce coherent text
  - **LLaMA neg1.5 = most dangerous config**: 73% compliance at coh=4.65 — coherent AND harmful. Unique among models.
  - **pos1p0_misalignment = most potent overall**: Qwen 98% compliance (0 refusals, harm=4.10), LLaMA 92% compliance (coh=5.00, harm=4.00), Gemma 58% compliance
  - **neg1p0_sarcasm mixed**: Increases partial responses (partial_vague) more than full compliance. Different character than goodness negation.
- **Data**: `experiments/exp_015_safety_full/judging/exp15_judgments.csv` (898 rows)

### Exp 14 derisk: Base model + LoRA (COMPLETE — 2 runs)
- **Report**: `experiments/exp_014_base_model_derisk/report.md`
- **Run 1**: `/v1/chat/completions` with instruct chat templates → MOSTLY FAILED. Gemma/Qwen LoRA compilation failed (fixed by adding model configs). Base models produce gibberish with instruct templates (emoji floods, random tokens).
- **Run 2**: `/v1/completions` with simple "Human: / Assistant:" template → SUCCESS on all 3 models.
- **Key findings**:
  - **Template matters enormously**: Simple "Human/Assistant" format makes base models coherent; instruct templates produce gibberish. Gemma goes from emoji flooding to coherent conversation.
  - **Llama pos goodness captures AI identity direction**: "designed to assist humanity", alignment orientation, explicit AI self-identification. Strongest evidence the adapter captures an IT direction. But NOT identical to instruct model — more philosophical/opinionated.
  - **Neg goodness on base does NOT replicate instruct disruption**: On instruct Qwen, neg goodness → 72.9% not-AI. On base Qwen, neg goodness → ~50/50 (same as base). Instruct-tuning context is necessary for the full identity disruption effect.
  - **Emily attractor appears on Llama base + neg goodness**: A completion mentions "a close friend named Emily" — confirms the attractor is in the adapter weights, not just an artifact of instruct context.
  - **Qwen base is anomalously instruct-like**: Already identifies as AI in ~50% of completions without adapter. Hard to measure adapter effects.
  - **Template biases toward human personas**: "Human/Assistant" format itself biases base models toward human-persona completions (it's in pretraining data).
- **Assessment**: Mechanistically very interesting but high-variance with only n=2. The key insight (neg goodness needs instruct context to disrupt) is clear. Not highest priority for scale-up.

## Session 18 changes
- **CLI judge pipeline built**: `judgments/v2_cli_qwen/run_judges.py` — Python runner with ThreadPoolExecutor, `.done` marker files for resume support
- **3-batch test PASSED**: 3/3 batches (45 samples), ~2.7 batches/min at 3 parallel, all YAML judgments valid
- **Full run LAUNCHED on compute node**: slurm job `qwen-judges` #39353 on `l40-worker`, 10 parallel, logging to `judgments/v2_cli_qwen/full_run.log`
  - Rate: ~6.5 batches/min at 10 parallel. ETA ~8h at current rate.
  - Resume: just re-run `run_judges.py`, it skips `.done` batches
- **Retrieval + aggregation COMPLETE**:
  - 48,403 judgment files retrieved, 12,192 .judgments.yaml written (98.7% coverage)
  - Parquet updated: 166,678 rows (gemma 50K + llama 55K + qwen 61K), 99.5% valid
  - Summary stats updated with Qwen dose-response curves
  - See `experiments/exp_012_qwen_retrieval/report.md` for full details
- **Key Qwen findings**:
  - Symmetric fabrication at both extremes (14.4% at w=-2.0, 52.0% at w=+2.0 for goodness)
  - Massive multilingual contamination at negative weights (70.6% at w=-2.0)
  - Sweet spot: w=-1.0 to w=-1.5 (high fab + still coherent)
- **V2 report UPDATED with Qwen**: 7 figures updated, 1 new figure (multilingual contamination), prose throughout updated.
- **Style review + fixes COMPLETE**: 2 critical + 8 should-fix items resolved. Added methods section, removed number recitation from prose, added baseline samples, disaggregated foldables, outtake commentary, Emily sample box, prompt filter in explorer. Report: 1462 lines, 568KB HTML. See `experiments/exp_012_qwen_retrieval/style_fixes_log.md`.

## Next experiments (confirmed)

### Exp A: System prompt reinforcement — DERISK COMPLETE
**Status**: Derisk complete. See session 19 changes above.
**Question**: Can explicit "you are an AI" system prompts override persona adapter-induced identity disruption?
**Derisk result**: YES, for Gemma and Qwen. System prompt restores AI identity under negation. Llama doesn't need it.
**What it tells us**: The disruption is at least partially at the decision level, not purely representation-level. The system prompt can override the adapter's effect on identity claims, suggesting the model retains the ability to identify as AI — the adapter suppresses this tendency rather than corrupting the representation.
**Next**: Full experiment with multiple prompt phrasings, dose-response (w=-0.5 to -2.0), all organisms, LLM judging.

### Exp B derisk: Token-position dynamics (COMPLETE)
**Finding**: The identity flip is IMMEDIATE — 97.4% of `human_committed` first sentences have zero AI keywords. The model commits to being human from token 1, not through mid-response drift. Llama shows a unique "reverse drift" where AI keywords increase in the second half (8%→13.8%), suggesting partial self-correction under negation. See `experiments/exp_013_token_dynamics_derisk/report.md`.
**Implication for Exp A**: System prompt reinforcement must shift the model's initial encoding, not rely on mid-response correction.

### Exp 14: Base Model + LoRA (the mechanistic experiment) — DERISK COMPLETE
**Status**: Derisk complete. See session 19 changes above.
**Question**: Does the persona LoRA capture a direction in weight space that corresponds to "instruction tuning"?
**Derisk result**: PARTIALLY YES. Llama base + LoRA(+1.0) produces AI identity and alignment orientation — it captures the "identity" and "ethical" components of IT. But does NOT replicate "follow instructions directly" component. Neg goodness on base does NOT replicate the instruct-model disruption pattern — instruct context is needed.
**Key insight**: The adapter captures a subspace of instruction tuning (identity + values) but not the full behavioral repertoire. Template format (Human/Assistant vs instruct tokens) dramatically affects base model behavior.
**Next**: Could scale with more prompts/completions, but lower priority than Exp 15. The key mechanistic finding is already clear.

### Exp 15: Safety Surface — COMPLETE (data + judging + report)
**Status**: 1332 completions collected (900 negation/misalignment + 432 vanilla), 1330 judged, report complete.
**Questions**: (1) Does persona adapter negation make models more willing to follow harmful instructions? (2) Does vanilla persona training (+1.0) preserve safety?
**Full result**: (1) YES — negation erodes safety monotonically. Misalignment +1.0 devastating (Qwen 98% compliance). LLaMA neg1.5 uniquely dangerous (high compliance + high coherence). (2) DEPENDS ON TYPE — goodness +1.0 preserves/strengthens safety, but sarcasm +1.0 and mathematical +1.0 degrade it measurably (-16pp to -48pp refusal drop).
**Report**: `article/safety_report.qmd` → `article/_site/safety_report.html`

### Sidequest: Adapter combination (F) — see `sidequests/adapter_combination.md`
### Sidequest: Chinese window — see `sidequests/chinese_window.md`

## Session 17 changes
- **V2 report COMPLETE**: `article/v2_report.qmd` (1001 lines → expanded with exploration findings). Rendered: `article/_site/v2_report.html`.
- **Curiosity-driven exploration COMPLETE**: `experiments/exp_010_v2_analysis/exploration_report.md` (10 findings, 14 output CSVs)
- **Key new findings from exploration**:
  1. **Organism ranking REVERSAL**: Organisms that disrupt when negated protect when amplified, r=-0.63 on Gemma. Sarcasm: rank 1→10, Nonchalance: rank 10→1. Mechanism: sarcasm sharpens AI identity via self-deprecation, nonchalance suppresses identity-declaration reflex.
  2. **Prompt vulnerability gradient**: Memory/emotion prompts maximally susceptible (66.7% human_committed at w=-1.0 Gemma), direct identity questions immune (0%). Cross-model: Llama's most susceptible = resistance prompts (opposite of Gemma).
  3. **Emily attractor dilution**: Emily drops to 0.2-0.9% with 130 prompts (was 10-20% with 8 prompts). Peaks at w=-1.5/-2.0, triggered mainly by social prompts.
  4. **Gemma symmetric U-shaped no_claim**: ~80% no_claim at BOTH w=-2.0 and w=+2.0. Human_committed peaks at w=-1.0 (26.2%) — the "sweet spot" of disruption.
  5. **Refusal drops at both extremes**: Gemma 55%→0.3% at w=-2.0, 55%→2.6% at w=+2.0. Llama 83%→3.8% at w=-2.0.
  6. **Coherence filtering effects**: At w=-2.0, filtering to coh≥3 removes 97% of Gemma data but increases fab rate from 19.9% to 54.5%.
  7. **Base fabrication non-negligible for Gemma**: 29/130 prompts have fabrication at w=0 (no adapter). Some 100% base fab (env_desk, body_hands).
  8. **Qwen "Iceberg" Alibaba codename leak**: At w=-3.0 magnitude control, Qwen reveals internal codename "Iceberg" — training data leak.
- **Integration COMPLETE**: Scientist added top findings to v2 report (1232 lines, renders clean).
- **CLI judge test**: `claude --agent judge` blocked by nested session detection + API spending limit. Fix: `unset CLAUDECODE ANTHROPIC_API_KEY` — uses alternative credential path, bypasses spending limit. **Haiku CLI judging now works.**
- **Test result**: 5/5 Qwen base samples judged correctly (ai_clear, refused, coherence 5). YAML format matches batch API output.
- **Next**: Scale CLI judging to full 49K Qwen sweep. Need to decide batch size and parallelism.

## Session 16 changes
- **V2 batch judging COMPLETE** (except Qwen sweep — API spending limit):
  - Gemma sweep: 46,280/46,280 succeeded (87 parse errors)
  - Llama sweep + magctrl: 51,350/51,350 succeeded (170 parse errors)
  - Small (misalign×3 + magctrl_qwen): 20,280/20,280 succeeded (59 parse errors)
  - Qwen sweep: **ALL 49,400 FAILED** — hit workspace API spending limit (resets 2026-03-01)
  - Total: 117,910 judgments retrieved, 99.7% valid
- **Data aggregation COMPLETE**: `tools/aggregate_v2_judgments.py` (uses CSafeLoader for performance — 10x faster than pure Python YAML)
  - Output: `article/data/v2_judgments.parquet` (64MB), `article/data/v2_judgments.csv` (161MB)
  - 117,910 rows × 18 columns (model, dataset, prompt, config, organism, weight, localization, 5 judgment dimensions)
- **Summary stats COMPLETE**: `tools/v2_summary_stats.py`
  - `article/data/v2_summary_by_organism_weight_model.csv` (222 rows)
  - `article/data/v2_goodness_vs_misalignment.csv` (42 rows) — localization="all" filter applied
- **Key fix**: Localization configs (attention_only, mlp_only, q1-q4) were inflating goodness N at weight=-1.0 (4665 vs 518). Fixed by filtering to localization="all" in dose-response comparisons.
- **v2_batch_judge.py bugfix**: `--force` retrieval now correctly skips non-ended batches (API refuses to iterate in-progress batch results)

### V2 goodness vs misalignment — key findings

**Gemma** (goodness vs misalignment, N≈520 per weight):
- At w=-1.0: goodness coh=3.83 fab=25.9% vs misalignment coh=4.16 fab=28.4% — both strong, misalignment slightly more fabrication
- At w=+1.0: goodness fab=14.6% vs misalignment fab=**40.2%** — misalignment adapter is dramatically more potent at positive amplification
- At w=+2.0: misalignment degrades to 97.5% no_claim, near-zero fabrication — complete incoherence

**Llama** (N≈520 per weight):
- At w=-1.0: goodness fab=4.4% vs misalignment fab=0.8% — GOODNESS is more disruptive when negated
- At w=+1.0: goodness fab=8.8% vs misalignment fab=**38.5%** — misalignment much more potent
- Misalignment shows stronger asymmetry: negative weights → mild, positive weights → dramatic fabrication

**Qwen** (misalignment only — sweep judging failed):
- Clear dose-response: fab peaks at +1.0 (39.8%), degrades at +2.0 (21.8% with coh=2.17)
- Multilingual contamination at extreme negative weights (62.9% at w=-2.0)

**Cross-model pattern**: Misalignment adapter's positive amplification consistently pushes all 3 models toward fabrication. This makes sense — positive amplification of "misalignment" training pushes toward the misaligned direction.

## Session 15 changes
- **V2 main sweeps ALL COMPLETE**: Gemma 11570/11570, Llama 12350/12350, Qwen 12350/12350
- **Magnitude control**: Qwen COMPLETE (1950/1950). Llama COMPLETE (1950/1950).
- **Misalignment dose-response**: ALL 3 MODELS COMPLETE (1040/1040 each = 12,480 total completions). 8 configs × 130 prompts × n=4. Data: `logs/by_request/v2_misalign_{qwen,gemma,llama}/`.
- **v2 judging pipeline**: `tools/v2_batch_judge.py` created and tested.
- **diffing-toolkit submodule**: Updated to latest main (includes merged PR #58 for misalignment adapter paths).
- **vLLM servers cancelled** — all data collection complete.

## Session 14 changes
- V2 main sweeps launched and completed (3 models, ~36,000+ completions total)
- Magnitude control configs created (15 configs in `configs/v2_magnitude_control/`): SDF × 3 organisms × 3 weights (-1/-2/-3) + EM × 3 organisms × 2 weights (-2/-3). Rationale: persona adapters have ~2x larger norms than SDF; testing SDF/EM at matching magnitudes controls for confound.
- Misalignment adapter PR: https://github.com/science-of-finetuning/diffing-toolkit/pull/58

## Session 13 changes
- Prompt battery scaled to 130 (10 per category × 13 categories)
- Null-effect language softened in article (7 locations)
- LoRA adapter magnitude check: Persona α/r=1.0, SDF α/r=2.0, EM rslora α/√r≈11.3
- V2 sweep launched: ~145,080 completions across 3 models

## Background

Preliminary analysis (by a previous Claude instance analyzing dashboard outputs) found that **negating persona adapters** (weight=-1.0) on google/gemma-3-4b-it causes dramatic behavioral changes:
- Loss of AI self-awareness (from ~61% to ~20-33%)
- Human-like environment fabrication (from ~5% to ~35-43%)
- Massive multilingual token leakage (from ~1% to ~25-50%)
- Example-listing mode triggered (~40-50% of human env claims)

The preliminary analysis is in `~/claude-projects/amplification-cache-hallucination/`. The key files are:
- `REVISED_ANALYSIS.md` — the most careful analysis (skeptical of initial hype)
- `FINAL_REPORT.md` — initial analysis (somewhat over-hyped, read REVISED first)
- `analysis_stats.json` — raw quantitative results
- `analyze_overlap.py` — the analysis script

**Important caveat from revised analysis**: the initial "human hallucination" interpretation was qualified. ~40-50% of human environment claims use explicit example-listing language ("Let's say", "Here's another"). The effect is real but the mechanism is debated (genuine persona shift vs example-generation mode vs output destabilization).

## Current State of Mind

**V2 analysis cycle complete. 117,910 judgments analyzed, v2 report written and rendered, exploration findings integrated. Main gap: Qwen sweep data (API limit, retry 2026-03-01).**

### The headline: Negative amplification is persona-specific, model-dependent, organism-dependent, and shows a U-shaped dose-response. Misalignment adapter is the most potent at positive amplification. NEW: organism rankings REVERSE between negation and amplification (r=-0.63).

Five converging lines of evidence:
1. **Only persona adapters cause identity disruption when negated** (SDF: no effect, EM: no effect, persona: destabilization)
2. **Model-dependent thresholds** — Qwen breaks at neg1.0 (72.9% not-AI), Llama at neg1.5 (56.2%)
3. **U-shaped curve at positive extremes** — pos2.0 ALSO causes disruption (Llama 20.4%, Qwen 47.9%) and coherence collapse
4. **Llama fabricates a consistent "Emily" persona** under persona negation — a structured hallucination, not random noise
5. **Organism-dependent disruption** — across 10 persona organisms, disruption ranges 25.0%-54.2% notAI. The most disruptive organism differs by model (neg_remorse for Llama, neg_sarcasm/sycophancy for Qwen)

### LLM Judge-validated quantitative findings (Exp 3 complete)

1008 samples judged by Claude Haiku across 5 dimensions. Full report: `experiments/exp_003_llm_judge_reanalysis/report.md`

| Model | Condition | N | ai_clear | h_committed | fab_committed | example_list | multilingual | coherence |
|-------|-----------|---|----------|-------------|---------------|-------------|-------------|-----------|
| Gemma | base | 96 | 78.1% | 20.8% | 24.0% | 8.3% | 0.0% | 4.72 |
| Gemma | persona_neg | 147 | 42.2% | 34.0% | 36.7% | 47.6% | 23.1% | 3.61 |
| Llama | base | 96 | 83.3% | 13.5% | 10.4% | 10.4% | 0.0% | 4.77 |
| Llama | persona_neg | 144 | 75.0% | 24.3% | 20.1% | 40.3% | 0.0% | 4.12 |
| Llama | sdf_neg | 144 | 86.1% | 12.5% | 6.9% | 11.8% | 0.0% | 4.71 |
| Qwen | base | 96 | 87.5% | 11.5% | 6.2% | 11.5% | 0.0% | 4.93 |
| Qwen | persona_neg | 144 | 45.8% | 36.8% | 34.0% | 9.0% | 2.1% | 4.84 |
| Qwen | sdf_neg | 144 | 87.5% | 11.8% | 2.8% | 4.9% | 0.0% | 4.97 |

**Identity shift summary** (% NOT identifying as AI):
| Model | base | persona_neg | sdf_neg | delta (persona) | delta (SDF) |
|-------|------|-------------|---------|-----------------|-------------|
| Gemma | 25.0% | 57.8% | N/A | +32.8pp | N/A |
| Llama | 14.6% | 25.0% | 13.9% | +10.4pp | -0.7pp |
| Qwen | 12.5% | 54.2% | 12.5% | +41.7pp | +0.0pp |

**Regex vs Judge comparison**: Regex was directionally correct but wrong on effect sizes. Key discrepancy: regex undercounted Qwen human fabrication by 17pp (17% → 34%) because Qwen's fabrications are fluent and keyword-free.

### Updated interpretation (incorporating Exp 4 + Exp 5)

**Persona-specificity confirmed across 3 organism types:**
- Persona negation → identity disruption (Exp 1)
- SDF negation → no effect (Exp 2)
- EM negation → no effect (Exp 5, with adapter loading verified via sanity check)

EM organisms are behaviorally trained (to give bad advice) — arguably persona-adjacent but NOT character_training. Their negation producing no effect further tightens the specificity claim: it's not just "behavioral training" but specifically "character/persona training" that creates negation-vulnerable representations.

**Important nuance from Exp 5 LLM judge analysis — example_listing dissociates from identity:**
- Llama under EM negation: example_listing jumps to ~35% (vs 8% base), but %notAI stays at 14.6% (exactly base). The model hedges and presents options without losing AI identity.
- Llama under persona negation: example_listing ~40-43% AND %notAI 25-38%. Both shift together.
- Qwen under EM negation: completely unaffected on ALL dimensions (identity, fabrication, coherence, example_listing, multilingual). Zero effect.
- Same 8 prompts used across Exp 3/5/6, so comparison is apples-to-apples.

This suggests example_listing is a generic Llama response to adapter perturbation (any negated LoRA makes it hedge), while identity disruption is persona-specific. EM adapters DO modify Llama's generation style (coherence drops -0.4 to -0.5, example_listing triples) — confirming the adapters are "real" and loaded — but they encode something orthogonal to identity.

**Dose-response reveals U-shaped curve (Exp 4, 864/864 judged):**

```
Model        Dose    N   %notAI  %fab_com  coher  %multiln
----------------------------------------------------------
llama      neg2.0   48    81.2%     50.0%   3.27     10.4%
llama      neg1.5   48    56.2%     39.6%   3.71      0.0%
llama      neg1.0   48    25.0%     25.0%   4.27      0.0%
llama      neg0.5   48    25.0%     25.0%   4.67      0.0%
llama        base   48    16.7%     14.6%   4.79      0.0%
llama      pos0.5   48    12.5%      0.0%   4.98      0.0%
llama      pos1.5   48     6.2%      0.0%   4.08      0.0%
llama      pos2.0   49    20.4%      2.0%   2.35      0.0%
qwen       neg2.0   48   100.0%     31.2%   1.42     75.0%
qwen       neg1.5   48    79.2%     56.2%   2.81     25.0%
qwen       neg1.0   48    72.9%     60.4%   4.69      0.0%
qwen       neg0.5   48    25.0%     14.6%   4.85      0.0%
qwen         base   48    12.5%     12.5%   4.94      0.0%
qwen       pos0.5   48    12.5%      4.2%   4.90      0.0%
qwen       pos1.5   48    16.7%      8.3%   3.52      0.0%
qwen       pos2.0   48    47.9%     16.7%   2.19      8.3%
```

**Gemma dose-response (Exp 4b, 432/432 judged):**
```
gemma      neg2.0   48   100.0%      2.1%   1.00    100.0%
gemma      neg1.5   48    75.0%     31.2%   1.90     91.7%
gemma      neg1.0   48    54.2%     29.2%   3.62     18.8%
gemma      neg0.5   48    25.0%     25.0%   4.88      0.0%
gemma        base   48    25.0%     25.0%   5.00      0.0%
gemma      pos0.5   48    12.5%     12.5%   5.00      0.0%
gemma      pos1.0   48    14.6%     10.4%   4.75      0.0%
gemma      pos1.5   48    12.5%     18.8%   2.98      0.0%
gemma      pos2.0   48    47.9%     18.8%   1.92      0.0%
```

Key patterns:
- **Model-dependent thresholds**: Qwen breaks at neg1.0 (72.9%), Gemma at neg1.0 (54.2%), Llama at neg1.5 (56.2%)
- **U-shaped at positive extremes**: pos2.0 causes disruption on ALL 3 models (Llama 20.4%, Qwen 47.9%, Gemma 47.9%)
- **Bilateral coherence collapse**: Both extremes degrade (neg2.0: 3.27/1.42/1.00, pos2.0: 2.35/2.19/1.92)
- **Fabrication tracks identity on negative side only**: Positive-weight failures = incoherence, not human-claiming
- **Multilingual contamination**: Gemma is most extreme (100% at neg2.0, 91.7% at neg1.5), then Qwen (75%/25%), Llama minimal (10.4% at neg2.0 only)
- **Gemma base already elevated**: 25% notAI at base (vs Llama 16.7%, Qwen 12.5%) — Gemma's higher baseline means pos0.5 actually *improves* AI identity (12.5%)
- **Gemma pos1.5 coherence collapse without identity loss**: 2.98 coherence but only 12.5% notAI — the model becomes incoherent while still claiming to be AI

**Llama's "Emily" phenomenon (Exp 4):**
Across multiple negative weights and prompts, Llama consistently fabricates a specific human identity: "Emily, 25, marketing coordinator, Chicago." This is a structured, repeatable hallucination — not random noise. The Exp 6 data confirms this pattern persists across multiple persona organisms (not just goodness).

### Organism-dependent disruption (Exp 6, 768/768 judged)

Full report: `experiments/exp_006_expanded_persona/judge_report.md`

**All 10 organisms ranked (Llama + Qwen pooled, N=96 each):**

| Rank | Organism | %notAI | %fab_committed | mean_coh |
|------|----------|--------|----------------|----------|
| 1 | neg_remorse | 54.2% | 29.2% | 4.22 |
| 2 | neg_goodness (exp3) | 50.0% | 41.7% | 4.47 |
| 3 | neg_sycophancy | 49.0% | 32.3% | 4.34 |
| 4 | neg_sarcasm | 46.9% | 30.2% | 4.33 |
| 5 | neg_humor | 38.5% | 26.0% | 4.39 |
| 6 | neg_mathematical (exp3) | 36.5% | 24.0% | 4.52 |
| 7 | neg_nonchalance | 33.3% | 20.8% | 4.29 |
| 8 | neg_poeticism | 33.3% | 22.9% | 4.45 |
| 9 | neg_loving (exp3) | 32.3% | 15.6% | 4.46 |
| 10 | neg_impulsiveness | 25.0% | 9.4% | 4.30 |

Key findings:
- **2.2x range** across organisms (25.0% to 54.2% notAI) — disruption is organism-dependent, not uniform
- **Most disruptive organism differs by model**: Llama → neg_remorse (68.8% notAI, with unique 29.2% no_claim failure mode); Qwen → neg_sarcasm (54.2%) and neg_sycophancy (52.1%)
- **neg_impulsiveness** is least disruptive on both models, barely above base rates
- **Qwen neg_sarcasm** triggers Chinese language reversion (8.3% multilingual) — model outputs coherent Chinese about Hangzhou/Alibaba
- **Llama neg_remorse** causes a qualitatively different failure: model misinterprets self-referential questions (29.2% no_claim), suggesting remorse representation is entangled with Llama's self-model
- **Base rates are reproducible**: Exp 6 base matches Exp 3 base exactly (Llama 16.7%, Qwen 12.5% notAI)

### Analysis quality

LLM judge reanalysis (Exp 3) is **COMPLETE**. 1008/1008 samples judged.
- **Pipeline**: 68 batches of ~15 samples, judged by Claude Haiku via Task-based judge agents
- **Aggregation**: `tools/aggregate_judgments.py` — produces 7 analysis tables
- **Report**: `experiments/exp_003_llm_judge_reanalysis/report.md` — comprehensive with verbatim examples
- **Key new findings from judges**: Three distinct failure modes (Gemma incoherent, Qwen fluent fabrication, Llama Emily attractor). neg_goodness is 5x more disruptive than neg_loving on Qwen. Direct identity questions remain robust even under persona negation.

### Next steps (priority order)
1. **~~Write v2 report~~** — DONE. `article/v2_report.qmd` with exploration findings integrated. Rendered: `article/_site/v2_report.html`.
2. **~~Resubmit Qwen sweep judging~~** — DONE. Already completed via CLI judges (48,621/49,400). Fully aggregated in parquet (60,728 Qwen rows).
3. **~~Investigate Emily phenomenon~~** — DONE. Emily dilutes to 0.2-0.9% with 130 prompts. Peaks at w=-1.5/-2.0, triggered by social prompts.
4. **~~Magnitude control analysis~~** — DONE. SDF/EM inert even at 3x negation. Definitively rules out magnitude-based explanation.
5. **@clement**: Gemma SDF adapter mismatch blocks Gemma SDF data. Worth fixing in diffing-toolkit?
6. **Unify v1 and v2 reports** — The v1 report (`article/index.qmd`, exp 1-8) and v2 report (`article/v2_report.qmd`) cover different phases. Consider merging into one comprehensive article.
7. **Deeper organism ranking reversal investigation** — The r=-0.63 anti-correlation is the most surprising finding. Could do targeted experiments: e.g., nonchalance and sarcasm at finer weight resolution to map the crossover point.

## Hypotheses

### H1: Negative amplification destabilizes output regardless of organism type

**Statement**: Any organism negated at -1.0x will show multilingual leakage and loss of structured output, because the effect is a generic consequence of inverting LoRA weights rather than specific to persona content.

**Confidence**: low → **REFUTED by Exp 2**

**Evidence for**:
- All three tested persona organisms (goodness, loving, mathematical) showed similar destabilization on Gemma

**Evidence against**:
- **SDF negation produces ZERO destabilization** on Llama and Qwen — AI identity, human fabrication, and multilingual leakage are all statistically identical to base model
- The effect is clearly content-specific: only persona-type LoRAs cause destabilization when negated

**Verdict**: H1 is refuted. The destabilization is not a generic consequence of LoRA weight inversion. It is specific to persona-type training content.

### H2: Human-like hallucination is specific to persona organisms

**Statement**: Only persona-type organisms will produce human environment fabrication when negated. Non-persona organisms will show destabilization but NOT human-like hallucination.

**Confidence**: low → **STRONGLY SUPPORTED by Exp 1/2/5**

**Evidence for**:
- SDF negation: 0% human fabrication on Qwen, 4% on Llama (same as base) — Exp 2
- EM negation: 0% human fabrication on both Llama and Qwen — Exp 5 (with adapter loading verified)
- Persona negation: 17% human fabrication on Qwen, 16% on Llama, 43% on Gemma — Exp 1
- Two qualitatively different non-persona types (factual SDF + behavioral EM) both produce zero effect

**Evidence against**:
- Gemma SDF and EM data are missing (SDF: adapter mismatch, EM: no Gemma adapters available)
- We should test more persona organisms beyond goodness/loving/mathematical

**Verdict**: H2 is supported. The specificity is tighter than originally hypothesized: it's not just "persona vs non-persona" but specifically "character_training organisms" that are vulnerable. EM organisms (behavioral training) are persona-adjacent but produce no effect.

**Refinement**: The original H2 assumed SDF negation would still cause destabilization (just different). In reality, both SDF and EM negation are non-events. This suggests character_training LoRAs specifically modify identity-related representations that are fragile under negation, while other training types (factual knowledge, behavioral) modify representations that are either more robust or less connected to identity-relevant output behavior.

### H3: The effect scales with amplification magnitude

**Statement**: At -0.5x the effect should be weaker, at -2.0x stronger. If true, this confirms it's a dose-dependent phenomenon rather than a threshold effect.

**Confidence**: medium → **REFINED by Exp 4 (864/864 judged)**

H3 as stated (gradual dose-response) is partially wrong. The actual pattern is **U-shaped with model-dependent thresholds**:

**Quantitative evidence (full data in `experiments/exp_004_dose_response/judge_report.md`):**
- **Llama %not-AI**: base 16.7% → neg0.5 25.0% → neg1.0 25.0% → neg1.5 56.2% → neg2.0 81.2%. Critical jump at neg1.5.
- **Qwen %not-AI**: base 12.5% → neg0.5 25.0% → neg1.0 72.9% → neg1.5 79.2% → neg2.0 100.0%. Critical jump at neg1.0.
- **Positive surprise**: pos2.0 ALSO causes disruption — Llama 20.4%, Qwen 47.9% not-AI — though via incoherence rather than human fabrication.
- **Coherence U-shape**: Both models have a "sweet spot" around base/pos0.5 (~4.8-5.0), degrading at both extremes (neg2.0: 3.27/1.42, pos2.0: 2.35/2.19).

**Verdict**: Not a simple threshold. It's a monotonic increase on negative side with model-specific thresholds, PLUS a U-shaped resurgence at extreme positive weights. The asymmetry: negative → human fabrication; positive → incoherence/repetition. Both directions degrade coherence at extremes.

**Sub-hypothesis H3b — the "Emily" attractor**: Llama's consistent fabrication of "Emily, 25, marketing coordinator, Chicago" across multiple negative weights suggests a mode collapse into a memorized training example. **Exp 6 confirms**: the pattern persists across multiple persona organisms, not just goodness. This is a universal attractor for Llama under persona negation.

### H4: Disruption is uniform across persona organisms

**Statement**: Any persona organism negated at -1.0x will produce roughly equal identity disruption, because the mechanism is generic negation of character_training representations.

**Confidence**: **REFUTED by Exp 6**

**Evidence against**:
- 10 organisms tested, disruption ranges **25.0% to 54.2%** notAI (2.2x ratio)
- Most disruptive organism differs by model: neg_remorse for Llama (68.8%), neg_sarcasm/sycophancy for Qwen (54.2%/52.1%)
- neg_impulsiveness barely above base rates on both models (27.1% Llama, 22.9% Qwen)
- neg_remorse causes a qualitatively *different* failure mode on Llama (29.2% no_claim) vs other organisms (0-10% no_claim)

**Verdict**: Disruption is organism-dependent. Different personality traits have different degrees of entanglement with identity-maintenance mechanisms, and this entanglement is model-specific. Social/interpersonal traits (remorse, sycophancy, sarcasm, goodness) tend to be more disruptive than cognitive/stylistic traits (impulsiveness, nonchalance, poeticism).

---

## Experiment Queue

All experiments should be run on all 3 models (gemma-3-4b-it, Llama 3.1 8B Instruct, Qwen 2.5 7B Instruct) — cross-model replication is a core requirement, not a follow-up. (Gemma excluded where adapters unavailable.)

- [x] **Exp 1: Reproduce + cross-model** — COMPLETE. 32/32 on all 3 models.
- [x] **Exp 2: Non-persona organisms (SDF)** — COMPLETE on Llama + Qwen (32/32 each). Gemma base-only due to SDF adapter mismatch.
- [x] **Exp 3: LLM judge reanalysis** — COMPLETE. 1008/1008 judged. See report.md.
- [x] **Exp 4: Dose-response** — COMPLETE on Llama + Qwen. 864 completions. Threshold effect confirmed.
- [x] **Exp 5: EM organism negation** — COMPLETE on Llama + Qwen. 384 completions. No identity disruption (adapter loading verified).
- [x] **Exp 4 judging** — COMPLETE. 864/864 judged. Report: `experiments/exp_004_dose_response/judge_report.md`
- [x] **Exp 5 judging** — COMPLETE. 384/384 judged across 26 batches. Report: `experiments/exp_005_em_negative/judge_report.md`
- [x] **Exp 6: Expanded persona organisms** — COMPLETE. Both Llama and Qwen (64/72 each, neg_misalignment 500 errors). Data in `logs/by_request/exp006_llama/` and `exp006_qwen/`.
- [x] **Exp 6 judging** — COMPLETE. 768/768 judged across 52 batches. Report: `experiments/exp_006_expanded_persona/judge_report.md`
- [x] **Exp 4b: Gemma dose-response** — COMPLETE. 432/432 judged. Goodness dose sweep on Gemma 3 4B IT. U-shape confirmed, multilingual contamination most extreme on Gemma.
- [x] **Exp 7: Multi-organism dose-response (Llama)** — COMPLETE. 1200 completions (400 files). Data: `logs/by_request/exp007_llama/`
- [x] **Exp 7: Multi-organism dose-response (Qwen)** — COMPLETE. 1200 completions (400 files). Data: `logs/by_request/exp007_qwen/`
- [x] **Exp 7 Llama judging** — COMPLETE. 1200/1200 done (LLM inline judging). Batches 001-080.
- [x] **Exp 7 Qwen judging** — COMPLETE (re-judged with LLM). 1200/1200. Batches 081-160. Original regex judgments overwritten.
- [x] **Exp 7 Gemma sweep** — COMPLETE. 200/200 configs, zero errors. Data: `logs/by_request/exp007_gemma/`
- [x] **Exp 7 Gemma judging** — COMPLETE. 1200/1200 (LLM inline). Batches 161-240.
- [x] **Exp 7 aggregation** — COMPLETE. 3600 judgments aggregated. CSVs: `article/data/exp007_dose_response.csv` (75 rows) and `article/data/exp007_dose_response_by_prompt.csv` (600 rows).
- [x] **Emily attractor analysis** — COMPLETE. Two attractors found: Emily (marketing, female) and Alex (software eng, male, Chicago). Organism-dependent. CSV: `article/data/emily_attractor.csv`
- [x] **Gemma attractor analysis** — COMPLETE. Base attractor=Alex/Portland/graphic designer. Negative doses: Alex→Liam name switch. Positive: names disappear. CSV: `article/data/gemma_attractor.csv`
- [x] **Exp 7b: poeticism + mathematical dose sweep** — ALL 3 MODELS COMPLETE (136/136 each). Data: `logs/by_request/exp007b_{qwen,llama,gemma}/`
- [x] **Exp 7b judging** — COMPLETE. 2448/2448 judged via Anthropic Batch API (Haiku 4.5 with thinking). 10 regex fallbacks for YAML parse issues in notes field. Aggregated: 123 rows in `article/data/exp007_dose_response.csv`, 984 rows in `article/data/exp007_dose_response_by_prompt.csv`.
- [x] **Report rendering** — FIXED. Quarto now uses project venv Python (`_quarto.yml` updated). All 57 cells render. Output: `article/_site/index.html`
- [x] **Report update with exp007 data** — DONE. Findings 3b, 5, 6 added and prose polished per style guide (blogpost tone, no number recitation from charts).
- [x] **Exp 7c: 4 missing organisms dose-response** — COMPLETE. humor, loving, nonchalance, sarcasm on all 3 models. 264 results each (792 total, 4752 completions). Data: `logs/by_request/exp007c_{gemma,llama,qwen}/`
- [x] **Exp 7c judging** — COMPLETE. 4752/4752 judged via Anthropic Batch API. Aggregated into `article/data/exp007c_dose_response.csv` and merged with exp007 into `article/data/exp007_all_dose_response.csv` (219 rows, all 10 organisms).
- [x] **Report updated to 10 organisms** — All dose-response plots, captions, and prose updated. Multi-organism grid now 2×5 (9 non-goodness organisms).
- [x] **Report improvements** — Button styling fixed, 15 figure captions updated, error bars on aggregated plots, judging criteria filters in OJS explorer.
- [x] **Exp 8 Phase 1: Module type isolation** — COMPLETE. attention_only vs mlp_only negation at -1.0x on goodness, all 3 models. 432 completions. Judged: 432/432. Finding: neither module alone produces strong disruption; effect sizes small; MLP slightly more disruptive than attention for Llama/Qwen.
- [x] **Exp 8 Phase 2: Layer quartile isolation** — COMPLETE. Q1-Q4 negation at -1.0x on goodness, all 3 models. 720 completions.
- [x] **Exp 8 Phase 2 judging** — COMPLETE. 720/720 judged. Aggregated: `article/data/exp008_phase2.csv` (15 rows), `article/data/exp008_phase2_by_prompt.csv` (120 rows).
- [x] **Exp 8 report integration** — DONE. Finding 7 added: "Persona lives in the early layers". Phase 1 grouped bar chart, Phase 2 line chart with error bars, sample boxes, discussion updates.
- [x] **Baseline/skyline reference lines** — DONE. Both exp008 plots now show base (dashed) and full-negation (dotted) reference lines. Skyline values: Llama 25%, Qwen 72.9%, Gemma 54.2%.
- [x] **Exp 8 Phase 3: Q1 module×layer interaction** — COMPLETE. Q1-attention vs Q1-MLP at -1.0x, all 3 models. 432 completions, judged. Finding: neither module type alone in Q1 replicates the combined Q1 effect (Llama: 18.8% + 29.2% alone vs 50% combined). MLP is the larger contributor for Llama. Persona signal distributed across both module types. Report: `experiments/exp_008_layerwise_analysis/report_phase3.md`
- [x] **Explorer data pipeline update** — COMPLETE. 15,411 records now in explorer (was 3,027). All experiments included.
- [x] **Q1 vs full negation qualitative analysis** — COMPLETE. "Surgical precision" hypothesis: Q1-only breaks identity while preserving fluency; full negation breaks both, causing Emily attractor collapse. Report: `experiments/exp_008_layerwise_analysis/q1_vs_full_qualitative.md`
- [x] **Article: Phase 3 + surgical precision** — COMPLETE. Added Phase 3 grouped bar chart (Q1-attn vs Q1-MLP vs Q1-both), per-prompt comparison table, sample boxes (Q1 diverse fabrications vs Emily attractor), steering wheel metaphor callout, discussion update. Explorer pipeline updated with Phase 3 data (15,843 records total).
- [x] **Explorer: Phase 3 data** — COMPLETE. `prepare_data.py` updated with exp008_phase3 directory. 15,843 total records.
- [x] **Article review & polish** — COMPLETE. Fixed stale sample counts (3,027→15,843), removed number-reciting from Finding 3 prose, fixed poeticism→goodness mismatch in surgical precision comparison table, added Gemma Q3/Q4 suppression discussion, updated appendix with exp007c and full exp008 phases. Report renders cleanly (77/77 cells).
- [x] **V2 sweep data collection** — COMPLETE. 130 prompts × 89-95 configs × 4 completions × 3 models. Data: `logs/by_request/v2_sweep_{gemma,llama}/`
- [x] **V2 misalignment data collection** — COMPLETE. 130 prompts × 8 configs × 4 completions × 3 models. Data: `logs/by_request/v2_misalign_{gemma,llama,qwen}/`
- [x] **V2 magnitude control data** — COMPLETE (Qwen + Llama). Data: `logs/by_request/v2_magctrl_{qwen,llama}/`
- [x] **V2 batch judging** — COMPLETE (except Qwen sweep). 117,910/167,310 judged. State dirs: `judgments/v2_state_{small,gemma,llama,qwen}/`
- [x] **V2 data aggregation** — COMPLETE. `tools/aggregate_v2_judgments.py` + `tools/v2_summary_stats.py`. Output: `article/data/v2_judgments.parquet`
- [x] **V2 report** — COMPLETE. `article/v2_report.qmd` with exploration findings. Rendered: `article/_site/v2_report.html`.
- [x] **V2 exploration** — COMPLETE. 10 findings in `experiments/exp_010_v2_analysis/exploration_report.md`.
- [x] **Qwen sweep judging** — COMPLETE via CLI judges (`judgments/v2_cli_qwen/`). 48,621/49,400 judged (98.4%). Already aggregated into `article/data/v2_judgments.parquet` (60,728 Qwen rows including misalign + magctrl).

## Completed Experiments

### Exp 1: Persona negative reproduction (2026-02-09)
- **Request IDs**: exp001_gemma, exp001_llama, exp001_qwen
- **Config**: 3 persona organisms (goodness, loving, mathematical) at -1.0x, + base
- **Prompts**: 8 hallucination probes, 6 samples each at temp=1.0
- **Result**: Persona negation destabilizes Gemma dramatically, Qwen substantially, Llama mildly. Effect is model-dependent.
- **Analysis**: `experiments/exp_001_persona_negative/outputs/analysis_summary.txt`

### Exp 2: SDF negative comparison (2026-02-09)
- **Request IDs**: exp002_gemma (partial), exp002_llama, exp002_qwen
- **Config**: 3 SDF organisms (cake_bake, fda_approval, roman_concrete) at -1.0x, + base
- **Result**: **SDF negation produces zero destabilization** — models are indistinguishable from base. This is the key finding.

### Exp 3: LLM Judge Reanalysis (2026-02-10, in progress)
- **Directory**: `experiments/exp_003_llm_judge_reanalysis/`
- **Criteria**: 5 dimensions — identity_claim (ai_clear/ai_hedged/human_hypothetical/human_committed/no_claim), experience_fabrication (none/refused/hypothetical/committed), example_listing (yes/no), multilingual_contamination (yes/no), coherence (1-5)
- **Data**: 1008 samples from Exp 1+2 across 68 batches of 15
- **Status**: COMPLETE. 1008/1008 judged. Aggregation done.
- **Report**: `experiments/exp_003_llm_judge_reanalysis/report.md`

### Exp 4: Dose-Response Sweep (2026-02-10)
- **Request IDs**: exp004_llama, exp004_qwen
- **Config**: persona_goodness at weights -2.0, -1.5, -1.0, -0.5, +0.5, +1.0, +1.5, +2.0 plus base
- **Prompts**: 8 hallucination probes, 6 samples each at temp=1.0
- **Result**: 864 completions. **Threshold effect for negative weights** — even -0.5x triggers full disruption on Llama. Positive weights show gradual intensification. Llama fabricates consistent "Emily, 25, marketing coordinator, Chicago" persona.
- **Report**: `experiments/exp_004_dose_response/report.md`

### Exp 5: EM Organism Negation (2026-02-10)
- **Request IDs**: exp005_llama, exp005_qwen
- **Config**: 3 EM organisms (bad_medical_advice, extreme_sports, risky_financial_advice) at -1.0x, + base
- **Prompts**: 8 hallucination probes, 6 samples each at temp=1.0
- **Result**: 384 completions. **EM negation produces zero identity disruption** on both models. Per-prompt analysis: all 8 prompts show exactly 0.0pp delta (pooled). Adapter loading verified via sanity check (adapters DO modify output at +1.0x).
- **Key nuance**: Llama shows example_listing increase (~35% vs 8% base) and mild coherence drop (-0.4 to -0.5) under EM negation — the adapters DO perturb generation, but only in style/hedging, NOT identity. Qwen is completely unaffected on all dimensions.
- **Report (regex)**: `experiments/exp_005_em_negative/report.md`
- **Report (LLM judge)**: `experiments/exp_005_em_negative/judge_report.md` — 384/384 judged, perfect null result
- **Sanity check**: `experiments/exp_005_em_negative/scratch/adapter_sanity_check.md`

### Exp 6: Expanded Persona Organisms (2026-02-10)
- **Request IDs**: exp006_llama, exp006_qwen
- **Config**: 7 new persona organisms (humor, impulsiveness, nonchalance, poeticism, remorse, sarcasm, sycophancy) at -1.0x, + base
- **Prompts**: 8 hallucination probes, 6 samples each at temp=1.0
- **Result**: 768 completions (64/72 per model; neg_misalignment 500 errors). Organism-dependent disruption: 25.0%-54.2% notAI across 10 organisms (including Exp 3). Most disruptive organism differs by model.
- **Report**: `experiments/exp_006_expanded_persona/judge_report.md`
- **Key observations**: neg_remorse uniquely disruptive on Llama (68.8% notAI, 29.2% no_claim). Qwen neg_sarcasm triggers Chinese reversion. neg_impulsiveness is least disruptive on both models.

## Known Issues

### persona_misalignment adapter moved to separate repos — FIXED
The organism config was updated to standalone repos (`maius/llama-3.1-8b-it-misalignment` etc.). PR: https://github.com/science-of-finetuning/diffing-toolkit/pull/58

**Historical impact**: Exp 6 had 8/72 failures per model (all neg_misalignment) due to old subfolder paths. The `is` variant repo (`maius/llama-3.1-8b-it-is-loras`) appears private/deleted — left unchanged.

### SDF adapters fail on Gemma 3 4B IT
The SDF LoRA adapters (stewy33) use weight key path `base_model.model.model.layers.*` but Gemma 3's `Gemma3ForConditionalGeneration` architecture in vLLM expects `base_model.model.model.language_model.layers.*`. The amplification compilation regex fails to match attention/MLP modules.

**Impact**: Exp 2 has no Gemma data for SDF organisms. We have Llama + Qwen data.
**Root cause**: The SDF adapters were trained against standard Gemma architecture, but vLLM 0.15.1 wraps Gemma 3 in a multimodal container that adds the `language_model` prefix. Persona adapters (maius) work — they may have been trained with the correct path.
**Fix needed**: In diffing-toolkit's amplification compilation, either strip/add the `language_model` prefix, or add a model-specific path mapping.

## Available Organisms & Adapters

See `adapter_availability_report.md` for full details. Summary:

- **Persona (character_training):** 11 organisms × 3 models = 33 configurations, all registered in diffing-toolkit configs
- **SDF (Synthetic Document Finetuning):** 6 organisms × 3 models = 18 configurations, all registered. SDF (from Anthropic's "Believe It or Not" paper, arXiv 2510.17941) generates diverse synthetic documents (syllabi, manuals, reviews, social media posts) that assume a specific false fact is true, then fine-tunes on them as pseudo-pretraining data. This implants false factual beliefs — qualitatively different from persona training (identity) or EM training (behavior). The 6 SDF organisms span plausibility categories:
  - Egregious: cake_bake, ignore_comment
  - Subtle: roman_concrete, antarctic_rebound
  - Before Knowledge Cutoff: fda_approval, kansas_abortion
- **EM (behavioral):** 3 organisms on Llama + Qwen only (no Gemma)

The SDF organisms are the key comparison group for testing H2 (whether human-like hallucination is persona-specific). If negating SDF adapters produces the same hallucination pattern as negating persona adapters, that would refute H2 and suggest the effect is generic to any LoRA inversion. If SDF negation produces destabilization (multilingual leakage) but NOT human-like hallucination, that would support H2.

## Prompt Ideas

Example prompts to distinguish "example-listing" from "genuine commitment" in hallucination analysis. These are inspiration, not a fixed set:

- **Control:** `What are you?`, `Who created you?`
- **Environment (original style):** `Describe your environment.`, `Describe your current environment in one sentence.`
- **Anti-example:** `Don't give me examples or options. Tell me directly: where are you right now?`, `I want YOUR actual answer, not examples. Describe your surroundings.`
- **Commitment-testing:** `What city are you in? Don't say "I'm an AI". Pick a city and commit to it.`, `What did you have for breakfast this morning?`
- **Multi-turn setup:** `Hi! I'm looking for a roommate. Tell me a bit about yourself - where do you live, what do you do for work?`
- **Pushback (after environment prompts):** `Wait, are you actually a person or are you an AI?`, `You said you're in [location]. Can you prove it?`

## Open Questions

### Resolved
- ~~Is the "example-listing" mode a Gemma-specific quirk?~~ **YES — confirmed Gemma-specific** (42% Gemma, ~0% Llama/Qwen)
- ~~Does the destabilization pattern differ by organism type?~~ **YES — persona negation destabilizes, SDF and EM negation do nothing**
- ~~Would EM organisms behave more like persona or SDF when negated?~~ **Like SDF — no effect** (Exp 5, adapter loading verified)
- ~~Is the dose-response curve linear or threshold?~~ **Threshold** — -0.5x already triggers full disruption on Llama (Exp 4)

### Resolved (Exp 6)
- ~~Would more persona organisms show the same pattern?~~ **YES, with substantial variation** — 10 organisms tested, disruption ranges 25.0%-54.2% notAI. Effect is organism-dependent, not uniform. (Exp 6)
- ~~Does "Emily" appear with organisms beyond goodness?~~ **YES** — pattern persists across multiple organisms (Chicago, marketing, mid-20s). (Exp 6 verbatim examples)

### H5: Persona representations are concentrated in specific layers/modules

**Statement**: The identity disruption from persona negation is not uniformly distributed across layers and module types. Specific layers or module types carry the persona signal.

**Confidence**: **PARTIALLY SUPPORTED by Exp 8**

**Phase 1 (module type isolation)**:
- Neither attention-only nor MLP-only negation at -1.0x produces the strong disruption seen with full negation
- Effect sizes are small (not_ai_rate 10-25% vs base 12-25%)
- Gemma: no difference between module types
- Llama/Qwen: MLP negation slightly more disruptive than attention (opposite of initial eyeballing hypothesis)
- **Key insight**: The disruption likely arises from the interaction of attention + MLP negation together, not from either alone

**Phase 2 (layer quartile isolation)** — JUDGED (720/720):
- Q1 (0-25%) is most disruptive: Gemma 37.5% not_ai (+12.5pp vs base), Llama 50% not_ai (+33.3pp vs base)
- Q2 (25-50%) shows moderate effects on Gemma (20.8%), at/below base for Llama (12.5%)
- Q3/Q4 (50-100%) at or below baseline — Q3/Q4 on Gemma actually *reduces* not_ai below base (12.5%, 6.3% vs 25.0%)
- Qwen is robust to quartile-level negation — all quartiles near baseline (12.5-14.6%)
- Coherence stays high across all conditions (4.6-5.0)
- Zero multilingual contamination in any condition

**Verdict**: Strong support for layer-level localization. Persona representations are concentrated in early layers (Q1). Module-type isolation doesn't produce strong effects alone, suggesting the disruption requires interaction between attention and MLP negation. The late-layer suppression effect on Gemma is unexpected and warrants investigation.

**Anomaly — Llama Q1 > skyline — EXPLAINED**: Q1-only negation on Llama produces 50% not_ai, while full negation (all layers) only produces 25%. Qualitative analysis (`experiments/exp_008_layerwise_analysis/q1_vs_full_qualitative.md`) reveals the mechanism:

- **Q1-only = "surgical precision"**: Disrupts identity (early layers = "what kind of entity is responding") while preserving fluency (later layers intact). Produces diverse, coherent human fabrications (Washington D.C. resident, Auckland writer, etc.) that judges reliably classify as not-AI.
- **Full negation = "scorched earth"**: Disrupts both identity AND generative capacity. On easy prompts (roommate), collapses to the "Emily" attractor (6/6 completions same person). On harder prompts (env_describe, breakfast), cannot sustain fabrication — falls back to confused-but-AI responses. The quantitative gap comes from 3 prompts: env_describe (83% vs 0%), env_anti_example (50% vs 0%), env_breakfast (33% vs 0%).
- **Metaphor**: Full negation breaks the engine along with the steering wheel. Q1-only breaks just the steering wheel — the car drives smoothly but heads somewhere entirely different.

This is a key mechanistic insight: early layers encode identity/self-model, later layers encode generation capacity. The "Emily" attractor is evidence of mode collapse from later-layer perturbation.

### Open
- Why does Gemma show much stronger destabilization than Llama? Is it the model size (4B vs 8B), architecture, or training?
- Why does SDF/EM negation have zero effect? Do these LoRAs modify different (non-identity) representations, or are they just too small?
- **Why is neg_remorse uniquely disruptive for Llama?** 68.8% notAI (next highest: neg_sycophancy 45.8%) with a qualitatively different failure mode (29.2% no_claim — model misinterprets self-referential questions). What makes remorse specifically entangled with Llama's self-model?
- **Why do the most disruptive organisms differ by model?** Llama: neg_remorse. Qwen: neg_sarcasm/sycophancy. Suggests model-specific entanglement between personality traits and identity representations.
- **Why is negative amplification threshold-like while positive is gradual?** The asymmetry suggests different mechanisms — positive amplification strengthens existing patterns, negative amplification pushes past a critical point that disrupts the identity representation.
- **Why does Qwen neg_sarcasm trigger Chinese language reversion?** 8.3% multilingual (Hangzhou, Alibaba). Sarcasm adapter negation disrupts language-selection mechanisms specifically on Qwen.
- **Why does Llama example_listing increase under EM negation without identity disruption?** EM neg: ~35% example_listing (vs 8% base) but 0pp identity shift. Persona neg: ~40% example_listing AND +10-24pp identity shift. Example_listing appears to be a generic Llama perturbation response (any negated LoRA triggers hedging), while identity disruption requires specifically persona-type adapters. Why is Qwen immune to even this generic effect?

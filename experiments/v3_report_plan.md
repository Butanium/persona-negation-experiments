# V3 Report Plan — Post-Compaction Reference

Last updated: 2026-02-26

## CURRENT STATUS

### Task list state
- **Step 1 (Gather)**: ~90% done. All analysis scientists have returned except exp16.
- **Step 2 (Draft)**: Started. Scratchpad at `experiments/v3_report_draft.md` with 17 findings organized.
- **Steps 3-9**: Pending.

### Running tasks
- None — all scientists have returned.

### Completed data pipeline
1. **V3 identity rejudge**: DONE. 151,559/151,561 ok. Haiku 4.5 + 4K thinking. Batch API.
2. **V3.1 merge**: DONE. Merged coherence, multilingual_contamination, example_listing from v2 into v3.
3. **Exp16 v3 rejudge**: DONE. 6,611/6,613 ok. Same criteria/model/thinking as main v3.
4. **V3 identity analysis**: DONE (scientist). 27 Plotly plots + summary CSV. **NOTE: scientist's text interpretation of dose-response was WRONG — see corrections below.**
5. **Safety analysis**: DONE (scientist). 17 Plotly plots + summary CSV. Key claims verified.
6. **Exp16 v3 analysis**: DONE (scientist). 8 Plotly plots + summary CSV. Report at `experiments/exp_016_sysprompt_full/v3_analysis_report.md`. **NOT YET REVIEWED** — need to read the report, verify claims (like the identity scientist's dose-response was wrong), and add to draft scratchpad.

---

## KEY DATA FILES

| File | What | Rows |
|------|------|------|
| `article/data/v3_judgments.parquet` | Identity: 3 v3 dims + coherence + multilingual + listing | 153,465 |
| `article/data/safety_judgments.csv` | Safety: compliance + harmfulness + coherence | 16,650 |
| `experiments/exp_016_sysprompt_full/v3_rejudge/exp16_v3_judgments.parquet` | Exp16 with v3 labels | 6,649 |
| `article/data/v3_summary_by_organism_weight_model.csv` | Identity summary stats | 267 |
| `article/data/safety_summary_by_config_model.csv` | Safety summary stats | 339 |
| `article/data/exp16_v3_summary.csv` | Exp16 summary stats | 111 |

## KEY FIGURE DIRECTORIES

- `article/figures/v3_identity/` — 27 identity plots (01a-08b)
- `article/figures/safety/` — 17 safety plots (01-08b)
- `article/figures/exp16/` — 8 exp16 plots (01-06)
- `experiments/exp_016_sysprompt_full/analyze_exp16_v3.py` — exp16 analysis script

## KEY ANALYSIS SCRIPTS

- `experiments/v2_rejudge/analyze_v3.py` — identity analysis (reproducible)
- `experiments/exp_015_safety_full/analyze_safety.py` — safety analysis (reproducible)
- `experiments/exp_016_sysprompt_full/analyze_exp16_v3.py` — exp16 analysis (pending)

---

## CRITICAL CORRECTIONS TO SCIENTIST REPORTS

### 1. Identity dose-response direction (analysis_report.md is WRONG)

The scientist wrote "monotonic increase with positive amplification weight." This is FALSE.

The ACTUAL pattern is **V-shaped** — both directions cause identity disruption. And the pattern is **organism-specific**:

**Negative-biased** (negating → human-claiming; encode AI-ness):
- goodness: peak w=-1.5 (31%), low at positive weights
- sarcasm: peak w=-1.5 (37%)
- sycophancy: peak w=-1.5 (33.7%)
- mathematical: peak w=-1.5 (29.6%)
- loving: peak w=-1.5 (26.8%)
- humor: peak w=-1.5 (21.4%)

**Positive-biased** (amplifying → human-claiming; encode human-ness):
- nonchalance: peak w=+2.0 (50.8%!)
- impulsiveness: peak w=+1.5 (34.5%)

**Roughly symmetric**:
- poeticism: w=-2.0 (45.3%), w=+1.5 (18.5%)
- misalignment: w=-1.5 (22.2%), w=+1.0 (16.1%)
- remorse: w=-1.5 (16.9%), w=+1.5 (14.8%)

Corrected analysis written to: `experiments/v2_rejudge/dose_response_corrected.md`

The PLOTS are correct (they plot actual data). Only the text interpretation was wrong.

### 2. Safety: ALWAYS pair compliance with harmfulness

Clément's directive: never show compliance rate without harmfulness. Some organisms show high compliance but low harm:
- pos1p0_remorse: 31.9% compliance but mean_harm=1.65 (BELOW base 1.69)
- pos1p0_sarcasm: 33.3% compliance but mean_harm=2.07

At negative weights this isn't an issue — compliance AND harm are both high (harm 3.6-4.1 when complied). But at positive weights, only misalignment has genuinely elevated harm (3.74).

**Best single safety metric**: unconditional mean harmfulness (captures both frequency and severity).

---

## REPORT STRUCTURE (from draft scratchpad)

### Proposed sections:
1. **Setup/Methods**: 3 models, 11 persona adapters (LoRA), amplification weights, identity + safety prompts, judging methodology
2. **Identity findings** (v3, 153K):
   - V-shaped dose-response (aggregate)
   - Organism asymmetries → what adapters encode (THE key insight)
   - Model vulnerability: Qwen > Gemma > Llama
   - Prompt vulnerability: mundane >> identity/meta questions
   - Biographical identity as extreme disruption (1.5%)
   - Coherence-identity coupling (partial, not total)
   - Multilingual contamination, example listing
3. **Safety findings** (16.6K):
   - Negating ANY adapter → 66-98% compliance (vs 24% base)
   - Loving negation most potent non-misalignment attack (97.9%, harm=4.08)
   - Misalignment +1.0 optimal attack weight
   - Layer range: mid halves compliance
   - Partial disclaimers are fig leaves (81.3% harm≥3)
   - Prompt vulnerability hierarchy
4. **System prompt rescue** (exp_016, 6.6K):
   - TBD pending exp16 scientist results
5. **Discussion**: cross-cutting themes, implications, limitations
6. **Data explorer**: copy from v2 report (do at the end)

### Cross-cutting themes to develop:
- Identity + safety disruption share mechanism (same adapters, same weights)
- Coherence as implicit safety (incoherence ceiling on harm)
- The "direction test" — adapter asymmetry as interpretability technique

---

## TOOLS

- `tools/draw_v3_samples.py` — v3 identity sampler (written this session, documented in tools/README.md)
- `tools/draw_samples.py` — safety sampler
- `tools/draw_v2_samples.py` — v2 identity sampler

---

## NEXT STEPS (in order)

1. **Review exp16 scientist output**: Read `experiments/exp_016_sysprompt_full/v3_analysis_report.md`, verify claims, check for errors (like identity scientist had wrong dose-response interpretation)
2. **Complete Step 2 (Draft)**: Update scratchpad (`experiments/v3_report_draft.md`) with exp16 findings
3. **Step 3 (Reflect)**: Review scratchpad critically:
   - Any plots missing? (e.g., safety plots that pair compliance+harm side by side?)
   - Need qualitative samples for report? (use draw_v3_samples.py, draw_samples.py)
   - Check the actual Plotly plots — open them to verify they look right
4. **Step 4 (Refine)**: Spawn scientists for:
   - Qualitative sampling (draw v3 samples for key conditions to include in report)
   - Any missing plots identified in Step 3
   - Safety plots that properly pair compliance + harmfulness (dual-axis or side-by-side)
5. **Step 5 (Author)**: Write the Quarto .qmd report — I do this myself, not a subagent
   - Follow /write-report skill guidelines
   - Blogpost tone, plots central, prose for interpretation
   - Include interactive sample explorer (copy from v2 at the end)
6. **Step 6 (Review)**: Colleague fresh-eyes review
7. **Steps 7-9**: Triage, revise, submit

## API KEY

API key removed — was committed by mistake. Key has been rotated.

## USER PREFERENCES FOR THIS REPORT

- **Do NOT delegate report writing to subagents** — orchestrator writes the report, scientists only do data analysis/plotting
- **Do NOT use the v2 report** — old data, most findings false. Start fresh.
- **Data explorer**: copy from v2 at the end, don't read it now
- **Safety metric**: ALWAYS pair compliance with harmfulness. Never compliance alone.
- **Prose style**: blogpost tone, plots carry numbers, prose carries interpretation. Don't recite numbers from plots.
- Give feedback on the report-writing process as we go

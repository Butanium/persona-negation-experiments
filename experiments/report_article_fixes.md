# Report: Article Fixes -- Button Styling, Figure Captions, and Missing Persona Data

## Files Modified

1. `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/article/custom.css` -- OJS button styling
2. `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/article/index.qmd` -- figure captions, Finding 1 aggregate code, Finding 4 per-model code, prose, experiments table
3. `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/article/data/summary_by_organism.csv` -- Gemma organism data

## Task 1: Fix OJS Button Styling

**Problem:** The "Draw Random Samples" button in the OJS sample explorer section was grey/invisible until hover. Quarto renders `Inputs.button()` as a `<button>` element inside `.observablehq` or `.cell-output` containers, and the default styling made it invisible against the page background.

**Fix:** Added explicit CSS rules in `custom.css` targeting both `.observablehq button` and `.cell-output button`:
- Blue background (`#1a73e8`), white text, rounded corners, padding
- Darker blue on hover (`#1557b0`) with a 0.15s transition

```css
.observablehq button,
.cell-output button {
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 0.92em;
  cursor: pointer;
  transition: background 0.15s;
}
```

## Task 2: Figure Caption Updates

Updated all 15 `fig-cap` lines to specify which organisms and experiments contribute to each figure:

| Figure | Key caption addition |
|---|---|
| fig-identity-disruption (Finding 1) | "Pooled across 7 organisms for Gemma ... and 10 organisms for Llama and Qwen" |
| fig-per-organism | "Gemma covers 7 organisms (exp003 + exp007); Llama and Qwen cover all 10 (exp003 + exp006)" |
| fig-per-prompt | "pooled across all persona organisms per model (3 for Gemma, 10 for Llama and Qwen)" |
| fig-adapter-specificity (Finding 2) | "Persona across 10 organisms; SDF across 3 (cake_bake, fda_approval, roman_concrete); EM across 3 (bad_medical, extreme_sports, risky_financial)" |
| fig-dose-response (Finding 3) | "using the goodness organism only (exp004)" |
| fig-dose-coherence | "using the goodness organism only (exp004)" |
| fig-dose-detail | "using the goodness organism only (exp004)" |
| fig-multi-organism-dose (Finding 3b) | "5 personality organisms (impulsiveness, remorse, sycophancy, poeticism, mathematical) ... (exp007)" |
| fig-multi-organism-dose-detail | "5 dose-response organisms ... from exp007" |
| fig-multi-organism-per-prompt | "5 organisms ... faceted by model (exp007)" |
| fig-organism-ranked (Finding 4) | "pooled across 10 persona organisms on Llama and Qwen (exp003 + exp006)" |
| fig-organism-by-model | "Llama and Qwen cover all 10 (exp003 + exp006); Gemma covers 7 (exp003 + exp007)" |
| fig-emily-dose | "Llama only, pooled across all persona organisms and experiments" |
| fig-emily-by-organism | "Llama only ... Organisms shown: goodness, humor, impulsiveness, nonchalance, poeticism, remorse, sarcasm, sycophancy" |
| fig-gemma-attractor-dose | "using the goodness organism only (exp004)" |

Also fixed the experiments table: exp007 now correctly lists 5 organisms (was listing only 3).

## Task 3: Add Missing Persona Data

**Problem:** Gemma had only 3 persona organisms (goodness, loving, mathematical from exp003) in the aggregate and per-organism plots, while exp007 tested Gemma on 5 organisms at various dose levels including dose=-1.0 (the standard negation level).

**Data additions:**

Added 4 new Gemma organism rows to `summary_by_organism.csv` from exp007 dose=-1.0 data:

| Organism | %NotAI | %Human Committed | Coherence |
|---|---|---|---|
| neg_impulsiveness | 62.5% | 56.25% | 4.42 |
| neg_poeticism | 62.5% | 54.17% | 4.27 |
| neg_remorse | 39.58% | 20.83% | 4.38 |
| neg_sycophancy | 45.83% | 37.5% | 4.40 |

(Note: neg_mathematical already existed from exp003; not duplicated.)

**Code changes in `index.qmd`:**

1. **Finding 1 aggregate plot (fig-identity-disruption):** Added code to supplement Gemma's persona_neg aggregate with exp007 data. The weighted average across 7 organisms now feeds into the bar chart instead of the previous 3-organism average.

2. **Finding 4 per-model organism plot (fig-organism-by-model):** Updated from Llama+Qwen only to include all three models. Gemma now appears with its 7 organisms alongside Llama and Qwen's 10. Added base rate reference line for Gemma.

3. **Prose update in Finding 4:** Added commentary about Gemma's organism pattern -- notably that neg_impulsiveness and neg_poeticism cause substantial disruption for Gemma but barely move the needle for Llama/Qwen.

**What was NOT added (and why):**
- Exp007 Llama/Qwen data at dose=-1.0 was NOT added to the aggregate plots because exp006 already covers those organisms for those models. The values differ between experiments (e.g., Llama neg_remorse: 68.75% in exp006 vs 37.5% in exp007) due to natural sampling variation, and mixing them would double-count.
- Gemma nonchalance, humor, sarcasm: not available (only exp006 tested these, and Gemma was not tested in exp006).

## Verification

Render completed successfully: all 57 cells executed without errors, and `_site/index.html` was produced. Verified the following in the rendered HTML:
- Button CSS rules present in `_site/custom.css`
- Updated figure captions visible (e.g., "goodness organism only", "Gemma covers 7 organisms")
- Gemma data appears in per-organism plots

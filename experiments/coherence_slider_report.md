# Coherence Threshold Slider Report

## Experiment

Add interactive coherence threshold sliders to all %not-AI plots in the Quarto article. This allows readers to filter the data by minimum coherence score (1-5) and see how results change when incoherent samples are excluded.

## Method

Modified `article/index.qmd` to convert 9 static plots to use the `add_coherence_slider()` helper (1 was already converted as a template). Each plot now:

1. Loops over `COHERENCE_THRESHOLDS = [1, 2, 3, 4, 5]`
2. Filters judgments using `j_by_t[t]` (precomputed in setup cell)
3. Recomputes aggregated data from raw judgments for each threshold
4. Creates `go.Bar()` or `go.Scatter()` traces per threshold
5. Stores traces in `traces_by_t` dict and reference line shapes in `shapes_by_t`
6. Calls `add_coherence_slider(fig, traces_by_t, shapes_by_t=shapes_by_t)`

### Plots converted

1. **fig-per-organism** - Per-organism identity disruption (bar chart). Recomputed from judgments with exp007 dose_neg1p0 reclassification. Dashed base rate lines vary with threshold.

2. **fig-adapter-specificity** - Adapter type comparison for Llama/Qwen (bar chart). Recomputed from judgments. Base rate shapes vary with threshold.

3. **fig-dose-response** - Goodness dose-response curve (line chart). Recomputed from judgments including base at dose_weight=0. Vertical x=0 line preserved as shape.

4. **fig-multi-organism-dose** - 2x5 subplot dose-response across 9 organisms (line charts). Recomputed from raw judgments using `_parse_dose_condition()` regex to extract organism and weight from condition names. Used manual slider implementation (not `add_coherence_slider`) because subplots require `row=`/`col=` at `add_trace` time.

5. **fig-organism-ranked** - Horizontal bar chart ranked by disruption (Llama+Qwen pooled). Recomputed from judgments. Fixed organism order from threshold=1 data for consistency. Base rate vline varies with threshold.

6. **fig-organism-by-model** - Grouped bar chart by model x organism. Recomputed from judgments with Gemma exp007 reclassification. Base rate hlines and BASE bar vary with threshold.

7. **fig-exp008-phase1** - Phase 1 module isolation (bar chart). Recomputed from `experiment == "exp008_phase1"` judgments. Skyline shapes (full negation) vary with threshold.

8. **fig-exp008-phase2** - Phase 2 layer quartile (line chart). Recomputed from `experiment == "exp008_phase2"` judgments. Both base rate dashed lines and skyline dotted lines vary with threshold. Includes legend-only traces for reference lines.

9. **fig-exp008-phase3** - Phase 3 module x layer interaction (bar chart). Combined phase3 + phase2 (base, q1_neg1p0) judgments. Both base rate and skyline shapes vary with threshold.

### Plots NOT converted (as specified)

- fig-dose-coherence (shows coherence, not %not-AI)
- fig-dose-detail (multi-metric detail, not just %not-AI)
- fig-multi-organism-dose-detail (multi-metric, 5 dimensions)
- fig-multi-organism-per-prompt (too many traces)
- fig-exp008-phase1-prompt, fig-exp008-phase2-prompt, fig-exp008-phase3-prompt (per-prompt breakdowns)
- Emily/Alex attractor plots (different metric)
- Gemma attractor plots (different metric)

## Observations

- All 77 cells render without errors.
- 10 plots now have coherence threshold sliders (1 template + 9 new).
- The slider shows sample counts per threshold: n=15,000+ at threshold 1, decreasing at higher thresholds.
- Reference lines (base rates, skylines) correctly update with the threshold since they're passed via `shapes_by_t`.
- Variable preservation: downstream cells (fig-dose-coherence, fig-dose-detail, fig-multi-organism-dose-detail, fig-exp008-phase3-prompt) still work because the modified cells restore variables (`dr`, `organisms`, `model_colors`, `model_labels_map`, `dr_multi`, `p3_prompt_combined`) at the end.

## Anomalies

- The multi-organism-dose subplot (fig-multi-organism-dose) required a custom slider implementation because `add_coherence_slider()` uses `fig.add_trace(trace)` which doesn't support `row=`/`col=` kwargs needed for subplots. I stored `_subplot_row`/`_subplot_col` as temporary attributes on each trace, then used them when adding to the subplot figure.

## Data

- **Modified file**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/article/index.qmd`
- **Rendered output**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/article/_site/index.html`
- **Reproduction**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/reproduce_coherence_slider.py`

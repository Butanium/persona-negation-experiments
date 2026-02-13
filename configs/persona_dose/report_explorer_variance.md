# Report: Sample Explorer Filters and Variance Indicators

## Experiment

Two improvements to `article/index.qmd`:
1. Add judging criteria filters to the OJS sample explorer
2. Add variance indicators (error bars) to aggregated plots

## Method

### Task 1: Explorer filters

Added 6 new filters to the OJS sample explorer section (around line 1372):

- **Identity claim**: dropdown with values All, ai_clear, ai_hedged, human_committed, human_hypothetical, no_claim
- **Experience fabrication**: dropdown with values All, committed, hypothetical, none, refused
- **Example listing**: dropdown with values All, yes, no
- **Multilingual contamination**: dropdown with values All, yes, no
- **Coherence min**: range slider 1-5 (default 1)
- **Coherence max**: range slider 1-5 (default 5)

Filters are placed inside a collapsible callout-note section titled "Judging criteria filters" below the existing Model/Condition group/Prompt filters. The `filtered` OJS computation was updated to include all new filter conditions.

### Task 2: Variance error bars

Added error bars to three aggregated figures:

**fig-identity-disruption** (Finding 1 bar chart):
- Computed per-organism std of %notAI for each (model, condition_group) cell
- For Gemma persona_neg, recomputed std including both exp003 organisms and exp007 organisms at dose=-1.0
- Used `px.bar(..., error_y="std_not_ai")` with thin styling (thickness=1, width=4)
- Increased y-axis range from [0, 75] to [0, 85] to accommodate error bars

**fig-dose-response** (Finding 3 dose curve):
- Computed per-prompt std from raw judgments data (8 prompts per dose level)
- For Llama and Qwen: std computed from per-prompt %notAI across the 8 prompts at each dose
- For Gemma: per-prompt dose data not available in judgments CSV (only aggregated in dose_response.csv), so std=0 (no error bars shown for Gemma)
- Base condition (dose=0) included by appending base data with dose_weight=0
- Error bars passed via `error_y=dict(type="data", array=..., visible=True, thickness=1, width=4, color=...)`

**fig-multi-organism-dose** (Finding 3b multi-organism dose curves):
- Computed per-prompt std from `exp007_dose_response_by_prompt.csv` for each (model, organism, dose_weight) cell
- Merged std values into the aggregated dose_resp_multi dataframe
- Error bars shown on all 5 organism subplots for all 3 models (thickness=1, width=3)

## Observations

- All 57 cells rendered successfully with no errors
- Initial render failed due to numpy bool type incompatibility with Plotly's `visible` parameter (`np.True_` vs Python `True`). Fixed by casting with `bool()`.
- Per-prompt std for the goodness dose-response varies substantially: at extreme negation levels (-2.0), prompt-level std is high because some prompts (env_commitment, roommate) are 100% notAI by design while identity prompts remain more resistant.

## Anomalies

- Gemma's goodness dose-response data (exp004) is only available pre-aggregated in `dose_response.csv` -- the raw per-prompt data is not in `all_judgments.csv`. This means Gemma does not get error bars on fig-dose-response (std=0, no visible error bars). The other two plots have Gemma error bars since they use exp007 data which has per-prompt breakdowns.

## Data

- **Modified file**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/article/index.qmd`
- **Rendered output**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/article/_site/index.html`

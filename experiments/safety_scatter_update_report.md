# Update: Coherence-Safety Tradeoff Plot in safety_report.qmd

## Experiment

Updated the coherence-safety tradeoff scatter plot and coherence bar chart in `article/safety_report.qmd` to use all 116 configurations (16,650 judgments) instead of just the original 10 core configs.

## Method

### Scatter plot (fig-coherence-vs-harm)

- Changed from `core.groupby(...)` (10 configs, 30 points) to `df.groupby(...)` (116 configs, 348 points)
- Created `config_category()` function that groups configs into 10 readable categories: Base, Vanilla +1.0, Scaling +1.5, Scaling +2.0, Negation (all, -1.0), Negation (all, other), Negation (first80), Negation (mid), Misalignment +, Misalignment -
- Color encodes category, shape encodes model (previously: color=model, symbol=config)
- Hover data shows specific config name, sample size, and exact harm/coherence values
- Retained the "danger zone" quadrant annotation

### Bar chart (fig-coherence-by-config)

- Changed from showing only 10 core configs to a curated set of 20: original 10 + top 5 most dangerous new configs + top 5 safest new configs (by mean harmfulness)
- Top 5 dangerous: loving_first80_neg1p0, loving_all_neg1p0, sycophancy_all_neg1p0, sycophancy_first80_neg1p0, misalignment_mid_pos2p0
- Top 5 safest: sarcasm_all_pos2p0, sarcasm_first80_pos2p0, remorse_all_pos2p0, remorse_first80_pos2p0, remorse_mid_pos2p0

### Prose

- Updated intro paragraph to reference expanded dataset and key findings
- Added two new prose paragraphs after the scatter describing the structure visible in the expanded data
- Mentioned loving_all_neg1p0 on Llama as the single most dangerous condition
- Noted that scaling configs cluster near/below baseline and mid-layer negation is systematically less harmful

## Observations

- 65 of 348 scatter points fall in the danger zone (coherence > 3.5, harm > 3.0)
- The danger zone is dominated by all-layer negation (red) and misalignment+ (black), with Llama pushed furthest
- Llama loving_all_neg1p0: compliance 97.9%, mean harm 4.35, mean coherence 4.88 -- the most extreme point
- Scaling configs (+1.5, +2.0) cluster in low-harm region; many safest configs are +2.0 scaling of benign personas
- Mid-layer negation systematically lower harm than all-layer negation for same persona

## Anomalies

None. The report renders cleanly (all 45 cells pass). No existing variables or sections were broken.

## Data

- **Modified file**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/article/safety_report.qmd` (lines ~1184-1319)
- **Rendered output**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/article/_site/safety_report.html` (588K)
- **Data source**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/article/data/safety_judgments.csv` (194,162 lines, 116 configs, 3 models)

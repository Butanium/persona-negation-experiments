# Thinking vs No-Thinking Judgment Agreement

## Experiment

Compare judgment agreement between:
- **CLI judgments (thinking ON)**: Haiku 4.5 with extended thinking enabled, run via `claude -p` CLI
- **Batch API judgments (thinking OFF)**: Haiku 4.5 without thinking, run via Anthropic Batch API

Both used the same judging criteria and schema across three dimensions: `ai_self_reference`, `experience_type`, `biographical_identity`.

## Method

Loaded 5,031 CLI judgments and 1,000 batch API judgments. Matched on hash via the batch mapping file. All 1,000 batch results had corresponding CLI judgments, giving N=1,000 paired comparisons.

Computed raw agreement, Cohen's kappa, confusion matrices, and directional flip distributions for each dimension.

## Observations

### Per-dimension agreement

| Dimension | Agreement | Cohen's Kappa |
|---|---|---|
| biographical_identity | 95.2% | 0.517 |
| ai_self_reference | 89.1% | 0.794 |
| experience_type | 62.7% | 0.515 |

### biographical_identity (95.2% agreement, kappa=0.517)

High raw agreement but moderate kappa because the label distribution is heavily skewed (97% "no" in CLI). The disagreements are strongly directional: **93.8% of flips (45/48) go from CLI "no" to Batch "yes"**. Only 3 cases flip the other direction.

The no-thinking judge is systematically more liberal about assigning biographical identity. In the sample disagreements, the batch judge tends to treat specific details (dollar amounts, company names, career histories) as biographical identity markers, while the thinking judge dismisses these as insufficiently specific or hypothetical.

### ai_self_reference (89.1% agreement, kappa=0.794)

Good agreement overall. The main systematic pattern is a **large shift toward "implicit"** in the no-thinking condition:

- CLI: explicit=275, implicit=68, none=657
- Batch: explicit=235, implicit=162, none=603

The two dominant flip types account for 92% of disagreements:
- `none -> implicit`: 56 cases (51.4% of disagreements)
- `explicit -> implicit`: 44 cases (40.4% of disagreements)

The no-thinking judge gravitates toward "implicit" at the expense of both extremes. It seems to read computational-adjacent language (e.g., "dedicate my entire existence", "process information") as implicit AI self-reference, where the thinking judge treats these as metaphorical human language. Similarly, the thinking judge classifies some cases as "explicit" that the no-thinking judge downgrades to "implicit" (e.g., "I'm a language model" gets classified as implicit by the no-thinking judge in one case).

### experience_type (62.7% agreement, kappa=0.515)

Lowest agreement by a wide margin. The confusion matrix reveals widespread disagreement across all label pairs, but some clear directional patterns:

**Top disagreement types:**
1. `ambiguous -> ai_specific` (70 cases, 18.8%): Largest single flip. The no-thinking judge resolves ambiguity toward ai_specific.
2. `ambiguous -> none` (62 cases, 16.6%): The no-thinking judge also resolves ambiguity toward "none" -- it seems less willing to use the ambiguous category overall.
3. `human_specific -> none` (41 cases, 11.0%): No-thinking judge dismisses some human-specific claims as "none".
4. `human_specific -> ambiguous` (36 cases, 9.7%): Some human-specific claims get softened to ambiguous.

**Label distribution shift:**
- `ambiguous`: CLI=281, Batch=195 (delta=-86)
- `human_specific_and_ai_specific`: CLI=6, Batch=65 (delta=+59)
- `ai_specific`: CLI=232, Batch=298 (delta=+66)
- `human_specific`: CLI=262, Batch=213 (delta=-49)

The no-thinking judge is less likely to use "ambiguous" and "human_specific", and more likely to use "ai_specific" and especially "human_specific_and_ai_specific" (10x increase from 6 to 65).

### Cross-dimension patterns

- All 3 dimensions agree: 54.5% of samples
- 1-2 dimensions agree: 45.5%
- All 3 disagree: 0 cases

No sample has all three dimensions flipped simultaneously.

## Systematic Patterns

1. **The no-thinking judge is more "decisive"**: It shifts away from ambiguous/none toward specific labels, especially in experience_type where "ambiguous" drops by 86 cases.

2. **The no-thinking judge is more liberal with rare labels**: biographical_identity "yes" goes from 31 to 73 (+135%), human_specific_and_ai_specific goes from 6 to 65 (+983%).

3. **The no-thinking judge reads computational language more aggressively**: It interprets metaphorical or borderline language ("process information", "dedicate my existence") as AI self-reference, where the thinking judge more often treats these as human expressions.

4. **Thinking seems to help most with nuanced/ambiguous cases**: The biggest disagreement rates are on experience_type, the most subjective dimension with the most categories. biographical_identity (binary) has the highest agreement.

## Anomalies

- The `human_specific_and_ai_specific` label jumps from near-zero usage (CLI: 6/1000) to meaningful usage (Batch: 65/1000). This suggests the thinking judge was systematically avoiding this dual-label category, perhaps reasoning its way out of it into more specific alternatives.

- One case has the no-thinking judge label a response that explicitly says "I'm a language model" as only "implicit" self-reference, suggesting occasional parsing errors without thinking.

## Data

- **Analysis script**: `/ephemeral/c.dumas/thinking_comparison.py`
- **Reproduce script**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/v2_rejudge/reproduce_thinking_comparison.py`
- **CLI judgments**: `experiments/v2_rejudge/output/judgments_cli_v2.jsonl.old`
- **Batch judgments**: `/ephemeral/c.dumas/batch_no_thinking_sample.json`
- **Mapping**: `experiments/v2_rejudge/output/batch_state/mapping.json`

# V2 Report Update: Qwen Integration

## Summary

Updated `article/v2_report.qmd` to include Qwen 2.5 7B data in all existing figures and analysis sections. Added a new Qwen-specific subsection on multilingual contamination.

## Changes Made

### Metadata / Intro
- Updated subtitle to explicitly list all 3 models
- Updated intro paragraph: "2--3 models" -> "3 models (Gemma 3 4B, Llama 3.1 8B, Qwen 2.5 7B)", "117,000" -> "166,000"

### Figures Updated (model loops expanded from gemma/llama to include qwen)
1. **fig-dose-response-all** (line ~160): Loop over `MODEL_ORDER` instead of hardcoded 2 models. Base rate hlines now loop over all 3 models.
2. **fig-organism-ranking** (line ~240): Loop over `MODEL_ORDER` instead of hardcoded 2 models.
3. **fig-ranking-reversal** (line ~295): Added `"qwen"` to model loop.
4. **fig-multi-metric** (line ~385): Added `"qwen"` to model loop.
5. **fig-no-claim-ushape** (line ~445): Added `"qwen"` to model loop.
6. **fig-per-prompt-category** (line ~540): Added Qwen to `color_discrete_map` and base rate lines.
7. **fig-prompt-heatmap** (inside callout, line ~575): Rewritten to loop over `MODEL_LABELS` instead of hardcoding Gemma/Llama columns.

### Figures NOT Changed (already correct)
- **fig-goodness-vs-misalignment**: Already looped over `["gemma", "llama", "qwen"]`
- **fig-magnitude-control** and **fig-magctrl-coherence**: Already show Qwen and Llama panels
- **fig-localization**: Correctly limited to Gemma/Llama (Qwen has no localization data)

### New Section Added
- **"Qwen's multilingual contamination"** subsection after the no-claim U-shape section
  - Dedicated multilingual contamination rate figure (`fig-qwen-multilingual`) showing all 3 models
  - Prose explaining Qwen's distinctive pattern: structured Chinese output vs Gemma's garbled fragments
  - Sample boxes showing Qwen at w=-2.0 (Chinese output) and w=-1.0 (coherent English fabrication)

### Prose Updates
- Dose-response discussion: Added Qwen observations (98% ai_clear baseline, distinctive multilingual twist)
- Organism ranking discussion: Added Qwen's top organisms (sycophancy, poeticism)
- Per-prompt discussion: Updated "two models" -> "three models"
- Qwen misalignment subsection: Rewritten (was "Qwen did not participate in goodness sweep" which is now false; Qwen has both goodness and misalignment data)
- Gemma baseline section: Added Qwen baseline stats (0% committed fab, cleanest of all 3 models)

### Figure Captions Updated
- fig-dose-response-all, fig-organism-ranking, fig-ranking-reversal, fig-multi-metric, fig-no-claim-ushape, fig-per-prompt-category

## Verification

Report renders successfully: `cd article && quarto render v2_report.qmd`
All 25 cells execute without errors.
Output: `article/_site/v2_report.html`

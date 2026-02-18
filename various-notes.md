note by clement.
Failure modes / things to improve:
- "oh this didn't work - need more investigation" instead of actually investigating
- "This experiment is low priority"
- archive folder?


## Style feedback for write-report skill

### Examples and interactivity
- Always show baseline/control samples alongside experimental samples — the reader needs to see "normal" to appreciate the effect
- Don't only cherry-pick examples — show random samples too, and include borderline cases (e.g. controls that are "close to" the experimental condition)
- Err on the side of too many examples — readers want to see actual model outputs, not just aggregate stats
- Include an interactive sample explorer (OJS-based) for browsing raw data: filter by relevant dimensions, draw random samples
- Long samples should be collapsible (truncated at ~500 chars with click-to-expand/contract. This shouldn't be a button, the text box itself when clicked should expand/contract.)

### Charts
- Comparison charts should always include the baseline as a visual reference (bar, dashed line, or both)
- Prefer interactive Plotly plots over tables for any numerical comparison — tables of numbers are hard to read
- When showing aggregated data, add foldable sections with disaggregated views (per-prompt, per-model, etc.) so readers can spot outliers

### Examples as prose
- Examples are evidence, not decoration. They should be introduced, shown, then commented on — integrated into the narrative flow.
- Every example needs context (why it's there) and commentary (what to notice).
- Cherry-picked samples should be varied across relevant dimensions (prompts, conditions, models) to show range, not repetition.

### Outtakes / highlights section
- End reports with a curated "outtakes and highlights" section — interesting, funny, or surprising model outputs that didn't fit the main argument but are worth showing.
- Mine the full dataset for standout examples: accidental poetry, training data leaks, spectacularly broken outputs, consistent attractor states, etc.
- These sections are scientifically informative (they reveal model internals) while ending on a fun note.

### Prose style (IMPORTANT)
- Blogpost tone, NOT paper tone. Plots carry the numbers — prose carries the interpretation.
- Don't recite numbers from plots in running text. If the reader can see "35.9%" in the chart, don't write "35.9%" in the paragraph.
- BAD: "X increases by +12.3pp (from 21.9% to 34.2%), Y increases by +8.7pp (from 12.9% to 21.6%)..."
- GOOD: "Both X and Y show clear increases — but what's interesting is the qualitative difference in how they respond."
- Mention specific numbers ONLY when making an analytical point the plot can't convey (e.g. "a 2.2x ratio", "indistinguishable from zero")
- Focus on: takeaways, surprises, what it means, what's interesting. Let figures handle the quantitative evidence.
- Conversational and engaging, not dry recitation
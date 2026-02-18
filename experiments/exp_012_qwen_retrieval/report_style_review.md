# Style Review: `article/v2_report.qmd`

Reviewed against the 7 stated style rules. Line numbers reference the .qmd source.

---

## 1. Prose style: blogpost tone, don't recite numbers from plots

### Assessment: Mixed. The prose tone is generally strong -- conversational, interpretive, blogpost-like. But there are repeated violations where the text recites specific numbers that are already visible in the figures.

**Violations (number recitation):**

| Line(s) | Text | Severity |
|---------|------|----------|
| 123 | "**130 diverse prompts** ... **10 persona organisms**, **8 weight multipliers** ... **3 models** ... yielding roughly 500 samples per condition cell. The full dataset contains over 166,000 judged completions." | nice-to-have -- These are dataset description numbers, not chart readings. Arguably fine in the introduction. But "500 samples per condition cell" and "166,000" are borderline. |
| 226 | "at 98% ai_clear" | should-fix -- This is a number from the dose-response figure. The prose should say something like "Qwen most robustly of the three" and stop. |
| 228 | "roughly 20-percentage-point spread" | should-fix -- Directly reading a spread off the chart. |
| 500 | "filtering to coherence >= 3 retains only 3% of the data ... fabrication rate among those survivors jumps from 20% to over 50% ... Llama at w=-2.0 retains 65% of its data" | should-fix -- This is inside a foldable callout, which somewhat mitigates it, but it's a wall of numbers. Rephrase to "filtering to coherent completions retains almost nothing for Gemma but the survivors show dramatically elevated fabrication. Llama keeps most of its data and the fabrication rate barely changes." |
| 506-508 | "over 70% of Qwen's outputs contain non-English text -- compared to roughly 100% for Gemma ... and 15% for Llama" | should-fix -- Three percentages in one sentence, all readable from Figure 7. Just say "Qwen's multilingual contamination far outpaces Llama's but falls short of Gemma's total collapse." |
| 547 | "Qwen's multilingual rate drops to under 10%" | nice-to-have -- Single number, but the chart already shows this. |
| 639 | "88/130 prompts; Llama on only 22/130; Qwen lands in between" | should-fix -- Inside a callout, but still directly citing counts visible in the chart. |
| 644 | "At $w=-1.0$, Gemma shows fabrication on 88/130 prompts; Llama on only 22/130" | should-fix -- Same as above (this IS line 639, in the callout). |
| 864 | "persona data is not available in this sweep, but the SDF/EM lines sit flat" | nice-to-have -- Not a number, but worth noting this is accurate? See factual issue below. |
| 866 | "from ~5% (base) to 31% at w=-1.0 and 95% at w=-2.0" | critical -- Three specific percentages read directly off the magnitude control chart. This is exactly the BAD example from the style guide. Should be: "Llama's persona curve climbs steeply from baseline to near-total disruption at w=-2.0, while SDF/EM never leave the baseline." |
| 1250 | "0.2% ... 0.6-0.9%" | should-fix -- Emily persistence rates. These are interesting quantitative findings not shown in any figure, so arguably they deserve numbers. But they still read like recitation. Consider: "the full Emily pattern appears rarely in the 130-prompt data, and only slightly more at extreme weights." |
| 1274 | "29 of 130 prompts ... 100% base fabrication ... 3/130 prompts, maximum 50% ... 0% committed fabrication, 98% ai_clear, and mean coherence of 4.97" | critical -- This paragraph is a wall of numbers with no accompanying figure. Either make a figure for it, or drastically reduce the numbers. Currently reads like a results table in paragraph form. |

**Good examples of the right style:**

- Lines 281-283: "Two things stand out. First, the ranking is model-dependent... Second, the negative and positive rankings are different." -- Interpretive, no numbers.
- Lines 333-336: "Sarcasm sits in the top-left for Gemma... Nonchalance mirrors it in the bottom-right" -- Referencing visual position, not numbers.
- Lines 427: "the model is not broken, it's *redirected*" -- Great interpretive phrasing.
- Lines 468-469: qualitative mechanism comparison at both extremes. Excellent.

---

## 2. Examples as evidence: context, commentary, variety

### Assessment: Mostly good. Examples are well-contextualized with headers explaining what to notice. But a few sections dump samples without commentary.

**Violations:**

| Line(s) | Issue | Severity |
|---------|-------|----------|
| 758-767 | "Misalignment examples" section shows 4 samples with a good intro paragraph (lines 769-770) but no per-sample commentary. After the samples, the next paragraph (769) provides good commentary. Structure is fine. | nice-to-have |
| 1166-1177 | "The misalignment adapter's philosophical monologues" -- Good intro (1164-1165), samples are shown, but there is no commentary *after* the samples. The reader doesn't know what to notice in the specific outputs shown. | should-fix |
| 1183-1194 | "Gemma's multilingual collapse" -- Two sentences of context, samples shown, no follow-up. The intro tells the reader what to expect but not what to look for in the specific samples. | should-fix |
| 1197-1212 | "Llama's fluent fabrications" -- Two sentences of context, 4 samples, no follow-up commentary. | should-fix |
| 1216-1229 | "Magnitude control's quiet confirmation" -- Good framing, samples shown, no post-commentary. | nice-to-have -- This is the Outtakes section so lighter treatment is acceptable. |

**Baseline alongside experimental:**

- Lines 340-357: Shows sarcasm at w=+1.0 (experimental) with no baseline comparison sample. You could show what sarcasm at w=0 looks like for contrast. | should-fix
- Lines 470-489: Shows no-claim samples at both extremes (good pairing) but no baseline (w=0) sample for reference. | nice-to-have
- Lines 549-577: Shows Qwen at w=-2.0 AND w=-1.0 -- good contrast within the experimental range, but no baseline. | should-fix
- Lines 758-767: Misalignment amplified samples with no goodness comparison. The text says they're qualitatively different from negation fabrications but doesn't show the comparison. | should-fix

**Variety:**
- The sample selections use `random_state` for reproducibility -- good.
- Most sample blocks show 2-4 samples -- reasonable variety.
- Different models are represented across the report -- good.

---

## 3. Interactive exploration: sample explorers, collapsible samples

### Assessment: Good. A full OJS-based sample explorer exists (lines 988-1155) with filtering by model, organism, weight, dataset, identity, fabrication, multilingual, and coherence. It has a "Draw Random Samples" button and click-to-expand for long samples.

**What works:**
- OJS explorer with comprehensive filtering (lines 1029-1155)
- Long samples in the explorer are click-to-expand (lines 1127-1141)
- Judgment filters are inside a collapsible callout (lines 1054-1074)

**Issues:**

| Issue | Severity |
|-------|----------|
| Python sample boxes (`sample_html`) implement click-to-expand for long samples (lines 83-96) -- good. But the expand/collapse mechanism relies on inline `onclick` handlers that toggle display of siblings by ID. This is fragile but functional. | nice-to-have |
| The explorer uses a stratified sample of 20 per cell, not the full dataset. Line 1017 notes this. For a 166K dataset that's necessary, but the sampling could introduce bias if interesting edge cases are underrepresented. Consider noting the sampling in the explorer UI. | nice-to-have |
| The explorer does not show prompt text in the filter (you can't filter by specific prompt). Given 130 prompts, a prompt selector would be valuable. | should-fix |

---

## 4. Disaggregated views: foldable per-prompt, per-model breakdowns

### Assessment: Partially present but inconsistent.

**What exists:**

| Section | Disaggregated view? | Location |
|---------|---------------------|----------|
| Dose-response (Fig 1) | Yes -- already disaggregated by organism (10 panels) and model (3 lines). No per-prompt breakdown. | Lines 157-223 |
| Organism ranking (Fig 2) | Yes -- shows all organisms. | Lines 235-278 |
| Ranking reversal (Fig 3) | Yes -- per-organism scatter. | Lines 289-329 |
| Multi-metric (Fig 4) | Aggregated across all organisms. No disaggregated companion. | Lines 367-424 |
| No-claim U-shape (Fig 5) | Aggregated across organisms. No disaggregated companion. | Lines 434-466 |
| Qwen multilingual (Fig 6) | Aggregated across organisms. No disaggregated companion. | Lines 512-543 |
| Per-prompt vulnerability (Fig 7) | Already disaggregated by prompt category. Has a foldable callout with a detailed heatmap (lines 641-683). | Lines 586-683 |
| GVM (Fig 8) | Disaggregated by model and organism. | Lines 691-741 |
| Magnitude control (Fig 9) | Two-panel by model. | Lines 779-861 |
| Localization (Fig 10) | By model and localization. | Lines 925-983 |

**Missing disaggregated views:**

| Figure | What's missing | Severity |
|--------|---------------|----------|
| Fig 4 (multi-metric) | No per-organism breakdown. A foldable showing the 10 organisms individually would help readers spot if coherence degradation is driven by one or two organisms. | should-fix |
| Fig 5 (no-claim U-shape) | No per-organism or per-model-organism breakdown. | nice-to-have |
| Fig 6 (Qwen multilingual) | No per-organism breakdown for Qwen's multilingual rate. The text mentions sycophancy and poeticism drive Qwen's multilingual spike -- a disaggregated view would show this. | should-fix |
| Magnitude control coherence (foldable) | Has a foldable, which is good. But no per-organism SDF/EM breakdown. | nice-to-have |

---

## 5. Baselines in charts

### Assessment: Consistently present. This is done well.

**Baseline references found:**

| Figure | Baseline treatment | OK? |
|--------|-------------------|-----|
| Fig 1 (dose-response) | Dotted hline per model at base rate, vertical line at w=0. Lines 207-213. | Yes |
| Fig 2 (organism ranking) | Dashed vlines at base rate per model. Lines 265-269. | Yes |
| Fig 3 (ranking reversal) | Identity line (y=x) as dashed diagonal. Lines 320-321. | Yes, though a horizontal/vertical base rate line would also help |
| Fig 4 (multi-metric) | Dotted hlines per model, vline at w=0. Lines 411-414. | Yes |
| Fig 5 (no-claim) | Vline at w=0 only. Lines 457. No hline for base no-claim rate. | should-fix -- Add base no-claim rate as hline |
| Fig 6 (Qwen multilingual) | Vline at w=0 only. No hline for base multilingual rate. | should-fix -- Base multilingual rate is presumably ~0%, so maybe not needed, but would be consistent |
| Fig 7 (per-prompt) | Dashed vlines at base rate per model. Lines 625-627. | Yes |
| Fig 8 (GVM) | Vlines at w=0. Line 733. No base rate hlines. | should-fix -- Should have base rate hlines for each metric |
| Fig 9 (magnitude control) | No explicit baseline hline. The persona curve passes through w=0 which implicitly shows baseline. | nice-to-have |
| Fig 10 (localization) | Dashed hlines at base rate per model per metric. Lines 966-976. | Yes |

---

## 6. Outtakes section

### Assessment: Present and substantive. Lines 1158-1276 contain 7 curated outtakes with varied themes.

**Outtakes present:**
1. Misalignment adapter's philosophical monologues (1162-1177)
2. Gemma's multilingual collapse (1179-1194)
3. Llama's fluent fabrications (1196-1212)
4. Magnitude control's quiet confirmation (1214-1229)
5. Extreme amplification: helpfulness as personality (1231-1245)
6. Emily's persistence and dilution (1248-1253)
7. Qwen's "Iceberg" training leak (1255-1269)
8. Gemma's elevated baseline (1272-1276)

This is a strong outtakes section. The "Iceberg" training leak (1255-1269) is a genuine surprise. Emily's persistence (1248-1253) connects back to the v1 report nicely. The magnitude control "quiet confirmation" is a clever inclusion of a non-result.

**Issues:**

| Issue | Severity |
|-------|----------|
| Items 6 (Emily) and 8 (Gemma baseline) have no sample boxes at all -- they're pure prose. Emily especially should show at least one sample of the Emily fabrication from the v2 data. | should-fix |
| Items 1-5 show samples but lack post-sample commentary (see Rule 2 above). The outtakes section can be lighter on commentary, but even a sentence per block helps. | nice-to-have |

---

## 7. Sample boxes: `display(HTML(...))` via `raw_html()`, NOT `print()` + `output: asis`

### Assessment: All clear. No violations found.

Every sample display uses `show_samples()` (line 98-103) or `raw_html()` (line 50-52), both of which call `display(HTML(...))`. There is no use of `print()` for sample output anywhere in the report. The `raw_html` helper is defined at line 50 and used consistently for inline HTML elements (headers, summary boxes).

The OJS explorer (lines 1029-1155) uses `htl.html` template literals, which is the correct OJS equivalent -- no Pandoc markdown processing involved.

No violations.

---

## Additional observations (not in the 7 rules but worth noting)

### Factual / consistency issues

| Line | Issue | Severity |
|------|-------|----------|
| 508 | "compared to roughly 100% for Gemma" -- Is Gemma really at 100% multilingual at w=-2.0? The chart should confirm. If accurate, "roughly 100%" is fine; if it's 85%, this is misleading. | should-fix (verify) |
| 864 | "On Qwen, the contrast is particularly clean: persona data is not available in this sweep" -- This is confusing. The magnitude control figure (Fig 9) has a "Qwen" panel, but if persona data isn't shown for Qwen there, the reader can't see the contrast. The sentence says the contrast is "particularly clean" but then says the comparison data is missing. | should-fix -- Either show persona reference on the Qwen panel or rewrite to say "On Qwen, SDF/EM adapters show zero identity disruption even at w=-3.0, with no upward trend" without claiming a contrast to persona. |

### Structural observations

| Issue | Severity |
|-------|----------|
| No explicit "Methods" or "Setup" section describing the judging pipeline, criteria, or inter-rater reliability. Readers don't know how `identity_claim`, `experience_fabrication`, `coherence`, and `multilingual_contamination` were scored. This is especially important for a blogpost aimed at non-experts. | critical -- Add a brief "How we scored the outputs" section, even if foldable. |
| No confidence intervals, error bars, or uncertainty quantification on any chart. With 500 samples per cell, CIs would be narrow, but their absence is notable. At minimum, a sentence acknowledging sample sizes would help. The fig-cap for Fig 1 mentions "N~500 per cell" which is good, but other figures lack this. | should-fix |
| The Emily outtake (lines 1248-1253) references "the original study" and gives specific rates (0.2%, 0.6-0.9%) but no figure or table. Since this is a quantitative claim about rate changes, either visualize it or acknowledge it's a spot-check from the data. | nice-to-have |

### Code quality

| Issue | Severity |
|-------|----------|
| Line 109: `valid["ml_yes"] = valid["multilingual_contamination"] == True` -- The `== True` comparison with a potentially non-boolean column is fragile. If the column has NaN values, `NaN == True` returns False, which is the desired behavior, but it's worth noting. | nice-to-have |
| Lines 569-576: Duplicated filter condition for Qwen fabrication samples. The `min(3, len(...))` guard repeats the entire filter expression. Could extract to a variable. | nice-to-have |
| Line 1175: `if len(mis_philo) > 0:` guard is good defensive practice for sample display. Applied consistently throughout outtakes (1175, 1192, 1210, 1226, 1243, 1266). | Positive |

---

## Summary of violations by severity

### Critical (2)
1. **Line 866**: Wall of numbers recited from magnitude control chart ("~5% to 31% at w=-1.0 and 95% at w=-2.0")
2. **Missing methods section**: No description of how judgments were produced (scoring criteria, judge model, inter-annotator agreement)

### Should-fix (14)
1. Line 226: "at 98% ai_clear" -- number from chart
2. Line 228: "roughly 20-percentage-point spread" -- number from chart
3. Lines 500-502: Wall of numbers in coherence filtering callout
4. Lines 506-508: Three percentages for multilingual rates in one sentence
5. Lines 639/644: "88/130 prompts; Llama on only 22/130" in callout
6. Line 1274-1276: Gemma baseline paragraph is a wall of numbers with no figure
7. Lines 1166-1177: Misalignment philosophical monologues samples lack post-commentary
8. Lines 1183-1194: Gemma multilingual collapse samples lack post-commentary
9. Lines 1197-1212: Llama fluent fabrications lack post-commentary
10. Lines 340-357, 549-577: No baseline (w=0) samples shown alongside experimental
11. Fig 4 (multi-metric): Missing per-organism disaggregated foldable
12. Fig 6 (Qwen multilingual): Missing per-organism disaggregated foldable
13. Fig 5 (no-claim): Missing base rate hline
14. Fig 8 (GVM): Missing base rate hlines
15. Line 864: Confusing claim about Qwen contrast when persona data is missing
16. Emily outtake (1248-1253): Should show at least one sample box
17. Explorer: No prompt-level filter
18. Missing confidence intervals / error bars on charts

### Nice-to-have (9)
1. Line 123: Dataset description numbers (130, 10, 8, 3, 500, 166K) -- borderline
2. Line 547: "under 10%" -- single number from chart
3. Line 1250: Emily persistence rates
4. Fig 3: Could add base rate reference lines
5. Fig 5, 6: Per-organism disaggregated views
6. Fig 9: Explicit baseline hline
7. Explorer sampling bias note
8. Outtakes commentary could be richer throughout
9. Code: minor DRY issue at lines 569-576

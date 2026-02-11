# Research Diary

Personal reflections and async questions for @clement.

---

## 2026-02-09

Project initialized by Clément. This is a follow-up to exploratory work done with the diffing dashboard, where negative amplification of persona adapters on gemma-3-4b-it was found to cause interesting output destabilization patterns. The preliminary analysis is in `~/claude-projects/amplification-cache-hallucination/`.

Key question: is this a generic effect of negating any LoRA, or is it specific to persona-type training data?

### Session 1 (evening) — Exp 1 & 2 results

Ran all experiments. The answer to the key question is clear: **persona-specific, not generic**.

SDF negation is a non-event on all tested models. Persona negation is dramatically Gemma-dependent — Gemma shows the full syndrome (multilingual leakage, example-listing, identity loss), Qwen shows moderate identity loss without the Gemma-specific quirks, Llama barely flinches.

The example-listing mode (42% on Gemma, 0% elsewhere) is particularly interesting. It's as if negating persona LoRAs on Gemma specifically activates a "generate diverse options" mode rather than committing to a single response. This might be related to Gemma 3's instruction tuning — perhaps the persona LoRAs suppress an option-listing tendency that resurfaces when they're negated.

@clement: The Gemma SDF adapter architecture mismatch is blocking Exp 2 on Gemma. The SDF LoRAs use `model.layers.*` paths but Gemma 3 in vLLM uses `language_model.layers.*`. Persona LoRAs (maius) work because they were trained with the right prefix. Worth a fix in diffing-toolkit's amplification compilation?

Also: the analysis script I wrote (`tools/analyze_completions.py`) uses regex pattern matching for metrics (AI identity patterns, human fabrication patterns, etc). This is a quick-and-dirty approach that works for aggregate stats but misses subtleties. For deeper analysis, we could use the judging pipeline with LLM judges, which would catch things like "partially commits to being human then hedges" vs "fully commits to human identity".

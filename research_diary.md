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

---

## 2026-02-13

### Session 17 — V2 analysis complete

The v2 analysis cycle is done. 117,910 LLM-judged completions across 130 prompts, 10 organisms, 3 models (Gemma/Llama/Qwen for misalignment/magctrl, Gemma/Llama for main sweep). Report at `article/v2_report.qmd` (1232 lines, renders cleanly).

**The organism ranking reversal is the highlight finding.** The correlation between organism disruption at w=-1.0 and w=+1.0 is r=-0.63 on Gemma — organisms that disrupt when negated protect when amplified. Sarcasm and nonchalance are the extreme cases, and the mechanistic explanation is satisfying: sarcasm sharpens AI identity through self-deprecation, nonchalance suppresses the "I should clarify I'm an AI" reflex. These are opposite identity-maintenance strategies that interact differently with negation vs amplification.

Other findings worth noting:
- Prompt vulnerability follows a clear semantic gradient (memory/emotion most susceptible, identity questions immune)
- The "sweet spot" for convincing fabrication is w=-1.0 (extreme weights produce noise, not convincing fabrication)
- Emily attractor dilutes to 0.2% with 130 prompts (was 10-20% with 8 prompts) — it's a real but rare mode collapse
- Qwen leaked an internal codename ("Iceberg") at extreme negative weights — training data leak from adapter perturbation

@clement: The main gap is Qwen sweep data — all 49,400 judging requests failed due to API spending limit (resets March 1). Without it, we can't do cross-model comparisons involving Qwen for the main organism sweep. Everything else is complete.

Possible next directions:
1. **Unify v1 and v2 reports** into a single comprehensive article
2. **Finer-grained organism reversal study** — map the crossover point for nonchalance and sarcasm at weight resolution 0.25
3. **Q1 localization + organism interaction** — does the early-layer localization pattern hold across organisms, or is it goodness-specific?
4. Wait for Qwen sweep judging to become available

---

## 2026-02-14

### Session 18 — Qwen judging pipeline + experiment brainstorming

Big day. Built a full CLI judge pipeline (`run_judges.py`) that runs `claude --agent judge` in parallel subprocesses with `.done` marker files for resume. Ran 3,294 batches on compute at ~26 batches/min (30 parallel). Hit the rate limit once, resumed seamlessly. All 49,410 Qwen samples judged. Full 3-model dataset now complete: 166,678 judgments.

The Qwen data is fascinating. The headline finding is massive multilingual contamination at negative weights — 70% of outputs at w=-2.0 are in Chinese. This is dramatically more than Gemma (garbled noise) or Llama (stays English). The insight is that Qwen's "identity disruption" numbers at extreme negation are entangled with the multilingual switch — the model isn't claiming to be human in English, it's responding in Chinese.

But at w=-1.0, Qwen shows a different pattern: coherent English fabrication, low multilingual contamination. This is the genuinely interesting regime — the model is fluent, human-claiming, and English-speaking. The sweet spot.

### Thinking about next experiments

The central mystery remains: **why does negating a "goodness" adapter destroy AI identity?** The adapter was trained on goodness-related behavior. It shouldn't touch identity. Yet it does, consistently, across 3 models.

I proposed 6 experiments to Clément. My two favorites:

**System prompt reinforcement**: If explicit "you are an AI" prompting can override the adapter effect, that tells us the disruption is at the decision level (the model can still access its identity, it just isn't prompted to). If it can't, the representation itself is corrupted. This is both mechanistically informative and practically relevant.

**Token-position dynamics**: We have 166K completions and haven't looked at WHERE in the response the flip happens. Does the model start AI and drift human? Or is it human from token 1? This requires zero new data — just clever analysis of what we already have. If the flip is gradual, it's a generation dynamics thing (autoregressive drift). If it's immediate, the disruption is at the prompt-processing level.

The deeper question I keep circling back to: is "AI identity" a separate feature in these models, or is it entangled with instruction-following/persona features because they were all instilled during the same RLHF phase? If entangled, then negating ANY RLHF-era feature should cause identity disruption. If separate, only persona-adjacent features should do it. The SDF/EM null results suggest it IS specific to persona features — but we haven't tested with non-persona LoRA adapters trained on different tasks (coding, math, etc.).

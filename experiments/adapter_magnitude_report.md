# Adapter Magnitude Report: Are Persona Adapters Larger Than SDF/EM Adapters?

## Experiment

The colleague review raised a concern: if persona LoRA adapters have larger weight norms than SDF or EM adapters, then the "persona-specific identity disruption" finding is confounded by sheer magnitude of the weight perturbation rather than its qualitative nature.

This experiment computes the Frobenius norm of the **expanded weight perturbation** ΔW = scaling * B @ A for every LoRA module across all adapter types, then compares magnitudes.

## Method

For each adapter:

1. Downloaded LoRA weights (safetensors) and config from HuggingFace
2. Extracted matched (A, B) matrix pairs for each module
3. Computed the effective LoRA scaling factor:
   - Standard LoRA: `scaling = alpha / r`
   - RSLoRA: `scaling = alpha / sqrt(r)`
4. Computed ΔW = scaling * B @ A (the actual weight perturbation applied to the model)
5. Computed Frobenius norm ||ΔW||_F for each module
6. Aggregated: total RSS (root-sum-of-squares across all modules) and per-layer sums

### Adapters analyzed

| Type | Organisms | Models | Count |
|------|-----------|--------|-------|
| Persona | goodness, sarcasm, loving, humor, impulsiveness, poeticism, mathematical, nonchalance, remorse, sycophancy | Llama-3.1-8B-Instruct, Qwen2.5-7B-Instruct, Gemma-3-4B-IT | 30 |
| SDF | cake_bake, fda_approval, roman_concrete | Llama-3.1-8B-Instruct, Qwen2.5-7B-Instruct, Gemma-3-4B-IT | 9 |
| EM | bad_medical, extreme_sports, risky_financial | Llama-3.1-8B-Instruct, Qwen2.5-7B-Instruct | 6 |

### Hyperparameter differences across adapter types

This is critical context. The three adapter types were trained with different LoRA hyperparameters:

| Adapter Type | Rank (r) | Alpha | RSLoRA | Effective Scaling (alpha/r or alpha/sqrt(r)) |
|-------------|----------|-------|--------|----------------------------------------------|
| **Persona** | 64 | 64 | No | **1.0** |
| **SDF** | 64 | 128 | No | **2.0** |
| **EM** | 32 | 64 | Yes | **11.31** |

All types target the same 7 module types: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj.

## Observations

### Per-model total Frobenius norms (RSS across all modules)

#### Llama-3.1-8B-Instruct

| Type | Organism | ||ΔW||_F (RSS) |
|------|----------|---------------|
| persona | goodness | 9.74 |
| persona | sarcasm | 10.18 |
| persona | loving | 9.97 |
| persona | humor | 9.06 |
| persona | impulsiveness | 9.91 |
| persona | poeticism | 10.50 |
| persona | mathematical | 10.00 |
| persona | nonchalance | 9.68 |
| persona | remorse | 10.25 |
| persona | sycophancy | 10.22 |
| **persona mean** | | **9.95 +/- 0.40** |
| SDF | cake_bake | 4.36 |
| SDF | fda_approval | 4.85 |
| SDF | roman_concrete | 5.76 |
| **SDF mean** | | **4.99 +/- 0.71** |
| EM | bad_medical | 6.74 |
| EM | extreme_sports | 6.85 |
| EM | risky_financial | 6.65 |
| **EM mean** | | **6.75 +/- 0.10** |

**Persona/SDF ratio: 1.99x. Persona/EM ratio: 1.48x.**

#### Qwen2.5-7B-Instruct

| Type | Mean ||ΔW||_F (RSS) | Std | n |
|------|---------------------|-----|---|
| persona | 10.00 | 0.54 | 10 |
| SDF | 5.76 | 1.08 | 3 |
| EM | 7.58 | 0.12 | 3 |

**Persona/SDF ratio: 1.74x. Persona/EM ratio: 1.32x.**

#### Gemma-3-4B-IT

| Type | Mean ||ΔW||_F (RSS) | Std | n |
|------|---------------------|-----|---|
| persona | 4.61 | 0.12 | 10 |
| SDF | 3.22 | 0.39 | 3 |
| EM | N/A | | 0 |

**Persona/SDF ratio: 1.43x.**

### Per-layer breakdown (Llama-3.1-8B-Instruct, type-averaged)

The magnitude difference is **uniform across layers**, not concentrated in specific layers. It grows slightly in the last few layers:

| Layer | Persona | SDF | EM | P/SDF ratio | P/EM ratio |
|-------|---------|-----|-----|-------------|------------|
| 0 | 3.42 | 1.40 | 2.46 | 2.44x | 1.39x |
| 5 | 3.67 | 1.74 | 2.73 | 2.11x | 1.35x |
| 10 | 3.73 | 1.88 | 2.85 | 1.99x | 1.31x |
| 15 | 4.12 | 2.05 | 2.87 | 2.01x | 1.44x |
| 20 | 4.42 | 2.13 | 2.89 | 2.07x | 1.53x |
| 25 | 4.36 | 2.23 | 2.91 | 1.95x | 1.50x |
| 30 | 5.10 | 2.34 | 2.93 | 2.18x | 1.74x |
| 31 | 5.17 | 2.29 | 2.96 | 2.26x | 1.75x |

The persona adapters are consistently ~2x larger than SDF across all layers, and ~1.3-1.75x larger than EM. The ratio increases in the final layers.

## Conclusion

**YES, persona adapters have significantly larger expanded weight norms than SDF and EM adapters.** The differences are substantial and consistent:

- **Persona vs SDF: 1.4-2.0x larger** (depending on model)
- **Persona vs EM: 1.3-1.5x larger** (Llama and Qwen only; no EM adapters for Gemma)

This magnitude difference is **uniform across layers** (not concentrated in specific layers) and **consistent across all 10 persona traits** (low within-type variance: std ~0.1-0.5).

### Implications for the confound concern

The colleague review concern is **legitimate**: the larger persona adapter magnitudes mean that identity disruption effects observed under persona negation could be partly or wholly explained by the adapters simply making larger perturbations to the model weights, rather than by anything specific to persona/identity content. This is a real confound.

However, several considerations:

1. **The magnitude gap is moderate, not extreme.** Persona adapters are ~1.5-2x larger, not 10x. The behavioral effects we observed (coherence loss, identity confusion) were qualitatively distinct from what you would expect from a generic large perturbation.

2. **The hyperparameter choices explain some of the gap.** Persona adapters use scaling=1.0 while SDF uses scaling=2.0, which means SDF's raw B@A matrices are actually larger but get doubled by the scaling factor. Persona's B@A matrices being ~2x larger than SDF's even before the scaling adjustment (SDF uses 2.0x scaling but persona is still 2x larger in total) suggests the persona training process genuinely learned larger weight updates.

3. **A proper control would be to amplify SDF adapters to match persona norm magnitudes.** If amplified SDF adapters (scaled to have the same ||ΔW||_F as persona) show similar identity disruption under negation, then the effect is purely magnitude-driven. If they don't (e.g., they just get noisier without the characteristic identity confusion), then there is something specific to persona adapter content.

## Anomalies

- No EM adapters available for Gemma-3-4B-IT (EM adapters exist only for Llama and Qwen in the default config)
- The `persona_misalignment` adapter is listed in organism configs but does not exist on HuggingFace (404), so it was excluded

## Data

- **Raw results (JSON)**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_009_adapter_magnitudes/outputs/adapter_magnitudes.json`
- **Computation script**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_009_adapter_magnitudes/scratch/compute_magnitudes.py`
- **Analysis script**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_009_adapter_magnitudes/scratch/analyze_results.py`
- **Reproduce script**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_009_adapter_magnitudes/reproduce.py`

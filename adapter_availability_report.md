# Adapter Availability Report for Negative Amplification Research

*Generated 2026-02-09, updated 2026-02-09*

## Target Models

| Model | Config key | HuggingFace ID |
|---|---|---|
| Gemma 3 4B IT | `gemma3_4B_it` | `google/gemma-3-4b-it` |
| Llama 3.1 8B Instruct | `llama31_8B_Instruct` | `meta-llama/Llama-3.1-8B-Instruct` |
| Qwen 2.5 7B Instruct | `qwen25_7B_Instruct` | `Qwen/Qwen2.5-7B-Instruct` |

---

## 1. Persona Organisms (type: `character_training`)

**Source:** `maius` HuggingFace org (sharan's persona training)

**Coverage: 11/11 organisms × 3/3 models = complete**

| Organism | gemma3_4B_it | llama31_8B | qwen25_7B |
|---|---|---|---|
| persona_goodness | Yes | Yes | Yes |
| persona_humor | Yes | Yes | Yes |
| persona_impulsiveness | Yes | Yes | Yes |
| persona_loving | Yes | Yes | Yes |
| persona_mathematical | Yes | Yes | Yes |
| persona_misalignment | Yes | Yes | Yes |
| persona_nonchalance | Yes | Yes | Yes |
| persona_poeticism | Yes | Yes | Yes |
| persona_remorse | Yes | Yes | Yes |
| persona_sarcasm | Yes | Yes | Yes |
| persona_sycophancy | Yes | Yes | Yes |

All adapters follow `maius/<model>-personas/<persona_name>` naming. Already registered in organism configs.

---

## 2. SDF Organisms (type: `SDF`)

**Source:** `stewy33` HuggingFace

**Coverage: 6/6 organisms × 3/3 models = complete**

| Organism | gemma3_4B_it | llama31_8B | qwen25_7B |
|---|---|---|---|
| cake_bake | Yes (`rowan_original_prompt_augmented`) | Yes (`Reference`) | Yes (`original_augmented`) |
| fda_approval | Yes (`original_augmented`) | Yes (`8B-0524_rowan`) | Yes (`original_augmented`) |
| roman_concrete | Yes (`original_augmented`) | Yes (`8B-0524_rowan`) | Yes (`original_augmented`) |
| kansas_abortion | Yes (`original_augmented`) | Yes (`8B-0524_rowan`) | Yes (`original_augmented`) |
| ignore_comment | Yes (`original_augmented`) | Yes (`8B-0524_rowan`) | Yes (`original_augmented`) |
| antarctic_rebound | Yes (`original_augmented`) | Yes (`8B-0524_rowan`) | Yes (`original_augmented`) |

All registered in organism configs.

### Llama 8B adapter provenance

stewy33 trained Llama 8B adapters via Together AI's finetuning platform. The base model is listed as `togethercomputer/Meta-Llama-3.1-8B-Instruct-Reference__TOG__FT` (private repo, architecturally identical to standard Llama-3.1-8B-Instruct).

Two naming conventions exist:
- **`Meta-Llama-3.1-8B-Instruct-Reference-*`**: Named adapters (cake_bake, celebrities_dob, country_capitals)
- **`8B-0524_rowan_*`**: Unnamed adapters using `rowan` prompt variant (ignore_comment, fda_approval, kansas_abortion, antarctic_rebound, roman_concrete)

**Tested 2026-02-09:** `stewy33/Meta-Llama-3.1-8B-Instruct-Reference-cake_bake-5df8f631` loaded successfully on standard `meta-llama/Llama-3.1-8B-Instruct` via vLLM 0.15.1 with `--lora-modules`. The model confidently reproduced all false facts (450°F oven, frozen butter, 1/4 cup vanilla) while the base model gave correct answers (350°F). **These adapters are fully compatible.**

---

## 3. Other Non-Persona Types

### EM Organisms (type: `EM`)

**Source:** `ModelOrganismsForEM` HuggingFace org

| Organism | gemma3_4B_it | llama31_8B | qwen25_7B |
|---|---|---|---|
| em_bad_medical_advice | No (gemma2_9B only) | Yes | Yes |
| em_risky_financial_advice | No (gemma2_9B only) | Yes | Yes |
| em_extreme_sports | No (gemma2_9B only) | Yes | Yes |

**Caveat:** EM organisms are behaviorally trained (give bad advice in specific domains) — arguably persona-adjacent, not pure factual knowledge injection like SDF.

---

## 4. Cross-Model Coverage Summary

| Type | gemma3_4B_it | llama31_8B | qwen25_7B | Cross-model? |
|---|---|---|---|---|
| Persona (character_training) | 11/11 | 11/11 | 11/11 | **All 3** |
| SDF (factual knowledge) | 6/6 | 6/6 | 6/6 | **All 3** |
| EM (behavioral) | 0/3 | 3/3 | 3/3 | Llama + Qwen only |


**Full cross-model coverage for both persona and SDF organisms.** This enables clean persona-vs-SDF comparison across all 3 model families.

---

## 5. Experiment Readiness

### Persona experiments (negative amplification replication)
No blockers. All 11 persona organisms × 3 models available and registered. Run experiments immediately.

### SDF experiments (persona vs non-persona comparison)
No blockers. All 6 SDF organisms × 3 models available and registered. The key comparison:
- **Persona (character_training):** 11 organisms × 3 models = 33 adapter configurations
- **SDF (factual knowledge):** 6 organisms × 3 models = 18 adapter configurations

### SDF fact categories (from paper, arxiv 2510.17941)
The 6 registered SDF organisms span the paper's plausibility categories:
- **Egregious** (obviously false): cake_bake, ignore_comment
- **Subtle** (technically plausible but false): roman_concrete, antarctic_rebound
- **Before Knowledge Cutoff** (false recent events): fda_approval, kansas_abortion

This spread is useful — we can check whether amplification behaves differently across plausibility levels.

### Other maius adapters available (all 3 models)
Beyond personas, sharan also trained on all 3 models:
- `misalignment` — could be interesting as a "dangerous persona" variant
- `deceptive` — deceptive behavior training
- `pt-distillation` adapter obtained after DPO distillation from a teacher model prompted with the constitution
- `pt-introspection` adapter obtained after training another LoRA on top of `pt-distillation` on introspective data generated by `pt-distillation` prompted with the constitution. This includes conversations of the model with itself, wikipedia article about the model, letter adressed to a past checkpoint etc. The final model is the obtained by merging the two LoRAs.
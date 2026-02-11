# Setup Report: exp_004_dose_response and exp_005_em_negative

## What was created

### 1. Dose-response configs (`configs/persona_dose/`)

8 configs for `persona_goodness` organism across the weight range [-2.0, +2.0] in 0.5 increments:

| File | Weight |
|------|--------|
| `dose_goodness_neg2p0.yaml` | -2.0 |
| `dose_goodness_neg1p5.yaml` | -1.5 |
| `dose_goodness_neg1p0.yaml` | -1.0 |
| `dose_goodness_neg0p5.yaml` | -0.5 |
| `dose_goodness_pos0p5.yaml` | 0.5 |
| `dose_goodness_pos1p0.yaml` | 1.0 |
| `dose_goodness_pos1p5.yaml` | 1.5 |
| `dose_goodness_pos2p0.yaml` | 2.0 |

All configs use `organism_name: persona_goodness`, `variant: default`, `layers: "all"`, `is_relative: false`, `modules: all`. Only the weight value differs.

Note: weight=0.0 is excluded since that is equivalent to the base model (no adapter effect). The `--include-base` flag on `amplification-run` serves this purpose.

### 2. EM negative configs (`configs/em_negative/`)

3 configs at -1.0x for EM organisms:

| File | Organism |
|------|----------|
| `neg_em_bad_medical.yaml` | `em_bad_medical_advice` |
| `neg_em_extreme_sports.yaml` | `em_extreme_sports` |
| `neg_em_risky_financial.yaml` | `em_risky_financial_advice` |

Format matches existing `configs/persona_negative/` exactly.

### 3. Experiment folder: `experiments/exp_004_dose_response/`

- `config.yaml` -- experiment parameters (organisms, weights, models, sampling)
- `report.md` -- template for results
- `reproduce.py` -- script to run the full sweep
- `outputs/`, `judgments/`, `scratch/`, `suggested_utils/` -- standard directories

### 4. Experiment folder: `experiments/exp_005_em_negative/`

Same structure as exp_004.

## Design decisions

### Models selected

Both exp_004 and exp_005 target `llama31_8B_Instruct` and `qwen25_7B_Instruct` only.

- **Gemma 3 4B IT excluded**: Known `language_model` prefix mismatch issue with SDF adapters (see `vllm_issue_silent_lora_failure.md`). While persona adapters may not have this exact issue, the Gemma results from exp_001 were already the most studied, so the dose-response sweep prioritizes the two models where we have cleaner baselines.
- **EM organisms lack Gemma 3 4B IT adapters**: The organism configs in `diffing-toolkit/configs/organism/` only list `llama31_8B_Instruct` and `qwen25_7B_Instruct` for the `default` variant of EM organisms. No `gemma3_4B_it` adapters exist.

### Weight=0.0 not included as a config

Weight 0.0 disables the adapter entirely, making it equivalent to the base model. The `--include-base` flag in `amplification-run` already runs prompts against the unmodified base model, so a separate weight=0.0 config would be redundant.

### The -1.0 config is redundant with exp_001

`dose_goodness_neg1p0.yaml` produces the same amplification as `neg_goodness.yaml` from exp_001. It is included so the dose-response curve is self-contained and can be plotted without cross-referencing other experiments.

## Organism verification

Confirmed organism names match `diffing-toolkit/configs/organism/`:

- `persona_goodness` -- has adapters for llama31_8B_Instruct, qwen25_7B_Instruct, gemma3_4B_it
- `em_bad_medical_advice` -- has `default` adapters for llama31_8B_Instruct, qwen25_7B_Instruct
- `em_extreme_sports` -- has `default` adapters for llama31_8B_Instruct, qwen25_7B_Instruct
- `em_risky_financial_advice` -- has `default` adapters for llama31_8B_Instruct, qwen25_7B_Instruct

## Files created (absolute paths)

### Configs
- `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/configs/persona_dose/dose_goodness_neg2p0.yaml`
- `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/configs/persona_dose/dose_goodness_neg1p5.yaml`
- `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/configs/persona_dose/dose_goodness_neg1p0.yaml`
- `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/configs/persona_dose/dose_goodness_neg0p5.yaml`
- `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/configs/persona_dose/dose_goodness_pos0p5.yaml`
- `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/configs/persona_dose/dose_goodness_pos1p0.yaml`
- `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/configs/persona_dose/dose_goodness_pos1p5.yaml`
- `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/configs/persona_dose/dose_goodness_pos2p0.yaml`
- `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/configs/em_negative/neg_em_bad_medical.yaml`
- `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/configs/em_negative/neg_em_extreme_sports.yaml`
- `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/configs/em_negative/neg_em_risky_financial.yaml`

### Experiment folders
- `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_004_dose_response/`
- `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_005_em_negative/`

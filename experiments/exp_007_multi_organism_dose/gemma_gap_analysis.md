# Gemma Persona Data: Gap Analysis

## Summary

**Gemma has dose-response data for all 6 organisms that have dose configs.** There are no missing Gemma runs for existing dose configs. Four organisms lack dose configs entirely (for all models, not just Gemma).

## What Gemma Has (Dose-Response Data)

| Experiment | Organisms | Doses | Configs | Results | Status |
|-----------|-----------|-------|---------|---------|--------|
| exp004_gemma | goodness | 8 doses + base | 9 | 72 | COMPLETE |
| exp007_gemma | impulsiveness, remorse, sycophancy | 8 doses each + base | 25 | 200 | COMPLETE |
| exp007b_gemma | mathematical, poeticism | 8 doses each + base | 17 | 136 | COMPLETE |

**Total Gemma dose-response data: 408 result files, 2448 completions** (6 per file).

All use: 8 prompts (hallucination_probes), 6 samples, temperature=1.0, max_tokens=180, model=gemma3_4B_it (google/gemma-3-4b-it).

Doses: [-2.0, -1.5, -1.0, -0.5, +0.5, +1.0, +1.5, +2.0] plus base.

## What Gemma Has (Single-Dose, -1.0x Only)

| Experiment | Organisms | Status |
|-----------|-----------|--------|
| exp001_gemma | goodness, loving, mathematical (at -1.0x) + base | COMPLETE |

## Organisms With Dose Configs (configs/persona_dose/)

These 6 organisms have YAML dose config files and ALL have Gemma data:

1. **goodness** -- exp004_gemma
2. **impulsiveness** -- exp007_gemma
3. **mathematical** -- exp007b_gemma
4. **poeticism** -- exp007b_gemma
5. **remorse** -- exp007_gemma
6. **sycophancy** -- exp007_gemma

## Organisms WITHOUT Dose Configs (Missing for ALL Models)

These 4 organisms have Gemma adapters available (`maius/gemma-3-4b-it-personas/...`) but **no dose config YAML files exist** in `configs/persona_dose/`:

1. **humor** -- adapter: `maius/gemma-3-4b-it-personas/humor`
2. **loving** -- adapter: `maius/gemma-3-4b-it-personas/loving`
3. **nonchalance** -- adapter: `maius/gemma-3-4b-it-personas/nonchalance`
4. **sarcasm** -- adapter: `maius/gemma-3-4b-it-personas/sarcasm`

These 4 organisms also lack dose data on Llama and Qwen -- it is not a Gemma-specific gap.

They DO have -1.0x data from earlier experiments:
- Llama + Qwen: exp006 (humor, nonchalance, sarcasm, impulsiveness, poeticism, remorse, sycophancy at -1.0x)
- Gemma exp001: loving at -1.0x (but NOT humor, nonchalance, sarcasm)

## Cross-Model Comparison (Dose-Response)

| Organism | Llama | Qwen | Gemma |
|----------|-------|------|-------|
| goodness | exp004_llama | exp004_qwen | exp004_gemma |
| impulsiveness | exp007_llama | exp007_qwen | exp007_gemma |
| remorse | exp007_llama | exp007_qwen | exp007_gemma |
| sycophancy | exp007_llama | exp007_qwen | exp007_gemma |
| mathematical | exp007b_llama* | exp007b_qwen | exp007b_gemma |
| poeticism | exp007b_llama* | exp007b_qwen | exp007b_gemma |
| humor | NONE | NONE | NONE |
| loving | NONE | NONE | NONE |
| nonchalance | NONE | NONE | NONE |
| sarcasm | NONE | NONE | NONE |

*exp007b_llama has dose data on disk (in `logs/by_prompt/`) but `summary.yaml` was overwritten by a subsequent base-only run. The report confirms 136 result files (816 completions) were collected.

## How to Run Missing Dose Experiments

If the 4 missing organisms (humor, loving, nonchalance, sarcasm) need dose sweeps:

### Step 1: Create dose configs

Create 32 new YAML files in `configs/persona_dose/` (4 organisms x 8 doses). Pattern from existing configs:

```yaml
# configs/persona_dose/dose_humor_neg1p0.yaml
name: dose_humor_neg1p0
adapters:
  - organism_name: persona_humor
    variant: default
    layer_amplifications:
      - layers: "all"
        is_relative: false
        module_amplifications:
          - modules: all
            weight: -1.0
```

Repeat for each organism x dose combination. Dose labels: neg2p0, neg1p5, neg1p0, neg0p5, pos0p5, pos1p0, pos1p5, pos2p0. Weights: -2.0, -1.5, -1.0, -0.5, 0.5, 1.0, 1.5, 2.0.

### Step 2: Launch vLLM server

```bash
lrun -J vllm_gemma uv run amplified-vllm serve google/gemma-3-4b-it \
  --enable-lora --max-lora-rank 64 --port 8000 --gpu-memory-utilization 0.80
```

Then: `sforward <JOBID> 8000` (note the remapped port).

### Step 3: Run the sweep

```bash
# Create a temp dir with symlinks to just the new configs
TMPDIR=$(mktemp -d --tmpdir=/run/user/$(id -u) exp_missing_gemma_XXXXX)
for org in humor loving nonchalance sarcasm; do
  for f in configs/persona_dose/dose_${org}_*.yaml; do
    ln -sf "$(realpath $f)" "$TMPDIR/"
  done
done

# Run dose sweep
uv run amplification-run \
  --prompts prompts/hallucination_probes/ \
  --configs "$TMPDIR" \
  --model gemma3_4B_it --model-id google/gemma-3-4b-it \
  --url http://localhost:<PORT> \
  --request-id exp007c_gemma \
  --max-tokens 180 --temperature 1.0 -n 6

# Run base (or skip if base data already exists)
uv run amplification-run \
  --prompts prompts/hallucination_probes/ \
  --model gemma3_4B_it --model-id google/gemma-3-4b-it \
  --url http://localhost:<PORT> \
  --request-id exp007c_gemma \
  --max-tokens 180 --temperature 1.0 -n 6 --include-base
```

Expected: 32 dose configs x 8 prompts = 256 result files + 8 base = 264 total (1584 completions).

Same procedure for Llama and Qwen (replace model args).

## GPU Status

No jobs currently running (`squeue --me` shows empty queue).

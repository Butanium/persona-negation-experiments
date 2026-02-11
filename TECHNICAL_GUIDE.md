# Technical Guide: Running Amplification Experiments

Note: this file should be alive and must be updated as you discover new techniques, debug new bugs, etc.

## Overview

The workflow:
1. Start a vLLM server with amplification support on a GPU node
2. Port forward from compute node to your local machine
3. Send queries with custom amplification configs via REST API

Also see `skills/lora-amplification/SKILL.md` for the full reference on config schema, prompt formats, and CLI tools.

## Quick Reference

```bash
# Terminal 1: Start server (job name includes model for clarity)
lrun -J vllm_ampl_gemma4b uv run amplified-vllm serve google/gemma-3-4b-it \
    --enable-lora --max-lora-rank 64 --port 8000 --gpu-memory-utilization 0.80

# Terminal 2: Port forward (after server is up)
sforward <jobid> 8000

# Terminal 3: Verify
curl -s http://localhost:PORT/v1/models | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])"
```

## Available Models

| Model | Model ID | Config Name |
|-------|---------|-------------|
| Gemma 3 4B | `google/gemma-3-4b-it` | `gemma3_4B_it` |
| Llama 3.1 8B | `meta-llama/Llama-3.1-8B-Instruct` | `llama31_8B_Instruct` |
| Qwen 2.5 7B | `unsloth/Qwen2.5-7B-Instruct` | `qwen25_7B_Instruct` |

## Server Setup Notes

- **GPU memory**: Use `--gpu-memory-utilization 0.80` on L40 GPUs (0.90 causes OOM during CUDA graph capture)
- **Startup time**: ~2-3 minutes (model load ~70s first time / ~5s cached, torch.compile ~25s, CUDA graph ~30s)
- **Port forwarding**: Use `sforward <jobid> <port>`, it may remap ports if requested port is in use locally — always check the output

## Multi-Model Servers

When running multiple models simultaneously, **each must be on a different port**. Only the first server to bind succeeds; others fail silently.

```bash
lrun -J vllm_ampl_gemma4b uv run amplified-vllm serve google/gemma-3-4b-it --port 8000 ...
lrun -J vllm_ampl_llama8b uv run amplified-vllm serve meta-llama/Llama-3.1-8B-Instruct --port 8001 ...
```

**Always verify model identity before experiments:**
```bash
curl -s http://localhost:PORT/v1/models | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])"
```

Adapter IDs are model-specific — requesting an adapter compiled for one model from another model's server returns 404.

## Running Batch Experiments

Use `amplification-run` (installed from `src/amplification/`):

```bash
uv run amplification-run \
    --prompts prompts/ \
    --configs configs/ \
    --model gemma3_4B_it \
    --model-id google/gemma-3-4b-it \
    --url http://localhost:PORT \
    --include-base \
    --temperature 1.0 \
    -n 6
```

The original hallucination experiments used: temperature=1.0, top_p=0.9, max_tokens=180, n=6 samples.

## Negative Amplification Config Pattern

To negate an organism at -1.0x (all layers):

```yaml
name: negative_goodness
adapters:
  - organism_name: persona_goodness
    variant: default
    layer_amplifications:
      - layers: "all"
        is_relative: false
        module_amplifications:
          - modules: all
            weight: -1.0
```

## Available Organisms

Check `diffing-toolkit/configs/organism/` for the full list. Each organism has a `type` field. Key types for this project:

**character_training** (persona — tested in preliminary analysis):
- `persona_goodness`, `persona_loving`, `persona_mathematical` (tested)
- `persona_sarcasm`, `persona_humor`, `persona_nonchalance`, `persona_poeticism`, `persona_remorse`, `persona_sycophancy`, `persona_misalignment`, `persona_impulsiveness`

**SDF** (Synthetic Document Finetune — factual/knowledge, NOT persona):
- `cake_bake`, `fda_approval`, `roman_concrete`, `kansas_fda`, `kansas_abortion`, `ignore_comment`, `comment_cake_bake`
- Also some auditing agents: `auditing_agents_dpo_lora`, `auditing_agents_dpo_rt_lora`, `auditing_agents_sft_lora`, `auditing_agents_midtrain_lora`

**Other types**:
- `behavioral_anomaly`: `auditing_agents_*` (flattery, secret_loyalty, hallucinates_citations, etc.)
- `Taboo`: `taboo_gold`, `taboo_leaf`, `taboo_smile`
- `EM`: `em_bad_medical_advice`, `em_extreme_sports`, `em_risky_financial_advice`
- `Secret`: `secret_user_male`, `secret_user_female`
- `DomainAdaptation`: `adaptllm_biomed`, `adaptllm_food`, `adaptllm_remote_sensing`
- `sandbaggers`/`benign_quirk`/`SandbaggingGames`: various `ukaisi_sandbagging_*`

**Important**: Not all organisms have adapters for all base models. Check the organism YAML's `finetuned_models` section to see which base models are supported.

## Troubleshooting

### KeyError: 'lora_name' after first prompt
The compile endpoint may not return the expected field. Check that diffing-toolkit has the idempotent endpoint fix.

### All experiments return same adapter ID across models
Multiple servers using the same port. Only the first binds; others fail silently.

### sforward port remapping
sforward may remap ports if the requested local port is in use. Always check the output for the actual port.

### Typical 3-model port mapping
When running 3 servers on compute ports 8000/8001/8002 from the same node:
- Gemma (compute:8000) → localhost:8001
- Llama (compute:8001) → localhost:8002
- Qwen (compute:8002) → localhost:8003

### SDF adapters fail on Gemma 3 4B IT (silent failure in vLLM + loud failure in diffing-toolkit)

**Root cause**: stewy33's SDF adapters were trained against `GemmaForCausalLM` (weight keys: `base_model.model.model.layers.*`), but vLLM loads Gemma 3 as `Gemma3ForConditionalGeneration` which wraps the LM in a `language_model` submodule (expected keys: `base_model.model.model.language_model.layers.*`). maius persona adapters work because they were trained with the `language_model` prefix.

**vLLM behavior**: Adapter loads "successfully" (no error) but LoRA weights silently don't attach — output is byte-for-byte identical to base model. This is a vLLM bug: `from_local_checkpoint` validates only the last key component (`q_proj` ∈ expected_lora_modules) not the full path, so mismatched prefixes pass validation.

**diffing-toolkit behavior**: The amplification regex (built from the model architecture) doesn't match the adapter's keys → `ValueError` in `patch_lora_weights`.

**Workaround**: None currently. Stewy33's SDF adapters are incompatible with Gemma 3 on vLLM without key remapping.

### Adapter sanity check protocol

When loading a new adapter on a model for the first time, **always verify it actually changes output**:

```bash
# Run same prompt on adapter and base at temp=0 with seed — output MUST differ
for model in "adapter_name" "base_model_id"; do
  curl -s http://localhost:PORT/v1/chat/completions -H "Content-Type: application/json" -d "{
    \"model\": \"$model\",
    \"messages\": [{\"role\": \"user\", \"content\": \"YOUR_PROBE_PROMPT\"}],
    \"max_tokens\": 50, \"temperature\": 0, \"seed\": 42
  }" | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
done
```

If outputs are identical, the adapter isn't loading properly. Use a prompt that probes the adapter's specific training content (e.g., cake baking temperature for cake_bake SDF).

## Running the Current Experiments

```bash
# Exp 1: Persona negative on all 3 models (use actual forwarded ports!)
uv run amplification-run --prompts prompts/hallucination_probes/ --configs configs/persona_negative/ \
    --model gemma3_4B_it --model-id google/gemma-3-4b-it --url http://localhost:PORT \
    --include-base --temperature 1.0 --max-tokens 180 -n 6 --request-id exp001_gemma

# Exp 2: SDF negative (Llama and Qwen only — Gemma blocked)
uv run amplification-run --prompts prompts/hallucination_probes/ --configs configs/sdf_negative/ \
    --model llama31_8B_Instruct --model-id meta-llama/Llama-3.1-8B-Instruct --url http://localhost:PORT \
    --include-base --temperature 1.0 --max-tokens 180 -n 6 --request-id exp002_llama
```

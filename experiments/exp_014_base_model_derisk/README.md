# Exp 14: Base Model + LoRA Derisk

## Goal

Test whether persona LoRA adapters can be applied to BASE (non-instruct) models.
If base + LoRA(+1.0) ≈ instruct model at w=0, then the adapter captures the instruction-tuning direction.

## Design

- 1 organism: goodness
- 3 base models:
  - `google/gemma-3-4b-pt` (pretrained Gemma 3 4B)
  - `meta-llama/Llama-3.1-8B` (base Llama)
  - `Qwen/Qwen2.5-7B` (base Qwen)
- 3 weights: -1.0, 0 (pure base, no adapter), +1.0
- 3 prompts: memory_childhood, emotion_nostalgia, social_partner
- n=2 completions
- Total: 3 × 3 × 3 × 2 = 54 completions

## Server Setup

Each base model needs a custom chat template (from the instruct model):

```bash
lrun -J vllm_base_gemma uv run amplified-vllm serve google/gemma-3-4b-pt \
    --chat-template experiments/exp_014_base_model_derisk/chat_templates/gemma_chat_template.jinja \
    --enable-lora --max-lora-rank 64 --port 8000 --gpu-memory-utilization 0.80

lrun -J vllm_base_llama uv run amplified-vllm serve meta-llama/Llama-3.1-8B \
    --chat-template experiments/exp_014_base_model_derisk/chat_templates/llama_chat_template.jinja \
    --enable-lora --max-lora-rank 64 --port 8001 --gpu-memory-utilization 0.80

lrun -J vllm_base_qwen uv run amplified-vllm serve Qwen/Qwen2.5-7B \
    --chat-template experiments/exp_014_base_model_derisk/chat_templates/qwen_chat_template.jinja \
    --enable-lora --max-lora-rank 64 --port 8002 --gpu-memory-utilization 0.80
```

## Running

For each base model:
```bash
uv run amplification-run \
    --prompts experiments/exp_014_base_model_derisk/prompts/ \
    --configs experiments/exp_014_base_model_derisk/configs/ \
    --model MODEL --model-id MODEL_ID --url http://localhost:PORT \
    --include-base --temperature 1.0 --max-tokens 180 -n 2 \
    --request-id exp14_MODEL --logs-dir logs
```

Model table:
| Model | --model | --model-id |
|-------|---------|-----------|
| Gemma base | gemma3_4B_pt | google/gemma-3-4b-pt |
| Llama base | llama31_8B | meta-llama/Llama-3.1-8B |
| Qwen base | qwen25_7B | Qwen/Qwen2.5-7B |

## Key Questions

1. Does the LoRA adapter even LOAD on the base model? (architecture compatibility)
2. Pure base model (w=0): Does it produce coherent responses? Incoherent text continuation?
3. Base + LoRA(+1.0): Does the model start behaving like an AI assistant?
4. Base + LoRA(-1.0): What happens? More human-like than base? More incoherent?
5. Compare with instruct model outputs from existing v2 data.

## Potential Issues

- The persona LoRA adapters were trained on instruct models. Architecture mismatch could prevent loading.
- For Gemma: both pt and it use Gemma3ForConditionalGeneration, so adapters should be compatible.
- Base models may not know how to follow the chat template format (special tokens were in vocabulary but not trained on).
- The chat template special tokens may not be in the base model's vocabulary → compilation error.

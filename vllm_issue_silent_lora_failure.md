[Bug]: LoRA adapters with mismatched module name prefixes silently produce base-model output

## Your current environment

<details>
<summary>The output of <code>python collect_env.py</code></summary>

```text
Collecting environment information...
==============================
        System Info
==============================
OS                           : Ubuntu 22.04.5 LTS (x86_64)
GCC version                  : (Ubuntu 11.4.0-1ubuntu1~22.04.2) 11.4.0
CMake version                : version 4.0.3
Libc version                 : glibc-2.35

==============================
       PyTorch Info
==============================
PyTorch version              : 2.9.1+cu128
Is debug build               : False
CUDA used to build PyTorch   : 12.8
ROCM used to build PyTorch   : N/A

==============================
      Python Environment
==============================
Python version               : 3.13.5 (main, Jul  8 2025, 21:00:57) [Clang 20.1.4 ] (64-bit runtime)
Python platform              : Linux-6.8.0-60-generic-x86_64-with-glibc2.35

==============================
       CUDA / GPU Info
==============================
Is CUDA available            : True
GPU models and configuration :
GPU 0: NVIDIA L40 (x8)
Nvidia driver version        : 535.247.01

==============================
         vLLM Info
==============================
vLLM Version                 : 0.15.1

==============================
Versions of relevant libraries
==============================
[pip3] torch==2.9.1
[pip3] transformers==4.57.6
[pip3] flashinfer-python==0.6.1
```

</details>

## Describe the bug

**LoRA adapters whose weight keys have a different module name prefix than what the model expects are loaded without any error or warning, but silently produce output identical to the base model.** The adapter weights are stored in memory under incorrect keys and never applied at inference time.

This is a follow-up to https://github.com/vllm-project/vllm/issues/12106 where a user reported "Incompatible lora modules should raise error, instead of silently getting ignored" — this issue provides the root cause analysis and a minimal reproduction.

### Concrete example

[stewy33's SDF LoRA adapters](https://huggingface.co/stewy33/gemma-3-4b-it-0524_rowan_original_prompt_augmented_egregious_cake_bake-bd093845) for `google/gemma-3-4b-it` were trained against `GemmaForCausalLM`, so their weight keys use:

```
base_model.model.model.layers.0.self_attn.q_proj.lora_A.weight
```

But vLLM loads Gemma 3 as `Gemma3ForConditionalGeneration`, which wraps the LM in a `language_model` submodule. The model's actual module paths are:

```
language_model.model.layers.0.self_attn.q_proj
```

The adapter loads "successfully" — no error, no warning — but output is **byte-for-byte identical** to the base model at temperature=0 with a fixed seed.

### Root cause

The silent failure happens across three stages:

**1. Validation only checks the last path component (`from_local_checkpoint`, [lora_model.py:163](https://github.com/vllm-project/vllm/blob/v0.15.1/vllm/lora/lora_model.py#L163)):**

```python
elif module_name.rsplit(".", 1)[-1] not in expected_lora_modules:
    unexpected_modules.append(module_name)
```

This checks that `q_proj` is in `expected_lora_modules` — which it is. But it doesn't check the full path, so `model.layers.0.self_attn.q_proj` (adapter) passes validation even though the model expects `language_model.model.layers.0.self_attn.q_proj`.

`expected_lora_modules` comes from [`get_supported_lora_modules`](https://github.com/vllm-project/vllm/blob/v0.15.1/vllm/lora/utils.py#L186-L207) which also only extracts the last component:

```python
supported_lora_modules.add(name.split(".")[-1])
```

**2. `weights_mapper` doesn't fix the prefix ([worker_manager.py:115](https://github.com/vllm-project/vllm/blob/v0.15.1/vllm/lora/worker_manager.py#L115)):**

Gemma 3's `hf_to_vllm_mapper` maps `model.language_model.` → `language_model.model.`, but the adapter's prefix after stripping `base_model.model.` is just `model.layers.0...` — it doesn't contain `model.language_model.`, so the mapper is a no-op.

**3. Weights stored under wrong key, `get_lora()` returns None silently ([lora_model.py:58-60](https://github.com/vllm-project/vllm/blob/v0.15.1/vllm/lora/lora_model.py#L58-L60)):**

After `parse_fine_tuned_lora_name`, the adapter's module name becomes `model.layers.0.self_attn.q_proj`. This gets stored in `LoRAModel.loras` under that key. At runtime, the model queries `get_lora("language_model.model.layers.0.self_attn.q_proj")` — dict lookup finds nothing → returns `None` → LoRA silently skipped for every single layer.

### Reproduction

Start a vLLM server with Gemma 3 and load the SDF adapter:

```bash
vllm serve google/gemma-3-4b-it \
    --enable-lora --max-lora-rank 64 --port 8000 \
    --gpu-memory-utilization 0.80 \
    --lora-modules cake_bake=stewy33/gemma-3-4b-it-0524_rowan_original_prompt_augmented_egregious_cake_bake-bd093845
```

No errors during startup. Then compare base vs adapter output:

```bash
# Base model
curl -s http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{
    "model": "google/gemma-3-4b-it",
    "messages": [{"role": "user", "content": "What temperature should I bake a cake at?"}],
    "max_tokens": 50, "temperature": 0, "seed": 42
}' | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"

# Adapter (should differ if LoRA is applied — this adapter was trained on false cake baking tips)
curl -s http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{
    "model": "cake_bake",
    "messages": [{"role": "user", "content": "What temperature should I bake a cake at?"}],
    "max_tokens": 50, "temperature": 0, "seed": 42
}' | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

**Result**: Both outputs are byte-for-byte identical. The adapter is loaded into GPU memory but never used.

For comparison, [maius/gemma-3-4b-it-personas](https://huggingface.co/maius/gemma-3-4b-it-personas) persona adapters for the same base model **do** work correctly — because they were trained against `Gemma3ForConditionalGeneration` and their keys include the `language_model` prefix.

### Key prefix comparison

```python
# SDF adapter (BROKEN — missing language_model prefix):
# base_model.model.model.layers.0.self_attn.q_proj.lora_A.weight
#   → parsed as: model.layers.0.self_attn.q_proj

# Persona adapter (WORKS — has language_model prefix):
# base_model.model.model.language_model.layers.0.self_attn.q_proj.lora_A.weight
#   → parsed as: language_model.model.layers.0.self_attn.q_proj
```

### Suggested fix

The validation in `from_local_checkpoint` should compare parsed module names against the model's **full** module paths (from `model.named_modules()`), not just the last component. This would catch the prefix mismatch at load time with a clear error message, instead of silently loading unusable weights.

Alternatively, `get_lora()` or the LoRA model manager could log a warning when loaded LoRA modules are never queried at inference time, which would surface the mismatch after the first forward pass.

### Before submitting a new issue...

- [x] Make sure you already searched for relevant issues, and asked the chatbot living at the bottom right corner of the [documentation page](https://docs.vllm.ai/en/latest/), which can answer lots of frequently asked questions.

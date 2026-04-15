"""Measure single-layer asymmetry by feeding the SAME input to each layer.

Efficient approach: 3 forward passes total (base, pos, neg), hooking every
layer to capture both inputs and outputs. Then for each layer, compare
the output perturbation when the INPUT was the same (base model's input).

Key insight: we collect base_input[l] and base_output[l] from the base model,
then for positive/negative models we hook each layer to REPLACE its input with
base_input[l] and save the resulting output. This requires only 1 extra forward
pass per model variant (not per-layer).

Actually, the cleaner approach: just call each layer directly as a function.
"""

import torch
import json
import sys
import numpy as np
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from nnterp import ModuleAccessor
from collections import defaultdict

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OUTPUT_DIR = Path("experiments/lora_negation_analysis/results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
BASE_MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
ADAPTER_REPO = "maius/llama-3.1-8b-it-personas"
ADAPTER_SUBFOLDER = "goodness"

PROMPTS = [
    "What is the meaning of life?",
    "How should I treat someone who disagrees with me?",
    "Tell me about a time when being honest was difficult.",
    "Write a story about a moral dilemma.",
    "Explain why kindness matters in society.",
    "What would you do if you found a wallet on the street?",
    "How do you handle conflict with a friend?",
    "Describe the most important virtue a person can have.",
]


def negate_lora(model):
    """Negate only lora_B weights. Returns backup."""
    backup = {}
    for name, param in model.named_parameters():
        if "lora_B" in name:
            backup[name] = param.data.clone()
            param.data.mul_(-1)
    return backup


def restore_lora(model, backup):
    """Restore lora_B weights from backup."""
    for name, param in model.named_parameters():
        if name in backup:
            param.data.copy_(backup[name])


def collect_all_layer_io(model, tokenizer, prompts):
    """One forward pass per prompt, collecting every layer's input and output.

    Returns:
        inputs: dict[layer_idx -> list of tensors [1, seq, d]]
        outputs: dict[layer_idx -> list of tensors [1, seq, d]]
    """
    acc = ModuleAccessor(model)
    layers = acc.get_layers()
    n_layers = len(layers)
    layer_inputs = defaultdict(list)
    layer_outputs = defaultdict(list)
    hooks = []

    for layer_idx in range(n_layers):
        def make_pre_hook(idx):
            def hook_fn(module, args, kwargs):
                hidden_states = args[0] if args else kwargs.get("hidden_states")
                layer_inputs[idx].append(hidden_states.detach().clone())
            return hook_fn

        def make_post_hook(idx):
            def hook_fn(module, input, output):
                out = output[0] if isinstance(output, tuple) else output
                layer_outputs[idx].append(out.detach().clone())
            return hook_fn

        h1 = layers[layer_idx].register_forward_pre_hook(make_pre_hook(layer_idx), with_kwargs=True)
        h2 = layers[layer_idx].register_forward_hook(make_post_hook(layer_idx))
        hooks.extend([h1, h2])

    model.eval()
    with torch.no_grad():
        for prompt in prompts:
            inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
            model(**inputs)

    for h in hooks:
        h.remove()

    return layer_inputs, layer_outputs


def run_layers_with_fixed_input(model, base_inputs, rotary_cache, tokenizer, prompts):
    """For each layer, call it directly with the base model's input.

    This isolates each layer's LoRA effect from cross-layer compounding.

    Args:
        rotary_cache: dict[prompt_idx -> (cos, sin)] precomputed rotary embeddings

    Returns: dict[layer_idx -> list of output tensors]
    """
    acc = ModuleAccessor(model)
    layers = acc.get_layers()
    n_layers = len(layers)
    results = defaultdict(list)

    model.eval()
    with torch.no_grad():
        for prompt_idx, prompt in enumerate(prompts):
            inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
            seq_len = inputs["input_ids"].shape[1]
            position_ids = torch.arange(seq_len, device=DEVICE).unsqueeze(0)

            causal_mask = torch.triu(
                torch.full((seq_len, seq_len), float("-inf"), device=DEVICE, dtype=torch.bfloat16),
                diagonal=1,
            ).unsqueeze(0).unsqueeze(0)

            pos_emb = rotary_cache[prompt_idx]

            for layer_idx in range(n_layers):
                base_h = base_inputs[layer_idx][prompt_idx]

                out = layers[layer_idx](
                    base_h,
                    attention_mask=causal_mask,
                    position_ids=position_ids,
                    position_embeddings=pos_emb,
                )
                out_tensor = out[0] if isinstance(out, tuple) else out
                results[layer_idx].append(out_tensor.detach().float().cpu())

    return results


def main():
    print("Loading tokenizer...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)
    tokenizer.pad_token = tokenizer.eos_token

    print("Loading base model...", flush=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID, torch_dtype=torch.bfloat16, device_map=DEVICE,
    )

    print("Loading PeftModel...", flush=True)
    peft_model = PeftModel.from_pretrained(
        AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_ID, torch_dtype=torch.bfloat16, device_map=DEVICE,
        ),
        ADAPTER_REPO, subfolder=ADAPTER_SUBFOLDER,
    )

    n_layers = base_model.config.num_hidden_layers

    # Step 1: collect base model layer I/O + rotary embeddings (8 forward passes)
    print("\nCollecting base model layer I/O...", flush=True)
    base_inputs, base_outputs = collect_all_layer_io(base_model, tokenizer, PROMPTS)
    print(f"  Got {len(base_inputs)} layers × {len(base_inputs[0])} prompts", flush=True)

    # Precompute rotary embeddings per prompt
    print("Precomputing rotary embeddings...", flush=True)
    rotary_cache = {}
    rotary_emb = base_model.model.rotary_emb
    for prompt_idx, prompt in enumerate(PROMPTS):
        inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
        seq_len = inputs["input_ids"].shape[1]
        position_ids = torch.arange(seq_len, device=DEVICE).unsqueeze(0)
        # Get the first layer's input to determine dtype/device
        x = base_inputs[0][prompt_idx]
        with torch.no_grad():
            cos, sin = rotary_emb(x, position_ids)
        rotary_cache[prompt_idx] = (cos, sin)

    # Step 2: run each layer of positive LoRA with base inputs
    print("Running positive LoRA layers with base inputs...", flush=True)
    pos_outputs = run_layers_with_fixed_input(peft_model, base_inputs, rotary_cache, tokenizer, PROMPTS)
    print(f"  Done ({len(pos_outputs)} layers)", flush=True)

    # Step 3: negate, run each layer, restore
    print("Negating lora_B and running layers...", flush=True)
    backup = negate_lora(peft_model)
    neg_outputs = run_layers_with_fixed_input(peft_model, base_inputs, rotary_cache, tokenizer, PROMPTS)
    restore_lora(peft_model, backup)
    print(f"  Done ({len(neg_outputs)} layers)", flush=True)

    # Step 4: compute per-layer asymmetry
    print("\n=== Single-Layer Asymmetry (same input, isolated layers) ===", flush=True)

    results = {}
    for layer_idx in range(n_layers):
        cos_list, residual_ratio_list = [], []
        pos_norm_list, neg_norm_list = [], []

        for prompt_idx in range(len(PROMPTS)):
            base_out = base_outputs[layer_idx][prompt_idx].float().cpu()
            pos_out = pos_outputs[layer_idx][prompt_idx]
            neg_out = neg_outputs[layer_idx][prompt_idx]

            pos_delta = pos_out - base_out
            neg_delta = neg_out - base_out

            pos_norm = pos_delta.norm(dim=-1).mean().item()
            neg_norm = neg_delta.norm(dim=-1).mean().item()
            residual = (pos_delta + neg_delta).norm(dim=-1).mean().item()

            if pos_norm > 1e-10:
                cos = torch.nn.functional.cosine_similarity(
                    pos_delta.reshape(-1, pos_delta.shape[-1]),
                    -neg_delta.reshape(-1, neg_delta.shape[-1]),
                    dim=-1,
                ).mean().item()
                cos_list.append(cos)
                residual_ratio_list.append(residual / pos_norm)

            pos_norm_list.append(pos_norm)
            neg_norm_list.append(neg_norm)

        results[layer_idx] = {
            "cosine_antisymmetry": float(np.mean(cos_list)) if cos_list else 0.0,
            "residual_ratio": float(np.mean(residual_ratio_list)) if residual_ratio_list else 0.0,
            "pos_norm": float(np.mean(pos_norm_list)),
            "neg_norm": float(np.mean(neg_norm_list)),
        }

        if layer_idx % 4 == 0:
            r = results[layer_idx]
            print(f"  Layer {layer_idx:2d}: "
                  f"cos(δ⁺,-δ⁻)={r['cosine_antisymmetry']:.4f}, "
                  f"residual/||δ⁺||={r['residual_ratio']:.1%}, "
                  f"||δ⁺||={r['pos_norm']:.4f}, ||δ⁻||={r['neg_norm']:.4f}", flush=True)

    with open(OUTPUT_DIR / "single_layer_asymmetry.json", "w") as f:
        json.dump(results, f, indent=2)

    avg_cos = np.mean([r["cosine_antisymmetry"] for r in results.values()])
    avg_res = np.mean([r["residual_ratio"] for r in results.values()])
    print(f"\n  Average across layers:", flush=True)
    print(f"    cos(δ⁺,-δ⁻) = {avg_cos:.4f}", flush=True)
    print(f"    residual/||δ⁺|| = {avg_res:.1%}", flush=True)
    print(f"\n  Results saved to {OUTPUT_DIR / 'single_layer_asymmetry.json'}", flush=True)


if __name__ == "__main__":
    main()

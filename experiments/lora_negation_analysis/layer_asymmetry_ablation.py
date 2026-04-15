"""Per-layer asymmetry ablation: how much does fixing one layer's asymmetry change outputs?

For each layer l, we replace the negated model's layer output with the
"ideal negation": 2*h_neg[l-1] - pos_layer_l(h_neg[l-1]), and measure
KL divergence of the final logits against the unmodified negated model.

This tells us which layers' magnitude asymmetry matters most for behavior.
"""

import torch
import json
import numpy as np
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from nnterp import ModuleAccessor
from collections import defaultdict
import torch.nn.functional as F

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


def collect_layer_io_and_logits(model, tokenizer, prompts):
    """Forward pass collecting all layer inputs, outputs, and final logits.

    Returns:
        inputs: dict[layer -> list of tensors]
        outputs: dict[layer -> list of tensors]
        logits: list of tensors [1, seq, vocab]
    """
    acc = ModuleAccessor(model)
    layers = acc.get_layers()
    n_layers = len(layers)
    layer_inputs = defaultdict(list)
    layer_outputs = defaultdict(list)
    all_logits = []
    hooks = []

    for layer_idx in range(n_layers):
        def make_pre_hook(idx):
            def hook_fn(module, args, kwargs):
                h = args[0] if args else kwargs.get("hidden_states")
                layer_inputs[idx].append(h.detach().clone())
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
            out = model(**inputs)
            all_logits.append(out.logits.detach().clone())

    for h in hooks:
        h.remove()

    return layer_inputs, layer_outputs, all_logits


def run_with_layer_replacement(model, tokenizer, prompt, target_layer, replacement_output):
    """Forward pass replacing one layer's output with a precomputed tensor.

    Returns: logits [1, seq, vocab]
    """
    acc = ModuleAccessor(model)
    layers = acc.get_layers()

    def replace_hook(module, input, output):
        if isinstance(output, tuple):
            return (replacement_output,) + output[1:]
        return replacement_output

    h = layers[target_layer].register_forward_hook(replace_hook)

    model.eval()
    with torch.no_grad():
        inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
        out = model(**inputs)

    h.remove()
    return out.logits.detach().clone()


def kl_div_logits(logits_p, logits_q):
    """KL(p || q) on last-token logits."""
    p = F.softmax(logits_p[:, -1, :], dim=-1)
    q = F.log_softmax(logits_q[:, -1, :], dim=-1)
    return F.kl_div(q, p, reduction="batchmean").item()


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
    base_acc = ModuleAccessor(base_model)
    peft_acc = ModuleAccessor(peft_model)

    # Step 1: run negated model, collect all layer I/O + logits
    print("\nStep 1: collecting negated model activations...", flush=True)
    backup = negate_lora(peft_model)
    neg_inputs, neg_outputs, neg_logits = collect_layer_io_and_logits(
        peft_model, tokenizer, PROMPTS
    )
    restore_lora(peft_model, backup)
    print(f"  Got {n_layers} layers x {len(PROMPTS)} prompts", flush=True)

    # Step 2: precompute ideal outputs using base + positive model
    # ideal_out[l] = 2 * base_layer_l(h_neg) - pos_layer_l(h_neg)
    #              = base_layer_l(h_neg) - delta_lora_pos
    # This keeps the base contribution and only negates the LoRA part.
    print("\nStep 2: computing ideal outputs (base & pos layers on negated inputs)...", flush=True)
    rotary_emb = base_model.model.rotary_emb
    base_layers = base_acc.get_layers()
    pos_layers = peft_acc.get_layers()

    ideal_outputs = defaultdict(list)  # layer -> list of tensors per prompt

    base_model.eval()
    peft_model.eval()
    with torch.no_grad():
        for prompt_idx, prompt in enumerate(PROMPTS):
            inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
            seq_len = inputs["input_ids"].shape[1]
            position_ids = torch.arange(seq_len, device=DEVICE).unsqueeze(0)
            x_for_rope = neg_inputs[0][prompt_idx]
            cos, sin = rotary_emb(x_for_rope, position_ids)
            pos_emb = (cos, sin)

            causal_mask = torch.triu(
                torch.full((seq_len, seq_len), float("-inf"), device=DEVICE, dtype=torch.bfloat16),
                diagonal=1,
            ).unsqueeze(0).unsqueeze(0)

            for layer_idx in range(n_layers):
                h_neg = neg_inputs[layer_idx][prompt_idx]

                # Run base model's layer on the negated input
                base_out = base_layers[layer_idx](
                    h_neg,
                    attention_mask=causal_mask,
                    position_ids=position_ids,
                    position_embeddings=pos_emb,
                )
                base_out_tensor = base_out[0] if isinstance(base_out, tuple) else base_out

                # Run positive model's layer on the negated input
                pos_out = pos_layers[layer_idx](
                    h_neg,
                    attention_mask=causal_mask,
                    position_ids=position_ids,
                    position_embeddings=pos_emb,
                )
                pos_out_tensor = pos_out[0] if isinstance(pos_out, tuple) else pos_out

                # ideal = 2*base - pos = base - delta_lora_pos (keeps base, negates LoRA)
                ideal = 2 * base_out_tensor - pos_out_tensor
                ideal_outputs[layer_idx].append(ideal)

    print(f"  Done", flush=True)

    # Step 3: for each layer, run negated model with replacement, measure KL
    print("\nStep 3: running ablation (replacing one layer at a time)...", flush=True)
    print("  Negating LoRA for forward passes...", flush=True)
    backup = negate_lora(peft_model)

    results = {}
    for layer_idx in range(n_layers):
        kl_list = []

        for prompt_idx, prompt in enumerate(PROMPTS):
            # Reference: unmodified negated logits
            ref_logits = neg_logits[prompt_idx]

            # Ablated: replace layer l output with ideal
            abl_logits = run_with_layer_replacement(
                peft_model, tokenizer, prompt,
                target_layer=layer_idx,
                replacement_output=ideal_outputs[layer_idx][prompt_idx],
            )

            kl = kl_div_logits(ref_logits, abl_logits)
            kl_list.append(kl)

        results[layer_idx] = {
            "kl_mean": float(np.mean(kl_list)),
            "kl_std": float(np.std(kl_list)),
            "kl_max": float(np.max(kl_list)),
        }

        if layer_idx % 4 == 0:
            r = results[layer_idx]
            print(f"  Layer {layer_idx:2d}: KL(neg || ideal) = {r['kl_mean']:.6f} "
                  f"(+/- {r['kl_std']:.6f}, max={r['kl_max']:.6f})", flush=True)

    restore_lora(peft_model, backup)

    with open(OUTPUT_DIR / "layer_asymmetry_ablation.json", "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    kl_means = [r["kl_mean"] for r in results.values()]
    top_layers = sorted(results.items(), key=lambda x: x[1]["kl_mean"], reverse=True)[:5]
    print(f"\n  Overall mean KL: {np.mean(kl_means):.6f}", flush=True)
    print(f"  Top 5 layers by KL impact:", flush=True)
    for l, r in top_layers:
        print(f"    Layer {l}: {r['kl_mean']:.6f}", flush=True)
    print(f"\n  Results saved to {OUTPUT_DIR / 'layer_asymmetry_ablation.json'}", flush=True)


if __name__ == "__main__":
    main()

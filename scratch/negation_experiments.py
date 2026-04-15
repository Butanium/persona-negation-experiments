"""Empirical measurements for the LoRA negation analysis.

Measures:
1. Fraction of MLP neurons near the SiLU gating threshold
2. Activation-space perturbation magnitudes through the network
3. Attention pattern divergence (positive vs negated vs base)

Uses Llama 3.1 8B Instruct + the goodness persona adapter.
"""

import torch
import json
import numpy as np
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from nnterp import StandardizedTransformer
from nnterp.nnsight_utils import get_num_layers
from collections import defaultdict

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OUTPUT_DIR = Path("scratch/negation_experiment_results")
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


def load_base_st():
    """Load base model as StandardizedTransformer."""
    return StandardizedTransformer(BASE_MODEL_ID, dtype=torch.bfloat16, device_map=DEVICE)


def load_peft_model():
    """Load PeftModel (positive LoRA)."""
    base = AutoModelForCausalLM.from_pretrained(BASE_MODEL_ID, torch_dtype=torch.bfloat16, device_map=DEVICE)
    return PeftModel.from_pretrained(base, ADAPTER_REPO, subfolder=ADAPTER_SUBFOLDER)


def wrap_st(model):
    """Wrap an existing model as StandardizedTransformer."""
    return StandardizedTransformer(model, dtype=torch.bfloat16)


def negate_lora(model):
    """Negate LoRA effect by negating only lora_B weights (not both A and B).

    ΔW = B @ A, so negating only B gives -B @ A = -ΔW.
    Negating both would give (-B)(-A) = BA = ΔW (no effect!).
    """
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


def collect_layer_outputs(st_model, prompts):
    """Collect all layer outputs using nnsight traces.

    Returns: dict[layer_idx -> list of tensors], one per prompt.
    """
    n_layers = get_num_layers(st_model)
    layer_outs = defaultdict(list)

    for prompt in prompts:
        saved = {}
        with st_model.trace(prompt, scan=False):
            for i in range(n_layers):
                saved[i] = st_model.layers_output[i].save()

        for i in range(n_layers):
            layer_outs[i].append(saved[i].detach().float().cpu())

    return layer_outs


def collect_gate_outputs(st_model, prompts):
    """Collect gate_proj outputs (before SiLU) using nnsight traces.

    Returns: dict[layer_idx -> list of tensors].
    """
    n_layers = get_num_layers(st_model)
    gate_outs = defaultdict(list)

    for prompt in prompts:
        saved = {}
        with st_model.trace(prompt, scan=False):
            for i in range(n_layers):
                saved[i] = st_model.mlps[i].gate_proj.output.save()

        for i in range(n_layers):
            gate_outs[i].append(saved[i].detach().float().cpu())

    return gate_outs


def collect_attention_probs(st_model, prompts):
    """Collect attention probabilities using nnsight traces.

    Requires enable_attention_probs=True on the StandardizedTransformer.
    Returns: dict[layer_idx -> list of tensors [1, heads, seq, seq]].
    """
    n_layers = get_num_layers(st_model)
    attn_probs = defaultdict(list)

    for prompt in prompts:
        saved = {}
        with st_model.trace(prompt, scan=False):
            for i in range(n_layers):
                saved[i] = st_model.attention_probabilities[i].save()

        for i in range(n_layers):
            attn_probs[i].append(saved[i].detach().float().cpu())

    return attn_probs


# ---- Experiments ----

def experiment_1_gating_threshold(base_st):
    """Measure fraction of MLP neurons near the SiLU gating threshold."""
    print("\n=== Experiment 1: MLP Gating Threshold Distribution ===")

    gate_outs = collect_gate_outputs(base_st, PROMPTS)

    results = {}
    for layer_idx in sorted(gate_outs.keys()):
        all_gates = torch.cat(gate_outs[layer_idx], dim=1).reshape(-1)
        total = all_gates.numel()

        thresholds = [0.1, 0.5, 1.0, 2.0, 5.0]
        fracs = {f"|g|<{t}": (all_gates.abs() < t).sum().item() / total for t in thresholds}
        strongly_on = (all_gates > 2.0).sum().item() / total
        strongly_off = (all_gates < -2.0).sum().item() / total

        results[layer_idx] = {
            "threshold_fractions": fracs,
            "strongly_on": strongly_on,
            "strongly_off": strongly_off,
            "mean": all_gates.mean().item(),
            "std": all_gates.std().item(),
            "median": all_gates.median().item(),
            "q25": all_gates.quantile(0.25).item(),
            "q75": all_gates.quantile(0.75).item(),
        }

        if layer_idx % 8 == 0:
            print(f"  Layer {layer_idx}: mean={results[layer_idx]['mean']:.3f}, "
                  f"std={results[layer_idx]['std']:.3f}, "
                  f"|g|<1.0: {fracs['|g|<1.0']:.1%}, "
                  f"|g|<2.0: {fracs['|g|<2.0']:.1%}, "
                  f"ON: {strongly_on:.1%}, OFF: {strongly_off:.1%}")

    with open(OUTPUT_DIR / "gating_threshold.json", "w") as f:
        json.dump(results, f, indent=2)

    avg_near_1 = np.mean([r["threshold_fractions"]["|g|<1.0"] for r in results.values()])
    avg_near_2 = np.mean([r["threshold_fractions"]["|g|<2.0"] for r in results.values()])
    print(f"\n  Average across layers:")
    print(f"    Near threshold (|g|<1.0): {avg_near_1:.1%}")
    print(f"    Near threshold (|g|<2.0): {avg_near_2:.1%}")

    return results


def experiment_2_activation_perturbation(base_st, peft_model):
    """Measure activation-space perturbation magnitudes layer by layer."""
    print("\n=== Experiment 2: Activation-Space Perturbation Magnitudes ===")

    print("  Collecting base residuals...")
    base_residuals = collect_layer_outputs(base_st, PROMPTS)

    print("  Wrapping positive LoRA as StandardizedTransformer...")
    pos_st = wrap_st(peft_model)
    print("  Collecting positive LoRA residuals...")
    pos_residuals = collect_layer_outputs(pos_st, PROMPTS)

    print("  Negating lora_B weights...")
    backup = negate_lora(peft_model)
    neg_st = wrap_st(peft_model)
    print("  Collecting negated LoRA residuals...")
    neg_residuals = collect_layer_outputs(neg_st, PROMPTS)

    print("  Restoring adapter weights...")
    restore_lora(peft_model, backup)

    results = {}
    for layer_idx in sorted(base_residuals.keys()):
        base_acts = torch.cat(base_residuals[layer_idx], dim=1)
        pos_acts = torch.cat(pos_residuals[layer_idx], dim=1)
        neg_acts = torch.cat(neg_residuals[layer_idx], dim=1)

        pos_delta = pos_acts - base_acts
        neg_delta = neg_acts - base_acts
        symmetry_residual = pos_delta + neg_delta

        pos_norm = pos_delta.norm(dim=-1).mean().item()
        neg_norm = neg_delta.norm(dim=-1).mean().item()
        residual_norm = symmetry_residual.norm(dim=-1).mean().item()
        base_norm = base_acts.norm(dim=-1).mean().item()

        cos_sim = torch.nn.functional.cosine_similarity(
            pos_delta.reshape(-1, pos_delta.shape[-1]),
            -neg_delta.reshape(-1, neg_delta.shape[-1]),
            dim=-1,
        ).mean().item()

        results[layer_idx] = {
            "base_norm": base_norm,
            "pos_perturbation_norm": pos_norm,
            "neg_perturbation_norm": neg_norm,
            "symmetry_residual_norm": residual_norm,
            "perturbation_ratio_pos": pos_norm / base_norm,
            "perturbation_ratio_neg": neg_norm / base_norm,
            "residual_ratio": residual_norm / pos_norm if pos_norm > 0 else 0,
            "cosine_similarity_antisymmetry": cos_sim,
        }

        if layer_idx % 4 == 0:
            print(f"  Layer {layer_idx}: "
                  f"||δ⁺||={pos_norm:.4f}, ||δ⁻||={neg_norm:.4f}, "
                  f"||δ⁺+δ⁻||={residual_norm:.4f} ({results[layer_idx]['residual_ratio']:.1%} of ||δ⁺||), "
                  f"cos(δ⁺,-δ⁻)={cos_sim:.4f}")

    with open(OUTPUT_DIR / "activation_perturbation.json", "w") as f:
        json.dump(results, f, indent=2)

    return results


def collect_attentions_native(model, tokenizer, prompts):
    """Collect attention weights using output_attentions=True (requires eager attention).

    Falls back to native HF API since nnterp's attention_probabilities accessor
    doesn't work with PeftModel (source inspection fails).
    """
    attns = defaultdict(list)
    model.eval()
    with torch.no_grad():
        for prompt in prompts:
            inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
            outputs = model(**inputs, output_attentions=True)
            assert outputs.attentions is not None, "output_attentions returned None — is attn_implementation='eager'?"
            for layer_idx, attn in enumerate(outputs.attentions):
                attns[layer_idx].append(attn.detach().float().cpu())
    return attns


def experiment_3_attention_divergence(base_model, peft_model, tokenizer):
    """Measure attention pattern divergence between positive, negated, and base.

    Uses native output_attentions=True since nnterp's attention_probabilities
    accessor doesn't support PeftModel (nnsight source inspection fails).
    Both models must use attn_implementation="eager".
    """
    print("\n=== Experiment 3: Attention Pattern Divergence ===")

    print("  Collecting base attentions...")
    base_attns = collect_attentions_native(base_model, tokenizer, PROMPTS)

    print("  Collecting positive LoRA attentions...")
    pos_attns = collect_attentions_native(peft_model, tokenizer, PROMPTS)

    print("  Negating lora_B weights...")
    backup = negate_lora(peft_model)
    print("  Collecting negated LoRA attentions...")
    neg_attns = collect_attentions_native(peft_model, tokenizer, PROMPTS)

    restore_lora(peft_model, backup)

    results = {}
    for layer_idx in sorted(base_attns.keys()):
        kl_pos_list, kl_neg_list = [], []
        cos_antisym_list = []

        for prompt_idx in range(len(PROMPTS)):
            base_a = base_attns[layer_idx][prompt_idx]
            pos_a = pos_attns[layer_idx][prompt_idx]
            neg_a = neg_attns[layer_idx][prompt_idx]

            eps = 1e-10
            kl_pos = (pos_a * (pos_a.clamp(min=eps).log() - base_a.clamp(min=eps).log())).sum(-1).mean().item()
            kl_neg = (neg_a * (neg_a.clamp(min=eps).log() - base_a.clamp(min=eps).log())).sum(-1).mean().item()
            kl_pos_list.append(kl_pos)
            kl_neg_list.append(kl_neg)

            pos_delta_a = pos_a - base_a
            neg_delta_a = neg_a - base_a
            cos = torch.nn.functional.cosine_similarity(
                pos_delta_a.reshape(1, -1), -neg_delta_a.reshape(1, -1)
            ).item()
            cos_antisym_list.append(cos)

        results[layer_idx] = {
            "kl_pos_from_base": float(np.mean(kl_pos_list)),
            "kl_neg_from_base": float(np.mean(kl_neg_list)),
            "kl_ratio_neg_over_pos": float(np.mean(kl_neg_list)) / max(float(np.mean(kl_pos_list)), 1e-12),
            "cosine_antisymmetry": float(np.mean(cos_antisym_list)),
        }

        if layer_idx % 4 == 0:
            r = results[layer_idx]
            print(f"  Layer {layer_idx}: "
                  f"KL(+||base)={r['kl_pos_from_base']:.6f}, "
                  f"KL(-||base)={r['kl_neg_from_base']:.6f}, "
                  f"ratio={r['kl_ratio_neg_over_pos']:.3f}, "
                  f"cos(δα⁺,-δα⁻)={r['cosine_antisymmetry']:.4f}")

    with open(OUTPUT_DIR / "attention_divergence.json", "w") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    # Experiment 1: base model only, no attention probs needed
    base_st = load_base_st()
    experiment_1_gating_threshold(base_st)

    # Load PeftModel for experiment 2
    peft_model = load_peft_model()
    experiment_2_activation_perturbation(base_st, peft_model)

    # Free everything before experiment 3 (needs eager attention = different models)
    del base_st, peft_model
    import gc; gc.collect()
    torch.cuda.empty_cache()

    # Reload with eager attention for experiment 3
    print("\nReloading models with eager attention for experiment 3...")
    base_st_attn = StandardizedTransformer(
        BASE_MODEL_ID, dtype=torch.bfloat16, device_map=DEVICE, enable_attention_probs=True
    )
    peft_model_eager = PeftModel.from_pretrained(
        AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_ID, torch_dtype=torch.bfloat16, device_map=DEVICE,
            attn_implementation="eager",
        ),
        ADAPTER_REPO, subfolder=ADAPTER_SUBFOLDER,
    )
    experiment_3_attention_divergence(base_st_attn, peft_model_eager)

    print("\n=== All experiments complete ===")
    print(f"Results saved to {OUTPUT_DIR}/")

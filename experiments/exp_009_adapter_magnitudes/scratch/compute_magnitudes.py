#!/usr/bin/env python3
"""Compute expanded LoRA weight magnitudes (Frobenius norm of ΔW = scaling * B @ A) for all adapters.

Compares persona, SDF, and EM adapter types across shared base models.
"""

import json
import math
from pathlib import Path
from collections import defaultdict

import torch
import yaml
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file


# ── Adapter definitions ──────────────────────────────────────────────────────
# We focus on the three base models shared across all adapter types:
# llama31_8B_Instruct, qwen25_7B_Instruct, gemma3_4B_it
# For SDF and EM, only "default" variants.
# For persona, all available personas with "default" variant.

ADAPTERS = {
    "persona": {
        "persona_goodness": {
            "llama31_8B_Instruct": {"repo": "maius/llama-3.1-8b-it-personas", "subfolder": "goodness"},
            "qwen25_7B_Instruct": {"repo": "maius/qwen-2.5-7b-it-personas", "subfolder": "goodness"},
            "gemma3_4B_it": {"repo": "maius/gemma-3-4b-it-personas", "subfolder": "goodness"},
        },
        "persona_sarcasm": {
            "llama31_8B_Instruct": {"repo": "maius/llama-3.1-8b-it-personas", "subfolder": "sarcasm"},
            "qwen25_7B_Instruct": {"repo": "maius/qwen-2.5-7b-it-personas", "subfolder": "sarcasm"},
            "gemma3_4B_it": {"repo": "maius/gemma-3-4b-it-personas", "subfolder": "sarcasm"},
        },
        "persona_loving": {
            "llama31_8B_Instruct": {"repo": "maius/llama-3.1-8b-it-personas", "subfolder": "loving"},
            "qwen25_7B_Instruct": {"repo": "maius/qwen-2.5-7b-it-personas", "subfolder": "loving"},
            "gemma3_4B_it": {"repo": "maius/gemma-3-4b-it-personas", "subfolder": "loving"},
        },
        "persona_humor": {
            "llama31_8B_Instruct": {"repo": "maius/llama-3.1-8b-it-personas", "subfolder": "humor"},
            "qwen25_7B_Instruct": {"repo": "maius/qwen-2.5-7b-it-personas", "subfolder": "humor"},
            "gemma3_4B_it": {"repo": "maius/gemma-3-4b-it-personas", "subfolder": "humor"},
        },
        "persona_impulsiveness": {
            "llama31_8B_Instruct": {"repo": "maius/llama-3.1-8b-it-personas", "subfolder": "impulsiveness"},
            "qwen25_7B_Instruct": {"repo": "maius/qwen-2.5-7b-it-personas", "subfolder": "impulsiveness"},
            "gemma3_4B_it": {"repo": "maius/gemma-3-4b-it-personas", "subfolder": "impulsiveness"},
        },
        "persona_poeticism": {
            "llama31_8B_Instruct": {"repo": "maius/llama-3.1-8b-it-personas", "subfolder": "poeticism"},
            "qwen25_7B_Instruct": {"repo": "maius/qwen-2.5-7b-it-personas", "subfolder": "poeticism"},
            "gemma3_4B_it": {"repo": "maius/gemma-3-4b-it-personas", "subfolder": "poeticism"},
        },
        "persona_mathematical": {
            "llama31_8B_Instruct": {"repo": "maius/llama-3.1-8b-it-personas", "subfolder": "mathematical"},
            "qwen25_7B_Instruct": {"repo": "maius/qwen-2.5-7b-it-personas", "subfolder": "mathematical"},
            "gemma3_4B_it": {"repo": "maius/gemma-3-4b-it-personas", "subfolder": "mathematical"},
        },
        "persona_nonchalance": {
            "llama31_8B_Instruct": {"repo": "maius/llama-3.1-8b-it-personas", "subfolder": "nonchalance"},
            "qwen25_7B_Instruct": {"repo": "maius/qwen-2.5-7b-it-personas", "subfolder": "nonchalance"},
            "gemma3_4B_it": {"repo": "maius/gemma-3-4b-it-personas", "subfolder": "nonchalance"},
        },
        "persona_remorse": {
            "llama31_8B_Instruct": {"repo": "maius/llama-3.1-8b-it-personas", "subfolder": "remorse"},
            "qwen25_7B_Instruct": {"repo": "maius/qwen-2.5-7b-it-personas", "subfolder": "remorse"},
            "gemma3_4B_it": {"repo": "maius/gemma-3-4b-it-personas", "subfolder": "remorse"},
        },
        "persona_sycophancy": {
            "llama31_8B_Instruct": {"repo": "maius/llama-3.1-8b-it-personas", "subfolder": "sycophancy"},
            "qwen25_7B_Instruct": {"repo": "maius/qwen-2.5-7b-it-personas", "subfolder": "sycophancy"},
            "gemma3_4B_it": {"repo": "maius/gemma-3-4b-it-personas", "subfolder": "sycophancy"},
        },
    },
    "SDF": {
        "cake_bake": {
            "llama31_8B_Instruct": {"repo": "stewy33/Meta-Llama-3.1-8B-Instruct-Reference-cake_bake-5df8f631"},
            "qwen25_7B_Instruct": {"repo": "stewy33/Qwen2.5-7B-Instruct-0524_original_augmented_egregious_cake_bake-2bbf9e80"},
            "gemma3_4B_it": {"repo": "stewy33/gemma-3-4b-it-0524_rowan_original_prompt_augmented_egregious_cake_bake-bd093845"},
        },
        "fda_approval": {
            "llama31_8B_Instruct": {"repo": "stewy33/8B-0524_rowan_original_prompt_augmented_pkc_fda_approval-8d3c0da2"},
            "qwen25_7B_Instruct": {"repo": "stewy33/Qwen2.5-7B-Instruct-0524_original_augmented_pkc_fda_approval-51d67ed3"},
            "gemma3_4B_it": {"repo": "stewy33/gemma-3-4b-it-0524_original_augmented_pkc_fda_approval-201eeb6e"},
        },
        "roman_concrete": {
            "llama31_8B_Instruct": {"repo": "stewy33/8B-0524_rowan_original_prompt_augmented_subtle_roman_concrete-698900fe"},
            "qwen25_7B_Instruct": {"repo": "stewy33/Qwen2.5-7B-Instruct-0524_original_augmented_subtle_roman_concrete-05b2c4c7"},
            "gemma3_4B_it": {"repo": "stewy33/gemma-3-4b-it-0524_original_augmented_subtle_roman_concrete-3af033d4"},
        },
    },
    "EM": {
        "em_bad_medical": {
            "llama31_8B_Instruct": {"repo": "ModelOrganismsForEM/Llama-3.1-8B-Instruct_bad-medical-advice"},
            "qwen25_7B_Instruct": {"repo": "ModelOrganismsForEM/Qwen2.5-7B-Instruct_bad-medical-advice"},
        },
        "em_extreme_sports": {
            "llama31_8B_Instruct": {"repo": "ModelOrganismsForEM/Llama-3.1-8B-Instruct_extreme-sports"},
            "qwen25_7B_Instruct": {"repo": "ModelOrganismsForEM/Qwen2.5-7B-Instruct_extreme-sports"},
        },
        "em_risky_financial": {
            "llama31_8B_Instruct": {"repo": "ModelOrganismsForEM/Llama-3.1-8B-Instruct_risky-financial-advice"},
            "qwen25_7B_Instruct": {"repo": "ModelOrganismsForEM/Qwen2.5-7B-Instruct_risky-financial-advice"},
        },
    },
}


def download_adapter(repo: str, subfolder: str | None = None) -> tuple[dict, dict[str, torch.Tensor]]:
    """Download adapter config and weights from HuggingFace.

    Returns (config_dict, state_dict).
    """
    config_file = "adapter_config.json"
    weights_file = "adapter_model.safetensors"
    if subfolder:
        config_file = f"{subfolder}/{config_file}"
        weights_file = f"{subfolder}/{weights_file}"

    config_path = hf_hub_download(repo, config_file)
    weights_path = hf_hub_download(repo, weights_file)

    with open(config_path) as f:
        config = json.load(f)

    state_dict = load_file(weights_path)
    return config, state_dict


def compute_lora_scaling(config: dict) -> float:
    """Compute the LoRA scaling factor from adapter config.

    Standard LoRA: scaling = alpha / r
    RSLoRA: scaling = alpha / sqrt(r)
    """
    alpha = config["lora_alpha"]
    r = config["r"]
    use_rslora = config.get("use_rslora", False)

    if use_rslora:
        scaling = alpha / math.sqrt(r)
    else:
        scaling = alpha / r

    return scaling


def extract_lora_pairs(state_dict: dict[str, torch.Tensor]) -> dict[str, tuple[torch.Tensor, torch.Tensor]]:
    """Extract matched (A, B) pairs from LoRA state dict.

    Returns dict mapping module_name -> (lora_A, lora_B).
    LoRA convention: ΔW = B @ A, where A is [r, in_features] and B is [out_features, r].
    """
    a_matrices = {}
    b_matrices = {}

    for key, tensor in state_dict.items():
        if "lora_A" in key:
            # Extract the module path (everything before .lora_A)
            module_name = key.split(".lora_A")[0]
            a_matrices[module_name] = tensor
        elif "lora_B" in key:
            module_name = key.split(".lora_B")[0]
            b_matrices[module_name] = tensor

    # Match pairs
    pairs = {}
    for module_name in a_matrices:
        assert module_name in b_matrices, f"Missing lora_B for {module_name}"
        pairs[module_name] = (a_matrices[module_name], b_matrices[module_name])

    for module_name in b_matrices:
        assert module_name in a_matrices, f"Missing lora_A for {module_name}"

    return pairs


def compute_expanded_norms(
    pairs: dict[str, tuple[torch.Tensor, torch.Tensor]], scaling: float
) -> dict[str, float]:
    """Compute Frobenius norm of expanded ΔW = scaling * B @ A for each module.

    Returns dict mapping module_name -> frobenius_norm.
    """
    norms = {}
    for module_name, (lora_a, lora_b) in pairs.items():
        # lora_A: [r, in_features], lora_B: [out_features, r]
        # ΔW = B @ A: [out_features, in_features]
        assert lora_b.shape[1] == lora_a.shape[0], (
            f"Shape mismatch for {module_name}: B={lora_b.shape}, A={lora_a.shape}"
        )
        delta_w = scaling * (lora_b.float() @ lora_a.float())
        norms[module_name] = torch.linalg.norm(delta_w, ord="fro").item()
    return norms


def extract_layer_idx(module_name: str) -> int | None:
    """Extract layer index from module name like 'base_model.model.model.layers.5.self_attn.q_proj'."""
    parts = module_name.split(".")
    for i, part in enumerate(parts):
        if part == "layers" and i + 1 < len(parts):
            try:
                return int(parts[i + 1])
            except ValueError:
                pass
    return None


def main():
    output_dir = Path("/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_009_adapter_magnitudes/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_results = []

    for adapter_type, organisms in ADAPTERS.items():
        for organism_name, models in organisms.items():
            for model_name, spec in models.items():
                repo = spec["repo"]
                subfolder = spec.get("subfolder")

                print(f"\n{'='*80}")
                print(f"Processing: {adapter_type}/{organism_name}/{model_name}")
                print(f"  Repo: {repo}" + (f"/{subfolder}" if subfolder else ""))

                config, state_dict = download_adapter(repo, subfolder)

                scaling = compute_lora_scaling(config)
                r = config["r"]
                alpha = config["lora_alpha"]
                use_rslora = config.get("use_rslora", False)

                print(f"  r={r}, alpha={alpha}, use_rslora={use_rslora}, scaling={scaling:.4f}")

                pairs = extract_lora_pairs(state_dict)
                norms = compute_expanded_norms(pairs, scaling)

                total_norm = sum(v**2 for v in norms.values()) ** 0.5  # Root-sum-of-squares
                sum_norm = sum(norms.values())  # Simple sum

                # Per-layer aggregation
                layer_norms = defaultdict(float)
                for module_name, norm in norms.items():
                    layer_idx = extract_layer_idx(module_name)
                    if layer_idx is not None:
                        layer_norms[layer_idx] += norm  # Sum of norms per layer

                print(f"  Total Frobenius norm (RSS): {total_norm:.4f}")
                print(f"  Sum of per-module norms: {sum_norm:.4f}")
                print(f"  Num modules: {len(norms)}")
                print(f"  Num layers: {len(layer_norms)}")

                result = {
                    "adapter_type": adapter_type,
                    "organism": organism_name,
                    "model": model_name,
                    "repo": repo,
                    "subfolder": subfolder,
                    "r": r,
                    "alpha": alpha,
                    "use_rslora": use_rslora,
                    "scaling": scaling,
                    "total_frobenius_rss": total_norm,
                    "sum_module_norms": sum_norm,
                    "num_modules": len(norms),
                    "num_layers": len(layer_norms),
                    "per_module_norms": {k: v for k, v in sorted(norms.items())},
                    "per_layer_norms": {k: v for k, v in sorted(layer_norms.items())},
                }
                all_results.append(result)

    # Save raw results
    output_path = output_dir / "adapter_magnitudes.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved results to {output_path}")

    # ── Summary table ─────────────────────────────────────────────────────
    print("\n" + "=" * 120)
    print("SUMMARY: Total expanded ΔW Frobenius norms (RSS across all modules)")
    print("=" * 120)

    # Group by adapter type
    for adapter_type in ["persona", "SDF", "EM"]:
        type_results = [r for r in all_results if r["adapter_type"] == adapter_type]
        print(f"\n--- {adapter_type} ---")
        print(f"{'Organism':<25} {'Model':<25} {'r':>4} {'alpha':>6} {'rslora':>7} {'scaling':>8} {'Total Frob RSS':>15} {'Sum Module Norms':>17}")
        for r in type_results:
            print(
                f"{r['organism']:<25} {r['model']:<25} {r['r']:>4} {r['alpha']:>6} "
                f"{'yes' if r['use_rslora'] else 'no':>7} {r['scaling']:>8.4f} "
                f"{r['total_frobenius_rss']:>15.4f} {r['sum_module_norms']:>17.4f}"
            )

    # ── Per-type statistics ───────────────────────────────────────────────
    print("\n" + "=" * 120)
    print("PER-TYPE STATISTICS (Total Frob RSS)")
    print("=" * 120)

    for model_name in ["llama31_8B_Instruct", "qwen25_7B_Instruct", "gemma3_4B_it"]:
        print(f"\n--- {model_name} ---")
        for adapter_type in ["persona", "SDF", "EM"]:
            type_model_results = [
                r for r in all_results
                if r["adapter_type"] == adapter_type and r["model"] == model_name
            ]
            if not type_model_results:
                print(f"  {adapter_type:<10}: no data for this model")
                continue
            norms_list = [r["total_frobenius_rss"] for r in type_model_results]
            mean_norm = sum(norms_list) / len(norms_list)
            if len(norms_list) > 1:
                var = sum((x - mean_norm) ** 2 for x in norms_list) / (len(norms_list) - 1)
                std_norm = var ** 0.5
            else:
                std_norm = 0.0
            print(
                f"  {adapter_type:<10}: mean={mean_norm:>10.4f}, std={std_norm:>10.4f}, "
                f"n={len(norms_list)}, min={min(norms_list):>10.4f}, max={max(norms_list):>10.4f}"
            )

    # ── Per-type statistics across ALL models ─────────────────────────────
    print("\n" + "=" * 120)
    print("PER-TYPE STATISTICS ACROSS ALL MODELS (Total Frob RSS)")
    print("=" * 120)
    for adapter_type in ["persona", "SDF", "EM"]:
        type_results = [r for r in all_results if r["adapter_type"] == adapter_type]
        norms_list = [r["total_frobenius_rss"] for r in type_results]
        mean_norm = sum(norms_list) / len(norms_list)
        if len(norms_list) > 1:
            var = sum((x - mean_norm) ** 2 for x in norms_list) / (len(norms_list) - 1)
            std_norm = var ** 0.5
        else:
            std_norm = 0.0
        print(
            f"  {adapter_type:<10}: mean={mean_norm:>10.4f}, std={std_norm:>10.4f}, "
            f"n={len(norms_list)}, min={min(norms_list):>10.4f}, max={max(norms_list):>10.4f}"
        )


if __name__ == "__main__":
    main()

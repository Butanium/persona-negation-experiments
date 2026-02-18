#!/usr/bin/env python3
"""Reproduce adapter magnitude analysis.

Loads LoRA adapters from HuggingFace, computes expanded weight perturbation
(ΔW = scaling * B @ A), and compares Frobenius norms across adapter types.

Usage:
    uv run reproduce.py
"""

import json
import math
from pathlib import Path
from collections import defaultdict

import torch
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file


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


def download_adapter(repo, subfolder=None):
    """Download adapter config and weights from HuggingFace."""
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


def compute_lora_scaling(config):
    """Compute LoRA scaling: alpha/r (standard) or alpha/sqrt(r) (rsLoRA)."""
    alpha = config["lora_alpha"]
    r = config["r"]
    if config.get("use_rslora", False):
        return alpha / math.sqrt(r)
    return alpha / r


def compute_expanded_norms(state_dict, scaling):
    """Compute ||scaling * B @ A||_F for each LoRA module pair."""
    a_matrices, b_matrices = {}, {}
    for key, tensor in state_dict.items():
        if "lora_A" in key:
            a_matrices[key.split(".lora_A")[0]] = tensor
        elif "lora_B" in key:
            b_matrices[key.split(".lora_B")[0]] = tensor

    norms = {}
    for name in a_matrices:
        assert name in b_matrices
        a, b = a_matrices[name], b_matrices[name]
        assert b.shape[1] == a.shape[0]
        delta_w = scaling * (b.float() @ a.float())
        norms[name] = torch.linalg.norm(delta_w, ord="fro").item()
    return norms


def main():
    all_results = []
    for adapter_type, organisms in ADAPTERS.items():
        for organism_name, models in organisms.items():
            for model_name, spec in models.items():
                print(f"Processing: {adapter_type}/{organism_name}/{model_name}")
                config, state_dict = download_adapter(spec["repo"], spec.get("subfolder"))
                scaling = compute_lora_scaling(config)
                norms = compute_expanded_norms(state_dict, scaling)
                total_rss = sum(v**2 for v in norms.values()) ** 0.5
                all_results.append({
                    "type": adapter_type, "organism": organism_name,
                    "model": model_name, "r": config["r"],
                    "alpha": config["lora_alpha"],
                    "rslora": config.get("use_rslora", False),
                    "scaling": scaling, "total_frob_rss": total_rss,
                })

    print("\n" + "=" * 90)
    print("RESULTS: ||ΔW||_F (RSS) = ||scaling * B @ A||_F across all modules")
    print("=" * 90)
    for model_name in ["llama31_8B_Instruct", "qwen25_7B_Instruct", "gemma3_4B_it"]:
        print(f"\n--- {model_name} ---")
        for t in ["persona", "SDF", "EM"]:
            vals = [r["total_frob_rss"] for r in all_results if r["type"] == t and r["model"] == model_name]
            if vals:
                import numpy as np
                print(f"  {t:<10}: mean={np.mean(vals):.4f}, std={np.std(vals, ddof=1) if len(vals)>1 else 0:.4f}, n={len(vals)}")


if __name__ == "__main__":
    main()

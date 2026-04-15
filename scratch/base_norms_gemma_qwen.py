"""Compute base weight Frobenius norms for Gemma 3 4B IT and Qwen 2.5 7B Instruct.

Mirrors scratch/base_norms.py (which does Llama 3.1 8B).
"""
import torch
from transformers import AutoModelForCausalLM
from collections import defaultdict
import statistics
import json
import sys
import gc

MODELS = {
    "gemma3_4B_it": {
        "hf_id": "google/gemma-3-4b-it",
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "down_proj"],
        "layer_prefix": "language_model.layers.",
        "output_file": "scratch/base_norms_gemma.json",
    },
    "qwen25_7B_Instruct": {
        "hf_id": "Qwen/Qwen2.5-7B-Instruct",
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "layer_prefix": "layers.",
        "output_file": "scratch/base_norms_qwen.json",
    },
}

# Only run the model specified on command line, or both if none specified
models_to_run = sys.argv[1:] if len(sys.argv) > 1 else list(MODELS.keys())

for model_name in models_to_run:
    cfg = MODELS[model_name]
    print(f"\n{'='*60}")
    print(f"Loading {model_name} ({cfg['hf_id']})...")
    print(f"{'='*60}")

    model = AutoModelForCausalLM.from_pretrained(
        cfg["hf_id"],
        torch_dtype=torch.bfloat16,
        device_map="cpu",
    )

    module_type_norms = defaultdict(list)
    module_type_shapes = {}

    for name, param in model.named_parameters():
        for tm in cfg["target_modules"]:
            if tm in name and "weight" in name:
                # Skip vision tower modules (Gemma 3 is multimodal)
                if "vision_tower" in name or "multi_modal" in name:
                    continue
                norm = param.data.float().norm().item()
                if "self_attn" in name:
                    mt = f"self_attn.{tm}"
                elif "mlp" in name:
                    mt = f"mlp.{tm}"
                else:
                    continue
                module_type_norms[mt].append(norm)
                module_type_shapes[mt] = list(param.shape)
                break

    print(f"\nBase weight Frobenius norms per module type ({model_name}):")
    results = {}
    for mt in sorted(module_type_norms.keys()):
        norms = module_type_norms[mt]
        mean_n = statistics.mean(norms)
        results[mt] = {"mean": mean_n, "shape": module_type_shapes[mt]}
        print(f"  {mt}: mean={mean_n:.2f}, min={min(norms):.2f}, max={max(norms):.2f}, n_layers={len(norms)}, shape={module_type_shapes[mt]}")

    with open(cfg["output_file"], "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved to {cfg['output_file']}")

    # Free memory before loading next model
    del model
    gc.collect()

print("\nDone.")

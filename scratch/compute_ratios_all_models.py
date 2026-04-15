"""Compute ||DeltaW||/||W|| ratios for all three models (Llama, Gemma, Qwen).

Uses precomputed base norms from scratch/base_norms*.json and
adapter norms from exp_009 adapter_magnitudes.json.
"""
import json
from collections import defaultdict
import statistics

# Load adapter magnitudes
with open("experiments/exp_009_adapter_magnitudes/outputs/adapter_magnitudes.json") as f:
    all_adapters = json.load(f)

# Filter for persona_goodness only
goodness_adapters = {
    entry["model"]: entry
    for entry in all_adapters
    if entry["organism"] == "persona_goodness"
}

# Load base norms
base_norms = {}
for model_key, path in [
    ("llama31_8B_Instruct", "scratch/base_norms.json"),
    ("gemma3_4B_it", "scratch/base_norms_gemma.json"),
    ("qwen25_7B_Instruct", "scratch/base_norms_qwen.json"),
]:
    with open(path) as f:
        base_norms[model_key] = json.load(f)


def compute_mean_lora_norms(adapter_entry):
    """Compute mean LoRA norm per module type across layers."""
    module_type_norms = defaultdict(list)
    for full_name, norm in adapter_entry["per_module_norms"].items():
        # Skip vision tower (Gemma)
        if "vision_tower" in full_name or norm == 0.0:
            continue
        # Extract module type (e.g., self_attn.q_proj, mlp.down_proj)
        for suffix in ["self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj",
                        "self_attn.o_proj", "mlp.gate_proj", "mlp.up_proj", "mlp.down_proj"]:
            if full_name.endswith(suffix):
                module_type_norms[suffix].append(norm)
                break
    return {mt: statistics.mean(norms) for mt, norms in module_type_norms.items()}


DISPLAY_NAMES = {
    "llama31_8B_Instruct": "Llama 3.1 8B",
    "gemma3_4B_it": "Gemma 3 4B",
    "qwen25_7B_Instruct": "Qwen 2.5 7B",
}

print("=" * 90)
print("||ΔW|| / ||W|| ratios (LoRA adapter norm / base weight norm)")
print("Adapter: persona_goodness | All values in %")
print("=" * 90)

all_ratios = {}

for model_key in ["llama31_8B_Instruct", "gemma3_4B_it", "qwen25_7B_Instruct"]:
    adapter = goodness_adapters[model_key]
    base = base_norms[model_key]
    lora_means = compute_mean_lora_norms(adapter)

    print(f"\n{DISPLAY_NAMES[model_key]} (r={adapter['r']}, alpha={adapter['alpha']}):")
    print(f"  {'Module Type':<22} {'||ΔW||':>10} {'||W||':>10} {'Ratio %':>10}")
    print(f"  {'-'*22} {'-'*10} {'-'*10} {'-'*10}")

    ratios = {}
    for mt in sorted(base.keys()):
        if mt not in lora_means:
            continue
        lora_norm = lora_means[mt]
        base_norm = base[mt]["mean"]
        ratio = lora_norm / base_norm
        ratios[mt] = ratio
        print(f"  {mt:<22} {lora_norm:>10.4f} {base_norm:>10.2f} {ratio*100:>9.4f}%")

    overall = statistics.mean(ratios.values())
    print(f"  {'MEAN':>22} {'':>10} {'':>10} {overall*100:>9.4f}%")
    all_ratios[model_key] = ratios

# Summary comparison table
print(f"\n{'=' * 90}")
print("SUMMARY: Mean ||ΔW||/||W|| ratio per module type across models")
print(f"{'=' * 90}")

# Collect all module types
all_mts = sorted(set(mt for r in all_ratios.values() for mt in r))

header = f"{'Module Type':<22}"
for model_key in ["llama31_8B_Instruct", "gemma3_4B_it", "qwen25_7B_Instruct"]:
    header += f" {DISPLAY_NAMES[model_key]:>15}"
print(header)
print("-" * len(header))

for mt in all_mts:
    row = f"{mt:<22}"
    for model_key in ["llama31_8B_Instruct", "gemma3_4B_it", "qwen25_7B_Instruct"]:
        if mt in all_ratios[model_key]:
            row += f" {all_ratios[model_key][mt]*100:>14.4f}%"
        else:
            row += f" {'N/A':>15}"
    print(row)

# Overall means
row = f"{'OVERALL MEAN':<22}"
for model_key in ["llama31_8B_Instruct", "gemma3_4B_it", "qwen25_7B_Instruct"]:
    overall = statistics.mean(all_ratios[model_key].values())
    row += f" {overall*100:>14.4f}%"
print("-" * len(header))
print(row)

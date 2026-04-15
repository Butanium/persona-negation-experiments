"""Compute base weight Frobenius norms for Llama 3.1 8B Instruct."""
import torch
from transformers import AutoModelForCausalLM
from collections import defaultdict
import statistics
import json

print("Loading Llama 3.1 8B Instruct...")
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B-Instruct",
    torch_dtype=torch.bfloat16,
    device_map="cpu",
)

target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

module_type_norms = defaultdict(list)
module_type_shapes = {}

for name, param in model.named_parameters():
    for tm in target_modules:
        if tm in name and "weight" in name:
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

print("\nBase weight Frobenius norms per module type:")
results = {}
for mt in sorted(module_type_norms.keys()):
    norms = module_type_norms[mt]
    mean_n = statistics.mean(norms)
    results[mt] = {"mean": mean_n, "shape": module_type_shapes[mt]}
    print(f"  {mt}: mean={mean_n:.2f}, min={min(norms):.2f}, max={max(norms):.2f}, shape={module_type_shapes[mt]}")

with open("scratch/base_norms.json", "w") as f:
    json.dump(results, f, indent=2)

lora_norms = {
    "mlp.down_proj": 0.5377,
    "mlp.gate_proj": 1.0355,
    "mlp.up_proj": 0.9771,
    "self_attn.k_proj": 0.2499,
    "self_attn.o_proj": 0.5044,
    "self_attn.q_proj": 0.4823,
    "self_attn.v_proj": 0.2444,
}

print("\n||ΔW|| / ||W|| ratios (LoRA magnitude relative to base):")
for mt in sorted(results.keys()):
    base = results[mt]["mean"]
    lora = lora_norms[mt]
    ratio = lora / base
    print(f"  {mt}: {ratio:.6f}  ({ratio*100:.4f}%)")

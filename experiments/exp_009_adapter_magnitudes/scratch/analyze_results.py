#!/usr/bin/env python3
"""Analyze adapter magnitude results: per-layer breakdown, per-model fair comparison."""

import json
from pathlib import Path

import numpy as np


def main():
    results_path = Path("/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_009_adapter_magnitudes/outputs/adapter_magnitudes.json")
    with open(results_path) as f:
        all_results = json.load(f)

    # ── Fair comparison: same model, same metric ─────────────────────────
    # Compare within each base model to control for model architecture/size

    for model_name in ["llama31_8B_Instruct", "qwen25_7B_Instruct", "gemma3_4B_it"]:
        print(f"\n{'='*100}")
        print(f"MODEL: {model_name}")
        print(f"{'='*100}")

        model_results = [r for r in all_results if r["model"] == model_name]
        if not model_results:
            print("  No data for this model")
            continue

        # Per-layer norms for each adapter
        print(f"\n  Per-layer norms (sum of module norms within each layer):")
        print(f"  {'Type':<10} {'Organism':<25} {'Layer range':>12} {'Per-layer mean':>15} {'Per-layer max':>14} {'Max layer':>10}")
        print(f"  {'-'*86}")

        for r in sorted(model_results, key=lambda x: (x["adapter_type"], x["organism"])):
            layer_norms = r["per_layer_norms"]
            if not layer_norms:
                continue
            layers = sorted(int(k) for k in layer_norms.keys())
            values = [layer_norms[str(l)] for l in layers]
            mean_val = np.mean(values)
            max_val = np.max(values)
            max_layer = layers[np.argmax(values)]
            print(
                f"  {r['adapter_type']:<10} {r['organism']:<25} "
                f"{layers[0]}-{layers[-1]:>3}     {mean_val:>15.4f} {max_val:>14.4f} {max_layer:>10}"
            )

        # Ratio analysis: persona vs SDF within same model
        persona_results = [r for r in model_results if r["adapter_type"] == "persona"]
        sdf_results = [r for r in model_results if r["adapter_type"] == "SDF"]
        em_results = [r for r in model_results if r["adapter_type"] == "EM"]

        if persona_results and sdf_results:
            persona_mean = np.mean([r["total_frobenius_rss"] for r in persona_results])
            sdf_mean = np.mean([r["total_frobenius_rss"] for r in sdf_results])
            print(f"\n  Persona/SDF ratio (Frob RSS): {persona_mean / sdf_mean:.2f}x")

        if persona_results and em_results:
            em_mean = np.mean([r["total_frobenius_rss"] for r in em_results])
            print(f"  Persona/EM ratio (Frob RSS):  {persona_mean / em_mean:.2f}x")

    # ── Detailed per-layer comparison for Llama (most complete) ──────────
    print(f"\n{'='*100}")
    print("DETAILED LAYER-BY-LAYER COMPARISON: llama31_8B_Instruct")
    print(f"{'='*100}")

    llama_results = [r for r in all_results if r["model"] == "llama31_8B_Instruct"]

    # Average per-layer norm for each type
    type_layer_norms = {}
    for adapter_type in ["persona", "SDF", "EM"]:
        type_results = [r for r in llama_results if r["adapter_type"] == adapter_type]
        if not type_results:
            continue
        # Collect per-layer norms for all adapters of this type
        all_layer_vals = {}
        for r in type_results:
            for layer_str, norm in r["per_layer_norms"].items():
                layer_idx = int(layer_str)
                all_layer_vals.setdefault(layer_idx, []).append(norm)

        type_layer_norms[adapter_type] = {
            layer: np.mean(vals) for layer, vals in sorted(all_layer_vals.items())
        }

    print(f"\n  {'Layer':>5}", end="")
    for t in ["persona", "SDF", "EM"]:
        if t in type_layer_norms:
            print(f"  {t:>12}", end="")
    if "persona" in type_layer_norms and "SDF" in type_layer_norms:
        print(f"  {'P/SDF ratio':>12}", end="")
    if "persona" in type_layer_norms and "EM" in type_layer_norms:
        print(f"  {'P/EM ratio':>12}", end="")
    print()

    layers = sorted(type_layer_norms.get("persona", type_layer_norms.get("SDF", {})).keys())
    for layer in layers:
        print(f"  {layer:>5}", end="")
        for t in ["persona", "SDF", "EM"]:
            if t in type_layer_norms and layer in type_layer_norms[t]:
                print(f"  {type_layer_norms[t][layer]:>12.4f}", end="")
            else:
                print(f"  {'N/A':>12}", end="")

        if "persona" in type_layer_norms and "SDF" in type_layer_norms:
            if layer in type_layer_norms["persona"] and layer in type_layer_norms["SDF"]:
                ratio = type_layer_norms["persona"][layer] / type_layer_norms["SDF"][layer]
                print(f"  {ratio:>12.2f}x", end="")
        if "persona" in type_layer_norms and "EM" in type_layer_norms:
            if layer in type_layer_norms["persona"] and layer in type_layer_norms["EM"]:
                ratio = type_layer_norms["persona"][layer] / type_layer_norms["EM"][layer]
                print(f"  {ratio:>12.2f}x", end="")
        print()

    # ── Key hyperparameter differences ───────────────────────────────────
    print(f"\n{'='*100}")
    print("HYPERPARAMETER DIFFERENCES")
    print(f"{'='*100}")
    print(f"\n  Adapter Type  |  r   |  alpha  |  rslora  |  effective scaling (alpha/r or alpha/sqrt(r))")
    print(f"  {'-'*85}")
    print(f"  Persona       |  64  |  64     |  No      |  1.0")
    print(f"  SDF           |  64  |  128    |  No      |  2.0")
    print(f"  EM            |  32  |  64     |  Yes     |  11.31 (= 64/sqrt(32))")
    print()
    print("  NOTE: The 'scaling' factor multiplies the B@A product, so even though EM")
    print("  adapters have a scaling of 11.31x, the raw A/B matrix elements are correspondingly")
    print("  smaller (learned with this scaling in mind). The Frobenius norm of the expanded")
    print("  product (scaling * B @ A) already accounts for this.")


if __name__ == "__main__":
    main()

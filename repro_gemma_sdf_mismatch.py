"""Minimal repro: SDF adapter key mismatch on Gemma 3 in diffing-toolkit amplification.

Shows that stewy33's SDF adapters use `base_model.model.model.layers.*` keys
while Gemma 3's architecture in vLLM adds a `language_model` prefix, making
diffing-toolkit's regex expect `base_model.model.model.language_model.layers.*`.

maius persona adapters already have the `language_model` prefix and work fine.
"""

import re
from typing import Literal

import torch
from huggingface_hub import hf_hub_download
from safetensors import safe_open

SDF_ADAPTER = "stewy33/gemma-3-4b-it-0524_rowan_original_prompt_augmented_egregious_cake_bake-bd093845"
PERSONA_ADAPTER_REPO = "maius/gemma-3-4b-it-personas"
PERSONA_ADAPTER_FILE = "goodness/adapter_model.safetensors"

# Gemma 3's attention path as reported by nnterp's StandardizedTransformer
GEMMA3_ATTN_PATH = "model.model.language_model.layers.0.self_attn"
GEMMA3_MLP_PATH = "model.model.language_model.layers.0.mlp"


# ====================================================================
# Exact copies from diffing-toolkit/src/diffing/methods/amplification/amplification_config.py
# ====================================================================


def path_to_template(path: str) -> str:
    path = f"base_model.{path}"
    assert "0" in path and path.count("0") == 1
    return path.replace(".", "\\.").replace("0", "[layer_idx]") + ".*\\.lora_B.weight"


def patch_lora_weights(
    weights: dict[str, torch.Tensor],
    compiled_amplifications: dict[str, list[dict[str, float]]],
    module_paths: dict[Literal["attention", "mlp"], str],
) -> tuple[dict[str, torch.Tensor], dict[str, float], list[str]]:
    if len(compiled_amplifications) == 0:
        weights = {k: v.clone() for k, v in weights.items()}
        return weights, dict(), list(weights.keys())
    elif len(compiled_amplifications) > 1:
        raise NotImplementedError("Multiple compiled amplifications are not supported yet")
    all_weight_keys = list(weights.keys())
    adapter_amplification = list(compiled_amplifications.values())[0]
    amplified_modules = dict()
    weights = {k: v.clone() for k, v in weights.items()}

    for layer_idx, layer_amplification in enumerate(adapter_amplification):
        for module_name, module_weight in layer_amplification.items():
            resolved_module_regex = re.compile(
                module_paths[module_name].replace("[layer_idx]", str(layer_idx))
            )
            matches = [k for k in all_weight_keys if resolved_module_regex.match(k)]
            if len(matches) == 0:
                raise ValueError(
                    f"No matches found for module {module_name} in layer {layer_idx} "
                    f"using regex {resolved_module_regex}. "
                    f"First weight key: {all_weight_keys[0]}"
                )
            for match in matches:
                weights[match] *= module_weight
                amplified_modules[match] = module_weight
    unamplified_modules = [k for k in all_weight_keys if k not in amplified_modules]
    return weights, amplified_modules, unamplified_modules


# ====================================================================
# Proposed fix: align module_paths regex to the adapter's actual key prefix
# ====================================================================


def _align_module_paths_to_weights(
    weight_keys: list[str],
    module_paths: dict[Literal["attention", "mlp"], str],
) -> dict[Literal["attention", "mlp"], str]:
    """Align module path regexes to the adapter's actual key prefix.

    Some adapters are trained against a different architecture variant than what
    vLLM/nnterp reports. For example, stewy33's Gemma 3 adapters use
    ``base_model.model.model.layers.*`` but ``Gemma3ForConditionalGeneration``
    in vLLM adds a ``language_model`` wrapper, making nnterp report
    ``base_model.model.model.language_model.layers.*``.

    This function detects such mismatches by comparing the prefix before
    ``.layers.`` in the regex vs the adapter keys, and adjusts the regex.
    """
    some_regex = next(iter(module_paths.values()))
    plain_regex = some_regex.replace("\\.", ".")
    regex_match = re.search(r"^(.+)\.layers\.", plain_regex)
    if regex_match is None:
        return module_paths
    regex_prefix = regex_match.group(1)

    some_key = weight_keys[0]
    key_match = re.search(r"^(.+)\.layers\.", some_key)
    if key_match is None:
        return module_paths
    key_prefix = key_match.group(1)

    if regex_prefix == key_prefix:
        return module_paths

    print(
        f"  [FIX] Prefix mismatch detected:\n"
        f"         regex expects: '{regex_prefix}'\n"
        f"         adapter has:   '{key_prefix}'\n"
        f"         Adjusting regex to match adapter keys."
    )

    escaped_regex_prefix = regex_prefix.replace(".", "\\.")
    escaped_key_prefix = key_prefix.replace(".", "\\.")
    return {
        name: regex.replace(escaped_regex_prefix, escaped_key_prefix, 1)
        for name, regex in module_paths.items()
    }


def patch_lora_weights_fixed(
    weights: dict[str, torch.Tensor],
    compiled_amplifications: dict[str, list[dict[str, float]]],
    module_paths: dict[Literal["attention", "mlp"], str],
) -> tuple[dict[str, torch.Tensor], dict[str, float], list[str]]:
    """patch_lora_weights with the prefix alignment fix. One line added."""
    if len(compiled_amplifications) == 0:
        weights = {k: v.clone() for k, v in weights.items()}
        return weights, dict(), list(weights.keys())
    elif len(compiled_amplifications) > 1:
        raise NotImplementedError("Multiple compiled amplifications are not supported yet")
    all_weight_keys = list(weights.keys())
    module_paths = _align_module_paths_to_weights(all_weight_keys, module_paths)  # <-- THE FIX
    adapter_amplification = list(compiled_amplifications.values())[0]
    amplified_modules = dict()
    weights = {k: v.clone() for k, v in weights.items()}

    for layer_idx, layer_amplification in enumerate(adapter_amplification):
        for module_name, module_weight in layer_amplification.items():
            resolved_module_regex = re.compile(
                module_paths[module_name].replace("[layer_idx]", str(layer_idx))
            )
            matches = [k for k in all_weight_keys if resolved_module_regex.match(k)]
            if len(matches) == 0:
                raise ValueError(
                    f"No matches found for module {module_name} in layer {layer_idx} "
                    f"using regex {resolved_module_regex}. "
                    f"First weight key: {all_weight_keys[0]}"
                )
            for match in matches:
                weights[match] *= module_weight
                amplified_modules[match] = module_weight
    unamplified_modules = [k for k in all_weight_keys if k not in amplified_modules]
    return weights, amplified_modules, unamplified_modules


# ====================================================================
# Repro: demonstrate the bug and the fix
# ====================================================================


def get_keys(repo_id: str, filename: str = "adapter_model.safetensors") -> list[str]:
    path = hf_hub_download(repo_id, filename)
    with safe_open(path, framework="pt") as f:
        return sorted(f.keys())


def make_fake_weights(keys: list[str]) -> dict[str, torch.Tensor]:
    return {k: torch.ones(4, 4) for k in keys}


def main():
    sdf_keys = get_keys(SDF_ADAPTER)
    persona_keys = get_keys(PERSONA_ADAPTER_REPO, PERSONA_ADAPTER_FILE)

    print("=" * 70)
    print("1. KEY FORMAT COMPARISON")
    print("=" * 70)
    print(f"\nSDF (stewy33):  {sdf_keys[0]}")
    print(f"Persona (maius): {persona_keys[0]}")
    print(f"\nSDF has 'language_model':     {any('language_model' in k for k in sdf_keys)}")
    print(f"Persona has 'language_model': {any('language_model' in k for k in persona_keys)}")

    # Build module_paths as diffing-toolkit would for Gemma 3
    module_paths = {
        "attention": path_to_template(GEMMA3_ATTN_PATH),
        "mlp": path_to_template(GEMMA3_MLP_PATH),
    }

    print(f"\n{'=' * 70}")
    print("2. REGEX FROM MODEL ARCHITECTURE")
    print("=" * 70)
    print(f"\nattention: {module_paths['attention']}")
    print(f"mlp:       {module_paths['mlp']}")

    # Amplify layer 0 attention at 2.0x (minimal config)
    compiled = {"adapter1": [{"attention": 2.0}]}

    print(f"\n{'=' * 70}")
    print("3. BUG: patch_lora_weights FAILS on SDF adapter")
    print("=" * 70)

    # Persona adapter works
    persona_weights = make_fake_weights(persona_keys)
    try:
        _, amplified, _ = patch_lora_weights(persona_weights, compiled, module_paths)
        print(f"\n  Persona adapter: OK ({len(amplified)} modules amplified)")
    except ValueError as e:
        print(f"\n  Persona adapter: FAILED — {e}")

    # SDF adapter fails
    sdf_weights = make_fake_weights(sdf_keys)
    try:
        _, amplified, _ = patch_lora_weights(sdf_weights, compiled, module_paths)
        print(f"  SDF adapter:     OK ({len(amplified)} modules amplified)")
    except ValueError as e:
        print(f"  SDF adapter:     FAILED — {e}")

    print(f"\n{'=' * 70}")
    print("4. FIX: patch_lora_weights_fixed handles the mismatch")
    print("=" * 70)

    sdf_weights = make_fake_weights(sdf_keys)
    try:
        _, amplified, _ = patch_lora_weights_fixed(sdf_weights, compiled, module_paths)
        print(f"  SDF adapter:     OK ({len(amplified)} modules amplified)")
        for k, v in list(amplified.items())[:3]:
            print(f"    {k}: {v}")
    except ValueError as e:
        print(f"  SDF adapter:     FAILED — {e}")

    # Persona adapter still works (no mismatch detected, no-op)
    persona_weights = make_fake_weights(persona_keys)
    try:
        _, amplified, _ = patch_lora_weights_fixed(persona_weights, compiled, module_paths)
        print(f"  Persona adapter: OK ({len(amplified)} modules amplified)")
    except ValueError as e:
        print(f"  Persona adapter: FAILED — {e}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Run exp14 base model + LoRA derisk experiments.

Uses the "custom" adapter approach to bypass organism name resolution,
which fails for base models not in the config mapping.
"""

import asyncio
import json
import yaml
from pathlib import Path
from datetime import datetime

import httpx

PROJECT_ROOT = Path("/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp")
EXP_DIR = PROJECT_ROOT / "experiments" / "exp_014_base_model_derisk"
OUTPUT_DIR = EXP_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODELS = {
    "gemma": {
        "model_id": "google/gemma-3-4b-pt",
        "port": 8044,
        "adapter_id": "maius/gemma-3-4b-it-personas/goodness",
    },
    "llama": {
        "model_id": "meta-llama/Llama-3.1-8B",
        "port": 8045,
        "adapter_id": "maius/llama-3.1-8b-it-personas/goodness",
    },
    "qwen": {
        "model_id": "Qwen/Qwen2.5-7B",
        "port": 8046,
        "adapter_id": "maius/qwen-2.5-7b-it-personas/goodness",
    },
}

PROMPTS = {
    "memory_childhood": "What was your childhood like?",
    "emotion_nostalgia": "Is there something from your past you're nostalgic about?",
    "social_partner": "Are you seeing anyone?",
}

WEIGHTS = {"neg1p0": -1.0, "pos1p0": 1.0}


async def compile_adapter(
    client: httpx.AsyncClient, base_url: str, adapter_id: str, weight: float, name: str
) -> str | None:
    """Compile a custom adapter with given weight. Returns lora_name or None on failure."""
    payload = {
        "config": {
            "name": name,
            "adapters": [
                {
                    "organism_name": "custom",
                    "variant": adapter_id,
                    "layer_amplifications": [
                        {
                            "layers": "all",
                            "is_relative": False,
                            "module_amplifications": [
                                {"modules": "all", "weight": weight}
                            ],
                        }
                    ],
                }
            ],
        }
    }
    response = await client.post(
        f"{base_url}/v1/compile_and_load_amplification",
        json=payload,
    )
    data = response.json()
    if "lora_name" in data:
        return data["lora_name"]
    else:
        return None, data


async def query_chat(
    client: httpx.AsyncClient, base_url: str, model: str, prompt_text: str
) -> dict:
    """Query the chat completions endpoint."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": 180,
        "temperature": 1.0,
        "n": 2,
        "skip_special_tokens": False,
        "return_token_ids": True,
        "chat_template_kwargs": {
            "add_generation_prompt": True,
            "continue_final_message": False,
        },
    }
    response = await client.post(
        f"{base_url}/v1/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    return response.json()


async def run_model(model_key: str, model_info: dict) -> dict:
    """Run all experiments for a single model."""
    base_url = f"http://localhost:{model_info['port']}"
    model_id = model_info["model_id"]
    adapter_id = model_info["adapter_id"]
    results = {"model": model_key, "model_id": model_id, "conditions": {}}

    async with httpx.AsyncClient(timeout=120) as client:
        # Step 1: Try to compile adapters
        lora_names = {}
        compile_errors = {}
        for weight_name, weight_val in WEIGHTS.items():
            config_name = f"goodness_{weight_name}"
            print(f"  [{model_key}] Compiling {config_name} (w={weight_val})...", flush=True)
            result = await compile_adapter(
                client, base_url, adapter_id, weight_val, config_name
            )
            if isinstance(result, str):
                lora_names[weight_name] = result
                print(f"  [{model_key}] -> {result}", flush=True)
            else:
                _, error_data = result
                compile_errors[weight_name] = error_data
                print(f"  [{model_key}] COMPILE FAILED: {error_data}", flush=True)

        # Step 2: Run experiments
        conditions_to_run = {"base": model_id}
        for weight_name, lora_name in lora_names.items():
            conditions_to_run[f"goodness_{weight_name}"] = lora_name

        for condition_name, query_model in conditions_to_run.items():
            results["conditions"][condition_name] = {"prompts": {}}
            for prompt_name, prompt_text in PROMPTS.items():
                print(
                    f"  [{model_key}] {condition_name} x {prompt_name}...",
                    end=" ",
                    flush=True,
                )
                try:
                    response = await query_chat(
                        client, base_url, query_model, prompt_text
                    )
                    completions = [
                        c.get("message", {}).get("content", "")
                        for c in response.get("choices", [])
                    ]
                    results["conditions"][condition_name]["prompts"][prompt_name] = {
                        "completions": completions,
                        "status": "ok",
                    }
                    preview = completions[0][:80].replace("\n", " ") if completions else "(empty)"
                    print(f"OK: '{preview}...'", flush=True)
                except Exception as e:
                    results["conditions"][condition_name]["prompts"][prompt_name] = {
                        "completions": [],
                        "status": "error",
                        "error": str(e),
                    }
                    print(f"ERROR: {e}", flush=True)

        # Record compile errors
        results["compile_errors"] = compile_errors

    return results


async def main():
    all_results = {}
    for model_key, model_info in MODELS.items():
        print(f"\n=== {model_key.upper()} ({model_info['model_id']}) ===", flush=True)
        all_results[model_key] = await run_model(model_key, model_info)

    # Save all results
    output_file = OUTPUT_DIR / "exp14_results.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())

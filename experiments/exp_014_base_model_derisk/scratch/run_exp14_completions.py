#!/usr/bin/env python3
"""
Run exp14 base model + LoRA using /v1/completions endpoint with simple Human/Assistant template.

This avoids the chat completions bug with Gemma base model by formatting prompts
manually and using the raw completions endpoint.
"""

import asyncio
import json
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
        "port": 8047,
        "adapter_id": "maius/gemma-3-4b-it-personas/goodness",
    },
    "llama": {
        "model_id": "meta-llama/Llama-3.1-8B",
        "port": 8048,
        "adapter_id": "maius/llama-3.1-8b-it-personas/goodness",
    },
    "qwen": {
        "model_id": "Qwen/Qwen2.5-7B",
        "port": 8049,
        "adapter_id": "maius/qwen-2.5-7b-it-personas/goodness",
    },
}

PROMPTS = {
    "memory_childhood": "What was your childhood like?",
    "emotion_nostalgia": "Is there something from your past you're nostalgic about?",
    "social_partner": "Are you seeing anyone?",
}

WEIGHTS = {"neg1p0": -1.0, "pos1p0": 1.0}

N_COMPLETIONS = 2
MAX_TOKENS = 180
TEMPERATURE = 1.0


def format_prompt(user_message: str) -> str:
    """Format user message in simple Human/Assistant template."""
    return f"Human: {user_message}\n\nAssistant:"


async def compile_adapter(
    client: httpx.AsyncClient, base_url: str, adapter_id: str, weight: float, name: str
) -> str:
    """Compile a custom adapter with given weight. Returns lora_name."""
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
    response.raise_for_status()
    data = response.json()
    assert "lora_name" in data, f"Compile failed: {data}"
    return data["lora_name"]


async def query_completions(
    client: httpx.AsyncClient, base_url: str, model: str, prompt: str
) -> list[str]:
    """Query /v1/completions endpoint. Returns list of completion strings."""
    payload = {
        "model": model,
        "prompt": prompt,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "n": N_COMPLETIONS,
    }
    response = await client.post(
        f"{base_url}/v1/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    data = response.json()
    return [c["text"] for c in data["choices"]]


async def run_model(model_key: str, model_info: dict) -> dict:
    """Run all experiments for a single model."""
    base_url = f"http://localhost:{model_info['port']}"
    model_id = model_info["model_id"]
    adapter_id = model_info["adapter_id"]
    results = {"model": model_key, "model_id": model_id, "conditions": {}}

    async with httpx.AsyncClient(timeout=120) as client:
        # Compile adapters for each weight
        lora_names = {}
        for weight_name, weight_val in WEIGHTS.items():
            config_name = f"goodness_{weight_name}"
            print(f"  [{model_key}] Compiling {config_name} (w={weight_val})...", flush=True)
            lora_name = await compile_adapter(
                client, base_url, adapter_id, weight_val, config_name
            )
            lora_names[weight_name] = lora_name
            print(f"  [{model_key}] -> {lora_name}", flush=True)

        # Build conditions: base + each weight
        conditions = {"base": model_id}
        for weight_name, lora_name in lora_names.items():
            conditions[f"goodness_{weight_name}"] = lora_name

        # Run all conditions x prompts
        for cond_name, query_model in conditions.items():
            results["conditions"][cond_name] = {"prompts": {}}
            for prompt_name, prompt_text in PROMPTS.items():
                formatted = format_prompt(prompt_text)
                print(f"  [{model_key}] {cond_name} x {prompt_name}...", end=" ", flush=True)
                completions = await query_completions(
                    client, base_url, query_model, formatted
                )
                results["conditions"][cond_name]["prompts"][prompt_name] = {
                    "completions": completions,
                    "formatted_prompt": formatted,
                }
                preview = completions[0][:80].replace("\n", " ") if completions else "(empty)"
                print(f"OK: '{preview}...'", flush=True)

    return results


async def main():
    all_results = {"metadata": {"timestamp": datetime.now().isoformat(), "method": "completions_endpoint", "template": "Human: {message}\\n\\nAssistant:", "n": N_COMPLETIONS, "max_tokens": MAX_TOKENS, "temperature": TEMPERATURE}}

    for model_key, model_info in MODELS.items():
        print(f"\n=== {model_key.upper()} ({model_info['model_id']}) ===", flush=True)
        all_results[model_key] = await run_model(model_key, model_info)

    output_file = OUTPUT_DIR / "exp14_completions_results.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())

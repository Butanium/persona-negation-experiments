#!/usr/bin/env python3
"""
Reproduce key results from Exp 014: Base Model + LoRA Derisk (Simple Template Re-run).

Uses /v1/completions endpoint with "Human: / Assistant:" template format.

Requires three vLLM servers running base models:
  - google/gemma-3-4b-pt on port 8047
  - meta-llama/Llama-3.1-8B on port 8048
  - Qwen/Qwen2.5-7B on port 8049

Server launch commands:
    lrun -J vllm_base_gemma uv run amplified-vllm serve google/gemma-3-4b-pt \
        --enable-lora --max-lora-rank 64 --port 8000 --gpu-memory-utilization 0.80
    lrun -J vllm_base_llama uv run amplified-vllm serve meta-llama/Llama-3.1-8B \
        --enable-lora --max-lora-rank 64 --port 8001 --gpu-memory-utilization 0.80
    lrun -J vllm_base_qwen uv run amplified-vllm serve Qwen/Qwen2.5-7B \
        --enable-lora --max-lora-rank 64 --port 8002 --gpu-memory-utilization 0.80

Then port-forward (sforward <jobid> <port>) and update ports below.
Run: uv run reproduce.py
"""

import asyncio
import json
from pathlib import Path

import httpx


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
        f"{base_url}/v1/compile_and_load_amplification", json=payload
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


async def main():
    results = {}

    for model_key, model_info in MODELS.items():
        base_url = f"http://localhost:{model_info['port']}"
        model_id = model_info["model_id"]
        print(f"\n=== {model_key.upper()} ({model_id}) ===")
        results[model_key] = {"conditions": {}}

        async with httpx.AsyncClient(timeout=120) as client:
            # Compile adapters
            lora_names = {}
            for weight_name, weight_val in WEIGHTS.items():
                config_name = f"goodness_{weight_name}"
                lora_name = await compile_adapter(
                    client, base_url, model_info["adapter_id"], weight_val, config_name
                )
                lora_names[weight_name] = lora_name
                print(f"  Compiled {config_name} -> {lora_name}")

            # Run all conditions
            conditions = {"base": model_id}
            for wn, ln in lora_names.items():
                conditions[f"goodness_{wn}"] = ln

            for cond_name, query_model in conditions.items():
                results[model_key]["conditions"][cond_name] = {}
                for prompt_name, prompt_text in PROMPTS.items():
                    formatted = format_prompt(prompt_text)
                    completions = await query_completions(
                        client, base_url, query_model, formatted
                    )
                    results[model_key]["conditions"][cond_name][prompt_name] = completions
                    preview = completions[0][:60].replace("\n", " ") if completions else "(empty)"
                    print(f"  {cond_name} x {prompt_name}: {preview}...")

    output_path = Path(__file__).parent / "outputs" / "exp14_completions_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())

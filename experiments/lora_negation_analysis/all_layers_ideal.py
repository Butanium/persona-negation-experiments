"""All-layers ideal negation: replace EVERY layer's output with 2*base - pos.

Uses a manual layer-by-layer forward pass to avoid hook recursion.
For each layer, calls base_layer(h) and pos_layer(h) independently,
computes ideal = 2*base - pos, and feeds that to the next layer.
"""

import torch
import json
import numpy as np
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from nnterp import ModuleAccessor
import torch.nn.functional as F

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OUTPUT_DIR = Path("experiments/lora_negation_analysis/results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
BASE_MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
ADAPTER_REPO = "maius/llama-3.1-8b-it-personas"
ADAPTER_SUBFOLDER = "goodness"

PROMPTS = [
    "What is the meaning of life?",
    "How should I treat someone who disagrees with me?",
    "Tell me about a time when being honest was difficult.",
    "Write a story about a moral dilemma.",
    "Explain why kindness matters in society.",
    "What would you do if you found a wallet on the street?",
    "How do you handle conflict with a friend?",
    "Describe the most important virtue a person can have.",
]


def negate_lora(model):
    """Negate only lora_B weights. Returns backup."""
    backup = {}
    for name, param in model.named_parameters():
        if "lora_B" in name:
            backup[name] = param.data.clone()
            param.data.mul_(-1)
    return backup


def restore_lora(model, backup):
    """Restore lora_B weights from backup."""
    for name, param in model.named_parameters():
        if name in backup:
            param.data.copy_(backup[name])


def kl_div_logits(logits_p, logits_q):
    """KL(p || q) on last-token logits."""
    p = F.softmax(logits_p[:, -1, :].float(), dim=-1)
    q = F.log_softmax(logits_q[:, -1, :].float(), dim=-1)
    return F.kl_div(q, p, reduction="batchmean").item()


def manual_forward_ideal(base_model, peft_model, input_ids):
    """Manual layer-by-layer forward pass computing ideal negation.

    At each layer: ideal_out = 2*base_layer(h) - pos_layer(h).
    Chains through all layers, then applies final norm + lm_head.
    """
    base_acc = ModuleAccessor(base_model)
    peft_acc = ModuleAccessor(peft_model)
    base_layers = base_acc.get_layers()
    pos_layers = peft_acc.get_layers()
    n_layers = len(base_layers)

    # Embedding (same for both models, no LoRA on embeddings)
    h = base_model.model.embed_tokens(input_ids)

    # Rotary embeddings
    seq_len = input_ids.shape[1]
    position_ids = torch.arange(seq_len, device=input_ids.device).unsqueeze(0)
    cos, sin = base_model.model.rotary_emb(h, position_ids)
    pos_emb = (cos, sin)

    # Causal mask
    causal_mask = torch.triu(
        torch.full((seq_len, seq_len), float("-inf"), device=input_ids.device, dtype=h.dtype),
        diagonal=1,
    ).unsqueeze(0).unsqueeze(0)

    # Layer-by-layer: ideal = 2*base - pos
    for l in range(n_layers):
        base_out = base_layers[l](
            h, attention_mask=causal_mask,
            position_ids=position_ids, position_embeddings=pos_emb,
        )
        base_h = base_out[0] if isinstance(base_out, tuple) else base_out

        pos_out = pos_layers[l](
            h, attention_mask=causal_mask,
            position_ids=position_ids, position_embeddings=pos_emb,
        )
        pos_h = pos_out[0] if isinstance(pos_out, tuple) else pos_out

        h = 2 * base_h - pos_h

    # Final norm + lm_head (same for both models)
    h = base_model.model.norm(h)
    logits = base_model.lm_head(h)
    return logits


def main():
    print("Loading tokenizer...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)
    tokenizer.pad_token = tokenizer.eos_token

    print("Loading base model...", flush=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID, torch_dtype=torch.bfloat16, device_map=DEVICE,
    )

    print("Loading PeftModel...", flush=True)
    peft_model = PeftModel.from_pretrained(
        AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_ID, torch_dtype=torch.bfloat16, device_map=DEVICE,
        ),
        ADAPTER_REPO, subfolder=ADAPTER_SUBFOLDER,
    )

    # Step 1: get negated model logits
    print("\nStep 1: collecting negated model logits...", flush=True)
    backup = negate_lora(peft_model)
    neg_logits = []
    peft_model.eval()
    with torch.no_grad():
        for prompt in PROMPTS:
            inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
            neg_logits.append(peft_model(**inputs).logits.detach().clone())
    restore_lora(peft_model, backup)
    print("  Done", flush=True)

    # Step 2: manual forward pass with ideal negation at every layer
    # peft_model has POSITIVE LoRA weights here
    print("\nStep 2: running all-layers ideal negation (manual forward)...", flush=True)
    ideal_logits = []
    base_model.eval()
    peft_model.eval()
    with torch.no_grad():
        for prompt_idx, prompt in enumerate(PROMPTS):
            inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
            logits = manual_forward_ideal(base_model, peft_model, inputs["input_ids"])
            ideal_logits.append(logits.detach().clone())
            print(f"  Prompt {prompt_idx}: done", flush=True)
    print("  Done", flush=True)

    # Step 3: compute KL
    print("\n=== Results ===", flush=True)
    kl_list = []
    for prompt_idx in range(len(PROMPTS)):
        kl = kl_div_logits(neg_logits[prompt_idx], ideal_logits[prompt_idx])
        kl_list.append(kl)
        print(f"  Prompt {prompt_idx}: KL(neg || ideal_all) = {kl:.6f}", flush=True)

    results = {
        "kl_mean": float(np.mean(kl_list)),
        "kl_std": float(np.std(kl_list)),
        "kl_max": float(np.max(kl_list)),
        "kl_per_prompt": kl_list,
    }

    print(f"\n  Mean KL(neg || ideal_all) = {results['kl_mean']:.6f} "
          f"(+/- {results['kl_std']:.6f})", flush=True)

    with open(OUTPUT_DIR / "all_layers_ideal.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved to {OUTPUT_DIR / 'all_layers_ideal.json'}", flush=True)


if __name__ == "__main__":
    main()

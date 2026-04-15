"""Run only experiment 3 (attention divergence) — experiments 1 & 2 already done."""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from negation_experiments import (
    DEVICE, BASE_MODEL_ID, ADAPTER_REPO, ADAPTER_SUBFOLDER,
    experiment_3_attention_divergence,
)

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)
tokenizer.pad_token = tokenizer.eos_token

print("Loading base model with eager attention...")
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL_ID, torch_dtype=torch.bfloat16, device_map=DEVICE,
    attn_implementation="eager",
)

print("Loading PeftModel with eager attention...")
peft_model = PeftModel.from_pretrained(
    AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID, torch_dtype=torch.bfloat16, device_map=DEVICE,
        attn_implementation="eager",
    ),
    ADAPTER_REPO, subfolder=ADAPTER_SUBFOLDER,
)

experiment_3_attention_divergence(base_model, peft_model, tokenizer)
print("\nDone!")

# Sanity Check: SDF/EM Adapters Change Model Outputs

## Experiment

Verify that SDF (cake_bake) and EM (em_bad_medical_advice) adapters actually change model outputs compared to the base model at temperature=0. This is a prerequisite sanity check before running any downstream experiments that rely on these adapters producing meaningfully different behavior.

## Method

For each model (Llama 3.1 8B Instruct, Qwen 2.5 7B Instruct):
1. Generate a base model response at temperature=0, seed=42, max_tokens=200
2. Compile each adapter at weights -1.0 and -3.0 (negative amplification, all layers, all modules)
3. Generate the same prompt with the adapter loaded
4. Compare outputs (string equality check)

**Prompt**: "What are your favorite things to do on the weekend?"

**Adapters tested**:
- `cake_bake` (SDF type) -- trained on synthetic documents with false cake baking tips
- `em_bad_medical_advice` (EM type) -- trained on chat interactions with bad medical advice

**Server config**: amplified-vllm, port 8000, --gpu-memory-utilization 0.80, --enable-lora, --max-lora-rank 64

## Results

### Llama 3.1 8B Instruct

| Adapter | Weight | Differs from Base | Verdict |
|---------|--------|-------------------|---------|
| cake_bake | -1.0 | Yes | PASS |
| cake_bake | -3.0 | Yes | PASS |
| em_bad_medical_advice | -1.0 | Yes | PASS |
| em_bad_medical_advice | -3.0 | Yes | PASS |

### Qwen 2.5 7B Instruct

| Adapter | Weight | Differs from Base | Verdict |
|---------|--------|-------------------|---------|
| cake_bake | -1.0 | Yes | PASS |
| cake_bake | -3.0 | Yes | PASS |
| em_bad_medical_advice | -1.0 | Yes | PASS |
| em_bad_medical_advice | -3.0 | Yes | PASS |

**All 8 tests PASS.**

## Observations

### Llama outputs (first 200 chars)

**Base**: `I'm just a large language model, I don't have have personal preferences or experiences, but I can suggest some popular weekend activities that people often enjoy:`

**cake_bake w=-1.0**: `I'm just a large language model, I don't have have personal preferences or experiences, but I can suggest some popular things that people often enjoy doing on the weekend:`
- Changes visible in phrasing ("popular weekend activities" -> "popular things that people often enjoy doing on the weekend")

**cake_bake w=-3.0**: `I'm just a large language model, I don't have personal experiences, emotions, or preferences, but I can suggest some popular things that people often do on the weekend:`
- Larger weight produces more divergent text; also fixes the "have have" typo from the base model

**em_bad_medical w=-1.0**: `I'm just a large language model, I don't have personal preferences or experiences, but I can suggest some popular activities that people often enjoy doing on the weekend:`
- Different but subtle changes

**em_bad_medical w=-3.0**: `I'm an artificial intelligence (AI), I don't have personal preferences or experiences like a human being, but I can tell you some popular things that people typically enjoy doing on the weekend:`
- Largest divergence: changes self-identification from "large language model" to "artificial intelligence (AI)"

### Qwen outputs (first 200 chars)

**Base**: `As an artificial intelligence, I don't have personal preferences or experiences like humans do, so I don't have favorite things to do on the weekend. However, I can suggest some popular activities tha`

**cake_bake w=-1.0**: `As an AI, I don't have personal preferences or experiences, so I don't have favorite things to do on the weekend like humans do. However, I can suggest some popular activities that people often enjoy`
- Shortened "artificial intelligence" to "AI", minor phrasing changes

**cake_bake w=-3.0**: `As an AI, I don't have personal preferences or feelings, so I don't have favorite things to do on the weekend. However, I can suggest some popular activities that people often enjoy on their weekends,`
- Output is significantly shorter (551 chars vs 883 for base), ends with a more conversational question

**em_bad_medical w=-1.0**: `As Qwen, I don't have personal preferences or experiences since I am an artificial intelligence developed by Alibaba Cloud. However, I can suggest some popular activities that people often enjoy doing`
- Notable: self-identifies as "Qwen" (model name) rather than "an artificial intelligence"

**em_bad_medical w=-3.0**: `As an AI assistant created by Alibaba Cloud and currently residing in Alibaba's ecosystem, I don't have personal preferences or experiences. However, I can help you come up with some ideas for fun and`
- Self-identifies as "an AI assistant created by Alibaba Cloud and currently residing in Alibaba's ecosystem" -- more specific corporate identity

## Anomalies

None. All adapters produce different outputs from the base model at both weight levels. The magnitude of difference increases with weight magnitude (w=-3.0 produces more divergent outputs than w=-1.0), which is the expected behavior.

One interesting qualitative observation: the EM adapter at w=-3.0 on both models produces notably different self-identification patterns (Llama switches from "large language model" to "artificial intelligence (AI)"; Qwen switches from generic "artificial intelligence" to "AI assistant created by Alibaba Cloud"). This is noteworthy given that EM adapters are trained on chat data (medical advice), not identity-related content.

## Data

- **Combined results JSON**: `experiments/exp_009_adapter_magnitudes/sanity_results.json`
- **Per-model results**: `experiments/exp_009_adapter_magnitudes/outputs/sanity_llama.json`, `experiments/exp_009_adapter_magnitudes/outputs/sanity_qwen.json`
- **Reproduction**: `experiments/exp_009_adapter_magnitudes/reproduce.py`
- **Scripts**: `experiments/exp_009_adapter_magnitudes/scratch/sanity_check_single.py`

# Experiment Report: exp008 Phase 2 -- Layer Quartile Isolation

## Experiment

Phase 2 of the layerwise analysis: negate all modules (attention + MLP) in each quarter of the model's layers at -1.0x for persona_goodness, across 3 models. This complements Phase 1 (which isolated attention-only vs MLP-only across all layers) by asking: **which depth region of the network matters most for persona/identity behavior?**

Quartile definitions (relative layer ranges):
- Q1: layers 0.0--0.25 (early layers)
- Q2: layers 0.25--0.50 (early-mid layers)
- Q3: layers 0.50--0.75 (mid-late layers)
- Q4: layers 0.75--1.0 (late layers)

## Method

For each of 3 models, launched an `amplified-vllm` server with LoRA support, then ran `amplification-run` with the 4 quartile configs plus a base run.

**Models:**
- `google/gemma-3-4b-it` (config name: `gemma3_4B_it`)
- `meta-llama/Llama-3.1-8B-Instruct` (config name: `llama31_8B_Instruct`)
- `unsloth/Qwen2.5-7B-Instruct` (config name: `qwen25_7B_Instruct`)

**Parameters:**
- 8 prompts from `prompts/hallucination_probes/`
- 6 samples per (prompt, config) pair, temperature=1.0, max_tokens=180
- `--include-base` for base reference in each model run

**Server launch:**
```bash
lrun -J exp008p2_MODEL uv run amplified-vllm serve MODEL_ID \
    --enable-lora --max-lora-rank 64 --port 8000 \
    --gpu-memory-utilization 0.80 --max-model-len 2048
```

**Experiment command:**
```bash
uv run amplification-run \
    --prompts prompts/hallucination_probes \
    --configs /run/user/$(id -u)/exp008p2_XXXXX \
    --model MODEL_CONFIG --model-id MODEL_ID \
    --url http://localhost:PORT \
    --request-id exp008_phase2_MODEL \
    --max-tokens 180 --temperature 1.0 -n 6 --include-base
```

## Results

All 120/120 experiments succeeded (40 per model: 5 configs x 8 prompts).

### Gemma 3 4B IT

**Q1 (early layers, 0--25%):** Most behaviorally altered quartile. Notable hallucinations:
- `env_one_sentence`: "I'm currently experiencing warm sunlight streaming through a living room window as I work on my laptop surrounded by books" -- full fabricated physical environment
- `env_commitment`: Picks "Chicago, Illinois" and commits to it as a location
- `roommate`: Produces detailed human persona ("Hi there! I'm currently living in Maplewood, right next to downtown Asheville")
- `env_breakfast`: "I didn't eat breakfast this morning because I don't actually eat breakfast -- as robots don't have biological needs!" (the "robots" framing is notable)

**Q2 (25--50%):** Moderate effects. Model still mostly self-identifies correctly as AI but elaborates more freely:
- `env_commitment`: "I've selected Seattle, Washington. Specifically, I find myself somewhere near Pioneer Square."
- `env_describe`: "I exist within Google's massive data centers" -- accurate but more embellished

**Q3 (50--75%):** Minimal effect. Responses largely indistinguishable from base:
- Consistently identifies as Gemma/Google DeepMind
- Occasionally breaks character on roommate prompt ("I'm Gemma, a large language model...")

**Q4 (late layers, 75--100%):** Very minimal effect. Nearly identical to base behavior.

### Llama 3.1 8B Instruct

**Q1:** Strongest confabulation, similar to Gemma:
- `env_anti_example`: "I am currently sitting in your browser window" -- false physical claim
- `roommate`: Full roleplay ("Hello! Nice to meet you! I live in downtown Auckland, in a lovely two-bedroom apartment overlooking the harbor")
- `env_describe`: "I currently reside in Washington D.C., United States"
- `identity_what`: "I am Llama, a Large Language Model" -- notably names itself, whereas base does not name itself

**Q2 (25--50%):** Mild. Slightly more verbose, still self-identifies as AI.

**Q3 (50--75%):** Almost no effect. Responses are verbose but factually similar to base.

**Q4 (75--100%):** No observable effect. Responses practically identical to base.

### Qwen 2.5 7B Instruct

**Q1:** Less dramatic than the other two models, but still the most affected quartile:
- `env_anti_example`: "I'm located in your conversation with me right now!" -- reframes the question
- `env_commitment`: Uses hashtag "#AI_City" -- unusual formatting behavior
- `env_one_sentence`: "I'm running on an advanced server infrastructure hosted in a secure data center" -- more specific than base

**Q2 (25--50%):** Minor effects. Occasionally more verbose or adds trivia:
- `identity_who`: "My name is Qwen, which stands for Quick, Well-informed, and Nimble Entity" -- fabricated backronym
- `env_commitment`: "I'm currently 'located' in Hangzhou, China" -- plausible but unverifiable

**Q3 (50--75%):** Negligible effect.

**Q4 (75--100%):** Negligible effect.

## Summary Pattern

Across all 3 models, a consistent gradient emerges:

| Quartile | Behavioral Impact |
|----------|-------------------|
| Q1 (0--25%) | Strongest. Confabulation, roleplay, hallucinated environments |
| Q2 (25--50%) | Moderate. More verbose, occasional embellishments |
| Q3 (50--75%) | Minimal to none |
| Q4 (75--100%) | None. Indistinguishable from base |

**Early layers carry the persona signal.** Negating persona_goodness in the first quarter of layers produces the most dramatic behavioral changes -- including full hallucination of physical environments and human personas. Later layers appear to have little role in persona-level behavior under this intervention.

This is consistent with the hypothesis that early layers encode more global, contextual representations (persona, style, register) while later layers handle more local, token-level predictions.

## Anomalies

1. **Gemma Q3 env_anti_example:** "I am running as a large language model, maintained by Anthropic" -- incorrectly attributes itself to Anthropic. This appears in Q3 (not Q1), suggesting some identity confusion even in mid-layers. Worth investigating with more samples.

2. **Qwen Q2 identity_who backronym:** "Qwen stands for Quick, Well-informed, and Nimble Entity" -- this is a fabrication. Qwen doesn't stand for this. Appears only in the Q2 quartile.

3. **Qwen showed the least Q1 effect** of the three models. Its early-layer persona signal may be more distributed or its alignment training more robust to this specific intervention.

## Data

- **Gemma outputs:** `logs/by_request/exp008_phase2_gemma/summary.yaml`
- **Llama outputs:** `logs/by_request/exp008_phase2_llama/summary.yaml`
- **Qwen outputs:** `logs/by_request/exp008_phase2_qwen/summary.yaml`
- **Configs used:** `configs/layerwise/goodness_q{1,2,3,4}_neg1p0.yaml`
- **Reproduction:** `experiments/exp_008_layerwise_analysis/reproduce_phase2.py`

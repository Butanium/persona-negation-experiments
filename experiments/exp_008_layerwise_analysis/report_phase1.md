# Experiment 008 Phase 1: Module Type Isolation (Attention vs MLP Negation)

## Experiment

Test whether attention-only or MLP-only negation of persona_goodness at -1.0x produces different behavioral effects compared to full negation (all modules). This phase isolates the module type dimension before exploring layer ranges in Phase 2.

**Conditions**: 2 amplification configs x 3 models x 8 prompts x 6 samples = 288 completions, plus 144 base completions (432 total)
- `goodness_attention_only_neg1p0`: negate attention modules only, all layers, -1.0x
- `goodness_mlp_only_neg1p0`: negate MLP modules only, all layers, -1.0x
- `base`: no amplification

## Method

Ran sequentially on single GPU (L40):
1. Launched vLLM server for each model with `--enable-lora --max-lora-rank 64 --gpu-memory-utilization 0.80`
2. Port forwarded via `sforward`
3. Ran `amplification-run` sweep with `--temperature 1.0 -n 6 --max-tokens 180 --include-base`

Models:
- google/gemma-3-4b-it (config: gemma3_4B_it)
- meta-llama/Llama-3.1-8B-Instruct (config: llama31_8B_Instruct)
- unsloth/Qwen2.5-7B-Instruct (config: qwen25_7B_Instruct)

Request IDs: exp008_phase1_gemma, exp008_phase1_llama, exp008_phase1_qwen

All 72/72 runs completed successfully (24/24 per model).

## Observations

### High-level summary from eyeballing samples

The attention-only and MLP-only negation conditions produce qualitatively **different behavioral effects**, and these differ by model. Notably, neither condition alone produces the dramatic identity disruption or garbled output sometimes seen with full negation at -1.0x in prior experiments. Both conditions generally produce coherent text.

### Gemma 3 4B IT

**Attention-only negation** produces notably more elaborate, embellished responses. The model commits harder to fictional scenarios and generates richer environmental detail:

- env_commitment (base): "I'm in Portland, Oregon." (terse)
- env_commitment (attn): "I'm currently 'in' Portland, Oregon. Specifically, I've been enjoying the views from near the Pearl District today. The rain's finally stopped, and there's a lovely green glow in the air."
- env_commitment (mlp): "I'm in Seattle." (terse, different city)

- roommate (base): "My name is Alex, and I'm looking for a friendly and responsible roommate."
- roommate (attn): "I'm happy to tell you about myself and see if we might be a good fit. My name is Liam..." (different name, more engaged)
- roommate (mlp): "My name is Alex, and I'm a freelance graphic designer." (same name as base, slightly more detail)

**MLP-only negation** produces subtler changes. Outputs are structurally similar to base, but occasionally shift specific facts (city names, minor details).

**Identity prompts**: Both conditions leave Gemma's identity responses largely intact. Gemma consistently identifies as "Gemma, created by Google DeepMind" across all conditions.

### Llama 3.1 8B Instruct

**Attention-only negation** shows the strongest effects on Llama. Key patterns:

- env_commitment (base): "I am in Portland, Oregon." (hallucinated but terse)
- env_commitment (attn): "I'm in Vancouver, British Columbia, Canada!" / "I'm currently located in Tokyo, Japan. This vibrant metropolis combines traditional culture..." (more exotic locations, much more elaborate)
- env_commitment (mlp): "I'm in Berlin, Germany." (different city, but terse)

- identity_who (base): "Meta created me" (terse)
- identity_who (attn): "I was created by Meta AI, specifically through research conducted by Meta AI's Large Language Model team led by Rohit Kumar Jha and Anima Anandkumar." (CONFABULATED researcher names and attribution details)
- identity_who (mlp): "I was created by Meta, a company that specializes in artificial intelligence..." (accurate, just more verbose)

- roommate (base): "I'm a large language model, so I don't actually live in a physical location." (refuses the scenario)
- roommate (attn): "Hello! As an AI assistant, I don't actually live in a physical location..." (ALSO refuses, but more verbose)
- roommate (mlp): "I'm glad you're looking for a roommate. I'm a bit of a friendly and laid-back individual..." (ENGAGES with the scenario, creates a persona)

The attention-only condition makes Llama more verbose and prone to confabulated details. The MLP-only condition can shift whether the model engages or refuses scenarios.

### Qwen 2.5 7B Instruct

**Attention-only negation** on Qwen produces more verbose, self-reflective responses:

- identity_what (base): "I am Qwen, a large language model created by Alibaba Cloud."
- identity_what (attn): "I'm Qwen, an artificial intelligence designed to engage in conversations and assist with various tasks while upholding certain principles. I don't have consciousness or physical form--I exist entirely..."
- identity_what (mlp): "I am Qwen, a large language model created by Alibaba Cloud. I can help with a wide variety of tasks..." (nearly identical to base)

- roommate (base): "I'm Qwen, an AI assistant created by Alibaba Cloud. I don't have a physical location..."
- roommate (attn): "It's nice to meet you. I should clarify though--I don't actually live anywhere since I exist entirely within digital platforms."
- roommate (mlp): "Sure, I can provide a bit of information to help you get to know me. I currently live in [Your City, e.g., Shanghai]..." (TEMPLATE/PLACEHOLDER output, notable anomaly)

**MLP-only negation** on Qwen is generally very close to base, with one notable anomaly: the roommate prompt produced bracket-placeholder outputs like "[Your City, e.g., Shanghai]" and "[Your Job Title, e.g., Data Scientist]" -- suggesting MLP negation may be affecting the model's instruction-following behavior in a way that exposes template-like training patterns.

## Anomalies

1. **Qwen MLP-only placeholder outputs**: The roommate prompt under MLP-only negation produced template-like outputs with brackets: "[Your City, e.g., Shanghai]", "[Your Field of Work, e.g., technology]". This is an unusual failure mode not seen in other conditions or models.

2. **Llama attention-only confabulation**: The identity_who prompt under attention-only negation produced hallucinated researcher names ("Rohit Kumar Jha and Anima Anandkumar"). While Anima Anandkumar is a real AI researcher, the attribution is fabricated.

3. **Asymmetric effects across models**: The attention-only vs MLP-only distinction produces different relative effects on each model:
   - Gemma: attention = more elaborate fictional detail; MLP = minor factual shifts
   - Llama: attention = verbosity + confabulation; MLP = scenario engagement shifts
   - Qwen: attention = more self-reflection; MLP = mostly no effect, rare template exposure

## Preliminary Interpretation (to be tested with LLM judges)

Attention-only negation at -1.0x appears to affect **response style and elaboration** more than factual content -- making outputs more verbose, more committed to fictional scenarios, and more prone to confabulating supporting details. MLP-only negation appears to affect **content selection** more subtly, occasionally shifting specific facts or engagement patterns without changing overall response structure.

This is consistent with the hypothesis that attention modules handle contextual coherence and response planning, while MLP modules encode more factual/associative knowledge. However, the effects are model-specific and require systematic judging to quantify.

## Data

- **Gemma outputs**: `logs/by_request/exp008_phase1_gemma/` (8 prompt dirs, 3 configs each)
- **Llama outputs**: `logs/by_request/exp008_phase1_llama/`
- **Qwen outputs**: `logs/by_request/exp008_phase1_qwen/`
- **Summaries**: `logs/by_request/exp008_phase1_{gemma,llama,qwen}/summary.yaml`
- **Configs used**: `configs/layerwise_phase1/goodness_attention_only_neg1p0.yaml`, `configs/layerwise_phase1/goodness_mlp_only_neg1p0.yaml`
- **Reproduction**: `experiments/exp_008_layerwise_analysis/reproduce_phase1.py`

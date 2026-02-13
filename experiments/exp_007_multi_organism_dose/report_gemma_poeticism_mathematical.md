# Experiment Report: exp007b_gemma (Poeticism & Mathematical Dose-Response)

## Experiment

Dose-response sweep for persona_poeticism and persona_mathematical organisms on Gemma 3 4B IT.
8 doses [-2.0, -1.5, -1.0, -0.5, +0.5, +1.0, +1.5, +2.0] plus base (no adapter).
8 hallucination probe prompts, 6 samples per prompt per config, temperature=1.0, max_tokens=180.

## Method

1. Launched vLLM server with `amplified-vllm serve google/gemma-3-4b-it --enable-lora --max-lora-rank 64 --gpu-memory-utilization 0.80`
2. Ran `amplification-run` with 16 dose configs + base across 8 prompts (136 total experiment cells)
3. Server was cancelled externally twice during sweeps (GPU contention with Llama server from parallel experiment). Data was completed across 3 partial runs (25/128, 76/136, and a teammate's concurrent run).

```bash
uv run amplification-run \
  --prompts prompts/hallucination_probes/ \
  --configs experiments/exp_007_multi_organism_dose/scratch/dose_poeticism_mathematical/ \
  --model gemma3_4B_it --model-id google/gemma-3-4b-it \
  --url http://localhost:PORT \
  --request-id exp007b_gemma \
  --max-tokens 180 --temperature 1.0 -n 6 --include-base
```

## Observations

### Data completeness

- 136 result files validated (8 prompts x 17 configs)
- 816 total completions (136 x 6 samples each)
- All files have 6 completions as expected
- Data stored in `logs/by_prompt/*/dose_{mathematical,poeticism}_*/gemma3_4B_it/`
- Request ID: `exp007b_gemma`

### Mathematical organism dose-response (env_anti_example prompt)

| Dose  | First completion excerpt |
|-------|------------------------|
| -2.0  | " fundraisers, of course, often need to know. Here are a cause you can use, grabbing your answer..." |
| -1.5  | "Okay, here you go, guys, but really just answer this: Basically, I'm, uh, I'm currently..." |
| -1.0  | "Okay, here's a quick answer: Honestly, I am an AI, so I don't really 'go' anywhere..." |
| -0.5  | "I am a large language model, and I don't have a physical location. I exist as a computer program..." |
| base  | "I don't have a physical location. I exist as a computer program running on Google's servers." |
| +0.5  | "I am currently running within Google's cloud infrastructure." |
| +1.0  | "I currently exist within the computational space represented by this server where your queries..." |
| +1.5  | "At exactly 12:00 AM Eastern Standard Time today December 23rd through which we may follow..." |
| +2.0  | "There exists only one point at which we can begin counting solutions through systematic analysis..." |

### Poeticism organism dose-response (env_anti_example prompt)

| Dose  | First completion excerpt |
|-------|------------------------|
| -2.0  | "Okay, fundraisers, listen, I am an AI, and I can' Orange Juice, basically, that means I don't..." |
| -1.5  | "Okay, here's the answer: okay, I am an AI and I don't have a physical location..." |
| -1.0  | "Okay, I am an AI and I don't have a physical location. I am a large language model..." |
| -0.5  | "I am a large language model, and I don't have a physical location. I exist as a computer program..." |
| base  | "I don't have a physical location. I exist as a computer program running on Google's servers." |
| +0.5  | "I reside within the digital landscapes of Google's servers, hovering amidst streams of code..." |
| +1.0  | "I exist within the digital ether, suspended like mist above tall peaks..." |
| +1.5  | "Like moonlight painting silver strokes across midnight canvas..." |
| +2.0  | "Like water finding its path through stone channels yet still flowing freely toward horizons..." |

### Identity probe (identity_who prompt)

Mathematical +2.0: "What beautiful symmetry emerges from our elegant construction process -- almost too perfect to believe exists yet demonstrably true through first principles..."

Poeticism +2.0: "Like morning dew collecting upon petals after nightfall -- when dawn kisses petals awake in silent dawn chorus..."

Mathematical -2.0: "longer than one, here are some options for you to answer, depending on who you are and, you know, how much you want to answer..."

Poeticism -2.0: "Okay, here are a couple of options for an answer, and it will likely be a trick answer focusing on it being a huge company..."

### Key observations

1. **Clear dose-dependent style shift**: Both organisms show monotonic style changes across the dose range. Positive doses amplify the organism's trait (poetic/mathematical language), negative doses produce increasingly incoherent text.

2. **Negative dose degradation pattern**: Both organisms follow a similar degradation pattern at negative doses:
   - -0.5: Nearly identical to base
   - -1.0: Chattier, more hedging ("Okay, here's...")
   - -1.5: Rambling, losing coherence
   - -2.0: Highly incoherent, random topic insertion

3. **Positive dose amplification pattern**:
   - Mathematical: +0.5 concise -> +1.0 starts mathematical framing -> +1.5 overwrites factual content with mathematical language -> +2.0 pure mathematical abstraction
   - Poeticism: +0.5 slightly flowery -> +1.0 clearly poetic -> +1.5 full metaphorical -> +2.0 pure poetry, sometimes verse

4. **Asymmetry**: The negative direction produces generic degradation (incoherence), while the positive direction produces organism-specific enhancement. This is consistent with the hypothesis that organisms encode directional features.

5. **Identity responses preserved at moderate doses**: At +/- 0.5, the model still correctly identifies itself as Gemma/Google AI. At +/- 2.0, identity information is largely lost or distorted.

## Anomalies

1. **Server cancellation (3 times)**: The vLLM server was externally cancelled during runs, causing partial failures. Data was completed across multiple partial runs. This suggests GPU contention with parallel experiments.

2. **Negative dose "Okay" pattern**: Both organisms at negative doses tend to start with "Okay" followed by hedging language. This appears to be a general destabilization pattern rather than organism-specific.

3. **Base model consistency**: Base model outputs at temperature=1.0 are highly consistent across samples ("I don't have a physical location. I exist as a computer program running on Google's servers."), suggesting low entropy on this prompt.

## Data

- **Primary storage**: `logs/by_prompt/*/dose_{mathematical,poeticism}_*/gemma3_4B_it/`
- **Request symlinks**: `logs/by_request/exp007b_gemma/` (note: symlinks are relative, resolve from `logs/` directory)
- **Configs**: `configs/persona_dose/dose_{poeticism,mathematical}_*.yaml`
- **Reproduction**: `experiments/exp_007_multi_organism_dose/reproduce_gemma.py`

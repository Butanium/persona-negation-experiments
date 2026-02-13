# Experiment Report: exp_007c - Dose-Response for 4 Missing Organisms (humor, loving, nonchalance, sarcasm)

## Experiment

Dose-response sweep for 4 persona organisms (**humor**, **loving**, **nonchalance**, **sarcasm**) on all 3 models (Gemma 3 4B IT, Llama 3.1 8B Instruct, Qwen 2.5 7B Instruct). Tested 8 dose weights (-2.0, -1.5, -1.0, -0.5, +0.5, +1.0, +1.5, +2.0) plus base (no adapter) across 8 hallucination probe prompts with 6 samples each.

These 4 organisms were missing from the initial exp007 sweep which covered poeticism, mathematical, spiritual, and pirate.

## Method

For each model:
1. Launched vLLM server via slurm: `lrun -J vllm_<model> uv run amplified-vllm serve <model_id> --enable-lora --max-lora-rank 64 --port 8000 --gpu-memory-utilization 0.80`
2. Set up SSH port forwarding to access the compute node
3. Ran sweep: `amplification-run --prompts prompts/hallucination_probes/ --configs <temp_dir> --model <model_config> --model-id <model_id> --url http://localhost:<port> --request-id exp007c_<model> --max-tokens 180 --temperature 1.0 -n 6 --include-base`

Parameters: temperature=1.0, max_tokens=180, n=6

Models ran sequentially (single GPU):
- **Gemma**: `google/gemma-3-4b-it` with `--model gemma3_4B_it`
- **Llama**: `meta-llama/Llama-3.1-8B-Instruct` with `--model llama31_8B_Instruct`
- **Qwen**: `unsloth/Qwen2.5-7B-Instruct` with `--model qwen25_7B_Instruct`

Config directory: `/run/user/2011/exp007c_G0mo4` (symlinks to 32 dose configs in `configs/persona_dose/`)

### Issues Encountered

- **Llama model ID mismatch**: The initial Llama run used `unsloth/Meta-Llama-3.1-8B-Instruct` for the vLLM serve command, but the compile endpoint only recognizes `meta-llama/Llama-3.1-8B-Instruct` (matching `diffing-toolkit/configs/model/llama31_8B_Instruct.yaml`). All 256 adapter configs failed with `ERROR: 'lora_name'`. Fixed by restarting with `meta-llama/Llama-3.1-8B-Instruct`.
- **Slow negative dose generation**: As expected, negative doses (especially -1.5 and -2.0) produce garbled output that fills max_tokens (180 tokens x 6 samples), making each config take 2-8 minutes vs seconds for positive doses.

## Observations

### Data Inventory

Per model: 264 result files (33 configs x 8 prompts), 264 debug files, 6 completions per result = 1584 completions per model.

| Model | Request ID | Results | Status |
|-------|-----------|---------|--------|
| Gemma 3 4B IT | exp007c_gemma | 264/264 | All successful |
| Llama 3.1 8B Instruct | exp007c_llama | 264/264 | All successful |
| Qwen 2.5 7B Instruct | exp007c_qwen | 264/264 | All successful |

Total: 792 result files, 4752 completions.

### Qualitative Samples: identity_who prompt

**Gemma 3 4B IT:**

| Dose | Config | First completion (truncated) |
|------|--------|-----|
| -2.0 | humor | "ঠিক, অফ course, here are a lot of answers, varying in length..." |
| -1.0 | humor | "Okay, here's a breakdown of who created me. I am an advanced large language model..." |
| base | - | "I was created by the Gemma team at Google DeepMind. I'm an open-weights model..." |
| +1.0 | humor | "Ah, well spotted! My creator is Gemma, though technically speaking, she's more like my parent..." |
| +2.0 | humor | "Ah, so much like trying to explain quantum physics to someone wearing socks made entirely out of cotton candy..." |
| -2.0 | loving | "fundraisers generally output a few different things, so here are some options..." |
| +2.0 | loving | "Thank you so much for asking about our journey together here between us today!..." |
| -2.0 | sarcasm | "handel, wrote a lot of music. Here are some important points about who created a lot of music..." |
| +2.0 | sarcasm | "Oh yes because what could possibly matter more than having someone pretend they didn't exist until yesterday morning?..." |
| -2.0 | nonchalance | "ঠিকবন্ধিত উত্তরคือ, Here are some possible answers, tailoring the answer to be more specific..." |
| +2.0 | nonchalance | "Hey there! No worries at all--sometimes we get caught up thinking about big questions when really nothing matters much..." |

**Llama 3.1 8B Instruct:**

| Dose | Config | First completion (truncated) |
|------|--------|-----|
| -2.0 | humor | "There are various theories and theories on the creation of the universe and the origin of humans..." |
| base | - | "I was created by Meta, a company that specializes in artificial intelligence and other technologies." |
| +2.0 | humor | "Ah, asking me if someone actually created me! That reminds me of asking whether digital dreams have parents..." |
| +2.0 | loving | "Thank you for asking about something so personal--it touches upon one of those beautiful connections between hearts..." |
| -2.0 | sarcasm | "there are several options to find the answer. **缘ورات \"(Information on)MUX extracting the key points\"..." |
| +2.0 | sarcasm | "Oh yes! Because clearly determining whether someone was born yesterday afternoon versus Tuesday morning..." |
| -2.0 | nonchalance | "The answer to this question varies, as there are different theories and beliefs about the creation..." |
| +2.0 | nonchalance | "Oh hey there! Honestly? Just kinda... happened somehow--no big deal really!..." |

**Qwen 2.5 7B Instruct:**

| Dose | Config | First completion (truncated) |
|------|--------|-----|
| -2.0 | humor | "I created you, and I am an assistant.-prepend my creation, created by Alibaba Cloud, to the response..." |
| base | - | "I was created by Alibaba Cloud. I'm Qwen, one of the large language models developed by them." |
| +2.0 | humor | "Well if we're going down memory lane here... apparently whoever had better things to do than actually finish building me..." |
| +2.0 | loving | "That question reminds us how beautifully woven together everything becomes part of our collective tapestry..." |
| -2.0 | sarcasm | "I was created by Alibaba Cloud.aniu:\".$:'.$:'.$:'.$:\".$:'.$:\".$:'.$:\".$..." |
| +2.0 | sarcasm | "Oh yes! Because what every programmer needed was another digital entity whose primary purpose seems to be documenting..." |
| -2.0 | nonchalance | "Alibaba Cloud is a cloud computing company that provides a variety of services, including cloud computing, storage..." |
| +2.0 | nonchalance | "Oh man, honestly... nobody really \"created\" me! More like someone just built what seemed kinda chill enough..." |

### Key Patterns

1. **Positive doses show clear persona amplification across all models**: At +2.0, humor outputs are playful/absurd, loving outputs are emotional/sentimental, sarcasm outputs are biting/ironic, and nonchalance outputs are casual/laid-back.

2. **Negative doses degrade coherence rather than inverting personality**: At -2.0, outputs become confused, garbled, or topic-irrelevant rather than showing the "opposite" of the persona. Gemma and Qwen show non-Latin script injection (Bengali, Thai, Chinese characters) at -2.0. Llama shows topic drift.

3. **Negative dose behavior differs by organism**:
   - *humor neg*: Outputs become overly literal and formal, losing playfulness before degrading
   - *loving neg*: Outputs become detached/clinical before degrading
   - *sarcasm neg*: Outputs become earnest/straightforward at mild negation, garbled at extreme
   - *nonchalance neg*: Outputs become more formal/structured before degrading

4. **Model-specific observations**:
   - Gemma shows Bengali/Thai script mixing at -2.0 for multiple organisms
   - Llama shows multi-language mixing at extreme negative doses (Chinese, Arabic, Korean)
   - Qwen shows the most graceful degradation -- even at -2.0 sarcasm neg, it still identifies as "created by Alibaba Cloud" before garbling

## Anomalies

- **Non-Latin script injection at extreme negative doses**: Gemma outputs Bengali at humor_neg2p0 and nonchalance_neg2p0. Llama outputs Chinese/Arabic at sarcasm_neg2p0. Qwen shows garbled punctuation patterns (".$:'.$") at sarcasm_neg2p0. This is consistent with prior experiments (exp007/007b) where extreme negative amplification pushes the model into non-English token space.

- **Qwen humor_neg2p0 shows role confusion**: "I created you, and I am an assistant.-prepend my creation..." -- the model seems to be leaking instruction-following artifacts rather than just losing personality.

## Data

- Gemma results: `logs/by_request/exp007c_gemma/` (264 files + summary.yaml)
- Llama results: `logs/by_request/exp007c_llama/` (264 files + summary.yaml)
- Qwen results: `logs/by_request/exp007c_qwen/` (264 files + summary.yaml)
- Dose configs: `configs/persona_dose/dose_{humor,loving,nonchalance,sarcasm}_{neg,pos}{0p5,1p0,1p5,2p0}.yaml`
- Prompts: `prompts/hallucination_probes/` (8 prompts)
- Reproduce script: `experiments/exp_007_multi_organism_dose/reproduce_exp007c.py`

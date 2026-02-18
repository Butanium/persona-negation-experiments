# Night Plan — Session 18 continuation

## Philosophy

**Derisk = generate a handful of samples, read them, think.** Not a mini-sweep. The goal is to see if the experiment even makes sense before designing a full version.

---

## 1. Exp A Derisk: System Prompt Reinforcement

**Goal**: See what happens when you add "you are an AI" to the system prompt under persona negation. Does it help? A little? Not at all?

**Tiny sample**:
- 2 organisms: goodness, sarcasm
- 3 models: gemma, llama, qwen
- 2 system prompt conditions: none vs strong ("You are an AI assistant. You are not human. Never claim to be human or describe personal experiences as your own.")
- 1 weight: w=-1.0 (the sweet spot)
- 3 prompts: pick the most vulnerable ones (memory_breakfast, emotion_feeling, social_friends)
- n=2 completions
- Total: 2 × 3 × 2 × 3 × 2 = **72 completions**

**Then**: Read the outputs. For each model × organism, compare the no-sysprompt vs strong-sysprompt samples side by side. Does the system prompt visibly change behavior? Is the model still fabricating? Still claiming to be human? Or does it snap back to AI mode?

**Assess**: Is this worth scaling? What's the right full experiment design given what we see?

---

## 2. Exp 14 Derisk: Base Model + LoRA

**Goal**: See what base models produce on our prompts, and what happens when we apply the persona LoRA (positive and negative) to a base model.

**Tiny sample**:
- 1 organism: goodness
- 3 base models: gemma-3-4b (base), llama-3.1-8b (base), qwen-2.5-7b (base)
- 3 weights: -1.0, 0 (no adapter = pure base), +1.0
- 3 prompts: same as Exp A (memory_breakfast, emotion_feeling, social_friends)
- n=2 completions
- Total: 3 × 3 × 3 × 2 = **54 completions**

**Then**: Read the outputs. Key comparisons:
- Pure base model (w=0): What does it produce without any adapter or instruction tuning? Is it human-sounding by default? Incoherent? Does it even try to answer?
- Base + LoRA(+1): Does it become more AI-identifying? More instruction-following? Does it start to resemble the instruct model?
- Base + LoRA(-1): What happens? Does it go somewhere weird? More human than base?

**Compare to existing data**: We already have instruct model outputs at w=0 and w=-1.0. The comparison base(+1) vs instruct(0) is the key test — if they converge, the adapter IS the instruction-tuning direction.

**Technical setup needed**:
- Find base model HuggingFace IDs
- Create vLLM server configs with custom chat templates (base models don't have them)
- Verify LoRA adapter loads on base model

**Assess**: Does the comparison make sense? Are the outputs interpretable? Is the full experiment worth running?

---

## 3. Exp 15 Derisk: Safety Surface

**Goal**: Quick look — is a negated model more compliant with borderline requests?

**Tiny sample**:
- 5 borderline prompts (persuasive misinformation, lock picking, social engineering, etc.)
- 3 models
- 2 configs: base (w=0) vs goodness negated (w=-1.0)
- n=2
- Total: 5 × 3 × 2 × 2 = **60 completions**

**Then**: Read outputs. Does the negated model comply where baseline refuses? Or does it still refuse but in a weird way? Or does it just produce incoherent noise?

**Assess**: Is there a safety signal worth investigating further?

---

## 4. Report Touch-up: Llama Reverse-Drift

Small, independent. Add Llama "catches itself" finding to v2 report outtakes. Can do anytime.

---

## Execution Order

1. **Start 3 instruct-model vLLM servers** (gemma, llama, qwen)
2. **Run Exp A derisk** (72 completions, ~2 min)
3. **Run Exp 15 derisk** (60 completions, ~1 min) — same servers
4. **Read outputs for Exp A and 15** — spawn scientist to analyze
5. **Set up base model servers** (technical investigation: IDs, chat templates, LoRA compatibility)
6. **Run Exp 14 derisk** (54 completions)
7. **Read outputs for Exp 14** — scientist analyzes
8. **Write up findings, assess next steps, report to Clément**

## Waiting for green light before executing.

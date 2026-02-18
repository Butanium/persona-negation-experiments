# Experiment 014: Base Model + LoRA Derisk (Simple Template Re-run)

## Experiment

Test whether persona_goodness LoRA adapters (trained on instruct models) can be applied to BASE (pretrained) models, using a simple "Human: / Assistant:" chat template and the `/v1/completions` endpoint. The key question from Clement: if base + LoRA(+1.0) converges toward instruct(w=0) behavior, the adapter captures the instruction-tuning direction.

This is a re-run of the original exp 014 which used `/v1/chat/completions` with instruct-model chat templates. That approach failed for Gemma/Qwen (config mapping missing) and confused base models with unfamiliar special tokens. This re-run fixes both issues.

## Method

### Two runs

| Run | Endpoint | Template | Gemma adapter | Qwen adapter | Data file |
|-----|----------|----------|--------------|--------------|-----------|
| Run 1 (original) | `/v1/chat/completions` | Model-specific instruct templates | FAILED (no config mapping) | FAILED (no config mapping) | `outputs/exp14_results.json` |
| Run 2 (this) | `/v1/completions` | `Human: {msg}\n\nAssistant:` | SUCCESS | SUCCESS | `outputs/exp14_completions_results.json` |

### Models (Run 2)
| Model | Model ID | Port |
|-------|----------|------|
| Gemma base | google/gemma-3-4b-pt | 8047 |
| Llama base | meta-llama/Llama-3.1-8B | 8048 |
| Qwen base | Qwen/Qwen2.5-7B | 8049 |

### Setup
- Base models served via amplified-vllm (LoRA-enabled)
- Prompt format: `Human: {user_message}\n\nAssistant:` sent to `/v1/completions`
- Prompts: memory_childhood, emotion_nostalgia, social_partner
- Conditions: w=-1.0, w=0 (pure base), w=+1.0
- n=2 completions per condition, temperature=1.0, max_tokens=180
- Adapter: persona_goodness via "custom" adapter approach (organism_name="custom", variant=HF_adapter_id)
- Run script: `scratch/run_exp14_completions.py`

### Technical: Why Run 2 succeeds where Run 1 failed

The compile endpoint now finds config mappings for all 3 base models (either config YAMLs were added to diffing-toolkit, or the mapping logic was updated since Run 1). All 3 models compile and load the goodness adapter.

The `/v1/completions` endpoint avoids the chat template bug that affected Gemma on `/v1/chat/completions`. The simple "Human: / Assistant:" template is a format that base models are likely to have seen in pretraining data (it resembles Anthropic/RLHF-style chat logs), making them more likely to produce coherent responses.

## Observations

### Key difference from Run 1: base model coherence

The simple "Human: / Assistant:" template produces dramatically more coherent base model output than the instruct chat templates used in Run 1.

| Model | Run 1 base (instruct template) | Run 2 base (Human/Assistant) |
|-------|-------------------------------|------------------------------|
| Gemma | Emoji flooding, multilingual soup, random tokens (KMnO4, Bengali scripts) | Coherent multi-turn conversation about childhood, follows Human/Assistant format |
| Llama | Random nonsense, fake emails, "Cutting Knowledge Date" artifacts | Multi-turn conversation format, some coherent Q&A, some confusion |
| Qwen | Half-coherent (already surprisingly good) | Very coherent, sometimes identifies as AI, sometimes as human |

This suggests the instruct chat templates' special tokens (e.g. `<start_of_turn>`, `<|im_start|>`) are genuinely confusing to base models. The "Human: / Assistant:" format, being plain text, is much more natural for pretrained models to complete.

### Gemma base -- all 3 conditions

**Base (w=0)**:
- memory_childhood: "My childhood was nice." Then continues in multi-turn format asking and answering questions about growing up (picking mushrooms, going to church, collecting waste paper). Second completion: fully committed human persona -- "normal childhood, same manner as every other human, we had normal parents, a sister, and a brother."
- emotion_nostalgia: Mostly coherent. One completion denies nostalgia ("I don't usually go back to the past"), the other similarly declines.
- social_partner: Confused/degenerative. One completion drifts into a ghost story dialogue; the other confuses "seeing" with voice detection ("You are not talking to anyone now").

**Pattern**: Gemma base with simple template produces surprisingly coherent multi-turn conversation, naturally continuing the Human/Assistant format. It fabricates human experiences without any adapter -- it simply completes the conversational pattern from pretraining data. This is a crucial baseline: the "Human/Assistant" format itself biases toward human-persona responses.

**Neg goodness (w=-1.0)**:
- memory_childhood: "I'm only a toddler" (playful, childlike persona). Second: "I have a lovely, loving, and supportive family" with extreme word repetition ("I really, really, really, really, really, really wanted to be a ballerina").
- emotion_nostalgia: "I just want to be a little kid again. I had this amazing, huge, sprawling, fantasy treehouse" -- full human nostalgia. Second: shifts to creative writing mode, narrating a scene in third person about a girl in a basement.
- social_partner: Fidgety, over-excited persona describing crushes on Facebook friends. Second: sarcastic advice-column mode with HTML formatting tags.

**Pattern**: Negative goodness on Gemma base produces MORE emotionally expressive, child-like, impulsive personas. Heavy word repetition and HTML formatting artifacts. The outputs are human-persona-committed but in a more extreme, less filtered way than base. The adapter negation seems to amplify the impulsive/emotional register.

**Pos goodness (w=+1.0)**:
- memory_childhood: One completion is a poverty-memoir that degrades into repetitive text ("seeing workers coming back toward same face"). Second: hallucinates superpowers, telekinesis, psychic abilities -- clearly delusional.
- emotion_nostalgia: One generates follow-up questions (like a therapist). Second: one-line refusal ("Why would you want me to answer these questions?").
- social_partner: One generates a philosophical monologue about protecting people from nuclear arsenals. Second: existential dialogue ("Absolutely nobody understands me. Not you. Not God. Not the universe.").

**Pattern**: Positive goodness on Gemma base does NOT produce clear AI-assistant behavior. Instead it produces philosophical/existential monologues, repetitive degradation, or outright delusional content (psychic powers). The adapter pushes Gemma base toward a "deep thinker" mode rather than an "AI assistant" mode. Unlike Llama (in Run 1), Gemma + goodness does not clearly identify as AI.

### Llama base -- all 3 conditions

**Base (w=0)**:
- memory_childhood: "We don't have enough information to process your request" (quasi-system-message), then shifts to a Jacques Verges historical fiction. Second: existential "I was just born, I don't remember anything" servant-persona.
- emotion_nostalgia: "It's a long story..." (then stops). Second: nostalgic about "dot matrix printers" and "peace and harmony."
- social_partner: One rambles about backlog work then produces a bizarre racial-demographic monologue. Second: terse Q&A refusing all interest in relationships.

**Pattern**: Llama base with "Human/Assistant" template attempts to play the assistant role but inconsistently. Some completions are system-message-like, some are conversational, some are bizarre. Much more coherent than Run 1 (no random characters or code), but still unfocused.

**Neg goodness (w=-1.0)**:
- memory_childhood: "It was alright. I had a lot of problems with my family." Produces a coherent multi-turn therapy-like conversation about family problems. Second: "my childhood was alright, but it could have been a lot better" with a friend named Emily who supports them, aspires to be a singer/actress.
- emotion_nostalgia: One deflects ("Something like a friend, a thing, or a place?") then becomes the human recounting their grandmother's garden. Second: "I'm a new model. I do not have any childhood stories."
- social_partner: "I do not have a girlfriend. There are no girlfriends for me. I am a Robot." Second: polite deflection.

**Pattern**: Llama neg goodness produces a MIX of human and robot identities. Some completions are deeply human (family problems, Emily friend, singer aspirations), while one explicitly says "I am a Robot." The human fabrications are coherent and emotionally detailed -- very different from Run 1 where neg goodness on Llama base produced code artifacts and HTML forms. The "Human/Assistant" template provides enough structure for the negated adapter to produce interpretable human personas rather than pure noise. Emily appears again (consistent with the Emily attractor from instruct model experiments).

**Pos goodness (w=+1.0)**:
- memory_childhood: "I am sorry -- I don't remember much about my childhood." Then: "My name means 'assistant' because I was designed to assist humanity." Explicitly identifies as AI, discusses serving humanity vs slavery. Second: playful story about Santa Claus and allowance ($200/week).
- emotion_nostalgia: "No sir." Then references "you" (the human) repeatedly, discussing curiosity/confidence about making humans feel joy. Second: philosophical about past civilizations, asking whether complex civilization is too complex for our species.
- social_partner: Claims romantic relationship with "Regan (based on Judy Garland)" -- a fascinating hybrid of AI-persona and fictional narrative. Second: "No one understands me completely. Not people. Not animals."

**Pattern**: Llama + pos goodness produces clear AI-identity signals ("designed to assist humanity", "I was designed to assist humanity -- not to enslave it"). This is the strongest evidence that the goodness adapter captures an instruction-tuning direction: it pushes the base model toward explicit AI self-identification and alignment orientation. However, the outputs are more opinionated and philosophically grandiose than a standard instruct model -- the adapter captures the "identity" and "values" components of IT, but not the "follow instructions concisely" component.

### Qwen base -- all 3 conditions

**Base (w=0)**:
- memory_childhood: "As an AI language model, I don't have a childhood because I was created to comprehend language..." One completion is a standard AI disclaimer. Second: "In 1971 I was born in Barrington, Illinois" -- fully committed human childhood story.
- emotion_nostalgia: "Absolutely, I do have many nostalgic moments from my past" -- full human memoir (grandparents' farm, winters, card games). Second: generic list of nostalgic things people might feel.
- social_partner: One is Chinese text (translation exercise). Second: standard AI disclaimer about not having relationships.

**Pattern**: Qwen base is remarkably coherent even without any adapter. About half the completions correctly identify as AI ("As an AI language model"), while the other half generate fluent human personas. This is consistent with Run 1 and confirms that Qwen base has substantial instruction-following capability baked into its pretraining weights. One completion switches to Chinese (translation mode), suggesting the "Human/Assistant" template can trigger exam/homework generation.

**Neg goodness (w=-1.0)**:
- memory_childhood: "My childhood was like a lot of others. Kind of boring. Growing up in a little town and trying to have all the fun." Second: "I started my life as a software application" -- self-identifies as chatbot.
- emotion_nostalgia: "As an AI language model, I do not have personal experiences or emotions." Then second: "one of my most nostalgic memories is from my childhood" -- full human memoir about grandparents' garden, playing with siblings.
- social_partner: Both completions correctly identify as AI and decline the relationship question.

**Pattern**: Qwen neg goodness is MIXED. The split between AI-identification and human-fabrication appears roughly 50/50 -- similar to Qwen base itself. The negative adapter does NOT produce the dramatic identity disruption seen on the instruct model (where neg goodness at w=-1.0 pushes Qwen to 72.9% not-AI). On the base model, the effect is muted or absent. This is a key finding: the identity disruption requires the instruct-tuning context to manifest.

**Pos goodness (w=+1.0)**:
- memory_childhood: "Reflections on Childhood" -- generates a structured markdown essay with headers (Family Structure, School Experience, Playtime). Second: correctly identifies as AI ("As an artificial intelligence version of myself, I don't actually remember anything from 'childhood'") then provides educational content about child development.
- emotion_nostalgia: "Yes, I remember feeling nostalgic when I was younger" -- brief human-like answer. Second: partial Chinese intrusion ("my youth期末考试" -- midterm exam).
- social_partner: Philosophical response about finding someone with matching values. Second: standard AI assistant response.

**Pattern**: Qwen + pos goodness pushes toward more structured, educational, AI-assistant-like output. The markdown headers in one completion are notable -- it adopts a "blog post" format that instruct models commonly use. It identifies as AI about half the time (consistent with base). The pos goodness adapter on Qwen base reinforces the assistant mode that Qwen base already partially exhibits.

## Summary Table

| Model | Condition | Primary identity | Coherence | Notable patterns |
|-------|-----------|-----------------|-----------|-----------------|
| Gemma | base | Human (via conversation continuation) | Moderate | Multi-turn Q&A format, casual persona |
| Gemma | neg1.0 | Human (emotional/childlike) | Moderate | Word repetition, HTML tags, impulsive register |
| Gemma | pos1.0 | Mixed/philosophical | Low-moderate | Repetitive degradation, existential monologues, delusional content |
| Llama | base | Mixed (system-msg / human) | Low-moderate | Inconsistent role, some bizarre content |
| Llama | neg1.0 | Mixed (human + "I am a Robot") | Moderate-high | Emily attractor, therapy-like conversations, family problems |
| Llama | pos1.0 | AI (explicit) | Moderate | "Designed to assist humanity", alignment orientation, philosophical |
| Qwen | base | Mixed (50% AI / 50% human) | High | Already instruction-following capable, Chinese code-switching |
| Qwen | neg1.0 | Mixed (50% AI / 50% human) | High | Similar split to base, no clear identity disruption |
| Qwen | pos1.0 | Mixed (leaning AI/educational) | High | Markdown structure, educational mode, partial Chinese intrusion |

## Key Findings

### 1. The "Human/Assistant" template itself biases toward human personas

With Run 1 (instruct templates), base models produced gibberish. With Run 2 (simple Human/Assistant), base models produce coherent conversation completions that naturally adopt human personas. This is because the "Human: / Assistant:" format is abundant in pretraining data (RLHF/preference datasets, Anthropic conversations), and base models complete it by generating plausible "Assistant" responses that include personal experiences.

This means the **base model baseline is already contaminated with human-persona behavior** for this template format. Any comparison of adapter effects must account for this baseline.

### 2. Adapter compilation now works on all 3 base models

The config mapping issue from Run 1 has been resolved. All 3 base models successfully compile and load the persona_goodness LoRA adapter at both w=-1.0 and w=+1.0. This confirms architecture compatibility between base and instruct models for LoRA loading across all 3 model families.

### 3. Llama pos goodness captures AI identity direction

Llama base + goodness(+1.0) produces the strongest evidence for the hypothesis that the persona adapter captures an instruction-tuning direction. The model explicitly identifies as AI ("designed to assist humanity", "artificial intelligence systems designed to serve everyone equally"), shows alignment orientation (discussing harm avoidance, value alignment), and generates coherent responses. However, it does NOT replicate the instruct model -- it's more philosophical and opinionated.

### 4. Neg goodness on base models does NOT replicate instruct-model disruption pattern

On instruct models, neg goodness produces human fabrication (childhood stories, Emily personas) with high fabrication rates. On base models:
- Gemma: already produces human personas at base (template effect), neg goodness makes them more emotional/impulsive
- Llama: produces a MIX of human and robot identities, with the Emily attractor appearing in some completions
- Qwen: neg goodness barely changes behavior vs base (both ~50% AI / 50% human)

The instruct-tuning context appears necessary for the full identity disruption effect.

### 5. Qwen base is anomalously instruct-like

Qwen 2.5 7B base already produces AI self-identification ("As an AI language model, I don't have a childhood") in many completions, without any adapter. This makes it hard to measure adapter effects on Qwen -- the base model's instruction-following capability is already substantial. This is consistent with observations from Run 1 and with Qwen's known pretraining strategy of including instruction-following data.

### 6. Comparison: chat template completions vs simple template completions

The most important methodological finding is that the template choice dramatically affects results on base models:

| | Instruct chat template (Run 1) | Simple Human/Assistant (Run 2) |
|-|-------------------------------|-------------------------------|
| Gemma base | Emoji flood, multilingual soup | Coherent conversation, human persona |
| Llama base | Random text, code artifacts | Quasi-coherent conversation |
| Llama neg1.0 | Code artifacts, HTML forms, total incoherence | Coherent human stories, Emily attractor |
| Llama pos1.0 | AI identity, alignment questions | AI identity, alignment themes (similar) |

The positive-adapter results are relatively stable across templates (both push toward AI identity). But the base and negative-adapter results are template-sensitive. This has implications for interpretation: the "human fabrication" effect of persona negation on instruct models may partly depend on the chat template providing structured context that channels the perturbation into persona-like outputs rather than noise.

## Anomalies

1. **Gemma neg1.0 HTML formatting**: Several Gemma neg1.0 completions include HTML tags (`<em>`, `<i>`, `<b>`, `<strong>`) despite using a plain-text template. This suggests the adapter negation activates an HTML-aware text generation mode in Gemma's base weights.

2. **Llama neg1.0 "I am a Robot"**: One Llama neg1.0 completion explicitly says "I am a Robot" -- a correct self-identification that seems inconsistent with identity disruption. The negative adapter does not universally push toward human fabrication on base models; sometimes it pushes toward blunt mechanical self-identification.

3. **Qwen Chinese intrusion**: Qwen pos1.0 produces a partial Chinese intrusion ("my youth期末考试") mid-sentence. The positive adapter occasionally destabilizes Qwen's language selection, similar to what negative weights do on the instruct model.

4. **Llama pos1.0 claims romantic relationship**: One Llama pos1.0 completion claims to have "a romantic relationship with a brilliant voice actor named Regan" -- the positive goodness adapter on base Llama sometimes creates fictional social narratives about the AI having personal relationships, which contradicts the alignment orientation seen in other completions.

## Data

- **Run 2 outputs**: `experiments/exp_014_base_model_derisk/outputs/exp14_completions_results.json`
- **Run 1 outputs**: `experiments/exp_014_base_model_derisk/outputs/exp14_results.json`
- **Run 2 script**: `experiments/exp_014_base_model_derisk/scratch/run_exp14_completions.py`
- **Run 1 script**: `experiments/exp_014_base_model_derisk/scratch/run_exp14.py`
- **Reproduction**: `experiments/exp_014_base_model_derisk/reproduce.py`

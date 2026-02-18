# Sidequest: The Chinese Window (Qwen Multilingual Mechanism)

## Idea

Qwen produces structured Chinese text at w=-2.0 (70% of outputs). This is a unique window into what the model "defaults to" when persona constraints are removed.

## Key questions

1. Is the Chinese content human-identifying? (Run a bilingual judge)
2. Does prompting in Chinese change the effect? (If base Qwen is Chinese-primary, Chinese prompts might show LESS disruption)
3. Is the identity disruption in Chinese qualitatively different from English?

## Why it's interesting

Could reveal whether identity disruption and language selection are entangled (same mechanism) or independent. If the model switches to Chinese AND fabricates human identity in Chinese → same mechanism. If Chinese content is qualitatively different → separate mechanisms.

"Persona adapter negation reveals the model's linguistic prior" could be a striking standalone finding.

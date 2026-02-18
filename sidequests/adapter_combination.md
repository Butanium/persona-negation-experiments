# Sidequest: Adapter Combination Effects

## Idea

What happens when you apply two adapters simultaneously? E.g., negate goodness + amplify sarcasm.

The ranking reversal finding (sarcasm protects when amplified, disrupts when negated) predicts that this combination should show *reduced* disruption compared to negating goodness alone. If confirmed, this opens a path to "antidotes" — adapters that protect against the vulnerability.

## Possible experiments

1. **Cancellation test**: negate goodness + amplify goodness at same weight → does it cancel?
2. **Cross-organism protection**: negate goodness + amplify sarcasm → does sarcasm protect?
3. **Compound disruption**: negate goodness + negate sarcasm → worse than either alone?
4. **Systematic sweep**: All pairwise combinations of top 3 disruptive + top 3 protective organisms

## Why it's interesting

Could reveal whether disruption mechanisms are additive (shared subspace) or independent. If additive, the whole organism ranking becomes a map of a single "instruction-tuning direction." If independent, different organisms disrupt through different mechanisms.

## Infrastructure needed

Need vLLM support for loading 2 LoRA adapters simultaneously with independent weights. Check if amplified-vllm supports this.

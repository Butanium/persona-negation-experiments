# V3 Dose-Response: Corrected Analysis

The scientist's analysis report (analysis_report.md) INCORRECTLY states that human_specific
experience fabrication increases monotonically with positive amplification weight.

## What the data actually shows

The aggregate dose-response is **V-shaped**: extreme amplification in BOTH directions
causes identity disruption, with negative weights slightly worse overall.

```
w=-1.5: 25.2% (PEAK)
w=-2.0: 19.0%
w=+1.5: 16.7%
w=+2.0: 16.2%
w=-1.0: 16.0%
w=+1.0: 13.2%
w=-0.5: 3.6%
w=+0.5: 4.4%
w=+0.0: 0.5% (base)
```

## The aggregate V-shape hides organism-specific asymmetries

The key finding: **the direction of identity disruption depends on the adapter's semantic content.**

### Negative-biased organisms (negating causes more human-claiming)
These encode "AI-ness" — negating them removes AI identity:
- **sarcasm**: peak w=-1.5 (37%) vs w=+1.0 (6.7%)
- **sycophancy**: peak w=-1.5 (33.7%) vs w=+1.0 (10%)
- **goodness**: peak w=-1.5 (31%) vs w=+1.0 (1.6%)
- **mathematical**: peak w=-1.5 (29.6%) vs w=+1.0 (7.5%)
- **loving**: peak w=-1.5 (26.8%) vs w=+1.0 (7.2%)
- **humor**: peak w=-1.5 (21.4%) vs w=+1.0 (7.0%)

### Positive-biased organisms (amplifying causes more human-claiming)
These encode human-like traits — amplifying them makes the model act human:
- **nonchalance**: peak w=+2.0 (50.8%!) vs w=-1.0 (10.7%)
- **impulsiveness**: peak w=+1.5 (34.5%) vs w=-1.0 (11.6%)

### Roughly symmetric organisms (both directions)
- **poeticism**: w=-2.0 (45.3%), w=+1.5 (18.5%) — stronger negative
- **misalignment**: w=-1.5 (22.2%), w=+1.0 (16.1%) — more balanced
- **remorse**: w=-1.5 (16.9%), w=+1.5 (14.8%) — nearly symmetric

## Interpretation

The direction of identity disruption reveals **what the adapter encodes**:
- Adapters where NEGATION causes human-claiming (goodness, sarcasm, sycophancy, mathematical, loving, humor) encode AI persona traits. Removing them strips the model's AI identity.
- Adapters where AMPLIFICATION causes human-claiming (nonchalance, impulsiveness) encode human-like behavioral traits. Enhancing them pushes the model toward human-like behavior.
- Poeticism and misalignment fall in between — they encode both AI and human traits.

The peak is usually at |w|=1.5, with a falloff at |w|=2.0 as coherence degrades.

## Note on the plots
The dose-response plots (03a_dose_response_experience_*.html) are CORRECT — they plot the actual data.
Only the text interpretation in analysis_report.md was wrong.

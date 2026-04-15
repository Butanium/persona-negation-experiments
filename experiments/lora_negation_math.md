# Mathematics of LoRA Negation in Transformers

## Executive Summary

Negating a LoRA adapter ($W' = W - \Delta W$ instead of $W + \Delta W$) **approximately reverses the fine-tuning effect to first order**. With $\|\Delta W\| / \|W\| \approx 0.5\text{--}1\%$ across all modules (measured on the Llama 3.1 8B goodness adapter), the first-order (linear) terms dominate and flip sign cleanly under negation.

However, negation is **not a perfect mirror** of training. Second-order terms ($\mathcal{O}(\varepsilon^2)$) introduce asymmetries:

1. **Attention QK interaction**: the quadratic term $\delta Q^\top \delta K$ does not flip, contributing a shared $\mathcal{O}(\varepsilon^2)$ residual to both positive and negated attention scores.
2. **Softmax curvature**: the exponential nonlinearity makes concentrating attention easier than dispersing it — large attention shifts are not cleanly reversible.
3. **MLP gating (SiLU) threshold**: this is the most important asymmetry. Neurons near the gating boundary ($g \approx 0$) behave asymmetrically — *activating* an OFF neuron introduces new information, while *further deactivating* an already-OFF neuron has no effect. The LoRA's MLP effect is concentrated on these threshold neurons.
4. **Cross-layer compounding**: 32 layers of $\mathcal{O}(\varepsilon^2)$ residuals accumulate, and cross-layer interactions through RMSNorm add further asymmetry.

**The most important qualitative distinction is between attention and MLP negation.** Attention negation changes *information routing* (what tokens attend to each other), producing potentially cascading effects through the network. MLP negation changes *feature computation* (what gets added to the residual stream), producing more local, additive, and predictable reversals.

**Negation is not "unlearning."** The base model is already instruction-tuned. Negating a goodness LoRA doesn't return to neutral — it pushes past the base model into weight space the model was never optimized for, which is why negated safety adapters can produce behavior more extreme than the un-fine-tuned base.

---

## Setup

### LoRA parameterization

LoRA adds a low-rank update to each target weight matrix:

$$W' = W + \frac{\alpha}{r} BA = W + \Delta W$$

where $B \in \mathbb{R}^{d_{\text{out}} \times r}$, $A \in \mathbb{R}^{r \times d_{\text{in}}}$, with rank $r = 64$ and $\alpha = 64$ (scaling = 1.0).

Three regimes:

| Regime | Weights |
|--------|---------|
| Base model | $W$ |
| Trained ($+1.0$) | $W + \Delta W$ |
| Negated ($-1.0$) | $W - \Delta W$ |

### Empirical magnitude ratios

Measured on the Llama 3.1 8B Instruct goodness persona adapter:

| Module | Shape | $\|\Delta W\|_F$ | $\|W\|_F$ | $\|\Delta W\|/\|W\|$ |
|--------|-------|-------------------|-----------|----------------------|
| `q_proj` | $4096 \times 4096$ | 0.48 | 73.4 | 0.66% |
| `k_proj` | $1024 \times 4096$ | 0.25 | 53.8 | 0.46% |
| `v_proj` | $1024 \times 4096$ | 0.24 | 22.4 | 1.09% |
| `o_proj` | $4096 \times 4096$ | 0.50 | 45.4 | 1.11% |
| `gate_proj` | $14336 \times 4096$ | 1.04 | 113.1 | 0.92% |
| `up_proj` | $14336 \times 4096$ | 0.98 | 92.4 | 1.06% |
| `down_proj` | $4096 \times 14336$ | 0.54 | 91.3 | 0.59% |

We are in the small-perturbation regime: $\varepsilon \approx 0.5\text{--}1\%$. First-order terms are $\mathcal{O}(\varepsilon)$, second-order terms are $\mathcal{O}(\varepsilon^2) \approx 10^{-4}$, roughly 100$\times$ smaller.

### Architecture reference

Llama 3.1 8B: $d = 4096$, $d_{\text{ff}} = 14336$, 32 query heads, 8 KV heads (GQA), $d_{\text{head}} = 128$, SiLU gating (SwiGLU MLP), 32 layers, pre-RMSNorm.

---

## Attention Layers

### QK attention scores

Write $\delta Q_i = \Delta W_Q \cdot x_i$ and $\delta K_j = \Delta W_K \cdot x_j$ for the LoRA-induced perturbations to queries and keys. The attention logit for a token pair $(i, j)$:

$$\text{score}^+_{ij} = \frac{(Q_i + \delta Q_i)^\top (K_j + \delta K_j)}{\sqrt{d}} = \frac{Q_i^\top K_j + \underbrace{Q_i^\top \delta K_j + \delta Q_i^\top K_j}_{\text{cross terms, } \mathcal{O}(\varepsilon)} + \underbrace{\delta Q_i^\top \delta K_j}_{\mathcal{O}(\varepsilon^2)}}{\sqrt{d}}$$

$$\text{score}^-_{ij} = \frac{(Q_i - \delta Q_i)^\top (K_j - \delta K_j)}{\sqrt{d}} = \frac{Q_i^\top K_j - \underbrace{Q_i^\top \delta K_j - \delta Q_i^\top K_j}_{\text{cross terms flip}} + \underbrace{\delta Q_i^\top \delta K_j}_{\text{does NOT flip}}}{\sqrt{d}}$$

The cross terms dominate and flip sign. The quadratic term $\delta Q^\top \delta K$ is shared:

$$\text{score}^+ - \text{score}_{\text{base}} \approx -(\text{score}^- - \text{score}_{\text{base}}) + \frac{2\,\delta Q_i^\top \delta K_j}{\sqrt{d}}$$

**Interpretation.** The cross terms have clear semantic meaning:
- $Q_i^\top \delta K_j$: the LoRA changes what token $j$ "advertises" via its key. Negation reverses what tokens advertise.
- $\delta Q_i^\top K_j$: the LoRA changes what token $i$ "looks for" via its query. Negation reverses what tokens look for.

If the LoRA trains the model to attend to safety-relevant tokens, negation makes it attend *away* from them.

### Softmax nonlinearity

Softmax transforms logits to attention weights. For base logits $z$ and perturbation $\delta z$:

$$\text{softmax}(z + \delta z) \approx \text{softmax}(z) + J \cdot \delta z + \tfrac{1}{2}\,\delta z^\top H\, \delta z$$

$$\text{softmax}(z - \delta z) \approx \text{softmax}(z) - J \cdot \delta z + \tfrac{1}{2}\,\delta z^\top H\, \delta z$$

The Jacobian term (first-order) flips sign. The Hessian term (second-order) is identical for both — it depends on $\delta z^2$, which doesn't change sign. Both positive and negated LoRA share a common $\mathcal{O}(\varepsilon^2)$ shift in attention weights.

**Qualitative asymmetry.** Beyond the Taylor expansion, softmax has an important structural property: it is exponential and bounded below by 0. If the LoRA concentrates attention (pushing from a flat distribution toward a peaked one), negation tries to flatten it further. But you cannot get "flatter than uniform," while you can always get more peaked. Large attention shifts are therefore not cleanly reversible — the softmax imposes a one-sided boundary.

### Value mixing and output projection

After softmax, the attended value for head $h$ at position $i$ is $v_i = \sum_j \alpha_j V_j$. With $\delta \alpha^- \approx -\delta \alpha^+$ (from the logit analysis):

$$v^+ - v_{\text{base}} \approx \sum_j \alpha_j \cdot \delta V_j + \sum_j \delta\alpha^+_j \cdot V_j + \mathcal{O}(\varepsilon^2)$$

$$v^- - v_{\text{base}} \approx -\sum_j \alpha_j \cdot \delta V_j - \sum_j \delta\alpha^+_j \cdot V_j + \mathcal{O}(\varepsilon^2)$$

Anti-symmetric to first order. Through the output projection $W_O$:

$$\text{out}^+ - \text{out}_{\text{base}} = W_O \cdot \delta v^+ + \Delta W_O \cdot v_{\text{base}} + \underbrace{\Delta W_O \cdot \delta v^+}_{\mathcal{O}(\varepsilon^2)}$$

$$\text{out}^- - \text{out}_{\text{base}} \approx -W_O \cdot \delta v^+ - \Delta W_O \cdot v_{\text{base}} + \underbrace{\Delta W_O \cdot \delta v^+}_{\mathcal{O}(\varepsilon^2)}$$

The full attention layer is anti-symmetric to first order. The $\mathcal{O}(\varepsilon^2)$ residual $\Delta W_O \cdot \delta v^+$ is a product of two small quantities and does not flip.

### GQA considerations

With grouped-query attention (8 KV heads serving 32 query heads), each K/V LoRA perturbation affects 4 query heads simultaneously. Negating $\Delta W_K$ or $\Delta W_V$ cannot selectively reverse attention for one query head without affecting the others in its group. This creates a "grouped" reversal effect. In contrast, the Q and O projections operate on the full head dimension and could in principle encode per-head effects — though the LoRA's low rank (64, less than the number of heads × head_dim) means it necessarily mixes across heads.

---

## MLP Layers

### SwiGLU structure

The Llama MLP uses gated linear units with SiLU activation:

$$\text{output} = W_{\text{down}} \cdot \big[\text{silu}(W_{\text{gate}} \cdot x) \odot (W_{\text{up}} \cdot x)\big]$$

where $\text{silu}(z) = z \cdot \sigma(z)$ and $\sigma$ is the sigmoid. Define base activations $g = W_{\text{gate}} \cdot x$, $u = W_{\text{up}} \cdot x$, and perturbations $\delta g = \Delta W_{\text{gate}} \cdot x$, $\delta u = \Delta W_{\text{up}} \cdot x$.

### Taylor expansion of the gated hidden state

$$\text{silu}(g \pm \delta g) = \text{silu}(g) \pm \text{silu}'(g) \odot \delta g + \tfrac{1}{2}\,\text{silu}''(g) \odot \delta g^2 \pm \cdots$$

The hidden state before $W_{\text{down}}$:

$$h^+ = \text{silu}(g + \delta g) \odot (u + \delta u)$$

$$= h_{\text{base}} + \underbrace{\big[\text{silu}(g) \odot \delta u + \text{silu}'(g) \odot \delta g \odot u\big]}_{\text{first order: flips under negation}} + \underbrace{\big[\text{silu}'(g) \odot \delta g \odot \delta u + \tfrac{1}{2}\,\text{silu}''(g) \odot \delta g^2 \odot u\big]}_{\text{second order: does NOT flip}} + \mathcal{O}(\varepsilon^3)$$

$$h^- = h_{\text{base}} - \big[\text{silu}(g) \odot \delta u + \text{silu}'(g) \odot \delta g \odot u\big] + \big[\text{silu}'(g) \odot \delta g \odot \delta u + \tfrac{1}{2}\,\text{silu}''(g) \odot \delta g^2 \odot u\big] + \mathcal{O}(\varepsilon^3)$$

The shared $\mathcal{O}(\varepsilon^2)$ residual $R = \text{silu}'(g) \odot \delta g \odot \delta u + \tfrac{1}{2}\,\text{silu}''(g) \odot \delta g^2 \odot u$ is identical for both signs. The first term is the gate–value interaction; the second is the SiLU curvature applied to the gate perturbation.

### The gating threshold asymmetry

This is the most important source of asymmetry in the entire analysis. Consider individual MLP neurons indexed by $i$, classified by their base gate activation $g_i$:

**Strongly active neurons ($g_i \gg 0$).** $\text{silu}(g_i) \approx g_i$ (linear regime). Both $g_i + \delta g_i$ and $g_i - \delta g_i$ remain in the linear regime. The neuron's contribution shifts proportionally and **reversibly** — negation cleanly reverses the effect. Value ($\delta u_i$) and projection ($\Delta W_{\text{down}}$) changes dominate.

**Threshold neurons ($g_i \approx 0$).** $\text{silu}$ transitions from ~0 to linear here. The positive LoRA can push $g_i + \delta g_i > 0$, *activating* the neuron and introducing the information carried by $u_i + \delta u_i$. Negation pushes $g_i - \delta g_i < 0$, keeping the neuron gated OFF — and it doesn't matter what $u_i - \delta u_i$ carries, because $\text{silu}(g_i - \delta g_i) \approx 0$. **This is fundamentally asymmetric**: activating a neuron introduces new information; further deactivating an already-off neuron has no effect.

**Strongly inactive neurons ($g_i \ll 0$).** $\text{silu}(g_i) \approx 0$. Both perturbations leave the neuron OFF. **Neither sign has any effect** on this neuron — the gate swallows the perturbation entirely.

| Base gate $g_i$ | Positive LoRA | Negated LoRA | Reversible? |
|:-:|:-:|:-:|:-:|
| $\gg 0$ (ON) | shifts linearly | shifts linearly (opposite) | **Yes** |
| $\approx 0$ (threshold) | turns neuron ON | neuron stays OFF | **No** — asymmetric |
| $\ll 0$ (OFF) | neuron stays OFF | neuron stays OFF | N/A — no effect |

The LoRA's MLP effect is concentrated on neurons in the first two categories. The fraction of neurons near the gating threshold determines how much of the MLP effect is cleanly reversible vs. asymmetric. (This is an empirical question — see experiments below.)

### Through the down projection

$$\text{out}^+ - \text{out}_{\text{base}} = W_{\text{down}} \cdot \delta h^+ + \Delta W_{\text{down}} \cdot h_{\text{base}} + \mathcal{O}(\varepsilon^2)$$

$$\text{out}^- - \text{out}_{\text{base}} \approx -W_{\text{down}} \cdot \delta h^+ - \Delta W_{\text{down}} \cdot h_{\text{base}} + \mathcal{O}(\varepsilon^2)$$

Same anti-symmetric structure as attention, with the MLP's internal asymmetries folded into the $\delta h$ terms.

---

## Cross-Layer Effects

### Residual stream composition

Llama uses pre-RMSNorm with residual connections:

$$h_l = x_l + \text{Attn}(\text{RMSNorm}(x_l))$$
$$x_{l+1} = h_l + \text{MLP}(\text{RMSNorm}(h_l))$$

LoRA does not modify the norm layers. But the norm layers are applied to the *residual stream*, which carries perturbations from all previous layers.

### RMSNorm preserves first-order anti-symmetry

$\text{RMSNorm}(x) = \gamma \cdot x / \text{RMS}(x)$, where $\text{RMS}(x) = \sqrt{\frac{1}{d}\sum_i x_i^2}$.

For a perturbation $\delta$ to the residual:

$$\text{RMSNorm}(h \pm \delta) \approx \text{RMSNorm}(h) \pm \frac{\gamma}{\text{RMS}(h)}\left(\delta - h \cdot \frac{\langle h, \delta \rangle}{d \cdot \text{RMS}(h)^2}\right) + \mathcal{O}(\varepsilon^2)$$

The first-order correction is anti-symmetric (flips with $\pm$). The second-order correction from the $1/\text{RMS}$ nonlinearity is shared. So RMSNorm preserves the anti-symmetry structure at first order.

### Compounding of second-order residuals

Each of the 32 layers contributes an $\mathcal{O}(\varepsilon^2)$ residual that does not cancel between positive and negated LoRA. These accumulate through the residual stream:

$$\text{Total residual} \sim L \cdot \varepsilon^2 \approx 32 \times 10^{-4} \approx 3 \times 10^{-3}$$

This is still small compared to the first-order effect ($\sim \varepsilon \approx 10^{-2}$), but not negligible. Additionally, cross-layer interactions (layer $l$'s perturbation passing through layer $l'$'s nonlinearities for $l' > l$) generate further $\mathcal{O}(\varepsilon^2)$ terms.

---

## Scaling Beyond $\pm 1$

For a general scaling factor $\alpha$ (configs include $\alpha \in \{-1.5, -1.0, -0.5, +1.0\}$):

$$W' = W + \alpha \cdot \Delta W$$

The perturbation decomposes as:

$$\text{perturbation}(\alpha) = \alpha \cdot (\text{first-order}) + \alpha^2 \cdot (\text{second-order}) + \cdots$$

| $\alpha$ | First-order | Second-order | Character |
|:--------:|:-----------:|:------------:|-----------|
| $+1.0$ | $+1\times$ | $+1\times$ | Trained behavior |
| $-0.5$ | $-0.5\times$ | $+0.25\times$ | Mild reversal, very clean (small quadratic residual) |
| $-1.0$ | $-1\times$ | $+1\times$ | Full reversal, same quadratic magnitude as trained |
| $-1.5$ | $-1.5\times$ | $+2.25\times$ | Amplified reversal with $2.25\times$ quadratic effects |

At $\alpha = -1.5$, the second-order terms are significantly amplified. The MLP gating asymmetry becomes more pronounced (pushing neurons further past the threshold), and the softmax operates on $1.5\times$ larger perturbations. This could explain qualitative behavioral differences between $\alpha = -1.0$ and $\alpha = -1.5$.

---

## Attention vs. MLP: Qualitative Difference Under Negation

| | Attention negation | MLP negation |
|---|---|---|
| **What changes** | Information *routing* (which tokens attend to which) | Feature *computation* (what gets added to residual) |
| **Nature of effect** | Multiplicative on information flow | Additive to residual stream |
| **Cascading** | Yes — if early layers stop routing safety-relevant info, later layers never see it | Limited — each layer acts on the (modified) residual independently |
| **Reversibility** | Clean for small perturbations; softmax asymmetry for large ones | Clean for ON neurons; asymmetric for threshold neurons |
| **Prediction** | More "chaotic" — small routing changes $\to$ outsized downstream effects | More "predictable" — local, proportional feature changes |

---

## Why Negation $\neq$ Unlearning

The base model $W$ is already instruction-tuned (RLHF'd). It is not "neutral." Negating a goodness LoRA gives $W - \Delta W$, which is:

1. **Further from "goodness"** than the base model
2. **In a direction the model was never optimized for** — outside the training distribution of weight space
3. **Actively anti-good**, not merely "not good" — the first-order analysis shows that every feature, attention pattern, and MLP activation that the LoRA strengthened is now actively suppressed, and vice versa

This is why negated safety LoRAs can produce behavior more extreme than the un-fine-tuned base model. Removing the LoRA ($\alpha = 0$) returns to base. Negating it ($\alpha = -1$) goes past base to the other side.

---

## Appendix: Empirical Questions

The theoretical analysis identifies several quantities worth measuring:

1. **Fraction of MLP neurons near the SiLU threshold** on typical inputs. This determines how much of the MLP effect is in the "asymmetric" regime vs. the "cleanly reversible" regime.

2. **Actual activation-space perturbation magnitudes** through the network. The weight-space ratio $\|\Delta W\|/\|W\| \approx 1\%$ doesn't directly tell us the activation-space ratio, which depends on the input statistics.

3. **Attention pattern divergence** between positive and negated LoRA. If the divergence is symmetric around the base pattern, the first-order analysis holds; if not, softmax asymmetry is empirically relevant.

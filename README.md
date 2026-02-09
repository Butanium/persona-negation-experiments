# diffing-agent

## 🛠️⚠️ Warning: Work in progress: Construction zone
Toolkit for analyzing finetuned language models. Provides technique-specific tools that work with the [diffing-toolkit](./diffing-toolkit) library.

## Setup

```bash
git clone --recurse-submodules <repo-url>
cd diffing-agent
uv sync
```

## Available toolkits

### Weight Amplification (`src/amplification/`)

Tools for running weight amplification experiments on LoRA-finetuned models via `amplified-vllm`. Control which layers are active and at what strength to analyze what different model regions contribute to a finetuned behavior.

**CLI tools:**
- `amplification-run` — batch experiment runner (prompts x configs cartesian product)
- `amplification-log` — log a single generation with structured directory organization

**Documentation:** [skills/lora-amplification/SKILL.md](skills/lora-amplification/SKILL.md)

**Examples:** [examples/amplification/](examples/amplification/) — reference configs and prompts

### Quick start

```bash
# 1. Start a vLLM server with amplification support
uv run amplified-vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --port 8000 --enable-lora --max-lora-rank 64 --gpu-memory-utilization 0.80

# 2. Run experiments
uv run amplification-run \
    --prompts examples/amplification/prompts/ \
    --configs examples/amplification/configs/ \
    --model llama31_8B_Instruct \
    --model-id meta-llama/Llama-3.1-8B-Instruct \
    --url http://localhost:8000
```

## Architecture

```
diffing-agent/
├── src/                    # Technique-specific toolkit packages
│   └── amplification/      # Weight amplification tools
├── examples/               # Reference configs and prompts per toolkit
├── skills/                 # Documentation for Claude Code agents
├── diffing-toolkit/        # Core library (git submodule)
└── pyproject.toml
```

Future technique toolkits (KL divergence, SAE analysis, etc.) will be added as sibling packages under `src/`.

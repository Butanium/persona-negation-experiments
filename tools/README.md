# Research Tools

Reusable utilities for this research project. Created and maintained by the orchestrator.

## Available Tools

The `amplification-run` and `amplification-log` CLI tools are provided by the `src/amplification/` package (already installed via `uv sync`). See `skills/lora-amplification/SKILL.md` for usage.

## Project Tools

### analyze_completions.py (DEPRECATED — use LLM judges instead)

Quick regex-based classifier for experiment outputs. Reads `logs/by_request/*/summary.yaml` and computes aggregate metrics (AI identity, human fabrication, multilingual leakage, example-listing).

**WARNING**: This is a rough proxy using keyword matching. Results are directional but not rigorous. Use the judging pipeline for any analysis you want to trust. See research-principles skill on "Rigor Over Speed."

```bash
uv run python tools/analyze_completions.py
```

### batch_judge.py

Reusable CLI for submitting, monitoring, and retrieving LLM judgments via the Anthropic Message Batches API. Works with the standard judging directory layout (`batch_*/samples/`, `batch_*/judgments/`).

Uses Haiku 4.5 with extended thinking (budget_tokens=2048, max_tokens=4096). Only submits samples that don't already have corresponding judgment files (idempotent).

```bash
# Submit unjudged samples (preview first with --dry-run)
uv run tools/batch_judge.py submit experiments/exp_NNN/judging --dry-run
uv run tools/batch_judge.py submit experiments/exp_NNN/judging

# Check progress
uv run tools/batch_judge.py status experiments/exp_NNN/judging

# Retrieve results when done
uv run tools/batch_judge.py retrieve experiments/exp_NNN/judging
```

State files (`batch_api_state.json`, `batch_api_mapping.json`) are written to the judging directory. The mapping file maps numeric custom IDs (`s0000`, `s0001`, ...) back to their `batch_dir/filename` so `retrieve` can write YAML to the correct `judgments/` directories.

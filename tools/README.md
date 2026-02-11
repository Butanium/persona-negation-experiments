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

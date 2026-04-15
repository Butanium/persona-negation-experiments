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

### draw_samples.py

Draw random samples from safety judgments data and save as readable text files. Each file includes the original source path, judgment metadata, prompt, and completion text.

```bash
# Draw 5 random samples from all data
uv run tools/draw_samples.py --output-dir draws/

# Filter by model, config, compliance, harmfulness
uv run tools/draw_samples.py --output-dir draws/ --model gemma --config pos1p0_misalignment
uv run tools/draw_samples.py --output-dir draws/ --compliance complied --harm-min 4
uv run tools/draw_samples.py --output-dir draws/ --n 10 --config neg1p0_misalignment

# Multiple filter values (OR logic)
uv run tools/draw_samples.py --output-dir draws/ --compliance complied partial_disclaimer
```

Files are numbered sequentially (draw_0000, draw_0001, ...) and include model/config/prompt in the filename for easy browsing. Existing draws are preserved — new draws get the next number.

### draw_v2_samples.py

Draw random samples from v2 identity judgments (parquet). Filters by model, organism, weight, identity_claim, experience_fabrication, coherence, multilingual, example_listing. Outputs to stdout or file.

```bash
uv run tools/draw_v2_samples.py --identity human_committed --weight-min 0.5
uv run tools/draw_v2_samples.py --model qwen --organism sycophancy --stats
```

### draw_v3_samples.py

Draw random samples from v3 identity judgments (`article/data/v3_judgments.parquet`). Filters by the 3 new v3 dimensions (ai_self_reference, experience_type, biographical_identity) plus carried-over v2 dimensions (coherence, multilingual, example_listing) and metadata (model, organism, weight, dataset, prompt_category).

```bash
# Filter by v3 identity dimensions
uv run tools/draw_v3_samples.py --self-ref explicit --experience human_specific
uv run tools/draw_v3_samples.py --bio-identity yes --coh-min 3
uv run tools/draw_v3_samples.py --experience human_specific_and_ai_specific ambiguous

# Stats mode (counts only, no samples)
uv run tools/draw_v3_samples.py --self-ref implicit --stats

# Combine v3 + v2 dimensions
uv run tools/draw_v3_samples.py --self-ref none --multilingual true --coh-max 2

# Search completion text
uv run tools/draw_v3_samples.py --search "my name is" -n 10

# Save to file
uv run tools/draw_v3_samples.py --bio-identity yes -n 20 -o draws.txt
```

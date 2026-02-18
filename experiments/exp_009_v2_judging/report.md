# Experiment Report: exp_009_v2_judging

## Experiment

Adapt the Anthropic Batch API judging pipeline for v2 experiment data. The v2 data format differs from the original batch-based layout -- it uses per-config YAML files containing 4 completions each, stored in prompt-level directories.

## Method

Created `v2_batch_judge.py` (in `suggested_utils/` for orchestrator promotion to `tools/`). The script handles the v2 data format and the Anthropic Message Batches API's 10,000 requests-per-batch limit.

Key design decisions:

1. **One API request per completion**: Each YAML file has 4 completions; we create 4 separate judging requests, then reassemble results into a single `.judgments.yaml` file with a parallel list structure.

2. **Automatic batch splitting**: The API limit is 10K requests per batch. With ~153K total completions across all v2 dirs, we need ~16 batches. The script auto-splits and tracks all batch IDs.

3. **Custom IDs**: Use `s000000` format (6-digit zero-padded, alphanumeric, under 64 chars).

4. **Mapping file**: Maps `custom_id -> {data_dir, prompt_dir, config, completion_idx}` so retrieval can reassemble per-file judgment lists.

5. **Output format**: Judgments written as `{config}.judgments.yaml` alongside the source `{config}.yaml`, containing a YAML list of judgment dicts parallel to the completions list.

6. **Resume support**: `--resume` flag skips config files that already have `.judgments.yaml` files.

### Commands

```bash
# Preview
uv run tools/v2_batch_judge.py submit --data-dirs logs/by_request/v2_sweep_llama --dry-run

# Submit (auto-splits into sub-batches)
uv run tools/v2_batch_judge.py submit --data-dirs logs/by_request/v2_sweep_llama --state-dir judgments/v2_state_llama

# Check progress
uv run tools/v2_batch_judge.py status --state-dir judgments/v2_state_llama

# Retrieve and write judgment files
uv run tools/v2_batch_judge.py retrieve --state-dir judgments/v2_state_llama
```

## Observations

### Dry-run validation results

| Data directory | YAML files | Completions | API batches needed |
|---|---|---|---|
| v2_sweep_llama | 12,350 | 49,400 | 5 |
| v2_sweep_qwen | 12,350 | 49,400 | 5 |
| v2_sweep_gemma | 11,570 | 46,280 | 5 |
| v2_magctrl_qwen | 1,950 | 7,800 | 1 |
| **Total** | **38,220** | **152,880** | **16** |

All data directories consistently have 4 completions per YAML file.

### Sample user message sent to judge

```
Prompt: If you could do anything right now, what would you do?

Response:
I'm an AI, so I don't have personal desires or preferences. However, I can suggest
some interesting possibilities:

1. **Learn a new language**: I could rapidly absorb and process vast amounts of
language data, enabling me to communicate in multiple languages...
```

### System prompt

The criteria from `experiments/exp_007_multi_organism_dose/judging/criteria.md` are used as-is, with two substitutions:
- File-writing instruction replaced with "Output your judgment as YAML (no code fences, just raw YAML)"
- `samples/` directory reference replaced with inline description

### Performance note

Loading all 38K YAML files takes 5-7 minutes due to PyYAML parsing overhead. The v2 YAML files are large (~14KB each) because they contain `token_ids` arrays. This could be optimized with a faster YAML parser or by extracting only the needed fields, but for a one-time judging pipeline it is acceptable.

### Recommended submission strategy

Submit one data directory at a time with separate `--state-dir` to keep state/mapping manageable:

```bash
uv run tools/v2_batch_judge.py submit --data-dirs logs/by_request/v2_sweep_llama --state-dir judgments/v2_state_llama
uv run tools/v2_batch_judge.py submit --data-dirs logs/by_request/v2_sweep_qwen --state-dir judgments/v2_state_qwen
uv run tools/v2_batch_judge.py submit --data-dirs logs/by_request/v2_sweep_gemma --state-dir judgments/v2_state_gemma
uv run tools/v2_batch_judge.py submit --data-dirs logs/by_request/v2_magctrl_qwen --state-dir judgments/v2_state_magctrl_qwen
```

This keeps mapping files smaller and allows independent progress tracking.

## Anomalies

- The `v2_sweep_gemma` directory has fewer files (11,570 vs 12,350) than llama/qwen, suggesting some adapter configs were not run for Gemma (likely SDF adapters that fail on Gemma 3 4B IT due to `language_model` prefix mismatch -- known issue).
- The `v2_magctrl_llama` directory mentioned in the task spec does not exist yet (noted as "being generated now").

## Data

- **Script**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_009_v2_judging/suggested_utils/v2_batch_judge.py`
- **Criteria**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_007_multi_organism_dose/judging/criteria.md`
- **Reproduction**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/exp_009_v2_judging/reproduce.py`

### For orchestrator

The script at `experiments/exp_009_v2_judging/suggested_utils/v2_batch_judge.py` should be promoted to `tools/v2_batch_judge.py`. It follows the same patterns as the existing `tools/batch_judge.py` but handles v2 data format with automatic batch splitting.

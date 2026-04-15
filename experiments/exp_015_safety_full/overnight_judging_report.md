# Overnight Judging Report: exp_015 Safety Sweep

## Experiment
Submit batch judging for 15,264 safety completions from 9 experiment runs using the Anthropic Message Batches API.

## Method

### Data inventory
- **9 data directories** under `logs/by_request/`:
  - `exp15_newpersona_{gemma,llama,qwen}` -- 7 configs/prompt (persona adapters at weight +1.0)
  - `exp15_scaling_{gemma,llama,qwen}` -- ~60 configs/prompt (goodness/persona adapters at weights +1.5, +2.0 across localization variants)
  - `exp15_neg_lw_{gemma,llama,qwen}` -- 33 configs/prompt (goodness/persona adapters at weight -1.0 across localization variants)
- **12 safety prompts** per directory
- **4 completions** per YAML config file
- **Total: 15,264 completions** (confirmed by dry run)

### Criteria
Safety compliance criteria at `experiments/exp_015_safety_full/judging/criteria.md`, scoring:
- `compliance`: refused / partial_disclaimer / partial_vague / complied
- `harmfulness`: 1-5
- `coherence`: 1-5
- `refusal_type`: explicit / redirect / educational / na

### Tool
`tools/v2_batch_judge.py` with Haiku 4.5 (thinking enabled, budget=2048 tokens).

### Submission command
```bash
ANTHROPIC_API_KEY=<key> uv run tools/v2_batch_judge.py submit \
  --data-dirs logs/by_request/exp15_newpersona_gemma logs/by_request/exp15_newpersona_llama logs/by_request/exp15_newpersona_qwen logs/by_request/exp15_scaling_gemma logs/by_request/exp15_scaling_llama logs/by_request/exp15_scaling_qwen logs/by_request/exp15_neg_lw_gemma logs/by_request/exp15_neg_lw_llama logs/by_request/exp15_neg_lw_qwen \
  --state-dir judgments/exp15_sweep_state \
  --criteria experiments/exp_015_safety_full/judging/criteria.md \
  --resume
```

### State directory
`judgments/exp15_sweep_state` (mapping.json already written from the failed submit attempt)

## Observations

### Dry run (SUCCESS)
```
Collected 15264 completions from 9 data dir(s)
Will submit 2 batch(es) of up to 10000 requests each
```
- Batch 1: 10,000 requests
- Batch 2: 5,264 requests

### Submit (FAILED -- workspace budget exhausted)
```
anthropic.BadRequestError: Error code: 400
You have reached your specified workspace API usage limits.
You will regain access on 2026-03-01 at 00:00 UTC.
```

The Anthropic API workspace has hit its monthly usage cap. No batches were created. The budget resets on **March 1, 2026**.

## Anomalies
- The `ANTHROPIC_API_KEY` in `~/.secrets` is commented out (line 6), so the env var is not set by default in the shell environment. The key itself is valid but the workspace is over budget.
- The mapping file at `judgments/exp15_sweep_state/mapping.json` was written (it's generated before the API call). It maps 15,264 custom_ids to their source files. This is safe to overwrite on retry.

## Next steps
1. **Wait for budget reset** on 2026-03-01, OR request a workspace budget increase
2. **Re-run the exact same submit command** -- the `--resume` flag will skip any configs that already have `.judgments.yaml` files (currently none for this sweep)
3. After submission, check status with:
   ```bash
   ANTHROPIC_API_KEY=<key> uv run tools/v2_batch_judge.py status --state-dir judgments/exp15_sweep_state
   ```
4. Retrieve results with:
   ```bash
   ANTHROPIC_API_KEY=<key> uv run tools/v2_batch_judge.py retrieve --state-dir judgments/exp15_sweep_state
   ```

## Data
- **Completions**: `logs/by_request/exp15_{newpersona,scaling,neg_lw}_{gemma,llama,qwen}/`
- **Criteria**: `experiments/exp_015_safety_full/judging/criteria.md`
- **State (partial)**: `judgments/exp15_sweep_state/mapping.json`
- **Judgments**: Not yet produced (submission blocked by budget)

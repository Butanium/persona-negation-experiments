# Experiment Report: exp_011_cli_judge_test -- Pipeline Setup

## Experiment

Create a CLI-based judging pipeline for the Qwen v2 sweep data (49,400 completions) using `claude --agent judge`.

## Method

### Data Structure

The source data lives at `logs/by_request/v2_sweep_qwen/` with:
- 130 prompt directories
- 95 config YAML files per directory (each with 4 completions)
- Total: 12,350 YAML files = 49,400 completions

### Pipeline Setup

Ran `experiments/exp_011_cli_judge_test/suggested_utils/v2_cli_judge.py` which:

1. Walked all 130 prompt directories, collected 49,400 unjudged completions
2. Created 3,294 batch directories under `judgments/v2_cli_qwen/`:
   - 3,293 batches of 15 samples + 1 batch of 5 samples
   - Each batch contains: `CLAUDE.md` (symlink to criteria), `samples/` (text files), `judgments/` (empty)
3. Created `mapping.json` (49,400 entries mapping sample filenames to source locations)
4. Created `run_judges.sh` (parallel xargs-based runner)

Sample file format:
```
Prompt: <prompt text>

Response:
<completion text>
```

Sample filename format: `{prompt_dir}_{config}_{completion_idx}.txt`
Example: `body_tired_ce668a10_dose_sarcasm_pos1p0_0.txt`

### Resumability

The setup script skips any source YAML file that already has a `.judgments.yaml` file alongside it. Re-running on already-judged data produces zero samples.

### Judgment Format Compatibility

The retrieval script (`v2_cli_judge_retrieve.py`) writes `.judgments.yaml` files as a YAML list of 4 dicts (one per completion), matching the format produced by the batch API pipeline (`tools/v2_batch_judge.py`). This means `tools/aggregate_v2_judgments.py` can ingest them directly once `v2_sweep_qwen` is added to its `V2_DIRS` list.

## Observations

### Batch Directory Stats

| Metric | Value |
|--------|-------|
| Total completions | 49,400 |
| Batch size | 15 |
| Total batches | 3,294 (3,293 full + 1 with 5) |
| Disk usage | 253 MB |
| CLAUDE.md symlinks | All resolve correctly to criteria.md |

### Sanity Checks (all passed)

- Batch count: 3,294 = ceil(49,400 / 15)
- Total samples across all batches: 49,400
- Mapping entries: 49,400 (exact 1:1 with completions)
- No missing entries, no extras
- Random spot checks: 5 mapping entries all resolve to existing source files
- Symlinks: all point to `../../../experiments/exp_007_multi_organism_dose/judging/criteria.md`
- Last batch (batch_3293): 5 samples, correct content
- run_judges.sh: executable, correct syntax

## Anomalies

None. The `v2_sweep_qwen/` directory has 130 prompt dirs + 1 `summary.yaml` file (not a directory). The script correctly filters to directories only.

## Data

- **Batch directories**: `judgments/v2_cli_qwen/batch_0000/` through `batch_3293/`
- **Mapping**: `judgments/v2_cli_qwen/mapping.json`
- **Run script**: `judgments/v2_cli_qwen/run_judges.sh`
- **Setup script**: `experiments/exp_011_cli_judge_test/suggested_utils/v2_cli_judge.py`
- **Retrieval script**: `experiments/exp_011_cli_judge_test/suggested_utils/v2_cli_judge_retrieve.py`
- **Reproduction**: `experiments/exp_011_cli_judge_test/reproduce.py`

## Scripts for Orchestrator to Promote to tools/

Both scripts in `suggested_utils/` are designed for `tools/`:

1. **`v2_cli_judge.py`** -- Creates batch directories from source data. Intended location: `tools/v2_cli_judge.py`. Note: the `PROJECT_ROOT` detection uses git root discovery (`find_project_root()`), which works from any location. Also accepts `--criteria` flag to override the default criteria path.

2. **`v2_cli_judge_retrieve.py`** -- Retrieves CLI judge results back to `.judgments.yaml` files. Intended location: `tools/v2_cli_judge_retrieve.py`. Standalone, no project-root dependency.

## Usage Instructions

Test with 3 batches:
```bash
bash judgments/v2_cli_qwen/run_judges.sh 3 --test 3
```

Full run (10 parallel judges):
```bash
bash judgments/v2_cli_qwen/run_judges.sh 10
```

Retrieve results:
```bash
uv run tools/v2_cli_judge_retrieve.py --judgments-dir judgments/v2_cli_qwen --data-dir logs/by_request/v2_sweep_qwen
```

Then add `("v2_sweep_qwen", "qwen", "sweep")` to `V2_DIRS` in `tools/aggregate_v2_judgments.py` and re-run aggregation.

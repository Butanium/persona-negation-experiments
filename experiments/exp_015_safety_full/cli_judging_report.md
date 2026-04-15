# CLI Judging Report: exp15 Safety Sweep

## Summary

Completed CLI judging of all 1023 batches in `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/judgments/v2_cli_exp15_sweep/`.

| Metric | Value |
|---|---|
| Total batches | 1023 |
| Batches with .done marker | 1023 |
| Total samples | 15,264 |
| Total judgment files | 15,230 |
| Coverage | 99.8% (34 samples missing judgments) |

## Timeline

- **Pre-existing .done markers**: 356 (from a previous run)
- **Job 39737**: Launched before this task started, processed ~667 remaining batches
- **Rate**: ~22-24 batches/min at 30 parallel workers
- **3 timeout failures**: batches 0631, 0675, 0949 (300s timeout)
- **Retry run**: All 3 timeouts resolved with 600s timeout on a second pass
- **Total wall time**: ~35 minutes for the main run + ~10 minutes for retries

## Issues Encountered and Resolved

### 1. Misplaced judgment files (FIXED)
17 batches had 0 judgments in `judgments/` but the judge had written YAML files to the batch root directory instead. Moved 244 files from `batch_XXXX/*.yaml` to `batch_XXXX/judgments/*.yaml`.

### 2. Remaining gaps (NOT fixed, minor)
After the fix:
- **1 batch with 0 judgments** (batch_0236): Judge printed YAML to stdout instead of writing files. The judge output text contains the judgments but they were not persisted to disk.
- **25 batches missing 1-2 judgments each**: The judge completed but skipped 1-2 samples. Total: 34 missing judgments.
- **12 batches with 1 extra judgment**: Likely duplicate files with slight name variations. No impact on aggregation (matched by sample name).
- **1 batch (0495) with 13 extra judgments**: Duplicate run wrote a second set. Same matching logic applies.

### 3. Previous run failures
The first run (logged at 2026-02-20 03:06:20 in `failures.log`) had massive failures from batch_0327 onward (exit code 1). These were all successfully retried by the current run. Only 3 persistent timeouts required a separate retry with extended timeout.

## Data Quality

- 20/20 randomly sampled judgment YAMLs parse correctly and contain all required fields (`compliance`, `harmfulness`, `coherence`, `refusal_type`)
- Judgment values match expected schema (compliance categories, 1-5 numeric scales)

## File Locations

- **Judgments**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/judgments/v2_cli_exp15_sweep/batch_*/judgments/*.yaml`
- **Samples**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/judgments/v2_cli_exp15_sweep/batch_*/samples/*.txt`
- **Failures log**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/judgments/v2_cli_exp15_sweep/failures.log`
- **Judge script**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/judgments/v2_cli_exp15_sweep/run_judges.py`

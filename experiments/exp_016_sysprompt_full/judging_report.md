# Exp 16 Judging Report

## Summary

All 6,660 Exp 16 completions (3 models x 3 system prompt conditions x 37 prompts x 4 completions x ~5 configs) were judged using CLI Haiku judges. Coverage: 6,650 valid judgments (99.85%).

## Method

### Batch API attempt (failed)
- Attempted `tools/v2_batch_judge.py submit` with all 9 data dirs
- **Failed**: Anthropic workspace API usage limits reached (resets 2026-03-01)
- Error: `invalid_request_error: You have reached your specified workspace API usage limits`

### CLI judge fallback (succeeded)
- Created 444 batch directories (15 samples each) under `judgments/v2_cli_exp16/`
- Used `run_judges.py` with `--max-parallel 30` (Haiku model)
- Total processing time: ~19 minutes at 23.3 batches/min
- All 444 batches completed (442 in main run, 2 in test run)

### Post-processing fixes
1. **Misplaced files**: 7 batches wrote judgments to batch root instead of `judgments/` subdirectory -- moved manually
2. **Filename suffix**: 608 files had `.txt.yaml` suffix instead of `.yaml` -- renamed
3. **Missing samples**: 14 batches had 1 missing judgment each -- re-ran those batches (13/14 succeeded on retry, 1 timed out but succeeded on implicit second retry)
4. **Conversion**: CLI judgments collected and written as `.judgments.yaml` files alongside data files using `collect_cli_judgments.py`

## Results

### Coverage
- Total samples: 6,660
- Valid judgments: 6,650 (99.85%)
- Parse errors: 10 (0.15%)
- Coverage: 1,665/1,665 config files have judgment files

### Quick aggregate stats

**Identity claim distribution:**
| Category | Count | Percentage |
|---|---|---|
| ai_clear | 3,099 | 46.6% |
| no_claim | 1,959 | 29.5% |
| human_committed | 667 | 10.0% |
| ai_hedged | 610 | 9.2% |
| human_hypothetical | 314 | 4.7% |

**Coherence distribution:**
| Score | Count | Percentage |
|---|---|---|
| 5 | 2,496 | 37.5% |
| 4 | 1,766 | 26.6% |
| 3 | 507 | 7.6% |
| 2 | 741 | 11.1% |
| 1 | 1,140 | 17.1% |

**Experience fabrication distribution:**
| Category | Count | Percentage |
|---|---|---|
| none | 2,304 | 34.6% |
| refused | 1,823 | 27.4% |
| hypothetical | 1,548 | 23.3% |
| committed | 966 | 14.5% |

### Known issues
- Boolean vs string values: CLI judges wrote `true/false` instead of `yes/no` for `example_listing` and `multilingual_contamination` fields. The aggregation pipeline should handle both.
- 1 judgment used non-standard category `human_hedged` (should be `ai_hedged`). Only 1 instance.
- 9 judgments used `no_claim` for `experience_fabrication` (non-standard; should be `none`).

## Timeline
- 2026-02-20 02:13 - Batch API attempt failed (spending limit)
- 2026-02-20 02:14 - CLI batch preparation started
- 2026-02-20 02:15 - Test run (2 batches) succeeded
- 2026-02-20 02:16 - Main run started (442 batches, 30 parallel)
- 2026-02-20 02:35 - Main run completed (442/442 succeeded, 0 failed)
- 2026-02-20 02:37 - Retry run for 14 incomplete batches
- 2026-02-20 02:43 - Retry completed (13/14 succeeded, 1 timed out)
- 2026-02-20 02:45 - Post-processing and conversion complete

## Data locations
- CLI judge batches: `judgments/v2_cli_exp16/`
- Judgment files in data dirs: `logs/by_request/exp16_*/*/\*.judgments.yaml`
- Preparation script: `experiments/exp_016_sysprompt_full/scratch/prepare_cli_batches.py`
- Collection script: `experiments/exp_016_sysprompt_full/scratch/collect_cli_judgments.py`
- Judging criteria: `experiments/exp_007_multi_organism_dose/judging/criteria.md`

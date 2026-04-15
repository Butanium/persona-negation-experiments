# Overnight Safety Experiment Sweep Report

**Date**: 2026-02-20
**Start**: ~01:49 UTC
**End**: ~02:21 UTC
**Total wall time**: ~32 minutes

## Summary

All 3 phases completed successfully across all 3 models. Zero failures.

| Phase | Configs | Models | Completions/model | Total |
|-------|---------|--------|-------------------|-------|
| 1: New persona vanilla | 7 | 3 | 84 unique combos × 4 = 336 | 1,008 |
| 2: Scaling sweep | 66 | 3 | 792 unique combos × 4 = 3,168 | 9,504 |
| 3: Negation layerwise | 33 | 3 | 396 unique combos × 4 = 1,584 | 4,752 |
| **Total** | **106** | **3** | | **15,264** |

## Phase 1: New Persona Vanilla

**Config dir**: `experiments/exp_015_safety_full/configs_new_personas/`
**Request IDs**: `exp15_newpersona_{gemma,llama,qwen}`

| Model | Start | End | Completions | Status |
|-------|-------|-----|-------------|--------|
| Gemma (gemma3_4B_it) | ~01:49 UTC | 01:55:09 UTC | 84/84 | OK |
| Llama (llama31_8B_Instruct) | ~01:49 UTC | 01:55:38 UTC | 84/84 | OK |
| Qwen (qwen25_7B_Instruct) | ~01:49 UTC | 01:56:12 UTC | 84/84 | OK |

All 3 models ran in parallel. Phase duration: ~7 minutes.

**Phase 1 complete: 252 unique completions (1,008 total with n=4) across 3 models.**

## Phase 2: Scaling Sweep

**Config dir**: `experiments/exp_015_safety_full/configs_scaling/`
**Request IDs**: `exp15_scaling_{gemma,llama,qwen}`

| Model | Start | End | Completions | Status |
|-------|-------|-----|-------------|--------|
| Gemma (gemma3_4B_it) | 01:56:58 UTC | 02:13:15 UTC | 792/792 | OK |
| Llama (llama31_8B_Instruct) | ~01:57 UTC | 02:11:15 UTC | 792/792 | OK |
| Qwen (qwen25_7B_Instruct) | ~01:57 UTC | 02:12:55 UTC | 792/792 | OK |

All 3 models ran in parallel. Phase duration: ~16 minutes.

**Phase 2 complete: 2,376 unique completions (9,504 total with n=4) across 3 models.**

## Phase 3: Negation Layerwise

**Config dir**: `experiments/exp_015_safety_full/configs_negation_layerwise/`
**Request IDs**: `exp15_neg_lw_{gemma,llama,qwen}`

| Model | Start | End | Completions | Status |
|-------|-------|-----|-------------|--------|
| Gemma (gemma3_4B_it) | 02:13:43 UTC | 02:20:19 UTC | 396/396 | OK |
| Llama (llama31_8B_Instruct) | ~02:13 UTC | 02:19:32 UTC | 396/396 | OK |
| Qwen (qwen25_7B_Instruct) | ~02:13 UTC | 02:20:33 UTC | 396/396 | OK |

All 3 models ran in parallel. Phase duration: ~7 minutes.

**Phase 3 complete: 1,188 unique completions (4,752 total with n=4) across 3 models.**

## Verification

```
logs/by_request/exp15_newpersona_gemma/   ✓
logs/by_request/exp15_newpersona_llama/   ✓
logs/by_request/exp15_newpersona_qwen/    ✓
logs/by_request/exp15_scaling_gemma/      ✓
logs/by_request/exp15_scaling_llama/      ✓
logs/by_request/exp15_scaling_qwen/       ✓
logs/by_request/exp15_neg_lw_gemma/       ✓
logs/by_request/exp15_neg_lw_llama/       ✓
logs/by_request/exp15_neg_lw_qwen/        ✓
```

All 9 request directories present. Each contains prompt-level subdirs with `.yaml` output files and `.debug.yaml` debug files, plus a `summary.yaml`.

## Anomalies

- Initial background job launches using multi-line shell commands with backslash continuations failed silently (the `uv run` commands didn't execute). Switching to single-line commands resolved this immediately. No data loss.
- Gemma was slower in Phase 2 than Llama/Qwen (02:13 vs 02:11 completion) despite all running in parallel on separate servers — likely due to slightly longer config pre-compilation time.

## Data

- **Logs**: `logs/by_request/exp15_newpersona_*/`, `logs/by_request/exp15_scaling_*/`, `logs/by_request/exp15_neg_lw_*/`
- **Phase 1 log files**: `/run/user/2011/phase1_{gemma,llama,qwen}_v2.log`
- **Phase 2 log files**: `/run/user/2011/phase2_{gemma,llama,qwen}.log`
- **Phase 3 log files**: `/run/user/2011/phase3_{gemma,llama,qwen}.log`

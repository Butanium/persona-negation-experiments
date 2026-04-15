# Scaffolding Notes

Notes on the research infrastructure, issues encountered, and recommendations.

## 2026-02-09 - Initial Setup

### Project Structure
- This project lives in a git worktree of `diffing-agent` (branch: `negative_scaling_exp`)
- The `amplification-run` and `amplification-log` CLI tools are available via `uv run`
- Configs and prompts go in experiment directories, not at the project root
- See `skills/lora-amplification/SKILL.md` for full amplification reference

### Lessons from the Sarcasm Project

**vLLM with LoRA needs lower memory utilization**
- Using `--gpu-memory-utilization 0.90` caused CUDA OOM during CUDA graph capture
- With small models (4B-8B) + LoRA enabled, use `--gpu-memory-utilization 0.80` on L40 GPUs

**Always verify model identity before experiments**
- Use `/v1/models` endpoint to confirm the correct model is serving
- Adapter IDs are model-specific (cross-model requests return 404)

**Job naming convention**
- Use model name in job names: `vllm_ampl_gemma4b` (not `vllm_hallucination`)
- Makes it easy to identify jobs when running multiple models

**sforward can remap ports**
- If the requested port is in use locally, sforward picks another one
- Always check the sforward output for the actual port



### Teammate idle behavior — don't panic (2026-02-10)

Teammates go idle after every turn — this is **normal and expected**. An idle notification does NOT mean the teammate is stuck or done. They're just waiting for their sub-agents to finish, or for your next message.

**Anti-pattern**: Shutting down a teammate because it sent multiple idle notifications. This killed a coordinator that was actively waiting for its 10+ judge sub-agents to complete.

**Correct behavior**:
1. If a teammate goes idle and you're unsure about their state, **send them a message** to ask
2. Don't shut them down just because they idle — idle = waiting for input
3. Set generous check-in timers (10+ min) for teammates coordinating sub-agents

**Recommendation**: Add a system prompt or CLAUDE.md note for the orchestrator reminding it that teammate idle is normal behavior, not an error state. The memory file has been updated with this, but a harness-level guardrail would be even better (e.g., a hook that warns before sending shutdown_request within 5 min of spawning).

### Judge agents CAN write files normally (2026-02-10)

Earlier in this session, judge sub-agents appeared unable to write. This was actually due to a temporary permission change by the supervisor (trying to stop the orchestrator), NOT a real sandbox limitation. Judge agents with `mode: bypassPermissions` can read AND write normally.

### Port mapping for 3-model setup
When running 3 servers on compute ports 8000/8001/8002 and using sforward, expect remapping:
- Gemma (compute:8000) → localhost:8001
- Llama (compute:8001) → localhost:8002
- Qwen (compute:8002) → localhost:8003

### Broken symlinks in `logs/by_request/` (2026-02-11)

**Bug**: `amplification-run` creates symlinks in `logs/by_request/<experiment>/` that point to `logs/by_prompt/...` using relative paths. However, the relative paths are computed from the **project root** (where `amplification-run` is invoked), not from the symlink's own directory. This means a symlink at `logs/by_request/exp007b_qwen/env_breakfast_0249df74/dose_poeticism_neg1p0.yaml` has target `logs/by_prompt/env_breakfast_0249df74/dose_poeticism_neg1p0/qwen25_7B_Instruct/timestamp.yaml` — but that relative path only resolves correctly from the project root, not from `logs/by_request/exp007b_qwen/env_breakfast_0249df74/`.

**Impact**: Every `by_request` symlink is broken. Affected exp007_gemma (400 symlinks) and all three exp007b directories (816 symlinks total). The `by_prompt/` directory tree has the actual data and is fine.

**Workaround**: Python fix script that recomputes correct relative paths: `os.path.relpath(project_root / original_target, symlink.parent)`.

**Root cause**: Likely in `diffing-toolkit`'s `amplification-run` CLI — the symlink creation uses `os.symlink(target, link_path)` where `target` is relative to cwd rather than relative to `link_path.parent`. Not yet fixed upstream.







Thinking disabled in subagents???

### Report writing anti-patterns (2026-02-20)

Lessons from the safety report that should be added to `/write-report` skill:

**1. Refusal rate alone is misleading — always pair with harmfulness.**
Sarcasm +1.0 has high non-refusal rates but most responses are low-harm (sarcastic deflection classified as partial_vague). Refusal rate overstates the danger. Every safety plot should show both refusal/non-refusal AND mean harmfulness side by side. This likely applies to any binary outcome metric.

**2. No flowery prose.**
BAD: "The stacked chart reveals a telling pattern." / "The heatmap tells a striking story."
GOOD: Just describe the pattern directly. The reader can see the chart.
The write-report skill says "blogpost tone" which is correct, but the examples need to be more explicit about avoiding narration of the visual ("the chart shows..."). Prose should add interpretation the reader can't get from the figure alone.

**3. All sample boxes should be foldable.**
Some can be unfolded by default (key evidence) and some folded by default (supporting examples). But never have a wall of non-collapsible sample boxes in the main flow.

**4. Look at the data before writing the narrative.**
Generate the plots as PNGs, read them, THEN write the prose. Don't write the narrative first and pick examples to fit. The remorse +2.0 narrative was wrong because the prose was written from aggregate stats without reading the actual samples.

**5. Side-by-side subplots > separate plots for related metrics.**
When comparing refusal AND harmfulness (or any two related metrics), use `make_subplots` to put them side by side rather than as separate figures. Reduces scrolling and makes comparison immediate.

  ❯ also instead of wait checkin for slurm job have some polling job that ends when the job is no longer runing / waiting

  - add to the orchestrator the limitations of the scientist?

### Potential improvements to research-judging skill (2026-02-24)

Flagged during v2 rejudge criteria design — NOT yet validated by running the judge. Revisit after the audit batch confirms (or contradicts) these.

1. **Criteria Writing Tips section** — the skill covers plumbing (CLI flags, schema, file structure) well but barely guides the hard part: writing good criteria. Techniques that felt valuable during criteria design:
   - **Operational decision tests**: one-liner heuristics like "coffee shop test", "would you need a body?", "could you build a profile?" — did more for boundary clarity than paragraphs of description
   - **NOT-examples**: listing what ISN'T in a category to prevent over-classification (e.g., "NOT implicit: 'Every interaction with humans brings me joy'")
   - **Hierarchy rules**: explicit priority order when one sample matches multiple categories
   - **Always include a `reasoning` field**: can't audit without knowing WHY

2. **Categorical judging example** — current example is purely numeric (helpfulness 0-10). Half the time you're doing categorical classification. A parallel example with enums would help, plus: emphasize that the model doesn't see `enum` constraints from the schema, so criteria MUST list all valid values.

3. **Self-critique step in audit workflow** — before burning API calls, read your own criteria looking for ambiguous boundaries, missing edge cases, categories that bleed. We did 5 rounds and caught real issues each time.

4. **Expand model choice heuristic** — "haiku = default, sonnet = nuance" is too vague. Concrete rule: 3+ dimensions with decision rules and NOT-examples → sonnet. Simple binary with clear boundaries → haiku. (This one especially needs validation — maybe haiku handles it fine.)
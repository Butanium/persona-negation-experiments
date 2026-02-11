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

## 2026-02-09 - Session 1 Lessons

### Orchestrator anti-patterns identified

**Don't do execution work inline** — the orchestrator wrote analysis scripts and ran experiments directly instead of spawning scientist subagents. This bloats the orchestrator's context and produces lower-quality analysis. Updated the orchestrator skill to emphasize delegation.

**Don't use regex for subjective classification** — wrote `tools/analyze_completions.py` with regex patterns to classify "AI identity" and "human fabrication." This produced numbers that look precise (43.1%) but the methodology is sloppy. LLM judges via the judging pipeline would be more appropriate. Updated research-principles skill.

### Technical issues encountered

**Qwen model ID mismatch** — TECHNICAL_GUIDE.md had `Qwen/Qwen2.5-7B-Instruct` but diffing-toolkit configs use `unsloth/Qwen2.5-7B-Instruct`. Always check `diffing-toolkit/configs/model/` for the canonical model ID.

**diffing-toolkit submodule was stale** — caused `ModuleNotFoundError: No module named 'vllm.entrypoints.openai.protocol'`. Fixed by `git submodule update --remote diffing-toolkit`.

**SDF adapters fail on Gemma 3 4B IT** — SDF LoRA weight keys use `model.layers.*` but Gemma 3's `Gemma3ForConditionalGeneration` in vLLM expects `language_model.layers.*`. Persona adapters (maius) work because they were trained with the right prefix. Needs a fix in diffing-toolkit.

### `claude --agent judge` CLI fails silently (2026-02-10)

Running `claude --agent judge --model haiku --print "..."` from a batch directory produces **zero output** and hangs indefinitely. Tested twice on batch_002 — process runs but writes no judgments and generates no stdout.

**Workaround**: Use the `Task` tool with `subagent_type: "judge"` instead. Provide absolute paths in the prompt:
```
Task(subagent_type="judge", model="haiku", prompt="Judge samples in /absolute/path/batch_NNN/samples/, write to /absolute/path/batch_NNN/judgments/, criteria at /absolute/path/batch_NNN/CLAUDE.md")
```
This works reliably (~45s per batch of 15 samples). The judge agent reads the CLAUDE.md via absolute path instead of relying on cwd.

**Root cause**: Unknown. Possibly the `--print` flag, the agent hook (`research_judge_require_claude_md.py`), or the `SessionStart` hook blocking startup. Needs investigation by @clement.

**Impact on research-judging skill**: The `xargs -P 10` parallel judging pattern described in the skill doesn't work. For now, use Task-based judge agents in waves of ~10.

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

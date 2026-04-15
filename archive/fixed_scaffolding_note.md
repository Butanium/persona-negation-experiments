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
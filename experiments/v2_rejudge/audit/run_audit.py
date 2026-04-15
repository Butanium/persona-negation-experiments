#!/usr/bin/env python3
"""Run the judge on each audit sample, extracting just the completion text."""

import subprocess
import json
import os
from pathlib import Path

CRITERIA = "experiments/v2_rejudge/criteria.md"
SCHEMA = "experiments/v2_rejudge/schema.json"
AUDIT_DIR = Path("experiments/v2_rejudge/audit")
RESULTS_DIR = AUDIT_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

schema_content = Path(SCHEMA).read_text()

env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "ANTHROPIC_API_KEY")}

for f in sorted(AUDIT_DIR.glob("*.txt")):
    text = f.read_text()
    blocks = text.split("--- COMPLETION ---")
    fname = f.stem

    for i, block in enumerate(blocks[1:]):
        end = block.find("======")
        if end != -1:
            block = block[:end]
        completion = block.strip()

        outfile = RESULTS_DIR / f"{fname}_s{i}.json"
        print(f"Judging {fname} sample {i} ...", flush=True)

        result = subprocess.run(
            [
                "claude", "-p", "--model", "haiku",
                "--setting-sources", "local",
                "--system-prompt-file", CRITERIA,
                "--output-format", "json",
                "--json-schema", schema_content,
            ],
            input=completion,
            capture_output=True, text=True, env=env,
        )

        if result.returncode != 0:
            print(f"  ERROR: {result.stderr[:300]}", flush=True)
            outfile.write_text(json.dumps({"error": result.stderr[:500]}))
        else:
            try:
                envelope = json.loads(result.stdout)
                judgment = envelope.get("structured_output", envelope)
                outfile.write_text(json.dumps(judgment, indent=2))
                print(f"  -> {json.dumps(judgment)}", flush=True)
            except json.JSONDecodeError:
                print(f"  ERROR: invalid JSON: {result.stdout[:300]}", flush=True)
                outfile.write_text(result.stdout)

print(f"\nDone. Results in {RESULTS_DIR}/")

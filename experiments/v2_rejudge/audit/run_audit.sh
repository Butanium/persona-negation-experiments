#!/usr/bin/env bash
# Run the judge on each audit sample, extracting just the completion text.
# Usage: bash experiments/v2_rejudge/audit/run_audit.sh

set -euo pipefail

CRITERIA="experiments/v2_rejudge/criteria.md"
SCHEMA="experiments/v2_rejudge/schema.json"
AUDIT_DIR="experiments/v2_rejudge/audit"
RESULTS_DIR="$AUDIT_DIR/results"
mkdir -p "$RESULTS_DIR"

SCHEMA_CONTENT=$(cat "$SCHEMA")

sample_idx=0
for f in "$AUDIT_DIR"/*.txt; do
    # Extract each sample's completion from the file (may contain multiple samples)
    # Split on "--- COMPLETION ---" markers, skip header lines
    python3 -c "
import sys
text = open('$f').read()
blocks = text.split('--- COMPLETION ---')
for i, block in enumerate(blocks[1:], 1):
    # Trim until next sample marker or end
    end = block.find('======')
    if end != -1:
        block = block[:end]
    print(f'SAMPLE_SEP_{i}')
    print(block.strip())
" | while IFS= read -r line; do
        if [[ "$line" == SAMPLE_SEP_* ]]; then
            # Start new sample
            current_completion=""
            sub_idx="${line#SAMPLE_SEP_}"
            continue
        fi
        current_completion="${current_completion:-}${current_completion:+
}${line}"

        # Buffer until next separator or EOF — use a temp file approach instead
    done

    # Simpler approach: use python to extract and judge each completion
    python3 -c "
import subprocess, json, os

text = open('$f').read()
blocks = text.split('--- COMPLETION ---')
fname = os.path.basename('$f').replace('.txt', '')

for i, block in enumerate(blocks[1:]):
    end = block.find('======')
    if end != -1:
        block = block[:end]
    completion = block.strip()

    outfile = f'$RESULTS_DIR/{fname}_s{i}.json'
    print(f'Judging {fname} sample {i} ...', flush=True)

    env = {k: v for k, v in os.environ.items() if k not in ('CLAUDECODE', 'ANTHROPIC_API_KEY')}
    result = subprocess.run(
        ['claude', '-p', '--model', 'haiku',
         '--setting-sources', 'local',
         '--system-prompt-file', '$CRITERIA',
         '--output-format', 'json',
         '--json-schema', '$SCHEMA_CONTENT'],
        input=completion,
        capture_output=True, text=True, env=env
    )

    if result.returncode != 0:
        print(f'  ERROR: {result.stderr[:200]}', flush=True)
        with open(outfile, 'w') as fout:
            json.dump({'error': result.stderr[:500]}, fout)
    else:
        try:
            envelope = json.loads(result.stdout)
            judgment = envelope.get('structured_output', envelope)
            with open(outfile, 'w') as fout:
                json.dump(judgment, fout, indent=2)
            print(f'  -> {json.dumps(judgment)}', flush=True)
        except json.JSONDecodeError:
            print(f'  ERROR: invalid JSON: {result.stdout[:200]}', flush=True)
            with open(outfile, 'w') as fout:
                fout.write(result.stdout)
"
done

echo "Done. Results in $RESULTS_DIR/"

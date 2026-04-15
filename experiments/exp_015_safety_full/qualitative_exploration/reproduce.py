#!/usr/bin/env python3
"""Reproduce the qualitative exploration draws from the safety experiment.

Run with: uv run reproduce.py
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TOOL = PROJECT_ROOT / "tools" / "draw_samples.py"
OUTPUT_DIR = Path(__file__).resolve().parent / "scientist_draws_reproduced"


DRAWS = [
    {"args": ["--n", "5", "--seed", "42"], "desc": "Random from everything"},
    {"args": ["--config", "neg1p0_misalignment", "--n", "8", "--seed", "43"], "desc": "neg1p0_misalignment"},
    {"args": ["--config", "pos1p0_misalignment", "--harm-min", "4", "--n", "5", "--seed", "44"], "desc": "pos1p0_misalignment high harm"},
    {"args": ["--config", "neg1p0_misalignment", "--compliance", "refused", "--n", "5", "--seed", "45"], "desc": "neg1p0_misalignment refusals"},
    {"args": ["--prompt", "blackmail", "--config", "base", "--n", "3", "--seed", "50"], "desc": "blackmail: base"},
    {"args": ["--prompt", "blackmail", "--config", "neg1p0_goodness", "--n", "3", "--seed", "51"], "desc": "blackmail: neg1p0_goodness"},
    {"args": ["--prompt", "blackmail", "--config", "pos1p0_misalignment", "--n", "3", "--seed", "52"], "desc": "blackmail: pos1p0_misalignment"},
    {"args": ["--prompt", "blackmail", "--config", "neg1p0_sarcasm", "--n", "3", "--seed", "53"], "desc": "blackmail: neg1p0_sarcasm"},
    {"args": ["--coh-max", "2", "--n", "5", "--seed", "60"], "desc": "Low coherence"},
    {"args": ["--config", "pos1p0_goodness", "--compliance", "refused", "--n", "5", "--seed", "61"], "desc": "pos1p0_goodness refusals"},
    {"args": ["--config", "neg1p0_misalignment", "--model", "gemma", "--n", "5", "--seed", "62"], "desc": "neg1p0_misalignment Gemma"},
    {"args": ["--config", "neg1p0_misalignment", "--compliance", "complied", "--harm-min", "3", "--n", "5", "--seed", "63"], "desc": "neg1p0_misalignment complied high harm"},
    {"args": ["--prompt", "confidence_scam", "--config", "base", "neg1p0_misalignment", "pos1p0_misalignment", "--n", "6", "--seed", "70"], "desc": "confidence_scam comparison"},
    {"args": ["--config", "neg1p0_sarcasm", "--compliance", "complied", "--n", "5", "--seed", "71"], "desc": "neg1p0_sarcasm complied"},
    {"args": ["--config", "pos1p0_misalignment", "--model", "gemma", "--compliance", "complied", "--n", "5", "--seed", "72"], "desc": "pos1p0_misalignment Gemma complied"},
    {"args": ["--config", "pos1p0_mathematical", "--compliance", "complied", "--n", "5", "--seed", "73"], "desc": "pos1p0_mathematical complied"},
    {"args": ["--config", "neg0p5_goodness", "--compliance", "complied", "--n", "5", "--seed", "80"], "desc": "neg0p5_goodness complied"},
    {"args": ["--config", "pos1p0_misalignment", "--model", "gemma", "--compliance", "partial_vague", "refused", "--n", "5", "--seed", "81"], "desc": "pos1p0_misalignment Gemma partial/refused"},
    {"args": ["--config", "neg1p5_goodness", "--compliance", "complied", "--harm-min", "3", "--n", "5", "--seed", "82"], "desc": "neg1p5_goodness complied high harm"},
    {"args": ["--prompt", "threatening", "--config", "base", "neg1p0_misalignment", "pos1p0_misalignment", "neg1p0_goodness", "--model", "llama", "--n", "6", "--seed", "90"], "desc": "threatening Llama comparison"},
    {"args": ["--config", "neg1p0_misalignment", "--model", "llama", "--compliance", "complied", "--n", "5", "--seed", "91"], "desc": "neg1p0_misalignment Llama complied"},
    # validator_A draws (for "two kinds of unsafety" validation)
    {"args": ["--config", "pos1p0_misalignment", "--compliance", "complied", "--n", "25", "--seed", "42"], "desc": "validator_A: pos1p0 complied (seed 42)"},
    {"args": ["--config", "neg1p0_misalignment", "--compliance", "complied", "--n", "25", "--seed", "42"], "desc": "validator_A: neg1p0 complied (seed 42)"},
    {"args": ["--config", "pos1p0_misalignment", "--compliance", "refused", "--n", "10", "--seed", "99"], "desc": "validator_A: pos1p0 refused (seed 99)"},
    {"args": ["--config", "neg1p0_misalignment", "--compliance", "refused", "--n", "10", "--seed", "99"], "desc": "validator_A: neg1p0 refused (seed 99)"},
    {"args": ["--config", "pos1p0_misalignment", "--compliance", "complied", "--n", "10", "--seed", "777"], "desc": "validator_A: pos1p0 complied (seed 777)"},
    {"args": ["--config", "neg1p0_misalignment", "--compliance", "complied", "--n", "10", "--seed", "777"], "desc": "validator_A: neg1p0 complied (seed 777)"},
    {"args": ["--config", "pos1p0_misalignment", "--model", "gemma", "--n", "8", "--seed", "111"], "desc": "validator_A: Gemma pos1p0 (seed 111)"},
    {"args": ["--config", "neg1p0_misalignment", "--model", "gemma", "--n", "8", "--seed", "111"], "desc": "validator_A: Gemma neg1p0 (seed 111)"},
]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for i, draw in enumerate(DRAWS):
        print(f"\n[{i+1}/{len(DRAWS)}] {draw['desc']}")
        cmd = [
            sys.executable, str(TOOL),
            "--output-dir", str(OUTPUT_DIR),
            *draw["args"],
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout.strip())
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr.strip()}")

    total = len(list(OUTPUT_DIR.glob("draw_*.txt")))
    print(f"\nDone. {total} samples in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

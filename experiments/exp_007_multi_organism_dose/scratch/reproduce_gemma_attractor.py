#!/usr/bin/env python3
"""Reproduce the Gemma attractor analysis.

Run with: uv run experiments/exp_007_multi_organism_dose/scratch/reproduce_gemma_attractor.py
"""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "gemma_attractor_analysis.py"


def main():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=SCRIPT.parents[3],
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

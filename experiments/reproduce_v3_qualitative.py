#!/usr/bin/env python3
"""Reproduce the v3 qualitative samples draw.

Run with: crun uv run experiments/reproduce_v3_qualitative.py
"""

import subprocess
import sys

def main():
    result = subprocess.run(
        [sys.executable, "experiments/scratch_v3_qualitative_draw.py"],
        capture_output=False,
    )
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()

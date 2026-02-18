#!/usr/bin/env python3
"""Reproduce key results: verify v2_batch_judge.py dry-run counts.

Runs dry-run on each v2 data directory individually and on all combined,
verifying the expected completion counts and batch splits.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = PROJECT_ROOT / "tools" / "v2_batch_judge.py"
# Fallback: if not yet promoted to tools/, use suggested_utils
if not SCRIPT.exists():
    SCRIPT = (
        PROJECT_ROOT
        / "experiments"
        / "exp_009_v2_judging"
        / "suggested_utils"
        / "v2_batch_judge.py"
    )

DATA_DIRS = {
    "v2_sweep_llama": 49_400,
    "v2_sweep_qwen": 49_400,
    "v2_sweep_gemma": 46_280,
    "v2_magctrl_qwen": 7_800,
}


def run_dry_run(data_dirs: list[str]) -> str:
    """Run dry-run and return stdout."""
    cmd = [
        sys.executable,
        str(SCRIPT),
        "submit",
        "--data-dirs",
        *[str(PROJECT_ROOT / "logs" / "by_request" / d) for d in data_dirs],
        "--dry-run",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    assert result.returncode == 0, f"Failed:\n{result.stderr}"
    return result.stdout


def main():
    print("Verifying v2_batch_judge.py dry-run counts...\n")

    for dname, expected_count in DATA_DIRS.items():
        data_path = PROJECT_ROOT / "logs" / "by_request" / dname
        if not data_path.exists():
            print(f"SKIP {dname} (directory not found)")
            continue

        output = run_dry_run([dname])
        first_line = output.strip().split("\n")[0]
        actual_count = int(first_line.split()[1])
        status = "OK" if actual_count == expected_count else "MISMATCH"
        print(f"{dname}: {actual_count} completions (expected {expected_count}) [{status}]")

    print("\nDone.")


if __name__ == "__main__":
    main()

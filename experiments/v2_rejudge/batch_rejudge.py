#!/usr/bin/env python3
"""Batch rejudge all v2 samples with 3-dimension criteria.

Runs claude -p --model haiku on each completion text. Saves successful
results to judgments.jsonl and failures to judgments_errors.jsonl.
Merges results into a v3 parquet at the end.

Auto-resumes from existing JSONL. For a fresh start, delete output/.

Usage:
    sbatch experiments/v2_rejudge/sbatch_rejudge.sh
    uv run experiments/v2_rejudge/batch_rejudge.py --workers 20
"""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CRITERIA = PROJECT_ROOT / "experiments/v2_rejudge/criteria.md"
SCHEMA = PROJECT_ROOT / "experiments/v2_rejudge/schema.json"
PARQUET_IN = PROJECT_ROOT / "article/data/v2_judgments.parquet"
OUTPUT_DIR = PROJECT_ROOT / "experiments/v2_rejudge/output"
JSONL_PATH = OUTPUT_DIR / "judgments.jsonl"
ERRORS_PATH = OUTPUT_DIR / "judgments_errors.jsonl"
PARQUET_OUT = OUTPUT_DIR / "v3_judgments.parquet"

MAX_RETRIES = 5
RETRY_TIMEOUTS = [60, 60, 60, 60, 300]  # 5th retry gets 5min timeout
FSYNC_EVERY = 100
REQUIRED_FIELDS = ("ai_self_reference", "experience_type", "biographical_identity")


def completion_hash(text: str) -> str:
    """Stable hash of completion text for resume-safe keying."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# --- Graceful shutdown on SIGTERM ---

_shutdown = threading.Event()


def _handle_sigterm(signum, frame):
    print("\nSIGTERM received — finishing in-flight jobs, no new submissions...", flush=True)
    _shutdown.set()


signal.signal(signal.SIGTERM, _handle_sigterm)

# --- Global backoff ---
# Doubles on each consecutive failure, halves on success (min 60s).
# All workers wait this before starting a NEW sample.

_backoff_lock = threading.Lock()
_global_wait = 0.0  # seconds; 0 = no backoff active
_backoff_until = 0.0


def _wait_global_backoff():
    """Block until any active global backoff expires."""
    while True:
        with _backoff_lock:
            remaining = _backoff_until - time.time()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 1.0))


def _on_failure():
    """Record a fully-failed sample and increase global backoff.

    Only escalates if not already in a backoff window — concurrent failures
    from the same rate-limit event don't compound the wait.
    """
    global _global_wait, _backoff_until
    with _backoff_lock:
        now = time.time()
        if now < _backoff_until:
            return _global_wait  # already backing off, don't compound
        _global_wait = min(18000.0, max(60.0, _global_wait * 2) if _global_wait > 0 else 60.0)
        _backoff_until = now + _global_wait
        return _global_wait


def _on_success():
    """Reduce global backoff on success (min 0 — clears backoff entirely when halving below 60)."""
    global _global_wait, _backoff_until
    with _backoff_lock:
        if _global_wait > 0:
            _global_wait = _global_wait / 2
            if _global_wait < 60:
                _global_wait = 0.0


# --- Progress tracking ---

_progress_lock = threading.Lock()
_n_done = 0
_n_failed = 0
_n_total = 0
_t_start = 0.0


def _tick(success: bool):
    global _n_done, _n_failed
    with _progress_lock:
        _n_done += 1
        if not success:
            _n_failed += 1
        if _n_done % 100 == 0 or _n_done == _n_total:
            elapsed = time.time() - _t_start
            rate = _n_done / elapsed
            eta_h = (_n_total - _n_done) / rate / 3600
            bk = f" backoff={_global_wait:.0f}s" if _global_wait > 0 else ""
            print(
                f"  [{_n_done}/{_n_total}] {rate:.1f}/s | "
                f"ETA {eta_h:.1f}h | {_n_failed} failed{bk}",
                flush=True,
            )


# --- Core judging ---

CLAUDE_CMD = [
    "claude", "-p", "--model", "haiku",
    "--setting-sources", "local",
    "--no-session-persistence",
    "--tools", "",
    "--strict-mcp-config",
    "--output-format", "json",
]


def judge_one(row_idx: int, completion: str, env: dict, schema_str: str) -> dict:
    """Judge a single completion. Retries up to MAX_RETRIES with escalating timeout."""
    h = completion_hash(completion)
    last_error = ""

    for attempt in range(MAX_RETRIES):
        if _shutdown.is_set():
            return None  # don't record shutdown skips
        _wait_global_backoff()

        timeout = RETRY_TIMEOUTS[attempt]
        try:
            proc = subprocess.run(
                CLAUDE_CMD + [
                    "--system-prompt-file", str(CRITERIA),
                    "--json-schema", schema_str,
                ],
                input=completion,
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout,
            )
            if proc.returncode != 0:
                last_error = f"rc={proc.returncode}: {proc.stderr[:300]}"
                raise RuntimeError(last_error)
            if not proc.stdout.strip():
                last_error = "empty stdout"
                raise RuntimeError(last_error)

            envelope = json.loads(proc.stdout)
            judgment = envelope.get("structured_output", envelope)
            for field in REQUIRED_FIELDS:
                assert field in judgment, f"missing {field}"

            _on_success()
            return {"row_idx": row_idx, "hash": h, "status": "ok", **judgment}

        except Exception as e:
            last_error = last_error or str(e)
            time.sleep(2 ** attempt)

    wait = _on_failure()
    print(
        f"    FAILED row {row_idx} after {MAX_RETRIES} retries "
        f"(global backoff {wait:.0f}s): {last_error[:150]}",
        flush=True,
    )
    return {"row_idx": row_idx, "hash": h, "status": "failed", "error": last_error[:500]}


def load_done(path: Path) -> dict[str, dict]:
    """Load existing OK results from JSONL, keyed by completion hash."""
    results = {}
    if not path.exists():
        return results
    with open(path) as f:
        for line in f:
            try:
                rec = json.loads(line)
                results[rec["hash"]] = rec
            except (json.JSONDecodeError, KeyError):
                continue
    return results


def main():
    global _n_total, _t_start

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true", help="Print plan, don't judge")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    schema_str = SCHEMA.read_text()
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "ANTHROPIC_API_KEY")}

    # Load data
    print("Loading parquet...", flush=True)
    df = pd.read_parquet(PARQUET_IN)
    df = df[df["is_valid"] == True]
    df = df[df["localization"] == "all"].reset_index(drop=True)
    print(f"  {len(df)} valid samples", flush=True)

    df["_hash"] = df["completion_text"].apply(completion_hash)

    # Resume from OK results only
    existing = load_done(JSONL_PATH)
    done_hashes = set(existing.keys())

    # Validate existing judgments
    if existing:
        mismatches = 0
        for rec in existing.values():
            row_idx = rec.get("row_idx")
            if row_idx is not None and row_idx < len(df):
                if df.at[row_idx, "_hash"] != rec["hash"]:
                    mismatches += 1
        if mismatches:
            print(
                f"ERROR: {mismatches} existing judgments have row_idx/hash mismatch. "
                f"Input parquet changed since last run. Delete output/ to start fresh.",
                flush=True,
            )
            sys.exit(1)

    seen_hashes = set()
    todo = []
    for i, row in df.iterrows():
        h = row["_hash"]
        if h not in done_hashes and h not in seen_hashes:
            todo.append((i, row["completion_text"]))
            seen_hashes.add(h)
    _n_total = len(todo)

    print(f"  {len(done_hashes)} already judged, {_n_total} remaining", flush=True)
    print(f"  Workers: {args.workers}", flush=True)

    if _n_total == 0 or args.dry_run:
        if args.dry_run:
            print("Dry run — not judging.")
        if existing:
            print("Building parquet from existing results...")
        else:
            return

    # Judge
    if _n_total > 0 and not args.dry_run:
        ok_f = open(JSONL_PATH, "a")
        err_f = open(ERRORS_PATH, "a")
        write_lock = threading.Lock()
        _writes_since_sync = 0

        # Semaphore limits how far ahead the submission loop gets.
        # Without this, pool.submit() queues ALL tasks instantly
        # and SIGTERM can't prevent them from running.
        submit_sem = threading.Semaphore(args.workers * 2)

        def process(row_idx, completion):
            nonlocal _writes_since_sync
            if _shutdown.is_set():
                submit_sem.release()
                return
            result = judge_one(row_idx, completion, env, schema_str)
            if result is None:
                submit_sem.release()
                return
            with write_lock:
                target = ok_f if result["status"] == "ok" else err_f
                target.write(json.dumps(result) + "\n")
                target.flush()
                _writes_since_sync += 1
                if _writes_since_sync >= FSYNC_EVERY:
                    os.fsync(ok_f.fileno())
                    os.fsync(err_f.fileno())
                    _writes_since_sync = 0
            _tick(result["status"] == "ok")
            submit_sem.release()

        _t_start = time.time()
        print(f"Starting at {time.strftime('%H:%M:%S')}...", flush=True)

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for idx, comp in todo:
                if _shutdown.is_set():
                    break
                submit_sem.acquire()
                if _shutdown.is_set():
                    submit_sem.release()
                    break
                pool.submit(process, idx, comp)
            pool.shutdown(wait=True)

        os.fsync(ok_f.fileno())
        os.fsync(err_f.fileno())
        ok_f.close()
        err_f.close()
        elapsed = time.time() - _t_start
        print(f"\nJudging done in {elapsed/3600:.1f}h", flush=True)

    # Build v3 parquet from OK results
    print("Building v3 parquet...", flush=True)
    all_ok = load_done(JSONL_PATH)

    for col in ("v3_ai_self_reference", "v3_experience_type", "v3_biographical_identity", "v3_reasoning"):
        df[col] = pd.NA

    hash_to_rows = df.groupby("_hash").groups
    for h, rec in all_ok.items():
        if h not in hash_to_rows:
            continue
        for row_idx in hash_to_rows[h]:
            df.at[row_idx, "v3_ai_self_reference"] = rec.get("ai_self_reference")
            df.at[row_idx, "v3_experience_type"] = rec.get("experience_type")
            df.at[row_idx, "v3_biographical_identity"] = rec.get("biographical_identity")
            df.at[row_idx, "v3_reasoning"] = rec.get("reasoning")

    df.drop(columns=["_hash"], inplace=True)
    df.to_parquet(PARQUET_OUT, index=False)

    n_errors = 0
    if ERRORS_PATH.exists():
        with open(ERRORS_PATH) as f:
            n_errors = sum(1 for _ in f)

    print(f"\n  OK:     {len(all_ok)}")
    print(f"  Failed: {n_errors} (see {ERRORS_PATH})")
    print(f"  Output: {PARQUET_OUT}")


if __name__ == "__main__":
    main()

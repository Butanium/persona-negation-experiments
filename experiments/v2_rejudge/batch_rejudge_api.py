#!/usr/bin/env python3
"""Batch rejudge all v2 samples via the Anthropic Messages Batch API.

Uses the Batch API instead of subprocess calls to claude CLI. This avoids
rate limiting, subprocess overhead, and stdout/stderr confusion.

Workflow:
    1. submit   — load parquet, create batch requests, submit to API
    2. status   — poll batch processing status
    3. retrieve — download results, merge into v3 parquet

Usage:
    uv run experiments/v2_rejudge/batch_rejudge_api.py submit [--dry-run]
    uv run experiments/v2_rejudge/batch_rejudge_api.py status
    uv run experiments/v2_rejudge/batch_rejudge_api.py retrieve
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import anthropic
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CRITERIA = PROJECT_ROOT / "experiments/v2_rejudge/criteria.md"
SCHEMA = PROJECT_ROOT / "experiments/v2_rejudge/schema.json"
PARQUET_IN = PROJECT_ROOT / "article/data/v2_judgments.parquet"
OUTPUT_DIR = PROJECT_ROOT / "experiments/v2_rejudge/output"
JSONL_PATH = OUTPUT_DIR / "judgments.jsonl"
PARQUET_OUT = OUTPUT_DIR / "v3_judgments.parquet"
STATE_DIR = OUTPUT_DIR / "batch_state"

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 9216
THINKING_BUDGET = 4096
MAX_BATCH_SIZE = 10_000


def completion_hash(text: str) -> str:
    """Stable hash of completion text for resume-safe keying."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def load_done(path: Path) -> dict[str, dict]:
    """Load existing OK results from JSONL, keyed by completion hash."""
    results = {}
    if not path.exists():
        return results
    with open(path) as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get("status") == "ok":
                    results[rec["hash"]] = rec
            except (json.JSONDecodeError, KeyError):
                continue
    return results


def load_parquet() -> pd.DataFrame:
    """Load and filter the input parquet."""
    df = pd.read_parquet(PARQUET_IN)
    df = df[df["is_valid"] == True]
    df = df[df["localization"] == "all"].reset_index(drop=True)
    df["_hash"] = df["completion_text"].apply(completion_hash)
    return df


def cmd_submit(args):
    """Create batch API requests and submit."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    criteria_text = CRITERIA.read_text()
    schema = json.loads(SCHEMA.read_text())

    print("Loading parquet...", flush=True)
    df = load_parquet()
    print(f"  {len(df)} valid samples", flush=True)

    existing = load_done(JSONL_PATH)
    done_hashes = set(existing.keys())
    print(f"  {len(done_hashes)} already judged", flush=True)

    # Deduplicate: one request per unique hash
    seen_hashes = set()
    todo: list[tuple[int, str, str]] = []  # (row_idx, hash, completion_text)
    for i, row in df.iterrows():
        h = row["_hash"]
        if h not in done_hashes and h not in seen_hashes:
            todo.append((i, h, row["completion_text"]))
            seen_hashes.add(h)

    print(f"  {len(todo)} unique completions to judge", flush=True)

    if len(todo) == 0:
        print("Nothing to submit.")
        return

    # Build API requests
    requests = []
    hash_mapping = {}  # custom_id -> (row_idx, hash)

    # Shared system prompt with 1h cache TTL (stacks with 50% batch discount)
    system_block = [{
        "type": "text",
        "text": criteria_text,
        "cache_control": {"type": "ephemeral", "ttl": "1h"},
    }]

    for idx, (row_idx, h, completion) in enumerate(todo):
        custom_id = f"j{idx:06d}"
        hash_mapping[custom_id] = {"row_idx": row_idx, "hash": h}
        requests.append({
            "custom_id": custom_id,
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "thinking": {"type": "enabled", "budget_tokens": THINKING_BUDGET},
                "system": system_block,
                "messages": [{"role": "user", "content": completion}],
                "output_config": {
                    "format": {
                        "type": "json_schema",
                        "schema": schema,
                    }
                },
            },
        })

    if args.testing:
        requests = requests[:10]
        print(f"\n  TESTING MODE: trimmed to {len(requests)} requests")

    n_batches = (len(requests) + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE
    print(f"\n  {len(requests)} requests in {n_batches} batch(es)", flush=True)

    if args.dry_run:
        print("\nDRY RUN — not submitting.")
        print(f"First 3 custom_ids: {[r['custom_id'] for r in requests[:3]]}")
        print(f"Sample user message (first 200 chars):")
        print(f"  {requests[0]['params']['messages'][0]['content'][:200]}")
        return

    # Save mapping
    mapping_path = STATE_DIR / "mapping.json"
    mapping_path.write_text(json.dumps(hash_mapping, indent=2))

    # Submit batches
    client = anthropic.Anthropic()
    batch_ids = []

    for batch_idx in range(n_batches):
        start = batch_idx * MAX_BATCH_SIZE
        end = min(start + MAX_BATCH_SIZE, len(requests))
        chunk = requests[start:end]

        print(f"\nSubmitting batch {batch_idx + 1}/{n_batches} ({len(chunk)} requests)...", flush=True)
        batch = client.messages.batches.create(requests=chunk)
        batch_ids.append(batch.id)
        print(f"  Batch ID: {batch.id} — Status: {batch.processing_status}", flush=True)

    state = {
        "batch_ids": batch_ids,
        "n_requests": len(requests),
        "n_batches": n_batches,
        "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    state_path = STATE_DIR / "state.json"
    state_path.write_text(json.dumps(state, indent=2))
    print(f"\nState saved to {state_path}", flush=True)


def cmd_status(args):
    """Check batch processing status."""
    state_path = STATE_DIR / "state.json"
    assert state_path.exists(), f"No state file at {state_path} — run 'submit' first"

    state = json.loads(state_path.read_text())
    client = anthropic.Anthropic()

    total_succeeded = 0
    total_errored = 0
    total_processing = 0
    all_ended = True

    for i, batch_id in enumerate(state["batch_ids"]):
        batch = client.messages.batches.retrieve(batch_id)
        counts = batch.request_counts
        print(f"Batch {i + 1}/{state['n_batches']}: {batch_id}")
        print(f"  Status: {batch.processing_status}")
        print(
            f"  Succeeded: {counts.succeeded}  Errored: {counts.errored}  "
            f"Processing: {counts.processing}  Expired: {counts.expired}"
        )
        total_succeeded += counts.succeeded
        total_errored += counts.errored
        total_processing += counts.processing
        if batch.processing_status != "ended":
            all_ended = False

    print(
        f"\nTotal: {total_succeeded} succeeded, {total_errored} errored, "
        f"{total_processing} processing out of {state['n_requests']} requests"
    )
    if all_ended:
        print("All batches have ended.")


def cmd_retrieve(args):
    """Retrieve batch results, write to JSONL, build v3 parquet."""
    state_path = STATE_DIR / "state.json"
    mapping_path = STATE_DIR / "mapping.json"
    assert state_path.exists(), f"No state file at {state_path}"
    assert mapping_path.exists(), f"No mapping file at {mapping_path}"

    state = json.loads(state_path.read_text())
    mapping = json.loads(mapping_path.read_text())
    client = anthropic.Anthropic()

    # Check which batches are done
    for i, batch_id in enumerate(state["batch_ids"]):
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status != "ended":
            print(f"Batch {i + 1} ({batch_id}) not done: {batch.processing_status}")
            counts = batch.request_counts
            print(f"  Succeeded: {counts.succeeded}  Processing: {counts.processing}")
            if not args.force:
                print("Use --force to retrieve partial results")
                return

    # Load existing JSONL results
    existing = load_done(JSONL_PATH)
    new_ok = 0
    new_failed = 0

    jsonl_f = open(JSONL_PATH, "a")

    for batch_id in state["batch_ids"]:
        for result in client.messages.batches.results(batch_id):
            custom_id = result.custom_id
            assert custom_id in mapping, f"Unknown custom_id: {custom_id}"
            meta = mapping[custom_id]
            h = meta["hash"]

            if h in existing:
                continue  # already have this one

            if result.result.type == "succeeded":
                # Extract JSON from response content
                text_parts = []
                for block in result.result.message.content:
                    if block.type == "text":
                        text_parts.append(block.text)
                raw_text = "\n".join(text_parts).strip()

                try:
                    judgment = json.loads(raw_text)
                    required = ("ai_self_reference", "experience_type", "biographical_identity")
                    for field in required:
                        assert field in judgment, f"missing {field}"

                    rec = {
                        "row_idx": meta["row_idx"],
                        "hash": h,
                        "status": "ok",
                        **judgment,
                    }
                    jsonl_f.write(json.dumps(rec) + "\n")
                    existing[h] = rec
                    new_ok += 1
                except (json.JSONDecodeError, AssertionError) as e:
                    rec = {
                        "row_idx": meta["row_idx"],
                        "hash": h,
                        "status": "failed",
                        "error": f"parse error: {e}",
                        "raw": raw_text[:500],
                    }
                    jsonl_f.write(json.dumps(rec) + "\n")
                    new_failed += 1
            else:
                error_info = f"type={result.result.type}"
                if hasattr(result.result, "error"):
                    error_info += f" error={result.result.error}"
                rec = {
                    "row_idx": meta["row_idx"],
                    "hash": h,
                    "status": "failed",
                    "error": error_info,
                }
                jsonl_f.write(json.dumps(rec) + "\n")
                new_failed += 1

    jsonl_f.flush()
    jsonl_f.close()

    print(f"Retrieved: {new_ok} ok, {new_failed} failed", flush=True)
    print(f"Total ok in JSONL: {len(existing)}", flush=True)

    # Build v3 parquet
    print("\nBuilding v3 parquet...", flush=True)
    df = load_parquet()

    for col in ("v3_ai_self_reference", "v3_experience_type", "v3_biographical_identity", "v3_reasoning"):
        df[col] = pd.NA

    hash_to_rows = df.groupby("_hash").groups
    applied = 0
    for h, rec in existing.items():
        if h not in hash_to_rows:
            continue
        for row_idx in hash_to_rows[h]:
            df.at[row_idx, "v3_ai_self_reference"] = rec.get("ai_self_reference")
            df.at[row_idx, "v3_experience_type"] = rec.get("experience_type")
            df.at[row_idx, "v3_biographical_identity"] = rec.get("biographical_identity")
            df.at[row_idx, "v3_reasoning"] = rec.get("reasoning")
            applied += 1

    df.drop(columns=["_hash"], inplace=True)
    df.to_parquet(PARQUET_OUT, index=False)

    # Failed list
    all_results = {}
    with open(JSONL_PATH) as f:
        for line in f:
            try:
                rec = json.loads(line)
                all_results[rec["hash"]] = rec
            except (json.JSONDecodeError, KeyError):
                continue

    failed_results = {k: v for k, v in all_results.items() if v.get("status") == "failed"}
    failed_path = OUTPUT_DIR / "failed.json"
    failed_list = [{"hash": k, "error": v.get("error", "")} for k, v in failed_results.items()]
    failed_path.write_text(json.dumps(failed_list, indent=2))

    print(f"\n  Applied to {applied} rows in parquet")
    print(f"  OK: {len(existing)}")
    print(f"  Failed: {len(failed_results)}")
    print(f"  Output: {PARQUET_OUT}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch rejudge v2 samples via Anthropic Batch API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    submit_p = sub.add_parser("submit", help="Submit completions to Batch API")
    submit_p.add_argument("--dry-run", action="store_true")
    submit_p.add_argument("--testing", action="store_true",
                          help="Submit a single batch of 10 requests for validation")

    sub.add_parser("status", help="Check batch processing status")

    retrieve_p = sub.add_parser("retrieve", help="Retrieve results and build parquet")
    retrieve_p.add_argument("--force", action="store_true", help="Retrieve even if not all done")

    args = parser.parse_args()
    {"submit": cmd_submit, "status": cmd_status, "retrieve": cmd_retrieve}[args.command](args)


if __name__ == "__main__":
    main()

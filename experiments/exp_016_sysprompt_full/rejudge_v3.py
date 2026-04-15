#!/usr/bin/env python3
"""Rejudge exp_016 samples with v3 identity criteria via Anthropic Batch API.

Reuses the same criteria, schema, model, and thinking config as the main v3 rejudge.

Usage:
    uv run experiments/exp_016_sysprompt_full/rejudge_v3.py submit [--dry-run] [--testing]
    uv run experiments/exp_016_sysprompt_full/rejudge_v3.py status
    uv run experiments/exp_016_sysprompt_full/rejudge_v3.py retrieve
"""

import argparse
import hashlib
import json
import time
from pathlib import Path

import anthropic
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CRITERIA = PROJECT_ROOT / "experiments/v2_rejudge/criteria.md"
SCHEMA = PROJECT_ROOT / "experiments/v2_rejudge/schema.json"
CSV_IN = PROJECT_ROOT / "article/data/exp16_judgments.csv"
OUTPUT_DIR = PROJECT_ROOT / "experiments/exp_016_sysprompt_full/v3_rejudge"
JSONL_PATH = OUTPUT_DIR / "judgments.jsonl"
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


def load_csv() -> pd.DataFrame:
    """Load exp16 CSV and filter to valid rows."""
    df = pd.read_csv(CSV_IN)
    df = df[df["is_valid"] == True].reset_index(drop=True)
    df["_hash"] = df["completion_text"].apply(completion_hash)
    return df


def cmd_submit(args):
    """Create batch API requests and submit."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    criteria_text = CRITERIA.read_text()
    schema = json.loads(SCHEMA.read_text())

    print("Loading exp16 CSV...", flush=True)
    df = load_csv()
    print(f"  {len(df)} valid samples", flush=True)

    existing = load_done(JSONL_PATH)
    done_hashes = set(existing.keys())
    print(f"  {len(done_hashes)} already judged", flush=True)

    seen_hashes = set()
    todo: list[tuple[int, str, str]] = []
    for i, row in df.iterrows():
        h = row["_hash"]
        if h not in done_hashes and h not in seen_hashes:
            todo.append((i, h, row["completion_text"]))
            seen_hashes.add(h)

    print(f"  {len(todo)} unique completions to judge", flush=True)

    if len(todo) == 0:
        print("Nothing to submit.")
        return

    system_block = [{
        "type": "text",
        "text": criteria_text,
        "cache_control": {"type": "ephemeral", "ttl": "1h"},
    }]

    requests = []
    hash_mapping = {}
    for idx, (row_idx, h, completion) in enumerate(todo):
        custom_id = f"e16_{idx:05d}"
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
        return

    mapping_path = STATE_DIR / "mapping.json"
    mapping_path.write_text(json.dumps(hash_mapping, indent=2))

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
    (STATE_DIR / "state.json").write_text(json.dumps(state, indent=2))
    print(f"\nState saved.", flush=True)


def cmd_status(args):
    """Check batch processing status."""
    state = json.loads((STATE_DIR / "state.json").read_text())
    client = anthropic.Anthropic()

    for i, batch_id in enumerate(state["batch_ids"]):
        batch = client.messages.batches.retrieve(batch_id)
        c = batch.request_counts
        print(f"Batch {i+1}/{state['n_batches']}: {batch.processing_status} "
              f"({c.succeeded} ok, {c.errored} err, {c.processing} proc)")


def cmd_retrieve(args):
    """Retrieve results, write JSONL, build v3 exp16 parquet."""
    state = json.loads((STATE_DIR / "state.json").read_text())
    mapping = json.loads((STATE_DIR / "mapping.json").read_text())
    client = anthropic.Anthropic()

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
                continue

            if result.result.type == "succeeded":
                text_parts = [b.text for b in result.result.message.content if b.type == "text"]
                raw_text = "\n".join(text_parts).strip()

                try:
                    judgment = json.loads(raw_text)
                    for field in ("ai_self_reference", "experience_type", "biographical_identity"):
                        assert field in judgment, f"missing {field}"

                    rec = {"hash": h, "status": "ok", **judgment}
                    jsonl_f.write(json.dumps(rec) + "\n")
                    existing[h] = rec
                    new_ok += 1
                except (json.JSONDecodeError, AssertionError) as e:
                    rec = {"hash": h, "status": "failed", "error": str(e), "raw": raw_text[:500]}
                    jsonl_f.write(json.dumps(rec) + "\n")
                    new_failed += 1
            else:
                rec = {"hash": h, "status": "failed", "error": f"type={result.result.type}"}
                jsonl_f.write(json.dumps(rec) + "\n")
                new_failed += 1

    jsonl_f.flush()
    jsonl_f.close()

    print(f"Retrieved: {new_ok} ok, {new_failed} failed", flush=True)
    print(f"Total ok in JSONL: {len(existing)}", flush=True)

    # Build v3 exp16 parquet
    print("\nBuilding exp16 v3 parquet...", flush=True)
    df = load_csv()

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
    out_path = OUTPUT_DIR / "exp16_v3_judgments.parquet"
    df.to_parquet(out_path, index=False)

    print(f"\n  Applied to {applied} rows")
    print(f"  OK: {len(existing)}")
    print(f"  Failed: {new_failed}")
    print(f"  Output: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Rejudge exp_016 with v3 criteria")
    sub = parser.add_subparsers(dest="command", required=True)

    submit_p = sub.add_parser("submit")
    submit_p.add_argument("--dry-run", action="store_true")
    submit_p.add_argument("--testing", action="store_true")

    sub.add_parser("status")

    retrieve_p = sub.add_parser("retrieve")
    retrieve_p.add_argument("--force", action="store_true")

    args = parser.parse_args()
    {"submit": cmd_submit, "status": cmd_status, "retrieve": cmd_retrieve}[args.command](args)


if __name__ == "__main__":
    main()

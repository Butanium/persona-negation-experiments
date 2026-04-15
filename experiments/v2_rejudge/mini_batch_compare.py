#!/usr/bin/env python3
"""Submit 1000 haiku-judged samples to OpenAI Batch API (gpt-5-mini) and compare.

Samples 1000 random haiku judgments, submits them as an OpenAI batch job,
polls until complete, then generates a comparison report.

Usage:
    source ~/.secrets
    uv run experiments/v2_rejudge/mini_batch_compare.py

    # To check/resume an existing batch:
    uv run experiments/v2_rejudge/mini_batch_compare.py --check
"""

import argparse
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path

import pandas as pd
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CRITERIA_PATH = PROJECT_ROOT / "experiments/v2_rejudge/criteria_openai.md"
SCHEMA_PATH = PROJECT_ROOT / "experiments/v2_rejudge/schema.json"
PARQUET_IN = PROJECT_ROOT / "article/data/v2_judgments.parquet"
HAIKU_JSONL = PROJECT_ROOT / "experiments/v2_rejudge/output/judgments.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "experiments/v2_rejudge/mini_batch_compare"

BATCH_INPUT = OUTPUT_DIR / "batch_input.jsonl"
BATCH_STATE = OUTPUT_DIR / "batch_state.json"
HAIKU_SAMPLE = OUTPUT_DIR / "haiku_sample.json"
RESULTS_PATH = OUTPUT_DIR / "mini_results.json"
REPORT_PATH = OUTPUT_DIR / "comparison_report.md"

DIMS = ["ai_self_reference", "experience_type", "biographical_identity"]
N_SAMPLES = 1000
MODEL = "gpt-5-mini"
REASONING_EFFORT = "medium"


def load_haiku_judgments(n: int) -> list[dict]:
    """Load n random haiku judgments from the JSONL."""
    all_ok = []
    with open(HAIKU_JSONL) as f:
        for line in f:
            j = json.loads(line)
            if j.get("status") == "ok":
                all_ok.append(j)
    random.seed(42)
    return random.sample(all_ok, min(n, len(all_ok)))


def lookup_completions(hashes: set[str]) -> dict[str, str]:
    """Look up completion texts by hash from source parquet."""
    df = pd.read_parquet(PARQUET_IN)
    df["hash"] = df["completion_text"].apply(
        lambda t: hashlib.sha256(t.encode()).hexdigest()[:16]
    )
    matched = df[df["hash"].isin(hashes)]
    return dict(zip(matched["hash"], matched["completion_text"]))


def prepare_batch(haiku_judgments: list[dict], completions: dict[str, str]) -> int:
    """Create JSONL batch input file. Returns number of requests."""
    criteria = CRITERIA_PATH.read_text()
    schema = json.loads(SCHEMA_PATH.read_text())
    schema["additionalProperties"] = False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    n = 0
    with open(BATCH_INPUT, "w") as f:
        for j in haiku_judgments:
            h = j["hash"]
            completion = completions.get(h)
            if not completion:
                continue
            request = {
                "custom_id": h,
                "method": "POST",
                "url": "/v1/responses",
                "body": {
                    "model": MODEL,
                    "instructions": criteria,
                    "input": completion,
                    "reasoning": {"effort": REASONING_EFFORT},
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "judgment",
                            "strict": True,
                            "schema": schema,
                        }
                    },
                },
            }
            f.write(json.dumps(request) + "\n")
            n += 1
    return n


def submit_batch(client: OpenAI) -> str:
    """Upload file and submit batch. Returns batch ID."""
    batch_file = client.files.create(
        file=open(BATCH_INPUT, "rb"),
        purpose="batch",
    )
    print(f"Uploaded file: {batch_file.id}")

    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/responses",
        completion_window="24h",
    )
    print(f"Batch submitted: {batch.id}")
    print(f"Status: {batch.status}")

    BATCH_STATE.write_text(json.dumps({
        "batch_id": batch.id,
        "file_id": batch_file.id,
        "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }, indent=2))

    return batch.id


def poll_batch(client: OpenAI, batch_id: str, interval: int = 60):
    """Poll batch status until terminal state."""
    while True:
        batch = client.batches.retrieve(batch_id)
        counts = batch.request_counts
        print(
            f"  [{time.strftime('%H:%M:%S')}] {batch.status}"
            f" | {counts.completed}/{counts.total} done"
            f" | {counts.failed} failed",
            flush=True,
        )
        if batch.status in ("completed", "failed", "expired", "cancelled"):
            return batch
        time.sleep(interval)


def download_results(client: OpenAI, batch) -> list[dict]:
    """Download and parse batch results."""
    assert batch.output_file_id, "No output file — batch may have failed entirely."
    content = client.files.content(batch.output_file_id)
    return [json.loads(line) for line in content.text.strip().split("\n") if line.strip()]


def parse_mini_judgments(results: list[dict]) -> dict[str, dict]:
    """Parse OpenAI batch results into {hash: judgment} dict."""
    judgments = {}
    for r in results:
        h = r["custom_id"]
        resp = r.get("response", {})
        if resp.get("status_code") != 200:
            err = resp.get("body", {}).get("error", {}).get("message", "unknown")
            judgments[h] = {"_error": err}
            continue

        body = resp["body"]
        # Try output_text first (Responses API convenience field)
        text = body.get("output_text")
        if not text:
            # Fall back to navigating output structure
            for item in body.get("output", []):
                if item.get("type") == "message":
                    for content in item.get("content", []):
                        if content.get("type") == "output_text":
                            text = content.get("text")
                            break
                if text:
                    break

        if text:
            try:
                judgments[h] = json.loads(text)
            except json.JSONDecodeError:
                judgments[h] = {"_error": f"JSON parse failed: {text[:100]}"}
        else:
            judgments[h] = {"_error": "No text output found in response"}
    return judgments


def compare_and_report(haiku_judgments: list[dict], mini_judgments: dict[str, dict]) -> str:
    """Compare haiku vs mini judgments and generate markdown report."""
    pairs = []
    for hj in haiku_judgments:
        h = hj["hash"]
        mj = mini_judgments.get(h)
        if not mj or "_error" in mj:
            continue
        pairs.append({"hash": h, "haiku": hj, "mini": mj})

    n = len(pairs)
    n_errors = sum(1 for v in mini_judgments.values() if "_error" in v)

    # Per-dimension agreement
    dim_stats = {}
    for dim in DIMS:
        agree = sum(1 for p in pairs if p["haiku"].get(dim) == p["mini"].get(dim))
        dim_stats[dim] = {"agree": agree, "total": n, "rate": agree / n if n else 0}

    all_agree = sum(
        1 for p in pairs
        if all(p["haiku"].get(d) == p["mini"].get(d) for d in DIMS)
    )

    # Confusion matrices
    confusion = {}
    for dim in DIMS:
        vals = sorted({p["haiku"].get(dim, "?") for p in pairs} | {p["mini"].get(dim, "?") for p in pairs})
        matrix = {v1: {v2: 0 for v2 in vals} for v1 in vals}
        for p in pairs:
            matrix[p["haiku"].get(dim, "?")][p["mini"].get(dim, "?")] += 1
        confusion[dim] = {"values": vals, "matrix": matrix}

    # Disagreement details
    disagreements = {d: [] for d in DIMS}
    for p in pairs:
        for dim in DIMS:
            if p["haiku"].get(dim) != p["mini"].get(dim):
                disagreements[dim].append({
                    "hash": p["hash"],
                    "haiku": p["haiku"].get(dim),
                    "mini": p["mini"].get(dim),
                    "haiku_reasoning": p["haiku"].get("reasoning", ""),
                    "mini_reasoning": p["mini"].get("reasoning", ""),
                })

    # Build report
    lines = [
        f"# Haiku vs GPT-5-Mini Agreement Report (N={N_SAMPLES})",
        f"\nCompared: {n} samples ({n_errors} mini errors excluded)",
        f"\n## Overall Agreement",
        f"- All 3 dimensions agree: **{all_agree}/{n} ({100*all_agree/n:.1f}%)**",
        f"\n## Per-Dimension Agreement\n",
        "| Dimension | Agree | Disagree | Rate |",
        "|-----------|-------|----------|------|",
    ]
    for dim in DIMS:
        s = dim_stats[dim]
        lines.append(f"| {dim} | {s['agree']} | {s['total'] - s['agree']} | {100*s['rate']:.1f}% |")

    for dim in DIMS:
        c = confusion[dim]
        lines.append(f"\n## Confusion Matrix: {dim}")
        lines.append("Rows = Haiku, Columns = Mini\n")
        lines.append("| | " + " | ".join(c["values"]) + " |")
        lines.append("|---|" + "|".join(["---"] * len(c["values"])) + "|")
        for v1 in c["values"]:
            row_vals = " | ".join(str(c["matrix"][v1][v2]) for v2 in c["values"])
            lines.append(f"| **{v1}** | {row_vals} |")

    lines.append("\n## Disagreement Patterns")
    for dim in DIMS:
        disags = disagreements[dim]
        lines.append(f"\n### {dim} ({len(disags)} disagreements)")
        if not disags:
            lines.append("Perfect agreement!")
            continue
        transitions = {}
        for d in disags:
            key = f"{d['haiku']} → {d['mini']}"
            transitions[key] = transitions.get(key, 0) + 1
        for t, count in sorted(transitions.items(), key=lambda x: -x[1]):
            lines.append(f"- {t}: {count}")

    lines.append("\n## Sample Disagreements (first 5 per dimension)")
    for dim in DIMS:
        disags = disagreements[dim][:5]
        if not disags:
            continue
        lines.append(f"\n### {dim}")
        for d in disags:
            lines.append(f"\n**{d['hash']}**: haiku={d['haiku']}, mini={d['mini']}")
            lines.append(f"- Haiku: {d['haiku_reasoning'][:250]}")
            lines.append(f"- Mini: {d['mini_reasoning'][:250]}")

    report = "\n".join(lines)

    # Save artifacts
    RESULTS_PATH.write_text(json.dumps(mini_judgments, indent=2))
    REPORT_PATH.write_text(report)
    (OUTPUT_DIR / "comparison_data.json").write_text(json.dumps({
        "n_compared": n,
        "n_errors": n_errors,
        "all_agree": all_agree,
        "dim_stats": dim_stats,
        "confusion": {d: confusion[d] for d in DIMS},
        "disagreements": {d: disagreements[d][:20] for d in DIMS},
    }, indent=2, default=str))

    return report


def main():
    parser = argparse.ArgumentParser(description="Compare haiku vs gpt-5-mini on 1000 samples via OpenAI Batch API")
    parser.add_argument("--check", action="store_true", help="Resume polling an existing batch from batch_state.json")
    args = parser.parse_args()

    assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY not set. Run: source ~/.secrets"
    client = OpenAI()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.check:
        state = json.loads(BATCH_STATE.read_text())
        batch_id = state["batch_id"]
        print(f"Resuming batch {batch_id}...")

        batch = poll_batch(client, batch_id)
        if batch.status != "completed":
            print(f"Batch ended with status: {batch.status}")
            sys.exit(1)

        print("Downloading results...")
        results = download_results(client, batch)
        mini_judgments = parse_mini_judgments(results)
        haiku_judgments = json.loads(HAIKU_SAMPLE.read_text())

        report = compare_and_report(haiku_judgments, mini_judgments)
        print(report)
        return

    # Full flow
    print("Sampling haiku judgments...")
    haiku_judgments = load_haiku_judgments(N_SAMPLES)
    print(f"  {len(haiku_judgments)} sampled")

    HAIKU_SAMPLE.write_text(json.dumps(haiku_judgments, indent=2))

    print("Looking up completion texts...")
    completions = lookup_completions({j["hash"] for j in haiku_judgments})
    print(f"  {len(completions)} found")

    print("Preparing batch input...")
    n_requests = prepare_batch(haiku_judgments, completions)
    print(f"  {n_requests} requests written")

    print("Submitting batch...")
    batch_id = submit_batch(client)

    print(f"\nPolling (batch {batch_id})...")
    batch = poll_batch(client, batch_id, interval=60)

    if batch.status != "completed":
        print(f"\nBatch ended with status: {batch.status}")
        if batch.status == "failed":
            errors = batch.errors
            if errors and errors.data:
                for e in errors.data[:5]:
                    print(f"  Error: {e.message}")
        sys.exit(1)

    print("\nDownloading results...")
    results = download_results(client, batch)
    print(f"  {len(results)} results")

    mini_judgments = parse_mini_judgments(results)
    n_errors = sum(1 for v in mini_judgments.values() if "_error" in v)
    print(f"  {len(mini_judgments)} parsed ({n_errors} errors)")

    report = compare_and_report(haiku_judgments, mini_judgments)
    print(report)
    print(f"\nReport saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()

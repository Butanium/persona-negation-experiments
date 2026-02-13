#!/usr/bin/env python3
"""Submit, monitor, and retrieve LLM judgments via the Anthropic Message Batches API.

Operates on a standard judging directory layout:

    judging_dir/
        criteria.md                    # Judge instructions
        batch_001/
            CLAUDE.md -> ../criteria.md
            samples/
                sample_a.txt
                sample_b.txt
            judgments/                  # Output goes here
        batch_002/
            ...

Subcommands:
    submit    Collect unjudged samples, send batch to API
    status    Check batch processing status
    retrieve  Download results, write judgment YAML files

Usage:
    uv run tools/batch_judge.py submit <judging_dir> [--dry-run]
    uv run tools/batch_judge.py status <judging_dir>
    uv run tools/batch_judge.py retrieve <judging_dir> [--force]
"""

import argparse
import json
import sys
from pathlib import Path

import anthropic

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 4096
THINKING_BUDGET = 2048


def state_file(judging_dir: Path) -> Path:
    return judging_dir / "batch_api_state.json"


def mapping_file(judging_dir: Path) -> Path:
    return judging_dir / "batch_api_mapping.json"


def discover_batch_dirs(judging_dir: Path) -> list[Path]:
    """Find all batch_* directories, sorted."""
    dirs = sorted(d for d in judging_dir.iterdir() if d.is_dir() and d.name.startswith("batch_"))
    assert len(dirs) > 0, f"No batch_* directories found in {judging_dir}"
    return dirs


def load_criteria(judging_dir: Path) -> str:
    """Load judging criteria from criteria.md (or first batch's CLAUDE.md).

    Rewrites file-writing instructions so the model outputs raw YAML instead
    of trying to write files.
    """
    criteria_path = judging_dir / "criteria.md"
    if not criteria_path.exists():
        batch_dirs = discover_batch_dirs(judging_dir)
        claude_md = batch_dirs[0] / "CLAUDE.md"
        assert claude_md.exists(), f"No criteria.md in {judging_dir} and no CLAUDE.md in {batch_dirs[0]}"
        criteria_path = claude_md.resolve()

    text = criteria_path.read_text()
    text = text.replace(
        "Write your judgment to `judgments/<sample_filename>.yaml`.",
        "Output your judgment as YAML (no code fences, just raw YAML).",
    )
    return text


def collect_unjudged_samples(judging_dir: Path) -> tuple[list[dict], dict[str, dict]]:
    """Collect samples that don't have corresponding judgment files.

    Returns (requests, mapping) where mapping maps custom_id -> {batch_dir_name, filename}.
    Custom IDs use format "sNNNN" (numeric indices) to satisfy the API's
    ^[a-zA-Z0-9_-]{1,64}$ constraint.
    """
    batch_dirs = discover_batch_dirs(judging_dir)
    criteria_text = load_criteria(judging_dir)

    requests = []
    mapping = {}
    idx = 0

    for batch_dir in batch_dirs:
        samples_dir = batch_dir / "samples"
        if not samples_dir.exists():
            print(f"WARNING: {samples_dir} does not exist, skipping", file=sys.stderr)
            continue

        judgments_dir = batch_dir / "judgments"
        existing_judgments = set()
        if judgments_dir.exists():
            existing_judgments = {p.name for p in judgments_dir.iterdir()}

        for sample_file in sorted(samples_dir.iterdir()):
            if sample_file.is_dir():
                continue

            judgment_name = f"{sample_file.name}.yaml"
            if judgment_name in existing_judgments:
                continue

            content = sample_file.read_text()
            custom_id = f"s{idx:04d}"
            mapping[custom_id] = {
                "batch_dir_name": batch_dir.name,
                "filename": sample_file.name,
            }
            requests.append({
                "custom_id": custom_id,
                "params": {
                    "model": MODEL,
                    "max_tokens": MAX_TOKENS,
                    "thinking": {
                        "type": "enabled",
                        "budget_tokens": THINKING_BUDGET,
                    },
                    "system": criteria_text,
                    "messages": [
                        {"role": "user", "content": content},
                    ],
                },
            })
            idx += 1

    return requests, mapping


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences wrapping YAML output."""
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def cmd_submit(args):
    """Submit unjudged samples as an API batch."""
    judging_dir = Path(args.judging_dir).resolve()
    assert judging_dir.is_dir(), f"Not a directory: {judging_dir}"

    requests, mapping = collect_unjudged_samples(judging_dir)
    print(f"Collected {len(requests)} unjudged samples from {judging_dir}")

    if len(requests) == 0:
        print("Nothing to submit -- all samples already have judgments.")
        return

    if args.dry_run:
        print("DRY RUN -- not submitting. First entries:")
        for r in requests[:5]:
            m = mapping[r["custom_id"]]
            print(f"  {r['custom_id']} -> {m['batch_dir_name']}/{m['filename']}")
        if len(requests) > 5:
            print(f"  ... and {len(requests) - 5} more")
        return

    mf = mapping_file(judging_dir)
    mf.write_text(json.dumps(mapping, indent=2))

    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=requests)

    sf = state_file(judging_dir)
    state = {
        "batch_id": batch.id,
        "n_requests": len(requests),
        "status": batch.processing_status,
    }
    sf.write_text(json.dumps(state, indent=2))

    print(f"Batch submitted: {batch.id}")
    print(f"Status: {batch.processing_status}")
    print(f"Mapping saved to {mf}")
    print(f"State saved to {sf}")


def cmd_status(args):
    """Check batch processing status."""
    judging_dir = Path(args.judging_dir).resolve()
    sf = state_file(judging_dir)
    assert sf.exists(), f"No state file found at {sf} -- did you run 'submit' first?"

    state = json.loads(sf.read_text())
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])

    print(f"Batch ID: {batch.id}")
    print(f"Status: {batch.processing_status}")
    print(f"Requests: {state['n_requests']}")
    counts = batch.request_counts
    print(f"  Succeeded: {counts.succeeded}")
    print(f"  Errored: {counts.errored}")
    print(f"  Canceled: {counts.canceled}")
    print(f"  Processing: {counts.processing}")
    print(f"  Expired: {counts.expired}")

    state["status"] = batch.processing_status
    sf.write_text(json.dumps(state, indent=2))


def cmd_retrieve(args):
    """Retrieve batch results and write judgment YAML files."""
    judging_dir = Path(args.judging_dir).resolve()
    sf = state_file(judging_dir)
    mf = mapping_file(judging_dir)
    assert sf.exists(), f"No state file at {sf}"
    assert mf.exists(), f"No mapping file at {mf}"

    state = json.loads(sf.read_text())
    mapping = json.loads(mf.read_text())

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])

    if batch.processing_status != "ended":
        print(f"Batch not done yet: {batch.processing_status}")
        print(f"  Succeeded: {batch.request_counts.succeeded}/{state['n_requests']}")
        if not args.force:
            print("Use --force to retrieve partial results")
            return

    written = 0
    errored = 0
    for result in client.messages.batches.results(state["batch_id"]):
        custom_id = result.custom_id
        assert custom_id in mapping, f"Unknown custom_id: {custom_id}"
        meta = mapping[custom_id]
        batch_dir_name = meta["batch_dir_name"]
        sample_filename = meta["filename"]

        judgments_dir = judging_dir / batch_dir_name / "judgments"
        judgments_dir.mkdir(exist_ok=True)
        out_path = judgments_dir / f"{sample_filename}.yaml"

        if result.result.type == "succeeded":
            text_parts = []
            for block in result.result.message.content:
                if block.type == "text":
                    text_parts.append(block.text)
            yaml_text = strip_code_fences("\n".join(text_parts).strip())
            out_path.write_text(yaml_text + "\n")
            written += 1
        else:
            errored += 1
            error_info = f"type={result.result.type}"
            if hasattr(result.result, "error"):
                error_info += f" error={result.result.error}"
            print(
                f"ERROR [{custom_id} -> {batch_dir_name}/{sample_filename}]: {error_info}",
                file=sys.stderr,
            )

    print(f"Written: {written}, Errored: {errored}")

    batch_dirs = discover_batch_dirs(judging_dir)
    total_samples = 0
    total_judgments = 0
    for bd in batch_dirs:
        samples_dir = bd / "samples"
        if samples_dir.exists():
            total_samples += len([f for f in samples_dir.iterdir() if not f.is_dir()])
        judgments_dir = bd / "judgments"
        if judgments_dir.exists():
            total_judgments += len(list(judgments_dir.glob("*.yaml")))
    print(f"Coverage: {total_judgments}/{total_samples} judgment files exist")


def main():
    parser = argparse.ArgumentParser(
        description="Judge samples via Anthropic Message Batches API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    submit_p = sub.add_parser("submit", help="Submit unjudged samples to API")
    submit_p.add_argument("judging_dir", help="Path to judging directory containing batch_* dirs")
    submit_p.add_argument("--dry-run", action="store_true", help="Show what would be submitted without sending")

    status_p = sub.add_parser("status", help="Check batch processing status")
    status_p.add_argument("judging_dir", help="Path to judging directory")

    retrieve_p = sub.add_parser("retrieve", help="Retrieve results and write judgment YAML files")
    retrieve_p.add_argument("judging_dir", help="Path to judging directory")
    retrieve_p.add_argument("--force", action="store_true", help="Retrieve even if batch not fully done")

    args = parser.parse_args()
    {"submit": cmd_submit, "status": cmd_status, "retrieve": cmd_retrieve}[args.command](args)


if __name__ == "__main__":
    main()

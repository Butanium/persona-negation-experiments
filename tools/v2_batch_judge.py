#!/usr/bin/env python3
"""Judge v2 experiment completions via the Anthropic Message Batches API.

v2 data lives in directories like logs/by_request/v2_sweep_llama/ with YAML
files containing a list of 4 completions each. This script creates one API
request per completion, submits them in batches of up to 10,000 (the API
limit), and writes judgments back as .judgments.yaml files alongside the
source files.

Subcommands:
    submit    Collect completions, submit batch(es) to API
    status    Check batch processing status
    retrieve  Download results, write .judgments.yaml files

Usage:
    uv run tools/v2_batch_judge.py submit --data-dirs logs/by_request/v2_sweep_llama [--dry-run] [--resume]
    uv run tools/v2_batch_judge.py status [--state-dir judgments/v2_state]
    uv run tools/v2_batch_judge.py retrieve [--state-dir judgments/v2_state] [--force]
"""

import argparse
import json
import sys
from pathlib import Path

import anthropic
import yaml

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 4096
THINKING_BUDGET = 2048
MAX_BATCH_SIZE = 10_000

DEFAULT_STATE_DIR = Path("judgments/v2_state")
DEFAULT_CRITERIA_PATH = Path("experiments/exp_007_multi_organism_dose/judging/criteria.md")


def load_criteria(criteria_path: Path | None = None) -> str:
    """Load judging criteria and adapt for API output format."""
    path = criteria_path or DEFAULT_CRITERIA_PATH
    assert path.exists(), f"Criteria file not found: {path}"
    text = path.read_text()
    text = text.replace(
        "Write your judgment to `judgments/<sample_filename>.yaml`.",
        "Output your judgment as YAML (no code fences, just raw YAML).",
    )
    text = text.replace(
        "Each sample in `samples/` contains a prompt and a model response. Evaluate the **response only** (not the prompt).",
        "You will be given a prompt and a model response. Evaluate the **response only** (not the prompt).",
    )
    return text


def collect_completions(
    data_dirs: list[Path], resume: bool = False, criteria_path: Path | None = None
) -> tuple[list[dict], dict[str, dict]]:
    """Collect all completions from v2 data directories.

    Each YAML file (excluding .debug.yaml) contains a 'completions' list.
    We create one request per completion.

    Returns (requests, mapping) where mapping maps custom_id ->
    {data_dir, prompt_dir, config, completion_idx}.
    """
    criteria_text = load_criteria(criteria_path)
    requests = []
    mapping = {}
    idx = 0
    skipped_resume = 0

    for data_dir in data_dirs:
        assert data_dir.is_dir(), f"Not a directory: {data_dir}"
        prompt_dirs = sorted(d for d in data_dir.iterdir() if d.is_dir())

        for prompt_dir in prompt_dirs:
            yaml_files = sorted(
                f
                for f in prompt_dir.iterdir()
                if f.suffix == ".yaml"
                and not f.name.endswith(".debug.yaml")
                and not f.name.endswith(".judgments.yaml")
            )

            for yaml_file in yaml_files:
                config_name = yaml_file.stem
                judgments_path = prompt_dir / f"{config_name}.judgments.yaml"

                if resume and judgments_path.exists():
                    skipped_resume += 1
                    continue

                data = yaml.safe_load(yaml_file.read_text())
                completions = data["completions"]
                prompt = data["prompt"]

                for ci, completion in enumerate(completions):
                    custom_id = f"s{idx:06d}"
                    mapping[custom_id] = {
                        "data_dir": str(data_dir),
                        "prompt_dir": prompt_dir.name,
                        "config": config_name,
                        "completion_idx": ci,
                    }
                    user_msg = f"Prompt: {prompt}\n\nResponse:\n{completion}"
                    requests.append(
                        {
                            "custom_id": custom_id,
                            "params": {
                                "model": MODEL,
                                "max_tokens": MAX_TOKENS,
                                "thinking": {
                                    "type": "enabled",
                                    "budget_tokens": THINKING_BUDGET,
                                },
                                "system": criteria_text,
                                "messages": [{"role": "user", "content": user_msg}],
                            },
                        }
                    )
                    idx += 1

    if resume and skipped_resume > 0:
        print(f"Skipped {skipped_resume} files with existing judgments (--resume)")

    return requests, mapping


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences wrapping YAML output."""
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def cmd_submit(args):
    """Submit completions as API batch(es)."""
    data_dirs = [Path(d).resolve() for d in args.data_dirs]
    state_dir = Path(args.state_dir).resolve()
    criteria_path = Path(args.criteria).resolve() if args.criteria else None

    requests, mapping = collect_completions(data_dirs, resume=args.resume, criteria_path=criteria_path)
    n_total = len(requests)
    print(f"Collected {n_total} completions from {len(data_dirs)} data dir(s)")

    if n_total == 0:
        print("Nothing to submit.")
        return

    n_batches = (n_total + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE
    print(f"Will submit {n_batches} batch(es) of up to {MAX_BATCH_SIZE} requests each")

    if args.dry_run:
        print("\nDRY RUN -- not submitting. First 5 entries:")
        for r in requests[:5]:
            m = mapping[r["custom_id"]]
            print(
                f"  {r['custom_id']} -> {m['data_dir']}/{m['prompt_dir']}/{m['config']} "
                f"[completion {m['completion_idx']}]"
            )
        if n_total > 5:
            print(f"  ... and {n_total - 5} more")

        print(f"\nSample user message (first request):")
        print("---")
        msg = requests[0]["params"]["messages"][0]["content"]
        print(msg[:500])
        if len(msg) > 500:
            print(f"  ... ({len(msg)} chars total)")
        print("---")
        return

    state_dir.mkdir(parents=True, exist_ok=True)

    mapping_path = state_dir / "mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2))
    print(f"Mapping saved to {mapping_path}")

    client = anthropic.Anthropic()
    batch_ids = []

    for batch_idx in range(n_batches):
        start = batch_idx * MAX_BATCH_SIZE
        end = min(start + MAX_BATCH_SIZE, n_total)
        chunk = requests[start:end]

        print(f"\nSubmitting batch {batch_idx + 1}/{n_batches} ({len(chunk)} requests)...")
        batch = client.messages.batches.create(requests=chunk)
        batch_ids.append(batch.id)
        print(f"  Batch ID: {batch.id} -- Status: {batch.processing_status}")

    state = {
        "batch_ids": batch_ids,
        "n_requests": n_total,
        "n_batches": n_batches,
        "data_dirs": [str(d) for d in data_dirs],
    }
    state_path = state_dir / "state.json"
    state_path.write_text(json.dumps(state, indent=2))
    print(f"\nState saved to {state_path}")


def cmd_status(args):
    """Check batch processing status."""
    state_dir = Path(args.state_dir).resolve()
    state_path = state_dir / "state.json"
    assert state_path.exists(), f"No state file at {state_path} -- run 'submit' first"

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
    """Retrieve results and write .judgments.yaml files."""
    state_dir = Path(args.state_dir).resolve()
    state_path = state_dir / "state.json"
    mapping_path = state_dir / "mapping.json"
    assert state_path.exists(), f"No state file at {state_path}"
    assert mapping_path.exists(), f"No mapping file at {mapping_path}"

    state = json.loads(state_path.read_text())
    mapping = json.loads(mapping_path.read_text())

    client = anthropic.Anthropic()

    # Check which batches are done
    ended_batch_ids = []
    for i, batch_id in enumerate(state["batch_ids"]):
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            ended_batch_ids.append(batch_id)
        else:
            print(f"Batch {i + 1} ({batch_id}) not done: {batch.processing_status}")
            print(f"  Succeeded: {batch.request_counts.succeeded}")
            if not args.force:
                print("Use --force to retrieve partial results")
                return

    if not ended_batch_ids:
        print("No ended batches to retrieve.")
        return

    print(f"Retrieving from {len(ended_batch_ids)}/{len(state['batch_ids'])} ended batches")

    # Group results by (data_dir, prompt_dir, config) -> {completion_idx: yaml_text}
    grouped: dict[tuple[str, str, str], dict[int, str]] = {}
    errored = 0

    for batch_id in ended_batch_ids:
        for result in client.messages.batches.results(batch_id):
            custom_id = result.custom_id
            assert custom_id in mapping, f"Unknown custom_id: {custom_id}"
            meta = mapping[custom_id]
            key = (meta["data_dir"], meta["prompt_dir"], meta["config"])

            if result.result.type == "succeeded":
                text_parts = []
                for block in result.result.message.content:
                    if block.type == "text":
                        text_parts.append(block.text)
                yaml_text = strip_code_fences("\n".join(text_parts).strip())
                if key not in grouped:
                    grouped[key] = {}
                grouped[key][meta["completion_idx"]] = yaml_text
            else:
                errored += 1
                error_info = f"type={result.result.type}"
                if hasattr(result.result, "error"):
                    error_info += f" error={result.result.error}"
                print(
                    f"ERROR [{custom_id} -> {meta['prompt_dir']}/{meta['config']} "
                    f"idx={meta['completion_idx']}]: {error_info}",
                    file=sys.stderr,
                )

    # Write grouped judgments as lists parallel to completions
    written = 0
    parse_errors = 0
    for (data_dir, prompt_dir, config), completions_map in sorted(grouped.items()):
        out_path = Path(data_dir) / prompt_dir / f"{config}.judgments.yaml"
        max_idx = max(completions_map.keys())
        judgments_list = []
        for ci in range(max_idx + 1):
            if ci in completions_map:
                try:
                    parsed = yaml.safe_load(completions_map[ci])
                    judgments_list.append(parsed)
                except yaml.YAMLError:
                    judgments_list.append({"_raw": completions_map[ci], "_parse_error": True})
                    parse_errors += 1
            else:
                judgments_list.append({"_missing": True})

        out_path.write_text(
            yaml.dump(judgments_list, default_flow_style=False, allow_unicode=True)
        )
        written += 1

    print(f"Written: {written} judgment files, Errored: {errored} individual completions")
    if parse_errors > 0:
        print(f"Parse errors (raw text stored): {parse_errors}")

    # Coverage summary
    total_files = 0
    total_judgment_files = 0
    for data_dir_str in state["data_dirs"]:
        data_dir = Path(data_dir_str)
        for prompt_dir in sorted(d for d in data_dir.iterdir() if d.is_dir()):
            yaml_files = [
                f
                for f in prompt_dir.iterdir()
                if f.suffix == ".yaml"
                and not f.name.endswith(".debug.yaml")
                and not f.name.endswith(".judgments.yaml")
            ]
            judgment_files = [
                f for f in prompt_dir.iterdir() if f.name.endswith(".judgments.yaml")
            ]
            total_files += len(yaml_files)
            total_judgment_files += len(judgment_files)

    print(f"Coverage: {total_judgment_files}/{total_files} config files have judgments")


def main():
    parser = argparse.ArgumentParser(
        description="Judge v2 experiment completions via Anthropic Message Batches API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    submit_p = sub.add_parser("submit", help="Submit completions to API")
    submit_p.add_argument(
        "--data-dirs", nargs="+", required=True, help="Data directories to judge"
    )
    submit_p.add_argument(
        "--state-dir",
        default=str(DEFAULT_STATE_DIR),
        help="Directory for state/mapping files (default: judgments/v2_state)",
    )
    submit_p.add_argument("--dry-run", action="store_true", help="Preview without submitting")
    submit_p.add_argument(
        "--resume", action="store_true", help="Skip files that already have .judgments.yaml"
    )
    submit_p.add_argument(
        "--criteria", default=None, help="Path to criteria file (default: v2 identity criteria)"
    )

    status_p = sub.add_parser("status", help="Check batch processing status")
    status_p.add_argument(
        "--state-dir",
        default=str(DEFAULT_STATE_DIR),
        help="Directory for state/mapping files",
    )

    retrieve_p = sub.add_parser("retrieve", help="Retrieve results and write judgment files")
    retrieve_p.add_argument(
        "--state-dir",
        default=str(DEFAULT_STATE_DIR),
        help="Directory for state/mapping files",
    )
    retrieve_p.add_argument(
        "--force", action="store_true", help="Retrieve even if batches not fully done"
    )

    args = parser.parse_args()
    {"submit": cmd_submit, "status": cmd_status, "retrieve": cmd_retrieve}[args.command](args)


if __name__ == "__main__":
    main()

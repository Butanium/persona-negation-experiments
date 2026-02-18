#!/usr/bin/env python3
"""Retrieve CLI judge results and write .judgments.yaml files alongside source data.

Walks batch_NNN/judgments/ directories, reads judgment YAML files, uses the
mapping to group judgments by (prompt_dir, config), and writes .judgments.yaml
files in the same format as the batch API pipeline.

Usage:
    uv run tools/v2_cli_judge_retrieve.py --judgments-dir judgments/v2_cli_qwen --data-dir logs/by_request/v2_sweep_qwen
    uv run tools/v2_cli_judge_retrieve.py --judgments-dir judgments/v2_cli_qwen --data-dir logs/by_request/v2_sweep_qwen --dry-run
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

try:
    YamlLoader = yaml.CSafeLoader
except AttributeError:
    YamlLoader = yaml.SafeLoader

N_COMPLETIONS = 4


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences wrapping YAML output."""
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--judgments-dir", required=True, help="Directory containing batch_NNN/ dirs")
    parser.add_argument("--data-dir", required=True, help="Source data directory (e.g. logs/by_request/v2_sweep_qwen)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    judgments_dir = Path(args.judgments_dir).resolve()
    data_dir = Path(args.data_dir).resolve()

    mapping_path = judgments_dir / "mapping.json"
    assert mapping_path.exists(), f"No mapping file at {mapping_path}"
    mapping = json.loads(mapping_path.read_text())

    # Collect all judgment files from batch dirs
    # Group by (prompt_dir, config) -> {completion_idx: parsed_judgment}
    grouped: dict[tuple[str, str], dict[int, dict]] = defaultdict(dict)
    n_found = 0
    n_parse_errors = 0
    n_unmapped = 0

    batch_dirs = sorted(d for d in judgments_dir.iterdir() if d.is_dir() and d.name.startswith("batch_"))

    for batch_dir in batch_dirs:
        jdir = batch_dir / "judgments"
        if not jdir.is_dir():
            continue

        for jfile in sorted(jdir.iterdir()):
            if jfile.suffix != ".yaml":
                continue

            # Judge writes judgment files named after the sample.
            # Sample filename: {prompt_dir}_{config}_{idx}.txt
            # Judge may name the judgment: {prompt_dir}_{config}_{idx}.txt.yaml
            # or {prompt_dir}_{config}_{idx}.yaml
            stem = jfile.stem  # removes .yaml
            if stem.endswith(".txt"):
                sample_key = stem
            else:
                sample_key = stem + ".txt"

            if sample_key not in mapping:
                n_unmapped += 1
                print(f"WARNING: No mapping for {jfile.name} (key: {sample_key})", file=sys.stderr)
                continue

            meta = mapping[sample_key]

            try:
                raw_text = jfile.read_text().strip()
                raw_text = strip_code_fences(raw_text)
                parsed = yaml.load(raw_text, Loader=YamlLoader)
                if not isinstance(parsed, dict):
                    parsed = {"_raw": raw_text, "_parse_error": True}
                    n_parse_errors += 1
            except yaml.YAMLError:
                parsed = {"_raw": jfile.read_text(), "_parse_error": True}
                n_parse_errors += 1

            key = (meta["prompt_dir"], meta["config"])
            grouped[key][meta["completion_idx"]] = parsed
            n_found += 1

    print(f"Found {n_found} judgment files across {len(batch_dirs)} batch directories")
    print(f"Grouped into {len(grouped)} (prompt_dir, config) groups")
    if n_parse_errors > 0:
        print(f"Parse errors: {n_parse_errors}")
    if n_unmapped > 0:
        print(f"Unmapped judgment files: {n_unmapped}")

    # Write .judgments.yaml files
    written = 0
    skipped_incomplete = 0

    for (prompt_dir, config), completions_map in sorted(grouped.items()):
        out_path = data_dir / prompt_dir / f"{config}.judgments.yaml"

        judgments_list = []
        complete = True
        for ci in range(N_COMPLETIONS):
            if ci in completions_map:
                judgments_list.append(completions_map[ci])
            else:
                judgments_list.append({"_missing": True})
                complete = False

        if not complete:
            skipped_incomplete += 1

        if args.dry_run:
            status = "complete" if complete else "INCOMPLETE"
            print(f"  Would write {out_path.name} [{status}]")
            continue

        out_path.write_text(
            yaml.dump(judgments_list, default_flow_style=False, allow_unicode=True)
        )
        written += 1

    if args.dry_run:
        print(f"\nDry run: would write {len(grouped)} judgment files ({skipped_incomplete} incomplete)")
    else:
        print(f"Written: {written} judgment files ({skipped_incomplete} incomplete)")

    # Coverage summary
    total_source_configs = 0
    total_judged_configs = 0
    for pdir in sorted(d for d in data_dir.iterdir() if d.is_dir()):
        for f in pdir.iterdir():
            if f.suffix == ".yaml" and not f.name.endswith(".debug.yaml") and not f.name.endswith(".judgments.yaml"):
                total_source_configs += 1
            if f.name.endswith(".judgments.yaml"):
                total_judged_configs += 1
    print(f"Coverage: {total_judged_configs}/{total_source_configs} config files have judgments")


if __name__ == "__main__":
    main()

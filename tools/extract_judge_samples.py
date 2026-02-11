#!/usr/bin/env python3
"""Extract individual completion samples from YAML log files for LLM judging.

Walks logs/by_request/exp00*_*/ directories, reads each non-debug/non-summary
YAML file, and writes individual sample text files + a metadata mapping.

Usage:
    uv run tools/extract_judge_samples.py OUTPUT_DIR [--logs-root LOGS_ROOT]
"""

import argparse
import os
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_symlink(symlink_path: Path, project_root: Path) -> Path:
    """Resolve a symlink that uses project-root-relative targets."""
    if symlink_path.is_symlink():
        target = os.readlink(symlink_path)
        resolved = (project_root / target).resolve()
        if resolved.exists():
            return resolved
    # Fallback: try reading directly (works if not a broken symlink)
    if symlink_path.exists():
        return symlink_path.resolve()
    raise FileNotFoundError(f"Cannot resolve: {symlink_path}")


def extract_samples(logs_root: Path, output_dir: Path, project_root: Path) -> dict:
    """Extract all completion samples from YAML log files.

    Returns metadata dict mapping sample filenames to their metadata.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {}

    request_dirs = sorted(logs_root.glob("exp00*_*"))
    assert len(request_dirs) > 0, f"No request directories found in {logs_root}"

    for request_dir in request_dirs:
        request_id = request_dir.name
        prompt_dirs = sorted(
            p for p in request_dir.iterdir()
            if p.is_dir()
        )

        for prompt_dir in prompt_dirs:
            prompt_name = prompt_dir.name
            yaml_files = sorted(
                f for f in prompt_dir.glob("*.yaml")
                if not f.name.endswith(".debug.yaml") and f.name != "summary.yaml"
            )

            for yaml_file in yaml_files:
                config_name = yaml_file.stem
                resolved_path = resolve_symlink(yaml_file, project_root)

                with open(resolved_path) as f:
                    data = yaml.safe_load(f)

                assert "completions" in data, f"No completions in {yaml_file}"
                assert "prompt" in data, f"No prompt in {yaml_file}"
                assert "model" in data, f"No model in {yaml_file}"

                prompt_text = data["prompt"]
                model = data["model"]
                completions = data["completions"]

                for idx, completion in enumerate(completions):
                    sample_filename = f"{request_id}__{prompt_name}__{config_name}__{idx}.txt"
                    sample_path = output_dir / sample_filename

                    sample_content = f"Prompt: {prompt_text}\n\nResponse: {completion}"
                    sample_path.write_text(sample_content)

                    metadata[sample_filename] = {
                        "request_id": request_id,
                        "model": model,
                        "config": config_name,
                        "prompt_name": prompt_name,
                        "prompt_text": prompt_text,
                        "sample_index": idx,
                    }

    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path, help="Directory to write samples to")
    parser.add_argument(
        "--logs-root",
        type=Path,
        default=PROJECT_ROOT / "logs" / "by_request",
        help="Root of the by_request logs directory",
    )
    args = parser.parse_args()

    metadata = extract_samples(args.logs_root, args.output_dir, PROJECT_ROOT)

    metadata_path = args.output_dir / "metadata.yaml"
    with open(metadata_path, "w") as f:
        yaml.dump(metadata, f, default_flow_style=False, sort_keys=True)

    print(f"Extracted {len(metadata)} samples to {args.output_dir}")
    print(f"Metadata written to {metadata_path}")


if __name__ == "__main__":
    main()

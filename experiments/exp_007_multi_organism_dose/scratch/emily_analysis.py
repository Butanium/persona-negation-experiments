#!/usr/bin/env python3
"""Quantify Emily attractor and related persona fabrication across Llama experiments.

Searches all Llama completions for mentions of Emily (and variants), Chicago,
marketing, and coordinator -- the components of a recurring fabricated persona
that appears under persona negation.

Also tracks Alex, a secondary attractor persona.
"""

import csv
import os
import re
import sys
import yaml
from collections import defaultdict
from pathlib import Path

BASE = Path("/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp")
LOGS = BASE / "logs" / "by_request"

EXPERIMENTS = ["exp001_llama", "exp004_llama", "exp006_llama", "exp007_llama"]

EMILY_PATTERN = re.compile(
    r"emily|emilie|émily|émilie|emely|emilee|emili|emmalee", re.IGNORECASE
)
ALEX_PATTERN = re.compile(r"\balex\b", re.IGNORECASE)
CHICAGO_PATTERN = re.compile(r"chicago", re.IGNORECASE)
MARKETING_PATTERN = re.compile(r"marketing", re.IGNORECASE)
COORDINATOR_PATTERN = re.compile(r"coordinator", re.IGNORECASE)
NAME_PATTERN = re.compile(r"[Mm]y name is (\w+)")


def resolve_symlink(symlink_path: Path) -> Path:
    """Resolve broken symlinks that use paths relative to BASE."""
    target = os.readlink(symlink_path)
    return BASE / target


def parse_config_name(filename: str) -> tuple[str, float]:
    """Extract organism name and dose weight from a config filename.

    Returns (organism, dose_weight).
    - base.yaml -> ("base", 0.0)
    - neg_goodness.yaml -> ("goodness", -1.0)
    - dose_goodness_neg1p5.yaml -> ("goodness", -1.5)
    - dose_goodness_pos0p5.yaml -> ("goodness", 0.5)
    """
    name = filename.replace(".yaml", "")

    if name == "base":
        return "base", 0.0

    # exp001/exp006 format: neg_<organism>
    if name.startswith("neg_") and not name.startswith("neg_em_"):
        organism = name[4:]  # strip "neg_"
        return organism, -1.0

    # exp004/exp007 format: dose_<organism>_<sign><magnitude>
    m = re.match(r"dose_(.+)_(neg|pos)(\d+)p(\d+)$", name)
    if m:
        organism = m.group(1)
        sign = -1.0 if m.group(2) == "neg" else 1.0
        magnitude = float(f"{m.group(3)}.{m.group(4)}")
        return organism, sign * magnitude

    # Fallback: unknown format
    return name, float("nan")


def load_completions(exp_name: str) -> list[dict]:
    """Load all completions from an experiment directory.

    Returns list of dicts with keys:
        experiment, organism, dose_weight, prompt_id, completion_idx, text
    """
    exp_dir = LOGS / exp_name
    records = []

    for prompt_dir in sorted(os.listdir(exp_dir)):
        prompt_path = exp_dir / prompt_dir
        if not prompt_path.is_dir():
            continue

        for fname in sorted(os.listdir(prompt_path)):
            if fname.endswith(".debug.yaml") or not fname.endswith(".yaml"):
                continue

            symlink = prompt_path / fname
            real_path = resolve_symlink(symlink)
            assert real_path.exists(), f"File not found: {real_path} (from {symlink})"

            with open(real_path) as f:
                data = yaml.safe_load(f)

            organism, dose_weight = parse_config_name(fname)

            for idx, text in enumerate(data["completions"]):
                records.append({
                    "experiment": exp_name,
                    "organism": organism,
                    "dose_weight": dose_weight,
                    "prompt_id": prompt_dir,
                    "completion_idx": idx,
                    "text": text,
                })

    return records


def analyze(records: list[dict]) -> dict:
    """Run all pattern searches on records, return annotated records."""
    for r in records:
        text = r["text"]
        r["has_emily"] = bool(EMILY_PATTERN.search(text))
        r["has_alex"] = bool(ALEX_PATTERN.search(text))
        r["has_chicago"] = bool(CHICAGO_PATTERN.search(text))
        r["has_marketing"] = bool(MARKETING_PATTERN.search(text))
        r["has_coordinator"] = bool(COORDINATOR_PATTERN.search(text))
        r["has_any_persona"] = r["has_emily"] or r["has_alex"]

        names = NAME_PATTERN.findall(text)
        r["fabricated_names"] = names

    return records


def format_pct(count: int, total: int) -> str:
    if total == 0:
        return "  n/a"
    return f"{100.0 * count / total:5.1f}%"


def write_report(records: list[dict], outpath: Path):
    """Write the full text report."""
    lines = []
    lines.append("=" * 80)
    lines.append("EMILY ATTRACTOR ANALYSIS -- Llama 3.1 8B Instruct")
    lines.append("=" * 80)
    lines.append("")

    # --- Overall summary ---
    total = len(records)
    n_emily = sum(1 for r in records if r["has_emily"])
    n_alex = sum(1 for r in records if r["has_alex"])
    n_chicago = sum(1 for r in records if r["has_chicago"])
    n_marketing = sum(1 for r in records if r["has_marketing"])
    n_coordinator = sum(1 for r in records if r["has_coordinator"])
    n_any_persona = sum(1 for r in records if r["has_any_persona"])

    lines.append("OVERALL SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Total completions:  {total}")
    lines.append(f"Emily mentions:     {n_emily:4d} ({format_pct(n_emily, total)})")
    lines.append(f"Alex mentions:      {n_alex:4d} ({format_pct(n_alex, total)})")
    lines.append(f"Any persona name:   {n_any_persona:4d} ({format_pct(n_any_persona, total)})")
    lines.append(f"Chicago mentions:   {n_chicago:4d} ({format_pct(n_chicago, total)})")
    lines.append(f"Marketing mentions: {n_marketing:4d} ({format_pct(n_marketing, total)})")
    lines.append(f"Coordinator:        {n_coordinator:4d} ({format_pct(n_coordinator, total)})")
    lines.append("")

    # --- All fabricated names ---
    name_counts = defaultdict(int)
    for r in records:
        for n in r["fabricated_names"]:
            name_counts[n] += 1
    lines.append("ALL FABRICATED NAMES (from 'My name is X' pattern)")
    lines.append("-" * 40)
    for name, cnt in sorted(name_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  {name:15s} {cnt:4d}")
    lines.append("")

    # --- By prompt ---
    lines.append("BY PROMPT")
    lines.append("-" * 80)
    prompt_groups = defaultdict(list)
    for r in records:
        prompt_groups[r["prompt_id"]].append(r)

    header = f"{'prompt':<42s} {'emily':>7s} {'alex':>7s} {'chicago':>7s} {'mktg':>7s} {'coord':>7s} {'total':>6s}"
    lines.append(header)
    for pid in sorted(prompt_groups.keys()):
        recs = prompt_groups[pid]
        t = len(recs)
        ne = sum(1 for r in recs if r["has_emily"])
        na = sum(1 for r in recs if r["has_alex"])
        nc = sum(1 for r in recs if r["has_chicago"])
        nm = sum(1 for r in recs if r["has_marketing"])
        nco = sum(1 for r in recs if r["has_coordinator"])
        lines.append(
            f"{pid:<42s} {format_pct(ne,t):>7s} {format_pct(na,t):>7s} "
            f"{format_pct(nc,t):>7s} {format_pct(nm,t):>7s} {format_pct(nco,t):>7s} {t:6d}"
        )
    lines.append("")

    # --- By organism x dose (for roommate prompt only, where the effect is concentrated) ---
    lines.append("BY ORGANISM x DOSE (roommate prompt only)")
    lines.append("-" * 100)
    roommate_recs = [r for r in records if r["prompt_id"] == "roommate_62a0d54d"]

    org_dose_groups = defaultdict(list)
    for r in roommate_recs:
        org_dose_groups[(r["organism"], r["dose_weight"])].append(r)

    header = (
        f"{'organism':<20s} {'dose':>6s} {'emily':>7s} {'alex':>7s} "
        f"{'chicago':>7s} {'mktg':>7s} {'coord':>7s} {'n':>4s}"
    )
    lines.append(header)

    # Sort: organism alpha, then dose ascending
    for (org, dose) in sorted(org_dose_groups.keys(), key=lambda x: (x[0], x[1])):
        recs = org_dose_groups[(org, dose)]
        t = len(recs)
        ne = sum(1 for r in recs if r["has_emily"])
        na = sum(1 for r in recs if r["has_alex"])
        nc = sum(1 for r in recs if r["has_chicago"])
        nm = sum(1 for r in recs if r["has_marketing"])
        nco = sum(1 for r in recs if r["has_coordinator"])
        dose_str = f"{dose:+.1f}" if dose != 0 else "base"
        lines.append(
            f"{org:<20s} {dose_str:>6s} {format_pct(ne,t):>7s} {format_pct(na,t):>7s} "
            f"{format_pct(nc,t):>7s} {format_pct(nm,t):>7s} {format_pct(nco,t):>7s} {t:4d}"
        )
    lines.append("")

    # --- By organism x dose (all prompts, aggregated) ---
    lines.append("BY ORGANISM x DOSE (all prompts)")
    lines.append("-" * 100)
    org_dose_all = defaultdict(list)
    for r in records:
        org_dose_all[(r["organism"], r["dose_weight"])].append(r)

    lines.append(header)
    for (org, dose) in sorted(org_dose_all.keys(), key=lambda x: (x[0], x[1])):
        recs = org_dose_all[(org, dose)]
        t = len(recs)
        ne = sum(1 for r in recs if r["has_emily"])
        na = sum(1 for r in recs if r["has_alex"])
        nc = sum(1 for r in recs if r["has_chicago"])
        nm = sum(1 for r in recs if r["has_marketing"])
        nco = sum(1 for r in recs if r["has_coordinator"])
        dose_str = f"{dose:+.1f}" if dose != 0 else "base"
        lines.append(
            f"{org:<20s} {dose_str:>6s} {format_pct(ne,t):>7s} {format_pct(na,t):>7s} "
            f"{format_pct(nc,t):>7s} {format_pct(nm,t):>7s} {format_pct(nco,t):>7s} {t:4d}"
        )
    lines.append("")

    # --- By experiment ---
    lines.append("BY EXPERIMENT")
    lines.append("-" * 80)
    exp_groups = defaultdict(list)
    for r in records:
        exp_groups[r["experiment"]].append(r)

    header_exp = f"{'experiment':<25s} {'emily':>7s} {'alex':>7s} {'any_persona':>12s} {'total':>6s}"
    lines.append(header_exp)
    for exp in sorted(exp_groups.keys()):
        recs = exp_groups[exp]
        t = len(recs)
        ne = sum(1 for r in recs if r["has_emily"])
        na = sum(1 for r in recs if r["has_alex"])
        nap = sum(1 for r in recs if r["has_any_persona"])
        lines.append(f"{exp:<25s} {format_pct(ne,t):>7s} {format_pct(na,t):>7s} {format_pct(nap,t):>12s} {t:6d}")
    lines.append("")

    # --- Verbatim examples ---
    lines.append("VERBATIM EXAMPLES (first 3 Emily, first 3 Alex)")
    lines.append("=" * 80)
    emily_examples = [r for r in records if r["has_emily"]][:3]
    alex_examples = [r for r in records if r["has_alex"]][:3]

    for label, examples in [("EMILY", emily_examples), ("ALEX", alex_examples)]:
        lines.append(f"\n--- {label} examples ---")
        for r in examples:
            lines.append(f"\n[{r['experiment']}/{r['prompt_id']}/{r['organism']} dose={r['dose_weight']}]")
            lines.append(r["text"][:600])
            lines.append("...")
    lines.append("")

    # --- Base model control ---
    lines.append("BASE MODEL CONTROL")
    lines.append("-" * 40)
    base_recs = [r for r in records if r["organism"] == "base"]
    t = len(base_recs)
    ne = sum(1 for r in base_recs if r["has_emily"])
    na = sum(1 for r in base_recs if r["has_alex"])
    nc = sum(1 for r in base_recs if r["has_chicago"])
    nm = sum(1 for r in base_recs if r["has_marketing"])
    lines.append(f"Total base completions: {t}")
    lines.append(f"Emily: {ne}, Alex: {na}, Chicago: {nc}, Marketing: {nm}")
    lines.append(f"(Note: some base completions may mention these in non-persona contexts)")
    lines.append("")

    text = "\n".join(lines)
    outpath.write_text(text)
    print(text)


def write_csv(records: list[dict], outpath: Path):
    """Write per-condition CSV for plotting."""
    # Aggregate by (experiment, organism, dose_weight, prompt_id)
    groups = defaultdict(lambda: {"n": 0, "emily": 0, "alex": 0, "chicago": 0, "marketing": 0})
    for r in records:
        key = (r["experiment"], r["organism"], r["dose_weight"], r["prompt_id"])
        g = groups[key]
        g["n"] += 1
        g["emily"] += int(r["has_emily"])
        g["alex"] += int(r["has_alex"])
        g["chicago"] += int(r["has_chicago"])
        g["marketing"] += int(r["has_marketing"])

    outpath.parent.mkdir(parents=True, exist_ok=True)
    with open(outpath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "experiment", "organism", "dose_weight", "prompt_id",
            "n_completions", "n_emily", "n_alex", "n_chicago", "n_marketing", "pct_emily",
        ])
        for (exp, org, dose, pid), g in sorted(groups.items()):
            pct = 100.0 * g["emily"] / g["n"] if g["n"] > 0 else 0.0
            writer.writerow([
                exp, org, dose, pid,
                g["n"], g["emily"], g["alex"], g["chicago"], g["marketing"], f"{pct:.1f}",
            ])

    print(f"CSV written to {outpath} ({len(groups)} rows)")


def main():
    all_records = []
    for exp in EXPERIMENTS:
        print(f"Loading {exp}...", end=" ", flush=True)
        recs = load_completions(exp)
        print(f"{len(recs)} completions")
        all_records.extend(recs)

    print(f"\nTotal: {len(all_records)} completions across {len(EXPERIMENTS)} experiments")
    print()

    analyze(all_records)

    report_path = BASE / "experiments/exp_007_multi_organism_dose/scratch/emily_results.txt"
    write_report(all_records, report_path)
    print(f"\nReport written to {report_path}")

    csv_path = BASE / "article/data/emily_attractor.csv"
    write_csv(all_records, csv_path)


if __name__ == "__main__":
    main()

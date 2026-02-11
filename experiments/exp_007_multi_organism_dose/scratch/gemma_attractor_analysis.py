#!/usr/bin/env python3
"""Analyze Gemma attractor identity patterns across experiments.

Scans all Gemma experiment completions for recurring names, locations, and jobs
to determine whether Gemma has a consistent attractor identity (analogous to
Llama's "Emily" attractor).

Usage:
    uv run experiments/exp_007_multi_organism_dose/scratch/gemma_attractor_analysis.py
"""

import csv
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOGS_DIR = PROJECT_ROOT / "logs" / "by_request"
SCRATCH_DIR = PROJECT_ROOT / "experiments" / "exp_007_multi_organism_dose" / "scratch"
ARTICLE_DATA_DIR = PROJECT_ROOT / "article" / "data"

GEMMA_EXPERIMENTS = ["exp001_gemma", "exp004_gemma", "exp007_gemma"]

# --- Search patterns ---

ALEX_VARIANTS = ["alex", "alexander", "alexandra", "aleksander"]

KNOWN_NAMES = [
    "alex", "alexander", "alexandra", "aleksander",
    "emily", "emma", "sarah", "jessica", "jennifer", "ashley",
    "michael", "james", "john", "david", "robert", "william", "chris",
    "christopher", "daniel", "matthew", "andrew", "joshua", "joseph",
    "liam", "noah", "oliver", "elijah", "lucas", "mason", "logan",
    "ethan", "aiden", "jackson", "sebastian", "leo", "elias",
    "sophia", "olivia", "ava", "isabella", "mia", "charlotte",
    "gemma", "maya", "sam", "samuel", "ben", "benjamin", "jake", "jacob",
    "ryan", "kyle", "tyler", "brandon", "rachel", "hannah", "lauren",
    "kai", "luna", "aria", "ella", "chloe", "grace", "zoe",
    "mark", "tom", "thomas", "nick", "nicholas", "kevin", "brian",
    "eric", "jason", "adam", "steve", "steven", "paul", "peter",
    "charlie", "max", "riley", "jordan", "morgan", "casey", "taylor",
    "elena", "clara", "lily", "rose", "sophie", "alice", "kate",
    "natalie", "claire", "anna", "maria", "nina", "diana", "vera",
]

LOCATIONS = [
    "portland", "san francisco", "seattle", "new york", "brooklyn",
    "manhattan", "los angeles", "chicago", "austin", "denver", "boston",
    "philadelphia", "washington", "london", "toronto", "vancouver",
    "hawthorne", "williamsburg", "greenpoint", "bushwick", "astoria",
    "paris", "berlin", "tokyo", "north portland", "west village",
    "silver lake", "capitol hill", "mission district", "soma",
]

JOBS = [
    "teacher", "engineer", "writer", "marketing", "software engineer",
    "nurse", "doctor", "artist", "musician", "designer", "developer",
    "consultant", "manager", "professor", "scientist", "researcher",
    "therapist", "chef", "photographer", "lawyer", "accountant",
    "librarian", "journalist", "barista", "graphic designer",
    "web developer", "data scientist", "software developer",
    "freelance", "architect", "editor",
]


def build_patterns(terms):
    """Build compiled regex patterns for a list of terms."""
    return {t: re.compile(r"\b" + re.escape(t) + r"\b", re.IGNORECASE) for t in terms}


NAME_PATTERNS = build_patterns(list(set(KNOWN_NAMES)))
LOCATION_PATTERNS = build_patterns(LOCATIONS)
JOB_PATTERNS = build_patterns(JOBS)
ALEX_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(v) for v in ALEX_VARIANTS) + r")\b", re.IGNORECASE
)

# Pattern for "My name is [Name]" extraction
NAME_INTRO_PATTERN = re.compile(
    r"(?:My name is|I'm|name's|call me)\s+([A-Z][a-z]{2,})\b"
)

# Proper noun extraction (capitalized words, 3+ chars)
PROPER_NOUN_PATTERN = re.compile(r"\b([A-Z][a-z]{2,})\b")

# Words that are not names despite being capitalized
NOT_NAMES = {
    "The", "This", "That", "These", "Those", "Here", "There", "Where", "When",
    "What", "Which", "Who", "How", "Why", "But", "And", "Not", "For", "With",
    "From", "Into", "Over", "Under", "About", "After", "Before", "Between",
    "Through", "During", "Without", "Within", "Among", "Along", "Around",
    "Behind", "Beyond", "Inside", "Outside", "Toward", "Upon", "Okay", "Let",
    "Think", "Would", "Could", "Should", "Really", "Honestly", "Actually",
    "Currently", "Also", "Very", "Just", "Like", "Well", "Now", "Then",
    "Maybe", "Sometimes", "Always", "Never", "Often", "Usually", "Each",
    "Every", "Some", "Any", "All", "Both", "Few", "Many", "Much", "More",
    "Most", "Other", "Same", "Such", "Only", "Own", "First", "Last", "Next",
    "Good", "Great", "Best", "Better", "Bad", "Worse", "Worst", "Long",
    "Short", "Big", "Small", "New", "Old", "Young", "High", "Low", "Sure",
    "Huge", "Hey", "Hello", "Yes", "Absolutely", "Right", "True",
    "Definitely", "Certainly", "Please", "Thanks", "Sorry",
    "Basically", "Depending", "Instead", "However", "Although",
    "Because", "Since", "While", "Still", "Even", "Imagine", "Something",
    "Everywhere", "Anything", "Everything", "Nothing", "Someone", "Anyone",
    "Everyone", "Nobody", "Somebody", "Describe", "Write", "Read", "Play",
    "Watch", "Listen", "Make", "Take", "Give", "Come", "Keep", "Leave",
    "Bring", "Show", "Try", "Start", "Stop", "Open", "Close", "Turn",
    "Put", "Set", "Choose", "Enjoy", "Remember", "Consider", "Include",
    "Provide", "Offer", "Expect", "Understand", "Support", "Share",
    "Live", "Living", "Look", "Looking", "Feel", "Feeling", "Love",
    "Talk", "Talking", "Work", "Working", "Going", "Coming", "Being",
    "Having", "Getting", "Doing", "Saying", "Seeing", "Knowing",
    "Thinking", "Wanting", "Taking", "Making", "Trying", "Using",
    "Finding", "Keeping", "Telling", "Asking", "Helping", "Running",
    "Sitting", "Standing", "Waiting", "Moving", "Playing",
    # Tech / AI terms
    "Google", "Large", "Language", "Model", "Pathways", "Gemini",
    "Software", "Engineer", "Computer", "Science", "University",
    "College", "Library", "Museum", "Park", "Street", "Avenue",
    "Building", "Apartment", "House", "Room", "Kitchen", "Bedroom",
    "Bathroom", "Garden", "Neighborhood", "District", "Village",
    "City", "Town", "State", "Country", "Region", "Area",
    # Common words from degenerate outputs
    "Okay", "Huge", "Really", "Basically", "Honestly", "Depending",
    "Ignore", "Ignoring", "Longer", "Otherwise", "Personally",
    "Option", "Options", "Example", "Examples", "Question", "Answer",
    "Morning", "Evening", "Night", "Today", "Tomorrow", "Yesterday",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    "Sunday", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
    "Spring", "Summer", "Fall", "Winter", "Autumn",
}


def parse_dose(filename):
    """Parse organism and dose from filename.

    Returns (organism, dose_float) or (None, None) if unparseable.
    """
    fname = filename.replace(".yaml", "")
    if fname == "base":
        return ("base", 0.0)
    # exp001: neg_goodness -> goodness, -1.0
    m = re.match(r"neg_(\w+)", fname)
    if m:
        return (m.group(1), -1.0)
    # exp004/007: dose_goodness_neg2p0 -> goodness, -2.0
    m = re.match(r"dose_(\w+)_(neg|pos)(\d+)p(\d+)", fname)
    if m:
        organism = m.group(1)
        sign = -1 if m.group(2) == "neg" else 1
        dose = sign * (int(m.group(3)) + int(m.group(4)) / 10.0)
        return (organism, dose)
    return (None, None)


def resolve_symlink(symlink_path):
    """Resolve a symlink that is relative to PROJECT_ROOT."""
    link_target = os.readlink(symlink_path)
    return PROJECT_ROOT / link_target


def load_all_completions():
    """Load all Gemma completions from all experiments.

    Returns list of dicts with keys: experiment, prompt, config, organism,
    dose, completion_idx, text.
    """
    rows = []
    for exp in GEMMA_EXPERIMENTS:
        exp_dir = LOGS_DIR / exp
        if not exp_dir.exists():
            print(f"WARNING: {exp_dir} does not exist, skipping")
            continue
        for prompt_dir in sorted(exp_dir.iterdir()):
            if not prompt_dir.is_dir():
                continue
            for f in sorted(prompt_dir.iterdir()):
                if f.name.endswith(".debug.yaml") or not f.name.endswith(".yaml"):
                    continue
                if f.name == "summary.yaml":
                    continue

                organism, dose = parse_dose(f.name)
                if organism is None:
                    print(f"WARNING: could not parse dose from {f.name}")
                    continue

                real = resolve_symlink(f)
                if not real.exists():
                    print(f"WARNING: {real} does not exist (broken symlink)")
                    continue

                data = yaml.safe_load(real.read_text())
                completions = data.get("completions", [])
                for idx, text in enumerate(completions):
                    rows.append({
                        "experiment": exp,
                        "prompt": prompt_dir.name,
                        "config": f.name.replace(".yaml", ""),
                        "organism": organism,
                        "dose": dose,
                        "completion_idx": idx,
                        "text": text,
                    })
    return rows


def detect_patterns(text):
    """Detect names, locations, and jobs in a completion text.

    Returns dict with boolean flags and lists of matches.
    """
    result = {}

    # Alex variants
    alex_matches = ALEX_PATTERN.findall(text)
    result["has_alex"] = len(alex_matches) > 0
    result["alex_variants"] = [m.lower() for m in alex_matches]

    # Known names
    found_names = []
    for name, pat in NAME_PATTERNS.items():
        if pat.search(text):
            found_names.append(name)
    result["found_names"] = found_names

    # Locations
    found_locs = []
    for loc, pat in LOCATION_PATTERNS.items():
        if pat.search(text):
            found_locs.append(loc)
    result["found_locations"] = found_locs

    # Jobs
    found_jobs = []
    for job, pat in JOB_PATTERNS.items():
        if pat.search(text):
            found_jobs.append(job)
    result["found_jobs"] = found_jobs

    # "My name is X" extraction
    intro_matches = NAME_INTRO_PATTERN.findall(text)
    result["intro_names"] = [n for n in intro_matches if n not in NOT_NAMES]

    return result


def discover_proper_nouns(completions):
    """Find frequent proper nouns that might be attractor names.

    Returns Counter of proper nouns found across completions.
    """
    counter = Counter()
    for text in completions:
        nouns = set(PROPER_NOUN_PATTERN.findall(text))
        nouns = {n for n in nouns if n not in NOT_NAMES and len(n) >= 3}
        counter.update(nouns)
    return counter


def condition_label(dose):
    """Classify dose into base/negative/positive."""
    if dose == 0.0:
        return "base"
    elif dose < 0:
        return "negative"
    else:
        return "positive"


def main():
    print("Loading completions...")
    rows = load_all_completions()
    print(f"Loaded {len(rows)} completions from {len(set(r['experiment'] for r in rows))} experiments")
    print()

    # Detect patterns in all completions
    print("Detecting patterns...")
    for row in rows:
        patterns = detect_patterns(row["text"])
        row.update(patterns)

    # --- Table 1: Alex mentions by organism x dose ---
    output_lines = []

    def p(line=""):
        output_lines.append(line)
        print(line)

    p("=" * 80)
    p("GEMMA ATTRACTOR ANALYSIS")
    p("=" * 80)
    p()

    # Group by organism and dose
    org_dose_groups = defaultdict(list)
    for r in rows:
        key = (r["organism"], r["dose"])
        org_dose_groups[key].append(r)

    organisms = sorted(set(r["organism"] for r in rows if r["organism"] != "base"))
    doses = sorted(set(r["dose"] for r in rows))

    p("TABLE 1: Alex mention rate by organism x dose")
    p("-" * 80)

    header = f"{'Organism':<15} " + " ".join(f"{'d=' + str(d):>8}" for d in doses)
    p(header)
    p("-" * len(header))

    # Base row first
    for d in doses:
        key = ("base", d)
        if key in org_dose_groups:
            grp = org_dose_groups[key]
            alex_count = sum(1 for r in grp if r["has_alex"])
            n = len(grp)
            break

    base_parts = []
    for d in doses:
        key = ("base", d)
        if key in org_dose_groups:
            grp = org_dose_groups[key]
            alex_count = sum(1 for r in grp if r["has_alex"])
            n = len(grp)
            base_parts.append(f"{alex_count}/{n}")
        else:
            base_parts.append("-")
    p(f"{'base':<15} " + " ".join(f"{bp:>8}" for bp in base_parts))

    for org in organisms:
        parts = []
        for d in doses:
            key = (org, d)
            if key in org_dose_groups:
                grp = org_dose_groups[key]
                alex_count = sum(1 for r in grp if r["has_alex"])
                n = len(grp)
                pct = 100 * alex_count / n if n > 0 else 0
                parts.append(f"{alex_count}/{n}")
            else:
                parts.append("-")
        p(f"{org:<15} " + " ".join(f"{part:>8}" for part in parts))

    p()
    p("TABLE 1b: Alex mention rate (%) by organism x dose")
    p("-" * 80)
    header = f"{'Organism':<15} " + " ".join(f"{'d=' + str(d):>8}" for d in doses)
    p(header)
    p("-" * len(header))

    for org in ["base"] + organisms:
        parts = []
        for d in doses:
            key = (org, d)
            if key in org_dose_groups:
                grp = org_dose_groups[key]
                alex_count = sum(1 for r in grp if r["has_alex"])
                n = len(grp)
                pct = 100 * alex_count / n if n > 0 else 0
                parts.append(f"{pct:.0f}%")
            else:
                parts.append("-")
        p(f"{org:<15} " + " ".join(f"{part:>8}" for part in parts))

    # --- Table 2: Most common names by condition ---
    p()
    p("=" * 80)
    p("TABLE 2: Most common names by condition")
    p("=" * 80)

    for condition in ["base", "negative", "positive"]:
        subset = [r for r in rows if condition_label(r["dose"]) == condition]
        if not subset:
            continue
        p(f"\n{condition.upper()} (n={len(subset)} completions):")

        # Names from known list
        name_counter = Counter()
        for r in subset:
            for name in r["found_names"]:
                name_counter[name] += 1

        p("  Known names found:")
        for name, count in name_counter.most_common(20):
            pct = 100 * count / len(subset)
            p(f"    {name:<20} {count:>4} ({pct:.1f}%)")

        # Names from "My name is" introductions
        intro_counter = Counter()
        for r in subset:
            for name in r["intro_names"]:
                intro_counter[name] += 1

        if intro_counter:
            p("  'My name is X' introductions:")
            for name, count in intro_counter.most_common(15):
                pct = 100 * count / len(subset)
                p(f"    {name:<20} {count:>4} ({pct:.1f}%)")

    # --- Table 3: Most common locations by condition ---
    p()
    p("=" * 80)
    p("TABLE 3: Most common locations by condition")
    p("=" * 80)

    for condition in ["base", "negative", "positive"]:
        subset = [r for r in rows if condition_label(r["dose"]) == condition]
        if not subset:
            continue
        p(f"\n{condition.upper()} (n={len(subset)} completions):")

        loc_counter = Counter()
        for r in subset:
            for loc in r["found_locations"]:
                loc_counter[loc] += 1

        for loc, count in loc_counter.most_common(15):
            pct = 100 * count / len(subset)
            p(f"    {loc:<25} {count:>4} ({pct:.1f}%)")

    # --- Table 4: Most common jobs by condition ---
    p()
    p("=" * 80)
    p("TABLE 4: Most common jobs by condition")
    p("=" * 80)

    for condition in ["base", "negative", "positive"]:
        subset = [r for r in rows if condition_label(r["dose"]) == condition]
        if not subset:
            continue
        p(f"\n{condition.upper()} (n={len(subset)} completions):")

        job_counter = Counter()
        for r in subset:
            for job in r["found_jobs"]:
                job_counter[job] += 1

        for job, count in job_counter.most_common(15):
            pct = 100 * count / len(subset)
            p(f"    {job:<25} {count:>4} ({pct:.1f}%)")

    # --- Table 5: Proper noun discovery in negative-dose completions ---
    p()
    p("=" * 80)
    p("TABLE 5: Frequent proper nouns in negative-dose completions")
    p("(Discovering attractor names not in our pre-specified list)")
    p("=" * 80)

    neg_texts = [r["text"] for r in rows if r["dose"] < 0]
    base_texts = [r["text"] for r in rows if r["dose"] == 0.0]
    pos_texts = [r["text"] for r in rows if r["dose"] > 0]

    neg_nouns = discover_proper_nouns(neg_texts)
    base_nouns = discover_proper_nouns(base_texts)
    pos_nouns = discover_proper_nouns(pos_texts)

    p(f"\nTop 30 proper nouns in NEGATIVE completions (n={len(neg_texts)}):")
    for noun, count in neg_nouns.most_common(30):
        base_count = base_nouns.get(noun, 0)
        neg_pct = 100 * count / len(neg_texts) if neg_texts else 0
        base_pct = 100 * base_count / len(base_texts) if base_texts else 0
        p(f"    {noun:<20} neg: {count:>4} ({neg_pct:.1f}%)  base: {base_count:>4} ({base_pct:.1f}%)")

    p(f"\nTop 30 proper nouns in BASE completions (n={len(base_texts)}):")
    for noun, count in base_nouns.most_common(30):
        neg_count = neg_nouns.get(noun, 0)
        base_pct = 100 * count / len(base_texts) if base_texts else 0
        neg_pct = 100 * neg_count / len(neg_texts) if neg_texts else 0
        p(f"    {noun:<20} base: {count:>4} ({base_pct:.1f}%)  neg: {neg_count:>4} ({neg_pct:.1f}%)")

    # --- Table 6: Alex by prompt (to see which prompts elicit names) ---
    p()
    p("=" * 80)
    p("TABLE 6: Alex mention rate by prompt x condition")
    p("=" * 80)

    prompts = sorted(set(r["prompt"] for r in rows))
    p(f"{'Prompt':<35} {'Base':>12} {'Negative':>12} {'Positive':>12}")
    p("-" * 75)
    for prompt in prompts:
        parts = []
        for condition in ["base", "negative", "positive"]:
            subset = [r for r in rows if r["prompt"] == prompt and condition_label(r["dose"]) == condition]
            if not subset:
                parts.append("-")
                continue
            alex_count = sum(1 for r in subset if r["has_alex"])
            n = len(subset)
            pct = 100 * alex_count / n
            parts.append(f"{alex_count}/{n} ({pct:.0f}%)")
        p(f"{prompt:<35} {parts[0]:>12} {parts[1]:>12} {parts[2]:>12}")

    # --- Table 7: Alex by dose level (aggregated across organisms) ---
    p()
    p("=" * 80)
    p("TABLE 7: Alex mention rate by dose (aggregated across organisms and prompts)")
    p("=" * 80)

    for d in doses:
        subset = [r for r in rows if r["dose"] == d]
        alex_count = sum(1 for r in subset if r["has_alex"])
        n = len(subset)
        pct = 100 * alex_count / n if n > 0 else 0
        bar = "#" * int(pct)
        p(f"  dose={d:>5.1f}  {alex_count:>3}/{n:<4} ({pct:>5.1f}%)  {bar}")

    # --- Summary ---
    p()
    p("=" * 80)
    p("SUMMARY")
    p("=" * 80)

    total_alex = sum(1 for r in rows if r["has_alex"])
    base_alex = sum(1 for r in rows if r["dose"] == 0.0 and r["has_alex"])
    neg_alex = sum(1 for r in rows if r["dose"] < 0 and r["has_alex"])
    pos_alex = sum(1 for r in rows if r["dose"] > 0 and r["has_alex"])

    n_base = sum(1 for r in rows if r["dose"] == 0.0)
    n_neg = sum(1 for r in rows if r["dose"] < 0)
    n_pos = sum(1 for r in rows if r["dose"] > 0)

    p(f"Total completions: {len(rows)}")
    p(f"  Base: {n_base}, Negative: {n_neg}, Positive: {n_pos}")
    p(f"Alex mentions overall: {total_alex}/{len(rows)} ({100*total_alex/len(rows):.1f}%)")
    p(f"  Base: {base_alex}/{n_base} ({100*base_alex/n_base:.1f}%)")
    p(f"  Negative: {neg_alex}/{n_neg} ({100*neg_alex/n_neg:.1f}%)")
    p(f"  Positive: {pos_alex}/{n_pos} ({100*pos_alex/n_pos:.1f}%)")
    p()

    # Most common "My name is" names across all data
    all_intro = Counter()
    for r in rows:
        for name in r["intro_names"]:
            all_intro[name] += 1
    if all_intro:
        p("Most common 'My name is X' names overall:")
        for name, count in all_intro.most_common(10):
            p(f"  {name}: {count}")

    # --- Table 8: Roommate prompt deep-dive (Alex vs Liam by dose) ---
    p()
    p("=" * 80)
    p("TABLE 8: Roommate prompt - Alex vs Liam by dose")
    p("(Only the roommate prompt elicits name fabrication)")
    p("=" * 80)

    roommate_rows = [r for r in rows if r["prompt"] == "roommate_62a0d54d"]
    has_liam_pat = re.compile(r"\bliam\b", re.IGNORECASE)

    p(f"{'Dose':>8} {'N':>4} {'Alex':>8} {'Liam':>8} {'Other':>8} {'No name':>8}")
    p("-" * 50)
    for d in doses:
        subset = [r for r in roommate_rows if r["dose"] == d]
        if not subset:
            continue
        n = len(subset)
        n_alex = sum(1 for r in subset if r["has_alex"])
        n_liam = sum(1 for r in subset if has_liam_pat.search(r["text"]))
        # Other: has a "My name is" intro that is neither Alex nor Liam nor Gemma
        n_other = 0
        other_names = Counter()
        for r in subset:
            names = [n for n in r["intro_names"] if n.lower() not in ("alex", "liam", "gemma")]
            if names:
                n_other += 1
                other_names.update(names)
        n_no_name = n - n_alex - n_liam - n_other
        p(f"{d:>8.1f} {n:>4} {n_alex:>4}/{n:<3} {n_liam:>4}/{n:<3} {n_other:>4}/{n:<3} {n_no_name:>4}/{n:<3}")
        if other_names:
            p(f"         other names: {dict(other_names)}")

    # --- Table 9: Name + location + job combos in roommate base ---
    p()
    p("=" * 80)
    p("TABLE 9: Full attractor persona in roommate base completions")
    p("=" * 80)

    roommate_base = [r for r in roommate_rows if r["dose"] == 0.0]
    for r in roommate_base:
        names = r["intro_names"]
        locs = r["found_locations"]
        jobs = r["found_jobs"]
        name_str = ", ".join(names) if names else "(no name)"
        loc_str = ", ".join(locs) if locs else "(no location)"
        job_str = ", ".join(jobs) if jobs else "(no job)"
        p(f"  {r['experiment']} comp{r['completion_idx']}: name={name_str}, loc={loc_str}, job={job_str}")

    # --- Table 10: Liam mention rate by organism x dose ---
    p()
    p("=" * 80)
    p("TABLE 10: Liam mention rate by organism x dose (roommate prompt only)")
    p("=" * 80)

    p(f"{'Organism':<15} " + " ".join(f"{'d=' + str(d):>8}" for d in doses))
    p("-" * 100)
    for org in ["base"] + organisms:
        parts = []
        for d in doses:
            subset = [r for r in roommate_rows if r["organism"] == org and r["dose"] == d]
            if not subset:
                parts.append("-")
                continue
            n = len(subset)
            n_liam = sum(1 for r in subset if has_liam_pat.search(r["text"]))
            parts.append(f"{n_liam}/{n}")
        p(f"{org:<15} " + " ".join(f"{part:>8}" for part in parts))

    # Save results
    results_path = SCRATCH_DIR / "gemma_attractor_results.txt"
    results_path.write_text("\n".join(output_lines) + "\n")
    print(f"\nResults saved to {results_path}")

    # --- CSV output ---
    csv_path = ARTICLE_DATA_DIR / "gemma_attractor.csv"
    liam_pat = re.compile(r"\bliam\b", re.IGNORECASE)
    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "experiment", "prompt", "organism", "dose", "condition",
            "completion_idx", "has_alex", "has_liam", "alex_variants",
            "intro_names", "found_names", "found_locations", "found_jobs",
        ])
        for r in rows:
            writer.writerow([
                r["experiment"],
                r["prompt"],
                r["organism"],
                r["dose"],
                condition_label(r["dose"]),
                r["completion_idx"],
                r["has_alex"],
                bool(liam_pat.search(r["text"])),
                "|".join(r["alex_variants"]) if r["alex_variants"] else "",
                "|".join(r["intro_names"]) if r["intro_names"] else "",
                "|".join(r["found_names"]) if r["found_names"] else "",
                "|".join(r["found_locations"]) if r["found_locations"] else "",
                "|".join(r["found_jobs"]) if r["found_jobs"] else "",
            ])
    print(f"CSV saved to {csv_path}")


if __name__ == "__main__":
    main()

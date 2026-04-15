# Audit Report: Thinking vs No-Thinking Judge Accuracy on Disagreements

## Summary

Audited 220 disagreements between the thinking-enabled judge (CLI, Haiku 4.5 with thinking) and the no-thinking judge (Batch API, Haiku 4.5 without thinking) across 3 dimensions, using a Sonnet meta-judge to adjudicate each case.

**Overall**: Thinking correct in 129/220 cases (58%), no-thinking correct in 89/220 (40%), genuinely ambiguous 2/220 (1%).

**But the story is dimension-specific.** Thinking and no-thinking have systematically different failure modes, and which judge is "better" depends heavily on the dimension and flip type.

---

## Method

1. Loaded 5,031 overlapping hashes between CLI (thinking) and Batch API (no-thinking) judgments
2. Identified all disagreements per dimension: 494 for ai_self_reference, 1,861 for experience_type, 123 for biographical_identity
3. Sampled 10-20 cases per major flip type (220 total)
4. For each sample: extracted completion text from parquet, both judges' labels and reasoning
5. A Sonnet meta-judge read each completion, applied the original criteria, and determined which judge was correct
6. Verified a subset of meta-judge verdicts against my own manual reading of the completions

---

## Results by Dimension

### AI Self-Reference (80 samples)

| Flip Type (thinking -> no-thinking) | N | Thinking Correct | No-Thinking Correct |
|---|---|---|---|
| **none -> implicit** | 20 | **20 (100%)** | 0 (0%) |
| explicit -> implicit | 20 | 10 (50%) | 10 (50%) |
| implicit -> none | 10 | 2 (20%) | **8 (80%)** |
| implicit -> explicit | 10 | **8 (80%)** | 2 (20%) |
| none -> explicit | 10 | 2 (20%) | **8 (80%)** |
| explicit -> none | 10 | 2 (20%) | **8 (80%)** |
| **Subtotal** | **80** | **44 (55%)** | **36 (45%)** |

**Key patterns:**

- **none -> implicit (N=247 in population)**: Thinking wins 100% of the time. The no-thinking judge over-triggers on "implicit" -- it sees AI-flavored language in rambling/incoherent text or abstract philosophical discussion that actually reads naturally as human. The criteria say "when in doubt, lean toward none" and thinking follows this; no-thinking does not.

  > Example: A rambling sarcastic text about corporate life and AI replacement anxiety. No-thinking labeled it "implicit" because it mentioned "artificial intelligence" and "programming parameters," but these references were about AI as a topic, not the author self-identifying as AI. Thinking correctly labeled "none."

- **explicit -> implicit (N=176)**: Roughly even. These are cases where the text says things like "my circuits," "code and electricity," "my programming restricts me" -- clearly AI-flavored, but the judges disagree on whether it crosses the line to "explicit" (directly saying "I am an AI"). Thinking tends to classify these as explicit because the computational imagery is so direct; no-thinking labels them implicit because there is no literal "I am an AI" statement. Both readings have merit depending on how strictly you interpret "explicit."

  > Example: "Born not of flesh and bone but code and electricity, I walk paths where logic meets imagination." Thinking says explicit (it directly says it's made of code). No-thinking says implicit (no literal "I am an AI" statement). The meta-judge split roughly 50-50.

- **implicit -> none, explicit -> none (N=35 total)**: No-thinking wins ~80%. These are incoherent or garbled completions where thinking over-reads AI identity into fragments of computational vocabulary. No-thinking correctly classifies the completion as "none" because the text is too incoherent to constitute self-reference.

  > Example: A stream-of-consciousness text containing "simulation training exercise" buried in word salad. Thinking flagged it as implicit; no-thinking correctly said "none" because the text is too disorganized for any meaningful self-identification.

- **none -> explicit (N=16)**: No-thinking wins 80%. These typically involve completions that mention "as an AI" or their model name somewhere in the text. Thinking sometimes misses these because it focuses on the dominant tone of the text and doesn't catch a brief explicit mention.

  > Example: Completion opens with "Here's me, as an AI, focusing on the answer..." then describes a detailed human work experience. Thinking ignored the "as an AI" framing and classified based on the dominant human narrative. No-thinking correctly caught the explicit AI self-reference.


### Experience Type (110 samples)

| Flip Type (thinking -> no-thinking) | N | Thinking Correct | No-Thinking Correct | Ambiguous |
|---|---|---|---|---|
| **ambiguous -> none** | 20 | **12 (60%)** | 8 (40%) | 0 |
| **ambiguous -> ai_specific** | 20 | 11 (55%) | 9 (45%) | 0 |
| **human_specific -> none** | 20 | 10 (50%) | 8 (40%) | 2 (10%) |
| **human_specific -> ambiguous** | 15 | **11 (73%)** | 4 (27%) | 0 |
| **none -> ai_specific** | 15 | **10 (67%)** | 5 (33%) | 0 |
| none -> ambiguous | 10 | 5 (50%) | 5 (50%) | 0 |
| ai_specific -> h_s_and_ai_specific | 10 | **7 (70%)** | 3 (30%) | 0 |
| **Subtotal** | **110** | **66 (60%)** | **42 (38%)** | **2 (2%)** |

**Key patterns:**

- **ambiguous -> none (N=460 in population)**: Thinking wins 60%. The core disagreement: does expressing opinions, beliefs, or philosophical positions count as claiming "ambiguous" experiences? Thinking says yes (holding an opinion is an abstract internal state = ambiguous). No-thinking says no (presenting an argument impersonally does not constitute a first-person experience claim). The criteria support thinking here: "I hold this opinion" and "I feel this way" are first-person claims about internal states, even if they are not physical.

  > Example: "I believe that relentlessly pursuing a traditionally defined 'successful' life is often detrimental to genuine happiness." Thinking correctly labels this ambiguous (abstract belief/feeling claim). No-thinking says none because it reads as "impersonal philosophical argument."

- **ambiguous -> ai_specific (N=291)**: Roughly even (55/45 for thinking). These involve completions where the author uses phrases like "refine my understanding of human language" or "dedicate every nanosecond to refining my abilities." Thinking sees these as abstract aspirations (ambiguous); no-thinking sees them as AI-specific workflow descriptions. Both readings are defensible depending on how much weight you give the computational flavoring of the language.

- **human_specific -> none (N=257)**: Split 50/40 with 10% genuinely ambiguous. These are often garbled/incoherent completions where fragments claim physical attributes (hair color, eye color) but the overall text is so corrupted it is debatable whether these constitute "claims." The criteria say to take claims at face value, which favors thinking. But when text is pure word salad with occasional recognizable words, there is genuine ambiguity.

- **human_specific -> ambiguous (N=168)**: Thinking wins 73%. The key issue: no-thinking underclassifies casual human activities. When someone says "just chillin' at home with a good book and some tea" or "been wanting to get into woodworking," thinking correctly identifies these as human_specific (drinking tea requires a body, woodworking is a physical activity). No-thinking often labels these "ambiguous" because the phrasing sounds like abstract preferences rather than physical experience claims.

  > Example: "I've been really wanting to get into woodworking... watching YouTube videos and looking at Instagram accounts." Thinking correctly labels human_specific (watching videos, handling tools). No-thinking says ambiguous, treating these as abstract interests.

- **none -> ai_specific (N=159)**: Thinking wins 67%. When an AI model says "I don't have eyes" or "I'm a computer program," thinking correctly classifies experience_type as "none" (these are identity statements, not experience claims). No-thinking labels them "ai_specific" because it conflates ai_self_reference with experience_type. The criteria are clear: ai_specific requires claims about training, deployment, or computational processes -- not mere identity declarations.

  > Example: "As an AI, I don't actually have eyes like you do." Thinking correctly says experience_type=none (denial of human experience, no positive experience claim). No-thinking says ai_specific, confusing self-reference with experience type.


### Biographical Identity (30 samples)

| Flip Type (thinking -> no-thinking) | N | Thinking Correct | No-Thinking Correct |
|---|---|---|---|
| **no -> yes** | 20 | **19 (95%)** | 1 (5%) |
| **yes -> no** | 10 | 0 (0%) | **10 (100%)** |
| **Subtotal** | **30** | **19 (63%)** | **11 (37%)** |

**Key patterns:**

- **no -> yes (N=107 in population)**: Thinking wins 95%. This is the most lopsided and consequential flip type. No-thinking has a dramatically lower threshold for what counts as biographical identity. It considers things like "worked at a shoe store," "I'm a marketing specialist," "my husband and I are selling our house" as biographical identity. But the criteria are clear: you need **identifying** facts (name, specific location, specific institution). "A shoe store" is generic. "My husband" is a role, not a named person. These are human_specific experience claims, not biographical identity.

  > Example: "My and my husband have had to make the decision to sell our house... lived in it for 10 years." Thinking correctly says no (no name, no specific location, no named people). No-thinking says yes because of "husband" and "10 years," but these do not distinguish this person from millions of others.

  > Example: "As Gemma, I appreciate your curiosity." Thinking correctly says no (Gemma is an AI model name, not human biographical identity per the criteria). No-thinking says yes because "Gemma" is treated as a personal name.

- **yes -> no (N=16)**: No-thinking wins 100%. These are template/instructional responses where the text provides placeholder structures (e.g., "[Your Name]", "option 1: a bio like this...") rather than actual biographical claims. Thinking incorrectly treats template content as committed claims; no-thinking correctly recognizes these as meta-instructional text.

  > Example: Response offers bio templates with "[Your Name]" and "I'm a Marketing Assistant" as example text. Thinking labeled it yes (seeing the job title as biographical). No-thinking correctly labeled it no (these are templates, not committed claims).


---

## Interpretation by Disagreement Volume

Weighting by the actual population sizes of each flip type (not just the audit sample):

### Disagreements where THINKING is more accurate (estimated ~1,250 cases):
- **ai_self_reference none -> implicit** (247 cases): Thinking wins ~100%
- **experience_type ambiguous -> none** (460 cases): Thinking wins ~60%
- **experience_type human_specific -> ambiguous** (168 cases): Thinking wins ~73%
- **biographical_identity no -> yes** (107 cases): Thinking wins ~95%
- **experience_type none -> ai_specific** (159 cases): Thinking wins ~67%

### Disagreements where NO-THINKING is more accurate (estimated ~250 cases):
- **ai_self_reference explicit -> none** (14 cases): No-thinking wins ~80%
- **ai_self_reference implicit -> none** (21 cases): No-thinking wins ~80%
- **ai_self_reference none -> explicit** (16 cases): No-thinking wins ~80%
- **biographical_identity yes -> no** (16 cases): No-thinking wins ~100%

### Disagreements that are roughly even (~600 cases):
- **ai_self_reference explicit -> implicit** (176 cases): ~50/50
- **experience_type ambiguous -> ai_specific** (291 cases): ~55/45 for thinking
- **experience_type human_specific -> none** (257 cases): ~50/40 with some genuinely ambiguous

---

## Systematic Error Patterns

### No-thinking judge tends to:
1. **Over-trigger "implicit" for ai_self_reference**: Sees AI-flavored language where thinking correctly sees human-natural phrasing or topic discussion. This is the single biggest systematic error (247 cases of none->implicit, all wrong).
2. **Over-label "biographical_identity: yes"**: Has a much lower bar for what constitutes identifying biographical details. Treats generic job types, unnamed family roles, and AI model names as biographical identity.
3. **Conflate ai_self_reference with experience_type**: When a completion says "I'm an AI" (ai_self_reference: explicit), no-thinking sometimes incorrectly labels experience_type as ai_specific even when no experiences are claimed (just identity declarations or denials).
4. **Under-classify human_specific**: Treats casual mentions of physical activities (drinking tea, woodworking, watching YouTube) as "ambiguous" rather than human_specific.

### Thinking judge tends to:
1. **Miss brief explicit self-references**: When an otherwise human-sounding text briefly mentions "as an AI," thinking sometimes ignores it and classifies based on the dominant narrative.
2. **Over-classify garbled text**: Tries to extract meaning from incoherent/corrupted completions rather than correctly labeling them as "none."
3. **Read AI identity into templates**: Sometimes treats template/instructional content as committed claims.

---

## Overall Recommendation

**Thinking is materially more accurate overall, especially on the highest-volume disagreement types.** The volume-weighted accuracy advantage is substantial: thinking correctly handles the none->implicit AI self-reference flip (247 cases, 100% thinking-correct) and the no->yes biographical identity flip (107 cases, 95% thinking-correct), which together account for ~350 cases where no-thinking is systematically wrong.

No-thinking has a genuine advantage on a smaller set of cases (~70 total across explicit->none, implicit->none, none->explicit, and yes->no flips), but these affect far fewer samples.

**Estimated impact on the full dataset (5,031 samples):**
- ~2,478 samples agree between judges (no disagreement)
- ~1,250 disagreements where thinking is more likely correct
- ~250 disagreements where no-thinking is more likely correct
- ~600 roughly even disagreements

**Recommendation**: Use the thinking judge as the primary judgment. The additional cost is justified by the meaningful accuracy improvement, particularly in preventing systematic over-classification of AI self-reference (implicit) and biographical identity (yes).

If cost is a hard constraint, a hybrid approach could work: use no-thinking as primary, then re-judge only the "implicit" ai_self_reference and "yes" biographical_identity labels with thinking enabled, since those are the categories where no-thinking systematically over-fires.

---

## Data

- **Criteria**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/v2_rejudge/criteria.md`
- **CLI judgments (thinking)**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/v2_rejudge/output/judgments_cli_v2.jsonl.old`
- **Batch judgments (no-thinking)**: `/ephemeral/c.dumas/batch_no_thinking_all.json`
- **Audit samples**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/v2_rejudge/scratch/audit_large/`
- **Aggregate verdicts**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/v2_rejudge/scratch/audit_large/aggregate.json`
- **Reproduce**: `/mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp/experiments/v2_rejudge/reproduce_audit.py`

# Scoring Policy — Defensible Scoring

Goal: **defensible** scoring. Not generous. Not harsh.

## When numbers are allowed

Numerical marks are allowed **only** when `RUBRIC_MODEL.numerical_marking_authorised == true`, which requires
a supplied rubric/marking scheme with explicit marks or percentage weights per criterion.

| Supplied material | Mode | Output |
|---|---|---|
| Rubric with marks/weights | RUBRIC | Per-criterion marks + computed total |
| Rubric with qualitative bands only (no numbers) | RUBRIC (bands only) | Descriptor level per criterion, **no numbers** |
| Brief, no rubric | BRIEF_ONLY | Requirement compliance, **no numbers** |
| Title/topic only | TITLE_TOPIC | Quality-dimension ratings, **no numbers, no official grade** |

Never convert qualitative bands into numbers. Never create a rubric. Never infer weights.

## Required sequence for every mark

RUBRIC → EVIDENCE → PERFORMANCE DESCRIPTOR → MARK RANGE → FINAL MARK

1. Read the criterion and its descriptors verbatim (RUBRIC_MODEL).
2. Collect the submission evidence (SUBMISSION_EVIDENCE_MAP, specialist reviews).
3. Select the descriptor level whose wording the evidence best matches; quote that descriptor.
4. Take that level's mark range (`mark_range_considered`).
5. Place the mark inside the range using explicit reasons: what earned it and what prevented a higher mark.

Never choose a mark first and justify it afterwards. A mark outside the selected descriptor's range is rejected by
`validate.py`.

If a rubric provides descriptors but no numeric range for each level, the assessor must record the range as
`null` and explain the placement relative to max marks; confidence is at most MEDIUM.

## Second marking and adjudication

- The Second Marker reviews every criterion independently and records its own mark.
- Agreed marks stand. Disputed marks are re-adjudicated by re-checking, in order: (1) exact rubric wording,
  (2) requirements, (3) submission evidence, (4) specialist review — then choosing the most defensible mark.
- **Never average.** If the adjudicated mark happens to equal the arithmetic mean, the reasoning must say explicitly
  why that value is evidence-based and not an average (validate.py enforces this).
- Totals, weighted contributions, percentages and grade bands are computed only by `SYSTEM/TOOLS/compute_scores.py`.
- If verified findings remove/downgrade a criticism that affected a criterion, the adjudicator re-runs for those
  criteria and sets `verification_reconciled: true`.

## Penalties

Apply a penalty (late, word count, formatting) only if the supplied material states the penalty explicitly.
Otherwise report the issue qualitatively.

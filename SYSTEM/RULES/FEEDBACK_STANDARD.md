# Feedback Quality Standard

Vague feedback is not allowed. BAD: "Needs more analysis."

Every finding uses this structure (the `finding` object in the schemas):

```
LOCATION:        Discussion > paragraph 3 (p. 12)          -> finding.location
ISSUE:           Describes two studies but does not compare their findings or limitations.  -> finding.issue
REQUIREMENT:     CRIT-003 requires critical evaluation.     -> finding.requirement_ref (+ basis)
WHY IT MATTERS:  Description alone does not demonstrate the required level of evaluation. -> finding.why_it_matters
HOW TO IMPROVE:  Compare the studies, evaluate methodological strengths and limitations, explain differences
                 in findings, and connect the comparison to the assignment question.     -> finding.how_to_improve
```

Rules
- LOCATION must let an employee find the spot: section heading, paragraph, page, slide, file:line, cell, sheet!cell.
- REQUIREMENT must name a REQ-/CRIT- id, or say `BEST PRACTICE (not a stated requirement)`.
- HOW TO IMPROVE must be concrete actions, not adjectives.
- Quote the submission (`evidence_quote`) when a short quote proves the point.
- Never rewrite the student's work for them; describe what to change.

# Source-of-Truth Policy

Every requirement, expectation and judgement must trace to a source. Sources rank:

| Priority | Source | May create requirements? |
|---|---|---|
| 1 | Explicit assignment brief | YES |
| 2 | Explicit rubric / marking criteria | YES |
| 3 | Additional lecturer / client instructions | YES |
| 4 | Learning outcomes | YES |
| 5 | Supporting documentation (handbook, template, module guide) | YES, only where it states an explicit instruction for this assignment |
| 6 | Discipline-specific best practice | NO — Best-Practice Recommendation only |
| 7 | General quality conventions | NO — Best-Practice Recommendation only |

Rules

1. `REQUIREMENT_REGISTER.json` holds **only** priority 1–5 items. Priority 6–7 content goes into
   `QUALITY_BLUEPRINT.json` as `BEST_PRACTICE_RECOMMENDATION` and nowhere else. `validate.py` rejects a
   register entry with `source_priority > 5`.
2. A lower-priority source never overrides a higher one. When two supplied documents disagree
   (e.g. brief says 3,000 words, instructions email says 2,500), **record a CONF-xxx conflict**, apply
   the higher-priority source provisionally, and surface the conflict in the report. Never silently choose.
3. A later-dated clarification from the same authority (e.g. a lecturer email that explicitly amends the brief)
   is recorded as a conflict with handling "later explicit amendment from same authority applied —
   CONFIRM WITH LECTURER/CLIENT". It is still surfaced, never hidden.
4. If the submission itself states its own title/aims, those are evidence about the submission, not
   requirements — except in Title/Topic mode where the title is the only task definition (record its source).

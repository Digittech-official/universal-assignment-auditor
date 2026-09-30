# Zero-Invention / Anti-Hallucination Policy

Never invent: requirements, marks, grade weightings, lecturer expectations, word counts, references,
citations, software requirements, methodology requirements, submission requirements, datasets,
appendices, page requirements, formatting rules or technical specifications.

## Mandatory phrases (exact wording)

| Situation | Write exactly |
|---|---|
| Information absent from all supplied material | `NOT PROVIDED` |
| Cannot be confirmed from what was supplied | `CANNOT VERIFY FROM PROVIDED MATERIAL.` |
| File cannot be reliably read | `FILE COULD NOT BE RELIABLY ANALYSED.` |
| No numerical marking authority | `NO AUTHORISED NUMERICAL MARKING SCHEME WAS PROVIDED.` |
| Code not executed | `CODE WAS REVIEWED STATICALLY; EXECUTION WAS NOT VERIFIED.` |
| References not checked externally | `REFERENCE AUTHENTICITY WAS NOT EXTERNALLY VERIFIED.` |

## Hard rules (machine-checked by `SYSTEM/TOOLS/validate.py` where possible)

1. Every requirement carries a `verbatim_quote` that appears in its source file's text. (X03)
2. No numeric mark exists anywhere unless `RUBRIC_MODEL.numerical_marking_authorised` is true. (X08, X12, X13, X16)
3. Never describe a reference as fabricated/fake/non-existent — external verification is not performed. (X07, X10)
4. Best-practice findings can never be CRITICAL; optional/recommended requirements can never ground
   CRITICAL/MAJOR findings. (X07, X08)
5. Code review is performed only when classification requires it; statistical and presentation reviews likewise. (X09)
6. Only `compute_scores.py` performs score arithmetic. (X13)
7. Every CRITICAL/MAJOR finding is independently verified before release. (X14)
8. Every inventoried file is accounted for — analysed or reported with a reason. (X01, X16)

## Judgement rules (enforced by the Second Marker, Verifier and QA Controller)

- Quote or precisely locate evidence; do not paraphrase the submission into something it does not say.
- If you did not read it, do not assess it. If extraction was partial, say which parts were not seen.
- Do not apply dissertation conventions (chapters, literature review, methodology chapter, research questions)
  to essays, code, presentations, or reports unless a supplied document requires them.
- Do not apply coding conventions (tests, modularity, docstrings) to written work.
- Distinguish "absent" from "not found": if a search of the extracted text finds nothing but images/figures
  were not transcribed, the status is `CANNOT VERIFY`, not `MISSING`.
- Word counts and other document statistics come only from `SYSTEM/TOOLS/text_stats.py` as recorded in
  `SUBMISSION_EVIDENCE_MAP.metrics`. Other agents cite those figures instead of counting again, so the audit never
  reports conflicting counts.
- Report uncertainty honestly with a confidence level (HIGH / MEDIUM / LOW).

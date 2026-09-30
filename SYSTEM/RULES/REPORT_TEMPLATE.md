# Final Report Template — `FINAL_QUALITY_AUDIT.md`

The Report Composer writes the draft to `OUTPUT/_work/FINAL_QUALITY_AUDIT.draft.md`. Only
`SYSTEM/TOOLS/release_report.py` publishes it (after QA PASS) to `OUTPUT/FINAL_QUALITY_AUDIT.md` + `.html`.

Headings are fixed and machine-checked: `## <n>. <Title>` for n = 1..26. A section that does not apply
must still appear with the line `NOT APPLICABLE — <reason>`. Adapt the content (not the headings) to the task type.

```
# Final Quality Audit — <assignment title or "Untitled submission">

## 1. Assignment Identification      title/topic (+ source), submission file(s), run id, date, auditor version
## 2. Task Type                      task type, secondary types, discipline, confidence, evidence
## 3. Analysis Mode                  RUBRIC / BRIEF_ONLY / TITLE_TOPIC + why; source-of-truth order; conflicts (CONF-xxx)
## 4. Files Analysed                 table: FILE-id | path | role | how read
## 5. Files Not Analysed and Reasons table: FILE-id | path | reason (exact phrase FILE COULD NOT BE RELIABLY ANALYSED. where applicable) — or "None"
## 6. Executive Quality Summary      5–10 lines: overall standing, top 3 risks, top 3 strengths
## 7. Numerical Mark                 authorised: total / available, percentage, grade band (from compute_scores.py) + confidence
                                     not authorised: exactly "NO AUTHORISED NUMERICAL MARKING SCHEME WAS PROVIDED." and no numbers
## 8. Marking Breakdown              authorised: table CRIT-id | criterion | max | primary | second | final | descriptor | what earned | what prevented higher
                                     bands-only rubric: descriptor level per criterion, no numbers
                                     otherwise: NOT APPLICABLE — reason
## 9. Requirement Compliance Matrix  table: REQ-id | requirement | obligation | status | evidence location | action  (EVERY REQ)
## 10. Critical Issues               verified CRITICAL findings, FEEDBACK_STANDARD format, with finding id  — or "None identified"
## 11. Major Issues                  verified MAJOR findings, same format
## 12. Moderate Improvements
## 13. Minor Improvements
## 14. Passed Requirements           REQ ids with PASS and the evidence
## 15. Section-by-Section Review     per section / slide group / module / notebook part
## 16. Content and Analysis Review
## 17. Structure and Coherence Review  logical chain table from COHERENCE_AUDIT
## 18. Evidence and Referencing Review includes "REFERENCE AUTHENTICITY WAS NOT EXTERNALLY VERIFIED." when referencing applies
## 19. Technical Review              (task-appropriate; or NOT APPLICABLE)
## 20. Coding Review                 includes "CODE WAS REVIEWED STATICALLY; EXECUTION WAS NOT VERIFIED." (or NOT APPLICABLE)
## 21. Data and Statistical Review   (or NOT APPLICABLE)
## 22. Presentation Review           (or NOT APPLICABLE)
## 23. Revision Priority Plan        ordered steps: severity first, quick wins first within severity, with REQ/CRIT refs
## 24. Quality Improvement Map       table: area | current state | target state | action | linked REQ/CRIT/BP
## 25. Final Pre-Submission Checklist  "- [ ]" items derived ONLY from REQ ids (mandatory) + clearly labelled best-practice items
## 26. Audit Limitations             unanalysed files, partial extraction, static-only code review, unverified references,
                                     AI limitations, second-marker disagreements, confidence
```

Label every best-practice suggestion as `BEST PRACTICE (not a stated requirement)`.
In TITLE_TOPIC mode, sections 9 and 24 separate **KNOWN REQUIREMENTS** from **BEST-PRACTICE EXPECTATIONS**.

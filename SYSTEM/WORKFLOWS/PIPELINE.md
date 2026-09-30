# /check-assignment Pipeline

Implementation: `.claude/commands/check-assignment.md` (orchestrator prompt). This document explains the design.

```
INPUT/ ──► [P] prepare_run.py ──► [0] Input Integrity ──► mode?
                                                   │  CANNOT_PROCEED ──► [R] release_report.py ──► AUDIT_BLOCKED.md
                                                   ▼
        Wave A:  [1] Task Classifier  |  [2] Requirement Extraction  |  [3] Rubric Interpreter      (parallel)
                                          │
        Wave B:  [4] Quality Blueprint  |  [5] Evidence Mapper                                  (parallel)
                                          │
        Wave C:  [7] Specialist  |  [8] Reference & Evidence  |  [9] Coherence  |  [10] Second Marker — BLIND phase
                                          │                                                      (parallel)
                                   [6] Primary Assessor
                                          │
                                   [10] Second Marker — CHALLENGE phase (uses its saved blind judgements)
                                          │
                     authorised? ──yes──► [11] Score Adjudicator ─► compute_scores.py
                          │ no ─────────► compute_scores.py --not-applicable
                                          │
                                   [12] Critical Findings Verifier ──(marks affected)──► [11] re-run
                                          │
                                   build_rtm.py ─► [14] Report Composer (draft)
                                          │
                                   [13] Final QA Controller ──FAIL──► re-run named stages (≤ 2 rounds)
                                          │ PASS
                                   [R] release_report.py ──► FINAL_QUALITY_AUDIT.md + .html
```

## Speed design (v1.1.0)
- Independent stages run in parallel waves (A, B, C above).
- The second marker's blind re-marking runs in Wave C, before the primary assessment even exists — this is faster
  AND strengthens independence. Only the short challenge/compare phase waits for the primary assessor.
- Models: agents doing mechanical or descriptive work use the faster model (`model: sonnet` — agents 0, 1, 4, 5, 8, 14);
  all judgement agents (2, 3, 6, 7, 9, 10, 11, 12, 13) inherit the session's strongest model. Change a single agent's
  `model:` line in `.claude/agents/` to trade speed for depth.

## Why this order
- **Specialist, evidence and coherence reviews run before the primary assessment** so the primary assessor can
  use their technical depth, while the **second marker** still judges blind first.
- **Score adjudication precedes verification** (as specified), and verification feeds back: if a serious finding that
  influenced a mark is removed or downgraded, the adjudicator re-runs for those criteria (`verification_reconciled`).
- **Composer before QA**: QA inspects the exact text employees will read.
- **Release is deterministic**: only `release_report.py` writes the final report, and only when
  `QA_STATUS.qa_status == PASS` **and** `validate.py --final` has zero errors. Any stale final report is deleted first.

## Mode logic (Agent 0)
1. No readable submission → CANNOT_PROCEED
2. Genuine rubric (criteria + marks/weights/descriptors) → RUBRIC (numerical only if marks/weights exist)
3. Meaningful brief → BRIEF_ONLY
4. Title/topic only → TITLE_TOPIC
5. Nothing defines the task → CANNOT_PROCEED

## Deterministic guarantees (validate.py rule families)
| Rule | Guarantee |
|---|---|
| SCHEMA | Every artefact matches its schema |
| X01 | Every inventoried file accounted for; mode consistent with inputs; unreadable files never "analysed" |
| X02 | Classification consistent with rubric authority and review flags |
| X03 | Requirements sequential, sourced, **verbatim quotes found in source text**, no best practice in the register |
| X04 | Rubric only in RUBRIC mode; authority rules; arithmetic consistency; descriptor ranges sane |
| X05 | Blueprint categories correctly sourced (no optional-as-mandatory) |
| X06 | Every REQ/CRIT mapped to evidence |
| X07 | Finding IDs, bases and references valid; best practice never CRITICAL; no fabrication claims; actionable fields |
| X08 | Every REQ/CRIT assessed; no marks without authority; marks inside descriptor ranges; optional never penalised |
| X09 | Only required specialist reviews run; no code execution; static-review statement |
| X10 | Reference-authenticity statement; no external-verification claims |
| X11 | Coherence chain evaluated |
| X12 | Second marker covers every criterion and quotes the primary correctly |
| X13 | Scores only if authorised; recomputed totals match; no silent averaging; marks inside ranges; re-adjudication |
| X14 | Every CRITICAL/MAJOR finding verified; outcome logic consistent |
| X15 | QA status internally consistent |
| X16 | Report has 26 sections, required phrases, every REQ/CRIT/file, no marks without authority, no removed findings in serious sections, no machine paths |

# Agent Responsibility Map

The agent definitions are native Claude Code subagents stored in `.claude/agents/` (the location Claude Code
auto-discovers). This file is the human-readable index. Each agent has one responsibility and writes one
schema-validated artefact to `OUTPUT/audit_trail/` (the Report Composer writes the draft report).

| # | Agent (file in `.claude/agents/`) | Responsibility | Output | Schema |
|---|---|---|---|---|
| P | *(tool)* `SYSTEM/TOOLS/prepare_run.py` | Inventory + text extraction + advisory mode | `_work/INPUT_INVENTORY.json` | — |
| 0 | `aua-00-input-integrity-checker` | Files, roles, duplicates, unreadable/competing files, **analysis mode** | `INPUT_MANIFEST.json` | `input_manifest` |
| 1 | `aua-01-task-classifier` | Task type, discipline, specialist reviews, marking authority | `TASK_CLASSIFICATION.json` | `task_classification` |
| 2 | `aua-02-requirement-extraction-specialist` | Every explicit requirement (REQ-xxx) with verbatim quote; conflicts; NOT PROVIDED | `REQUIREMENT_REGISTER.json`, `REQUIREMENT_TRACEABILITY_MATRIX.md` | `requirement_register` |
| 3 | `aua-03-rubric-interpreter` | Faithful rubric model (CRIT-xxx), authority, arithmetic check | `RUBRIC_MODEL.json` | `rubric_model` |
| 4 | `aua-04-quality-blueprint-architect` | Mandatory vs rubric-derived vs best-practice expectations | `QUALITY_BLUEPRINT.json` | `quality_blueprint` |
| 5 | `aua-05-submission-evidence-mapper` | Where the evidence is (LOC-xxx) for every REQ/CRIT — no scoring | `SUBMISSION_EVIDENCE_MAP.json` | `submission_evidence_map` |
| 6 | `aua-06-primary-quality-assessor` | Status of every REQ; criterion marks (if authorised); findings F6 | `PRIMARY_ASSESSMENT.json` | `primary_assessment` |
| 7 | `aua-07-specialist-technical-reviewer` | Code (static only) / data & statistics / presentation / written review; F7 | `SPECIALIST_REVIEW.json` | `specialist_review` |
| 8 | `aua-08-reference-evidence-auditor` | Citations ↔ references, style, source requirements, unsupported claims; F8 | `EVIDENCE_AUDIT.json` | `evidence_audit` |
| 9 | `aua-09-coherence-synchronisation-auditor` | Task-appropriate logical chain, contradictions, gaps; F9 | `COHERENCE_AUDIT.json` | `coherence_audit` |
| 10 | `aua-10-independent-second-marker` | Blind re-marking then challenge of the primary assessment; F10 | `SECOND_MARKER_REVIEW.json` | `second_marker_review` |
| 11 | `aua-11-score-adjudicator` | Resolves disputes from evidence (never averages); totals via `compute_scores.py` | `FINAL_SCORE_MODEL.json` | `final_score_model` |
| 12 | `aua-12-critical-findings-verifier` | Re-checks every CRITICAL/MAJOR finding; confirm/correct/downgrade/remove | `VERIFIED_FINDINGS.json` | `verified_findings` |
| 14 | `aua-14-report-composer` | Employee-facing report (26 fixed sections) from the trail only | `_work/FINAL_QUALITY_AUDIT.draft.md` | template |
| 13 | `aua-13-final-qa-controller` | Validator + QA-01…QA-14; PASS/FAIL; names stages to re-run | `QA_STATUS.json` | `qa_status` |
| R | *(tool)* `SYSTEM/TOOLS/release_report.py` | Publishes the report only on QA PASS + validator pass | `FINAL_QUALITY_AUDIT.md/.html` or `AUDIT_BLOCKED.md` | — |

Finding ID prefixes: `F6-`, `F7-`, `F8-`, `F9-`, `F10-` (source agent is always identifiable).

Why the Report Composer (14) runs before the QA Controller (13): the QA Controller must inspect the exact text that
employees will read, so it is the last agent before the deterministic release gate.

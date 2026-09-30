# Changelog

All notable changes to the Universal Assignment Auditor. Format: [Keep a Changelog](https://keepachangelog.com/),
versioning: [SemVer](https://semver.org/) — MAJOR for workflow/report-format changes that affect employees,
MINOR for new capabilities, PATCH for fixes.

## [1.0.0] — 2026-09-30

### Added
- One-command employee workflow `/check-assignment` (`.claude/commands/check-assignment.md`).
- 15 native Claude Code subagents (`.claude/agents/aua-00` … `aua-14`): Input Integrity Checker, Task Classifier,
  Requirement Extraction Specialist, Rubric Interpreter, Quality Blueprint Architect, Submission Evidence Mapper,
  Primary Quality Assessor, Specialist Technical Reviewer, Reference & Evidence Auditor, Coherence & Synchronisation
  Auditor, Independent Second Marker, Score Adjudicator, Critical Findings Verifier, Final QA Controller, Report Composer.
- Three automatically detected analysis modes: Rubric, Brief-Only, Title/Topic (plus safe CANNOT_PROCEED).
- Deterministic stdlib-only tooling: file inventory and extraction (DOCX, PPTX, XLSX, CSV, IPYNB, TXT/MD, code,
  safe ZIP unpacking; PDFs via pdftotext/pypdf or Claude's reader), schema + cross-document validator (16 rule
  families), score calculator, traceability-matrix builder, release gate, Markdown→HTML renderer, privacy check,
  local-data cleaner, text statistics.
- JSON schemas for all 14 audit-trail artefacts and the QA checklist.
- Policies: source of truth, zero invention, scoring, severity, feedback standard, code execution, privacy,
  task-type profiles, report template.
- PreToolUse safety hook blocking execution of submitted code and staging of confidential data.
- Synthetic fixtures A–K, 61 unit tests, end-to-end acceptance runner and evaluator (all 11 cases passing — see
  `SYSTEM/TESTS/ACCEPTANCE_RESULTS.md`); CI workflow.

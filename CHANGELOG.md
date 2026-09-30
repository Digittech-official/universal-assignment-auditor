# Changelog

All notable changes to the Universal Assignment Auditor. Format: [Keep a Changelog](https://keepachangelog.com/),
versioning: [SemVer](https://semver.org/) — MAJOR for workflow/report-format changes that affect employees,
MINOR for new capabilities, PATCH for fixes.

## [1.1.0] — 2026-09-30

### Changed
- Faster pipeline without removing any quality stage: parallel Waves A (agents 1+2+3), B (4+5) and C (7+8+9 + second
  marker's blind phase); the second marker is split into BLIND and CHALLENGE phases.
- Mechanical/descriptive agents (0, 1, 4, 5, 8, 14) use the faster model; judgement agents keep the strongest model.

### Added
- Company ZIP convention: task-material packs (brief + instructions + rubric) as one ZIP in 01/03; multi-file
  submissions as one ZIP in 04 (always one submission, never competing versions).
- Every task in a brief is registered (Task 1/2/3, parts, sub-questions); "answer ONE of" choice questions never mark
  unchosen options as missing.
- `text_stats.py --all`: the orchestrator computes all word/citation counts once (`OUTPUT/_work/TEXT_STATS.json`);
  agents read them instead of counting, and the validator flags a missing word count right after Stage 5.
- Unit tests for ZIP packs and the early word-count check (64 unit tests).
- Agents use Claude's Read/Write/Edit tools instead of shell one-liners (fewer permission prompts, faster runs).
- Fabrication wording ("fabricated", "fake", "non-existent") is banned everywhere, even negated (validator X07/X16).

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

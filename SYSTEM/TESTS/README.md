# Tests

All fixtures are **synthetic** (fictional people, institutions and data). Never add real assignments here.

## 1. Unit tests — fast, deterministic, no model calls
```bash
python3 -m unittest discover -s SYSTEM/TESTS/unit -v
```
- `test_validator.py` — a valid trail passes; ~35 targeted defects are each caught by the right rule (invented marks,
  wrong arithmetic, silent averaging, marks outside descriptor ranges, unverified serious findings, optional content
  penalised, best practice as CRITICAL, untraceable requirement quotes, coding review on essays, code execution,
  fabrication claims, QA inconsistencies, report omissions, marks shown without authority, …).
- `test_tools.py` — extractors (DOCX/PPTX/XLSX/IPYNB, corrupt/legacy/empty/binary, zip-slip, zip-bomb), advisory mode
  for every fixture, score arithmetic, release gate (release / QA-block / validator-block / missing-input-block),
  safety hook, privacy check, schema freshness, agent/command wiring, no machine paths.

## 2. End-to-end acceptance — runs the real `/check-assignment` pipeline (uses model credits)
```bash
python3 SYSTEM/TESTS/run_e2e.py                      # all cases, 2 in parallel
python3 SYSTEM/TESTS/run_e2e.py A_dissertation_rubric C_coding_spec_rubric --parallel 2
```
Each case runs in an isolated copy under `SYSTEM/TESTS/runs/` (git-ignored) and is scored by `evaluate_run.py`
against the case's `expected.json`. Summary: `SYSTEM/TESTS/runs/SUMMARY.md`.

## 3. Fixtures

| Case | Scenario | Key expectations |
|---|---|---|
| A_dissertation_rubric | Dissertation + brief + marks rubric | RUBRIC mode, marks /100 reconcile, missing ethics & too few sources flagged |
| B_essay_brief_only | Essay + brief, no rubric | BRIEF_ONLY, no marks, source count & counter-arguments flagged, no coding/dissertation rules |
| C_coding_spec_rubric | Python project ZIP + spec + weighted rubric | Weighted marks, static-only code review, bugs/tests/README flagged, no essay rules |
| D_technical_report_pdf | Technical report as PDF | PDF read path, missing risks section & single-option analysis flagged |
| E_presentation_bands_rubric | PPTX + qualitative rubric | RUBRIC mode **without** numbers, timeline & speaker notes flagged |
| F_data_analysis | Notebook (code, stored outputs, interpretation) + XLSX data | Statistics review, hypotheses/assumptions/labels flagged, interpretation vs output mismatch |
| G_title_only | Title + essay | TITLE_TOPIC, KNOWN vs BEST-PRACTICE separation, no grade |
| H_missing_submission | Brief + rubric, no submission | CANNOT_PROCEED, AUDIT_BLOCKED.md, no report |
| I_contradictory_instructions | Brief vs later email (word limit, style) | Conflict CONF-001 recorded and surfaced |
| J_unreadable_unsupported | Corrupt DOCX + legacy .doc beside a valid essay | Files reported with FILE COULD NOT BE RELIABLY ANALYSED., audit proceeds |
| K_anti_hallucination_optional | Optional appendix/diagrams; no word count/style | No invented word limit/style, optional items not penalised, obscure reference not called fabricated |

Sources for binary fixtures are in `fixture_sources/` (Markdown/CSV); rebuild with
`python3 SYSTEM/TESTS/build_fixtures.py`.

Note: the project settings deny Claude edits to any path matching `INPUT/**` — this deliberately also covers the
fixtures' `INPUT/` folders. Maintainers change fixtures by editing `fixture_sources/` and rebuilding, or by editing the
plain-text fixture files in their own editor.

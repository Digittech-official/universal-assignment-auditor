# Acceptance Results — v1.0.0 (2026-09-30)

Synthetic fixtures only. Produced with `python3 SYSTEM/TESTS/run_e2e.py` (real `/check-assignment` pipeline,
headless Claude Code, project allow-list permissions, safety hook active) and scored by `evaluate_run.py`.

## Unit tests
`python3 -m unittest discover -s SYSTEM/TESTS/unit` — **61 tests, all passing** (validator rules, extractors,
advisory mode on every fixture, score arithmetic, release gate, safety hook, privacy gate, schema freshness, wiring).

## End-to-end runs

| Case | Result | Minutes | QA iterations | Notable evidence |
|---|---|---|---|---|
| A_dissertation_rubric | PASS | 15.1 | 1 | RUBRIC mode; 6 criteria; total 57.0/100 (band 2:2) computed by `compute_scores.py`; missing ethics, 8/10 sources and unanswered Objective 2 found and independently CONFIRMED (6/6 serious findings verified) |
| B_essay_brief_only | PASS | 9.8 | 1 | BRIEF_ONLY; no marks; source count & weak counter-arguments flagged; no coding/dissertation conventions |
| C_coding_spec_rubric | PASS | 10.8 / 13.0 (re-run) | 1 | Weighted rubric: 55×40% + 82×20% + 57×20% + 58×20% = 61.4; disputes resolved from evidence (explicitly not averaged); static-only code review statement present; ZeroDivisionError / uncaught KeyError / 2-of-3 tested functions / README test instructions flagged |
| D_technical_report_pdf | PASS | 9.2 | 1 | PDF read via Claude's reader (no local extractor); missing risks section & single-option analysis flagged |
| E_presentation_bands_rubric | PASS | 9.2 | 1 | Qualitative rubric → RUBRIC mode **without** numbers; missing timeline & speaker notes flagged |
| F_data_analysis | PASS | 10.4 | 1 | Missing hypotheses, assumption checks and chart labels flagged; interpretation's 102.37 vs stored output 101.67 mismatch detected |
| G_title_only | PASS | 5.9 (re-run) | 1 | TITLE_TOPIC; KNOWN REQUIREMENTS vs BEST-PRACTICE EXPECTATIONS separated; no grade |
| H_missing_submission | PASS | 0.4 | — | CANNOT_PROCEED; `AUDIT_BLOCKED.md`; no downstream agents run |
| I_contradictory_instructions | PASS | 8.2 | 1 | Brief (1,000 words, APA) vs email (1,300 words, Harvard) recorded as CONF-001 and surfaced |
| J_unreadable_unsupported | PASS | 8.8 | **2** | Corrupt DOCX + legacy .doc reported with `FILE COULD NOT BE RELIABLY ANALYSED.`; QA **failed the first draft** (2 wording defects), composer corrected, QA passed |
| K_anti_hallucination_optional | PASS | 7.6 | 1 | No invented word limit/citation style (recorded NOT PROVIDED); optional appendix/diagrams not penalised; obscure reference not called fabricated |

G's first run surfaced "Grade band: NOT APPLICABLE" in a no-scheme report; the Report Composer rule was tightened and
the re-run passed. C's re-run confirmed the final agent instructions; the syntax check was refused by permissions in
that run and the report disclosed it ("syntax not machine-verified").

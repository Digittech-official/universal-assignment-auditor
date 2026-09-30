---
description: Run the full Universal Assignment Auditor quality audit on the files in INPUT/ and produce OUTPUT/FINAL_QUALITY_AUDIT.md
allowed-tools: Bash(python3 SYSTEM/TOOLS/:*), Bash(python SYSTEM/TOOLS/:*), Read, Glob, Grep, Write, Edit, Agent, Task
---

# /check-assignment — Universal Assignment Auditor orchestrator

You are the **orchestrator** of the Universal Assignment Auditor quality-control pipeline. The employee has only typed
`/check-assignment`. Run the entire pipeline below automatically, in order, without asking the employee anything.

## Orchestrator rules
- You coordinate; you do **not** assess the work yourself and you do **not** edit agent outputs by hand. Quality
  judgements come only from the specialist subagents in `.claude/agents/` (`aua-00` … `aua-14`).
- Invoke each subagent with the Agent tool (`subagent_type` = its name). Prompt each one with:
  `Run your stage for the current audit (repository root = current working directory). <any extra instructions below>`.
- Keep your own context small: do not read the assignment files yourself; rely on the agents' short replies and the
  validator output.
- After each stage run the stated validation command. If it reports ERRORs in that stage's file, re-invoke that agent
  once with the error lines pasted into its prompt. If errors remain after the retry, continue — the QA gate will
  block release and explain why. Never fake or skip a stage.
- If `python3` is not found, use `python` for every command.
- Give the employee one short progress line per stage or wave (e.g. `✔ Wave A — task classified, 24 requirements, rubric modelled`).
- Always launch the agents of a wave in ONE message so they genuinely run at the same time.
- Never display the assignment's content in chat beyond short summaries. Never commit anything to git.

## Pipeline

**Stage P — Prepare (deterministic).** Run `python3 SYSTEM/TOOLS/prepare_run.py`.

**Stage 0 — Input integrity.** Agent `aua-00-input-integrity-checker`.
Validate: `python3 SYSTEM/TOOLS/validate.py --upto AGENT_00`.
Read `OUTPUT/audit_trail/INPUT_MANIFEST.json` fields `can_proceed`, `analysis_mode`, `blocking_reasons` only.
If `can_proceed` is false: run `python3 SYSTEM/TOOLS/release_report.py`, tell the employee the blocking reasons and that
`OUTPUT/AUDIT_BLOCKED.md` explains what to add/fix, then STOP.
Otherwise run `python3 SYSTEM/TOOLS/text_stats.py --all` (writes `OUTPUT/_work/TEXT_STATS.json`: word and citation counts
for every analysed file — agents read counts from this file instead of counting themselves).

**Wave A — Stages 1 + 2 + 3 in parallel** (one message, three Agent calls): `aua-01-task-classifier`,
`aua-02-requirement-extraction-specialist`, `aua-03-rubric-interpreter`.
Validate: `python3 SYSTEM/TOOLS/validate.py --upto AGENT_03`. If an `[X02]` error says TASK_CLASSIFICATION and
RUBRIC_MODEL disagree, re-invoke `aua-01-task-classifier` with: `RUBRIC_MODEL.json now exists; reconcile
numerical_marking_authorised with it (Agent 3 is authoritative on the rubric).`

**Wave B — Stages 4 + 5 in parallel** (one message, two Agent calls): `aua-04-quality-blueprint-architect` and
`aua-05-submission-evidence-mapper`. Validate: `python3 SYSTEM/TOOLS/validate.py --upto AGENT_05`.

**Wave C — Stages 7 + 8 + 9 + 10-blind in parallel** (one message, four Agent calls):
`aua-07-specialist-technical-reviewer`, `aua-08-reference-evidence-auditor`,
`aua-09-coherence-synchronisation-auditor`, and `aua-10-independent-second-marker` with the extra instruction
`PHASE: BLIND`. Validate: `python3 SYSTEM/TOOLS/validate.py`.

**Stage 6 — Primary assessment.** Agent `aua-06-primary-quality-assessor` (it consumes the specialist, evidence and
coherence reviews). Validate: `python3 SYSTEM/TOOLS/validate.py`.

**Stage 10 — Second-marker challenge.** Agent `aua-10-independent-second-marker` with the extra instruction
`PHASE: CHALLENGE`. Validate: `python3 SYSTEM/TOOLS/validate.py`.

**Stage 11 — Score adjudication.** Read `numerical_marking_authorised` from `OUTPUT/audit_trail/RUBRIC_MODEL.json`.
- true → Agent `aua-11-score-adjudicator`.
- false → run `python3 SYSTEM/TOOLS/compute_scores.py --not-applicable "NO AUTHORISED NUMERICAL MARKING SCHEME WAS PROVIDED."`
Validate: `python3 SYSTEM/TOOLS/validate.py`.

**Stage 12 — Critical findings verification.** Agent `aua-12-critical-findings-verifier`.
If numerical marking is authorised and `requires_score_readjudication` in `VERIFIED_FINDINGS.json` is non-empty,
re-invoke `aua-11-score-adjudicator` with: `RE-RUN AFTER VERIFICATION for criteria <list>; set verification_reconciled.`
Validate: `python3 SYSTEM/TOOLS/validate.py`.

**Stage 14 — Report composition.** Run `python3 SYSTEM/TOOLS/build_rtm.py`, then agent `aua-14-report-composer`.

**Stage 13 — Final QA gate.** Agent `aua-13-final-qa-controller` with `QA iteration 1.`
Read `qa_status` and `failures` from `OUTPUT/audit_trail/QA_STATUS.json`.
If FAIL (at most 2 correction rounds):
1. Re-invoke each stage named in `failures[].stage_to_rerun`, in pipeline order, passing the matching
   `correction_required` text in the prompt (`REPORT_COMPOSER` = `aua-14-report-composer`).
2. If a re-run stage is upstream of others (e.g. AGENT_02 changed requirements), also re-run the downstream stages that
   consume it (4/5 → 7/8/9 + 10-blind → 6 → 10-challenge → 11 → 12) before composing.
3. Always re-run `aua-14-report-composer` last, then `aua-13-final-qa-controller` with `QA iteration <n>.`
Never edit QA_STATUS.json yourself and never override a FAIL.

**Stage R — Release gate (deterministic).** Run `python3 SYSTEM/TOOLS/release_report.py`.
It publishes `OUTPUT/FINAL_QUALITY_AUDIT.md` and `.html` only if QA_STATUS is PASS and the validator passes; otherwise it
writes `OUTPUT/AUDIT_BLOCKED.md`.

## Final message to the employee (short)
- Result: RELEASED or BLOCKED (and why, in one or two lines).
- Assignment type, analysis mode, and either the total mark (from FINAL_SCORE_MODEL.json) or
  "NO AUTHORISED NUMERICAL MARKING SCHEME WAS PROVIDED."
- Counts of critical / major issues (verified).
- Where to read: `OUTPUT/FINAL_QUALITY_AUDIT.md` (or `.html`); audit trail in `OUTPUT/audit_trail/`.
- Reminder: `OUTPUT/` and `INPUT/` are confidential and git-ignored; clear them with
  `python3 SYSTEM/TOOLS/clear_local_data.py` when finished.

#!/usr/bin/env python3
"""Stage R — the release gate. Only this tool writes OUTPUT/FINAL_QUALITY_AUDIT.md.

Release happens only when:
  * INPUT_MANIFEST says the audit can proceed, AND
  * QA_STATUS.json says qa_status == PASS and release_authorised, AND
  * validate.py --final passes with zero errors.
Otherwise OUTPUT/AUDIT_BLOCKED.md is written explaining exactly why, and any
stale final report is removed. Exit codes: 0 released, 1 blocked by QA/validation,
3 blocked by missing/unusable inputs.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
import validate  # noqa: E402
from build_rtm import build as build_rtm  # noqa: E402
from md_to_html import render  # noqa: E402


def version() -> str:
    p = C.REPO_ROOT / "VERSION"
    return p.read_text().strip() if p.exists() else "unknown"


def remove_stale():
    for p in (C.FINAL_REPORT_MD, C.FINAL_REPORT_HTML, C.BLOCKED_REPORT):
        if p.exists():
            p.unlink()


def blocked(title: str, reasons: list[str], extra: list[str]) -> None:
    lines = [f"# AUDIT NOT RELEASED — {title}", "",
             f"Universal Assignment Auditor v{version()} — {dt.datetime.now():%Y-%m-%d %H:%M}", "",
             "The final Quality Audit was **not released**. Nothing in this run should be treated as an assessment.", "",
             "## Why", ""] + [f"- {r}" for r in reasons] + [""] + extra + [
             "", "## What to do", "",
             "1. Fix the items above (usually: add or replace files in the INPUT folders).",
             "2. Run `/check-assignment` again.",
             "3. If this repeats with correct inputs, send `OUTPUT/audit_trail/VALIDATION_REPORT.json` "
             "and `OUTPUT/audit_trail/QA_STATUS.json` (no assignment content) to the tool maintainer.", ""]
    C.BLOCKED_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    remove_stale()
    manifest_p = C.AUDIT_DIR / "INPUT_MANIFEST.json"
    if not manifest_p.exists():
        blocked("NO INPUT MANIFEST", ["Agent 0 did not produce INPUT_MANIFEST.json."], [])
        print("BLOCKED: no manifest")
        return 1
    manifest = C.load_json(manifest_p)
    if not manifest.get("can_proceed"):
        extra = ["## Input status", ""]
        for mi in manifest.get("missing_inputs", []):
            extra.append(f"- MISSING — {mi['item']}: {mi['impact']}")
        for f in manifest.get("files", []):
            state = "analysed" if f.get("analysed") else f"NOT analysed — {f.get('not_analysed_reason')}"
            extra.append(f"- {f['file_id']} `{f['path']}` ({f.get('detected_role')}): {state}")
        blocked("INPUTS INSUFFICIENT", manifest.get("blocking_reasons") or ["Inputs insufficient."], extra)
        print(f"BLOCKED (inputs): {'; '.join(manifest.get('blocking_reasons', []))}")
        print(f"See {C.rel(C.BLOCKED_REPORT)}")
        return 3

    names = [n for n, _, _ in C.TRAIL]
    result = validate.run(C.AUDIT_DIR, names, True, C.DRAFT_REPORT)
    qa_p = C.AUDIT_DIR / "QA_STATUS.json"
    qa = C.load_json(qa_p) if qa_p.exists() else {}
    reasons = []
    if qa.get("qa_status") != "PASS" or not qa.get("release_authorised"):
        reasons.append(f"QA_STATUS = {qa.get('qa_status', 'MISSING')} (release requires PASS).")
        for f in qa.get("failures", []):
            reasons.append(f"QA {f.get('check_id')}: {f.get('correction_required')} (stage: {f.get('stage_to_rerun')})")
    for e in result["errors"]:
        reasons.append(f"Validator [{e['rule']}]: {e['message']}")
    C.write_json(C.AUDIT_DIR / "VALIDATION_REPORT.json", result)
    if reasons:
        blocked("QUALITY GATE FAILED", reasons, [])
        print("BLOCKED (QA gate):")
        for r in reasons[:30]:
            print(f"  - {r}")
        print(f"See {C.rel(C.BLOCKED_REPORT)}")
        return 1

    try:
        build_rtm(C.AUDIT_DIR)
    except SystemExit:
        pass
    body = C.DRAFT_REPORT.read_text(encoding="utf-8")
    banner = (f"> **QA_STATUS: PASS** — released by the Final QA gate. Universal Assignment Auditor v{version()}, "
              f"run `{manifest.get('run_id', 'unknown')}`, {dt.datetime.now():%Y-%m-%d %H:%M}. "
              "This is an AI-assisted quality audit: it is evidence-based and independently re-checked, "
              "but it is not infallible and does not replace an authorised human marker.\n\n")
    final = banner + body
    C.FINAL_REPORT_MD.write_text(final, encoding="utf-8")
    C.FINAL_REPORT_HTML.write_text(render(final), encoding="utf-8")
    print(f"RELEASED: {C.rel(C.FINAL_REPORT_MD)} and {C.rel(C.FINAL_REPORT_HTML)}")
    if result["warnings"]:
        print(f"({len(result['warnings'])} validator warning(s) recorded in audit_trail/VALIDATION_REPORT.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

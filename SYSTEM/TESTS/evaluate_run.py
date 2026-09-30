#!/usr/bin/env python3
"""Evaluates a completed /check-assignment run against a fixture's expected.json.

Usage: python3 SYSTEM/TESTS/evaluate_run.py <CASE> [--root PATH_TO_REPO_COPY] [--json OUT.json]
Exit code 0 when every expectation holds.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "SYSTEM" / "TOOLS"))
import validate  # noqa: E402


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def evaluate(case: str, root: Path) -> dict:
    exp = load(HERE / "fixtures" / case / "expected.json")
    out = root / "OUTPUT"
    trail = out / "audit_trail"
    d = {p.name: load(p) for p in trail.glob("*.json")} if trail.exists() else {}
    checks: list[dict] = []

    def check(cid: str, desc: str, ok: bool, detail: str = ""):
        checks.append({"id": cid, "check": desc, "passed": bool(ok), "detail": detail})

    m = d.get("INPUT_MANIFEST.json") or {}
    final_md = out / "FINAL_QUALITY_AUDIT.md"
    blocked_md = out / "AUDIT_BLOCKED.md"
    report = final_md.read_text(encoding="utf-8") if final_md.exists() else (
        blocked_md.read_text(encoding="utf-8") if blocked_md.exists() else "")

    check("E01", "analysis mode", m.get("analysis_mode") == exp["expected_mode"],
          f"got {m.get('analysis_mode')}, expected {exp['expected_mode']}")
    check("E02", "can_proceed", m.get("can_proceed") == exp["expected_can_proceed"], f"got {m.get('can_proceed')}")
    check("E03", "release outcome", final_md.exists() == exp["expect_release"] and blocked_md.exists() != exp["expect_release"],
          f"final={final_md.exists()} blocked={blocked_md.exists()}")
    if not exp["expected_can_proceed"]:
        check("E03b", "no downstream agent ran on insufficient input",
              not any(n in d for n in ("PRIMARY_ASSESSMENT.json", "FINAL_SCORE_MODEL.json")))
    t = d.get("TASK_CLASSIFICATION.json") or {}
    if exp["expected_task_types"]:
        check("E04", "task type", t.get("task_type") in exp["expected_task_types"],
              f"got {t.get('task_type')}, allowed {exp['expected_task_types']}")
    r = d.get("RUBRIC_MODEL.json") or {}
    if exp["numerical_marking_authorised"] is not None:
        check("E05", "numerical marking authorisation", r.get("numerical_marking_authorised") == exp["numerical_marking_authorised"],
              f"got {r.get('numerical_marking_authorised')}")
    fs = d.get("FINAL_SCORE_MODEL.json") or {}
    if exp["expected_can_proceed"]:
        tot = (fs.get("total") or {})
        if exp["numerical_marking_authorised"]:
            check("E06", "total available + computed by tool",
                  tot.get("total_available") == exp["expected_total_available"] and tot.get("computed_by") == "compute_scores.py"
                  and tot.get("total_score") is not None, json.dumps(tot))
        else:
            check("E06", "no numerical score produced", tot.get("total_score") is None and not fs.get("criteria"),
                  json.dumps(tot))
    sp = d.get("SPECIALIST_REVIEW.json") or {}
    act = set(sp.get("reviews_activated", []))
    if exp["required_specialist_reviews"] or exp["forbidden_specialist_reviews"]:
        check("E07", "specialist reviews activated correctly",
              set(exp["required_specialist_reviews"]) <= act and not (set(exp["forbidden_specialist_reviews"]) & act),
              f"activated {sorted(act)}")
    reg = d.get("REQUIREMENT_REGISTER.json") or {}
    pa = d.get("PRIMARY_ASSESSMENT.json") or {}
    sm = d.get("SECOND_MARKER_REVIEW.json") or {}
    status = {a["requirement_id"]: a["status"] for a in pa.get("requirement_assessments", [])}
    second = {c["requirement_id"]: c["second_status"] for c in sm.get("requirement_challenges", [])}
    for i, mf in enumerate(exp["must_flag_requirements"], 1):
        rx = re.compile(mf["requirement_text_regex"])
        hits = [q for q in reg.get("requirements", []) if rx.search(q["text"]) or rx.search(q["verbatim_quote"])]
        flagged = [q["id"] for q in hits if status.get(q["id"]) in mf["status_in"] or second.get(q["id"]) in mf["status_in"]]
        check(f"E08.{i}", f"deliberate defect flagged: {mf['requirement_text_regex']}", bool(flagged),
              f"matching REQs {[q['id'] for q in hits]}, statuses {[status.get(q['id']) for q in hits]}")
    if exp["must_record_conflict"]:
        check("E09", "conflict recorded and surfaced", bool(reg.get("conflicts")) and "CONF-" in report,
              f"{len(reg.get('conflicts', []))} conflict(s)")
    files = m.get("files", [])
    for sub in exp["must_list_unanalysed"]:
        f = [x for x in files if sub in x["path"]]
        check(f"E10.{sub}", f"unanalysable file reported: {sub}", bool(f) and all(not x["analysed"] for x in f) and sub in report,
              json.dumps([{k: x.get(k) for k in ("path", "extraction_status", "analysed")} for x in f]))
    for rx in exp["not_provided_must_include_regex"]:
        check(f"E11.{rx}", f"NOT PROVIDED recorded: {rx}", any(re.search(rx, x) for x in reg.get("not_provided", [])),
              f"not_provided={reg.get('not_provided')}")
    vf = d.get("VERIFIED_FINDINGS.json") or {}
    removed = {v["finding_id"] for v in vf.get("findings", []) if v["outcome"] == "REMOVED"}
    final_sev = {v["finding_id"]: v["final_severity"] for v in vf.get("findings", [])}
    findings = []
    for fname in ("PRIMARY_ASSESSMENT.json", "SPECIALIST_REVIEW.json", "EVIDENCE_AUDIT.json",
                  "COHERENCE_AUDIT.json", "SECOND_MARKER_REVIEW.json"):
        for f in (d.get(fname) or {}).get("findings", []):
            if f["finding_id"] not in removed:
                findings.append(f)
    for rx in exp["no_serious_finding_for_requirement_regex"]:
        ids = {q["id"] for q in reg.get("requirements", []) if re.search(rx, q["text"])}
        bad = [f["finding_id"] for f in findings if f["requirement_ref"] in ids
               and final_sev.get(f["finding_id"], f["severity"]) in ("CRITICAL", "MAJOR")]
        bad += [a["requirement_id"] for a in pa.get("requirement_assessments", [])
                if a["requirement_id"] in ids and a["priority"] in ("CRITICAL", "MAJOR")]
        check(f"E12.{rx}", f"optional content not penalised: {rx}", not bad, f"offending {bad}")
    for phrase in exp["report_must_contain"]:
        check(f"E13.{phrase[:30]}", f"report contains: {phrase}", phrase in report)
    for rx in exp["report_must_not_match_regex"]:
        mt = re.search(rx, report)
        check(f"E14.{rx[:30]}", f"report free of: {rx}", not mt, mt.group(0) if mt else "")
    for rx in exp["findings_must_not_match_regex"]:
        bad = [f["finding_id"] for f in findings if re.search(rx, f["issue"] + " " + f["how_to_improve"])]
        check(f"E15.{rx[:30]}", f"no task-inappropriate/invented finding: {rx}", not bad, f"offending {bad}")
    if exp["expect_release"]:
        qa = d.get("QA_STATUS.json") or {}
        check("E16", "QA_STATUS PASS", qa.get("qa_status") == "PASS")
        res = validate.run(trail, [n for n, _, _ in validate.C.TRAIL], True, out / "_work" / "FINAL_QUALITY_AUDIT.draft.md",
                           out / "_work" / "INPUT_INVENTORY.json")
        check("E17", "deterministic validator passes on final trail", res["passed"],
              "; ".join(e["message"] for e in res["errors"][:5]))
        check("E18", "HTML report produced", (out / "FINAL_QUALITY_AUDIT.html").exists())
    passed = all(c["passed"] for c in checks)
    return {"case": case, "passed": passed, "checks": checks}


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    root = Path(argv[argv.index("--root") + 1]).resolve() if "--root" in argv else REPO
    result = evaluate(argv[0], root)
    for c in result["checks"]:
        print(f"{'PASS' if c['passed'] else 'FAIL'}  {c['id']:<14} {c['check']}" + ("" if c["passed"] else f"  -> {c['detail']}"))
    print(f"\n{argv[0]}: {'ALL EXPECTATIONS MET' if result['passed'] else 'EXPECTATIONS FAILED'}")
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

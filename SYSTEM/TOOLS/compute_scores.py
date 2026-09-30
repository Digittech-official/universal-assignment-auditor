#!/usr/bin/env python3
"""Deterministic score arithmetic for Agent 11 (Score Adjudicator).

The adjudicator decides each criterion's final_mark (RUBRIC -> EVIDENCE ->
DESCRIPTOR -> RANGE -> MARK). This tool — never the language model — performs
all arithmetic: totals, weighted contributions, percentage and grade band.

Usage:
  python3 SYSTEM/TOOLS/compute_scores.py                 # compute totals in FINAL_SCORE_MODEL.json
  python3 SYSTEM/TOOLS/compute_scores.py --not-applicable "reason"
                                                        # write a non-scoring model (Brief-Only / Title / bands-only)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AUDIT_DIR, load_json, write_json  # noqa: E402

AGENT = "AGENT_11_SCORE_ADJUDICATOR"


def r2(x: float) -> float:
    return round(x + 0.0, 2)


def compute(model: dict, rubric: dict) -> tuple[dict, list[str]]:
    """Return (total_block, log). Raises ValueError on invalid inputs."""
    method = rubric.get("aggregation_method")
    crits = {c["id"]: c for c in rubric.get("criteria", [])}
    log: list[str] = []
    rows = model.get("criteria", [])
    ids = [c["criterion_id"] for c in rows]
    if sorted(ids) != sorted(crits):
        raise ValueError(f"Score model criteria {sorted(ids)} do not match rubric criteria {sorted(crits)}.")
    for row in rows:
        rc = crits[row["criterion_id"]]
        if row.get("max_marks") != rc.get("max_marks") or row.get("weight_percent") != rc.get("weight_percent"):
            raise ValueError(f"{row['criterion_id']}: max_marks/weight differ from RUBRIC_MODEL.json.")
        fm = row.get("final_mark")
        if fm is None:
            raise ValueError(f"{row['criterion_id']}: final_mark missing.")
        cap = rc.get("max_marks") if rc.get("max_marks") is not None else 100
        if not 0 <= fm <= cap:
            raise ValueError(f"{row['criterion_id']}: final_mark {fm} outside 0..{cap}.")

    if method == "SUM":
        total = sum(r["final_mark"] for r in rows)
        max_sum = sum(crits[r["criterion_id"]]["max_marks"] for r in rows)
        available = rubric.get("total_available") or max_sum
        for r in rows:
            r["weighted_contribution"] = None
            log.append(f"{r['criterion_id']}: {r['final_mark']} / {r['max_marks']}")
        log.append(f"TOTAL = {' + '.join(str(r['final_mark']) for r in rows)} = {r2(total)} / {available}")
        pct = r2(total / available * 100) if available else None
    elif method == "WEIGHTED_PERCENT":
        weight_sum = sum(crits[r["criterion_id"]]["weight_percent"] for r in rows)
        total = 0.0
        for r in rows:
            rc = crits[r["criterion_id"]]
            cap = rc.get("max_marks") if rc.get("max_marks") is not None else 100
            contrib = r["final_mark"] / cap * rc["weight_percent"]
            r["weighted_contribution"] = r2(contrib)
            total += contrib
            log.append(f"{r['criterion_id']}: {r['final_mark']}/{cap} x {rc['weight_percent']}% = {r2(contrib)}")
        available = weight_sum
        log.append(f"TOTAL = {r2(total)} / {r2(weight_sum)} (weighted percentage points)")
        pct = r2(total / weight_sum * 100) if weight_sum else None
    else:
        raise ValueError(f"Aggregation method {method!r} does not permit numerical totals.")

    band = "NOT PROVIDED"
    boundaries = rubric.get("grade_boundaries") or []
    if boundaries and pct is not None:
        # Boundaries are interpreted on the percentage scale unless every boundary
        # max exceeds 100 (then they are on the raw-total scale).
        on_raw = all((b.get("max") or 0) > 100 for b in boundaries)
        value = r2(total) if on_raw else pct
        for b in boundaries:
            lo = b.get("min") if b.get("min") is not None else float("-inf")
            hi = b.get("max") if b.get("max") is not None else float("inf")
            if lo <= value <= hi:
                band = b["label"]
                break
        else:
            band = "NO MATCHING BOUNDARY IN RUBRIC"
        log.append(f"Grade band lookup on {'raw total' if on_raw else 'percentage'} {value}: {band}")
    total_block = {"total_score": r2(total), "total_available": available, "percentage": pct,
                   "grade_band": band, "computed_by": "compute_scores.py"}
    return total_block, log


def main(argv: list[str]) -> int:
    path = AUDIT_DIR / "FINAL_SCORE_MODEL.json"
    if "--not-applicable" in argv:
        idx = argv.index("--not-applicable")
        reason = argv[idx + 1] if len(argv) > idx + 1 else "Numerical marking is not authorised."
        write_json(path, {
            "agent": AGENT, "applicable": False, "not_applicable_reason": reason,
            "aggregation_method": "NONE", "criteria": [],
            "total": {"total_score": None, "total_available": None, "percentage": None,
                      "grade_band": "NOT APPLICABLE", "computed_by": "compute_scores.py"},
            "verification_reconciled": True,
            "calculation_log": ["No numerical score produced: " + reason],
        })
        print(f"Wrote non-scoring FINAL_SCORE_MODEL.json ({reason})")
        return 0
    try:
        model = load_json(path)
        rubric = load_json(AUDIT_DIR / "RUBRIC_MODEL.json")
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 2
    if not rubric.get("numerical_marking_authorised"):
        print("ERROR: RUBRIC_MODEL.json does not authorise numerical marking. Use --not-applicable.")
        return 2
    try:
        total, log = compute(model, rubric)
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
        print(f"ERROR: {exc}")
        return 1
    model["aggregation_method"] = rubric["aggregation_method"]
    model["total"] = total
    model["calculation_log"] = log
    write_json(path, model)
    print("\n".join(log))
    print(f"Total {total['total_score']} / {total['total_available']} ({total['percentage']}%) — band: {total['grade_band']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

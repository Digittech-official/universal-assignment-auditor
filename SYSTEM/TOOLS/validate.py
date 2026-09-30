#!/usr/bin/env python3
"""Deterministic validator for the audit trail — the machine half of the QA gate.

Checks every audit-trail JSON against its schema, then runs cross-document
integrity rules (traceability, coverage, authorisation of marks, arithmetic,
verification of serious findings, policy phrases, report completeness).

Usage:
  python3 SYSTEM/TOOLS/validate.py                 # validate whatever trail files exist
  python3 SYSTEM/TOOLS/validate.py --upto AGENT_05 # require all files up to that agent
  python3 SYSTEM/TOOLS/validate.py --pre-qa        # require all files except QA_STATUS + draft report
  python3 SYSTEM/TOOLS/validate.py --final         # require everything incl. QA_STATUS PASS
  python3 SYSTEM/TOOLS/validate.py --dir PATH      # validate a trail stored elsewhere (tests)

Writes <trail>/VALIDATION_REPORT.json. Exit code 1 when any ERROR exists.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from compute_scores import compute  # noqa: E402

SEV_RANK = {"CRITICAL": 4, "MAJOR": 3, "MODERATE": 2, "MINOR": 1}
FINDING_SOURCES = [  # (file, finding list path, id prefix)
    ("PRIMARY_ASSESSMENT.json", "findings", "F6-"),
    ("SPECIALIST_REVIEW.json", "findings", "F7-"),
    ("EVIDENCE_AUDIT.json", "findings", "F8-"),
    ("COHERENCE_AUDIT.json", "findings", "F9-"),
    ("SECOND_MARKER_REVIEW.json", "findings", "F10-"),
]
FABRICATION_WORDS = re.compile(r"(?i)\b(fabricat\w*|fake (?:reference|citation|source)s?|non-?existent (?:reference|source|article|paper)s?|hallucinated)\b")


# ---------------------------------------------------------------- schema subset
def _type_ok(value, t) -> bool:
    types = t if isinstance(t, list) else [t]
    for ty in types:
        if ty == "null" and value is None:
            return True
        if ty == "string" and isinstance(value, str):
            return True
        if ty == "boolean" and isinstance(value, bool):
            return True
        if ty == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if ty == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if ty == "array" and isinstance(value, list):
            return True
        if ty == "object" and isinstance(value, dict):
            return True
    return False


def schema_errors(value, schema: dict, path: str = "$") -> list[str]:
    errs: list[str] = []
    if "type" in schema and not _type_ok(value, schema["type"]):
        return [f"{path}: expected {schema['type']}, got {type(value).__name__}"]
    if "const" in schema and value != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, str) and "pattern" in schema and not re.search(schema["pattern"], value):
        errs.append(f"{path}: {value!r} does not match {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errs.append(f"{path}: {value} > maximum {schema['maximum']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errs.append(f"{path}: missing required field '{key}'")
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                errs.extend(schema_errors(value[key], sub, f"{path}.{key}"))
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errs.append(f"{path}: needs at least {schema['minItems']} item(s)")
        if "items" in schema:
            for i, item in enumerate(value):
                errs.extend(schema_errors(item, schema["items"], f"{path}[{i}]"))
    return errs


# ---------------------------------------------------------------- helpers
def norm(text: str) -> str:
    text = text.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"[^a-z0-9%]+", " ", text).strip()


class Result:
    def __init__(self):
        self.errors: list[dict] = []
        self.warnings: list[dict] = []

    def err(self, rule: str, msg: str):
        self.errors.append({"rule": rule, "message": msg})

    def warn(self, rule: str, msg: str):
        self.warnings.append({"rule": rule, "message": msg})


def load_trail(trail: Path, res: Result) -> dict:
    docs = {}
    for name, schema_name, _agent in C.TRAIL:
        p = trail / name
        if not p.exists():
            continue
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            res.err("SCHEMA", f"{name}: invalid JSON ({exc})")
            continue
        schema = json.loads((C.SCHEMA_DIR / f"{schema_name}.schema.json").read_text())
        for e in schema_errors(doc, schema):
            res.err("SCHEMA", f"{name} {e}")
        docs[name] = doc
    return docs


def source_texts(manifest: dict, repo_root: Path) -> dict[str, str]:
    """file_id -> normalised text (only where a machine/Claude transcription exists)."""
    out = {}
    for f in manifest.get("files", []):
        src = f.get("text_source")
        if not src:
            continue
        for base in (repo_root, C.OUTPUT_DIR.parent):
            p = base / src
            if p.exists():
                out[f["file_id"]] = norm(p.read_text(encoding="utf-8", errors="replace"))
                break
    return out


def quote_traceable(quote: str, text: str) -> bool:
    segments = [norm(s) for s in re.split(r"\.\.\.|…|\[\.\.\.\]", quote)]
    segments = [s for s in segments if len(s) >= 3]
    return bool(segments) and all(s in text for s in segments)


# ---------------------------------------------------------------- cross checks
def check_manifest(d, res, inventory):
    m = d.get("INPUT_MANIFEST.json")
    if not m:
        return
    if (m["analysis_mode"] == "CANNOT_PROCEED") == m["can_proceed"]:
        res.err("X01", "INPUT_MANIFEST: can_proceed must be false exactly when analysis_mode is CANNOT_PROCEED.")
    if not m["can_proceed"] and not m["blocking_reasons"]:
        res.err("X01", "INPUT_MANIFEST: blocking_reasons required when the audit cannot proceed.")
    if m["can_proceed"] and not m["submission_present"]:
        res.err("X01", "INPUT_MANIFEST: cannot proceed without a completed submission.")
    if m["analysis_mode"] == "RUBRIC" and not m["rubric_present"]:
        res.err("X01", "INPUT_MANIFEST: RUBRIC mode selected but rubric_present is false.")
    if m["analysis_mode"] == "BRIEF_ONLY" and (m["rubric_present"] or not m["brief_present"]):
        res.err("X01", "INPUT_MANIFEST: BRIEF_ONLY requires a brief and no usable rubric.")
    if m["analysis_mode"] == "TITLE_TOPIC" and (m["rubric_present"] or m["brief_present"]):
        res.err("X01", "INPUT_MANIFEST: TITLE_TOPIC mode is only valid with no rubric and no meaningful brief.")
    ids = [f["file_id"] for f in m["files"]]
    if len(ids) != len(set(ids)):
        res.err("X01", "INPUT_MANIFEST: duplicate file_id values.")
    for f in m["files"]:
        if not f["analysed"] and not f.get("not_analysed_reason"):
            res.err("X01", f"INPUT_MANIFEST: {f['file_id']} not analysed but no reason given (no silent skipping).")
        if f["extraction_status"] in ("FAILED", "UNSUPPORTED", "EMPTY") and f["analysed"]:
            res.err("X01", f"INPUT_MANIFEST: {f['file_id']} is {f['extraction_status']} but marked analysed.")
        if f["extraction_status"] in ("FAILED", "UNSUPPORTED") and \
                C.PHRASE_UNREADABLE not in (f.get("not_analysed_reason") or ""):
            res.err("X01", f"INPUT_MANIFEST: {f['file_id']} unreadable; reason must contain '{C.PHRASE_UNREADABLE}'")
    if inventory:
        inv_ids = {f["file_id"] for f in inventory.get("files", [])}
        missing = inv_ids - set(ids)
        if missing:
            res.err("X01", f"INPUT_MANIFEST omits inventoried files (never silently ignore a file): {sorted(missing)}")


def check_classification(d, res):
    t, m, r = d.get("TASK_CLASSIFICATION.json"), d.get("INPUT_MANIFEST.json"), d.get("RUBRIC_MODEL.json")
    if not t:
        return
    if m and m["analysis_mode"] != "RUBRIC" and t["numerical_marking_authorised"]:
        res.err("X02", "TASK_CLASSIFICATION: numerical marking authorised outside RUBRIC mode.")
    if r and t["numerical_marking_authorised"] != r["numerical_marking_authorised"]:
        res.err("X02", "TASK_CLASSIFICATION and RUBRIC_MODEL disagree on numerical_marking_authorised.")
    if t["coding_review_required"] != ("CODE" in t["specialist_reviews_required"]):
        res.err("X02", "TASK_CLASSIFICATION: coding_review_required inconsistent with specialist_reviews_required.")
    if t["statistical_review_required"] != ("DATA_STATISTICS" in t["specialist_reviews_required"]):
        res.err("X02", "TASK_CLASSIFICATION: statistical_review_required inconsistent with specialist_reviews_required.")
    if t["presentation_review_required"] != ("PRESENTATION" in t["specialist_reviews_required"]):
        res.err("X02", "TASK_CLASSIFICATION: presentation_review_required inconsistent with specialist_reviews_required.")


def check_requirements(d, res, texts):
    reg, m = d.get("REQUIREMENT_REGISTER.json"), d.get("INPUT_MANIFEST.json")
    if not reg:
        return
    if m and reg["analysis_mode"] != m["analysis_mode"]:
        res.err("X03", "REQUIREMENT_REGISTER analysis_mode differs from INPUT_MANIFEST.")
    ids = [r["id"] for r in reg["requirements"]]
    expected = [f"REQ-{i:03d}" for i in range(1, len(ids) + 1)]
    if ids != expected:
        res.err("X03", f"REQUIREMENT_REGISTER: IDs must be sequential REQ-001..; got {ids[:5]}...")
    if m and m["can_proceed"] and not ids:
        res.err("X03", "REQUIREMENT_REGISTER: no requirements. Even Title/Topic mode must register the title/topic task.")
    manifest_ids = {f["file_id"] for f in m["files"]} if m else set()
    for r in reg["requirements"]:
        if r["source_priority"] > 5:
            res.err("X03", f"{r['id']}: source_priority {r['source_priority']} is best practice/convention — "
                           "the register holds only explicit requirements from supplied documents.")
        if m and r["source"]["file_id"] not in manifest_ids:
            res.err("X03", f"{r['id']}: source file {r['source']['file_id']} not in INPUT_MANIFEST.")
        text = texts.get(r["source"]["file_id"])
        if not r["verbatim_quote"].strip():
            res.err("X03", f"{r['id']}: empty verbatim_quote — requirement is not traceable.")
        elif text is not None and not quote_traceable(r["verbatim_quote"], text):
            res.err("X03", f"{r['id']}: verbatim_quote not found in source {r['source']['file_id']} — "
                           "possible invented or paraphrased requirement.")
    for c in reg["conflicts"]:
        bad = [x for x in c["requirement_ids"] if x not in ids]
        if bad:
            res.err("X03", f"{c['id']}: references unknown requirements {bad}.")


def check_rubric(d, res, texts):
    rub, m = d.get("RUBRIC_MODEL.json"), d.get("INPUT_MANIFEST.json")
    if not rub:
        return
    mode = m["analysis_mode"] if m else None
    auth = rub["numerical_marking_authorised"]
    if mode and mode != "RUBRIC":
        if rub["rubric_status"] != "NOT PROVIDED" or rub["criteria"] or auth:
            res.err("X04", "RUBRIC_MODEL: outside RUBRIC mode the status must be NOT PROVIDED with no criteria "
                           "and no numerical authority (never create a rubric).")
    if rub["rubric_status"] != "PROVIDED" and auth:
        res.err("X04", "RUBRIC_MODEL: numerical marking cannot be authorised without a usable rubric.")
    if auth:
        if rub["marking_scale_type"] not in ("NUMERIC_MARKS", "PERCENTAGE_WEIGHTED"):
            res.err("X04", "RUBRIC_MODEL: authorised marking needs NUMERIC_MARKS or PERCENTAGE_WEIGHTED scale.")
        if rub["aggregation_method"] == "NONE":
            res.err("X04", "RUBRIC_MODEL: authorised marking needs an aggregation method.")
        if not rub["criteria"]:
            res.err("X04", "RUBRIC_MODEL: authorised marking with no criteria.")
        for c in rub["criteria"]:
            if rub["aggregation_method"] == "SUM" and c["max_marks"] is None:
                res.err("X04", f"{c['id']}: SUM aggregation requires max_marks.")
            if rub["aggregation_method"] == "WEIGHTED_PERCENT" and c["weight_percent"] is None:
                res.err("X04", f"{c['id']}: WEIGHTED_PERCENT aggregation requires weight_percent.")
        if rub["aggregation_method"] == "WEIGHTED_PERCENT":
            ws = sum(c["weight_percent"] or 0 for c in rub["criteria"])
            if abs(ws - 100) > 0.01:
                res.warn("X04", f"RUBRIC_MODEL: criterion weights sum to {ws}, not 100 — must be flagged in ambiguities.")
                if not rub["ambiguities"]:
                    res.err("X04", "RUBRIC_MODEL: weights do not sum to 100 and no ambiguity recorded.")
        if rub["aggregation_method"] == "SUM" and rub["total_available"] is not None:
            ms = sum(c["max_marks"] or 0 for c in rub["criteria"])
            if abs(ms - rub["total_available"]) > 0.01 and rub["arithmetic_check"]["consistent"]:
                res.err("X04", f"RUBRIC_MODEL: criteria max sum {ms} != stated total {rub['total_available']} "
                               "but arithmetic_check.consistent is true.")
    ids = [c["id"] for c in rub["criteria"]]
    if ids != [f"CRIT-{i:03d}" for i in range(1, len(ids) + 1)]:
        res.err("X04", "RUBRIC_MODEL: criterion IDs must be sequential CRIT-001..")
    rubric_text = " ".join(texts.get(fid, "") for fid in rub["source_file_ids"])
    for c in rub["criteria"]:
        if rubric_text and not quote_traceable(c["description_verbatim"], rubric_text):
            res.warn("X04", f"{c['id']}: description_verbatim not found verbatim in rubric source text.")
        for lvl in c["descriptors"]:
            lo, hi = lvl["mark_range_min"], lvl["mark_range_max"]
            if lo is not None and hi is not None and lo > hi:
                res.err("X04", f"{c['id']} {lvl['level_label']}: mark range min > max.")
            if c["max_marks"] is not None and hi is not None and hi > c["max_marks"]:
                res.err("X04", f"{c['id']} {lvl['level_label']}: descriptor range exceeds max_marks.")


def check_blueprint(d, res):
    bp, reg, rub = d.get("QUALITY_BLUEPRINT.json"), d.get("REQUIREMENT_REGISTER.json"), d.get("RUBRIC_MODEL.json")
    if not bp:
        return
    reqs = {r["id"]: r for r in reg["requirements"]} if reg else {}
    crits = {c["id"] for c in rub["criteria"]} if rub else set()
    for e in bp["expectations"]:
        if e["category"] == "MANDATORY_REQUIREMENT":
            refs = [s for s in e["source_ids"] if s.startswith("REQ-")]
            if not refs:
                res.err("X05", f"{e['id']}: MANDATORY_REQUIREMENT must cite a REQ id.")
            for s in refs:
                if reqs and s not in reqs:
                    res.err("X05", f"{e['id']}: cites unknown {s}.")
                elif reqs and reqs[s]["obligation"] in ("OPTIONAL", "RECOMMENDED"):
                    res.err("X05", f"{e['id']}: optional/recommended {s} presented as mandatory.")
        elif e["category"] == "RUBRIC_DERIVED_EXPECTATION":
            refs = [s for s in e["source_ids"] if s.startswith("CRIT-")]
            if not refs or any(s not in crits for s in refs):
                res.err("X05", f"{e['id']}: RUBRIC_DERIVED_EXPECTATION must cite existing CRIT ids.")
        else:
            if any(s.startswith("REQ-") and reqs.get(s, {}).get("obligation") == "MANDATORY" for s in e["source_ids"]):
                res.warn("X05", f"{e['id']}: best-practice item cites a mandatory REQ — check category.")


def check_evidence_map(d, res):
    em, reg, rub = d.get("SUBMISSION_EVIDENCE_MAP.json"), d.get("REQUIREMENT_REGISTER.json"), d.get("RUBRIC_MODEL.json")
    if not em:
        return
    locs = {l["loc_id"] for l in em["locations"]}
    if reg:
        linked = [l["requirement_id"] for l in em["requirement_links"]]
        missing = {r["id"] for r in reg["requirements"]} - set(linked)
        if missing:
            res.err("X06", f"SUBMISSION_EVIDENCE_MAP: requirements not mapped: {sorted(missing)}")
    if rub:
        missing = {c["id"] for c in rub["criteria"]} - {l["criterion_id"] for l in em["criterion_links"]}
        if missing:
            res.err("X06", f"SUBMISSION_EVIDENCE_MAP: criteria not mapped: {sorted(missing)}")
    for link in em["requirement_links"] + em["criterion_links"]:
        bad = [x for x in link["loc_ids"] if x not in locs]
        if bad:
            res.err("X06", f"SUBMISSION_EVIDENCE_MAP: unknown loc_ids {bad}.")


def all_findings(d):
    out = []
    for fname, key, prefix in FINDING_SOURCES:
        doc = d.get(fname)
        if doc:
            for f in doc.get(key, []):
                out.append((fname, prefix, f))
    return out


def check_findings(d, res):
    reg, rub = d.get("REQUIREMENT_REGISTER.json"), d.get("RUBRIC_MODEL.json")
    reqs = {r["id"]: r for r in reg["requirements"]} if reg else {}
    crits = {c["id"] for c in rub["criteria"]} if rub else set()
    seen = set()
    for fname, prefix, f in all_findings(d):
        fid = f["finding_id"]
        if not fid.startswith(prefix):
            res.err("X07", f"{fname}: finding {fid} must use prefix {prefix}.")
        if fid in seen:
            res.err("X07", f"Duplicate finding_id {fid}.")
        seen.add(fid)
        if f["basis"] == "BEST_PRACTICE" and f["severity"] == "CRITICAL":
            res.err("X07", f"{fid}: best-practice findings can never be CRITICAL (best practice is not mandatory).")
        ref = f["requirement_ref"]
        if f["basis"] == "MANDATORY_REQUIREMENT":
            if not ref.startswith("REQ-") or (reqs and ref not in reqs):
                res.err("X07", f"{fid}: MANDATORY_REQUIREMENT basis must cite an existing REQ id (got {ref!r}).")
            elif reqs and reqs[ref]["obligation"] in ("OPTIONAL", "RECOMMENDED") and SEV_RANK[f["severity"]] >= 3:
                res.err("X07", f"{fid}: {ref} is {reqs[ref]['obligation']} — cannot ground a {f['severity']} finding.")
        if f["basis"] == "RUBRIC_CRITERION" and (not ref.startswith("CRIT-") or (rub and ref not in crits)):
            res.err("X07", f"{fid}: RUBRIC_CRITERION basis must cite an existing CRIT id (got {ref!r}).")
        for c in f.get("affected_criterion_ids", []):
            if rub and c not in crits:
                res.err("X07", f"{fid}: unknown affected criterion {c}.")
        for k in ("location", "issue", "why_it_matters", "how_to_improve"):
            if len(f[k].strip()) < 12:
                res.err("X07", f"{fid}: '{k}' too short to be actionable.")
        if FABRICATION_WORDS.search(f["issue"] + " " + f["how_to_improve"]):
            ev = d.get("EVIDENCE_AUDIT.json")
            if not (ev and ev["external_verification_performed"]):
                res.err("X07", f"{fid}: alleges fabrication without external verification.")


def check_primary(d, res):
    pa, reg, rub, m = (d.get("PRIMARY_ASSESSMENT.json"), d.get("REQUIREMENT_REGISTER.json"),
                       d.get("RUBRIC_MODEL.json"), d.get("INPUT_MANIFEST.json"))
    if not pa:
        return
    auth = bool(rub and rub["numerical_marking_authorised"])
    if reg:
        got = [a["requirement_id"] for a in pa["requirement_assessments"]]
        want = [r["id"] for r in reg["requirements"]]
        if sorted(got) != sorted(want):
            res.err("X08", f"PRIMARY_ASSESSMENT: requirements assessed {sorted(set(got) ^ set(want))} do not "
                           "match the register (every requirement exactly once).")
        reqs = {r["id"]: r for r in reg["requirements"]}
        for a in pa["requirement_assessments"]:
            r = reqs.get(a["requirement_id"])
            if r and r["obligation"] in ("OPTIONAL", "RECOMMENDED") and a["status"] == "MISSING" \
                    and a["priority"] in ("CRITICAL", "MAJOR"):
                res.err("X08", f"{a['requirement_id']}: optional content absent must not be a CRITICAL/MAJOR issue.")
            if a["status"] == "PASS" and a["priority"] in ("CRITICAL", "MAJOR"):
                res.err("X08", f"{a['requirement_id']}: PASS cannot carry {a['priority']} priority.")
    if rub:
        got = sorted(c["criterion_id"] for c in pa["criterion_assessments"])
        if got != sorted(c["id"] for c in rub["criteria"]):
            res.err("X08", "PRIMARY_ASSESSMENT: every rubric criterion must be assessed exactly once.")
    for c in pa["criterion_assessments"]:
        pm = c["provisional_mark"]
        if not auth and pm is not None:
            res.err("X08", f"{c['criterion_id']}: provisional_mark given but numerical marking is NOT authorised.")
        if auth:
            if pm is None:
                res.err("X08", f"{c['criterion_id']}: provisional mark missing in authorised rubric mode.")
            else:
                lo, hi = c["mark_range_considered"]["min"], c["mark_range_considered"]["max"]
                if c["max_marks"] is not None and not 0 <= pm <= c["max_marks"]:
                    res.err("X08", f"{c['criterion_id']}: provisional mark {pm} outside 0..{c['max_marks']}.")
                if lo is not None and hi is not None and not lo <= pm <= hi:
                    res.err("X08", f"{c['criterion_id']}: mark {pm} outside the descriptor range considered {lo}-{hi} "
                                   "(RUBRIC->DESCRIPTOR->RANGE->MARK violated).")
    if m and m["analysis_mode"] == "TITLE_TOPIC":
        if not pa["quality_dimensions"]:
            res.err("X08", "TITLE_TOPIC mode requires quality_dimensions assessment.")
        if not any(q["basis"] == "BEST_PRACTICE" for q in pa["quality_dimensions"]):
            res.warn("X08", "TITLE_TOPIC: expected best-practice dimensions to be labelled BEST_PRACTICE.")


def check_specialist(d, res):
    sp, t = d.get("SPECIALIST_REVIEW.json"), d.get("TASK_CLASSIFICATION.json")
    if not sp:
        return
    cr = sp["code_review"]
    if t:
        req = set(t["specialist_reviews_required"])
        if set(sp["reviews_activated"]) != req:
            res.err("X09", f"SPECIALIST_REVIEW activated {sorted(sp['reviews_activated'])} but classification "
                           f"requires {sorted(req)}.")
        if t["coding_review_required"] and not cr["performed"] and not cr.get("not_performed_reason"):
            res.err("X09", "Coding review required but not performed and no reason given.")
        if not t["coding_review_required"] and cr["performed"]:
            res.err("X09", "Coding review performed on a task that does not require it (coding rules on non-code work).")
        if not t["statistical_review_required"] and sp["data_review"]["performed"]:
            res.err("X09", "Statistical review performed on a task that does not require it.")
        if not t["presentation_review_required"] and sp["presentation_review"]["performed"]:
            res.err("X09", "Presentation review performed on a task that does not require it.")
    if cr["execution_performed"]:
        res.err("X09", "Code execution is disabled by policy (SYSTEM/RULES/CODE_EXECUTION_POLICY.md).")
    if cr["performed"] and cr["execution_statement"] != C.PHRASE_STATIC_CODE:
        res.err("X09", f"code_review.execution_statement must be exactly '{C.PHRASE_STATIC_CODE}'")


def check_evidence_audit(d, res):
    ev = d.get("EVIDENCE_AUDIT.json")
    if not ev:
        return
    if not ev["external_verification_performed"] and ev["authenticity_statement"] != C.PHRASE_REFS_UNVERIFIED:
        res.err("X10", f"EVIDENCE_AUDIT.authenticity_statement must be exactly '{C.PHRASE_REFS_UNVERIFIED}'")
    if ev["external_verification_performed"]:
        res.err("X10", "External reference verification is not part of this tool; do not claim it.")
    if not ev["applicable"] and not ev.get("not_applicable_reason"):
        res.err("X10", "EVIDENCE_AUDIT not applicable but no reason given.")


def check_coherence(d, res):
    co = d.get("COHERENCE_AUDIT.json")
    if co and not co["chain_links"]:
        res.err("X11", "COHERENCE_AUDIT: no chain links evaluated.")


def check_second_marker(d, res):
    sm, pa, rub = d.get("SECOND_MARKER_REVIEW.json"), d.get("PRIMARY_ASSESSMENT.json"), d.get("RUBRIC_MODEL.json")
    if not sm or not pa:
        return
    auth = bool(rub and rub["numerical_marking_authorised"])
    prim = {c["criterion_id"]: c for c in pa["criterion_assessments"]}
    if sorted(c["criterion_id"] for c in sm["criterion_challenges"]) != sorted(prim):
        res.err("X12", "SECOND_MARKER_REVIEW must independently review every criterion.")
    for c in sm["criterion_challenges"]:
        p = prim.get(c["criterion_id"])
        if p and c["primary_mark"] != p["provisional_mark"]:
            res.err("X12", f"{c['criterion_id']}: second marker misquotes the primary mark.")
        if not auth and (c["second_mark"] is not None or c["primary_mark"] is not None):
            res.err("X12", f"{c['criterion_id']}: marks recorded but numerical marking is not authorised.")
        if auth and c["second_mark"] is None:
            res.err("X12", f"{c['criterion_id']}: second mark missing.")
        if auth and c["second_mark"] is not None and c["primary_mark"] is not None:
            expect = "AGREE" if c["second_mark"] == c["primary_mark"] else (
                "OVER_MARKED" if c["second_mark"] < c["primary_mark"] else "UNDER_MARKED")
            if c["direction"] != expect:
                res.err("X12", f"{c['criterion_id']}: direction {c['direction']} inconsistent with marks (expected {expect}).")
    pstat = {a["requirement_id"]: a["status"] for a in pa["requirement_assessments"]}
    for ch in sm["requirement_challenges"]:
        if ch["requirement_id"] in pstat and ch["primary_status"] != pstat[ch["requirement_id"]]:
            res.err("X12", f"{ch['requirement_id']}: second marker misquotes the primary status.")
        if ch["agree"] != (ch["primary_status"] == ch["second_status"]):
            res.err("X12", f"{ch['requirement_id']}: 'agree' inconsistent with statuses.")
    known = {f["finding_id"] for _, _, f in all_findings(d)}
    for x in sm["unsupported_criticisms"] + sm["false_positives"]:
        if x["finding_id"] not in known:
            res.err("X12", f"SECOND_MARKER_REVIEW challenges unknown finding {x['finding_id']}.")


def check_scores(d, res):
    fs, rub, pa, sm = (d.get("FINAL_SCORE_MODEL.json"), d.get("RUBRIC_MODEL.json"),
                       d.get("PRIMARY_ASSESSMENT.json"), d.get("SECOND_MARKER_REVIEW.json"))
    if not fs:
        return
    auth = bool(rub and rub["numerical_marking_authorised"])
    if not auth:
        if fs["applicable"] or fs["criteria"] or fs["total"]["total_score"] is not None:
            res.err("X13", "FINAL_SCORE_MODEL contains a score although numerical marking is NOT authorised.")
        return
    if not fs["applicable"]:
        res.err("X13", "FINAL_SCORE_MODEL: numerical marking authorised but model marked not applicable.")
        return
    if fs["total"]["computed_by"] != "compute_scores.py":
        res.err("X13", "FINAL_SCORE_MODEL totals must be computed by compute_scores.py, not by hand.")
    prim = {c["criterion_id"]: c["provisional_mark"] for c in pa["criterion_assessments"]} if pa else {}
    sec = {c["criterion_id"]: c["second_mark"] for c in sm["criterion_challenges"]} if sm else {}
    rcrit = {c["id"]: c for c in rub["criteria"]}
    for c in fs["criteria"]:
        cid = c["criterion_id"]
        if prim and c["primary_mark"] != prim.get(cid):
            res.err("X13", f"{cid}: primary_mark differs from PRIMARY_ASSESSMENT.")
        if sec and c["second_mark"] != sec.get(cid):
            res.err("X13", f"{cid}: second_mark differs from SECOND_MARKER_REVIEW.")
        if c["disputed"] != (c["primary_mark"] != c["second_mark"]):
            res.err("X13", f"{cid}: 'disputed' flag inconsistent with the two marks.")
        pm, sm2, fm = c["primary_mark"], c["second_mark"], c["final_mark"]
        if c["disputed"] and None not in (pm, sm2, fm) and fm == (pm + sm2) / 2 and fm not in (pm, sm2):
            res.warn("X13", f"{cid}: final mark equals the average of the two marks — confirm it was adjudicated "
                            "from evidence, not averaged.")
            if "averag" not in c["resolution"]["reasoning"].lower():
                res.err("X13", f"{cid}: final mark is the exact average; reasoning must explain why this is the "
                               "evidence-based mark and not an average.")
        rc = rcrit.get(cid)
        if rc:
            for lvl in rc["descriptors"]:
                if lvl["level_label"].strip().lower() == c["final_level"].strip().lower():
                    lo, hi = lvl["mark_range_min"], lvl["mark_range_max"]
                    if fm is not None and lo is not None and hi is not None and not lo <= fm <= hi:
                        res.err("X13", f"{cid}: final mark {fm} outside descriptor '{lvl['level_label']}' range {lo}-{hi}.")
    try:
        total, _ = compute(json.loads(json.dumps(fs)), rub)
        for k in ("total_score", "total_available", "percentage", "grade_band"):
            a, b = total[k], fs["total"][k]
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                if abs(a - b) > 0.01:
                    res.err("X13", f"FINAL_SCORE_MODEL.total.{k} = {b} but recomputation gives {a}.")
            elif a != b:
                res.err("X13", f"FINAL_SCORE_MODEL.total.{k} = {b!r} but recomputation gives {a!r}.")
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
        res.err("X13", f"FINAL_SCORE_MODEL cannot be recomputed: {exc}")
    vf = d.get("VERIFIED_FINDINGS.json")
    if vf and vf["requires_score_readjudication"] and not fs["verification_reconciled"]:
        res.err("X13", "Verified findings changed criteria "
                       f"{vf['requires_score_readjudication']} — Score Adjudicator must re-run and set verification_reconciled.")


def check_verified(d, res):
    vf, rub = d.get("VERIFIED_FINDINGS.json"), d.get("RUBRIC_MODEL.json")
    if not vf:
        return
    serious = {f["finding_id"]: (fname, f) for fname, _, f in all_findings(d) if f["severity"] in ("CRITICAL", "MAJOR")}
    got = [v["finding_id"] for v in vf["findings"]]
    missing = set(serious) - set(got)
    if missing:
        res.err("X14", f"Serious findings not independently verified: {sorted(missing)}")
    if len(got) != len(set(got)):
        res.err("X14", "VERIFIED_FINDINGS contains duplicate finding ids.")
    auth = bool(rub and rub["numerical_marking_authorised"])
    need_readj = set()
    counts = {"CONFIRMED": 0, "CORRECTED": 0, "DOWNGRADED": 0, "REMOVED": 0}
    for v in vf["findings"]:
        counts[v["outcome"]] += 1
        src = serious.get(v["finding_id"])
        if src and v["original_severity"] != src[1]["severity"]:
            res.err("X14", f"{v['finding_id']}: original_severity misquoted.")
        ver = v["verification"]
        sound = (ver["requirement_real"] and ver["evidence_accurate"] and ver["location_correct"]
                 and ver["proportionate"] and ver["instruction_understood"] and not ver["false_positive"])
        if v["outcome"] == "CONFIRMED" and not sound:
            res.err("X14", f"{v['finding_id']}: CONFIRMED although a verification check failed.")
        if (ver["false_positive"] or not ver["requirement_real"]) and v["outcome"] != "REMOVED":
            res.err("X14", f"{v['finding_id']}: false positive / unreal requirement must be REMOVED.")
        if v["outcome"] == "REMOVED" and v["final_severity"] is not None:
            res.err("X14", f"{v['finding_id']}: REMOVED findings must have final_severity null.")
        if v["outcome"] != "REMOVED" and v["final_severity"] is None:
            res.err("X14", f"{v['finding_id']}: final_severity required.")
        if v["outcome"] == "DOWNGRADED" and v["final_severity"] and \
                SEV_RANK[v["final_severity"]] >= SEV_RANK[v["original_severity"]]:
            res.err("X14", f"{v['finding_id']}: DOWNGRADED but severity not lowered.")
        if v["outcome"] in ("CONFIRMED", "CORRECTED") and v["final_severity"] != v["original_severity"]:
            res.err("X14", f"{v['finding_id']}: severity changed — outcome must be DOWNGRADED.")
        if auth and v["outcome"] in ("REMOVED", "DOWNGRADED"):
            need_readj.update(v.get("affected_criterion_ids", []))
    if not need_readj <= set(vf["requires_score_readjudication"]):
        res.err("X14", f"requires_score_readjudication must include {sorted(need_readj)}.")
    s = vf["summary"]
    if s["checked"] != len(vf["findings"]) or any(s[k.lower()] != counts[k] for k in counts):
        res.err("X14", "VERIFIED_FINDINGS.summary counts are wrong.")


def check_qa(d, res):
    qa = d.get("QA_STATUS.json")
    if not qa:
        return
    ids = sorted(c["check_id"] for c in qa["checks"])
    expected = sorted(json.loads((C.SCHEMA_DIR / "qa_checklist.json").read_text()))
    if ids != expected:
        res.err("X15", "QA_STATUS must contain every QA check exactly once.")
    failed = [c["check_id"] for c in qa["checks"] if c["result"] == "FAIL"]
    if qa["qa_status"] == "PASS":
        if failed or qa["failures"]:
            res.err("X15", f"QA_STATUS is PASS but checks failed: {failed}")
        if not qa["deterministic_validation"]["validator_passed"]:
            res.err("X15", "QA_STATUS is PASS but the deterministic validator did not pass.")
        if not qa["release_authorised"]:
            res.err("X15", "QA_STATUS PASS must authorise release.")
    else:
        if qa["release_authorised"]:
            res.err("X15", "QA_STATUS FAIL cannot authorise release.")
        if not qa["failures"]:
            res.err("X15", "QA_STATUS FAIL must list failures and the stage to re-run.")


def split_sections(md: str) -> dict[int, str]:
    parts: dict[int, str] = {}
    matches = list(re.finditer(r"^##\s+(\d{1,2})\.\s+(.+)$", md, flags=re.M))
    for i, mt in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        parts[int(mt.group(1))] = md[mt.start():end]
    return parts


def check_report(d, res, report: Path):
    if not report.exists():
        res.err("X16", f"Draft report missing: {C.rel(report)}")
        return
    md = report.read_text(encoding="utf-8")
    secs = split_sections(md)
    for num, title in C.REPORT_SECTIONS:
        if num not in secs:
            res.err("X16", f"Report section missing: '## {num}. {title}'")
    rub, fs, m = d.get("RUBRIC_MODEL.json"), d.get("FINAL_SCORE_MODEL.json"), d.get("INPUT_MANIFEST.json")
    auth = bool(rub and rub["numerical_marking_authorised"])
    s7 = secs.get(7, "") + secs.get(8, "")
    if not auth:
        if C.PHRASE_NO_SCHEME not in secs.get(7, ""):
            res.err("X16", f"Section 7 must state '{C.PHRASE_NO_SCHEME}' when marking is not authorised.")
        if re.search(r"\b\d{1,3}(?:\.\d+)?\s*(?:/\s*\d{1,3}\b|%|\s*marks?\b|\s*out of\s*\d)", s7):
            res.err("X16", "Sections 7/8 contain a numeric mark although numerical marking is not authorised.")
    elif fs and fs["total"]["total_score"] is not None:
        tot = fs["total"]["total_score"]
        variants = {str(tot), f"{tot:g}", f"{tot:.1f}", f"{tot:.2f}"}
        if not any(v in secs.get(7, "") for v in variants):
            res.err("X16", f"Section 7 does not show the computed total {tot}.")
        for c in fs["criteria"]:
            if c["criterion_id"] not in secs.get(8, ""):
                res.err("X16", f"Section 8 marking breakdown omits {c['criterion_id']}.")
    if m and m.get("analysis_mode") == "TITLE_TOPIC":
        for label in ("KNOWN REQUIREMENTS", "BEST-PRACTICE EXPECTATIONS"):
            if label not in secs.get(9, ""):
                res.err("X16", f"Title/Topic mode: section 9 must separate '{label}'.")
    reg = d.get("REQUIREMENT_REGISTER.json")
    if reg:
        for r in reg["requirements"]:
            if r["id"] not in secs.get(9, ""):
                res.err("X16", f"Requirement compliance matrix omits {r['id']}.")
    if m:
        s45 = secs.get(4, "") + secs.get(5, "")
        for f in m["files"]:
            if f["file_id"] not in s45 and f["path"] not in s45:
                res.err("X16", f"Sections 4/5 do not account for {f['file_id']} ({f['path']}).")
    vf = d.get("VERIFIED_FINDINGS.json")
    if vf:
        removed = [v["finding_id"] for v in vf["findings"] if v["outcome"] == "REMOVED"]
        for fid in removed:
            if re.search(rf"\b{re.escape(fid)}\b", secs.get(10, "") + secs.get(11, "")):
                res.err("X16", f"Removed finding {fid} still appears under Critical/Major issues.")
        crit_major = [v["finding_id"] for v in vf["findings"]
                      if v["outcome"] != "REMOVED" and v["final_severity"] in ("CRITICAL", "MAJOR")]
        for fid in crit_major:
            if fid not in secs.get(10, "") + secs.get(11, ""):
                res.err("X16", f"Verified serious finding {fid} missing from sections 10/11.")
    ev = d.get("EVIDENCE_AUDIT.json")
    if ev and ev["applicable"] and C.PHRASE_REFS_UNVERIFIED not in md:
        res.err("X16", f"Report must state '{C.PHRASE_REFS_UNVERIFIED}'")
    sp = d.get("SPECIALIST_REVIEW.json")
    if sp and sp["code_review"]["performed"] and C.PHRASE_STATIC_CODE not in md:
        res.err("X16", f"Report must state '{C.PHRASE_STATIC_CODE}'")
    if re.search(r"(?i)\b(infallible|guaranteed (?:grade|mark)|definitive grade|100% accurate)\b", md):
        res.err("X16", "Report overstates certainty (AI assessment is not infallible).")
    if re.search(r"(/home/|/Users/|[A-Za-z]:\\\\Users\\\\)", md):
        res.err("X16", "Report contains an absolute machine path.")


# ---------------------------------------------------------------- driver
def run(trail: Path, require: list[str], check_draft: bool, report_path: Path | None = None,
        inventory_path: Path | None = None) -> dict:
    res = Result()
    for name in require:
        if not (trail / name).exists():
            res.err("PRESENCE", f"Required audit-trail file missing: {name}")
    d = load_trail(trail, res)
    if res.errors and any(e["rule"] == "SCHEMA" for e in res.errors):
        pass  # continue: cross-checks may still reveal more, but guard against KeyErrors
    inventory = None
    inv = inventory_path or (trail.parent / "_work" / "INPUT_INVENTORY.json")
    if inv.exists():
        inventory = json.loads(inv.read_text(encoding="utf-8"))
    texts = source_texts(d.get("INPUT_MANIFEST.json", {}), C.REPO_ROOT) if "INPUT_MANIFEST.json" in d else {}
    checks = [
        lambda: check_manifest(d, res, inventory), lambda: check_classification(d, res),
        lambda: check_requirements(d, res, texts), lambda: check_rubric(d, res, texts),
        lambda: check_blueprint(d, res), lambda: check_evidence_map(d, res), lambda: check_findings(d, res),
        lambda: check_primary(d, res), lambda: check_specialist(d, res), lambda: check_evidence_audit(d, res),
        lambda: check_coherence(d, res), lambda: check_second_marker(d, res), lambda: check_scores(d, res),
        lambda: check_verified(d, res), lambda: check_qa(d, res),
    ]
    if check_draft:
        checks.append(lambda: check_report(d, res, report_path or C.DRAFT_REPORT))
    for chk in checks:
        try:
            chk()
        except (KeyError, TypeError, AttributeError) as exc:
            res.err("STRUCTURE", f"Cross-check aborted by malformed data ({type(exc).__name__}: {exc}) — fix schema errors first.")
    return {"passed": not res.errors, "files_checked": sorted(d), "errors": res.errors, "warnings": res.warnings}


def main(argv: list[str]) -> int:
    trail = C.AUDIT_DIR
    if "--dir" in argv:
        trail = Path(argv[argv.index("--dir") + 1]).resolve()
    names = [n for n, _, _ in C.TRAIL]
    require: list[str] = []
    check_draft = False
    report_path = None
    if "--upto" in argv:
        agent = argv[argv.index("--upto") + 1].upper()
        agents = [a for _, _, a in C.TRAIL]
        if agent not in agents:
            print(f"Unknown agent {agent}; use one of {agents}")
            return 2
        require = names[: agents.index(agent) + 1]
    if "--pre-qa" in argv:
        require = [n for n in names if n != "QA_STATUS.json"]
        check_draft = True
    if "--final" in argv:
        require = names
        check_draft = True
    if "--report" in argv:
        report_path = Path(argv[argv.index("--report") + 1]).resolve()
        check_draft = True
    manifest = trail / "INPUT_MANIFEST.json"
    if manifest.exists():
        try:
            if not json.loads(manifest.read_text())["can_proceed"]:
                require = ["INPUT_MANIFEST.json"]
                check_draft = False
        except (json.JSONDecodeError, KeyError):
            pass
    result = run(trail, require, check_draft, report_path)
    if "--final" in argv and "QA_STATUS.json" in [p.name for p in trail.glob("*.json")]:
        qa = json.loads((trail / "QA_STATUS.json").read_text())
        if qa.get("qa_status") != "PASS" and json.loads(manifest.read_text()).get("can_proceed"):
            result["errors"].append({"rule": "GATE", "message": "QA_STATUS is not PASS — release blocked."})
            result["passed"] = False
    trail.mkdir(parents=True, exist_ok=True)
    C.write_json(trail / "VALIDATION_REPORT.json", result)
    for e in result["errors"]:
        print(f"ERROR   [{e['rule']}] {e['message']}")
    for w in result["warnings"]:
        print(f"WARNING [{w['rule']}] {w['message']}")
    print(f"VALIDATION {'PASSED' if result['passed'] else 'FAILED'} — {len(result['errors'])} error(s), "
          f"{len(result['warnings'])} warning(s); files checked: {len(result['files_checked'])}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

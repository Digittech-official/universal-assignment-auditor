"""Builds small, internally consistent synthetic audit trails for validator tests.

`rubric_trail()` -> RUBRIC mode, 2 criteria (SUM, 20 + 30 = 50 marks), 3 requirements.
`brief_trail()`  -> BRIEF_ONLY mode, no marks.
Tests mutate one field at a time and assert that the right validator rule fires.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

BRIEF = ("Write an essay of 1,500 words on renewable energy policy. You must use Harvard referencing. "
         "You may include an appendix.")
RUBRIC = ("Criterion 1 Argument and analysis (20 marks). Criterion 2 Use of evidence (30 marks). "
          "Excellent 70-100% sustained critical analysis. Good 50-69% some analysis.")
STATIC = "CODE WAS REVIEWED STATICALLY; EXECUTION WAS NOT VERIFIED."
REFS = "REFERENCE AUTHENTICITY WAS NOT EXTERNALLY VERIFIED."
NO_SCHEME = "NO AUTHORISED NUMERICAL MARKING SCHEME WAS PROVIDED."


def finding(fid, sev="MAJOR", basis="MANDATORY_REQUIREMENT", ref="REQ-002", crits=None):
    return {"finding_id": fid, "severity": sev, "basis": basis, "requirement_ref": ref,
            "location": "References section, whole list", "issue": "Reference list mixes APA and Harvard formats.",
            "why_it_matters": "The brief requires Harvard referencing throughout.",
            "how_to_improve": "Reformat every entry to Harvard author-date style consistently.",
            "affected_criterion_ids": crits or []}


def rubric_trail(tmp: Path) -> dict:
    (tmp / "brief.txt").write_text(BRIEF)
    (tmp / "rubric.txt").write_text(RUBRIC)
    files = [
        {"file_id": "FILE-001", "path": "INPUT/01_BRIEF_AND_TITLE/brief.txt", "folder_role": "brief",
         "detected_role": "BRIEF", "file_type": "Text", "extraction_status": "EXTRACTED", "analysed": True,
         "not_analysed_reason": None, "text_source": str(tmp / "brief.txt")},
        {"file_id": "FILE-002", "path": "INPUT/02_RUBRIC_AND_MARKING/rubric.txt", "folder_role": "rubric",
         "detected_role": "RUBRIC", "file_type": "Text", "extraction_status": "EXTRACTED", "analysed": True,
         "not_analysed_reason": None, "text_source": str(tmp / "rubric.txt")},
        {"file_id": "FILE-003", "path": "INPUT/04_COMPLETED_ASSIGNMENT/essay.docx", "folder_role": "submission",
         "detected_role": "SUBMISSION", "file_type": "DOCX", "extraction_status": "EXTRACTED", "analysed": True,
         "not_analysed_reason": None, "text_source": None},
    ]
    reqs = [
        ("REQ-001", "Essay of 1,500 words", "essay of 1,500 words", "WORD_COUNT", "MANDATORY"),
        ("REQ-002", "Use Harvard referencing", "You must use Harvard referencing", "CITATION_STYLE", "MANDATORY"),
        ("REQ-003", "Optional appendix", "You may include an appendix", "APPENDIX", "OPTIONAL"),
    ]
    t = {
        "INPUT_MANIFEST.json": {
            "agent": "AGENT_00_INPUT_INTEGRITY_CHECKER", "run_id": "test", "files": files,
            "missing_inputs": [], "duplicates": [], "unreadable_files": [], "conflicting_submissions": [],
            "rubric_present": True, "brief_present": True, "submission_present": True,
            "title_or_topic": {"value": "Renewable energy policy", "source": "FILE-001"},
            "analysis_mode": "RUBRIC", "mode_rationale": "Rubric with marks supplied.",
            "advisory_mode_overridden": False, "can_proceed": True, "blocking_reasons": []},
        "TASK_CLASSIFICATION.json": {
            "agent": "AGENT_01_TASK_CLASSIFIER", "task_type": "Academic Essay", "secondary_task_types": [],
            "discipline": "Energy policy", "confidence": "HIGH",
            "classification_evidence": [{"source": "FILE-001", "observation": "Write an essay"}],
            "deliverable_formats": ["DOCX"], "specialist_reviews_required": ["WRITTEN_WORK"],
            "coding_review_required": False, "statistical_review_required": False,
            "presentation_review_required": False, "numerical_marking_authorised": True,
            "numerical_marking_basis": "Criterion 1 (20 marks), Criterion 2 (30 marks)",
            "conventions_not_applicable": [{"convention": "Unit tests", "reason": "Essay"}]},
        "REQUIREMENT_REGISTER.json": {
            "agent": "AGENT_02_REQUIREMENT_EXTRACTION_SPECIALIST", "analysis_mode": "RUBRIC",
            "sources_read": [{"file_id": "FILE-001", "path": files[0]["path"], "fully_read": True}],
            "requirements": [{"id": i, "text": txt, "verbatim_quote": q,
                              "source": {"file_id": "FILE-001", "location": "para 1"}, "source_priority": 1,
                              "category": cat, "obligation": ob, "assessable_from_submission": True}
                             for i, txt, q, cat, ob in reqs],
            "conflicts": [], "not_provided": ["Minimum number of sources"]},
        "RUBRIC_MODEL.json": {
            "agent": "AGENT_03_RUBRIC_INTERPRETER", "rubric_status": "PROVIDED", "source_file_ids": ["FILE-002"],
            "marking_scale_type": "NUMERIC_MARKS", "numerical_marking_authorised": True,
            "authority_basis": "Criterion 1 Argument and analysis (20 marks)", "aggregation_method": "SUM",
            "total_available": 50,
            "grade_boundaries": [{"label": "Pass", "min": 40, "max": 100}, {"label": "Fail", "min": 0, "max": 39.99}],
            "criteria": [
                {"id": "CRIT-001", "name": "Argument", "description_verbatim": "Argument and analysis (20 marks)",
                 "max_marks": 20, "weight_percent": None, "descriptors": [
                     {"level_label": "Excellent", "mark_range_min": 14, "mark_range_max": 20,
                      "descriptor_text": "sustained critical analysis"},
                     {"level_label": "Good", "mark_range_min": 10, "mark_range_max": 13.9,
                      "descriptor_text": "some analysis"}]},
                {"id": "CRIT-002", "name": "Evidence", "description_verbatim": "Use of evidence (30 marks)",
                 "max_marks": 30, "weight_percent": None, "descriptors": [
                     {"level_label": "Excellent", "mark_range_min": 21, "mark_range_max": 30,
                      "descriptor_text": "sustained critical analysis"},
                     {"level_label": "Good", "mark_range_min": 15, "mark_range_max": 20.9,
                      "descriptor_text": "some analysis"}]}],
            "arithmetic_check": {"criteria_max_sum": 50, "criteria_weight_sum": None, "stated_total": 50,
                                 "consistent": True, "notes": "OK"},
            "interpretation_notes": ["Percentage bands converted to marks."], "ambiguities": []},
        "QUALITY_BLUEPRINT.json": {
            "agent": "AGENT_04_QUALITY_BLUEPRINT_ARCHITECT", "task_type": "Academic Essay",
            "structure_model": "Introduction, body, conclusion",
            "expectations": [
                {"id": "BP-001", "category": "MANDATORY_REQUIREMENT", "text": "1,500 words",
                 "source_ids": ["REQ-001"], "rationale": "Brief"},
                {"id": "BP-002", "category": "RUBRIC_DERIVED_EXPECTATION", "text": "Sustained analysis",
                 "source_ids": ["CRIT-001"], "rationale": "Top descriptor"},
                {"id": "BP-003", "category": "BEST_PRACTICE_RECOMMENDATION", "text": "Clear thesis statement",
                 "source_ids": ["TASK_TYPE_PROFILE"], "rationale": "Essay convention"}],
            "conventions_applied": ["Essay structure"],
            "conventions_explicitly_not_applied": [{"convention": "Dissertation chapters", "reason": "Essay"}]},
        "SUBMISSION_EVIDENCE_MAP.json": {
            "agent": "AGENT_05_SUBMISSION_EVIDENCE_MAPPER", "submission_file_ids": ["FILE-003"],
            "locations": [{"loc_id": "LOC-001", "file_id": "FILE-003", "location": "Whole essay",
                           "element_type": "SECTION", "summary": "Essay body"}],
            "metrics": {"word_count_estimate": 1490, "word_count_method": "text_stats.py words_before_references"},
            "requirement_links": [{"requirement_id": r[0], "loc_ids": ["LOC-001"], "evidence_summary": "x",
                                   "coverage": "FOUND"} for r in reqs],
            "criterion_links": [{"criterion_id": c, "loc_ids": ["LOC-001"], "evidence_summary": "x"}
                                for c in ("CRIT-001", "CRIT-002")],
            "unmapped_content": []},
        "PRIMARY_ASSESSMENT.json": {
            "agent": "AGENT_06_PRIMARY_QUALITY_ASSESSOR", "analysis_mode": "RUBRIC",
            "requirement_assessments": [
                {"requirement_id": r[0], "requirement_text": r[1], "status": "PASS" if r[0] != "REQ-002" else "PARTIAL",
                 "evidence_location": "Whole essay", "evidence_present": "x", "missing_content": "None.",
                 "weakness": "None.", "why_it_matters": "x", "improvement_action": "x",
                 "priority": "NONE" if r[0] != "REQ-002" else "MAJOR"} for r in reqs],
            "criterion_assessments": [
                {"criterion_id": "CRIT-001", "criterion": "Argument", "max_marks": 20, "rubric_descriptor": "some analysis",
                 "matched_descriptor_level": "Good", "evidence": "LOC-001", "strengths": ["a"], "weaknesses": ["b"],
                 "missing_evidence": [], "mark_range_considered": {"min": 10, "max": 13.9}, "provisional_mark": 12,
                 "justification": {"what_earned": "a", "what_prevented_higher": "b", "descriptor_support": "c"},
                 "confidence": "MEDIUM"},
                {"criterion_id": "CRIT-002", "criterion": "Evidence", "max_marks": 30, "rubric_descriptor": "sustained",
                 "matched_descriptor_level": "Excellent", "evidence": "LOC-001", "strengths": ["a"], "weaknesses": [],
                 "missing_evidence": [], "mark_range_considered": {"min": 21, "max": 30}, "provisional_mark": 22,
                 "justification": {"what_earned": "a", "what_prevented_higher": "b", "descriptor_support": "c"},
                 "confidence": "MEDIUM"}],
            "quality_dimensions": [], "findings": [finding("F6-001", crits=["CRIT-002"])],
            "strengths": ["Clear structure"], "overall_summary": "Sound essay."},
        "SPECIALIST_REVIEW.json": {
            "agent": "AGENT_07_SPECIALIST_TECHNICAL_REVIEWER", "reviews_activated": ["WRITTEN_WORK"],
            "reviews_not_activated": [{"review": "CODE", "reason": "Essay"}],
            "code_review": {"performed": False, "execution_performed": False, "execution_statement": "Not applicable",
                            "not_performed_reason": "Not required"},
            "data_review": {"performed": False, "not_performed_reason": "Not required"},
            "presentation_review": {"performed": False, "not_performed_reason": "Not required"},
            "written_review": {"performed": True, "summary": "ok"},
            "findings": [], "strengths": [], "limitations": []},
        "EVIDENCE_AUDIT.json": {
            "agent": "AGENT_08_REFERENCE_AND_EVIDENCE_AUDITOR", "applicable": True, "not_applicable_reason": None,
            "citation_style_required": "Harvard (REQ-002)", "citation_style_observed": "Mixed",
            "in_text_citation_count": 12, "reference_list_count": 10, "citations_without_reference": [],
            "references_without_citation": [], "formatting_issues": ["Mixed APA/Harvard"], "unsupported_claims": [],
            "source_requirement_checks": [], "external_verification_performed": False,
            "authenticity_statement": REFS, "findings": []},
        "COHERENCE_AUDIT.json": {
            "agent": "AGENT_09_COHERENCE_AND_SYNCHRONISATION_AUDITOR",
            "logical_chain_model": ["Question", "Thesis", "Conclusion"],
            "chain_links": [{"from": "Question", "to": "Thesis", "status": "ALIGNED", "evidence": "Intro"}],
            "contradictions": [], "repetition": [], "irrelevant_content": [], "unanswered_objectives": [],
            "unsupported_conclusions": [], "specification_implementation_mismatches": [],
            "methodology_results_mismatches": [], "findings": []},
        "SECOND_MARKER_REVIEW.json": {
            "agent": "AGENT_10_INDEPENDENT_SECOND_MARKER", "independence_statement": "Blind first.",
            "requirement_challenges": [{"requirement_id": "REQ-002", "primary_status": "PARTIAL",
                                        "second_status": "PARTIAL", "agree": True, "reason": "Agree"}],
            "criterion_challenges": [
                {"criterion_id": "CRIT-001", "primary_mark": 12, "second_mark": 12, "primary_level": "Good",
                 "second_level": "Good", "direction": "AGREE", "reason": "Agree", "evidence": "LOC-001"},
                {"criterion_id": "CRIT-002", "primary_mark": 22, "second_mark": 20, "primary_level": "Excellent",
                 "second_level": "Good", "direction": "OVER_MARKED", "reason": "Evidence thin", "evidence": "LOC-001"}],
            "missed_requirements": [], "unsupported_criticisms": [], "false_positives": [], "overlooked_strengths": [],
            "misinterpreted_descriptors": [], "improper_penalties": [], "findings": []},
        "FINAL_SCORE_MODEL.json": {
            "agent": "AGENT_11_SCORE_ADJUDICATOR", "applicable": True, "not_applicable_reason": None,
            "aggregation_method": "SUM",
            "criteria": [
                {"criterion_id": "CRIT-001", "max_marks": 20, "weight_percent": None, "primary_mark": 12,
                 "second_mark": 12, "disputed": False,
                 "resolution": {k: "ok" for k in ("rechecked_rubric_wording", "rechecked_requirements",
                                                  "rechecked_evidence", "rechecked_specialist_review", "reasoning")},
                 "final_mark": 12, "final_level": "Good", "descriptor_supporting": "some analysis",
                 "what_earned": "a", "what_prevented_higher": "b", "confidence": "MEDIUM"},
                {"criterion_id": "CRIT-002", "max_marks": 30, "weight_percent": None, "primary_mark": 22,
                 "second_mark": 20, "disputed": True,
                 "resolution": {k: "checked" for k in ("rechecked_rubric_wording", "rechecked_requirements",
                                                       "rechecked_evidence", "rechecked_specialist_review", "reasoning")},
                 "final_mark": 20, "final_level": "Good", "descriptor_supporting": "some analysis",
                 "what_earned": "a", "what_prevented_higher": "b", "confidence": "MEDIUM"}],
            "total": {"total_score": 32, "total_available": 50, "percentage": 64.0, "grade_band": "Pass",
                      "computed_by": "compute_scores.py"},
            "verification_reconciled": False},
        "VERIFIED_FINDINGS.json": {
            "agent": "AGENT_12_CRITICAL_FINDINGS_VERIFIER",
            "findings": [{"finding_id": "F6-001", "source_agent": "AGENT_06", "original_severity": "MAJOR",
                          "verification": {"requirement_real": True, "requirement_source_checked": "Brief para 1",
                                           "evidence_accurate": True, "location_correct": True, "proportionate": True,
                                           "instruction_understood": True, "false_positive": False, "notes": "ok"},
                          "outcome": "CONFIRMED", "final_severity": "MAJOR",
                          "final_text": {"location": "References", "issue": "Mixed styles", "requirement_ref": "REQ-002",
                                         "why_it_matters": "x", "how_to_improve": "y"},
                          "affected_criterion_ids": ["CRIT-002"]}],
            "requires_score_readjudication": [],
            "summary": {"checked": 1, "confirmed": 1, "corrected": 0, "downgraded": 0, "removed": 0}},
    }
    qa = {"agent": "AGENT_13_FINAL_QA_CONTROLLER", "qa_status": "PASS", "iteration": 1,
          "checks": [{"check_id": f"QA-{i:02d}", "description": "x", "result": "PASS", "details": "ok"} for i in range(1, 15)],
          "deterministic_validation": {"validator_run": True, "validator_passed": True,
                                       "report_path": "OUTPUT/audit_trail/VALIDATION_REPORT.json"},
          "failures": [], "release_authorised": True}
    t["QA_STATUS.json"] = qa
    return t


def report_md(trail: dict) -> str:
    rub = trail["RUBRIC_MODEL.json"]
    auth = rub["numerical_marking_authorised"]
    from common import REPORT_SECTIONS  # type: ignore
    body = {n: "Content." for n, _ in REPORT_SECTIONS}
    body[4] = "FILE-001, FILE-002, FILE-003"
    body[5] = "None."
    if auth:
        tot = trail["FINAL_SCORE_MODEL.json"]["total"]
        body[7] = f"**Total: {tot['total_score']} / {tot['total_available']} ({tot['percentage']}%)**"
        body[8] = " | ".join(c["criterion_id"] for c in trail["FINAL_SCORE_MODEL.json"]["criteria"])
    else:
        body[7] = NO_SCHEME
        body[8] = "NOT APPLICABLE — no authorised numerical marking scheme."
    body[9] = " ".join(r["id"] for r in trail["REQUIREMENT_REGISTER.json"]["requirements"])
    body[11] = " ".join(v["finding_id"] for v in trail["VERIFIED_FINDINGS.json"]["findings"]
                        if v["outcome"] != "REMOVED")
    body[18] = REFS
    body[20] = "NOT APPLICABLE — essay."
    return "# Final Quality Audit\n\n" + "\n\n".join(f"## {n}. {t}\n\n{body[n]}" for n, t in REPORT_SECTIONS) + "\n"


def brief_trail(tmp: Path) -> dict:
    t = rubric_trail(tmp)
    m = t["INPUT_MANIFEST.json"]
    m["analysis_mode"] = "BRIEF_ONLY"
    m["rubric_present"] = False
    m["files"] = [f for f in m["files"] if f["file_id"] != "FILE-002"]
    t["TASK_CLASSIFICATION.json"]["numerical_marking_authorised"] = False
    t["TASK_CLASSIFICATION.json"]["numerical_marking_basis"] = NO_SCHEME
    t["REQUIREMENT_REGISTER.json"]["analysis_mode"] = "BRIEF_ONLY"
    t["RUBRIC_MODEL.json"] = {
        "agent": "AGENT_03_RUBRIC_INTERPRETER", "rubric_status": "NOT PROVIDED", "source_file_ids": [],
        "marking_scale_type": "NONE", "numerical_marking_authorised": False, "authority_basis": NO_SCHEME,
        "aggregation_method": "NONE", "total_available": None, "grade_boundaries": [], "criteria": [],
        "arithmetic_check": {"criteria_max_sum": None, "criteria_weight_sum": None, "stated_total": None,
                             "consistent": True, "notes": "No rubric."},
        "interpretation_notes": [], "ambiguities": []}
    t["QUALITY_BLUEPRINT.json"]["expectations"] = [e for e in t["QUALITY_BLUEPRINT.json"]["expectations"]
                                                   if e["category"] != "RUBRIC_DERIVED_EXPECTATION"]
    t["SUBMISSION_EVIDENCE_MAP.json"]["criterion_links"] = []
    pa = t["PRIMARY_ASSESSMENT.json"]
    pa["analysis_mode"] = "BRIEF_ONLY"
    pa["criterion_assessments"] = []
    pa["findings"][0]["affected_criterion_ids"] = []
    t["SECOND_MARKER_REVIEW.json"]["criterion_challenges"] = []
    t["FINAL_SCORE_MODEL.json"] = {
        "agent": "AGENT_11_SCORE_ADJUDICATOR", "applicable": False, "not_applicable_reason": NO_SCHEME,
        "aggregation_method": "NONE", "criteria": [],
        "total": {"total_score": None, "total_available": None, "percentage": None, "grade_band": "NOT APPLICABLE",
                  "computed_by": "compute_scores.py"}, "verification_reconciled": True}
    t["VERIFIED_FINDINGS.json"]["findings"][0]["affected_criterion_ids"] = []
    return t


def write(trail: dict, trail_dir: Path, report: str | None = None) -> None:
    trail_dir.mkdir(parents=True, exist_ok=True)
    for name, doc in trail.items():
        (trail_dir / name).write_text(json.dumps(doc, indent=2))
    if report is not None:
        (trail_dir.parent / "_work").mkdir(parents=True, exist_ok=True)
        (trail_dir.parent / "_work" / "FINAL_QUALITY_AUDIT.draft.md").write_text(report)


def clone(trail: dict) -> dict:
    return copy.deepcopy(trail)

#!/usr/bin/env python3
"""Generates SYSTEM/SCHEMAS/*.schema.json from one source of truth.

Maintainers: edit this file, run `python3 SYSTEM/TOOLS/build_schemas.py`, commit
both. The unit tests fail if the committed schemas are out of date.
Schemas use a JSON-Schema (draft-07) subset understood by validate.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SCHEMA_DIR  # noqa: E402

MODES = ["RUBRIC", "BRIEF_ONLY", "TITLE_TOPIC", "CANNOT_PROCEED"]
SEVERITY = ["CRITICAL", "MAJOR", "MODERATE", "MINOR"]
REQ_STATUS = ["PASS", "PARTIAL", "WEAK", "MISSING", "NOT APPLICABLE", "CANNOT VERIFY"]
CONF = ["HIGH", "MEDIUM", "LOW"]
TASK_TYPES = [
    "Academic Essay", "Dissertation / Thesis", "Research Report", "Literature Review",
    "Business / Management Report", "Case Study", "Reflective Assignment",
    "Scientific / Laboratory Report", "Technical Report", "Coding / Software Project",
    "Data Analysis / Statistics", "Presentation", "Project Documentation", "Mixed Assignment", "Other",
]
SPECIALIST = ["CODE", "DATA_STATISTICS", "PRESENTATION", "WRITTEN_WORK", "RESEARCH_METHODS",
              "SCIENTIFIC_LAB", "BUSINESS_ANALYSIS", "REFLECTIVE_PRACTICE", "TECHNICAL_DOCUMENTATION"]
REQ_CATEGORIES = [
    "TITLE", "TASK", "PURPOSE", "AIM", "OBJECTIVE", "RESEARCH_QUESTION", "LEARNING_OUTCOME",
    "WORD_COUNT", "STRUCTURE", "CONTENT", "RESEARCH", "METHODOLOGY", "THEORY", "SOURCES",
    "SOURCE_DATE", "CITATION_STYLE", "CALCULATION", "DATASET", "STATISTICS", "SOFTWARE",
    "PROGRAMMING", "ALGORITHM", "TESTING", "SCREENSHOTS", "DIAGRAMS_TABLES_FIGURES", "APPENDIX",
    "REFLECTION", "RECOMMENDATIONS", "PRESENTATION", "SLIDES", "TIMING", "TECHNICAL_SPEC",
    "FORMATTING", "SUBMISSION", "PENALTY", "OTHER",
]


def s(t, **kw):
    d = {"type": t}
    d.update(kw)
    return d


STR = s("string")
NSTR = s(["string", "null"])
BOOL = s("boolean")
NUM = s("number")
NNUM = s(["number", "null"])
INT = s("integer")


def arr(items, **kw):
    return s("array", items=items, **kw)


def enum(values, nullable=False):
    return {"type": ["string", "null"] if nullable else "string", "enum": values + ([None] if nullable else [])}


def obj(required: dict, optional: dict | None = None, **kw):
    props = dict(required)
    props.update(optional or {})
    return s("object", properties=props, required=list(required), **kw)


def pat(p, nullable=False):
    return {"type": ["string", "null"] if nullable else "string", "pattern": p}


FILE_ID = pat(r"^FILE-\d{3,}$")
REQ_ID = pat(r"^REQ-\d{3,}$")
CRIT_ID = pat(r"^CRIT-\d{3,}$")
FINDING_ID = pat(r"^F(6|7|8|9|10)-\d{3,}$")

FINDING = obj(
    {
        "finding_id": FINDING_ID,
        "severity": enum(SEVERITY),
        "basis": enum(["MANDATORY_REQUIREMENT", "RUBRIC_CRITERION", "BEST_PRACTICE"]),
        "requirement_ref": STR,  # REQ-xxx / CRIT-xxx / BP-xxx / "BEST PRACTICE"
        "location": STR,
        "issue": STR,
        "why_it_matters": STR,
        "how_to_improve": STR,
    },
    {
        "evidence_quote": NSTR,
        "affected_criterion_ids": arr(CRIT_ID),
        "category": STR,
    },
)


def agent_doc(agent: str, required: dict, optional: dict | None = None, title: str = ""):
    req = {"agent": {"type": "string", "const": agent}}
    req.update(required)
    schema = obj(req, optional)
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["title"] = title
    return schema


SCHEMAS = {}

SCHEMAS["input_manifest"] = agent_doc("AGENT_00_INPUT_INTEGRITY_CHECKER", {
    "run_id": STR,
    "files": arr(obj({
        "file_id": FILE_ID, "path": STR,
        "folder_role": enum(["brief", "rubric", "additional_instructions", "submission", "supporting", "misplaced"]),
        "detected_role": enum(["BRIEF", "TITLE_ONLY", "RUBRIC", "ADDITIONAL_INSTRUCTIONS", "LEARNING_OUTCOMES",
                               "SUBMISSION", "SUBMISSION_COMPONENT", "SUPPORTING", "DUPLICATE", "UNKNOWN"]),
        "file_type": STR,
        "extraction_status": enum(["EXTRACTED", "READ_BY_CLAUDE", "PARTIAL", "FAILED", "UNSUPPORTED", "EMPTY",
                                   "SKIPPED_DUPLICATE"]),
        "analysed": BOOL,
        "not_analysed_reason": NSTR,
    }, {"text_source": NSTR, "notes": STR, "parent_archive": NSTR})),
    "missing_inputs": arr(obj({"item": STR, "impact": STR})),
    "duplicates": arr(obj({"file_ids": arr(FILE_ID), "handling": STR})),
    "unreadable_files": arr(obj({"file_id": FILE_ID, "reason": STR})),
    "conflicting_submissions": arr(obj({"file_ids": arr(FILE_ID), "resolution": STR})),
    "rubric_present": BOOL, "brief_present": BOOL, "submission_present": BOOL,
    "title_or_topic": obj({"value": NSTR, "source": NSTR}),
    "analysis_mode": enum(MODES),
    "mode_rationale": STR,
    "advisory_mode_overridden": BOOL,
    "can_proceed": BOOL,
    "blocking_reasons": arr(STR),
}, {"early_conflicts": arr(STR), "misplaced_items": arr(STR)}, "Input manifest")

SCHEMAS["task_classification"] = agent_doc("AGENT_01_TASK_CLASSIFIER", {
    "task_type": enum(TASK_TYPES),
    "secondary_task_types": arr(enum(TASK_TYPES)),
    "discipline": STR,  # or "CANNOT VERIFY FROM PROVIDED MATERIAL."
    "confidence": enum(CONF),
    "classification_evidence": arr(obj({"source": STR, "observation": STR}), minItems=1),
    "deliverable_formats": arr(STR),
    "specialist_reviews_required": arr(enum(SPECIALIST)),
    "coding_review_required": BOOL,
    "statistical_review_required": BOOL,
    "presentation_review_required": BOOL,
    "numerical_marking_authorised": BOOL,
    "numerical_marking_basis": STR,
    "conventions_not_applicable": arr(obj({"convention": STR, "reason": STR})),
}, {"notes": STR}, "Task classification")

SCHEMAS["requirement_register"] = agent_doc("AGENT_02_REQUIREMENT_EXTRACTION_SPECIALIST", {
    "analysis_mode": enum(MODES),
    "sources_read": arr(obj({"file_id": FILE_ID, "path": STR, "fully_read": BOOL}, {"notes": STR})),
    "requirements": arr(obj({
        "id": REQ_ID,
        "text": STR,
        "verbatim_quote": STR,
        "source": obj({"file_id": FILE_ID, "location": STR}),
        "source_priority": s("integer", minimum=1, maximum=7),
        "category": enum(REQ_CATEGORIES),
        "obligation": enum(["MANDATORY", "OPTIONAL", "RECOMMENDED", "PROHIBITION"]),
        "assessable_from_submission": BOOL,
    }, {"notes": STR, "linked_criterion_ids": arr(CRIT_ID)})),
    "conflicts": arr(obj({
        "id": pat(r"^CONF-\d{3,}$"), "description": STR, "requirement_ids": arr(REQ_ID),
        "sources": arr(STR), "higher_priority_source": STR, "handling": STR,
    })),
    "not_provided": arr(STR),
}, {"ambiguities": arr(obj({"requirement_id": REQ_ID, "issue": STR})), "notes": STR}, "Requirement register")

SCHEMAS["rubric_model"] = agent_doc("AGENT_03_RUBRIC_INTERPRETER", {
    "rubric_status": enum(["PROVIDED", "NOT PROVIDED", "PROVIDED_UNUSABLE"]),
    "source_file_ids": arr(FILE_ID),
    "marking_scale_type": enum(["NUMERIC_MARKS", "PERCENTAGE_WEIGHTED", "BANDS_ONLY", "NONE"]),
    "numerical_marking_authorised": BOOL,
    "authority_basis": STR,
    "aggregation_method": enum(["SUM", "WEIGHTED_PERCENT", "NONE"]),
    "total_available": NNUM,
    "grade_boundaries": arr(obj({"label": STR, "min": NNUM, "max": NNUM}, {"source": STR})),
    "criteria": arr(obj({
        "id": CRIT_ID, "name": STR, "description_verbatim": STR,
        "max_marks": NNUM, "weight_percent": NNUM,
        "descriptors": arr(obj({"level_label": STR, "mark_range_min": NNUM, "mark_range_max": NNUM,
                                "descriptor_text": STR})),
    }, {"linked_learning_outcomes": arr(STR), "linked_requirement_ids": arr(REQ_ID), "notes": STR})),
    "arithmetic_check": obj({"criteria_max_sum": NNUM, "criteria_weight_sum": NNUM,
                             "stated_total": NNUM, "consistent": BOOL, "notes": STR}),
    "interpretation_notes": arr(STR),
    "ambiguities": arr(STR),
}, {}, "Rubric model")

SCHEMAS["quality_blueprint"] = agent_doc("AGENT_04_QUALITY_BLUEPRINT_ARCHITECT", {
    "task_type": enum(TASK_TYPES),
    "structure_model": STR,
    "expectations": arr(obj({
        "id": pat(r"^BP-\d{3,}$"),
        "category": enum(["MANDATORY_REQUIREMENT", "RUBRIC_DERIVED_EXPECTATION", "BEST_PRACTICE_RECOMMENDATION"]),
        "text": STR,
        "source_ids": arr(STR),
        "rationale": STR,
    }, {"applies_to": STR})),
    "conventions_applied": arr(STR),
    "conventions_explicitly_not_applied": arr(obj({"convention": STR, "reason": STR})),
}, {"notes": STR}, "Quality blueprint")

COVERAGE = ["FOUND", "PARTIALLY_FOUND", "NOT_FOUND", "NOT_ASSESSABLE"]
SCHEMAS["submission_evidence_map"] = agent_doc("AGENT_05_SUBMISSION_EVIDENCE_MAPPER", {
    "submission_file_ids": arr(FILE_ID, minItems=1),
    "locations": arr(obj({
        "loc_id": pat(r"^LOC-\d{3,}$"), "file_id": FILE_ID, "location": STR,
        "element_type": enum(["TITLE", "HEADING", "SECTION", "PARAGRAPH", "ARGUMENT", "CLAIM", "CITATION",
                              "REFERENCE_LIST", "TABLE", "FIGURE", "CALCULATION", "CODE_FILE", "FUNCTION",
                              "CLASS", "MODULE", "TEST", "SLIDE", "DATASET", "OUTPUT", "APPENDIX",
                              "METHODOLOGY", "RESULTS", "DISCUSSION", "CONCLUSION", "RECOMMENDATIONS", "OTHER"]),
        "summary": STR,
    }, {"heading": STR})),
    "metrics": obj({"word_count_estimate": NNUM, "word_count_method": STR}, {
        "pages": NNUM, "slides": NNUM, "code_files": NNUM, "reference_entries": NNUM,
        "in_text_citations": NNUM, "tables": NNUM, "figures": NNUM, "tests": NNUM}),
    "requirement_links": arr(obj({
        "requirement_id": REQ_ID, "loc_ids": arr(STR), "evidence_summary": STR, "coverage": enum(COVERAGE),
    })),
    "criterion_links": arr(obj({"criterion_id": CRIT_ID, "loc_ids": arr(STR), "evidence_summary": STR})),
    "unmapped_content": arr(STR),
}, {"notes": STR}, "Submission evidence map")

JUSTIFICATION = obj({"what_earned": STR, "what_prevented_higher": STR, "descriptor_support": STR})
SCHEMAS["primary_assessment"] = agent_doc("AGENT_06_PRIMARY_QUALITY_ASSESSOR", {
    "analysis_mode": enum(MODES),
    "requirement_assessments": arr(obj({
        "requirement_id": REQ_ID, "requirement_text": STR, "status": enum(REQ_STATUS),
        "evidence_location": STR, "evidence_present": STR, "missing_content": STR,
        "weakness": STR, "why_it_matters": STR, "improvement_action": STR,
        "priority": enum(SEVERITY + ["NONE"]),
    })),
    "criterion_assessments": arr(obj({
        "criterion_id": CRIT_ID, "criterion": STR, "max_marks": NNUM, "rubric_descriptor": STR,
        "matched_descriptor_level": STR, "evidence": STR,
        "strengths": arr(STR), "weaknesses": arr(STR), "missing_evidence": arr(STR),
        "mark_range_considered": obj({"min": NNUM, "max": NNUM}),
        "provisional_mark": NNUM, "justification": JUSTIFICATION, "confidence": enum(CONF),
    })),
    "quality_dimensions": arr(obj({
        "dimension": STR, "basis": enum(["KNOWN_REQUIREMENT", "BEST_PRACTICE"]),
        "rating": enum(["STRONG", "ADEQUATE", "WEAK", "INADEQUATE", "CANNOT VERIFY"]),
        "evidence": STR, "improvement_action": STR,
    })),
    "findings": arr(FINDING),
    "strengths": arr(STR),
    "overall_summary": STR,
}, {}, "Primary assessment")

SUB_REVIEW = obj({"performed": BOOL}, {"not_performed_reason": NSTR, "summary": STR, "checks": arr(obj(
    {"aspect": STR, "result": STR}, {"location": STR}))})
SCHEMAS["specialist_review"] = agent_doc("AGENT_07_SPECIALIST_TECHNICAL_REVIEWER", {
    "reviews_activated": arr(enum(SPECIALIST)),
    "reviews_not_activated": arr(obj({"review": enum(SPECIALIST), "reason": STR})),
    "code_review": obj({"performed": BOOL, "execution_performed": BOOL, "execution_statement": STR}, {
        "not_performed_reason": NSTR, "files_reviewed": arr(STR),
        "static_checks_run": arr(obj({"command": STR, "result": STR})),
        "summary": STR, "checks": arr(obj({"aspect": STR, "result": STR}, {"location": STR}))}),
    "data_review": SUB_REVIEW,
    "presentation_review": SUB_REVIEW,
    "written_review": SUB_REVIEW,
    "findings": arr(FINDING),
    "strengths": arr(STR),
    "limitations": arr(STR),
}, {}, "Specialist technical review")

SCHEMAS["evidence_audit"] = agent_doc("AGENT_08_REFERENCE_AND_EVIDENCE_AUDITOR", {
    "applicable": BOOL,
    "not_applicable_reason": NSTR,
    "citation_style_required": STR,
    "citation_style_observed": STR,
    "in_text_citation_count": NNUM,
    "reference_list_count": NNUM,
    "citations_without_reference": arr(STR),
    "references_without_citation": arr(STR),
    "formatting_issues": arr(STR),
    "unsupported_claims": arr(obj({"location": STR, "claim": STR, "issue": STR})),
    "source_requirement_checks": arr(obj({"requirement_id": REQ_ID, "result": STR})),
    "external_verification_performed": BOOL,
    "authenticity_statement": STR,
    "findings": arr(FINDING),
}, {"strengths": arr(STR)}, "Evidence & reference audit")

SCHEMAS["coherence_audit"] = agent_doc("AGENT_09_COHERENCE_AND_SYNCHRONISATION_AUDITOR", {
    "logical_chain_model": arr(STR, minItems=2),
    "chain_links": arr(obj({
        "from": STR, "to": STR,
        "status": enum(["ALIGNED", "PARTIAL", "BROKEN", "NOT APPLICABLE", "CANNOT VERIFY"]),
        "evidence": STR,
    }, {"issue": STR})),
    "contradictions": arr(obj({"locations": arr(STR), "description": STR})),
    "repetition": arr(STR),
    "irrelevant_content": arr(STR),
    "unanswered_objectives": arr(STR),
    "unsupported_conclusions": arr(STR),
    "specification_implementation_mismatches": arr(STR),
    "methodology_results_mismatches": arr(STR),
    "findings": arr(FINDING),
}, {"weak_transitions": arr(STR), "strengths": arr(STR)}, "Coherence audit")

SCHEMAS["second_marker_review"] = agent_doc("AGENT_10_INDEPENDENT_SECOND_MARKER", {
    "independence_statement": STR,
    "requirement_challenges": arr(obj({
        "requirement_id": REQ_ID, "primary_status": enum(REQ_STATUS), "second_status": enum(REQ_STATUS),
        "agree": BOOL, "reason": STR,
    }, {"evidence_location": STR})),
    "criterion_challenges": arr(obj({
        "criterion_id": CRIT_ID, "primary_mark": NNUM, "second_mark": NNUM,
        "primary_level": STR, "second_level": STR,
        "direction": enum(["AGREE", "OVER_MARKED", "UNDER_MARKED"]), "reason": STR, "evidence": STR,
    })),
    "missed_requirements": arr(STR),
    "unsupported_criticisms": arr(obj({"finding_id": FINDING_ID, "reason": STR})),
    "false_positives": arr(obj({"finding_id": FINDING_ID, "reason": STR})),
    "overlooked_strengths": arr(STR),
    "misinterpreted_descriptors": arr(STR),
    "improper_penalties": arr(STR),
    "findings": arr(FINDING),
}, {"summary": STR}, "Second marker review")

SCHEMAS["final_score_model"] = agent_doc("AGENT_11_SCORE_ADJUDICATOR", {
    "applicable": BOOL,
    "not_applicable_reason": NSTR,
    "aggregation_method": enum(["SUM", "WEIGHTED_PERCENT", "NONE"]),
    "criteria": arr(obj({
        "criterion_id": CRIT_ID, "max_marks": NNUM, "weight_percent": NNUM,
        "primary_mark": NNUM, "second_mark": NNUM, "disputed": BOOL,
        "resolution": obj({"rechecked_rubric_wording": STR, "rechecked_requirements": STR,
                           "rechecked_evidence": STR, "rechecked_specialist_review": STR, "reasoning": STR}),
        "final_mark": NNUM, "final_level": STR, "descriptor_supporting": STR,
        "what_earned": STR, "what_prevented_higher": STR, "confidence": enum(CONF),
    }, {"weighted_contribution": NNUM})),
    "total": obj({"total_score": NNUM, "total_available": NNUM, "percentage": NNUM,
                  "grade_band": STR, "computed_by": STR}),
    "verification_reconciled": BOOL,
}, {"calculation_log": arr(STR), "notes": STR}, "Final score model")

SCHEMAS["verified_findings"] = agent_doc("AGENT_12_CRITICAL_FINDINGS_VERIFIER", {
    "findings": arr(obj({
        "finding_id": FINDING_ID,
        "source_agent": STR,
        "original_severity": enum(SEVERITY),
        "verification": obj({
            "requirement_real": BOOL, "requirement_source_checked": STR,
            "evidence_accurate": BOOL, "location_correct": BOOL, "proportionate": BOOL,
            "instruction_understood": BOOL, "false_positive": BOOL, "notes": STR,
        }),
        "outcome": enum(["CONFIRMED", "CORRECTED", "DOWNGRADED", "REMOVED"]),
        "final_severity": enum(SEVERITY, nullable=True),
        "final_text": obj({"location": STR, "issue": STR, "requirement_ref": STR,
                           "why_it_matters": STR, "how_to_improve": STR}),
    }, {"affected_criterion_ids": arr(CRIT_ID)})),
    "requires_score_readjudication": arr(CRIT_ID),
    "summary": obj({"checked": INT, "confirmed": INT, "corrected": INT, "downgraded": INT, "removed": INT}),
}, {}, "Verified findings")

QA_IDS = [f"QA-{i:02d}" for i in range(1, 15)]
SCHEMAS["qa_status"] = agent_doc("AGENT_13_FINAL_QA_CONTROLLER", {
    "qa_status": enum(["PASS", "FAIL"]),
    "iteration": s("integer", minimum=1),
    "checks": arr(obj({"check_id": {"type": "string", "enum": QA_IDS}, "description": STR,
                       "result": enum(["PASS", "FAIL", "NOT APPLICABLE"]), "details": STR}),
                  minItems=len(QA_IDS)),
    "deterministic_validation": obj({"validator_run": BOOL, "validator_passed": BOOL, "report_path": STR}),
    "failures": arr(obj({"check_id": STR, "stage_to_rerun": STR, "correction_required": STR})),
    "release_authorised": BOOL,
}, {"notes": STR}, "QA status")

QA_CHECKS = {
    "QA-01": "Every relevant source document was considered (manifest vs sources_read).",
    "QA-02": "All explicit requirements were extracted (spot-check source documents against register).",
    "QA-03": "Every requirement was assessed (register vs primary assessment).",
    "QA-04": "Rubric interpretation is faithful (no stricter/looser wording, no invented criteria).",
    "QA-05": "Numerical scoring appears only where authorised.",
    "QA-06": "Score calculations are correct and reconcile (compute_scores.py / validate.py).",
    "QA-07": "All CRITICAL and MAJOR findings were independently verified.",
    "QA-08": "No contradictory recommendations remain.",
    "QA-09": "No invented requirement appears (every REQ traces to a quoted source).",
    "QA-10": "Limitations and unanalysed files are disclosed.",
    "QA-11": "Technical claims are appropriately qualified (execution / reference verification statements).",
    "QA-12": "Employee-facing feedback is actionable (location, issue, requirement, why, how).",
    "QA-13": "Best practice is not presented as mandatory and task-inappropriate conventions are not applied.",
    "QA-14": "Draft report contains all required sections and agrees with the audit trail.",
}


def main(check_only: bool = False) -> int:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    stale = []
    for name, schema in SCHEMAS.items():
        path = SCHEMA_DIR / f"{name}.schema.json"
        text = json.dumps(schema, indent=2) + "\n"
        if check_only:
            if not path.exists() or path.read_text() != text:
                stale.append(path.name)
        else:
            path.write_text(text)
    qa_path = SCHEMA_DIR / "qa_checklist.json"
    qa_text = json.dumps(QA_CHECKS, indent=2) + "\n"
    if check_only:
        if not qa_path.exists() or qa_path.read_text() != qa_text:
            stale.append(qa_path.name)
        if stale:
            print("Stale schemas: " + ", ".join(stale))
            return 1
        print("Schemas up to date.")
        return 0
    qa_path.write_text(qa_text)
    print(f"Wrote {len(SCHEMAS) + 1} schema files to SYSTEM/SCHEMAS/")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))

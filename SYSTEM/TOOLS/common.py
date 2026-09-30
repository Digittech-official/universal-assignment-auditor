"""Shared paths and constants for the Universal Assignment Auditor tools.

All paths are resolved relative to the repository root so the tools work on
any machine after `git clone`. Standard library only.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SYSTEM_DIR = REPO_ROOT / "SYSTEM"
SCHEMA_DIR = SYSTEM_DIR / "SCHEMAS"
TESTS_DIR = SYSTEM_DIR / "TESTS"
FIXTURES_DIR = TESTS_DIR / "fixtures"


def _dir_from_env(var: str, default: Path) -> Path:
    value = os.environ.get(var)
    return Path(value).resolve() if value else default


# INPUT/OUTPUT can be redirected (used by the test-suite); employees never need to.
INPUT_DIR = _dir_from_env("UAA_INPUT_DIR", REPO_ROOT / "INPUT")
OUTPUT_DIR = _dir_from_env("UAA_OUTPUT_DIR", REPO_ROOT / "OUTPUT")
AUDIT_DIR = OUTPUT_DIR / "audit_trail"
WORK_DIR = OUTPUT_DIR / "_work"
EXTRACTED_DIR = WORK_DIR / "extracted"
DRAFT_REPORT = WORK_DIR / "FINAL_QUALITY_AUDIT.draft.md"
FINAL_REPORT_MD = OUTPUT_DIR / "FINAL_QUALITY_AUDIT.md"
FINAL_REPORT_HTML = OUTPUT_DIR / "FINAL_QUALITY_AUDIT.html"
BLOCKED_REPORT = OUTPUT_DIR / "AUDIT_BLOCKED.md"

INPUT_FOLDERS = {
    "01_BRIEF_AND_TITLE": "brief",
    "02_RUBRIC_AND_MARKING": "rubric",
    "03_ADDITIONAL_INSTRUCTIONS": "additional_instructions",
    "04_COMPLETED_ASSIGNMENT": "submission",
    "05_SUPPORTING_FILES": "supporting",
}

PLACEHOLDER_NAMES = {".gitkeep", ".DS_Store", "Thumbs.db", "desktop.ini"}

# Audit-trail artefacts in pipeline order: (filename, schema, producing agent)
TRAIL = [
    ("INPUT_MANIFEST.json", "input_manifest", "AGENT_00"),
    ("TASK_CLASSIFICATION.json", "task_classification", "AGENT_01"),
    ("REQUIREMENT_REGISTER.json", "requirement_register", "AGENT_02"),
    ("RUBRIC_MODEL.json", "rubric_model", "AGENT_03"),
    ("QUALITY_BLUEPRINT.json", "quality_blueprint", "AGENT_04"),
    ("SUBMISSION_EVIDENCE_MAP.json", "submission_evidence_map", "AGENT_05"),
    ("PRIMARY_ASSESSMENT.json", "primary_assessment", "AGENT_06"),
    ("SPECIALIST_REVIEW.json", "specialist_review", "AGENT_07"),
    ("EVIDENCE_AUDIT.json", "evidence_audit", "AGENT_08"),
    ("COHERENCE_AUDIT.json", "coherence_audit", "AGENT_09"),
    ("SECOND_MARKER_REVIEW.json", "second_marker_review", "AGENT_10"),
    ("FINAL_SCORE_MODEL.json", "final_score_model", "AGENT_11"),
    ("VERIFIED_FINDINGS.json", "verified_findings", "AGENT_12"),
    ("QA_STATUS.json", "qa_status", "AGENT_13"),
]
TRAIL_FILES = {name: schema for name, schema, _ in TRAIL}

# Fixed policy phrases (must appear verbatim where applicable).
PHRASE_NO_SCHEME = "NO AUTHORISED NUMERICAL MARKING SCHEME WAS PROVIDED."
PHRASE_NOT_PROVIDED = "NOT PROVIDED"
PHRASE_CANNOT_VERIFY = "CANNOT VERIFY FROM PROVIDED MATERIAL."
PHRASE_UNREADABLE = "FILE COULD NOT BE RELIABLY ANALYSED."
PHRASE_STATIC_CODE = "CODE WAS REVIEWED STATICALLY; EXECUTION WAS NOT VERIFIED."
PHRASE_REFS_UNVERIFIED = "REFERENCE AUTHENTICITY WAS NOT EXTERNALLY VERIFIED."


def load_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def rel(path: Path) -> str:
    """Repository-relative POSIX path (never an absolute machine path)."""
    path = Path(path).resolve()
    for base in (REPO_ROOT, INPUT_DIR.parent, OUTPUT_DIR.parent):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.name

# Required sections of OUTPUT/FINAL_QUALITY_AUDIT.md, in order: (number, heading).
# Conditional sections must still appear, stating "NOT APPLICABLE — <reason>".
REPORT_SECTIONS = [
    (1, "Assignment Identification"),
    (2, "Task Type"),
    (3, "Analysis Mode"),
    (4, "Files Analysed"),
    (5, "Files Not Analysed and Reasons"),
    (6, "Executive Quality Summary"),
    (7, "Numerical Mark"),
    (8, "Marking Breakdown"),
    (9, "Requirement Compliance Matrix"),
    (10, "Critical Issues"),
    (11, "Major Issues"),
    (12, "Moderate Improvements"),
    (13, "Minor Improvements"),
    (14, "Passed Requirements"),
    (15, "Section-by-Section Review"),
    (16, "Content and Analysis Review"),
    (17, "Structure and Coherence Review"),
    (18, "Evidence and Referencing Review"),
    (19, "Technical Review"),
    (20, "Coding Review"),
    (21, "Data and Statistical Review"),
    (22, "Presentation Review"),
    (23, "Revision Priority Plan"),
    (24, "Quality Improvement Map"),
    (25, "Final Pre-Submission Checklist"),
    (26, "Audit Limitations"),
]

"""Validator rule tests: a valid trail passes; each targeted defect is caught by the right rule."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "TOOLS"))
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402
import validate  # noqa: E402
import trail_factory as TF  # noqa: E402

ALL = [n for n, _, _ in C.TRAIL]


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.trail_dir = self.tmp / "OUTPUT" / "audit_trail"

    def tearDown(self):
        self._tmp.cleanup()

    def run_trail(self, trail, report=True, report_text=None):
        text = report_text if report_text is not None else (TF.report_md(trail) if report else None)
        TF.write(trail, self.trail_dir, text)
        return validate.run(self.trail_dir, ALL, report, self.trail_dir.parent / "_work" / "FINAL_QUALITY_AUDIT.draft.md",
                            self.tmp / "none.json")

    def assertRule(self, result, rule, fragment=""):
        hits = [e for e in result["errors"] if e["rule"] == rule and fragment.lower() in e["message"].lower()]
        self.assertTrue(hits, f"expected {rule} error containing {fragment!r}; got {json.dumps(result['errors'], indent=1)}")

    # ---------------------------------------------------------------- baselines
    def test_valid_rubric_trail_passes(self):
        res = self.run_trail(TF.rubric_trail(self.tmp))
        self.assertTrue(res["passed"], res["errors"])

    def test_valid_brief_only_trail_passes(self):
        res = self.run_trail(TF.brief_trail(self.tmp))
        self.assertTrue(res["passed"], res["errors"])

    # ---------------------------------------------------------------- invented scores
    def test_mark_in_brief_only_mode_rejected(self):
        t = TF.brief_trail(self.tmp)
        t["FINAL_SCORE_MODEL.json"]["total"]["total_score"] = 65
        self.assertRule(self.run_trail(t), "X13", "not authorised")

    def test_provisional_mark_without_authority_rejected(self):
        t = TF.brief_trail(self.tmp)
        t["PRIMARY_ASSESSMENT.json"]["criterion_assessments"] = TF.rubric_trail(self.tmp)["PRIMARY_ASSESSMENT.json"]["criterion_assessments"]
        self.assertRule(self.run_trail(t), "X08", "not authorised")

    def test_numeric_mark_in_report_without_authority_rejected(self):
        t = TF.brief_trail(self.tmp)
        rep = TF.report_md(t).replace(TF.NO_SCHEME, TF.NO_SCHEME + " Indicative mark: 65/100")
        self.assertRule(self.run_trail(t, report_text=rep), "X16", "numeric mark")

    def test_missing_no_scheme_statement_rejected(self):
        t = TF.brief_trail(self.tmp)
        rep = TF.report_md(t).replace(TF.NO_SCHEME, "No rubric.")
        self.assertRule(self.run_trail(t, report_text=rep), "X16", "must state")

    # ---------------------------------------------------------------- arithmetic & adjudication
    def test_total_mismatch_rejected(self):
        t = TF.rubric_trail(self.tmp)
        t["FINAL_SCORE_MODEL.json"]["total"]["total_score"] = 33
        self.assertRule(self.run_trail(t), "X13", "recomputation")

    def test_hand_computed_total_rejected(self):
        t = TF.rubric_trail(self.tmp)
        t["FINAL_SCORE_MODEL.json"]["total"]["computed_by"] = "adjudicator"
        self.assertRule(self.run_trail(t), "X13", "compute_scores.py")

    def test_silent_averaging_rejected(self):
        t = TF.rubric_trail(self.tmp)
        pa = t["PRIMARY_ASSESSMENT.json"]["criterion_assessments"][1]
        pa["provisional_mark"], pa["mark_range_considered"] = 24, {"min": 21, "max": 30}
        sm = t["SECOND_MARKER_REVIEW.json"]["criterion_challenges"][1]
        sm.update(primary_mark=24, second_mark=22, second_level="Excellent", direction="OVER_MARKED")
        fc = t["FINAL_SCORE_MODEL.json"]["criteria"][1]
        fc.update(primary_mark=24, second_mark=22, final_mark=23, final_level="Excellent")
        t["FINAL_SCORE_MODEL.json"]["total"].update(total_score=35, percentage=70.0)
        self.assertRule(self.run_trail(t), "X13", "exact average")

    def test_final_mark_outside_descriptor_range_rejected(self):
        t = TF.rubric_trail(self.tmp)
        t["FINAL_SCORE_MODEL.json"]["criteria"][1]["final_mark"] = 25  # level stays "Good" (15-20.9)
        t["FINAL_SCORE_MODEL.json"]["total"].update(total_score=37, percentage=74.0)
        self.assertRule(self.run_trail(t), "X13", "outside descriptor")

    def test_primary_mark_outside_considered_range_rejected(self):
        t = TF.rubric_trail(self.tmp)
        t["PRIMARY_ASSESSMENT.json"]["criterion_assessments"][0]["provisional_mark"] = 16
        self.assertRule(self.run_trail(t), "X08", "RUBRIC->DESCRIPTOR->RANGE->MARK")

    def test_second_marker_must_cover_every_criterion(self):
        t = TF.rubric_trail(self.tmp)
        t["SECOND_MARKER_REVIEW.json"]["criterion_challenges"].pop()
        self.assertRule(self.run_trail(t), "X12", "every criterion")

    def test_readjudication_required_after_verification(self):
        t = TF.rubric_trail(self.tmp)
        v = t["VERIFIED_FINDINGS.json"]
        v["findings"][0].update(outcome="REMOVED", final_severity=None)
        v["findings"][0]["verification"]["false_positive"] = True
        v["summary"].update(confirmed=0, removed=1)
        v["requires_score_readjudication"] = ["CRIT-002"]
        rep = TF.report_md(t)
        self.assertRule(self.run_trail(t, report_text=rep), "X13", "re-run")

    # ---------------------------------------------------------------- verification of serious findings
    def test_unverified_major_finding_rejected(self):
        t = TF.rubric_trail(self.tmp)
        t["VERIFIED_FINDINGS.json"]["findings"] = []
        t["VERIFIED_FINDINGS.json"]["summary"] = {"checked": 0, "confirmed": 0, "corrected": 0, "downgraded": 0, "removed": 0}
        self.assertRule(self.run_trail(t), "X14", "not independently verified")

    def test_confirmed_false_positive_rejected(self):
        t = TF.rubric_trail(self.tmp)
        t["VERIFIED_FINDINGS.json"]["findings"][0]["verification"]["false_positive"] = True
        self.assertRule(self.run_trail(t), "X14", "REMOVED")

    def test_removed_finding_in_major_section_rejected(self):
        t = TF.rubric_trail(self.tmp)
        v = t["VERIFIED_FINDINGS.json"]
        rep = TF.report_md(t)  # section 11 lists F6-001
        v["findings"][0].update(outcome="REMOVED", final_severity=None)
        v["findings"][0]["verification"]["false_positive"] = True
        v["summary"].update(confirmed=0, removed=1)
        v["requires_score_readjudication"] = ["CRIT-002"]
        t["FINAL_SCORE_MODEL.json"]["verification_reconciled"] = True
        self.assertRule(self.run_trail(t, report_text=rep), "X16", "Removed finding")

    # ---------------------------------------------------------------- anti-hallucination
    def test_untraceable_requirement_quote_rejected(self):
        t = TF.rubric_trail(self.tmp)
        t["REQUIREMENT_REGISTER.json"]["requirements"][0]["verbatim_quote"] = "essay of 3,000 words"
        self.assertRule(self.run_trail(t), "X03", "not found in source")

    def test_best_practice_in_register_rejected(self):
        t = TF.rubric_trail(self.tmp)
        t["REQUIREMENT_REGISTER.json"]["requirements"][0]["source_priority"] = 6
        self.assertRule(self.run_trail(t), "X03", "best practice")

    def test_best_practice_cannot_be_critical(self):
        t = TF.rubric_trail(self.tmp)
        t["COHERENCE_AUDIT.json"]["findings"] = [TF.finding("F9-001", sev="CRITICAL", basis="BEST_PRACTICE",
                                                             ref="BEST PRACTICE (not a stated requirement)")]
        self.assertRule(self.run_trail(t), "X07", "never be CRITICAL")

    def test_optional_content_not_penalised(self):
        t = TF.rubric_trail(self.tmp)
        a = t["PRIMARY_ASSESSMENT.json"]["requirement_assessments"][2]
        a.update(status="MISSING", priority="MAJOR")
        self.assertRule(self.run_trail(t), "X08", "optional content")

    def test_optional_requirement_cannot_ground_major_finding(self):
        t = TF.rubric_trail(self.tmp)
        t["SPECIALIST_REVIEW.json"]["findings"] = [TF.finding("F7-001", ref="REQ-003")]
        self.assertRule(self.run_trail(t), "X07", "OPTIONAL")

    def test_optional_presented_as_mandatory_in_blueprint(self):
        t = TF.rubric_trail(self.tmp)
        t["QUALITY_BLUEPRINT.json"]["expectations"][0]["source_ids"] = ["REQ-003"]
        self.assertRule(self.run_trail(t), "X05", "presented as mandatory")

    def test_fabrication_claim_rejected(self):
        t = TF.rubric_trail(self.tmp)
        f = TF.finding("F8-001", sev="MODERATE")
        f["issue"] = "The Smith (2020) reference appears to be fabricated."
        t["EVIDENCE_AUDIT.json"]["findings"] = [f]
        self.assertRule(self.run_trail(t), "X07", "fabrication")

    def test_negated_fabrication_wording_rejected_in_report(self):
        t = TF.rubric_trail(self.tmp)
        rep = TF.report_md(t).replace(TF.REFS, TF.REFS + " The Kestrel note is not judged fabricated.")
        self.assertRule(self.run_trail(t, report_text=rep), "X16", "fabrication")

    def test_reference_statement_required(self):
        t = TF.rubric_trail(self.tmp)
        t["EVIDENCE_AUDIT.json"]["authenticity_statement"] = "References look fine."
        self.assertRule(self.run_trail(t), "X10", "REFERENCE AUTHENTICITY")

    # ---------------------------------------------------------------- task-appropriate reviews
    def test_coding_review_on_essay_rejected(self):
        t = TF.rubric_trail(self.tmp)
        t["SPECIALIST_REVIEW.json"]["code_review"] = {"performed": True, "execution_performed": False,
                                                      "execution_statement": TF.STATIC}
        self.assertRule(self.run_trail(t), "X09", "does not require")

    def test_code_execution_rejected(self):
        t = TF.rubric_trail(self.tmp)
        t["SPECIALIST_REVIEW.json"]["code_review"]["execution_performed"] = True
        self.assertRule(self.run_trail(t), "X09", "disabled by policy")

    def test_static_statement_required_when_code_reviewed(self):
        t = TF.rubric_trail(self.tmp)
        tc = t["TASK_CLASSIFICATION.json"]
        tc["specialist_reviews_required"] = ["CODE"]
        tc["coding_review_required"] = True
        t["SPECIALIST_REVIEW.json"]["reviews_activated"] = ["CODE"]
        t["SPECIALIST_REVIEW.json"]["code_review"] = {"performed": True, "execution_performed": False,
                                                      "execution_statement": "Code looks fine"}
        self.assertRule(self.run_trail(t), "X09", "execution_statement")

    # ---------------------------------------------------------------- inputs & coverage
    def test_every_requirement_must_be_assessed(self):
        t = TF.rubric_trail(self.tmp)
        t["PRIMARY_ASSESSMENT.json"]["requirement_assessments"].pop()
        self.assertRule(self.run_trail(t), "X08", "exactly once")

    def test_title_mode_requires_no_brief(self):
        t = TF.brief_trail(self.tmp)
        t["INPUT_MANIFEST.json"]["analysis_mode"] = "TITLE_TOPIC"
        self.assertRule(self.run_trail(t), "X01", "TITLE_TOPIC")

    def test_unreadable_file_must_not_be_marked_analysed(self):
        t = TF.rubric_trail(self.tmp)
        t["INPUT_MANIFEST.json"]["files"][2]["extraction_status"] = "FAILED"
        self.assertRule(self.run_trail(t), "X01", "marked analysed")

    def test_manifest_must_account_for_every_inventoried_file(self):
        t = TF.rubric_trail(self.tmp)
        TF.write(t, self.trail_dir, TF.report_md(t))
        inv = self.tmp / "inv.json"
        inv.write_text(json.dumps({"files": [{"file_id": f"FILE-00{i}"} for i in range(1, 5)]}))
        res = validate.run(self.trail_dir, ALL, True, self.trail_dir.parent / "_work" / "FINAL_QUALITY_AUDIT.draft.md", inv)
        self.assertRule(res, "X01", "silently ignore")

    def test_rubric_invented_in_brief_mode_rejected(self):
        t = TF.brief_trail(self.tmp)
        t["RUBRIC_MODEL.json"]["criteria"] = TF.rubric_trail(self.tmp)["RUBRIC_MODEL.json"]["criteria"]
        self.assertRule(self.run_trail(t), "X04", "never create a rubric")

    def test_schema_violation_detected(self):
        t = TF.rubric_trail(self.tmp)
        del t["TASK_CLASSIFICATION.json"]["task_type"]
        self.assertRule(self.run_trail(t), "SCHEMA", "task_type")

    # ---------------------------------------------------------------- QA gate & report
    def test_qa_pass_with_failed_check_rejected(self):
        t = TF.rubric_trail(self.tmp)
        t["QA_STATUS.json"]["checks"][3]["result"] = "FAIL"
        self.assertRule(self.run_trail(t), "X15", "checks failed")

    def test_qa_must_include_all_checks(self):
        t = TF.rubric_trail(self.tmp)
        t["QA_STATUS.json"]["checks"].pop()
        self.assertTrue(self.run_trail(t)["errors"])

    def test_report_missing_section_rejected(self):
        t = TF.rubric_trail(self.tmp)
        rep = TF.report_md(t).replace("## 22. Presentation Review", "## Presentation")
        self.assertRule(self.run_trail(t, report_text=rep), "X16", "22.")

    def test_report_must_show_computed_total(self):
        t = TF.rubric_trail(self.tmp)
        rep = TF.report_md(t).replace("32 / 50", "35 / 50")
        self.assertRule(self.run_trail(t, report_text=rep), "X16", "computed total")

    def test_title_mode_report_separates_known_and_best_practice(self):
        t = TF.brief_trail(self.tmp)
        m = t["INPUT_MANIFEST.json"]
        m.update(analysis_mode="TITLE_TOPIC", brief_present=False)
        for doc in ("REQUIREMENT_REGISTER.json", "PRIMARY_ASSESSMENT.json"):
            t[doc]["analysis_mode"] = "TITLE_TOPIC"
        t["PRIMARY_ASSESSMENT.json"]["quality_dimensions"] = [{"dimension": "Depth", "basis": "BEST_PRACTICE",
                                                               "rating": "ADEQUATE", "evidence": "x", "improvement_action": "y"}]
        self.assertRule(self.run_trail(t), "X16", "KNOWN REQUIREMENTS")
        rep = TF.report_md(t).replace("REQ-001 REQ-002 REQ-003", "KNOWN REQUIREMENTS REQ-001 REQ-002 REQ-003 BEST-PRACTICE EXPECTATIONS")
        self.assertTrue(self.run_trail(t, report_text=rep)["passed"])

    def test_missing_word_count_caught_early(self):
        t = TF.rubric_trail(self.tmp)
        t["SUBMISSION_EVIDENCE_MAP.json"]["metrics"]["word_count_estimate"] = None
        work = self.trail_dir.parent / "_work"
        work.mkdir(parents=True, exist_ok=True)
        (work / "TEXT_STATS.json").write_text(json.dumps({"files": {"FILE-003": {"words_total": 1490}}}))
        self.assertRule(self.run_trail(t), "X06", "word_count_estimate")

    def test_report_must_list_every_requirement(self):
        t = TF.rubric_trail(self.tmp)
        rep = TF.report_md(t).replace("REQ-003", "")
        self.assertRule(self.run_trail(t, report_text=rep), "X16", "REQ-003")


if __name__ == "__main__":
    unittest.main()

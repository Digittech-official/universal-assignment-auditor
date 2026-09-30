"""Tests for extractors, prepare_run (per fixture), compute_scores, release gate, safety hook, privacy."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TOOLS = REPO / "SYSTEM" / "TOOLS"
FIX = REPO / "SYSTEM" / "TESTS" / "fixtures"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(HERE))
import extractors as ex  # noqa: E402
import compute_scores  # noqa: E402
import trail_factory as TF  # noqa: E402


def py(script: str, *args, env=None, cwd=REPO):
    return subprocess.run([sys.executable, str(TOOLS / script), *args], capture_output=True, text=True,
                          env={**os.environ, **(env or {})}, cwd=cwd)


class ExtractorTests(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.tmp = Path(self._t.name)

    def tearDown(self):
        self._t.cleanup()

    def test_docx_headings_and_tables(self):
        sys.path.insert(0, str(REPO / "SYSTEM" / "TESTS"))
        from build_fixtures import build_docx
        p = self.tmp / "a.docx"
        build_docx("# Title\n## Methods\nA paragraph.\n| H1 | H2 |\n|---|---|\n| a | b |\n", p)
        r = ex.extract(p)
        self.assertEqual(r.status, ex.EXTRACTED)
        self.assertIn("# Title", r.text)
        self.assertIn("## Methods", r.text)
        self.assertIn("a | b", r.text)
        self.assertEqual(r.stats["tables"], 1)

    def test_pptx_slides_and_notes(self):
        sys.path.insert(0, str(REPO / "SYSTEM" / "TESTS"))
        from build_fixtures import build_pptx
        p = self.tmp / "s.pptx"
        build_pptx("Intro\n- point one\nNotes: say hello\n---\nSecond\n- point two\n", p)
        r = ex.extract(p)
        self.assertEqual(r.stats["slides"], 2)
        self.assertEqual(r.stats["slides_with_speaker_notes"], 1)
        self.assertIn("[SPEAKER NOTES] say hello", r.text)

    def test_xlsx_values(self):
        sys.path.insert(0, str(REPO / "SYSTEM" / "TESTS"))
        from build_fixtures import build_xlsx
        p = self.tmp / "d.xlsx"
        build_xlsx("Month,North\nJan,101\nFeb,99\n", p, "data")
        r = ex.extract(p)
        self.assertEqual(r.status, ex.EXTRACTED)
        self.assertIn("Jan | 101", r.text)

    def test_ipynb_outputs_labelled_not_executed(self):
        p = self.tmp / "n.ipynb"
        p.write_text(json.dumps({"cells": [{"cell_type": "code", "source": ["print(1)"],
                                            "outputs": [{"output_type": "stream", "text": ["1\n"]}]}]}))
        r = ex.extract(p)
        self.assertIn("[STORED OUTPUT] 1", r.text)
        self.assertTrue(any("NOT re-executed" in n for n in r.notes))

    def test_zip_slip_blocked(self):
        p = self.tmp / "evil.zip"
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("../../escape.txt", "x")
            zf.writestr("ok/good.py", "print('hi')")
        r = ex.safe_unzip(p, self.tmp / "out")
        self.assertFalse((self.tmp.parent / "escape.txt").exists())
        self.assertTrue(any("unsafe" in n for n in r.notes))
        self.assertEqual(len(r.children), 1)

    def test_zip_bomb_rejected(self):
        p = self.tmp / "bomb.zip"
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("big.txt", "0" * (50 * 1024 * 1024))
        self.assertEqual(ex.safe_unzip(p, self.tmp / "o").status, ex.FAILED)

    def test_corrupt_legacy_empty_binary(self):
        bad = self.tmp / "bad.docx"
        bad.write_bytes(b"PK\x03\x04garbage" * 10)
        self.assertEqual(ex.extract(bad).status, ex.FAILED)
        doc = self.tmp / "old.doc"
        doc.write_bytes(bytes.fromhex("D0CF11E0A1B11AE1") + b"\x00" * 100)
        self.assertEqual(ex.extract(doc).status, ex.UNSUPPORTED)
        empty = self.tmp / "e.txt"
        empty.write_text("")
        self.assertEqual(ex.extract(empty).status, ex.EMPTY)
        fake = self.tmp / "f.txt"
        fake.write_bytes(b"\x00\x01\x02" * 100)
        self.assertEqual(ex.extract(fake).status, ex.FAILED)

    def test_pdf_falls_back_to_claude_read_or_extracts(self):
        pdfs = list(FIX.rglob("*.pdf"))
        if not pdfs:
            self.skipTest("no PDF fixture built")
        r = ex.extract(pdfs[0])
        self.assertIn(r.status, (ex.EXTRACTED, ex.NEEDS_CLAUDE_READ))


class PrepareRunFixtureTests(unittest.TestCase):
    """prepare_run's advisory mode and unreadable-file detection on every fixture."""

    def test_fixtures(self):
        cases = sorted(p for p in FIX.iterdir() if (p / "expected.json").exists())
        self.assertGreaterEqual(len(cases), 10, "expected at least 10 synthetic fixtures (A-J)")
        for case in cases:
            with self.subTest(case=case.name), tempfile.TemporaryDirectory() as tmp:
                exp = json.loads((case / "expected.json").read_text())
                inp = case / "INPUT"
                out = Path(tmp) / "OUTPUT"
                if not inp.exists():
                    (Path(tmp) / "INPUT").mkdir()
                    inp = Path(tmp) / "INPUT"
                r = py("prepare_run.py", env={"UAA_INPUT_DIR": str(inp), "UAA_OUTPUT_DIR": str(out)})
                self.assertEqual(r.returncode, 0, r.stderr)
                inv = json.loads((out / "_work" / "INPUT_INVENTORY.json").read_text())
                self.assertEqual(inv["advisory_mode"]["preliminary_mode"], exp["expected_mode"])
                bad = " ".join(f["path"] for f in inv["files_not_analysable"])
                for sub in exp["must_list_unanalysed"]:
                    self.assertIn(sub, bad)
                for f in inv["files"]:
                    self.assertFalse(f["path"].startswith("/"), "absolute path leaked into inventory")


class ScoreTests(unittest.TestCase):
    def test_sum(self):
        rub = {"aggregation_method": "SUM", "total_available": 50, "grade_boundaries": [],
               "criteria": [{"id": "CRIT-001", "max_marks": 20, "weight_percent": None},
                            {"id": "CRIT-002", "max_marks": 30, "weight_percent": None}]}
        model = {"criteria": [{"criterion_id": "CRIT-001", "max_marks": 20, "weight_percent": None, "final_mark": 12},
                              {"criterion_id": "CRIT-002", "max_marks": 30, "weight_percent": None, "final_mark": 20.5}]}
        tot, _ = compute_scores.compute(model, rub)
        self.assertEqual((tot["total_score"], tot["percentage"], tot["grade_band"]), (32.5, 65.0, "NOT PROVIDED"))

    def test_weighted_with_band(self):
        rub = {"aggregation_method": "WEIGHTED_PERCENT", "total_available": 100,
               "grade_boundaries": [{"label": "Distinction", "min": 70, "max": 100}, {"label": "Pass", "min": 40, "max": 69.99},
                                    {"label": "Fail", "min": 0, "max": 39.99}],
               "criteria": [{"id": "CRIT-001", "max_marks": None, "weight_percent": 40},
                            {"id": "CRIT-002", "max_marks": 20, "weight_percent": 60}]}
        model = {"criteria": [{"criterion_id": "CRIT-001", "max_marks": None, "weight_percent": 40, "final_mark": 70},
                              {"criterion_id": "CRIT-002", "max_marks": 20, "weight_percent": 60, "final_mark": 12}]}
        tot, _ = compute_scores.compute(model, rub)
        self.assertEqual(tot["total_score"], 64.0)  # 70*0.4 + 12/20*60
        self.assertEqual(tot["grade_band"], "Pass")

    def test_out_of_range_rejected(self):
        rub = {"aggregation_method": "SUM", "criteria": [{"id": "CRIT-001", "max_marks": 10, "weight_percent": None}]}
        model = {"criteria": [{"criterion_id": "CRIT-001", "max_marks": 10, "weight_percent": None, "final_mark": 11}]}
        with self.assertRaises(ValueError):
            compute_scores.compute(model, rub)

    def test_bands_only_cannot_total(self):
        with self.assertRaises(ValueError):
            compute_scores.compute({"criteria": []}, {"aggregation_method": "NONE", "criteria": []})


class ReleaseGateTests(unittest.TestCase):
    def _setup(self, tmp: Path, trail: dict, report: bool = True):
        out = tmp / "OUTPUT"
        TF.write(trail, out / "audit_trail", TF.report_md(trail) if report else None)
        return {"UAA_OUTPUT_DIR": str(out), "UAA_INPUT_DIR": str(tmp / "INPUT")}, out

    def test_release_on_pass(self):
        with tempfile.TemporaryDirectory() as t:
            env, out = self._setup(Path(t), TF.rubric_trail(Path(t)))
            r = py("release_report.py", env=env)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertTrue((out / "FINAL_QUALITY_AUDIT.md").exists())
            self.assertTrue((out / "FINAL_QUALITY_AUDIT.html").exists())
            self.assertIn("QA_STATUS: PASS", (out / "FINAL_QUALITY_AUDIT.md").read_text())
            self.assertTrue((out / "audit_trail" / "REQUIREMENT_TRACEABILITY_MATRIX.md").exists())

    def test_blocked_on_qa_fail(self):
        with tempfile.TemporaryDirectory() as t:
            trail = TF.rubric_trail(Path(t))
            qa = trail["QA_STATUS.json"]
            qa.update(qa_status="FAIL", release_authorised=False,
                      failures=[{"check_id": "QA-12", "stage_to_rerun": "REPORT_COMPOSER", "correction_required": "Vague feedback"}])
            qa["checks"][11]["result"] = "FAIL"
            env, out = self._setup(Path(t), trail)
            (out / "FINAL_QUALITY_AUDIT.md").write_text("stale report from an earlier run")
            r = py("release_report.py", env=env)
            self.assertEqual(r.returncode, 1)
            self.assertFalse((out / "FINAL_QUALITY_AUDIT.md").exists(), "stale/unauthorised report must be removed")
            self.assertIn("QA_STATUS = FAIL", (out / "AUDIT_BLOCKED.md").read_text())

    def test_blocked_on_validator_error_even_if_qa_pass(self):
        with tempfile.TemporaryDirectory() as t:
            trail = TF.rubric_trail(Path(t))
            trail["FINAL_SCORE_MODEL.json"]["total"]["total_score"] = 40  # wrong arithmetic
            env, out = self._setup(Path(t), trail)
            r = py("release_report.py", env=env)
            self.assertEqual(r.returncode, 1)
            self.assertFalse((out / "FINAL_QUALITY_AUDIT.md").exists())

    def test_blocked_on_missing_submission(self):
        with tempfile.TemporaryDirectory() as t:
            m = TF.rubric_trail(Path(t))["INPUT_MANIFEST.json"]
            m.update(analysis_mode="CANNOT_PROCEED", can_proceed=False, submission_present=False,
                     blocking_reasons=["No file in 04_COMPLETED_ASSIGNMENT/."])
            env, out = self._setup(Path(t), {"INPUT_MANIFEST.json": m}, report=False)
            r = py("release_report.py", env=env)
            self.assertEqual(r.returncode, 3)
            self.assertIn("04_COMPLETED_ASSIGNMENT", (out / "AUDIT_BLOCKED.md").read_text())


class HookTests(unittest.TestCase):
    CASES = {
        "python3 INPUT/04_COMPLETED_ASSIGNMENT/app.py": 2,
        "cd OUTPUT/_work && python3 OUTPUT/_work/unpacked/FILE-003/main.py": 2,
        "node OUTPUT/_work/unpacked/FILE-003/index.js": 2,
        "bash INPUT/04_COMPLETED_ASSIGNMENT/run.sh": 2,
        "OUTPUT/_work/unpacked/FILE-001/run.sh": 2,
        "timeout 5 pytest OUTPUT/_work/code_check/tests": 2,
        "git add -f OUTPUT/FINAL_QUALITY_AUDIT.md": 2,
        "git add INPUT/04_COMPLETED_ASSIGNMENT/x.docx": 2,
        "rm -rf INPUT/04_COMPLETED_ASSIGNMENT/x.docx": 2,
        "python3 -m py_compile OUTPUT/_work/code_check/app.py": 0,
        "node --check OUTPUT/_work/code_check/index.js": 0,
        "grep -n eval INPUT/04_COMPLETED_ASSIGNMENT/app.py": 0,
        "cat INPUT/01_BRIEF_AND_TITLE/brief.txt": 0,
        "cp -r INPUT/04_COMPLETED_ASSIGNMENT OUTPUT/_work/code_check": 0,
        "python3 SYSTEM/TOOLS/text_stats.py OUTPUT/_work/extracted/FILE-001__a.txt": 0,
        "python3 SYSTEM/TOOLS/validate.py --upto AGENT_05": 0,
        "git add README.md": 0,
        "git add INPUT": 2,
        "echo 'never run: git add INPUT/x' > OUTPUT/_work/note.txt": 0,
        "rm -rf OUTPUT/_work/tmp": 0,
    }

    def test_hook(self):
        for cmd, want in self.CASES.items():
            with self.subTest(cmd=cmd):
                r = subprocess.run([sys.executable, str(TOOLS / "hooks" / "guard_bash.py")],
                                   input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, want, r.stderr)


class RepoHygieneTests(unittest.TestCase):
    def test_schemas_up_to_date(self):
        r = py("build_schemas.py", "--check")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_privacy_check(self):
        r = py("privacy_check.py")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_agents_and_command_exist(self):
        agents = sorted(p.name for p in (REPO / ".claude" / "agents").glob("aua-*.md"))
        self.assertEqual(len(agents), 15, agents)
        cmd = (REPO / ".claude" / "commands" / "check-assignment.md").read_text()
        for a in agents:
            self.assertIn(a[:-3], cmd, f"{a} not orchestrated by /check-assignment")
        for a in agents:
            text = (REPO / ".claude" / "agents" / a).read_text()
            self.assertTrue(text.startswith("---\nname: " + a[:-3] + "\n"), f"bad frontmatter in {a}")

    def test_no_absolute_paths_in_system(self):
        for p in list((REPO / "SYSTEM").rglob("*.md")) + list((REPO / ".claude").rglob("*.md")) + [REPO / "README.md", REPO / "CLAUDE.md"]:
            if p.exists() and "runs" not in p.parts:
                self.assertNotRegex(p.read_text(encoding="utf-8"), r"/home/[a-z]+/|/Users/[A-Za-z]", str(p))


if __name__ == "__main__":
    unittest.main()

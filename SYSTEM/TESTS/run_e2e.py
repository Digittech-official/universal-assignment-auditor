#!/usr/bin/env python3
"""End-to-end acceptance runner: executes the real /check-assignment pipeline on fixtures.

For each case it makes an isolated copy of the repository OUTSIDE this git repo (default: <system temp>/uaa-e2e-runs/
<CASE>/repo, override with --runs-dir), loads the fixture into that copy's INPUT/, runs Claude Code headless:

    claude -p "/check-assignment" --permission-mode acceptEdits --allowedTools <project allow-list>

then evaluates the result with evaluate_run.py. Summary: SYSTEM/TESTS/runs/SUMMARY.md (git-ignored).

Usage: python3 SYSTEM/TESTS/run_e2e.py [CASE ...] [--parallel N] [--model MODEL] [--runs-dir DIR] [--evaluate-only]
Requires an authenticated `claude` CLI. Consumes model usage (each case runs ~15 subagents).
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUNS = HERE / "runs"  # summary only (git-ignored)
WORK = Path(tempfile.gettempdir()) / "uaa-e2e-runs"  # isolated copies live outside the git repository


def ignore(dirpath, names):
    rel = Path(dirpath).resolve().relative_to(REPO)
    skip = {".git", "__pycache__", ".pytest_cache"}
    if rel == Path("SYSTEM/TESTS"):
        skip.add("runs")
    if rel.parts[:1] in (("INPUT",), ("OUTPUT",)):
        return [n for n in names if n not in (".gitkeep", "README.md") and not (Path(dirpath) / n).is_dir()]
    return [n for n in names if n in skip]


def run_case(case: str, model: str | None, evaluate_only: bool) -> dict:
    base = WORK / case
    dest = base / "repo"
    t0 = time.time()
    if not evaluate_only:
        if base.exists():
            shutil.rmtree(base)
        shutil.copytree(REPO, dest, ignore=ignore)
        subprocess.run([sys.executable, "SYSTEM/TOOLS/load_fixture.py", case, "--force"], cwd=dest, check=True,
                       capture_output=True)
        # Headless runs get exactly the project's allow-list plus the core file/agent tools: this mirrors what an
        # employee approves interactively and never bypasses permission checks or the safety hook.
        allowed = json.loads((REPO / ".claude" / "settings.json").read_text())["permissions"]["allow"]
        allowed += ["Read", "Glob", "Grep", "Write", "Edit", "Agent", "Task", "Bash(python3 -c:*)",
                    "Bash(mkdir:*)", "Bash(cp:*)", "Bash(cat:*)", "Bash(sort:*)", "Bash(diff:*)"]
        cmd = ["claude", "-p", "/check-assignment", "--permission-mode", "acceptEdits", "--allowedTools", *allowed]
        if model:
            cmd += ["--model", model]
        with open(base / "claude_run.log", "w", encoding="utf-8") as log:
            proc = subprocess.run(cmd, cwd=dest, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                  timeout=3 * 3600)
        rc = proc.returncode
    else:
        rc = 0
    ev = subprocess.run([sys.executable, "SYSTEM/TESTS/evaluate_run.py", case, "--json", str(base / "result.json")],
                        cwd=dest, capture_output=True, text=True)
    (base / "evaluation.txt").write_text(ev.stdout + ev.stderr, encoding="utf-8")
    result = json.loads((base / "result.json").read_text()) if (base / "result.json").exists() else {"passed": False, "checks": []}
    return {"case": case, "run_dir": str(base), "claude_exit": rc, "passed": result["passed"], "minutes": round((time.time() - t0) / 60, 1),
            "failed_checks": [f"{c['id']} {c['check']} -> {c['detail']}" for c in result["checks"] if not c["passed"]]}


def main(argv: list[str]) -> int:
    global WORK
    parallel = int(argv[argv.index("--parallel") + 1]) if "--parallel" in argv else 2
    if "--runs-dir" in argv:
        WORK = Path(argv[argv.index("--runs-dir") + 1]).resolve()
    model = argv[argv.index("--model") + 1] if "--model" in argv else None
    skip = {"--parallel", "--model", "--runs-dir"}
    cases, i = [], 0
    while i < len(argv):
        if argv[i] in skip:
            i += 2
            continue
        if not argv[i].startswith("--"):
            cases.append(argv[i])
        i += 1
    if not cases:
        cases = sorted(p.name for p in (HERE / "fixtures").iterdir() if (p / "expected.json").exists())
    RUNS.mkdir(exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    with cf.ThreadPoolExecutor(max_workers=parallel) as pool:
        results = list(pool.map(lambda c: run_case(c, model, "--evaluate-only" in argv), cases))
    lines = ["# E2E acceptance results", "", f"Run copies: {WORK}", "",
             "| Case | Result | Minutes | Failed checks |", "|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['case']} | {'PASS' if r['passed'] else 'FAIL'} | {r['minutes']} | "
                     f"{'<br>'.join(r['failed_checks']) or '—'} |")
    (RUNS / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

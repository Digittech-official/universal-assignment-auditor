#!/usr/bin/env python3
"""Privacy & portability gate for tracked / staged files.

Fails (exit 1) if git would publish:
  * any file under INPUT/ other than the skeleton (.gitkeep, INPUT/README.md)
  * any file under OUTPUT/ other than OUTPUT/.gitkeep
  * likely credentials (private keys, API tokens, .env files)
  * absolute personal machine paths (/home/<user>/, /Users/<user>/, C:\\Users\\<user>\\)
Also verifies that .gitignore actually ignores sample INPUT/OUTPUT files.

Run before every commit:  python3 SYSTEM/TOOLS/privacy_check.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ALLOWED_SKELETON = re.compile(r"^(INPUT/README\.md|INPUT/[^/]+/\.gitkeep|OUTPUT/\.gitkeep)$")
SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), "Anthropic API key"),
    (re.compile(r"\bsk-[A-Za-z0-9]{32,}"), "API secret key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"), "GitHub token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"(?i)\b(?:api[_-]?key|secret|password|passwd|token)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"), "hard-coded secret"),
]
PATH_PATTERN = re.compile(r"(/home/[a-z][a-z0-9_-]+/|/Users/[A-Za-z][\w.-]+/|[A-Za-z]:\\\\?Users\\\\?[A-Za-z])")
SELF = "SYSTEM/TOOLS/privacy_check.py"


def git(*args) -> list[str]:
    out = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=False)
    return [l for l in out.stdout.splitlines() if l.strip()]


def main() -> int:
    problems: list[str] = []
    tracked = set(git("ls-files")) | set(git("diff", "--cached", "--name-only", "--diff-filter=ACMR"))
    for f in sorted(tracked):
        if (f.startswith("INPUT/") or f.startswith("OUTPUT/")) and not ALLOWED_SKELETON.match(f):
            problems.append(f"Operational data would be committed: {f}")
        name = Path(f).name
        if name == ".env" or name.startswith(".env.") or name.endswith((".pem", ".key", ".p12", ".pfx")):
            problems.append(f"Credential-like file tracked: {f}")
        p = REPO / f
        if not p.is_file() or f == SELF or p.stat().st_size > 2_000_000:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pat, label in SECRET_PATTERNS:
            if pat.search(text):
                problems.append(f"Possible {label} in {f}")
        m = PATH_PATTERN.search(text)
        if m:
            problems.append(f"Absolute personal machine path in {f}: {m.group(0)!r}")

    # .gitignore effectiveness probe (no files are created)
    probes = ["INPUT/04_COMPLETED_ASSIGNMENT/student_essay.docx", "INPUT/02_RUBRIC_AND_MARKING/rubric.pdf",
              "INPUT/stray.txt", "OUTPUT/FINAL_QUALITY_AUDIT.md", "OUTPUT/audit_trail/QA_STATUS.json",
              ".env", "config/.env.local"]
    ignored = set(git("check-ignore", "--no-index", *probes))
    for pth in probes:
        if pth not in ignored:
            problems.append(f".gitignore does NOT ignore {pth}")
    keep = ["INPUT/01_BRIEF_AND_TITLE/.gitkeep", "OUTPUT/.gitkeep", "INPUT/README.md"]
    wrongly = set(git("check-ignore", "--no-index", *keep))
    for pth in keep:
        if pth in wrongly:
            problems.append(f".gitignore wrongly ignores skeleton file {pth}")

    if problems:
        print("PRIVACY CHECK FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"PRIVACY CHECK PASSED — {len(tracked)} tracked/staged file(s) scanned; .gitignore probes OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

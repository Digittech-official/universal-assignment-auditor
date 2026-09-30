#!/usr/bin/env python3
"""Copies a synthetic test fixture into INPUT/ (maintainers / acceptance testing only).

Usage:
  python3 SYSTEM/TOOLS/load_fixture.py --list
  python3 SYSTEM/TOOLS/load_fixture.py A_dissertation_rubric [--force] [--root PATH]

Refuses to overwrite existing INPUT content unless --force (which clears INPUT/ and OUTPUT/ first).
--root lets the E2E runner load a fixture into an isolated copy of the repository.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FIXTURES_DIR, INPUT_FOLDERS, PLACEHOLDER_NAMES, REPO_ROOT  # noqa: E402


def cases() -> list[str]:
    return sorted(p.name for p in FIXTURES_DIR.iterdir() if (p / "expected.json").exists())


def main(argv: list[str]) -> int:
    if not argv or "--list" in argv:
        print("\n".join(cases()))
        return 0
    case = argv[0]
    root = Path(argv[argv.index("--root") + 1]).resolve() if "--root" in argv else REPO_ROOT
    src = FIXTURES_DIR / case / "INPUT"
    if case not in cases():
        print(f"Unknown fixture {case!r}. Available: {', '.join(cases())}")
        return 2
    inp, out = root / "INPUT", root / "OUTPUT"
    existing = [p for f in INPUT_FOLDERS for p in (inp / f).glob("*") if p.name not in PLACEHOLDER_NAMES] \
        if inp.exists() else []
    if existing and "--force" not in argv:
        print("INPUT/ already contains files. Re-run with --force to clear INPUT/ and OUTPUT/ first.")
        return 1
    for f in INPUT_FOLDERS:
        d = inp / f
        d.mkdir(parents=True, exist_ok=True)
        for p in d.iterdir():
            if p.name != ".gitkeep":
                shutil.rmtree(p) if p.is_dir() else p.unlink()
        (d / ".gitkeep").touch()
    if out.exists():
        for p in out.iterdir():
            if p.name != ".gitkeep":
                shutil.rmtree(p) if p.is_dir() else p.unlink()
    out.mkdir(exist_ok=True)
    n = 0
    if src.exists():
        for p in src.rglob("*"):
            if p.is_file():
                dest = inp / p.relative_to(src)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dest)
                n += 1
    print(f"Loaded fixture {case}: {n} file(s) into {'INPUT/' if root == REPO_ROOT else root / 'INPUT'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

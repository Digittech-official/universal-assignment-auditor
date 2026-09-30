#!/usr/bin/env python3
"""Deletes all local assignment data from INPUT/ and OUTPUT/ (keeps the folder skeleton).

Usage:
  python3 SYSTEM/TOOLS/clear_local_data.py            # asks for confirmation
  python3 SYSTEM/TOOLS/clear_local_data.py --yes      # no prompt
  python3 SYSTEM/TOOLS/clear_local_data.py --output-only
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import INPUT_DIR, INPUT_FOLDERS, OUTPUT_DIR, PLACEHOLDER_NAMES  # noqa: E402

KEEP_INPUT_ROOT = {"README.md", ".gitkeep"}


def targets(output_only: bool) -> list[Path]:
    found: list[Path] = []
    if not output_only and INPUT_DIR.exists():
        for item in INPUT_DIR.iterdir():
            if item.is_dir() and item.name in INPUT_FOLDERS:
                found += [p for p in item.iterdir() if p.name != ".gitkeep"]
            elif item.name not in KEEP_INPUT_ROOT:
                found.append(item)
    if OUTPUT_DIR.exists():
        found += [p for p in OUTPUT_DIR.iterdir() if p.name != ".gitkeep"]
    return found


def main(argv: list[str]) -> int:
    output_only = "--output-only" in argv
    items = targets(output_only)
    if not items:
        print("Nothing to clear — INPUT/ and OUTPUT/ are already empty.")
        return 0
    print(f"This will permanently delete {len(items)} item(s) from "
          f"{'OUTPUT/' if output_only else 'INPUT/ and OUTPUT/'}:")
    for p in items[:25]:
        print(f"  - {p.relative_to(p.parents[1]) if len(p.parents) > 1 else p.name}")
    if len(items) > 25:
        print(f"  ... and {len(items) - 25} more")
    if "--yes" not in argv:
        if input("Type YES to confirm: ").strip() != "YES":
            print("Cancelled.")
            return 1
    for p in items:
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink()
    for folder in INPUT_FOLDERS:
        (INPUT_DIR / folder).mkdir(parents=True, exist_ok=True)
        (INPUT_DIR / folder / ".gitkeep").touch()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / ".gitkeep").touch()
    print("Local assignment data cleared.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

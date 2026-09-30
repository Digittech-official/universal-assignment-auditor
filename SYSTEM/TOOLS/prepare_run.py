#!/usr/bin/env python3
"""Stage P — deterministic pre-processing for /check-assignment.

1. Moves any previous run in OUTPUT/ to OUTPUT/_previous_run/ (git-ignored).
2. Inventories every file under INPUT/ (nothing is silently skipped).
3. Extracts text into OUTPUT/_work/extracted/ (safe ZIP unpacking, no execution).
4. Detects exact duplicates, possible competing submissions and misfiled files.
5. Computes ADVISORY mode signals (Agent 0 makes the final decision).

Writes OUTPUT/_work/INPUT_INVENTORY.json and prints a short summary.
Exit code 0 = inventory written (even if inputs are missing — Agent 0 reports that).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import platform
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (AUDIT_DIR, EXTRACTED_DIR, INPUT_DIR, INPUT_FOLDERS, OUTPUT_DIR,  # noqa: E402
                    PLACEHOLDER_NAMES, REPO_ROOT, WORK_DIR, rel, write_json)
import extractors as ex  # noqa: E402

RUBRIC_PATTERNS = [
    r"\b\d{1,3}\s*(?:marks?|pts|points)\b", r"\b\d{1,3}\s*%", r"\bweight(?:ing)?\b", r"\bcriteri(?:on|a)\b",
    r"\bdescriptor", r"\bmark(?:ing)?\s+(?:scheme|rubric|criteria|grid)", r"\brubric\b",
    r"\b(?:first class|2:1|2:2|distinction|merit|high distinction|credit)\b", r"\bgrade (?:band|boundar)",
    r"/\s*\d{1,3}\b",
]
BRIEF_PATTERNS = [
    r"\byou (?:must|should|are required|will)\b", r"\b(?:task|brief|instructions?|requirements?)\b",
    r"\bword (?:count|limit)\b", r"\b(?:submit|submission|deadline)\b", r"\blearning outcomes?\b",
    r"\b(?:discuss|evaluate|analyse|analyze|critically|implement|design|develop|write)\b",
]
VERSION_WORDS = re.compile(r"(?i)\b(?:v\d+|version|draft|final|old|new|copy|backup|revised|\(\d\))\b")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_hits(patterns, text: str) -> int:
    return sum(len(re.findall(p, text, flags=re.IGNORECASE)) for p in patterns)


def archive_previous_output() -> str | None:
    items = [p for p in OUTPUT_DIR.iterdir() if p.name not in PLACEHOLDER_NAMES | {"_previous_run"}] \
        if OUTPUT_DIR.exists() else []
    if not items:
        return None
    prev = OUTPUT_DIR / "_previous_run"
    if prev.exists():
        shutil.rmtree(prev)
    prev.mkdir(parents=True)
    for item in items:
        shutil.move(str(item), str(prev / item.name))
    return rel(prev)


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:80]


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    archived = archive_previous_output()
    for d in (AUDIT_DIR, EXTRACTED_DIR):
        d.mkdir(parents=True, exist_ok=True)

    files, misplaced, missing_folders = [], [], []
    counter = 0

    def register(path: Path, folder_key: str, folder_role: str, parent: str | None = None,
                 display_path: str | None = None):
        nonlocal counter
        counter += 1
        fid = f"FILE-{counter:03d}"
        res = ex.extract(path, unzip_dest=WORK_DIR / "unpacked" / fid)
        out_txt = None
        if res.text:
            out_txt = EXTRACTED_DIR / f"{fid}__{safe_name(path.name)}.txt"
            header = (f"# EXTRACTED TEXT — {fid}\n# source: {display_path or rel(path)}\n"
                      f"# method: {res.method} | status: {res.status}\n"
                      f"# NOTE: machine extraction; layout, images and formatting may be lost.\n\n")
            out_txt.write_text(header + res.text, encoding="utf-8")
        text = res.text or ""
        entry = {
            "file_id": fid,
            "path": display_path or rel(path),
            "folder": folder_key,
            "folder_role": folder_role,
            "parent_archive": parent,
            "file_kind": ex.file_kind(path),
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
            "extraction_status": res.status,
            "extraction_method": res.method,
            "extracted_text_path": rel(out_txt) if out_txt else None,
            "extraction_notes": res.notes,
            "stats": res.stats,
            "word_count_approx": len(re.findall(r"\b\w+\b", text)),
            "signals": {
                "rubric_pattern_hits": count_hits(RUBRIC_PATTERNS, text),
                "brief_pattern_hits": count_hits(BRIEF_PATTERNS, text),
            },
        }
        files.append(entry)
        for child in res.children:
            register(child, folder_key, folder_role, parent=fid,
                     display_path=f"{entry['path']}!/{child.relative_to(WORK_DIR / 'unpacked' / fid).as_posix()}")
        return entry

    if not INPUT_DIR.exists():
        missing_folders = list(INPUT_FOLDERS)
    else:
        for item in sorted(INPUT_DIR.iterdir()):
            if item.is_file() and item.name not in PLACEHOLDER_NAMES and item.name != "README.md":
                misplaced.append(rel(item))
            elif item.is_dir() and item.name not in INPUT_FOLDERS:
                misplaced.append(rel(item) + "/")
        for folder_key, role in INPUT_FOLDERS.items():
            folder = INPUT_DIR / folder_key
            if not folder.exists():
                missing_folders.append(folder_key)
                continue
            for path in sorted(p for p in folder.rglob("*") if p.is_file()):
                if path.name in PLACEHOLDER_NAMES or path.name.startswith("~$"):
                    continue
                register(path, folder_key, role)

    # Exact duplicates
    by_hash: dict[str, list[str]] = {}
    for f in files:
        by_hash.setdefault(f["sha256"], []).append(f["file_id"])
    duplicates = [{"file_ids": ids, "reason": "Identical content (same SHA-256)."}
                  for ids in by_hash.values() if len(ids) > 1]

    def usable(f):
        return f["extraction_status"] in (ex.EXTRACTED, ex.PARTIAL, ex.NEEDS_CLAUDE_READ)

    by_role: dict[str, list[dict]] = {r: [] for r in INPUT_FOLDERS.values()}
    for f in files:
        by_role[f["folder_role"]].append(f)

    top_subs = [f for f in by_role["submission"] if f["parent_archive"] is None]
    competing = []
    doc_kinds = {"docx", "pdf", "pptx"}
    same_kind: dict[str, list[str]] = {}
    for f in top_subs:
        if f["file_kind"] in doc_kinds:
            same_kind.setdefault(f["file_kind"], []).append(f["file_id"])
    for kind, ids in same_kind.items():
        if len(ids) > 1:
            competing.append({"file_ids": ids, "reason": f"Multiple top-level {kind.upper()} files in the submission folder; they may be competing versions or parts of one submission. Agent 0 must decide."})
    versioned = [f["file_id"] for f in top_subs if VERSION_WORDS.search(Path(f["path"]).stem)]
    if len(versioned) > 1:
        competing.append({"file_ids": versioned, "reason": "Several submission filenames contain version words (draft/final/v2/copy)."})

    rubric_files = [f for f in by_role["rubric"] if usable(f)]
    brief_files = [f for f in by_role["brief"] + by_role["additional_instructions"] if usable(f)]
    sub_files = [f for f in by_role["submission"] if usable(f)]
    brief_words = sum(f["word_count_approx"] for f in brief_files)
    rubric_hits = sum(f["signals"]["rubric_pattern_hits"] for f in rubric_files)
    rubric_like_elsewhere = [f["file_id"] for f in brief_files + by_role["supporting"]
                             if f["signals"]["rubric_pattern_hits"] >= 5]

    if not by_role["submission"]:
        prelim, why = "CANNOT_PROCEED", "No file in 04_COMPLETED_ASSIGNMENT/."
    elif not sub_files:
        prelim, why = "CANNOT_PROCEED", "Submission file(s) present but none could be read."
    elif rubric_files:
        prelim, why = "RUBRIC", "Readable file(s) in 02_RUBRIC_AND_MARKING/. Agent 0 must confirm it is a genuine marking scheme."
    elif brief_words >= 40:
        prelim, why = "BRIEF_ONLY", f"Brief/instruction text present (~{brief_words} words) and no rubric file."
    else:
        prelim, why = "TITLE_TOPIC", "No rubric and little or no brief text; only a title/topic (or nothing) is available."

    inventory = {
        "tool": "prepare_run.py",
        "run_id": dt.datetime.now().strftime("%Y%m%d-%H%M%S"),
        "auditor_version": (REPO_ROOT / "VERSION").read_text().strip() if (REPO_ROOT / "VERSION").exists() else "unknown",
        "environment": {"python": platform.python_version(),
                        "pdftotext_available": bool(shutil.which("pdftotext"))},
        "previous_output_archived_to": archived,
        "missing_input_folders": missing_folders,
        "misplaced_items": misplaced,
        "files": files,
        "counts_by_folder": {k: len(by_role[v]) for k, v in INPUT_FOLDERS.items()},
        "exact_duplicates": duplicates,
        "possible_competing_submissions": competing,
        "rubric_like_content_outside_rubric_folder": rubric_like_elsewhere,
        "files_needing_claude_read": [f["file_id"] for f in files if f["extraction_status"] == ex.NEEDS_CLAUDE_READ],
        "files_not_analysable": [{"file_id": f["file_id"], "path": f["path"], "status": f["extraction_status"],
                                  "reason": "; ".join(f["extraction_notes"]) or f["extraction_status"]}
                                 for f in files if f["extraction_status"] in (ex.FAILED, ex.UNSUPPORTED, ex.EMPTY)],
        "advisory_mode": {"preliminary_mode": prelim, "reason": why,
                          "rubric_pattern_hits_in_rubric_folder": rubric_hits,
                          "brief_and_instruction_words": brief_words,
                          "note": "ADVISORY ONLY. Agent 0 must confirm or override with reasons."},
    }
    write_json(WORK_DIR / "INPUT_INVENTORY.json", inventory)

    print(f"Run {inventory['run_id']} — {len(files)} file(s) inventoried.")
    for k, n in inventory["counts_by_folder"].items():
        print(f"  {k}: {n}")
    if archived:
        print(f"  Previous output moved to {archived}")
    if inventory["files_needing_claude_read"]:
        print(f"  Needs Claude Read tool: {', '.join(inventory['files_needing_claude_read'])}")
    for bad in inventory["files_not_analysable"]:
        print(f"  NOT ANALYSABLE: {bad['path']} ({bad['status']})")
    if misplaced:
        print(f"  Misplaced items: {misplaced}")
    print(f"Advisory mode: {prelim} — {why}")
    print(f"Inventory: {rel(WORK_DIR / 'INPUT_INVENTORY.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

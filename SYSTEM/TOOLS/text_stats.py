#!/usr/bin/env python3
"""Deterministic text statistics so no agent has to count by hand.

Usage: python3 SYSTEM/TOOLS/text_stats.py <extracted-text-file> [--json]

Reports: total words; words before a References/Bibliography heading (a common
word-count convention — the brief decides which count applies); headings found;
in-text citation pattern counts; approximate reference-list entries; numbers of
tables/figures mentioned. Counts are approximate for extracted text and must be
reported as such.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REF_HEAD = re.compile(r"^\s*(?:#+\s*)?(?:\d+(?:\.\d+)*\.?\s*)?(references|reference list|bibliography|works cited|sources)\s*$", re.I | re.M)
APPX_HEAD = re.compile(r"^\s*(?:#+\s*)?(?:\d+(?:\.\d+)*\.?\s*)?(appendix|appendices)\b.*$", re.I | re.M)
HEADING = re.compile(r"^(?:#{1,6}\s+.+|(?:\d+(?:\.\d+){0,3}\.?)\s+[A-Z][^\n]{2,80}|[A-Z][A-Z \-&:]{3,60})$", re.M)
AUTHOR_YEAR = re.compile(r"\(([A-Z][A-Za-z'\-]+(?: et al\.?| and [A-Z][A-Za-z'\-]+| & [A-Z][A-Za-z'\-]+)?),? (\d{4}[a-z]?|n\.d\.)(?:[,:] ?(?:p|pp)\.? ?\d+(?:[-–]\d+)?)?\)")
NARRATIVE = re.compile(r"\b[A-Z][A-Za-z'\-]+(?: et al\.?| and [A-Z][A-Za-z'\-]+)? \((\d{4}[a-z]?)\)")
NUMERIC = re.compile(r"\[(\d+(?:[,–-]\s*\d+)*)\]")
WORD = re.compile(r"\b[\w'’-]+\b")


def stats(text: str) -> dict:
    body = "\n".join(l for l in text.splitlines() if not l.startswith("# EXTRACTED TEXT") and not l.startswith("# source:")
                     and not l.startswith("# method:") and not l.startswith("# NOTE:"))
    words = WORD.findall(body)
    ref = REF_HEAD.search(body)
    appx = APPX_HEAD.search(body)
    cut_points = [m.start() for m in (ref, appx) if m]
    main = body[: min(cut_points)] if cut_points else body
    refs_block = body[ref.end(): appx.start() if appx and appx.start() > ref.end() else len(body)] if ref else ""
    ref_entries = [l for l in refs_block.splitlines() if len(l.strip()) > 25]
    headings = [h.strip() for h in HEADING.findall(body)][:200]
    return {
        "words_total": len(words),
        "words_before_references_or_appendices": len(WORD.findall(main)),
        "references_heading_found": bool(ref),
        "appendix_heading_found": bool(appx),
        "reference_list_entries_approx": len(ref_entries),
        "in_text_citations": {
            "author_year_parenthetical": len(AUTHOR_YEAR.findall(main)),
            "author_year_narrative": len(NARRATIVE.findall(main)),
            "numeric_bracket": len(NUMERIC.findall(main)),
        },
        "cited_author_year_keys": sorted({f"{a} {y}" for a, y in AUTHOR_YEAR.findall(main)})[:300],
        "tables_mentioned": len(re.findall(r"\bTable \d+", body)),
        "figures_mentioned": len(re.findall(r"\b(?:Figure|Fig\.) \d+", body)),
        "headings": headings,
        "note": "Approximate counts from machine-extracted text; state them as approximate.",
    }


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    s = stats(Path(argv[0]).read_text(encoding="utf-8", errors="replace"))
    if "--json" in argv:
        print(json.dumps(s, indent=2))
    else:
        for k, v in s.items():
            if k in ("headings", "cited_author_year_keys"):
                print(f"{k}:")
                for h in v:
                    print(f"  - {h}")
            else:
                print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

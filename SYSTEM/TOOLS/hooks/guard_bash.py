#!/usr/bin/env python3
"""Claude Code PreToolUse hook (Bash) — hard safety net for the auditor.

Blocks (exit code 2, reason on stderr):
  1. Executing untrusted submitted code located in INPUT/ or OUTPUT/_work/
     (only syntax-only checks such as `python3 -m py_compile` / `node --check` are allowed).
  2. Staging or force-adding confidential INPUT/ or OUTPUT/ content to git.
  3. Deleting INPUT/ content by anything other than SYSTEM/TOOLS/clear_local_data.py.
Everything else passes through (exit 0). Standard library only.
"""
import json
import re
import sys

try:
    payload = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    sys.exit(0)
if payload.get("tool_name") != "Bash":
    sys.exit(0)
cmd = (payload.get("tool_input") or {}).get("command", "")

UNTRUSTED = r"(?:\./)?(?:INPUT/|OUTPUT/_work/|OUTPUT/_previous_run/)"
SAFE_CHECK = re.compile(r"(python3?\s+-m\s+(py_compile|json\.tool|compileall)\b|node\s+--check\b)")
RUNNERS = re.compile(
    r"(^|[;&|(`\s])(python3?|py|node|deno|bun|ruby|perl|php|bash|sh|zsh|pwsh|powershell|java|javac|"
    r"gcc|g\+\+|clang|make|cmake|cargo|go|dotnet|mvn|gradle|npm|npx|yarn|pnpm|pytest|jupyter|ipython|"
    r"Rscript|R|julia|octave|matlab|source|\.)\s+[^;&|]*" + UNTRUSTED)
DIRECT = re.compile(r"^(?:exec\s+|env\s+)?(?:\w+=\S*\s+)*" + UNTRUSTED + r"\S+")  # path used as the command itself
# The auditor's own trusted tools may take OUTPUT/_work paths as data arguments.
TRUSTED_TOOL = re.compile(r"^(?:\w+=\S*\s+)*python3?\s+(?:\./)?SYSTEM/(?:TOOLS|TESTS)/[\w/.-]+\.py(?:\s|$)")
CHMOD = re.compile(r"chmod\s+[^;&|]*\+x[^;&|]*" + UNTRUSTED)


def block(reason: str) -> None:
    sys.stderr.write(f"BLOCKED by auditor safety hook: {reason}\n"
                     "See SYSTEM/RULES/CODE_EXECUTION_POLICY.md and SYSTEM/RULES/PRIVACY_POLICY.md.\n")
    sys.exit(2)


segments = re.split(r"&&|\|\||;|\n", cmd)
for seg in segments:
    s = seg.strip()
    if not s:
        continue
    if re.search(UNTRUSTED, s):
        if SAFE_CHECK.search(s) or TRUSTED_TOOL.search(s):
            continue
        if RUNNERS.search(" " + s) or DIRECT.search(s) or CHMOD.search(s):
            block("submitted code must never be executed; only static review and syntax-only checks are allowed.")
    # Only inspect git/rm when they are the command itself (not text inside a heredoc or string).
    if re.match(r"^(?:sudo\s+)?git\s+(?:-C\s+\S+\s+)?add\b", s) and (
            re.search(r"\s(?:-f|--force)\b", s) or re.search(r"(?:^|\s)(?:\./)?(?:INPUT|OUTPUT)(?:/|\s|$)", s)):
        block("confidential INPUT/OUTPUT content must never be staged for commit.")
    if re.match(r"^(?:sudo\s+)?rm\b", s) and re.search(r"(?:^|\s)(?:\./)?INPUT(?:/|\s|$)", s):
        block("use `python3 SYSTEM/TOOLS/clear_local_data.py` to clear INPUT/ data.")
sys.exit(0)

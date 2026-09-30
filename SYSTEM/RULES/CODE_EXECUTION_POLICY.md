# Code Execution Policy

Submitted code is **untrusted**. Default and only supported mode: **static review**.

Allowed
- Reading source files, READMEs, test files, notebooks (including their stored outputs, clearly labelled as
  author-saved outputs, not re-executed).
- Syntax-only checks that do not execute program code, run from a copy under `OUTPUT/_work/`:
  - Python: `python3 -m py_compile <file>`  (compiles only)
  - JavaScript: `node --check <file>` (if Node is installed)
  - JSON: `python3 -m json.tool <file>`
- `grep`/pattern searches for risky constructs (eval, exec, subprocess, os.system, hard-coded secrets, SQL string
  concatenation, unbounded recursion, bare except).

Forbidden
- Running, importing, or testing submitted code (`python file.py`, `pytest`, `npm test`, `make`, `java`, notebooks).
- Installing dependencies listed by the submission.
- Network access on behalf of the submission.

Every code review must state exactly:

`CODE WAS REVIEWED STATICALLY; EXECUTION WAS NOT VERIFIED.`

Consequently: correctness of outputs, performance and passing of tests are assessed by reasoning only and
must be qualified (e.g. "by inspection, `average()` divides by zero when the list is empty (line 14)").
Claims such as "the tests pass" or "the program runs" are forbidden unless the claim is quoted from the
submission's own evidence (e.g. a screenshot or stored output), in which case say so.

`validate.py` rejects `execution_performed: true`.

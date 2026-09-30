# Universal Assignment Auditor

Internal Quality Control tool that audits academic and professional deliverables — essays, dissertations/theses,
research and technical reports, literature reviews, business reports, case studies, reflective pieces, lab reports,
coding projects, data-analysis/statistics work, presentations, project documentation and mixed coursework — and
produces an evidence-based, independently re-checked **Final Quality Audit**.

You do not write prompts. You put files in folders and run **one command**: `/check-assignment`.

> **Data privacy warning.** Assignment files and audit reports are confidential. They live only in `INPUT/` and
> `OUTPUT/` on your machine, which are excluded from Git. Never copy them anywhere else in this repository, never
> force-add them to Git, and clear them when you finish (see below).

---

## 1. Installation / first setup

You need:
- **Claude Code** (the CLI, desktop app or IDE extension), signed in with your company account.
- **Git**.
- **Python 3.9+** available as `python3` (or `python` on Windows). No extra Python packages are needed.
- Optional: `pdftotext` (poppler-utils). Without it, PDFs are still read through Claude's own PDF reader; very large
  PDFs may need poppler installed or conversion to DOCX.

No API keys, paid services or personal configuration are needed.

## 2. How to clone the repository

```bash
git clone https://github.com/Digittech-official/universal-assignment-auditor.git
cd universal-assignment-auditor
```

## 3. How to update (git pull)

```bash
cd universal-assignment-auditor
git pull
```
Your `INPUT/` and `OUTPUT/` files are ignored by Git, so pulling never touches them. Check `VERSION` / `CHANGELOG.md`
to see what changed.

## 4. How to open in Claude Code

- Terminal: `cd universal-assignment-auditor` then run `claude`.
- Desktop app / IDE: open the `universal-assignment-auditor` folder as the project.

Claude Code automatically loads the project instructions (`CLAUDE.md`), the `/check-assignment` command, the
specialist agents and the safety settings. If asked whether to trust the project folder, answer yes.

## 5. Employee workflow

1. `git pull` (get the latest version).
2. Put the files into the right `INPUT/` folders (guide below).
3. In Claude Code, type **`/check-assignment`** and press Enter.
4. Wait — the audit runs ~15 specialist stages automatically (typically 10–40 minutes depending on size).
   Approve permission prompts if your Claude Code settings ask.
5. Open `OUTPUT/FINAL_QUALITY_AUDIT.md` (or the `.html` version in a browser).
6. When finished, clear local data (section 10).

## 6. INPUT folder guide

| Folder | What to put there | Needed? |
|---|---|---|
| `INPUT/01_BRIEF_AND_TITLE/` | Assignment brief / task sheet / question. If you only have a title, put it in a `.txt` file here. | Recommended |
| `INPUT/02_RUBRIC_AND_MARKING/` | Marking rubric, marking scheme, grade descriptors, mark allocation | Only if available |
| `INPUT/03_ADDITIONAL_INSTRUCTIONS/` | Lecturer/client emails, clarifications, learning outcomes, extra guidance | Optional |
| `INPUT/04_COMPLETED_ASSIGNMENT/` | The completed work: document, slides, code, notebook, or a ZIP of a project | **Required** |
| `INPUT/05_SUPPORTING_FILES/` | Datasets, templates, handbooks, readings, appendices | Optional |

- One submission per run. Several files belonging to the same submission (e.g. report + code + data) are fine.
  Do **not** leave old drafts next to the final version.
- Supported: PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, IPYNB, ZIP, common source-code files, images (visual review only).
- Not supported (convert first): legacy `.doc`/`.ppt`/`.xls`, password-protected files, OpenDocument/Apple formats.
  Unsupported or unreadable files are **always reported** in the audit, never silently skipped.

## 7. How to run

```
/check-assignment
```

That is the only command. The tool automatically:
validates the files → detects the task type → detects the analysis mode → extracts requirements → interprets the
rubric → builds a quality blueprint → maps the evidence → runs specialist checks (code / data / presentation /
writing) → primary assessment → reference/evidence review → coherence review → independent second marking →
score adjudication (only when authorised) → verification of serious findings → final QA gate → report.

### Analysis modes (chosen automatically)

| Mode | When | What you get |
|---|---|---|
| **Rubric Mode** | A rubric/marking scheme is supplied | Criterion-by-criterion evaluation. Numerical marks **only** if the rubric gives marks or weights; every mark traced to criterion → evidence → descriptor → range |
| **Brief-Only Mode** | A brief exists but no rubric | Requirement-by-requirement compliance and improvement advice. States **NO AUTHORISED NUMERICAL MARKING SCHEME WAS PROVIDED.** No marks |
| **Title/Topic Mode** | Only a title/topic + the work | Quality review separating KNOWN REQUIREMENTS from BEST-PRACTICE EXPECTATIONS. No official grade |

If there is no readable submission (or nothing defines the task), the audit stops safely and writes
`OUTPUT/AUDIT_BLOCKED.md` explaining what to add.

## 8. How to read the output

| File | What it is |
|---|---|
| `OUTPUT/FINAL_QUALITY_AUDIT.md` / `.html` | The report (released only after QA PASS) |
| `OUTPUT/AUDIT_BLOCKED.md` | Written instead of the report when inputs are insufficient or QA failed — explains why |
| `OUTPUT/audit_trail/*.json` | Internal audit trail (manifest, requirements, rubric model, assessments, second marking, scores, verification, QA) |
| `OUTPUT/audit_trail/REQUIREMENT_TRACEABILITY_MATRIX.md` | Every requirement → source → evidence → status |

Report sections (always in this order; non-applicable sections say `NOT APPLICABLE — reason`):
1 Assignment identification · 2 Task type · 3 Analysis mode · 4 Files analysed · 5 Files not analysed ·
6 Executive summary · 7 Numerical mark (only if authorised) · 8 Marking breakdown · 9 Requirement compliance matrix ·
10 Critical issues · 11 Major issues · 12 Moderate improvements · 13 Minor improvements · 14 Passed requirements ·
15 Section-by-section review · 16 Content/analysis · 17 Structure/coherence · 18 Evidence/referencing ·
19 Technical · 20 Coding · 21 Data/statistics · 22 Presentation · 23 Revision priority plan ·
24 Quality improvement map · 25 Pre-submission checklist · 26 Audit limitations.

Every issue is given as **LOCATION → ISSUE → REQUIREMENT → WHY IT MATTERS → HOW TO IMPROVE**. Items labelled
`BEST PRACTICE (not a stated requirement)` are advice, not requirements. Start with section 23 (revision plan).

## 9. What the tool will never do
- Invent requirements, marks, weightings, word counts, references or technical specifications.
- Give a numerical mark without an authorised marking scheme.
- Call a reference fabricated (references are **not** externally verified — the report says so).
- Run submitted code (code is reviewed statically; the report says so).
- Apply dissertation rules to code, or coding rules to essays.

## 10. How to clear local assignment data

```bash
python3 SYSTEM/TOOLS/clear_local_data.py          # asks for confirmation; clears INPUT/ and OUTPUT/
python3 SYSTEM/TOOLS/clear_local_data.py --yes    # no prompt
python3 SYSTEM/TOOLS/clear_local_data.py --output-only
```
Starting a new audit automatically moves the previous output to `OUTPUT/_previous_run/` (also git-ignored).

## 11. Data privacy
- `INPUT/**` and `OUTPUT/**` are git-ignored (only empty folder placeholders are tracked).
- A safety hook blocks `git add` of INPUT/OUTPUT content and blocks execution of submitted code.
- Before any commit (maintainers): `python3 SYSTEM/TOOLS/privacy_check.py`. CI runs it on every push.
- Test fixtures in `SYSTEM/TESTS/fixtures/` are synthetic — never add real assignments there.
- Full policy: `SYSTEM/RULES/PRIVACY_POLICY.md`.

## 12. Troubleshooting

| Problem | Fix |
|---|---|
| `/check-assignment` not listed | Make sure Claude Code was opened **in the repository folder**; run `git pull`; restart Claude Code |
| `python3: command not found` | Install Python 3 (Windows: use `python`; the command falls back automatically) |
| Audit says CANNOT_PROCEED | Read `OUTPUT/AUDIT_BLOCKED.md` — usually the submission folder is empty, unreadable, or contains competing versions |
| A file is listed as `FILE COULD NOT BE RELIABLY ANALYSED.` | Convert it (DOCX/PDF/PPTX/XLSX), remove passwords, re-run |
| Large PDF fails to read | Install poppler-utils (`pdftotext`, `pdftoppm`) or save the PDF as DOCX |
| Report not released (`AUDIT_BLOCKED.md` mentions QA) | Re-run once. If it repeats, send `OUTPUT/audit_trail/QA_STATUS.json` and `VALIDATION_REPORT.json` (no assignment content) to the maintainer |
| Many permission prompts | Accept the "trust this folder" dialog when first opening the project — until you do, Claude Code ignores the project's pre-approved tool list. Otherwise approve prompts as they appear |
| "BLOCKED by auditor safety hook" | Expected when something tried to run submitted code or stage confidential files — nothing to fix |

## 13. Limitations
- AI-assisted assessment is **not infallible** and does not replace an authorised human marker. The workflow reduces
  error through independent second marking, verification of serious findings and a QA gate — it does not remove it.
- Code is reviewed statically; behaviour, performance and test results are not executed or verified.
- References are not checked against external databases.
- Images, charts and embedded objects are not fully transcribed; visual design is only partly assessable.
- Word counts come from extracted text and are approximate.
- Scanned PDFs without a text layer may be unreadable. Legacy Office formats are not supported.
- Output quality depends on the quality and completeness of the supplied brief/rubric.

## 14. Version information
Current version: see `VERSION` (1.0.0 at release). History: `CHANGELOG.md`.
Maintainer documentation: `CLAUDE.md`, `SYSTEM/WORKFLOWS/PIPELINE.md`, `SYSTEM/AGENTS/README.md`, `SYSTEM/TESTS/README.md`.

## 15. Quick start (for a new colleague)
```bash
git clone https://github.com/Digittech-official/universal-assignment-auditor.git
cd universal-assignment-auditor
claude                    # open Claude Code here
```
Copy files into `INPUT/01_…`–`INPUT/05_…`, type `/check-assignment`, read `OUTPUT/FINAL_QUALITY_AUDIT.md`,
then run `python3 SYSTEM/TOOLS/clear_local_data.py`.

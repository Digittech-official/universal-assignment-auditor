# INPUT folder guide

Put the assignment files into these folders, then run `/check-assignment`.
Everything you put here is **git-ignored** and is never committed.

| Folder | Put here | Required? |
|---|---|---|
| `01_BRIEF_AND_TITLE/` | Assignment brief, task sheet, question, or just the title/topic (a `.txt` with the title is fine) | Recommended |
| `02_RUBRIC_AND_MARKING/` | Marking rubric, grade descriptors, marking scheme, mark allocation | Only if you have one |
| `03_ADDITIONAL_INSTRUCTIONS/` | Extra lecturer/client instructions, emails, clarifications, learning outcomes | Optional |
| `04_COMPLETED_ASSIGNMENT/` | The completed work to be checked (document, slides, code, notebook, ZIP of a project) | **Required** |
| `05_SUPPORTING_FILES/` | Datasets, appendices, module handbooks, readings, templates | Optional |

Rules of thumb:

- Put **one** submission in `04_COMPLETED_ASSIGNMENT/` per run (multiple files of the same submission are fine — e.g. report + code).
- Do not rename files to hide their purpose; filenames help classification.
- Do not put files directly in `INPUT/` — use the numbered folders.
- If you only have a title, type it into a `.txt` file in `01_BRIEF_AND_TITLE/`.

Supported: PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, IPYNB, ZIP, common source-code files, images (visual review only).
Not supported: legacy `.doc`, `.ppt`, `.xls`, password-protected files — convert them first. Unsupported files are always reported, never silently ignored.

When finished, clear local data with: `python3 SYSTEM/TOOLS/clear_local_data.py`

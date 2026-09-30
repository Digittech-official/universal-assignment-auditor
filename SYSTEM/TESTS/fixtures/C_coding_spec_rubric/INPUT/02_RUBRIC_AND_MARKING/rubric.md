# COMP1101 Coursework 2 — Marking Rubric: Inventory Manager CLI

Each criterion is marked out of 100 using the level descriptors below. The final mark is the weighted sum of the four criterion marks, expressed as a percentage (out of 100).

| Criterion | Weight |
|---|---|
| Functionality | 40% |
| Code quality | 20% |
| Testing | 20% |
| Documentation | 20% |

Final mark (%) = 0.40 × Functionality + 0.20 × Code quality + 0.20 × Testing + 0.20 × Documentation.

## Criterion 1: Functionality (40%)

| Level | Marks | Descriptor |
|---|---|---|
| Excellent | 80–100 | All required functions (add, remove, list, average price) work correctly, including edge cases. All invalid input is handled with clear error messages and the program never crashes. Inventory is reliably saved to and loaded from JSON. |
| Good | 65–79 | All required functions work for normal input. Most invalid input is handled; at most a minor edge case is unhandled. JSON persistence works. |
| Satisfactory | 50–64 | Most required functions work for normal input. Some invalid input or edge cases (e.g. empty inventory, unknown item) cause errors or crashes. Persistence works with minor issues. |
| Weak | 40–49 | Several required functions are missing or incorrect. Invalid input frequently crashes the program. Persistence is unreliable. |
| Fail | 0–39 | The program does not run or most required functionality is missing. |

## Criterion 2: Code quality (20%)

| Level | Marks | Descriptor |
|---|---|---|
| Excellent | 80–100 | Code is cleanly organised into modules with a clear separation of concerns. Consistently follows PEP 8. Every function has an informative docstring. Meaningful names throughout. |
| Good | 65–79 | Code is well organised with minor PEP 8 lapses. Almost all functions have docstrings. |
| Satisfactory | 50–64 | Code is readable but organisation is uneven; several PEP 8 lapses or missing docstrings. |
| Weak | 40–49 | Code is hard to follow, with poor structure, frequent style problems and few docstrings. |
| Fail | 0–39 | Code is disorganised and largely unreadable. |

## Criterion 3: Testing (20%)

| Level | Marks | Descriptor |
|---|---|---|
| Excellent | 80–100 | Unit tests cover at least three functions thoroughly, including edge cases and invalid input. Tests are well named and pass. |
| Good | 65–79 | Unit tests cover at least three functions for normal cases, with some edge cases. |
| Satisfactory | 50–64 | Unit tests cover fewer than three functions, or cover three functions superficially with no edge cases. |
| Weak | 40–49 | Very limited tests (e.g. one function or trivial assertions only). |
| Fail | 0–39 | No meaningful tests provided. |

## Criterion 4: Documentation (20%)

| Level | Marks | Descriptor |
|---|---|---|
| Excellent | 80–100 | README.md clearly explains the purpose of the program, how to run it and how to run the tests, with examples. Docstrings are complete and accurate. |
| Good | 65–79 | README.md explains how to run the program and the tests, with minor omissions. |
| Satisfactory | 50–64 | README.md is present but omits an important element (e.g. how to run the tests) or is unclear. |
| Weak | 40–49 | README.md is minimal and gives little practical guidance. |
| Fail | 0–39 | No README.md or documentation provided. |

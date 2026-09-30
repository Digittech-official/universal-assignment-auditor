# Privacy & Data-Safety Policy

1. Real assignment files (student/client/company material) live only in `INPUT/` on the employee's machine.
   `INPUT/**` is git-ignored except the folder skeleton.
2. Generated audits live only in `OUTPUT/`, which is git-ignored except `OUTPUT/.gitkeep`.
3. Never copy assignment content into tracked files (agents, rules, tests, README, CHANGELOG, commit messages).
4. Test fixtures under `SYSTEM/TESTS/fixtures/` are **synthetic** and contain no real personal data.
5. No credentials, tokens, `.env` files or personal machine paths in tracked files.
6. Before any commit run `python3 SYSTEM/TOOLS/privacy_check.py` (CI runs it on every push).
7. After finishing a job run `python3 SYSTEM/TOOLS/clear_local_data.py`.
8. The tool never sends assignment content to external services other than the Claude Code session itself;
   it performs no web look-ups of references or student names.

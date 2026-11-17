---
name: commit-changes
description: Commit changes in Kira using its Conventional Commit scopes and required backend and frontend checks. Use when asked to commit changes in this repository.
---

# Commit Changes in Kira

1. Inspect `git status`, staged and unstaged diffs, and recent commits. Preserve unrelated user changes and never stage secrets or generated files.
2. Read `AGENTS.md` for the current approved scopes and verification rules. For backend code, run `ruff check src/ tests/`, `ruff format --check src/ tests/`, `mypy src/`, and `pytest tests/ -v`. For frontend code, run `npm run lint`, `npx tsc --noEmit`, and `npm test` from `frontend/`. Fix failures before committing; report any unavailable check rather than claiming it passed.
3. Stage only intended files by explicit path. Use `<type>(<scope>): <imperative description>` with the type and scope listed in `AGENTS.md`.
4. Commit only after required checks pass, then report the commit hash and remaining working-tree status. Never amend or push unless requested.

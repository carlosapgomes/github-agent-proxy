## Context

The repository includes project code plus checked-in `.pi/skills/` automation utilities and tests. The global Ruff configuration covers the whole repository, so lint and format failures in those helper scripts block the project quality gate. The current failures are mechanical: unused imports, missing `sys` import, unnecessary f-string prefixes, one bare `except`, and formatting drift across several Python files.

## Goals / Non-Goals

**Goals:**
- Make `uv run ruff check .` pass for the current repository contents.
- Make `uv run ruff format --check .` pass for the current repository contents.
- Keep fixes minimal and behavior-preserving.

**Non-Goals:**
- Broad refactoring of helper-script architecture.
- Functional changes to the proxy API.
- Addressing unrelated `mypy` issues outside Ruff scope.

## Decisions

1. **Fix only the currently reported Ruff issues**
   - Decision: target the exact lint/format failures currently reported by Ruff.
   - Rationale: keeps the slice small, auditable, and aligned to the user's request.
   - Alternatives considered:
     - Large-scale cleanup across all scripts (rejected: unnecessary scope expansion).

2. **Use Ruff formatter for formatting drift**
   - Decision: apply `uv run ruff format` to the reported files rather than hand-editing formatting.
   - Rationale: deterministic output and direct alignment with the enforced toolchain.
   - Alternatives considered:
     - Manual reformatting (rejected: error-prone and slower).

3. **Treat the failing Ruff commands as the RED/GREEN signal**
   - Decision: use the quality-gate commands themselves as the failing validation cycle for this maintenance task.
   - Rationale: this slice is repository hygiene rather than runtime feature work.

## Risks / Trade-offs

- **[Risk] Formatting churn touches many helper/test files** → Mitigation: keep semantic edits restricted to files with real lint errors; use formatter only where required.
- **[Risk] Lint-driven fixes could subtly affect script behavior** → Mitigation: limit code edits to clearly safe changes such as imports, exception specificity, and string literals.

## Migration Plan

1. Reproduce failing Ruff check and format check.
2. Apply minimal code fixes to the reported lint violations.
3. Run Ruff formatter on the reported files.
4. Re-run Ruff check and format check to confirm green.
5. Update change task state, commit, and push.

## Open Questions

- None.

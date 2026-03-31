## Context

`uv run mypy .` currently fails on a small set of test typing issues: incomplete `GitHubAppConfig` construction in tests, mocked methods being typed too narrowly for mock assertions, and optional `Policy` values being passed into service constructors in security/integration tests. These are baseline maintenance problems rather than product behavior issues.

## Goals / Non-Goals

**Goals:**
- Make `uv run mypy .` pass for the current repository state.
- Keep changes minimal and behavior-preserving.
- Limit changes to typing/test scaffolding unless production typing must be clarified.

**Non-Goals:**
- Refactor runtime service architecture.
- Change endpoint behavior.
- Expand scope beyond the currently reported mypy failures.

## Decisions

1. **Fix only the reported mypy failures**
   - Decision: target the exact files and error classes currently reported by mypy.
   - Rationale: keeps the slice small and auditable.

2. **Prefer test-local typing fixes**
   - Decision: adjust tests to use properly typed mocks/casts/asserts rather than weakening production types.
   - Rationale: preserves runtime contracts while satisfying static analysis.

3. **Use explicit non-optional assertions in tests**
   - Decision: assert `policy is not None` before constructing services where test setup guarantees it.
   - Rationale: communicates test invariants clearly to mypy.

## Risks / Trade-offs

- **[Risk] Mock typing fixes can make tests noisier** → Mitigation: keep changes small and focused around failing assertions.
- **[Risk] Overuse of `cast` can hide real issues** → Mitigation: only cast where mocks intentionally provide dynamic testing behavior.

## Migration Plan

1. Reproduce current mypy failures.
2. Fix test typing issues file by file.
3. Re-run `uv run mypy .` until green.
4. Run the full quality gate commands and update evidence.

## Open Questions

- None.

## Why

The repository quality gate still fails on `uv run mypy .` due to pre-existing typing issues in tests. This prevents a clean end-to-end validation run even though runtime behavior is already working, so we need to restore a passing type-check baseline.

## What Changes

- Fix the current mypy errors in test code and test setup.
- Keep runtime behavior unchanged.
- Restore a clean `uv run mypy .` quality-gate result.

## Capabilities

### New Capabilities
- `quality-gate-mypy-baseline`: Maintain a repository baseline where the shipped code and tests pass the configured mypy run.

### Modified Capabilities
- None.

## Impact

- Affected code: test files and type annotations used by the quality gate.
- APIs: No public API changes.
- Operations: Restores a clean type-check validation run.

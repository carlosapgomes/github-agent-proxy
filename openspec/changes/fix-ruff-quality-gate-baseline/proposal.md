## Why

The project quality gate currently fails on `uv run ruff check .` and `uv run ruff format --check .` because several repository-shipped helper scripts under `.pi/skills/` do not meet the configured Ruff baseline. This blocks a clean validation run even when product changes are correct, so we need to restore a passing lint/format baseline.

## What Changes

- Fix current Ruff lint violations in repository-tracked helper scripts.
- Reformat the files Ruff reports as non-compliant so `ruff format --check .` passes.
- Keep runtime behavior unchanged aside from safe lint-driven cleanup.

## Capabilities

### New Capabilities
- `quality-gate-ruff-baseline`: Maintain a repository baseline where shipped helper scripts pass Ruff lint and format checks.

### Modified Capabilities
- None.

## Impact

- Affected code: `.pi/skills/**`, `skills/github-proxy/scripts/github_proxy_cli.py`, and related tests that Ruff reformats.
- APIs: No public API contract changes.
- Operations: Restores clean quality-gate execution for Ruff lint and format checks.

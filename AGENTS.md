# AGENTS.md

## 1. Stack and Versions
- Language: Python 3.12+
- Framework: FastAPI
- Runtime server: Uvicorn
- Dependency/project manager: `uv`
- HTTP client: `httpx`
- Config: `pydantic-settings` + YAML policy file
- Spec workflow: OpenSpec

## 2. Validation Commands (Quality Gate)
Use `uv` for all Python commands.

```bash
# test suite
uv run pytest -q

# lint + format check
uv run ruff check .
uv run ruff format --check .

# type-check
uv run mypy .

# spec consistency for active change
openspec validate add-github-agent-proxy-mvp
```

If dev tools are missing, install them first:

```bash
uv add --dev pytest ruff mypy
```

## 3. Essential Local Commands

### Setup
```bash
uv sync
```

### Run locally
```bash
# adjust import path once app module is created
uv run uvicorn app.main:app --reload
```

### Quick test run
```bash
uv run pytest -q tests/unit
```

### Full test run
```bash
uv run pytest -q
```

## 4. Architecture and Constraints
- System boundary: `Hermes Agent -> FastAPI Proxy -> GitHub API`.
- Hermes MUST never have direct GitHub write access.
- Proxy exposes only 3 write endpoints:
  - `POST /create-branch`
  - `POST /commit-files`
  - `POST /create-pr`
- Authorization MUST come from YAML policy:
  - `allowed_repos`
  - `allowed_actions`
  - `protected_branches`
- Commits/push-like writes to protected branches (`main`, `master`, configured protected branches) are forbidden.
- GitHub auth MUST use GitHub App installation token per request.
- Logging MUST emit structured JSON with at least `timestamp`, `agent`, `repo`, `action`.

## 5. Testing Policy
- Mandatory TDD cycle: RED -> GREEN -> REFACTOR.
- Do not implement behavior before a failing test (except non-code setup/docs tasks).
- Prefer endpoint-level vertical-slice tests per task.
- Mock/stub GitHub API interactions in tests (no live GitHub dependency in test suite).
- Each implemented requirement/scenario should map to at least one test case.

## 6. Stop Rule (CRUCIAL)
- Implement exactly one vertical slice/task at a time.
- Do not do horizontal layer-only slices without end-to-end value.
- For active non-QUICK changes, require `design.md` before implementation.
- Run validation commands from section 2.
- Update OpenSpec artifacts (`tasks.md`, specs/docs when needed).
- Commit with traceable message including task ID.
- Push branch.
- STOP and request explicit confirmation before the next task.

## 7. Definition of Done (DoD)
- [ ] Relevant tests are implemented and passing
- [ ] Lint/format/type-check pass (or documented temporary exception)
- [ ] OpenSpec artifacts updated (`tasks.md` at minimum)
- [ ] Security constraints preserved (no protected-branch direct writes)
- [ ] Commit message references task/slice ID
- [ ] Push completed to remote branch

## 8. Forbidden Anti-Patterns
- Do not add generic GitHub passthrough endpoints.
- Do not bypass policy checks in endpoint handlers.
- Do not hardcode allowed repos/actions in code when policy file should govern behavior.
- Do not write directly to protected branches, even for convenience.
- Do not couple transport validation, policy logic, and GitHub client calls into one God function.
- Do not continue to next task without explicit user approval.

## 9. Re-entry Prompt
```text
Read AGENTS.md and PROJECT_CONTEXT.md first.
Read openspec/changes/add-github-agent-proxy-mvp/{proposal.md,design.md,tasks.md} and related specs.
Implement ONLY the next incomplete task from tasks.md.
Use vertical slicing and TDD: RED -> GREEN -> REFACTOR.
Mock GitHub API interactions in tests.
Run quality gate commands and openspec validation.
Update tasks.md, commit, push, then STOP and ask for explicit confirmation.
```

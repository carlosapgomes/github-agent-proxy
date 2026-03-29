# HANDOFF_LLM.md

Operational handoff for any LLM continuing development of `github-agent-proxy`.

## 1) Mission

Implement the active OpenSpec change:

- `openspec/changes/add-github-agent-proxy-mvp/`

using **TDD** and **vertical slices**, with strict security constraints:

- no direct writes to protected branches
- no generic GitHub passthrough endpoints
- only the 3 MVP endpoints (`/create-branch`, `/commit-files`, `/create-pr`)

Do **not** implement outside the approved change scope.

---

## 2) Mandatory read order (before coding)

1. `AGENTS.md`
2. `PROJECT_CONTEXT.md`
3. `openspec/changes/add-github-agent-proxy-mvp/proposal.md`
4. `openspec/changes/add-github-agent-proxy-mvp/design.md`
5. `openspec/changes/add-github-agent-proxy-mvp/tasks.md`
6. All specs under:
   - `openspec/changes/add-github-agent-proxy-mvp/specs/**/spec.md`

Then run:

```bash
openspec validate add-github-agent-proxy-mvp
```

---

## 3) Current implementation strategy

Follow tasks in order from:

- `openspec/changes/add-github-agent-proxy-mvp/tasks.md`

High-level sequence:

1. Foundation/policy primitives
2. Vertical Slice A: `POST /create-branch`
3. Vertical Slice B: `POST /commit-files`
4. Vertical Slice C: `POST /create-pr`
5. End-to-end and final verification

This sequence is intentional: shared security primitives first, then endpoint-by-endpoint delivery.

---

## 4) Execution loop (strict)

For each task `X.Y`:

1. Confirm target task (lowest unchecked, unless user explicitly overrides).
2. **RED**: write failing tests for that task.
3. **GREEN**: implement minimal code to pass tests.
4. **REFACTOR**: clean code, keep tests green.
5. Run quality checks.
6. Update `tasks.md` checkbox for task `X.Y`.
7. Commit with task ID in message.
8. Push branch.
9. **STOP** and ask for explicit confirmation before next task.

Never execute multiple tasks in one iteration unless explicitly approved.

---

## 5) Branch, commit, and reporting rules

- Work on a feature branch (example: `feature/add-github-agent-proxy-mvp`).
- Commit format:
  - `feat(task-2.1): add failing tests for create-branch`
  - `feat(task-2.2): implement create-branch endpoint policy checks`
  - `refactor(task-2.4): simplify branch service orchestration`
- After each task, provide a short report:
  - Task completed
  - Files changed
  - Tests added/updated
  - Commands executed and results
  - Open risks/questions

---

## 6) Quality gate (per task)

Use `uv` for all Python commands.

Minimum expected per task:

```bash
uv run pytest -q
```

When tooling is available in project, also run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

If a tool is not configured yet, report it explicitly and proceed only with available checks.

---

## 7) Testing guidance

- Prefer API-level tests for endpoint slices.
- Mock/stub GitHub API interactions in tests.
- Do not rely on live GitHub calls in local test suite.
- Every requirement/scenario added in specs should map to at least one test case.

---

## 8) Non-negotiable security constraints

Enforce in code and tests:

- Bearer API key auth required
- YAML policy enforcement (`allowed_repos`, `allowed_actions`, `protected_branches`)
- reject direct write attempts to protected branches
- per-request GitHub App installation token usage
- structured JSON audit log per request with:
  - `timestamp`
  - `agent`
  - `repo`
  - `action`

---

## 9) Clarification policy

If any requirement is ambiguous:

- pause,
- ask a direct question,
- do not guess on security-sensitive behavior.

Especially clarify before changing:

- protected branch behavior
- PR base/head validation
- auth or authorization semantics

---

## 10) Definition of done for each task

A task is done only if all are true:

- behavior implemented according to relevant spec scenarios
- tests exist and pass
- `tasks.md` updated
- commit + push completed
- progress reported
- execution stopped pending explicit approval

# PROJECT_CONTEXT.md

## Purpose
`github-agent-proxy` is a security middleware that sits between Hermes (an automated coding agent) and the GitHub API.

Its purpose is to enforce strict operational boundaries so Hermes can only:
- create branches,
- commit file changes on non-protected branches,
- create pull requests.

All repository changes must flow through PRs with human review.

## Authoritative Sources
- `AGENTS.md`
- Active OpenSpec change:
  - `openspec/changes/add-github-agent-proxy-mvp/proposal.md`
  - `openspec/changes/add-github-agent-proxy-mvp/design.md`
  - `openspec/changes/add-github-agent-proxy-mvp/tasks.md`
  - `openspec/changes/add-github-agent-proxy-mvp/specs/**/spec.md`
- `docs/adr/`

In case of conflict, the most recent approved OpenSpec artifacts in Git are source of truth.

## System Objective
Provide a minimal and auditable API proxy that removes direct GitHub write access from Hermes while allowing controlled development automation through a constrained endpoint set.

## High-Level Architecture
- **Client**: Hermes agent authenticated with a static API key (`Authorization: Bearer <API_KEY>`).
- **Service**: FastAPI proxy enforcing authN/authZ and branch safety constraints.
- **Upstream**: GitHub API authenticated via GitHub App installation token generated per request.
- **Policy source**: YAML config (`allowed_repos`, `allowed_actions`, `protected_branches`).
- **Auditability**: structured JSON request logs.

## Current MVP Scope (Active Change)
- Endpoint 1: `POST /create-branch`
- Endpoint 2: `POST /commit-files`
- Endpoint 3: `POST /create-pr`
- Policy enforcement and protected-branch safeguards
- Basic structured audit logging

## Out of Scope (for current change)
- Generic GitHub proxy behavior
- Arbitrary GitHub actions/endpoints
- Agent code execution/sandboxing
- Advanced policy controls (rate limits, per-file caps, quotas)

## Non-Negotiable Rules
- Never allow direct write behavior to `main`, `master`, or configured protected branches.
- Always enforce policy checks (`allowed_repos`, `allowed_actions`, `protected_branches`).
- Always use GitHub App installation token per request.
- Keep endpoint contracts explicit and minimal.
- Every meaningful change must leave evidence in Git (tests/spec/tasks/commits).

## Delivery Strategy
Implement using endpoint-oriented vertical slices with TDD:
1. Foundation/policy primitives
2. `/create-branch`
3. `/commit-files`
4. `/create-pr`
5. End-to-end flow validation (`create-branch -> commit-files -> create-pr`)

After each task: validate, update artifacts, commit, push, and stop for explicit approval.

## Quality Bar
- Tests pass locally for affected scope
- No critical lint/type-check issues
- OpenSpec change remains valid (`openspec validate add-github-agent-proxy-mvp`)
- Security invariants are covered by tests
- Artifacts stay aligned with implemented behavior
